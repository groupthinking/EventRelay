"""Offline lifecycle regressions; load only the stdlib fixture module."""

import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/youtube_extension/services/agents/astra_backend.py"
)
spec = importlib.util.spec_from_file_location("astra_lifecycle_subject", MODULE_PATH)
astra = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = astra
spec.loader.exec_module(astra)


class FixtureTransport:
    is_live = False

    def __init__(self):
        self.calls = 0

    async def create_response(self, payload):
        self.calls += 1
        return {
            "id": "response-fixture",
            "status": "in_progress",
            "output": [
                {
                    "type": "function_call",
                    "call_id": "call-1",
                    "name": "read",
                    "arguments": "{}",
                }
            ],
        }


class AstraLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.transport = FixtureTransport()
        self.backend = astra.AstraBackend(
            astra.AstraBackendConfig(
                enabled=True,
                tool_definitions=(
                    astra.AstraToolDefinition(
                        "read", ("GET",), ("https://example.invalid",)
                    ),
                ),
            ),
            self.transport,
        )
        self.control = astra.AstraControlRecord(
            "eventrelay-control-plane",
            "origin:test",
            "run-1",
            "task-1",
            "tool_call",
            "2099-01-01T00:00:00+00:00",
            "nonce",
            "receipt://fixture/control",
        )
        self.scope = {"origin": "test", "task_id": "task-1", "run_id": "run-1"}
        self.result = {
            "method": "GET",
            "destination": "https://example.invalid",
            "receipt_locator": "receipt://fixture/result",
        }

    def execute(self):
        return asyncio.run(
            self.backend.execute(
                "read evidence",
                {"stable_run_id": "run-1"},
                origin="test",
                task_id="task-1",
                control_record=self.control,
            )
        )

    def pending(self):
        return self.backend.store.get_pending_call(**self.scope, call_id="call-1")

    def submit(self):
        return self.backend.submit_tool_result(
            **self.scope, call_id="call-1", result=self.result
        )

    def test_expired_result_is_rejected(self):
        self.execute()
        self.pending().deadline_at = "2000-01-01T00:00:00+00:00"
        result = self.submit()
        self.assertFalse(result.applied)
        self.assertEqual(result.reason, "pending_call_expired")

    def test_malformed_deadline_is_rejected(self):
        self.execute()
        self.pending().deadline_at = "not-a-date"
        self.assertFalse(self.submit().applied)

    def test_duplicate_provider_call_does_not_reset_completed_result(self):
        self.execute()
        self.assertTrue(self.submit().applied)
        self.execute()
        duplicate = self.submit()
        self.assertFalse(duplicate.applied)
        self.assertEqual(duplicate.state, "duplicate_ignored")

    def test_cancelled_run_cannot_reopen_through_execute(self):
        self.execute()
        self.backend.store.set_run_status(**self.scope, status="cancelled")
        with self.assertRaises(astra.AstraExecutionBlocked):
            self.execute()
        self.assertEqual(self.transport.calls, 1)

    def test_receipt_contains_receipt_locators_not_run_dictionary_keys(self):
        self.execute()
        self.submit()
        receipt = self.execute()
        self.assertEqual(receipt.completed_receipts, ("receipt://fixture/result",))

    def test_prior_receipt_pending_snapshot_does_not_mutate(self):
        receipt = self.execute()
        self.submit()
        self.assertEqual(receipt.pending_calls[0].state, "pending")
        self.assertIsNone(receipt.pending_calls[0].result_digest)

    def test_cross_origin_callback_remains_denied(self):
        self.execute()
        result = self.backend.submit_tool_result(
            origin="peer",
            task_id="task-1",
            run_id="run-1",
            call_id="call-1",
            result=self.result,
        )
        self.assertFalse(result.applied)

    def test_replayed_call_id_with_changed_arguments_is_rejected(self):
        self.execute()
        original = self.pending()
        from dataclasses import replace

        replay = replace(original, serialized_input_digest="different")
        with self.assertRaises(astra.AstraExecutionBlocked):
            self.backend.store.add_pending_call(replay)
        self.assertIs(self.pending(), original)


if __name__ == "__main__":
    unittest.main()
