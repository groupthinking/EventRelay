"""Evidence-based completion verdicts for autonomous agent work."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


def _collection_errors(payload: Any) -> List[str]:
    """Return the non-empty collection errors recorded by evidence collection."""

    if not isinstance(payload, dict):
        return []
    raw = payload.get("collection_errors")
    if not isinstance(raw, list):
        return []
    return [str(error) for error in raw if str(error).strip()]


def evaluate(payload: Any) -> Dict[str, Any]:
    """Evaluate agent execution evidence and return a fail-closed verdict."""

    if not isinstance(payload, dict):
        return {
            "verdict": "blocked",
            "reasons": ["invalid_payload"],
            "details": {},
        }

    policy = payload.get("policy")
    if not isinstance(policy, dict):
        return {
            "verdict": "blocked",
            "reasons": ["invalid_payload"],
            "details": {"invalid_fields": ["policy"]},
        }
    if "applicable" not in policy or type(policy["applicable"]) is not bool:
        return {
            "verdict": "blocked",
            "reasons": ["invalid_payload"],
            "details": {"invalid_fields": ["policy.applicable"]},
        }
    if policy.get("applicable") is False:
        return {"verdict": "not_applicable", "reasons": [], "details": {}}

    issue = payload.get("issue")
    pull_request = payload.get("pull_request")
    evidence = payload.get("evidence")
    events = payload.get("events")
    reviews = payload.get("reviews")
    collection_errors = payload.get("collection_errors")
    invalid_fields = []

    for field in ("agent_login", "run_id"):
        value = policy.get(field)
        if not isinstance(value, str) or not value.strip():
            invalid_fields.append("policy." + field)
    head_sha = policy.get("head_sha")
    if not isinstance(head_sha, str) or not re.fullmatch(
        r"[a-fA-F0-9]{40}", head_sha
    ):
        invalid_fields.append("policy.head_sha")

    for field, value in (
        ("issue", issue),
        ("pull_request", pull_request),
        ("evidence", evidence),
    ):
        if not isinstance(value, dict):
            invalid_fields.append(field)
    if isinstance(issue, dict) and (
        type(issue.get("number")) is not int or issue.get("number") <= 0
    ):
        invalid_fields.append("issue.number")
    for field, value in (
        ("events", events),
        ("reviews", reviews),
        ("collection_errors", collection_errors),
    ):
        if not isinstance(value, list):
            invalid_fields.append(field)

    if isinstance(events, list):
        expected_agent_login = str(policy.get("agent_login") or "").strip()
        for index, event in enumerate(events):
            if not isinstance(event, dict):
                invalid_fields.append("events")
                continue
            event_kind = event.get("kind")
            if type(event_kind) is not str or event_kind not in {
                "artifact_ready",
                "completed",
                "error",
            }:
                invalid_fields.append(f"events[{index}].kind")
            if type(event.get("sequence")) is not int:
                invalid_fields.append(f"events[{index}].sequence")
            run_id = event.get("run_id")
            if run_id is not None and (
                not isinstance(run_id, str) or not run_id.strip()
            ):
                invalid_fields.append(f"events[{index}].run_id")
            event_head_sha = event.get("head_sha")
            if event_head_sha is not None and (
                not isinstance(event_head_sha, str)
                or not re.fullmatch(r"[a-fA-F0-9]{40}", event_head_sha)
            ):
                invalid_fields.append(f"events[{index}].head_sha")
            if "comment_id" in event and type(event["comment_id"]) is not int:
                invalid_fields.append(f"events[{index}].comment_id")
            author = event.get("author")
            if (
                not isinstance(author, str)
                or not author.strip()
                or author != expected_agent_login
            ):
                invalid_fields.append(f"events[{index}].author")
            if "raw_body" in event and not isinstance(event["raw_body"], str):
                invalid_fields.append(f"events[{index}].raw_body")

    if isinstance(reviews, list):
        for index, review in enumerate(reviews):
            if not isinstance(review, dict):
                invalid_fields.append("reviews")
                continue
            for field in ("blocking", "resolved"):
                if type(review.get(field)) is not bool:
                    invalid_fields.append(f"reviews[{index}].{field}")
            source = review.get("source")
            if not isinstance(source, str) or not source.strip():
                invalid_fields.append(f"reviews[{index}].source")

    if isinstance(collection_errors, list) and not all(
        isinstance(error, str) and error.strip()
        for error in collection_errors
    ):
        invalid_fields.append("collection_errors")

    if isinstance(issue, dict):
        if issue.get("description") is not None and not isinstance(
            issue.get("description"), str
        ):
            invalid_fields.append("issue.description")
        for field in ("acceptance_criteria", "declared_files"):
            value = issue.get(field)
            if not isinstance(value, list):
                invalid_fields.append("issue." + field)
            elif isinstance(value, list) and not all(
                isinstance(item, str) and bool(item.strip()) for item in value
            ):
                invalid_fields.append("issue." + field)
        allowed_extra_files = issue.get("allowed_extra_files", [])
        if not isinstance(allowed_extra_files, list) or (
            isinstance(allowed_extra_files, list)
            and not all(
                isinstance(item, str) and bool(item.strip())
                for item in allowed_extra_files
            )
        ):
            invalid_fields.append("issue.allowed_extra_files")
        if type(issue.get("scope_unrestricted")) is not bool:
            invalid_fields.append("issue.scope_unrestricted")

    if isinstance(pull_request, dict):
        for field in ("changed_files", "present_changed_files"):
            value = pull_request.get(field)
            if not isinstance(value, list):
                invalid_fields.append("pull_request." + field)
            elif not all(
                isinstance(item, str) and bool(item.strip()) for item in value
            ):
                invalid_fields.append("pull_request." + field)
        changed_files = pull_request.get("changed_files")
        present_changed_files = pull_request.get("present_changed_files")
        if (
            isinstance(changed_files, list)
            and isinstance(present_changed_files, list)
            and all(isinstance(item, str) for item in changed_files)
            and all(isinstance(item, str) for item in present_changed_files)
            and not set(present_changed_files).issubset(set(changed_files))
        ):
            invalid_fields.append("pull_request.present_changed_files")
        for field in (
            "merged",
            "draft",
            "title_valid",
            "required_checks_passed",
            "post_merge_checks_passed",
        ):
            if type(pull_request.get(field)) is not bool:
                invalid_fields.append("pull_request." + field)

    if isinstance(evidence, dict):
        for field in ("behavior_changed_files", "focused_test_files"):
            value = evidence.get(field)
            if not isinstance(value, list):
                invalid_fields.append("evidence." + field)
            elif isinstance(value, list) and not all(
                isinstance(item, str) and bool(item.strip()) for item in value
            ):
                invalid_fields.append("evidence." + field)
        focused_test_files = evidence.get("focused_test_files")
        focused_test_results = evidence.get("focused_test_results")
        result_fields = {
            "passed",
            "failed",
            "errors",
            "skipped",
            "xfailed",
            "xpassed",
        }
        invalid_focused_results = not isinstance(focused_test_results, dict)
        if isinstance(focused_test_results, dict):
            focused_files_valid = isinstance(focused_test_files, list) and all(
                isinstance(path, str) and bool(path.strip())
                for path in focused_test_files
            )
            if not focused_files_valid or set(focused_test_results) != set(
                focused_test_files
            ):
                invalid_focused_results = True
            for path, counts in focused_test_results.items():
                if not isinstance(path, str) or not path.strip():
                    invalid_focused_results = True
                    continue
                if not isinstance(counts, dict) or set(counts) != result_fields:
                    invalid_focused_results = True
                    continue
                if any(
                    type(counts[field]) is not int or counts[field] < 0
                    for field in result_fields
                ):
                    invalid_focused_results = True
        if invalid_focused_results:
            invalid_fields.append("evidence.focused_test_results")
        present_changed_files = (
            pull_request.get("present_changed_files")
            if isinstance(pull_request, dict)
            else None
        )
        if (
            isinstance(focused_test_files, list)
            and isinstance(present_changed_files, list)
            and all(isinstance(path, str) for path in focused_test_files)
            and all(isinstance(path, str) for path in present_changed_files)
            and not set(focused_test_files).issubset(set(present_changed_files))
        ):
            invalid_fields.append("evidence.focused_test_files")
        for field in (
            "copilot_current_head_reviewed",
            "copilot_rabbit_label",
        ):
            if type(evidence.get(field)) is not bool:
                invalid_fields.append("evidence." + field)
    if invalid_fields:
        # A malformed payload is still fail-closed, but the collector already
        # knows *why* the fields are missing. Surfacing those errors here keeps
        # the verdict identical while telling the author what to fix, instead of
        # stranding them on a bare "invalid_payload".
        details = {"invalid_fields": sorted(set(invalid_fields))}
        surfaced_errors = _collection_errors(payload)
        if surfaced_errors:
            details["collection_errors"] = surfaced_errors
        return {
            "verdict": "blocked",
            "reasons": ["invalid_payload"],
            "details": details,
        }

    reasons = []
    identity_projection = {
        "issue_number": issue.get("number"),
        "agent_login": str(policy.get("agent_login") or "").strip() or None,
        "run_id": str(policy.get("run_id") or "").strip() or None,
    }
    details = {"identity_projection": identity_projection}
    collection_errors = _collection_errors(payload)
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

    missing_declared = sorted(
        set(issue.get("declared_files") or [])
        - set(pull_request.get("present_changed_files") or [])
    )
    if missing_declared:
        reasons.append("missing_declared_files")
        details["missing_declared_files"] = missing_declared

    if not pull_request.get("changed_files"):
        reasons.append("empty_pr_diff")

    events = payload.get("events") or []
    active_run_id = str(policy.get("run_id") or "").strip()
    if active_run_id:
        active_head_sha = str(policy.get("head_sha") or "").strip().lower()
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
            or str(event.get("head_sha") or "").strip().lower()
            == active_head_sha
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
        error_evidence_exists = scoped_error_exists or bool(unscoped_errors)
        legacy_positive_evidence = [
            event
            for event in events
            if error_evidence_exists
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

    if evidence.get("copilot_current_head_reviewed") is not True:
        reasons.append("missing_copilot_current_head_review")
    if evidence.get("copilot_rabbit_label") is not True:
        reasons.append("missing_copilot_rabbit_label")

    if pull_request.get("required_checks_passed") is not True:
        reasons.append("required_checks_failed")
    if pull_request.get("draft") is True:
        reasons.append("draft_pr")
    if pull_request.get("title_valid") is not True:
        reasons.append("invalid_pr_title")

    if evidence.get("behavior_changed_files"):
        if not evidence.get("focused_test_files"):
            reasons.append("missing_test_evidence")
        else:
            focused_test_results = evidence.get("focused_test_results") or {}
            failing_focused_tests = sorted(
                path
                for path in evidence.get("focused_test_files") or []
                if focused_test_results[path]["passed"] < 1
                or focused_test_results[path]["failed"] > 0
                or focused_test_results[path]["errors"] > 0
            )
            if failing_focused_tests:
                reasons.append("focused_tests_failed")
                details["focused_test_failures"] = failing_focused_tests

    if (
        pull_request.get("merged") is True
        and pull_request.get("post_merge_checks_passed") is not True
    ):
        reasons.append("post_merge_checks_failed")

    if reasons:
        return {"verdict": "blocked", "reasons": reasons, "details": details}

    if pull_request.get("merged") is True:
        return {"verdict": "completed", "reasons": [], "details": details}

    return {"verdict": "ready", "reasons": [], "details": details}


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
