import unittest

from scripts.ci.agent_completion_enforcement import missing_publication, verify


HEAD = "a" * 40
POLICY = {"custom_role_policy": "fail_closed", "trusted_check_app_slugs": ["agent-lock-trusted"], "trusted_label_actors": ["maintainer"], "trusted_human_exemption_actors": ["maintainer"]}


def report():
    return {"schema_version": 1, "pull_number": 9, "head_sha": HEAD, "publisher": {"app_slug": "agent-lock-trusted", "delivery_id": "delivery-1"}, "applicability": {"state": "agent"}, "label_authorization": {"copilot_rabbit": True, "applied_by": "maintainer"}, "focused_tests": {"producer": "agent-lock-trusted", "paths": {"tests/unit/test_x.py": {"passed": 1, "failed": 0, "errors": 0}}}, "agent_events": [{"channel": "agent-lock-trusted", "kind": "artifact_ready"}]}


class EnforcementTests(unittest.TestCase):
    def test_accepts_head_bound_trusted_report(self):
        self.assertEqual(verify(report(), POLICY, HEAD, 9)["conclusion"], "success")

    def test_unprovisioned_policy_blocks(self):
        policy = dict(POLICY, trusted_check_app_slugs=[])
        self.assertEqual(verify(report(), policy, HEAD, 9)["reason"], "trust_policy_unprovisioned")

    def test_stale_report_blocks(self):
        body = report(); body["head_sha"] = "b" * 40
        self.assertEqual(verify(body, POLICY, HEAD, 9)["reason"], "report_identity_mismatch")

    def test_error_cannot_be_erased(self):
        body = report(); body["agent_events"].append({"channel": "agent-lock-trusted", "kind": "error"})
        self.assertEqual(verify(body, POLICY, HEAD, 9)["reason"], "agent_run_failed")

    def test_untrusted_label_blocks(self):
        body = report(); body["label_authorization"]["applied_by"] = "agent"
        self.assertEqual(verify(body, POLICY, HEAD, 9)["reason"], "untrusted_label_authorization")

    def test_missing_publication_with_unprovisioned_policy_is_neutral(self):
        policy = dict(POLICY, trusted_check_app_slugs=[], trusted_label_actors=[], trusted_human_exemption_actors=[])
        result = missing_publication(policy)
        self.assertEqual(result["conclusion"], "neutral")
        self.assertEqual(result["reason"], "trust_policy_unprovisioned_no_publication")

    def test_missing_publication_with_provisioned_policy_blocks(self):
        self.assertEqual(missing_publication(POLICY)["reason"], "missing_trusted_publication")

    def test_missing_publication_with_partially_provisioned_policy_blocks(self):
        policy = dict(POLICY, trusted_check_app_slugs=[], trusted_label_actors=[])
        self.assertEqual(missing_publication(policy)["reason"], "missing_trusted_publication")

    def test_missing_publication_with_malformed_policy_blocks(self):
        for policy in (None, [], {}, dict(POLICY, custom_role_policy="open", trusted_check_app_slugs=[], trusted_label_actors=[], trusted_human_exemption_actors=[]), dict(POLICY, trusted_check_app_slugs=None, trusted_label_actors=[], trusted_human_exemption_actors=[])):
            self.assertEqual(missing_publication(policy)["conclusion"], "failure")
            self.assertEqual(missing_publication(policy)["reason"], "missing_trusted_publication")
