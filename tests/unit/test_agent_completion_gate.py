import importlib
import io
import json
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
        "events": [{"kind": "completed", "sequence": 1}],
        "reviews": [],
        "evidence": {
            "behavior_changed_files": [
                "src/youtube_extension/agent_lock/completion_gate.py"
            ],
            "focused_test_files": ["tests/unit/test_agent_completion_gate.py"],
            "focused_tests_passed": True,
        },
        "policy": {"applicable": True},
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

    def test_explicit_unrestricted_scope_allows_undeclared_files(self):
        payload = _valid_payload()
        payload["issue"]["declared_files"] = []
        payload["issue"]["scope_unrestricted"] = True
        payload["pull_request"]["changed_files"].append("docs/extra.md")

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "ready")
        self.assertNotIn("scope_drift", result["reasons"])

    def test_completion_followed_by_error_is_contradictory(self):
        payload = _valid_payload()
        payload["events"] = [
            {"kind": "completed", "sequence": 1},
            {"kind": "error", "sequence": 2},
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("contradictory_terminal_events", result["reasons"])

    def test_artifact_ready_followed_by_error_is_failed_not_completed(self):
        payload = _valid_payload()
        payload["events"] = [
            {"kind": "artifact_ready", "sequence": 1},
            {"kind": "error", "sequence": 2},
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
            {"kind": "error", "run_id": "old-run", "sequence": 1},
            {"kind": "completed", "run_id": "new-run", "sequence": 2},
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "ready")

    def test_historical_success_cannot_satisfy_a_silent_current_run(self):
        payload = _valid_payload()
        payload["policy"]["run_id"] = "new-run"
        payload["events"] = [
            {"kind": "completed", "run_id": "old-run", "sequence": 1},
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("missing_agent_result", result["reasons"])

    def test_unscoped_success_cannot_satisfy_a_correlated_run(self):
        payload = _valid_payload()
        payload["policy"]["run_id"] = "new-run"
        payload["events"] = [
            {"kind": "completed", "sequence": 1},
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
            {"kind": "artifact_ready", "run_id": None, "sequence": 1},
            {
                "kind": "error",
                "run_id": "1892762060881911102",
                "sequence": 2,
            },
        ]

        result = _evaluate(payload)

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("contradictory_terminal_events", result["reasons"])

    def test_unscoped_error_still_blocks_a_correlated_run(self):
        payload = _valid_payload()
        payload["policy"]["run_id"] = "new-run"
        payload["events"] = [
            {"kind": "error", "sequence": 1},
            {"kind": "completed", "run_id": "new-run", "sequence": 2},
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

    def test_malformed_nested_fields_return_a_verdict(self):
        payload = _valid_payload()
        payload["events"] = ["not-an-event"]

        try:
            result = _evaluate(payload)
        except (AttributeError, TypeError):
            self.fail("malformed nested evidence raised instead of failing closed")

        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("invalid_payload", result["reasons"])

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

    def test_falsey_non_dict_containers_are_not_masked(self):
        for field in ("issue", "pull_request", "evidence", "policy"):
            with self.subTest(field=field):
                payload = _valid_payload()
                payload[field] = []

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("invalid_payload", result["reasons"])
                self.assertIn(field, result["details"]["invalid_fields"])

    def test_non_boolean_review_flags_cannot_bypass_blocking(self):
        for field in ("blocking", "resolved"):
            with self.subTest(field=field):
                payload = _valid_payload()
                payload["reviews"] = [
                    {"blocking": True, "resolved": False, "source": "r1"}
                ]
                payload["reviews"][0][field] = "true"

                result = _evaluate(payload)

                self.assertEqual(result["verdict"], "blocked")
                self.assertIn("invalid_payload", result["reasons"])
                self.assertIn(
                    "reviews[0]." + field,
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

        self.assertIn("id: resolve", workflow)
        self.assertIn("state: 'pending'", workflow)
        self.assertIn("if: always() && steps.resolve.outputs.pr_number != ''", workflow)
        self.assertIn("id: upload", workflow)
        self.assertIn("steps.upload.outcome", workflow)
        self.assertIn("id: publish", workflow)
        self.assertIn("steps.publish.outcome != 'success'", workflow)
        self.assertIn("latest.target_url === runUrl", workflow)
        self.assertLess(
            workflow.index("name: Upload gate evidence"),
            workflow.index("name: Publish stable status and comment"),
        )

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

        self.assertIn("dispatch-evidence-refresh:", workflow)
        self.assertIn("group: agent-completion-${{", workflow)
        self.assertIn("inputs.pull_request || github.event.pull_request.number", workflow)
        self.assertIn("cancel-in-progress: true", workflow)
        self.assertIn("trustedCommentAssociations", workflow)
        self.assertIn("comment.author_association", workflow)
        self.assertIn("google-labs-jules[bot]", workflow)

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
        self.assertIn("multiple_closing_issues", workflow)

    def test_snapshot_validates_contract_and_freezes_approval_state(self):
        workflow = self._workflow()

        self.assertIn("pre-dispatch confirmation", workflow.lower())
        self.assertIn("incomplete_agent_task_contract", workflow)
        self.assertIn("scope_unrestricted_approved", workflow)
        self.assertIn("intent_snapshot_after_dispatch", workflow)

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
