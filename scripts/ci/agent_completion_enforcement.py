"""Fail-closed verifier for the independently published agent-lock report.

The verifier intentionally accepts only a report published by a configured GitHub
App. It is designed to run from a default-branch pull_request_target workflow
that creates the required Check run directly on the pull request head SHA.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


SHA = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)


def verdict(reason: str, **details: Any) -> dict[str, Any]:
    return {"conclusion": "failure", "reason": reason, "details": details}


def neutral_verdict(reason: str, **details: Any) -> dict[str, Any]:
    return {"conclusion": "neutral", "reason": reason, "details": details}


def is_provisioned(policy: Any) -> bool:
    """Return True only when all three allowlists are non-empty.

    The three required allowlists are trusted_check_app_slugs,
    trusted_label_actors, and trusted_human_exemption_actors.
    """
    if not isinstance(policy, dict):
        return False
    return bool(
        policy.get("trusted_check_app_slugs") and
        policy.get("trusted_label_actors") and
        policy.get("trusted_human_exemption_actors")
    )


def verify(payload: Any, policy: Any, head_sha: str, pull_number: int) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(policy, dict):
        return verdict("invalid_payload")
    if not SHA.fullmatch(head_sha) or type(pull_number) is not int or pull_number < 1:
        return verdict("invalid_invocation")
    if policy.get("custom_role_policy") != "fail_closed":
        return verdict("invalid_custom_role_policy")
    apps = policy.get("trusted_check_app_slugs")
    labels = policy.get("trusted_label_actors")
    exemptions = policy.get("trusted_human_exemption_actors")
    if not all(isinstance(value, list) and all(isinstance(item, str) and item for item in value)
                   for value in (apps, labels, exemptions)):
        return verdict("invalid_trust_policy")
    if not is_provisioned(policy):
        return neutral_verdict("trust_policy_unprovisioned")
    required = {"schema_version", "pull_number", "head_sha", "publisher", "applicability", "label_authorization", "focused_tests", "agent_events"}
    if set(payload) != required or payload.get("schema_version") != 1:
        return verdict("invalid_report_schema")
    if payload.get("pull_number") != pull_number or str(payload.get("head_sha", "")).lower() != head_sha.lower():
        return verdict("report_identity_mismatch")
    publisher = payload.get("publisher")
    if not isinstance(publisher, dict) or publisher.get("app_slug") not in apps or not isinstance(publisher.get("delivery_id"), str) or not publisher["delivery_id"]:
        return verdict("untrusted_or_non_append_only_publication")
    applicability = payload.get("applicability")
    if not isinstance(applicability, dict) or applicability.get("state") not in {"agent", "human_exempt"}:
        return verdict("missing_trusted_applicability")
    if applicability["state"] == "human_exempt" and applicability.get("attested_by") not in exemptions:
        return verdict("untrusted_human_exemption")
    label = payload.get("label_authorization")
    if not isinstance(label, dict) or label.get("copilot_rabbit") is not True or label.get("applied_by") not in labels:
        return verdict("untrusted_label_authorization")
    focused = payload.get("focused_tests")
    if not isinstance(focused, dict) or focused.get("producer") != publisher.get("app_slug"):
        return verdict("untrusted_focused_test_report")
    paths = focused.get("paths")
    if not isinstance(paths, dict) or not paths:
        return verdict("missing_focused_test_report")
    for path, result in paths.items():
        if not isinstance(path, str) or not path or not isinstance(result, dict):
            return verdict("invalid_focused_test_report")
        if type(result.get("passed")) is not int or result["passed"] < 1:
            return verdict("focused_test_failed", path=path)
        if any(type(result.get(key)) is not int or result[key] != 0 for key in ("failed", "errors")):
            return verdict("focused_test_failed", path=path)
    events = payload.get("agent_events")
    if not isinstance(events, list) or not events:
        return verdict("missing_append_only_agent_events")
    if any(not isinstance(event, dict) or event.get("channel") != publisher.get("app_slug") for event in events):
        return verdict("untrusted_or_mutable_agent_events")
    if any(event.get("kind") == "error" for event in events):
        return verdict("agent_run_failed")
    if not any(event.get("kind") in {"artifact_ready", "completed"} for event in events):
        return verdict("missing_agent_success_event")
    return {"conclusion": "success", "reason": "verified", "details": {"head_sha": head_sha.lower(), "pull_number": pull_number}}


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--check-provisioned":
        policy_path = sys.argv[2]
        provisioned = is_provisioned(json.loads(Path(policy_path).read_text()))
        return 0 if provisioned else 1
    if len(sys.argv) != 5:
        raise SystemExit("usage: verifier REPORT POLICY HEAD_SHA PULL_NUMBER\n"
                         "       verifier --check-provisioned POLICY")
    report, policy, head, pull = sys.argv[1:]
    result = verify(json.loads(Path(report).read_text()), json.loads(Path(policy).read_text()), head, int(pull))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["conclusion"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
