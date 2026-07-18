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
            "focused_tests_passed": True,
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
        payload["evidence"]["behavior_changed_files"] = []

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("missing_declared_files", result["reasons"])
        self.assertEqual(
            result["details"]["missing_declared_files"],
            ["src/youtube_extension/agent_lock/completion_gate.py"],
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

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("missing_test_evidence", result["reasons"])

    def test_empty_pr_diff_cannot_be_ready(self):
        payload = _valid_payload()
        payload["pull_request"]["changed_files"] = []
        payload["evidence"]["behavior_changed_files"] = []
        payload["evidence"]["focused_test_files"] = []
        payload["evidence"]["focused_tests_passed"] = False

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("empty_pr_diff", result["reasons"])

    def test_focused_tests_must_pass(self):
        payload = _valid_payload()
        payload["evidence"]["focused_tests_passed"] = False

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("focused_tests_failed", result["reasons"])

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

        self.assertEqual(result, {"verdict": "completed", "reasons": [], "details": {}})

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
        cases = (
            ("kind", "unknown", "events[0].kind"),
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

    def test_blank_list_entries_fail_closed(self):
        cases = (
            ("issue", "acceptance_criteria"),
            ("issue", "declared_files"),
            ("issue", "allowed_extra_files"),
            ("pull_request", "changed_files"),
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

    def test_non_boolean_policy_fields_cannot_bypass_rules(self):
        for section, field in (
            ("policy", "applicable"),
            ("issue", "scope_unrestricted"),
            ("pull_request", "draft"),
            ("pull_request", "merged"),
            ("pull_request", "title_valid"),
            ("pull_request", "required_checks_passed"),
            ("pull_request", "post_merge_checks_passed"),
            ("evidence", "focused_tests_passed"),
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
            2,
        )
        self.assertIn("'gate-owner:' + process.env.PENDING_STATUS_ID", publish_step)
        self.assertIn("'gate-owner:' + process.env.PENDING_STATUS_ID", finalizer_step)
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
        self.assertIn("gate pending status missing", publish_step)
        self.assertIn("core.setFailed", publish_step)
        self.assertIn("disposition === 'successor'", finalizer_step)
        self.assertIn("disposition === 'already_failed'", finalizer_step)
        self.assertIn("state: 'failure'", finalizer_step)
        self.assertLess(
            workflow.index("name: Upload gate evidence"),
            workflow.index("name: Publish stable status and comment"),
        )

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
  'openai-codex[bot]'
]);
const rows = [
  ['OWNER', 'person', true],
  ['MEMBER', 'person', true],
  ['COLLABORATOR', 'person', true],
  ['NONE', 'google-labs-jules[bot]', true],
  ['NONE', 'github-copilot[bot]', true],
  ['NONE', 'openai-codex[bot]', true],
  ['NONE', 'external-user', false],
  ['NONE', 'github-actions[bot]', false],
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
        functions = _javascript_functions(
            workflow,
            "function hasTrustedLabelPermission(",
        )
        self.assertEqual(len(functions), 1)

        assertions = r"""
const rows = [
  ['admin', true],
  ['maintain', true],
  ['write', true],
  ['triage', true],
  ['read', false],
  ['none', false],
  ['', false],
  [null, false]
];
for (const [permission, expected] of rows) {
  const actual = hasTrustedLabelPermission(permission);
  if (actual !== expected) {
    throw new Error(`${permission}: ${actual} !== ${expected}`);
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
        self.assertIn("createHash('sha256')", workflow)
        self.assertIn("missing_intent_snapshot", workflow)
        self.assertIn("intent_changed_after_dispatch", workflow)

    def test_snapshot_authorizes_opening_author_or_privileged_relabel(self):
        workflow = self._workflow()
        header = workflow[
            workflow.index("  snapshot-agent-task-intent:"):
            workflow.index("    concurrency:", workflow.index(
                "  snapshot-agent-task-intent:"
            ))
        ]

        self.assertIn("github.event.action == 'opened' &&", header)
        self.assertIn("github.event.action == 'labeled'", header)
        self.assertIn("getCollaboratorPermissionLevel", workflow)
        self.assertIn("context.actor", workflow)
        self.assertNotIn(
            "(github.event.action == 'opened' || "
            "github.event.action == 'labeled') &&",
            header,
        )

    def test_workflow_publishes_one_machine_readable_gate(self):
        workflow = self._workflow()

        self.assertIn("scripts/ci/agent_completion_gate.py", workflow)
        self.assertIn("agent-completion/truth-gate", workflow)
        self.assertIn("agent-completion-truth-gate:v1", workflow)
        self.assertIn("actions/upload-artifact@", workflow)

    def test_workflow_uses_required_ci_and_separate_post_merge_evidence(self):
        workflow = self._workflow()

        self.assertIn("run.name === 'CI'", workflow)
        self.assertIn("pr.merge_commit_sha", workflow)
        self.assertNotIn("getCombinedStatusForRef", workflow)

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

    def test_gate_runs_are_serialized_and_coalesced_by_pr_number(self):
        workflow = self._workflow()
        truth_gate_header = workflow[
            workflow.index("  truth-gate:"):
            workflow.index("    steps:", workflow.index("  truth-gate:"))
        ]

        self.assertIn("dispatch-evidence-refresh:", workflow)
        self.assertIn("group: agent-completion-${{", workflow)
        self.assertIn("inputs.pull_request || github.event.pull_request.number", workflow)
        self.assertIn("cancel-in-progress: true", workflow)
        self.assertIn("trustedCommentAssociations", workflow)
        self.assertIn("comment.author_association", workflow)
        self.assertIn("google-labs-jules[bot]", workflow)
        self.assertIn("!cancelled()", truth_gate_header)
        self.assertNotIn("always()", truth_gate_header)

    def test_collector_binds_structured_agent_event_to_head(self):
        workflow = self._workflow()

        self.assertIn("agent-lock-event", workflow)
        self.assertIn("head_sha: pr.head.sha", workflow)
        self.assertIn("structuredEvent.head_sha", workflow)
        self.assertIn("ready for (?:a )?review", workflow)
        self.assertIn("\\[PR\\]", workflow)

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
            "Unrestricted scope",
        ):
            self.assertIn(field, template)

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


if __name__ == "__main__":
    unittest.main()
