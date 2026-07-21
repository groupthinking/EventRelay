import importlib
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


def _gate_module():
    try:
        return importlib.import_module(
            "scripts.ci.agent_completion_gate"
        )
    except ModuleNotFoundError:
        raise AssertionError("completion gate is not implemented") from None


def _evaluate(payload):
    return _gate_module().evaluate(payload)


def _valid_payload():
    run_id = "agent-run-123"
    head_sha = "a" * 40
    return {
        "issue": {
            "number": 813,
            "description": "Add a deterministic completion gate.",
            "acceptance_criteria": ["Reject incomplete agent output."],
            "declared_files": [
                "src/youtube_extension/agent_lock/completion_gate.py",
                "tests/unit/test_agent_completion_gate.py",
            ],
            "scope_unrestricted": False,
        },
        "pull_request": {
            "changed_files": [
                "src/youtube_extension/agent_lock/completion_gate.py",
                "tests/unit/test_agent_completion_gate.py",
            ],
            "present_changed_files": [
                "src/youtube_extension/agent_lock/completion_gate.py",
                "tests/unit/test_agent_completion_gate.py",
            ],
            "merged": False,
            "draft": False,
            "title_valid": True,
            "required_checks_passed": True,
            "post_merge_checks_passed": False,
        },
        "events": [
            {
                "kind": "completed",
                "sequence": 1,
                "author": "example-agent[bot]",
                "run_id": run_id,
                "head_sha": head_sha,
            }
        ],
        "reviews": [],
        "evidence": {
            "behavior_changed_files": [
                "src/youtube_extension/agent_lock/completion_gate.py"
            ],
            "focused_test_files": ["tests/unit/test_agent_completion_gate.py"],
            "focused_test_results": {
                "tests/unit/test_agent_completion_gate.py": {
                    "passed": 1,
                    "failed": 0,
                    "errors": 0,
                    "skipped": 0,
                    "xfailed": 0,
                    "xpassed": 0,
                }
            },
            "copilot_current_head_reviewed": True,
            "copilot_rabbit_label": True,
        },
        "collection_errors": [],
        "policy": {
            "applicable": True,
            "agent_login": "example-agent[bot]",
            "run_id": run_id,
            "head_sha": head_sha,
        },
    }


def _fixture(name):
    test_root = Path(__file__).resolve().parent
    fixture_root = test_root / "fixtures"
    if not fixture_root.exists():
        fixture_root = test_root.parent / "fixtures"
    return json.loads(
        (fixture_root / "agent_completion" / name).read_text(encoding="utf-8")
    )


def _repo_root():
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "scripts" / "ci" / "agent_completion_gate.py").exists():
            return candidate
    raise AssertionError("repository root not found")


def _javascript_functions(source, signature):
    """Extract repeated JavaScript function declarations with balanced braces."""

    functions = []
    cursor = 0
    while True:
        start = source.find(signature, cursor)
        if start < 0:
            return functions
        opening = source.index("{", start)
        depth = 0
        for index in range(opening, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    functions.append(source[start:index + 1])
                    cursor = index + 1
                    break
        else:
            raise AssertionError(f"unclosed JavaScript function: {signature}")


def _github_script_bodies(workflow):
    """Extract YAML literal bodies assigned to github-script's script input."""

    lines = workflow.splitlines()
    bodies = []
    for index, line in enumerate(lines):
        if line.lstrip() != "script: |":
            continue
        key_indent = len(line) - len(line.lstrip())
        body_lines = []
        for candidate in lines[index + 1:]:
            if candidate.strip():
                indent = len(candidate) - len(candidate.lstrip())
                if indent <= key_indent:
                    break
            body_lines.append(candidate)
        content_indents = [
            len(candidate) - len(candidate.lstrip())
            for candidate in body_lines
            if candidate.strip()
        ]
        if content_indents:
            content_indent = min(content_indents)
            bodies.append("\n".join(
                candidate[content_indent:] if candidate.strip() else ""
                for candidate in body_lines
            ))
    return bodies


class CompletionGateTests(unittest.TestCase):
    def test_blank_issue_description_is_blocked(self):
        payload = _valid_payload()
        payload["issue"]["description"] = "   "

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("blank_issue_description", result["reasons"])

    def test_missing_acceptance_criteria_is_blocked(self):
        payload = _valid_payload()
        payload["issue"]["acceptance_criteria"] = []

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("missing_acceptance_criteria", result["reasons"])

    def test_missing_declared_scope_is_blocked(self):
        payload = _valid_payload()
        payload["issue"]["declared_files"] = []

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("missing_declared_scope", result["reasons"])

    def test_pr_813_declared_two_files_but_changed_five_is_scope_drift(self):
        payload = _valid_payload()
        payload["issue"]["declared_files"] = [
            "src/agents/specialized/quality_agent.py",
            "src/youtube_extension/backend/ai_code_generator.py",
        ]
        payload["pull_request"]["changed_files"] = [
            "apps/web/package.json",
            "package-lock.json",
            "src/agents/specialized/quality_agent.py",
            "src/youtube_extension/backend/ai_code_generator.py",
            "tests/unit/test_cloud_routes.py",
        ]
        payload["pull_request"]["present_changed_files"] = list(
            payload["pull_request"]["changed_files"]
        )
        payload["evidence"]["behavior_changed_files"] = []
        payload["evidence"]["focused_test_files"] = []
        payload["evidence"]["focused_test_results"] = {}

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("scope_drift", result["reasons"])
        self.assertEqual(
            result["details"]["undeclared_files"],
            [
                "apps/web/package.json",
                "package-lock.json",
                "tests/unit/test_cloud_routes.py",
            ],
        )

    def test_declared_files_are_required_not_only_allowed(self):
        payload = _valid_payload()
        payload["pull_request"]["changed_files"] = [
            "tests/unit/test_agent_completion_gate.py"
        ]
        payload["pull_request"]["present_changed_files"] = [
            "tests/unit/test_agent_completion_gate.py"
        ]
        payload["evidence"]["behavior_changed_files"] = []

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("missing_declared_files", result["reasons"])
        self.assertEqual(
            result["details"]["missing_declared_files"],
            ["src/youtube_extension/agent_lock/completion_gate.py"],
        )

    def test_deleted_or_renamed_declared_file_is_missing(self):
        required = "src/youtube_extension/agent_lock/completion_gate.py"
        test_path = "tests/unit/test_agent_completion_gate.py"
        replacement = "src/youtube_extension/agent_lock/replacement.py"
        cases = (
            ([required, test_path], [test_path], []),
            (
                [required, replacement, test_path],
                [replacement, test_path],
                [replacement],
            ),
        )
        for changed, present, allowed_extras in cases:
            with self.subTest(changed=changed, present=present):
                payload = _valid_payload()
                payload["pull_request"]["changed_files"] = changed
                payload["pull_request"]["present_changed_files"] = present
                payload["issue"]["allowed_extra_files"] = allowed_extras
                payload["evidence"]["behavior_changed_files"] = present

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("missing_declared_files", result["reasons"])
                self.assertEqual(
                    result["details"]["missing_declared_files"],
                    [required],
                )
                self.assertNotIn("scope_drift", result["reasons"])

    def test_rename_source_still_counts_toward_scope_drift(self):
        payload = _valid_payload()
        replacement = "src/youtube_extension/agent_lock/replacement.py"
        payload["issue"]["declared_files"] = [
            replacement,
            "tests/unit/test_agent_completion_gate.py",
        ]
        payload["pull_request"]["changed_files"] = [
            "src/youtube_extension/agent_lock/completion_gate.py",
            replacement,
            "tests/unit/test_agent_completion_gate.py",
        ]
        payload["pull_request"]["present_changed_files"] = [
            replacement,
            "tests/unit/test_agent_completion_gate.py",
        ]
        payload["evidence"]["behavior_changed_files"] = [replacement]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("scope_drift", result["reasons"])
        self.assertEqual(
            result["details"]["undeclared_files"],
            ["src/youtube_extension/agent_lock/completion_gate.py"],
        )

    def test_declared_rename_with_allowed_previous_path_is_ready(self):
        payload = _valid_payload()
        previous = "src/youtube_extension/agent_lock/completion_gate.py"
        replacement = "src/youtube_extension/agent_lock/replacement.py"
        test_path = "tests/unit/test_agent_completion_gate.py"
        payload["issue"]["declared_files"] = [replacement, test_path]
        payload["issue"]["allowed_extra_files"] = [previous]
        payload["pull_request"]["changed_files"] = [
            previous,
            replacement,
            test_path,
        ]
        payload["pull_request"]["present_changed_files"] = [
            replacement,
            test_path,
        ]
        payload["evidence"]["behavior_changed_files"] = [replacement]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "ready")
        self.assertEqual(result["reasons"], [])

    def test_present_changed_files_must_be_subset_of_all_changed_files(self):
        payload = _valid_payload()
        payload["pull_request"]["present_changed_files"].append(
            "src/not-in-the-diff.py"
        )

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertEqual(result["reasons"], ["invalid_payload"])
        self.assertIn(
            "pull_request.present_changed_files",
            result["details"]["invalid_fields"],
        )

    def test_present_changed_files_is_required(self):
        payload = _valid_payload()
        del payload["pull_request"]["present_changed_files"]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertEqual(result["reasons"], ["invalid_payload"])
        self.assertIn(
            "pull_request.present_changed_files",
            result["details"]["invalid_fields"],
        )

    def test_allowed_extra_files_remain_optional(self):
        payload = _valid_payload()
        payload["issue"]["allowed_extra_files"] = ["docs/optional.md"]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "ready")

    def test_explicit_unrestricted_scope_allows_undeclared_files(self):
        payload = _valid_payload()
        payload["issue"]["declared_files"] = []
        payload["issue"]["scope_unrestricted"] = True
        payload["pull_request"]["changed_files"].append("docs/extra.md")
        payload["pull_request"]["present_changed_files"].append(
            "docs/extra.md"
        )

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "ready")
        self.assertNotIn("scope_drift", result["reasons"])

    def test_unrestricted_scope_does_not_waive_declared_deliverables(self):
        payload = _valid_payload()
        payload["issue"]["scope_unrestricted"] = True
        payload["pull_request"]["changed_files"] = [
            "tests/unit/test_agent_completion_gate.py",
            "docs/extra.md",
        ]
        payload["pull_request"]["present_changed_files"] = list(
            payload["pull_request"]["changed_files"]
        )
        payload["evidence"]["behavior_changed_files"] = []

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("missing_declared_files", result["reasons"])
        self.assertNotIn("scope_drift", result["reasons"])

    def test_completion_followed_by_error_is_contradictory(self):
        payload = _valid_payload()
        payload["events"] = [
            {
                "kind": "completed",
                "sequence": 1,
                "author": "example-agent[bot]",
                "run_id": "agent-run-123",
                "head_sha": "a" * 40,
            },
            {
                "kind": "error",
                "sequence": 2,
                "author": "example-agent[bot]",
                "run_id": "agent-run-123",
                "head_sha": "a" * 40,
            },
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("contradictory_terminal_events", result["reasons"])

    def test_artifact_ready_followed_by_error_is_failed_not_completed(self):
        payload = _valid_payload()
        payload["events"] = [
            {
                "kind": "artifact_ready",
                "sequence": 1,
                "author": "example-agent[bot]",
                "run_id": "agent-run-123",
                "head_sha": "a" * 40,
            },
            {
                "kind": "error",
                "sequence": 2,
                "author": "example-agent[bot]",
                "run_id": "agent-run-123",
                "head_sha": "a" * 40,
            },
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("agent_run_failed", result["reasons"])

    def test_missing_agent_result_is_blocked(self):
        payload = _valid_payload()
        payload["events"] = []

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("missing_agent_result", result["reasons"])

    def test_successful_new_run_can_recover_from_an_old_run_error(self):
        payload = _valid_payload()
        payload["policy"]["run_id"] = "new-run"
        payload["events"] = [
            {
                "kind": "error",
                "author": "example-agent[bot]",
                "run_id": "old-run",
                "head_sha": "a" * 40,
                "sequence": 1,
            },
            {
                "kind": "completed",
                "author": "example-agent[bot]",
                "run_id": "new-run",
                "head_sha": "a" * 40,
                "sequence": 2,
            },
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "ready")

    def test_historical_success_cannot_satisfy_a_silent_current_run(self):
        payload = _valid_payload()
        payload["policy"]["run_id"] = "new-run"
        payload["events"] = [
            {
                "kind": "completed",
                "author": "example-agent[bot]",
                "run_id": "old-run",
                "head_sha": "a" * 40,
                "sequence": 1,
            },
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("missing_agent_result", result["reasons"])

    def test_unscoped_success_cannot_satisfy_a_correlated_run(self):
        payload = _valid_payload()
        payload["policy"]["run_id"] = "new-run"
        payload["events"] = [
            {
                "kind": "completed",
                "sequence": 1,
                "author": "example-agent[bot]",
            },
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("missing_agent_result", result["reasons"])

    def test_success_from_an_old_head_cannot_satisfy_current_head(self):
        payload = _valid_payload()
        payload["policy"].update(
            {"run_id": "new-run", "head_sha": "b" * 40}
        )
        payload["events"] = [
            {
                "kind": "completed",
                "author": "example-agent[bot]",
                "run_id": "new-run",
                "head_sha": "a" * 40,
                "sequence": 1,
            },
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("missing_agent_result", result["reasons"])

    def test_head_sha_comparison_is_case_insensitive(self):
        payload = _valid_payload()
        payload["policy"]["head_sha"] = "A" * 40
        payload["events"][0]["head_sha"] = "a" * 40

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "ready")

    def test_legacy_ready_plus_correlated_error_is_contradictory(self):
        payload = _valid_payload()
        payload["policy"]["run_id"] = "1892762060881911102"
        payload["events"] = [
            {
                "kind": "artifact_ready",
                "run_id": None,
                "sequence": 1,
                "author": "example-agent[bot]",
            },
            {
                "kind": "error",
                "run_id": "1892762060881911102",
                "sequence": 2,
                "author": "example-agent[bot]",
            },
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("contradictory_terminal_events", result["reasons"])

    def test_legacy_ready_plus_unscoped_error_is_contradictory(self):
        payload = _valid_payload()
        payload["events"] = [
            {
                "kind": "artifact_ready",
                "sequence": 1,
                "author": "example-agent[bot]",
            },
            {
                "kind": "error",
                "sequence": 2,
                "author": "example-agent[bot]",
            },
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("agent_run_failed", result["reasons"])
        self.assertIn("contradictory_terminal_events", result["reasons"])

    def test_unscoped_error_still_blocks_a_correlated_run(self):
        payload = _valid_payload()
        payload["policy"]["run_id"] = "new-run"
        payload["events"] = [
            {
                "kind": "error",
                "sequence": 1,
                "author": "example-agent[bot]",
            },
            {
                "kind": "completed",
                "author": "example-agent[bot]",
                "run_id": "new-run",
                "head_sha": "a" * 40,
                "sequence": 2,
            },
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("agent_run_failed", result["reasons"])

    def test_green_ci_does_not_override_unresolved_blocking_review(self):
        payload = _valid_payload()
        payload["pull_request"]["required_checks_passed"] = True
        payload["reviews"] = [
            {
                "blocking": True,
                "resolved": False,
                "source": "discussion_r3599972900",
            }
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("unresolved_review", result["reasons"])
        self.assertEqual(
            result["details"]["unresolved_reviews"],
            ["discussion_r3599972900"],
        )

    def test_agent_pr_requires_copilot_review_contract(self):
        cases = (
            (
                "copilot_current_head_reviewed",
                "missing_copilot_current_head_review",
            ),
            ("copilot_rabbit_label", "missing_copilot_rabbit_label"),
        )
        for field, reason in cases:
            with self.subTest(field=field):
                payload = _valid_payload()
                payload["evidence"][field] = False

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn(reason, result["reasons"])

    def test_failed_required_checks_are_blocked(self):
        payload = _valid_payload()
        payload["pull_request"]["required_checks_passed"] = False

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("required_checks_failed", result["reasons"])

    def test_behavior_change_without_focused_test_evidence_is_blocked(self):
        payload = _valid_payload()
        payload["evidence"]["focused_test_files"] = []
        payload["evidence"]["focused_test_results"] = {}

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("missing_test_evidence", result["reasons"])

    def test_empty_pr_diff_cannot_be_ready(self):
        payload = _valid_payload()
        payload["pull_request"]["changed_files"] = []
        payload["pull_request"]["present_changed_files"] = []
        payload["evidence"]["behavior_changed_files"] = []
        payload["evidence"]["focused_test_files"] = []
        payload["evidence"]["focused_test_results"] = {}

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("empty_pr_diff", result["reasons"])

    def test_focused_tests_must_pass(self):
        for field, value in (("passed", 0), ("failed", 1), ("errors", 1)):
            with self.subTest(field=field):
                payload = _valid_payload()
                results = payload["evidence"]["focused_test_results"]
                results["tests/unit/test_agent_completion_gate.py"][field] = value

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("focused_tests_failed", result["reasons"])

    def test_focused_test_results_require_exact_declared_paths(self):
        for results in (
            {},
            {
                "tests/unit/test_agent_completion_gate.py": {
                    "passed": 1,
                    "failed": 0,
                    "errors": 0,
                    "skipped": 0,
                    "xfailed": 0,
                    "xpassed": 0,
                },
                "tests/unit/test_extra.py": {
                    "passed": 1,
                    "failed": 0,
                    "errors": 0,
                    "skipped": 0,
                    "xfailed": 0,
                    "xpassed": 0,
                },
            },
        ):
            with self.subTest(results=results):
                payload = _valid_payload()
                payload["evidence"]["focused_test_results"] = results

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("invalid_payload", result["reasons"])
                self.assertIn(
                    "evidence.focused_test_results",
                    result["details"]["invalid_fields"],
                )

    def test_focused_test_path_must_be_present_in_the_pr(self):
        payload = _valid_payload()
        missing_path = "tests/unit/test_not_changed.py"
        payload["evidence"]["focused_test_files"] = [missing_path]
        payload["evidence"]["focused_test_results"] = {
            missing_path: {
                "passed": 1,
                "failed": 0,
                "errors": 0,
                "skipped": 0,
                "xfailed": 0,
                "xpassed": 0,
            }
        }

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertEqual(result["reasons"], ["invalid_payload"])
        self.assertIn(
            "evidence.focused_test_files",
            result["details"]["invalid_fields"],
        )

    def test_focused_test_result_counts_are_nonnegative_integers(self):
        for count in (True, -1, 1.5, "1"):
            with self.subTest(count=count):
                payload = _valid_payload()
                results = payload["evidence"]["focused_test_results"]
                results["tests/unit/test_agent_completion_gate.py"][
                    "passed"
                ] = count

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("invalid_payload", result["reasons"])
                self.assertIn(
                    "evidence.focused_test_results",
                    result["details"]["invalid_fields"],
                )

    def test_unmerged_pr_can_be_ready_but_never_completed(self):
        payload = _valid_payload()

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "ready")
        self.assertNotEqual(result["verdict"], "completed")

    def test_merged_pr_without_post_merge_checks_is_blocked(self):
        payload = _valid_payload()
        payload["pull_request"]["merged"] = True
        payload["pull_request"]["post_merge_checks_passed"] = False

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("post_merge_checks_failed", result["reasons"])

    def test_fully_verified_merged_work_is_completed(self):
        payload = _valid_payload()
        payload["pull_request"]["merged"] = True
        payload["pull_request"]["post_merge_checks_passed"] = True

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "completed")
        self.assertEqual(result["reasons"], [])
        self.assertEqual(
            result["details"]["identity_projection"],
            {
                "issue_number": 813,
                "agent_login": "example-agent[bot]",
                "run_id": "agent-run-123",
            },
        )

    def test_draft_agent_pr_is_blocked(self):
        payload = _valid_payload()
        payload["pull_request"]["draft"] = True

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("draft_pr", result["reasons"])

    def test_invalid_pr_title_is_blocked(self):
        payload = _valid_payload()
        payload["pull_request"]["title_valid"] = False

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("invalid_pr_title", result["reasons"])

    def test_non_agent_pr_is_not_applicable(self):
        payload = _valid_payload()
        payload["policy"]["applicable"] = False

        result = _evaluate(payload)

        self.assertEqual(
            result,
            {"verdict": "not_applicable", "reasons": [], "details": {}},
        )

    def test_malformed_payload_fails_closed(self):
        result = _evaluate([])

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("invalid_payload", result["reasons"])

    def test_applicable_policy_requires_bound_identity(self):
        cases = (
            ("applicable", None, "policy.applicable"),
            ("agent_login", None, "policy.agent_login"),
            ("run_id", None, "policy.run_id"),
            ("head_sha", None, "policy.head_sha"),
            ("agent_login", "   ", "policy.agent_login"),
            ("run_id", 123, "policy.run_id"),
            ("head_sha", "not-a-sha", "policy.head_sha"),
        )
        for field, value, invalid_field in cases:
            with self.subTest(field=field, value=value):
                payload = _valid_payload()
                if value is None:
                    del payload["policy"][field]
                else:
                    payload["policy"][field] = value

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("invalid_payload", result["reasons"])
                self.assertIn(
                    invalid_field,
                    result["details"]["invalid_fields"],
                )

    def test_explicit_false_policy_remains_not_applicable(self):
        result = _evaluate({"policy": {"applicable": False}})

        self.assertEqual(
            result,
            {"verdict": "not_applicable", "reasons": [], "details": {}},
        )

    def test_event_fields_are_strictly_validated(self):
        class UnhashableString(str):
            __hash__ = None

        cases = (
            ("kind", "unknown", "events[0].kind"),
            ("kind", [], "events[0].kind"),
            ("kind", {}, "events[0].kind"),
            ("kind", UnhashableString("completed"), "events[0].kind"),
            ("sequence", "first", "events[0].sequence"),
            ("run_id", 123, "events[0].run_id"),
            ("head_sha", "short", "events[0].head_sha"),
            ("comment_id", "123", "events[0].comment_id"),
        )
        for field, value, invalid_field in cases:
            with self.subTest(field=field):
                payload = _valid_payload()
                payload["events"][0][field] = value

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("invalid_payload", result["reasons"])
                self.assertIn(
                    invalid_field,
                    result["details"]["invalid_fields"],
                )

    def test_event_author_must_match_policy_agent(self):
        cases = (None, "", "attacker[bot]", 123)
        for author in cases:
            with self.subTest(author=author):
                payload = _valid_payload()
                if author is None:
                    del payload["events"][0]["author"]
                else:
                    payload["events"][0]["author"] = author

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("invalid_payload", result["reasons"])
                self.assertIn(
                    "events[0].author",
                    result["details"]["invalid_fields"],
                )

    def test_missing_evidence_sections_are_invalid(self):
        for field in (
            "issue",
            "pull_request",
            "events",
            "reviews",
            "evidence",
            "collection_errors",
        ):
            with self.subTest(field=field):
                payload = _valid_payload()
                del payload[field]

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("invalid_payload", result["reasons"])
                self.assertIn(field, result["details"]["invalid_fields"])

    def test_malformed_nested_fields_return_a_verdict(self):
        payload = _valid_payload()
        payload["events"] = ["not-an-event"]

        try:
            result = _evaluate(payload)
        except (AttributeError, TypeError):
            self.fail("malformed nested evidence raised instead of failing closed")

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("invalid_payload", result["reasons"])

    def test_falsey_malformed_object_sections_fail_closed(self):
        for field in ("policy", "issue", "pull_request", "evidence"):
            with self.subTest(field=field):
                payload = _valid_payload()
                payload[field] = []

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("invalid_payload", result["reasons"])
                self.assertIn(field, result["details"]["invalid_fields"])

    def test_review_flags_must_be_booleans(self):
        for field in ("blocking", "resolved"):
            with self.subTest(field=field):
                payload = _valid_payload()
                payload["reviews"] = [
                    {"blocking": True, "resolved": False, "source": "thread-1"}
                ]
                payload["reviews"][0][field] = "false"

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("invalid_payload", result["reasons"])
                self.assertIn(
                    f"reviews[0].{field}",
                    result["details"]["invalid_fields"],
                )

    def test_review_source_must_be_nonempty_text(self):
        payload = _valid_payload()
        payload["reviews"] = [
            {"blocking": True, "resolved": False, "source": ""}
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("invalid_payload", result["reasons"])
        self.assertIn(
            "reviews[0].source",
            result["details"]["invalid_fields"],
        )

    def test_non_string_path_entries_return_a_verdict(self):
        payload = _valid_payload()
        payload["pull_request"]["changed_files"] = [{}]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("invalid_payload", result["reasons"])
        self.assertIn(
            "pull_request.changed_files",
            result["details"]["invalid_fields"],
        )

        payload = _valid_payload()
        payload["pull_request"]["present_changed_files"] = [{}]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("invalid_payload", result["reasons"])
        self.assertIn(
            "pull_request.present_changed_files",
            result["details"]["invalid_fields"],
        )

    def test_blank_list_entries_fail_closed(self):
        cases = (
            ("issue", "acceptance_criteria"),
            ("issue", "declared_files"),
            ("issue", "allowed_extra_files"),
            ("pull_request", "changed_files"),
            ("pull_request", "present_changed_files"),
            ("evidence", "behavior_changed_files"),
            ("evidence", "focused_test_files"),
        )
        for section, field in cases:
            with self.subTest(section=section, field=field):
                payload = _valid_payload()
                payload[section][field] = ["   "]

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("invalid_payload", result["reasons"])
                self.assertIn(
                    f"{section}.{field}",
                    result["details"]["invalid_fields"],
                )

    def test_unhashable_focused_test_path_fails_closed(self):
        payload = _valid_payload()
        payload["evidence"]["focused_test_files"] = [{}]
        payload["evidence"]["focused_test_results"] = {}

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("invalid_payload", result["reasons"])
        self.assertIn(
            "evidence.focused_test_files",
            result["details"]["invalid_fields"],
        )
        self.assertIn(
            "evidence.focused_test_results",
            result["details"]["invalid_fields"],
        )

    def test_non_boolean_policy_fields_cannot_bypass_rules(self):
        for section, field in (
            ("policy", "applicable"),
            ("issue", "scope_unrestricted"),
            ("pull_request", "draft"),
            ("pull_request", "merged"),
            ("pull_request", "title_valid"),
            ("pull_request", "required_checks_passed"),
            ("pull_request", "post_merge_checks_passed"),
            ("evidence", "copilot_current_head_reviewed"),
            ("evidence", "copilot_rabbit_label"),
        ):
            with self.subTest(section=section, field=field):
                payload = _valid_payload()
                payload[section][field] = "true"

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("invalid_payload", result["reasons"])
                self.assertIn(
                    f"{section}.{field}",
                    result["details"]["invalid_fields"],
                )

    def test_applicable_issue_number_must_be_a_positive_json_integer(self):
        for value in ("813", 0, -1, True, None, [], {}):
            with self.subTest(value=value):
                payload = _valid_payload()
                payload["issue"]["number"] = value

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("invalid_payload", result["reasons"])
                self.assertIn(
                    "issue.number",
                    result["details"]["invalid_fields"],
                )

    def test_evidence_collection_errors_fail_closed(self):
        payload = _valid_payload()
        payload["collection_errors"] = ["invalid_agent_lock_manifest"]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("evidence_collection_failed", result["reasons"])
        self.assertEqual(
            result["details"]["collection_errors"],
            ["invalid_agent_lock_manifest"],
        )

    def test_pr_813_fixture_is_blocked_for_every_expected_reason(self):
        result = _evaluate(_fixture("pr_813.json"))

        self.assertEqual(result["verdict"], "blocked")
        self.assertEqual(
            set(result["reasons"]),
            {
                "blank_issue_description",
                "missing_acceptance_criteria",
                "scope_drift",
                "agent_run_failed",
                "contradictory_terminal_events",
                "unresolved_review",
                "draft_pr",
                "invalid_pr_title",
                "missing_test_evidence",
                "missing_copilot_current_head_review",
                "missing_copilot_rabbit_label",
            },
        )
        self.assertEqual(
            result["details"]["undeclared_files"],
            [
                "apps/web/package.json",
                "package-lock.json",
                "tests/unit/test_cloud_routes.py",
            ],
        )

    def test_cli_prints_json_and_returns_nonzero_for_blocked_input(self):
        module = _gate_module()
        if not hasattr(module, "main"):
            self.fail("completion gate CLI is not implemented")
        payload = _valid_payload()
        payload["issue"]["description"] = ""
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            json.dump(payload, handle)
            handle.flush()
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = module.main([handle.name])

        self.assertEqual(exit_code, 1)
        self.assertEqual(json.loads(output.getvalue())["verdict"], "blocked")

    def test_cli_fails_closed_for_invalid_json(self):
        module = _gate_module()
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            handle.write("{not-json")
            handle.flush()
            output = io.StringIO()
            try:
                with redirect_stdout(output):
                    exit_code = module.main([handle.name])
            except json.JSONDecodeError:
                self.fail("CLI raised instead of returning a fail-closed verdict")

        result = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("invalid_json", result["reasons"])

    def test_cli_fails_closed_when_input_cannot_be_read(self):
        module = _gate_module()
        output = io.StringIO()
        missing = str(Path(tempfile.gettempdir()) / "agent-lock-missing.json")

        try:
            with redirect_stdout(output):
                exit_code = module.main([missing])
        except OSError:
            self.fail("CLI raised instead of returning an input-read verdict")

        result = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("input_read_failed", result["reasons"])

    def test_cli_returns_zero_for_ready_input(self):
        module = _gate_module()
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            json.dump(_valid_payload(), handle)
            handle.flush()
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = module.main([handle.name])

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.getvalue())["verdict"], "ready")


class CompletionGateWorkflowTests(unittest.TestCase):
    def _workflow(self):
        return (
            _repo_root() / ".github" / "workflows" / "pr-checks.yml"
        ).read_text(encoding="utf-8")

    def test_workflow_runs_from_trusted_default_branch(self):
        workflow = self._workflow()

        self.assertIn("pull_request_target:", workflow)
        self.assertIn("workflow_run:", workflow)
        self.assertIn("issue_comment:", workflow)
        self.assertIn("issues:", workflow)
        self.assertIn("schedule:", workflow)
        self.assertNotIn("\n  pull_request_review:", workflow)
        self.assertIn("github.event.repository.default_branch", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotIn("github.event.pull_request.head.sha }}", workflow)

    def test_workflow_cannot_leave_a_stale_green_status(self):
        workflow = self._workflow()
        publish_step = workflow[
            workflow.index("name: Publish stable status and comment"):
            workflow.index("name: Finalize failed gate publication")
        ]
        finalizer_step = workflow[
            workflow.index("name: Finalize failed gate publication"):
            workflow.index("name: Enforce verdict")
        ]

        self.assertIn("id: resolve", workflow)
        self.assertIn("state: 'pending'", workflow)
        self.assertEqual(
            publish_step.count("description: ownedDescription("),
            1,
        )
        self.assertEqual(
            publish_step.count("github.rest.repos.createCommitStatus({"),
            1,
        )
        self.assertIn("'gate-owner:' + process.env.PENDING_STATUS_ID", publish_step)
        self.assertIn("'gate-owner:' + process.env.PENDING_STATUS_ID", finalizer_step)
        self.assertIn(
            "PR_NUMBER: ${{ steps.resolve.outputs.pr_number }}",
            finalizer_step,
        )
        self.assertIn(
            "'agent-completion/truth-gate/pr-' +\n"
            "              process.env.PR_NUMBER",
            finalizer_step,
        )
        self.assertIn("description,", finalizer_step)
        self.assertIn("'pending_status_id'", workflow)
        self.assertIn("String(pendingStatus.data.id)", workflow)
        self.assertIn(
            "PENDING_STATUS_ID: ${{ steps.resolve.outputs.pending_status_id }}",
            workflow,
        )
        self.assertIn("if: always() && steps.resolve.outputs.pr_number != ''", workflow)
        self.assertIn("id: upload", workflow)
        self.assertIn("steps.upload.outcome", workflow)
        self.assertIn("id: publish", workflow)
        self.assertIn("steps.publish.outcome != 'success'", workflow)
        self.assertIn("target === currentRunUrl", workflow)
        self.assertEqual(
            publish_step.count("if (!await currentRunMayPublish(latest))"),
            2,
        )
        self.assertIn("Current run has no proven gate-status lease", publish_step)
        self.assertIn("core.setFailed", publish_step)
        self.assertIn("disposition === 'successor'", finalizer_step)
        self.assertIn("disposition === 'already_failed'", finalizer_step)
        self.assertIn(
            "Overriding success after failed gate publication",
            finalizer_step,
        )
        self.assertNotRegex(
            finalizer_step,
            r"already_failed'\s*\|\|\s*"
            r"disposition === 'already_succeeded",
        )
        self.assertIn("state: 'failure'", finalizer_step)
        self.assertEqual(
            finalizer_step.count("github.rest.repos.createCommitStatus({"),
            1,
        )
        self.assertLess(
            workflow.index("name: Upload gate evidence"),
            workflow.index("name: Publish stable status and comment"),
        )

    def test_resolve_collect_and_publish_commits_must_match(self):
        workflow = self._workflow()
        collect_step = workflow[
            workflow.index("name: Collect repository evidence"):
            workflow.index("name: Evaluate completion evidence")
        ]
        publish_step = workflow[
            workflow.index("name: Publish stable status and comment"):
            workflow.index("name: Finalize failed gate publication")
        ]
        functions = _javascript_functions(
            workflow,
            "function commitEvidenceDisposition(",
        )
        self.assertEqual(len(functions), 1)
        self.assertIn(
            "COLLECTED_HEAD_SHA: ${{ steps.collect.outputs.head_sha }}",
            publish_step,
        )
        self.assertIn(
            "COLLECTED_BASE_SHA: ${{ steps.collect.outputs.base_sha }}",
            publish_step,
        )
        self.assertIn(
            "BASE_SHA: ${{ steps.resolve.outputs.base_sha }}",
            publish_step,
        )
        self.assertIn(
            "RESOLVED_HEAD_SHA: ${{ steps.resolve.outputs.head_sha }}",
            collect_step,
        )
        self.assertIn(
            "RESOLVED_BASE_SHA: ${{ steps.resolve.outputs.base_sha }}",
            collect_step,
        )
        self.assertEqual(
            collect_step.count("github.rest.pulls.get("),
            2,
        )
        self.assertGreaterEqual(
            collect_step.count("collectionErrors.push('stale_head')"),
            2,
        )
        self.assertGreaterEqual(
            collect_step.count("collectionErrors.push('stale_base')"),
            2,
        )
        self.assertIn("compareCommitsWithBasehead", collect_step)
        self.assertIn("basehead: pr.base.sha + '...' + pr.head.sha", collect_step)
        self.assertNotIn("pulls.listFiles", collect_step)

        assertions = r"""
const a = 'a'.repeat(40);
const b = 'b'.repeat(40);
const rows = [
  [a, a, a, 'current_commit'],
  [a.toUpperCase(), a, a, 'current_commit'],
  [a, b, a, 'stale_commit'],
  [a, a, b, 'stale_commit'],
  [a, b, b, 'stale_commit'],
  [a, '', a, 'stale_commit'],
  ['not-a-sha', a, a, 'stale_commit']
];
for (const [resolved, collected, current, expected] of rows) {
  const actual = commitEvidenceDisposition(resolved, collected, current);
  if (actual !== expected) {
    throw new Error(`${resolved}/${collected}/${current}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_workflow_reserves_status_capacity_for_finalization(self):
        workflow = self._workflow()
        resolve = workflow[
            workflow.index("      - name: Resolve pull request"):
            workflow.index("      - name: Check out trusted gate")
        ]

        self.assertIn("listCommitStatusesForRef", resolve)
        self.assertIn(
            "status.context === gateContext",
            resolve,
        )
        self.assertIn("gateStatuses.length >= 998", resolve)
        self.assertIn("status_capacity_exhausted", resolve)
        self.assertLess(
            resolve.index("gateStatuses.length >= 998"),
            resolve.index("createCommitStatus"),
        )

    def test_finalizer_publishes_only_with_proven_lease(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function mayFinalizeFailure(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const rows = [
  ['current_pending', true],
  ['predecessor', true],
  ['already_succeeded', true],
  ['already_failed', false],
  ['successor', false],
  ['fail_closed', false],
  ['', false],
  [null, false]
];
for (const [disposition, expected] of rows) {
  const actual = mayFinalizeFailure(disposition);
  if (actual !== expected) {
    throw new Error(`${disposition}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        finalizer_step = workflow[
            workflow.index("name: Finalize failed gate publication"):
            workflow.index("name: Enforce verdict")
        ]
        self.assertIn("if (!mayFinalizeFailure(disposition))", finalizer_step)
        self.assertIn("No proven lease for failure publication", finalizer_step)

    def test_gate_status_disposition_decision_table(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function gateStatusDisposition(",
        )
        self.assertEqual(len(functions), 2)

        assertions = r"""
const prefix = 'https://github.com/acme/repo/actions/runs/';
const runUrl = prefix + '100';
const rows = [
  [null, '', 'fail_closed'],
  [{id: 100, state: 'pending', target_url: runUrl}, '100', 'current_pending'],
  [{id: 99, state: 'failure', target_url: runUrl}, '100', 'fail_closed'],
  [{id: 101, state: 'failure', target_url: runUrl, description: 'gate-owner:100 blocked'}, '100', 'already_failed'],
  [{id: 101, state: 'success', target_url: runUrl, description: 'gate-owner:100 ready'}, '100', 'already_succeeded'],
  [{id: 101, state: 'pending', target_url: runUrl}, '100', 'fail_closed'],
  [{id: 101, state: 'pending', target_url: prefix + '101'}, '100', 'successor'],
  [{id: 900, state: 'success', target_url: prefix + '500', description: 'gate-owner:101 ready'}, '100', 'successor'],
  [{id: 101, state: 'success', target_url: prefix + '99', description: 'gate-owner:99 ready'}, '100', 'predecessor'],
  [{id: 103, state: 'success', target_url: prefix + '900', description: 'gate-owner:100 stale'}, '102', 'predecessor', prefix + '101'],
  [{id: 103, state: 'success', target_url: prefix + '100'}, '102', 'fail_closed', prefix + '101'],
  [{id: 101, state: 'pending', target_url: 'https://example.test/101'}, '100', 'fail_closed'],
  [{id: 101, state: 'success', target_url: prefix + '101?attempt=2', description: 'gate-owner:101 ready'}, '100', 'fail_closed'],
  [{id: 101, state: 'pending', target_url: prefix + '101'}, '', 'fail_closed']
];
for (const [status, pendingId, expected, currentUrl = runUrl] of rows) {
  const actual = gateStatusDisposition(status, pendingId, currentUrl, prefix);
  if (actual !== expected) {
    throw new Error(`${JSON.stringify(status)}: ${actual} !== ${expected}`);
  }
}
"""
        for function in functions:
            with self.subTest(function=function):
                completed = subprocess.run(
                    ["node", "-e", function + assertions],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_copilot_review_must_be_current_head_and_submitted(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function isCurrentCopilotReview(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const reviewers = new Set(['copilot-pull-request-reviewer[bot]']);
const submittedStates = new Set(['APPROVED', 'COMMENTED', 'CHANGES_REQUESTED']);
const head = 'a'.repeat(40);
const rows = [
  [{user: {login: 'copilot-pull-request-reviewer[bot]'}, state: 'COMMENTED', commit_id: head}, true],
  [{user: {login: 'copilot-pull-request-reviewer[bot]'}, state: 'APPROVED', commit_id: head}, true],
  [{user: {login: 'copilot-pull-request-reviewer[bot]'}, state: 'CHANGES_REQUESTED', commit_id: head}, true],
  [{user: {login: 'copilot-pull-request-reviewer[bot]'}, state: 'DISMISSED', commit_id: head}, false],
  [{user: {login: 'copilot-pull-request-reviewer[bot]'}, state: 'PENDING', commit_id: head}, false],
  [{user: {login: 'copilot-pull-request-reviewer[bot]'}, state: 'COMMENTED', commit_id: 'b'.repeat(40)}, false],
  [{user: {login: 'someone-else[bot]'}, state: 'COMMENTED', commit_id: head}, false],
  [null, false]
];
for (const [review, expected] of rows) {
  const actual = isCurrentCopilotReview(
    review, reviewers, submittedStates, head
  );
  if (actual !== expected) {
    throw new Error(`${JSON.stringify(review)}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_refresh_dispatch_trust_decision_table(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function mayDispatchEvidenceRefresh(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const associations = new Set(['OWNER', 'MEMBER', 'COLLABORATOR']);
const agents = new Set([
  'google-labs-jules[bot]',
  'github-copilot[bot]',
  'openai-codex[bot]',
  'chatgpt-codex-connector[bot]',
  'github-actions[bot]'
]);
const rows = [
  ['OWNER', 'person', true],
  ['MEMBER', 'person', true],
  ['COLLABORATOR', 'person', true],
  ['NONE', 'google-labs-jules[bot]', true],
  ['NONE', 'github-copilot[bot]', true],
  ['NONE', 'openai-codex[bot]', true],
  ['NONE', 'chatgpt-codex-connector[bot]', true],
  ['NONE', 'external-user', false],
  ['NONE', 'github-actions[bot]', true],
  [null, null, false]
];
for (const [association, actor, expected] of rows) {
  const actual = mayDispatchEvidenceRefresh(
    association, actor, associations, agents
  );
  if (actual !== expected) {
    throw new Error(`${association}/${actor}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_comment_refresh_requires_declared_agent_result_evidence(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function issueCommentAffectsEvidence(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const pull = {
  pull_request: {},
  body: '<!-- agent-lock-manifest\n' +
    '{"agent_login":"google-labs-jules[bot]"}\n-->'
};
const issue = {
  body: '## Agent login\n\ngoogle-labs-jules[bot]\n\n## Objective\nTest'
};
const rows = [
  ['declared ready', pull, 'google-labs-jules[bot]',
    'Ready for a review! A PR has been created.', null, true],
  ['declared structured', issue, 'google-labs-jules[bot]',
    '<!-- agent-lock-event {bad-json} -->', null, true],
  ['event edited away', pull, 'google-labs-jules[bot]',
    'ordinary update', 'Jules encountered an unexpected error', true],
  ['declared chatter', pull, 'google-labs-jules[bot]',
    'ordinary update', null, false],
  ['human discussion', pull, 'maintainer',
    'Ready for a review! A PR has been created.', null, false],
  ['unrelated known bot', pull, 'openai-codex[bot]',
    'Ready for a review! A PR has been created.', null, false],
  ['gate comment', pull, 'github-actions[bot]',
    '<!-- agent-completion-truth-gate:v1 -->', null, false],
  ['intent invalidation', issue, 'github-actions[bot]',
    '<!-- agent-lock-intent-invalidated:v1 -->', null, true],
  ['missing contract', {body: ''}, 'google-labs-jules[bot]',
    'Ready for a review! A PR has been created.', null, false]
];
for (const [name, target, actor, body, previousBody, expected] of rows) {
  const actual = issueCommentAffectsEvidence(
    target,
    {user: {login: actor}, body},
    previousBody
  );
  if (actual !== expected) {
    throw new Error(`${name}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        dispatch = workflow[
            workflow.index("  dispatch-evidence-refresh:"):
            workflow.index("  validate:")
        ]
        self.assertIn("issueCommentAffectsEvidence(", dispatch)
        self.assertIn("context.payload.changes", dispatch)

    def test_issue_refresh_uses_sender_permission_decision_table(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function mayDispatchIssueRefresh(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const trustedPermissions = new Set([
  'admin', 'maintain', 'write', 'triage'
]);
const rows = [
  ['maintainer', {permission: 'admin', role_name: 'admin'}, true],
  ['maintainer', {permission: 'write', role_name: 'maintain'}, true],
  ['maintainer', {permission: 'write', role_name: 'write'}, true],
  ['custom-writer', {permission: 'write', role_name: 'release'}, true],
  ['triager', {permission: 'read', role_name: 'triage'}, true],
  ['external-user', {permission: 'read', role_name: 'read'}, false],
  ['custom-reader', {permission: 'read', role_name: 'observe'}, false],
  ['github-actions[bot]', {permission: 'none', role_name: 'none'}, false],
  ['google-labs-jules[bot]', {permission: 'none', role_name: 'none'}, false],
  ['github-copilot[bot]', {permission: 'read', role_name: 'read'}, false],
  ['openai-codex[bot]', {permission: 'write', role_name: 'write'}, true],
  [null, {permission: 'admin', role_name: 'admin'}, false]
];
for (const [actor, response, expected] of rows) {
  const actual = mayDispatchIssueRefresh(
    actor, response.permission, response.role_name, trustedPermissions
  );
  if (actual !== expected) {
    throw new Error(`${actor}/${JSON.stringify(response)}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        dispatch = workflow[
            workflow.index("  dispatch-evidence-refresh:"):
            workflow.index("  validate:")
        ]
        self.assertNotIn("!knownAgentCommenters.has(actor)", dispatch)
        self.assertIn("roleName = result.data.role_name", dispatch)

    def test_every_known_agent_is_treated_as_an_ai_reviewer(self):
        workflow = self._workflow()
        reviewer_set = workflow[
            workflow.index("function aiReviewerLoginSet("):
            workflow.index("function isCurrentCopilotReview(")
        ]

        self.assertNotIn("...knownAgents", reviewer_set)
        self.assertIn("'google-labs-jules[bot]'", reviewer_set)
        self.assertIn("'chatgpt-codex-connector[bot]'", reviewer_set)
        self.assertIn("'vercel[bot]'", reviewer_set)
        self.assertIn("const aiReviewerLogins = aiReviewerLoginSet()", reviewer_set)

        set_functions = _javascript_functions(
            workflow,
            "function aiReviewerLoginSet(",
        )
        self.assertEqual(len(set_functions), 1)
        set_assertions = r"""
const reviewers = aiReviewerLoginSet();
const required = [
  'google-labs-jules',
  'github-copilot',
  'copilot-swe-agent',
  'openai-codex',
  'chatgpt-codex-connector',
  'copilot-pull-request-reviewer',
  'coderabbitai',
  'vercel'
];
for (const login of required) {
  if (!reviewers.has(login)) {
    throw new Error(`missing reviewer alias: ${login}`);
  }
}
if (reviewers.has('human-reviewer')) {
  throw new Error('human reviewer must not be treated as an AI reviewer');
}
"""
        completed = subprocess.run(
            ["node", "-e", set_functions[0] + set_assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        functions = _javascript_functions(
            workflow,
            "function normaliseBotLogin(",
        )
        self.assertEqual(len(functions), 1)
        assertions = r"""
const reviewers = new Set([
  'google-labs-jules[bot]',
  'github-copilot[bot]',
  'copilot-swe-agent[bot]',
  'openai-codex[bot]',
  'chatgpt-codex-connector[bot]',
  'copilot-pull-request-reviewer[bot]',
  'coderabbitai[bot]',
  'vercel[bot]'
].map(normaliseBotLogin));
const rows = [
  ['google-labs-jules', true],
  ['google-labs-jules[bot]', true],
  ['github-copilot', true],
  ['copilot-swe-agent', true],
  ['openai-codex', true],
  ['chatgpt-codex-connector', true],
  ['copilot-pull-request-reviewer', true],
  ['coderabbitai', true],
  ['vercel', true],
  ['human-reviewer', false],
  ['', false],
  [null, false]
];
for (const [login, expected] of rows) {
  const actual = reviewers.has(normaliseBotLogin(login));
  if (actual !== expected) {
    throw new Error(`${login}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        thread_collector = workflow[
            workflow.index("const threads ="):
            workflow.index("function focusedTestResultsFromLog(")
        ]
        self.assertRegex(
            thread_collector,
            r"aiReviewerLogins\.has\(\s*"
            r"normaliseBotLogin\(comment\.author\.login\)\s*\)",
        )

    def test_unrestricted_scope_checkbox_decision_table(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function checkboxChecked(",
        )
        self.assertEqual(len(functions), 2)

        assertions = r"""
const rows = [
  ['- [ ] Yes, this task explicitly permits repository-wide changes.', false],
  ['- [x] Yes, this task explicitly permits repository-wide changes.', true],
  ['- [X] Yes, this task explicitly permits repository-wide changes.', true],
  ['yes', true],
  [' true ', true],
  ['no', false],
  ['_No response_', false],
  ['The word yes in prose is not approval.', false],
  ['', false]
];
for (const [value, expected] of rows) {
  const actual = checkboxChecked(value);
  if (actual !== expected) {
    throw new Error(`${JSON.stringify(value)}: ${actual} !== ${expected}`);
  }
}
"""
        for function in functions:
            with self.subTest(function=function):
                completed = subprocess.run(
                    ["node", "-e", function + assertions],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_snapshot_label_actor_permission_decision_table(self):
        workflow = self._workflow()
        snapshot = workflow[
            workflow.index("  snapshot-agent-task-intent:"):
            workflow.index("  refresh-open-pull-requests:")
        ]
        functions = _javascript_functions(
            workflow,
            "function hasTrustedSnapshotPermission(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const rows = [
  [{permission: 'admin', role_name: 'admin'}, true],
  [{permission: 'write', role_name: 'maintain'}, true],
  [{permission: 'write', role_name: 'write'}, true],
  [{permission: 'write', role_name: 'release'}, true],
  [{permission: 'read', role_name: 'triage'}, true],
  [{permission: 'read', role_name: 'read'}, false],
  [{permission: 'read', role_name: 'observe'}, false],
  [{permission: 'none', role_name: 'none'}, false],
  [{permission: '', role_name: ''}, false],
  [{permission: null, role_name: null}, false]
];
for (const [response, expected] of rows) {
  const actual = hasTrustedSnapshotPermission(
    response.permission, response.role_name
  );
  if (actual !== expected) {
    throw new Error(`${JSON.stringify(response)}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("author_association", snapshot)
        self.assertNotIn(
            "if (context.payload.action === 'labeled')",
            snapshot,
        )
        self.assertIn("username: context.actor", snapshot)
        self.assertIn("roleName = result.data.role_name", snapshot)
        self.assertNotIn("github.event.action == 'opened'", snapshot)
        self.assertIn("github.event.action == 'labeled'", snapshot)
        self.assertIn("github.event.action == 'edited'", snapshot)
        self.assertIn("github.event.action == 'unlabeled'", snapshot)
        self.assertIn("agent-lock-intent-invalidated:v1", snapshot)
        self.assertEqual(snapshot.count("workflow_run_id: workflowRunId"), 2)
        self.assertIn("/^[1-9]\\d*$/.test(workflowRunId)", snapshot)
        self.assertIn("'scopeunrestrictedapproved'", snapshot)
        self.assertIn("'agenttask'", snapshot)
        self.assertIn("'mcpagent'", snapshot)
        self.assertLess(
            snapshot.index("agent-lock-intent-invalidated:v1"),
            snapshot.index("getCollaboratorPermissionLevel"),
        )

    def test_snapshot_event_disposition_decision_table(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function snapshotEventDisposition(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const rows = [
  [false, 'opened', 'agenttask', '', '101', 'ignore'],
  [false, 'labeled', 'agenttask', '', '101', 'snapshot'],
  [false, 'labeled', 'mcpagent', '', '102', 'snapshot'],
  [false, 'labeled', 'priority', '', '103', 'ignore'],
  [true, 'labeled', 'agenttask', '101', '101', 'same_snapshot_run'],
  [true, 'labeled', 'agenttask', '101', '102', 'invalidate'],
  [true, 'edited', '', '101', '103', 'invalidate'],
  [true, 'unlabeled', 'agenttask', '101', '104', 'invalidate'],
  [true, 'opened', 'agenttask', '101', '105', 'ignore']
];
for (const [snapshot, action, label, sourceRun, run, expected] of rows) {
  const actual = snapshotEventDisposition(
    snapshot, action, label, sourceRun, run
  );
  if (actual !== expected) {
    throw new Error(`${JSON.stringify([snapshot, action, label, sourceRun, run])}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_linked_issue_contract_decision_table(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function linkedIssueContract(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const rows = [
  [[870, 870, 870], 'ok'],
  [[0, 870, 870], 'missing'],
  [[870, 0, 870], 'missing'],
  [[870, 870, 0], 'missing'],
  [[870, 871, 870], 'conflicting'],
  [[870, 870, 871], 'conflicting'],
  [['870', 870, 870], 'missing'],
  [[-1, 870, 870], 'missing']
];
for (const [values, expected] of rows) {
  const actual = linkedIssueContract(...values);
  if (actual !== expected) {
    throw new Error(`${JSON.stringify(values)}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_every_github_script_body_compiles(self):
        scripts = _github_script_bodies(self._workflow())
        self.assertEqual(len(scripts), 8)
        compiler = (
            "const AsyncFunction = Object.getPrototypeOf("
            "async function(){}).constructor;"
            "new AsyncFunction('github','context','core','require',"
        )
        for index, script in enumerate(scripts):
            with self.subTest(index=index):
                completed = subprocess.run(
                    ["node", "-e", compiler + json.dumps(script) + ");"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_workflow_pins_every_third_party_action(self):
        workflow = self._workflow()

        self.assertNotRegex(workflow, r"uses:\s+actions/[^@\s]+@v\d+")
        self.assertIn(
            "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0",
            workflow,
        )
        self.assertIn(
            "actions/github-script@3a2844b7e9c422d3c10d287c895573f7108da1b3",
            workflow,
        )
        self.assertIn(
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
            workflow,
        )

    def test_workflow_freezes_issue_intent_before_agent_execution(self):
        workflow = self._workflow()

        self.assertIn("types: [opened, edited, labeled, unlabeled, closed, reopened]", workflow)
        self.assertIn("snapshot-agent-task-intent:", workflow)
        self.assertIn("agent-lock-intent-snapshot:v1", workflow)
        self.assertGreaterEqual(
            workflow.count("agent-lock-intent-invalidated:v1"),
            3,
        )
        self.assertIn("createHash('sha256')", workflow)
        self.assertIn("missing_intent_snapshot", workflow)
        self.assertIn("intent_changed_after_dispatch", workflow)

    def test_snapshot_must_strictly_predate_pull(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function snapshotPredatesPull(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const rows = [
  ['2026-07-18T03:00:00.000Z', '2026-07-18T03:00:01.000Z', true],
  ['2026-07-18T03:00:00.000Z', '2026-07-18T03:00:00.000Z', false],
  ['2026-07-18T03:00:01.000Z', '2026-07-18T03:00:00.000Z', false],
  ['not-a-date', '2026-07-18T03:00:00.000Z', false],
  ['2026-07-18T03:00:00.000Z', null, false]
];
for (const [snapshot, pull, expected] of rows) {
  const actual = snapshotPredatesPull(snapshot, pull);
  if (actual !== expected) {
    throw new Error(`${snapshot}/${pull}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_snapshot_requires_privileged_actor_for_relabel(self):
        workflow = self._workflow()
        header = workflow[
            workflow.index("  snapshot-agent-task-intent:"):
            workflow.index("    concurrency:", workflow.index(
                "  snapshot-agent-task-intent:"
            ))
        ]

        self.assertNotIn("github.event.action == 'opened'", header)
        self.assertIn("github.event.action == 'labeled'", header)
        self.assertNotIn("author_association", header)
        self.assertIn("getCollaboratorPermissionLevel", workflow)
        self.assertIn("context.actor", workflow)

    def test_workflow_publishes_one_machine_readable_gate(self):
        workflow = self._workflow()

        self.assertIn("scripts/ci/agent_completion_gate.py", workflow)
        self.assertIn("agent-completion/truth-gate", workflow)
        self.assertIn("agent-completion-truth-gate:v1", workflow)
        self.assertIn("actions/upload-artifact@", workflow)

    def test_status_context_is_bound_to_the_pull_request(self):
        workflow = self._workflow()

        self.assertIn(
            "return 'agent-completion/truth-gate/pr-' + pullNumber",
            workflow,
        )
        self.assertGreaterEqual(
            workflow.count(
                "'agent-completion/truth-gate/pr-' + prNumber"
            ),
            1,
        )
        self.assertEqual(workflow.count("context: gateContext"), 3)
        self.assertIn("context: pendingRecovery.gateContext", workflow)
        self.assertIn("context: terminalInvalidation.gateContext", workflow)
        self.assertNotRegex(
            workflow,
            r"context:\s*'agent-completion/truth-gate'",
        )

    def test_workflow_uses_required_ci_and_separate_post_merge_evidence(self):
        workflow = self._workflow()

        self.assertIn("run.name === 'CI'", workflow)
        self.assertIn("pr.merge_commit_sha", workflow)
        self.assertNotIn("getCombinedStatusForRef", workflow)

    def test_focused_tests_require_per_path_passing_ci_log(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function focusedTestResultsFromLog(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const log = [
  'PASSED [1%]',
  '2026-07-18T03:00:00Z tests/unit/test_alpha.py::test_one PASSED [33%]',
  '2026-07-18T03:00:01Z tests/unit/test_beta.py::test_two SKIPPED [66%]',
  '\u001b[32mtests/unit/test_beta.py::test_three PASSED\u001b[0m [100%]',
  'tests/unit/test_alpha.py.evil::test_spoof PASSED [100%]',
  'tests/unit/test_gamma.py::test_failure FAILED [100%]',
  'tests/unit/test_only_skipped.py::test_skip SKIPPED [100%]',
  'tests/unit/test_param.py::test_x[PASSED fake] SKIPPED [100%]',
  'tests/unit/test_live.py::test_pass',
  '-------------------------------- live log call ---------------------------------',
  'INFO     example:test_live.py:10 still running',
  '\u001b[32m2026-07-18T03:00:02Z PASSED\u001b[0m [10%]',
  'tests/unit/test_live_failed.py::test_fail',
  '-------------------------------- live log call ---------------------------------',
  'WARNING  example:test_live.py:20 log says PASSED [99%]',
  'FAILED [20%]',
  'tests/unit/test_live_xpass.py::test_expected_failure',
  '-------------------------------- live log call ---------------------------------',
  'XPASS (known bug: now passing) [25%]',
  'tests/unit/test_shadowed.py::test_pending',
  '-------------------------------- live log call ---------------------------------',
  'tests/unit/untracked file.py::test_other',
  '-------------------------------- live log call ---------------------------------',
  'PASSED [30%]',
  'tests/unit/test_boundary.py::test_pending',
  '-------------------------------- live log call ---------------------------------',
  '============================= test session summary =============================',
  'PASSED [40%]',
  'tests/unit/test_param_spoof.py::test_x[value] PASSED [42%]',
  '-------------------------------- live log call ---------------------------------',
  'SKIPPED [50%]',
  '\uFEFF2026-07-18T03:00:03Z tests/unit/test_bom.py::test_pass PASSED [55%]',
  ' tests/unit/test_indented.py::test_spoof',
  '-------------------------------- live log call ---------------------------------',
  'PASSED [60%]',
  'tests/unit/test_blank_tail.py:: PASSED [65%]',
  'tests/unit/test_actions_boundary.py::test_pending',
  '-------------------------------- live log call ---------------------------------',
  '##[group]post-test diagnostics',
  'PASSED [70%]'
].join('\n');
const actual = focusedTestResultsFromLog(log, [
  'tests/unit/test_alpha.py',
  'tests/unit/test_beta.py',
  'tests/unit/test_gamma.py',
  'tests/unit/test_only_skipped.py',
  'tests/unit/test_param.py',
  'tests/unit/test_live.py',
  'tests/unit/test_live_failed.py',
  'tests/unit/test_live_xpass.py',
  'tests/unit/test_shadowed.py',
  'tests/unit/test_boundary.py',
  'tests/unit/test_param_spoof.py',
  'tests/unit/test_bom.py',
  'tests/unit/test_indented.py',
  'tests/unit/test_blank_tail.py',
  'tests/unit/test_actions_boundary.py'
]);
const expected = {
  'tests/unit/test_alpha.py': {passed: 1, failed: 0, errors: 0, skipped: 0, xfailed: 0, xpassed: 0},
  'tests/unit/test_beta.py': {passed: 1, failed: 0, errors: 0, skipped: 1, xfailed: 0, xpassed: 0},
  'tests/unit/test_gamma.py': {passed: 0, failed: 1, errors: 0, skipped: 0, xfailed: 0, xpassed: 0},
  'tests/unit/test_only_skipped.py': {passed: 0, failed: 0, errors: 0, skipped: 1, xfailed: 0, xpassed: 0},
  'tests/unit/test_param.py': {passed: 0, failed: 0, errors: 0, skipped: 1, xfailed: 0, xpassed: 0},
  'tests/unit/test_live.py': {passed: 1, failed: 0, errors: 0, skipped: 0, xfailed: 0, xpassed: 0},
  'tests/unit/test_live_failed.py': {passed: 0, failed: 1, errors: 0, skipped: 0, xfailed: 0, xpassed: 0},
  'tests/unit/test_live_xpass.py': {passed: 0, failed: 0, errors: 0, skipped: 0, xfailed: 0, xpassed: 1},
  'tests/unit/test_shadowed.py': {passed: 0, failed: 0, errors: 0, skipped: 0, xfailed: 0, xpassed: 0},
  'tests/unit/test_boundary.py': {passed: 0, failed: 0, errors: 0, skipped: 0, xfailed: 0, xpassed: 0},
  'tests/unit/test_param_spoof.py': {passed: 0, failed: 0, errors: 0, skipped: 1, xfailed: 0, xpassed: 0},
  'tests/unit/test_bom.py': {passed: 1, failed: 0, errors: 0, skipped: 0, xfailed: 0, xpassed: 0},
  'tests/unit/test_indented.py': {passed: 0, failed: 0, errors: 0, skipped: 0, xfailed: 0, xpassed: 0},
  'tests/unit/test_blank_tail.py': {passed: 0, failed: 0, errors: 0, skipped: 0, xfailed: 0, xpassed: 0},
  'tests/unit/test_actions_boundary.py': {passed: 0, failed: 0, errors: 0, skipped: 0, xfailed: 0, xpassed: 0}
};
if (JSON.stringify(actual) !== JSON.stringify(expected)) {
  throw new Error(`${JSON.stringify(actual)} !== ${JSON.stringify(expected)}`);
}
const crOnly = focusedTestResultsFromLog(
  [
    'tests/unit/test_cr.py::test_pass',
    '-------------------------------- live log call ---------------------------------',
    'PASSED [100%]'
  ].join('\r'),
  ['tests/unit/test_cr.py']
);
if (crOnly['tests/unit/test_cr.py'].passed !== 1) {
  throw new Error(`CR-only parsing failed: ${JSON.stringify(crOnly)}`);
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("listJobsForWorkflowRun", workflow)
        self.assertIn("downloadJobLogsForWorkflowRun", workflow)
        self.assertIn(
            "focused_test_results: focusedTestResults",
            workflow,
        )
        self.assertNotIn(
            "focused_tests_passed: focusedTestFiles.length > 0 && "
            "requiredChecksPassed",
            workflow,
        )

    def test_scheduled_sweep_can_list_pull_requests(self):
        workflow = self._workflow()
        sweep = workflow[
            workflow.index("  refresh-open-pull-requests:"):
            workflow.index("  dispatch-evidence-refresh:")
        ]

        self.assertIn("issues: read", sweep)
        self.assertIn("pull-requests: read", sweep)
        self.assertIn("statuses: write", sweep)
        self.assertIn("github.paginate(", sweep)
        self.assertIn("github.rest.pulls.list", sweep)
        self.assertIn("state: 'open'", sweep)
        self.assertIn("github.rest.repos.listCommitStatusesForRef", sweep)
        self.assertIn("closingIssuesReferences", sweep)
        self.assertIn("github.rest.issues.listComments", sweep)
        self.assertIn("github.rest.pulls.listReviews", sweep)
        self.assertIn("github.rest.actions.listWorkflowRunsForRepo", sweep)
        self.assertIn("github.rest.actions.getWorkflowRun", sweep)
        self.assertIn("run.data.name === 'PR Checks'", sweep)
        self.assertIn(
            "run.data.path === '.github/workflows/pr-checks.yml'",
            sweep,
        )
        self.assertIn("ownerRunId !== terminalRunId", sweep)
        self.assertIn("scheduledRefreshDecision(", sweep)
        self.assertIn("if (decision === 'dispatch')", sweep)
        self.assertIn("group: agent-completion-scheduled-scan", sweep)
        self.assertIn("timeout-minutes: 14", sweep)
        self.assertIn("Skipping stale scheduled decision", sweep)
        self.assertGreaterEqual(
            sweep.count("listCommitStatusesForRef"),
            2,
        )
        self.assertIn("github.rest.actions.createWorkflowDispatch", sweep)
        self.assertIn("workflow_id: 'pr-checks.yml'", sweep)
        self.assertIn("ref: context.payload.repository.default_branch", sweep)
        self.assertIn("inputs: {pull_request: String(pull.number)}", sweep)

        self.assertIn('cron: "*/15 * * * *"', workflow)

    def test_scheduled_sweep_dispatches_only_for_evidence_delta(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function scheduledRefreshDecision(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const base = {
  apiComplete: true,
  statusCount: 2,
  latestState: 'success',
  latestCreatedAt: '2026-07-18T04:30:00Z',
  ownerPendingAt: '2026-07-18T04:20:00Z',
  ownerRunState: 'completed',
  now: '2026-07-18T05:00:00Z',
  pullUpdatedAt: '2026-07-18T04:25:00Z',
  issueUpdatedAt: '2026-07-18T04:15:00Z',
  commentUpdatedAt: '2026-07-18T04:15:00Z',
  ciUpdatedAt: '2026-07-18T04:15:00Z',
  reviewProjectionChanged: false,
  intentProjectionChanged: false,
  policyProjectionChanged: false,
  terminalAlreadyInvalidated: false
};
const rows = [
  ['no status', {...base, latestState: null}, 'dispatch'],
  ['unchanged terminal', base, 'skip'],
  ['status capacity', {...base, statusCount: 998}, 'at_capacity'],
  ['capacity evidence delta', {
    ...base,
    statusCount: 998,
    commentUpdatedAt: '2026-07-18T04:21:00Z'
  }, 'invalidate_terminal'],
  ['last-slot evidence delta', {
    ...base,
    statusCount: 999,
    reviewProjectionChanged: true
  }, 'invalidate_terminal'],
  ['capacity failure evidence delta', {
    ...base,
    statusCount: 998,
    latestState: 'failure',
    commentUpdatedAt: '2026-07-18T04:21:00Z'
  }, 'at_capacity'],
  ['scheduled recovery failure evidence delta', {
    ...base,
    statusCount: 999,
    latestState: 'failure',
    reviewProjectionChanged: true
  }, 'at_capacity'],
  ['settled capacity invalidation', {
    ...base,
    statusCount: 999,
    reviewProjectionChanged: true,
    terminalAlreadyInvalidated: true
  }, 'at_capacity'],
  ['exhausted evidence delta', {
    ...base,
    statusCount: 1000,
    reviewProjectionChanged: true
  }, 'at_capacity'],
  ['API uncertainty', {...base, apiComplete: false}, 'retry'],
  ['malformed terminal lease', {...base, ownerPendingAt: null}, 'dispatch'],
  ['irrelevant PR timestamp', {...base, pullUpdatedAt: '2026-07-18T04:31:00Z'}, 'skip'],
  ['irrelevant issue timestamp', {...base, issueUpdatedAt: '2026-07-18T04:21:00Z'}, 'skip'],
  ['comment delta', {...base, commentUpdatedAt: '2026-07-18T04:21:00Z'}, 'dispatch'],
  ['CI delta', {...base, ciUpdatedAt: '2026-07-18T04:21:00Z'}, 'dispatch'],
  ['review delta', {...base, reviewProjectionChanged: true}, 'dispatch'],
  ['intent delta', {...base, intentProjectionChanged: true}, 'dispatch'],
  ['policy delta', {...base, policyProjectionChanged: true}, 'dispatch'],
  ['fresh pending', {
    ...base,
    latestState: 'pending',
    latestCreatedAt: '2026-07-18T04:30:00Z',
    ownerPendingAt: '2026-07-18T04:30:00Z',
    ownerRunState: 'in_progress',
    pendingLeaseValid: true
  }, 'skip'],
  ['stale pending', {
    ...base,
    latestState: 'pending',
    latestCreatedAt: '2026-07-18T03:59:59Z',
    ownerPendingAt: '2026-07-18T03:59:59Z',
    ownerRunState: 'in_progress',
    pendingLeaseValid: true
  }, 'finalize_pending'],
  ['completed pending', {
    ...base,
    latestState: 'pending',
    ownerPendingAt: '2026-07-18T04:30:00Z',
    ownerRunState: 'completed',
    pendingLeaseValid: true
  }, 'finalize_pending'],
  ['missing pending run', {
    ...base,
    latestState: 'pending',
    ownerPendingAt: '2026-07-18T04:30:00Z',
    ownerRunState: 'missing',
    pendingLeaseValid: true
  }, 'finalize_pending'],
  ['pending 998 recovery', {
    ...base,
    statusCount: 998,
    latestState: 'pending',
    latestCreatedAt: '2026-07-18T04:30:00Z',
    ownerPendingAt: '2026-07-18T04:30:00Z',
    ownerRunState: 'completed',
    pendingLeaseValid: true
  }, 'finalize_pending'],
  ['malformed pending at capacity', {
    ...base,
    statusCount: 998,
    latestState: 'pending',
    latestCreatedAt: '2026-07-18T04:30:00Z',
    ownerPendingAt: '2026-07-18T04:30:00Z',
    ownerRunState: 'missing',
    pendingLeaseValid: false
  }, 'at_capacity']
];
for (const [name, input, expected] of rows) {
  const actual = scheduledRefreshDecision(input);
  if (actual !== expected) {
    throw new Error(`${name}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_scheduled_review_projection_fails_safe_without_churning(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function verdictProjection(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
function comment(verdict) {
  return {
    user: {login: 'github-actions[bot]'},
    body: '<!-- agent-completion-truth-gate:v1 -->' +
      '<pre>' + JSON.stringify(verdict) + '</pre>'
  };
}
const invalid = verdictProjection([comment({
  verdict: 'blocked',
  reasons: ['invalid_payload'],
  details: {}
})]);
if (!invalid || invalid.projectionKnown !== false ||
    invalid.projectionUsable !== false) {
  throw new Error('invalid payload projection must be unknown');
}
const failedCollection = verdictProjection([comment({
  verdict: 'blocked',
  reasons: ['evidence_collection_failed'],
  details: {unresolved_reviews: ['thread-b']}
})]);
if (!failedCollection || failedCollection.projectionKnown !== false ||
    failedCollection.projectionUsable !== false) {
  throw new Error('partial collection projection must be unknown');
}
const recordedCollection = verdictProjection([comment({
  verdict: 'blocked',
  reasons: ['evidence_collection_failed'],
  details: {
    collection_errors: ['conflicting_linked_issue'],
    identity_projection: {
      issue_number: 870,
      agent_login: 'example-agent[bot]',
      run_id: 'run-1'
    }
  }
})]);
if (!recordedCollection || recordedCollection.projectionKnown !== false ||
    recordedCollection.projectionUsable !== true ||
    JSON.stringify(recordedCollection.collectionErrors) !==
      JSON.stringify(['conflicting_linked_issue']) ||
    recordedCollection.identityProjection.issue_number !== 870) {
  throw new Error('recorded collection projection must remain usable');
}
const partialIdentity = verdictProjection([comment({
  verdict: 'blocked',
  reasons: ['evidence_collection_failed'],
  details: {
    collection_errors: ['missing_agent_login'],
    identity_projection: {
      issue_number: 870,
      agent_login: null,
      run_id: 'run-1'
    }
  }
})]);
if (!partialIdentity ||
    JSON.stringify(partialIdentity.identityProjection) !== JSON.stringify({
      issue_number: 870,
      agent_login: null,
      run_id: 'run-1'
    })) {
  throw new Error('partial identity projection must be preserved');
}
const evaluated = verdictProjection([comment({
  verdict: 'blocked',
  reasons: [
    'missing_copilot_current_head_review',
    'unresolved_review',
    'draft_pr',
    'missing_copilot_rabbit_label'
  ],
  details: {
    unresolved_reviews: ['thread-b', 'thread-a'],
    collection_errors: ['agent_login_mismatch'],
    identity_projection: {
      issue_number: 870,
      agent_login: 'example-agent[bot]',
      run_id: 'run-1'
    }
  }
})]);
if (!evaluated || evaluated.projectionKnown !== true ||
    evaluated.projectionUsable !== true ||
    evaluated.copilotCurrentHeadReviewed !== false ||
    JSON.stringify(evaluated.unresolved) !==
      JSON.stringify(['thread-a', 'thread-b']) ||
    JSON.stringify(evaluated.mutablePolicyErrors) !== JSON.stringify([
      'agent_login_mismatch',
      'draft_pr',
      'missing_copilot_rabbit_label'
    ]) || evaluated.identityProjection.run_id !== 'run-1') {
  throw new Error('evaluated projection was not preserved');
}
const exempt = verdictProjection([comment({
  verdict: 'not_applicable',
  reasons: [],
  details: {}
})]);
if (!exempt || exempt.projectionKnown !== true ||
    exempt.projectionUsable !== true ||
    exempt.notApplicable !== true) {
  throw new Error('not-applicable projection must be stable');
}
if (verdictProjection([]) !== null) {
  throw new Error('missing verdict comment must remain unknown');
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        sweep = workflow[
            workflow.index("  refresh-open-pull-requests:"):
            workflow.index("  dispatch-evidence-refresh:")
        ]
        self.assertIn("latest.state === 'success'", sweep)
        self.assertIn("previousProjection.projectionKnown", sweep)

    def test_scheduled_scanner_ignores_ordinary_comments(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function scheduledCommentAffectsEvidence(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const agents = new Set(['google-labs-jules[bot]']);
const rows = [
  ['structured', 'google-labs-jules[bot]',
    '<!-- agent-lock-event {bad-json} -->', true],
  ['ready', 'google-labs-jules[bot]',
    'Ready for a review! A PR has been created.', true],
  ['error', 'google-labs-jules[bot]',
    "Jules wasn't able to complete the task", true],
  ['ordinary agent chatter', 'google-labs-jules[bot]',
    'Here is a progress update.', false],
  ['maintainer discussion', 'maintainer',
    'Ready for a review! A PR has been created.', false],
  ['gate publication', 'github-actions[bot]',
    '<!-- agent-completion-truth-gate:v1 -->', false]
];
for (const [name, actor, body, expected] of rows) {
  const actual = scheduledCommentAffectsEvidence(
    {user: {login: actor}, body},
    agents
  );
  if (actual !== expected) {
    throw new Error(`${name}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        sweep = workflow[
            workflow.index("  refresh-open-pull-requests:"):
            workflow.index("  dispatch-evidence-refresh:")
        ]
        self.assertIn("const evidenceComments =", sweep)
        self.assertNotIn("externalPullComments", sweep)

    def test_scheduled_scanner_detects_frozen_intent_changes(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function intentContractErrors(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const crypto = require('crypto');
const body = '## Objective\n\nKeep immutable intent.';
const digest = crypto.createHash('sha256')
  .update(body, 'utf8').digest('hex');
const issue = {
  number: 870,
  body,
  labels: {nodes: [{name: 'agent-task'}]}
};
function snapshot(overrides = {}) {
  const value = {
    issue_number: 870,
    body_sha256: digest,
    scope_unrestricted_approved: false,
    ...overrides
  };
  return {
    user: {login: 'github-actions[bot]'},
    created_at: '2026-07-18T03:00:00Z',
    body: '<!-- agent-lock-intent-snapshot:v1\n' +
      JSON.stringify(value) + '\n-->'
  };
}
function invalidation() {
  return {
    user: {login: 'github-actions[bot]'},
    created_at: '2026-07-18T03:00:02Z',
    body: '<!-- agent-lock-intent-invalidated:v1\n' +
      JSON.stringify({
        issue_number: 870,
        event_action: 'edited',
        actor: 'issue-author'
      }) + '\n-->'
  };
}
const rows = [
  ['valid', issue, [snapshot()], []],
  ['missing', issue, [], ['missing_intent_snapshot']],
  ['changed body', {...issue, body: body + ' changed'}, [snapshot()],
    ['intent_changed_after_dispatch']],
  ['restored body after edit', issue, [snapshot(), invalidation()],
    ['intent_changed_after_dispatch']],
  ['approval changed', {
    ...issue,
    labels: {nodes: [
      {name: 'agent-task'},
      {name: 'scope-unrestricted-approved'}
    ]}
  }, [snapshot()], ['unrestricted_approval_changed_after_dispatch']],
  ['label and snapshot missing', {
    ...issue,
    labels: {nodes: []}
  }, [], ['linked_issue_not_agent_task', 'missing_intent_snapshot']],
  ['bad issue number', issue, [snapshot({issue_number: 999})],
    ['invalid_intent_snapshot']]
];
for (const [name, candidate, comments, expected] of rows) {
  const actual = intentContractErrors(
    candidate,
    comments,
    '2026-07-18T03:00:01Z'
  );
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(`${name}: ${JSON.stringify(actual)} !== ` +
      JSON.stringify(expected));
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        sweep = workflow[
            workflow.index("  refresh-open-pull-requests:"):
            workflow.index("  dispatch-evidence-refresh:")
        ]
        self.assertIn("intentProjectionChanged", sweep)
        self.assertIn("previousProjection.collectionErrors", sweep)

        projection_functions = _javascript_functions(
            workflow,
            "function scheduledIntentProjectionChanged(",
        )
        self.assertEqual(len(projection_functions), 1)
        projection_assertions = r"""
const rows = [
  ['N/A remains N/A', {notApplicable: true, collectionErrors: []},
    ['missing_closing_issue_reference'], 0, false, false],
  ['N/A becomes applicable', {notApplicable: true, collectionErrors: []},
    [], 1, true, true],
  ['applicable becomes N/A', {notApplicable: false, collectionErrors: []},
    [], 1, false, true],
  ['new missing link', {notApplicable: false, collectionErrors: []},
    ['missing_closing_issue_reference'], 0, true, true],
  ['settled missing link', {
    notApplicable: false,
    collectionErrors: ['missing_closing_issue_reference']
  }, ['missing_closing_issue_reference'], 0, true, false],
  ['settled multiple links', {
    notApplicable: false,
    collectionErrors: [
      'missing_closing_issue_reference',
      'multiple_closing_issues',
      'missing_intent_snapshot'
    ]
  }, [
    'missing_closing_issue_reference',
    'multiple_closing_issues'
  ], 2, true, false],
  ['link repaired', {
    notApplicable: false,
    collectionErrors: ['missing_closing_issue_reference']
  }, [], 1, true, true],
  ['body changed', {notApplicable: false, collectionErrors: []},
    ['intent_changed_after_dispatch'], 1, true, true],
  ['body failure settled', {
    notApplicable: false,
    collectionErrors: ['intent_changed_after_dispatch']
  }, ['intent_changed_after_dispatch'], 1, true, false],
  ['new conflicting contract', {
    notApplicable: false,
    collectionErrors: []
  }, ['conflicting_linked_issue'], 1, true, true],
  ['settled conflicting contract', {
    notApplicable: false,
    collectionErrors: ['conflicting_linked_issue']
  }, ['conflicting_linked_issue'], 1, true, false],
  ['contract repaired', {
    notApplicable: false,
    collectionErrors: ['incomplete_linked_issue_contract']
  }, [], 1, true, true],
  ['settled unavailable conflicting target', {
    notApplicable: false,
    collectionErrors: [
      'conflicting_linked_issue',
      'linked_issue_unavailable',
      'missing_linked_issue'
    ]
  }, [
    'conflicting_linked_issue',
    'linked_issue_unavailable',
    'missing_linked_issue'
  ], 1, true, false],
  ['hard unknown failure stays settled', {
    notApplicable: false,
    projectionUsable: false,
    collectionErrors: []
  }, ['conflicting_linked_issue'], 1, true, false]
];
for (const [name, previous, current, count, applicable, expected] of rows) {
  const actual = scheduledIntentProjectionChanged(
    previous, current, count, applicable
  );
  if (actual !== expected) {
    throw new Error(`${name}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            [
                "node",
                "-e",
                projection_functions[0] + projection_assertions,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        sweep = workflow[
            workflow.index("  refresh-open-pull-requests:"):
            workflow.index("  dispatch-evidence-refresh:")
        ]
        self.assertIn("const applicableWithoutSelectedIssue =", sweep)
        self.assertIn("linkProjection.errors.length > 0", sweep)
        self.assertIn("if (error.status !== 404", sweep)
        self.assertIn("selectedIssueUnavailable = true", sweep)
        self.assertIn("['linked_issue_unavailable']", sweep)
        self.assertNotIn("selectedIssue || linkedIssues[0]", sweep)
        self.assertLess(
            sweep.index("const linkProjection = scheduledLinkProjection("),
            sweep.index("await github.rest.issues.get("),
        )

        applicable_functions = _javascript_functions(
            workflow,
            "function agentTaskApplicable(",
        )
        self.assertEqual(len(applicable_functions), 2)
        self.assertEqual(applicable_functions[0], applicable_functions[1])
        applicable_assertions = r"""
const issue = (number, labels) => ({
  number,
  labels: {nodes: labels.map(name => ({name}))}
});
const base = {
  user: {login: 'maintainer'},
  head: {ref: 'feature/ordinary'},
  labels: [],
  body: ''
};
const rows = [
  ['human', base, null, false],
  ['PR label', {...base, labels: [{name: 'agent-task'}]}, null, true],
  ['issue label', base, issue(1, ['mcp/agent']), true],
  ['branch', {...base, head: {ref: 'codex/fix'}}, null, true],
  ['manifest', {...base, body: '<!-- agent-lock-manifest {bad} -->'}, null, true],
  ['known agent', {...base, user: {login: 'google-labs-jules[bot]'}}, null, true],
  ['dependabot excluded', {
    ...base,
    user: {login: 'dependabot[bot]'},
    labels: [{name: 'agent-task'}]
  }, issue(1, ['agent-task']), false]
];
for (const [name, pull, selected, expected] of rows) {
  const actual = agentTaskApplicable(pull, selected);
  if (actual !== expected) {
    throw new Error(`${name}: ${actual} !== ${expected}`);
  }
}
"""
        for function in applicable_functions:
            completed = subprocess.run(
                ["node", "-e", function + applicable_assertions],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

        selection_functions = _javascript_functions(
            workflow,
            "function scheduledLinkProjection(",
        )
        self.assertEqual(len(selection_functions), 1)
        selection_assertions = r"""
const issue = number => ({number});
const rows = [
  ['valid contract', {
    body: '<!-- agent-lock-manifest {"issue_number":7} -->\nFixes #7'
  }, [issue(7)], 7, []],
  ['multi authoritative uses textual first', {
    body: 'Fixes #7\nFixes #8'
  }, [issue(7), issue(8)], 7, [
    'incomplete_linked_issue_contract',
    'missing_closing_issue_reference',
    'multiple_closing_issues'
  ]],
  ['textual non-authoritative fallback', {
    body: 'Fixes #9'
  }, [], 9, [
    'incomplete_linked_issue_contract',
    'missing_closing_issue_reference'
  ]],
  ['manifest wins', {
    body: '<!-- agent-lock-manifest {"issue_number":10} -->\nFixes #9'
  }, [issue(9)], 10, ['conflicting_linked_issue']],
  ['invalid manifest falls back', {
    body: '<!-- agent-lock-manifest {bad} -->\nFixes #11'
  }, [], 11, [
    'incomplete_linked_issue_contract',
    'invalid_agent_lock_manifest',
    'missing_closing_issue_reference'
  ]],
  ['no issue', {body: ''}, [], 0, [
    'incomplete_linked_issue_contract',
    'missing_closing_issue_reference'
  ]]
];
for (const [name, pull, issues, expectedNumber, expectedErrors] of rows) {
  const actual = scheduledLinkProjection(pull, issues);
  if (actual.selectedIssueNumber !== expectedNumber ||
      JSON.stringify(actual.errors) !== JSON.stringify(expectedErrors)) {
    throw new Error(`${name}: ${JSON.stringify(actual)}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", selection_functions[0] + selection_assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        combined_assertions = r"""
const first = {number: 1, labels: {nodes: []}};
const second = {number: 2, labels: {nodes: [{name: 'agent-task'}]}};
const multi = {
  user: {login: 'maintainer'},
  head: {ref: 'feature/ordinary'},
  labels: [],
  body: 'Fixes #1\nFixes #2'
};
const selected = scheduledLinkProjection(multi, [first, second]);
if (selected.selectedIssueNumber !== 1 ||
    agentTaskApplicable(multi, first) !== false) {
  throw new Error('multi-link applicability must use selected issue only');
}
const textual = {...multi, body: 'Fixes #2'};
if (scheduledLinkProjection(textual, []).selectedIssueNumber !== 2 ||
    agentTaskApplicable(textual, second) !== true) {
  throw new Error('textual fallback issue label must affect applicability');
}
"""
        completed = subprocess.run(
            [
                "node",
                "-e",
                selection_functions[0] + applicable_functions[0] +
                combined_assertions,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        policy_functions = _javascript_functions(
            workflow,
            "function scheduledMutablePolicyErrors(",
        )
        self.assertEqual(len(policy_functions), 1)
        policy_assertions = r"""
const issue = {
  body: '## Agent login\nexample-agent[bot]\n' +
    '## Agent run id\nrun-1'
};
const manifest = '<!-- agent-lock-manifest ' + JSON.stringify({
  issue_number: 870,
  agent_login: 'example-agent[bot]',
  run_id: 'run-1'
}) + ' -->';
const base = {
  title: 'ci: enforce agent truth gate',
  draft: false,
  labels: [{name: 'copilot-rabbit'}],
  body: manifest + '\nFixes #870'
};
const rows = [
  ['valid', base, issue, true, []],
  ['draft', {...base, draft: true}, issue, true, ['draft_pr']],
  ['invalid title', {...base, title: 'bad'}, issue, true,
    ['invalid_pr_title']],
  ['label removed', {...base, labels: []}, issue, true,
    ['missing_copilot_rabbit_label']],
  ['invalid manifest', {
    ...base,
    body: '<!-- agent-lock-manifest {bad} -->\nFixes #870'
  }, issue, true, [
    'agent_login_mismatch',
    'agent_run_id_mismatch',
    'invalid_agent_lock_manifest'
  ]],
  ['run mismatch', {
    ...base,
    body: '<!-- agent-lock-manifest ' + JSON.stringify({
      issue_number: 870,
      agent_login: 'example-agent[bot]',
      run_id: 'other-run'
    }) + ' -->\nFixes #870'
  }, issue, true, ['agent_run_id_mismatch']],
  ['login mismatch', {
    ...base,
    body: '<!-- agent-lock-manifest ' + JSON.stringify({
      issue_number: 870,
      agent_login: 'other-agent[bot]',
      run_id: 'run-1'
    }) + ' -->\nFixes #870'
  }, issue, true, ['agent_login_mismatch']],
  ['missing headings', base, {body: ''}, true, [
    'missing_agent_login',
    'missing_agent_run_id'
  ]],
  ['not applicable', {...base, draft: true, labels: []}, issue, false, []]
];
for (const [name, pull, selected, applicable, expected] of rows) {
  const actual = scheduledMutablePolicyErrors(
    pull, selected, applicable
  );
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(`${name}: ${JSON.stringify(actual)} !== ` +
      JSON.stringify(expected));
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", policy_functions[0] + policy_assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        policy_projection_functions = _javascript_functions(
            workflow,
            "function scheduledMutablePolicyProjectionChanged(",
        )
        self.assertEqual(len(policy_projection_functions), 1)
        policy_projection_assertions = r"""
const ready = {notApplicable: false, mutablePolicyErrors: []};
const blocked = {
  notApplicable: false,
  mutablePolicyErrors: ['missing_copilot_rabbit_label']
};
const rows = [
  ['success to violation', ready,
    ['missing_copilot_rabbit_label'], true, true],
  ['settled violation', blocked,
    ['missing_copilot_rabbit_label'], true, false],
  ['violation repaired', blocked, [], true, true],
  ['not applicable', {notApplicable: true, mutablePolicyErrors: []},
    ['draft_pr'], true, false],
  ['currently exempt', ready, ['draft_pr'], false, false],
  ['hard unknown failure', {
    notApplicable: false,
    projectionUsable: false,
    mutablePolicyErrors: []
  }, ['missing_copilot_rabbit_label'], true, false]
];
for (const [name, previous, current, applicable, expected] of rows) {
  const actual = scheduledMutablePolicyProjectionChanged(
    previous, current, applicable
  );
  if (actual !== expected) {
    throw new Error(`${name}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            [
                "node",
                "-e",
                policy_projection_functions[0] +
                policy_projection_assertions,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        identity_functions = _javascript_functions(
            workflow,
            "function scheduledContractIdentity(",
        )
        identity_projection_functions = _javascript_functions(
            workflow,
            "function scheduledIdentityProjectionChanged(",
        )
        self.assertEqual(len(identity_functions), 1)
        self.assertEqual(len(identity_projection_functions), 1)
        identity_assertions = r"""
const issueA = {
  body: '## Agent login\nexample-agent[bot]\n' +
    '## Agent run id\nrun-a'
};
const issueB = {
  body: '## Agent login\nexample-agent[bot]\n' +
    '## Agent run id\nrun-b'
};
const identityA = scheduledContractIdentity(870, issueA, true);
const identityB = scheduledContractIdentity(871, issueB, true);
const allNull = scheduledContractIdentity(0, null, true);
const missingLogin = scheduledContractIdentity(870, {
  body: '## Agent run id\nrun-a'
}, true);
const missingRun = scheduledContractIdentity(870, {
  body: '## Agent login\nexample-agent[bot]'
}, true);
if (JSON.stringify(identityA) !== JSON.stringify({
  issue_number: 870,
  agent_login: 'example-agent[bot]',
  run_id: 'run-a'
}) || scheduledContractIdentity(870, issueA, false) !== null) {
  throw new Error('contract identity extraction failed');
}
const previous = {
  notApplicable: false,
  projectionUsable: true,
  identityProjection: identityA
};
const rows = [
  ['unchanged', previous, identityA, true, false],
  ['issue and run switched', previous, identityB, true, true],
  ['missing baseline', {...previous, identityProjection: null},
    identityA, true, true],
  ['settled all-null identity', {...previous, identityProjection: allNull},
    allNull, true, false],
  ['settled missing login', {...previous, identityProjection: missingLogin},
    missingLogin, true, false],
  ['settled missing run', {...previous, identityProjection: missingRun},
    missingRun, true, false],
  ['partial identity repaired', {...previous, identityProjection: missingRun},
    identityA, true, true],
  ['hard unknown', {...previous, projectionUsable: false},
    identityB, true, false],
  ['not applicable', {...previous, notApplicable: true},
    identityB, true, false],
  ['currently exempt', previous, null, false, false]
];
for (const [name, prior, current, applicable, expected] of rows) {
  const actual = scheduledIdentityProjectionChanged(
    prior, current, applicable
  );
  if (actual !== expected) {
    throw new Error(`${name}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            [
                "node",
                "-e",
                identity_functions[0] + identity_projection_functions[0] +
                identity_assertions,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_validation_replaces_obsolete_failure_comment(self):
        workflow = self._workflow()
        validate = workflow[
            workflow.index("  validate:"):
            workflow.index("  truth-gate:")
        ]

        self.assertIn("✅ Current validation passed.", validate)
        self.assertIn("comment.user.login === 'github-actions[bot]'", validate)
        self.assertLess(
            validate.index("const marker = '<!-- pr-validation:v1 -->'"),
            validate.index("if (findings.length === 0)"),
        )
        self.assertIn("issues.updateComment", validate)

    def test_validation_comment_failure_is_non_fatal(self):
        """A rejected comment API must warn, not fail; ❌ findings still fail."""

        workflow = self._workflow()
        validate = workflow[
            workflow.index("  validate:"):
            workflow.index("  truth-gate:")
        ]
        script = _github_script_bodies(validate)[0]

        harness = (
            """
const calls = { warnings: [], failures: [] };
const core = {
  warning(message) { calls.warnings.push(String(message)); },
  setFailed(message) { calls.failures.push(String(message)); },
};
function rejectingComment() {
  const error = new Error('Resource not accessible by integration');
  error.status = 403;
  return Promise.reject(error);
}
async function runValidate(pr) {
  calls.warnings.length = 0;
  calls.failures.length = 0;
  const context = {
    repo: { owner: 'o', repo: 'r' },
    payload: { pull_request: pr },
  };
  const github = {
    paginate: async () => [],
    rest: { issues: {
      listComments: () => {},
      createComment: rejectingComment,
      updateComment: rejectingComment,
    } },
  };
  await (async () => {
"""
            + script
            + """
  })();
  return { warnings: calls.warnings.slice(), failures: calls.failures.slice() };
}
(async () => {
  // Warning-only findings + a rejecting comment API must NOT fail the job,
  // and the rejection must surface as a warning.
  const warnOnly = await runValidate({
    title: 'update the widget rendering path',
    body: 'This description is comfortably longer than twenty characters.',
    additions: 12,
    deletions: 4,
  });
  if (warnOnly.failures.length !== 0) {
    throw new Error(
      'warning-only validation must not fail when the comment API rejects: '
      + JSON.stringify(warnOnly));
  }
  if (warnOnly.warnings.length === 0) {
    throw new Error('a rejected comment API must emit a warning');
  }
  // An error (❌) finding must still call setFailed, comment rejection notwithstanding.
  const errorFinding = await runValidate({
    title: 'short',
    body: 'This description is comfortably longer than twenty characters.',
    additions: 12,
    deletions: 4,
  });
  if (errorFinding.failures.length === 0) {
    throw new Error(
      'an error finding must still call setFailed even when the comment API rejects: '
      + JSON.stringify(errorFinding));
  }
})().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exit(1);
});
"""
        )

        completed = subprocess.run(
            ["node", "-e", harness],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_commented_review_does_not_clear_changes_requested(self):
        workflow = self._workflow()

        self.assertIn(
            "['APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'].includes(",
            workflow,
        )
        self.assertIn("reviewDecision", workflow)

    def test_workflow_requires_copilot_review_label_and_committed_tests(self):
        workflow = self._workflow()

        self.assertIn("copilot-pull-request-reviewer[bot]", workflow)
        self.assertIn("function isCurrentCopilotReview(", workflow)
        self.assertIn("copilot-rabbit", workflow)
        self.assertNotIn("!thread.isOutdated", workflow)
        self.assertIn(
            "copilot_current_head_reviewed: copilotCurrentHeadReviewed",
            workflow,
        )
        self.assertIn("copilot_rabbit_label: copilotRabbitLabel", workflow)
        self.assertIn("expectedTests.every", workflow)
        self.assertIn("presentChangedFiles.has(path)", workflow)

    def test_adapter_fails_closed_on_pagination_and_binds_trusted_ci(self):
        workflow = self._workflow()

        self.assertIn("changed_files_truncated", workflow)
        self.assertIn("run.path === '.github/workflows/ci.yml'", workflow)
        self.assertIn("run.event === expectedEvent", workflow)
        self.assertIn("pull.number === prNumber", workflow)
        self.assertIn("trusted_ci_workflow_changed", workflow)
        self.assertIn("file.previous_filename", workflow)
        self.assertIn("file.status !== 'removed'", workflow)
        self.assertIn(
            "present_changed_files: [...presentChangedFiles]",
            workflow,
        )

    def test_gate_runs_are_serialized_and_coalesced_by_pr_number(self):
        workflow = self._workflow()
        dispatch = workflow[
            workflow.index("  dispatch-evidence-refresh:"):
            workflow.index("  validate:")
        ]
        truth_gate_header = workflow[
            workflow.index("  truth-gate:"):
            workflow.index("    steps:", workflow.index("  truth-gate:"))
        ]

        self.assertIn("dispatch-evidence-refresh:", workflow)
        self.assertIn("group: agent-completion-${{", workflow)
        self.assertIn("inputs.pull_request || github.event.pull_request.number", workflow)
        self.assertIn("cancel-in-progress: false", truth_gate_header)
        self.assertNotIn("cancel-in-progress: true", truth_gate_header)
        self.assertIn("timeout-minutes: 20", truth_gate_header)
        self.assertIn("trustedCommentAssociations", workflow)
        self.assertIn("comment.author_association", workflow)
        self.assertIn("google-labs-jules[bot]", workflow)
        self.assertIn("getCollaboratorPermissionLevel", dispatch)
        self.assertIn("context.payload.sender", dispatch)
        self.assertNotIn("issue.author_association", dispatch)
        self.assertIn("!cancelled()", truth_gate_header)
        self.assertNotIn("always()", truth_gate_header)

    def test_collector_binds_structured_agent_event_to_head(self):
        workflow = self._workflow()

        self.assertIn("agent-lock-event", workflow)
        self.assertIn("head_sha: pr.head.sha", workflow)
        self.assertIn("structuredEvent.head_sha", workflow)
        self.assertIn("ready for (?:a )?review", workflow)
        self.assertIn("\\[PR\\]", workflow)

    def test_legacy_run_id_requires_an_unambiguous_delimiter(self):
        workflow = self._workflow()
        functions = _javascript_functions(
            workflow,
            "function legacyRunId(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const rows = [
  ['Run failed', null],
  ['failed to complete task because the worker stopped', null],
  ['run id: provider-123', 'provider-123'],
  ['run_id=provider.456', 'provider.456'],
  ['task-id/abc:789', 'abc:789'],
  ['https://jules.google.com/task/1892762060881911102',
    '1892762060881911102'],
  ['https://example.test/tasks/task-42.', 'task-42'],
  ['Run: failed', null],
  ['Task: failed', null],
  ['runner:wrong', null],
  ['', null]
];
for (const [body, expected] of rows) {
  const actual = legacyRunId(body);
  if (actual !== expected) {
    throw new Error(`${body}: ${actual} !== ${expected}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-e", functions[0] + assertions],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_collector_uses_authoritative_closing_issue_references(self):
        workflow = self._workflow()

        self.assertIn("closingIssuesReferences", workflow)
        self.assertIn("incomplete_linked_issue_contract", workflow)
        self.assertIn("multiple_closing_issues", workflow)

    def test_snapshot_validates_contract_and_freezes_approval_state(self):
        workflow = self._workflow()

        self.assertIn("pre-dispatch confirmation", workflow.lower())
        self.assertIn("incomplete_agent_task_contract", workflow)
        self.assertIn("scope_unrestricted_approved", workflow)
        self.assertIn("intent_snapshot_after_dispatch", workflow)
        self.assertIn("function hasResponse(value)", workflow)
        self.assertIn("response !== '_No response_'", workflow)
        self.assertIn(
            "Boolean(hasResponse(declaredScope) || unrestrictedRequested)",
            workflow,
        )

    def test_adapter_recognizes_agent_labels_scripts_and_blocking_threads(self):
        workflow = self._workflow()

        self.assertIn("'agenttask'", workflow)
        self.assertIn("explicitlyNonBehavioral", workflow)
        self.assertIn("!explicitlyNonBehavioral", workflow)
        self.assertIn("VADE-RECOMMENDATION", workflow)

    def test_workflow_does_not_approve_or_merge(self):
        workflow = self._workflow()

        self.assertNotIn("createReview", workflow)
        self.assertNotIn("pulls.merge", workflow)
        self.assertNotIn("mergePullRequest", workflow)
        self.assertNotIn("event: 'APPROVE'", workflow)


class CompletionGateDocumentationTests(unittest.TestCase):
    def test_agent_task_template_requires_pre_dispatch_evidence(self):
        template = (
            _repo_root() / ".github" / "ISSUE_TEMPLATE" / "agent-task.yml"
        ).read_text(encoding="utf-8")

        for field in (
            "Objective",
            "Acceptance criteria",
            "Declared file scope",
            "Focused test paths",
        ):
            self.assertIn(field, template)
        declared_scope = template[
            template.index("    id: declared_scope"):
            template.index("    id: allowed_extra")
        ]
        self.assertIn("validations:", declared_scope)
        self.assertIn("required: true", declared_scope)
        self.assertNotIn("id: unrestricted", template)
        self.assertNotIn("scope-unrestricted-approved", template)

    def test_pr_template_uses_an_inert_example_marker(self):
        template = (
            _repo_root() / ".github" / "pull_request_template.md"
        ).read_text(encoding="utf-8")

        self.assertIn("agent-lock-example", template)
        self.assertNotIn("<!-- agent-lock-manifest", template)

    def test_operator_doc_defines_schemas_and_enforcement(self):
        documentation = (
            _repo_root() / "docs" / "agent-completion-truth-gate.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Input schema", documentation)
        self.assertIn("Verdict schema", documentation)
        self.assertIn("Fail-closed", documentation)
        self.assertIn("agent-completion/truth-gate", documentation)
        self.assertIn("branch protection", documentation.lower())
        self.assertIn(
            "previous successful status can remain visible",
            documentation,
        )
        self.assertIn(
            "independently head-bound required workflow",
            documentation,
        )
        self.assertIn("Snapshot creation is label-event-only", documentation)
        self.assertIn(
            "does not recursively trigger `issue_comment`",
            documentation,
        )
        self.assertIn(
            "Resolve-time, collection-time, and publication-time PR base and head",
            documentation,
        )
        self.assertIn("immutable resolved base/head commit comparison", documentation)


if __name__ == "__main__":
    unittest.main()
