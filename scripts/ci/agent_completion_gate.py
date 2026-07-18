"""Evidence-based completion verdicts for autonomous agent work."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


def _object_or_empty(value: Any) -> Any:
    """Return ``{}`` for an absent/``None`` field, else the value unchanged.

    Unlike ``value or {}`` this preserves a supplied non-dict value (e.g. ``[]``
    or ``0``) so the downstream ``isinstance`` checks can reject it with
    ``invalid_payload`` instead of silently coercing malformed input to an empty
    object and letting it pass validation.
    """

    return {} if value is None else value


def evaluate(payload: Any) -> Dict[str, Any]:
    """Evaluate agent execution evidence and return a fail-closed verdict."""

    if not isinstance(payload, dict):
        return {
            "verdict": "blocked",
            "reasons": ["invalid_payload"],
            "details": {},
        }

    policy = _object_or_empty(payload.get("policy"))
    if not isinstance(policy, dict):
        return {
            "verdict": "blocked",
            "reasons": ["invalid_payload"],
            "details": {"invalid_fields": ["policy"]},
        }
    if "applicable" in policy and type(policy["applicable"]) is not bool:
        return {
            "verdict": "blocked",
            "reasons": ["invalid_payload"],
            "details": {"invalid_fields": ["policy.applicable"]},
        }
    if policy.get("applicable") is False:
        return {"verdict": "not_applicable", "reasons": [], "details": {}}

    issue = _object_or_empty(payload.get("issue"))
    pull_request = _object_or_empty(payload.get("pull_request"))
    evidence = _object_or_empty(payload.get("evidence"))
    invalid_fields = []
    for field, value in (
        ("issue", issue),
        ("pull_request", pull_request),
        ("evidence", evidence),
    ):
        if not isinstance(value, dict):
            invalid_fields.append(field)
    for field in ("events", "reviews", "collection_errors"):
        value = payload.get(field)
        if value is not None and not isinstance(value, list):
            invalid_fields.append(field)
    for field, value in (
        ("events", payload.get("events") or []),
        ("reviews", payload.get("reviews") or []),
    ):
        if isinstance(value, list) and not all(
            isinstance(item, dict) for item in value
        ):
            invalid_fields.append(field)
    reviews_value = payload.get("reviews")
    if isinstance(reviews_value, list):
        for index, review in enumerate(reviews_value):
            if not isinstance(review, dict):
                continue
            for field in ("blocking", "resolved"):
                if field in review and type(review[field]) is not bool:
                    invalid_fields.append("reviews[%d].%s" % (index, field))
    if isinstance(issue, dict):
        for field in (
            "acceptance_criteria",
            "declared_files",
            "allowed_extra_files",
        ):
            value = issue.get(field)
            if value is not None and not isinstance(value, list):
                invalid_fields.append("issue." + field)
            elif isinstance(value, list) and not all(
                isinstance(item, str) for item in value
            ):
                invalid_fields.append("issue." + field)
        if (
            "scope_unrestricted" in issue
            and type(issue["scope_unrestricted"]) is not bool
        ):
            invalid_fields.append("issue.scope_unrestricted")
    if isinstance(pull_request, dict):
        value = pull_request.get("changed_files")
        if value is not None and not isinstance(value, list):
            invalid_fields.append("pull_request.changed_files")
        elif isinstance(value, list) and not all(
            isinstance(item, str) for item in value
        ):
            invalid_fields.append("pull_request.changed_files")
        for field in (
            "merged",
            "draft",
            "title_valid",
            "required_checks_passed",
            "post_merge_checks_passed",
        ):
            if field in pull_request and type(pull_request[field]) is not bool:
                invalid_fields.append("pull_request." + field)
    if isinstance(evidence, dict):
        for field in ("behavior_changed_files", "focused_test_files"):
            value = evidence.get(field)
            if value is not None and not isinstance(value, list):
                invalid_fields.append("evidence." + field)
            elif isinstance(value, list) and not all(
                isinstance(item, str) for item in value
            ):
                invalid_fields.append("evidence." + field)
        if (
            "focused_tests_passed" in evidence
            and type(evidence["focused_tests_passed"]) is not bool
        ):
            invalid_fields.append("evidence.focused_tests_passed")
    if invalid_fields:
        return {
            "verdict": "blocked",
            "reasons": ["invalid_payload"],
            "details": {"invalid_fields": sorted(set(invalid_fields))},
        }

    reasons = []
    details = {}
    collection_errors = [
        str(error)
        for error in (payload.get("collection_errors") or [])
        if str(error).strip()
    ]
    if collection_errors:
        reasons.append("evidence_collection_failed")
        details["collection_errors"] = collection_errors
    if not str(issue.get("description") or "").strip():
        reasons.append("blank_issue_description")
    if not issue.get("acceptance_criteria"):
        reasons.append("missing_acceptance_criteria")
    if not issue.get("declared_files") and not issue.get("scope_unrestricted", False):
        reasons.append("missing_declared_scope")

    if not issue.get("scope_unrestricted", False):
        declared = set(issue.get("declared_files") or [])
        declared.update(issue.get("allowed_extra_files") or [])
        changed = set(pull_request.get("changed_files") or [])
        undeclared = sorted(changed - declared)
        if undeclared:
            reasons.append("scope_drift")
            details["undeclared_files"] = undeclared

    events = payload.get("events") or []
    active_run_id = str(policy.get("run_id") or "").strip()
    if active_run_id:
        active_head_sha = str(policy.get("head_sha") or "").strip()
        scoped_events = [
            event
            for event in events
            if str(event.get("run_id") or "").strip() == active_run_id
        ]
        current_events = [
            event
            for event in scoped_events
            if str(event.get("kind") or "").lower() == "error"
            or not active_head_sha
            or str(event.get("head_sha") or "").strip() == active_head_sha
        ]
        unscoped_errors = [
            event
            for event in events
            if not str(event.get("run_id") or "").strip()
            and str(event.get("kind") or "").lower() == "error"
        ]
        scoped_error_exists = any(
            str(event.get("kind") or "").lower() == "error"
            for event in scoped_events
        )
        legacy_positive_evidence = [
            event
            for event in events
            if scoped_error_exists
            and not str(event.get("run_id") or "").strip()
            and str(event.get("kind") or "").lower()
            in {"artifact_ready", "completed"}
        ]
        events = current_events + unscoped_errors + legacy_positive_evidence

    terminal_kinds = {
        str(event.get("kind") or "").lower()
        for event in events
    }
    if not terminal_kinds.intersection({"artifact_ready", "completed"}):
        reasons.append("missing_agent_result")
    if "error" in terminal_kinds:
        reasons.append("agent_run_failed")
    if (
        "error" in terminal_kinds
        and terminal_kinds.intersection({"artifact_ready", "completed"})
    ):
        reasons.append("contradictory_terminal_events")

    unresolved_reviews = [
        str(review.get("source") or "unknown")
        for review in (payload.get("reviews") or [])
        if review.get("blocking") is True and review.get("resolved") is not True
    ]
    if unresolved_reviews:
        reasons.append("unresolved_review")
        details["unresolved_reviews"] = unresolved_reviews

    if pull_request.get("required_checks_passed") is not True:
        reasons.append("required_checks_failed")
    if pull_request.get("draft") is True:
        reasons.append("draft_pr")
    if pull_request.get("title_valid") is not True:
        reasons.append("invalid_pr_title")

    if evidence.get("behavior_changed_files"):
        if not evidence.get("focused_test_files"):
            reasons.append("missing_test_evidence")
        elif evidence.get("focused_tests_passed") is not True:
            reasons.append("focused_tests_failed")

    if (
        pull_request.get("merged") is True
        and pull_request.get("post_merge_checks_passed") is not True
    ):
        reasons.append("post_merge_checks_failed")

    if reasons:
        return {"verdict": "blocked", "reasons": reasons, "details": details}

    if pull_request.get("merged") is True:
        return {"verdict": "completed", "reasons": [], "details": {}}

    return {"verdict": "ready", "reasons": [], "details": {}}


def main(argv: Any = None) -> int:
    """Evaluate one JSON evidence file and emit a machine-readable verdict."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON evidence file, or - for stdin")
    args = parser.parse_args(argv)

    try:
        if args.input == "-":
            payload = json.load(sys.stdin)
        else:
            payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = evaluate(payload)
    except json.JSONDecodeError as exc:
        result = {
            "verdict": "blocked",
            "reasons": ["invalid_json"],
            "details": {"error": str(exc)},
        }
    except (OSError, UnicodeError) as exc:
        result = {
            "verdict": "blocked",
            "reasons": ["input_read_failed"],
            "details": {"error": str(exc)},
        }
    print(json.dumps(result, sort_keys=True))
    return 1 if result["verdict"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
