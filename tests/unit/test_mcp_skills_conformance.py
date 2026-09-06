"""Conformance fixtures for SEP-2640 Skills over MCP."""

from __future__ import annotations

import hashlib

import pytest

from youtube_extension.services.agents.mcp_skills_conformance import (
    EXTENSION_ID,
    SkillsConformanceError,
    SkillsConformanceHost,
)


SKILL_BYTES = (
    b"---\nname: video-pack-review\n"
    b"description: Review a normalized Video Pack\n---\n\n# Review\n"
)


def digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def capabilities(*, directory_read: bool = False) -> dict:
    return {
        "capabilities": {
            "resources": {},
            "extensions": {
                EXTENSION_ID: {"directoryRead": directory_read},
            },
        }
    }


def raw_skill(
    *, uri: str = "skill://video-pack-review/SKILL.md", content: bytes = SKILL_BYTES
) -> dict:
    return {
        "uri": uri,
        "frontmatter": {
            "name": "video-pack-review",
            "description": "Review a normalized Video Pack",
        },
        "resources": [
            {"uri": uri, "digest": digest(content), "size": len(content)},
        ],
    }


def host() -> SkillsConformanceHost:
    return SkillsConformanceHost("eventrelay-fixture", capabilities())


def test_capability_negotiation_and_request_shapes() -> None:
    with pytest.raises(SkillsConformanceError, match="resources"):
        SkillsConformanceHost(
            "server-a", {"capabilities": {"extensions": {EXTENSION_ID: {}}}}
        )
    current = SkillsConformanceHost("server-a", capabilities(directory_read=True))
    assert current.list_request(1)["method"] == "skills/list"
    assert current.get_request(2, "skill://a/SKILL.md")["method"] == "skills/get"
    assert current.read_request(3, "skill://a/SKILL.md")["method"] == "resources/read"
    assert current.directory_request(4, "skill://a")["method"] == (
        "resources/directory/read"
    )


def test_directory_read_is_not_called_without_capability() -> None:
    with pytest.raises(SkillsConformanceError, match="not declared"):
        host().directory_request(1, "skill://video-pack-review")


def test_compound_identity_keeps_same_uri_from_two_origins_distinct() -> None:
    first = host().ingest_list({"skills": [raw_skill()]})[0]
    second_host = SkillsConformanceHost("other-server", capabilities())
    second = second_host.ingest_list({"skills": [raw_skill()]})[0]
    assert first.identity != second.identity


def test_manifest_validation_rejects_digest_and_path_failures() -> None:
    malformed = raw_skill()
    malformed["resources"][0]["digest"] = "sha256:not-a-digest"
    with pytest.raises(SkillsConformanceError, match="digest"):
        host().ingest_list({"skills": [malformed]})

    escaped = raw_skill()
    escaped["resources"][0]["uri"] = "skill://other/SKILL.md"
    with pytest.raises(SkillsConformanceError, match="outside"):
        host().ingest_list({"skills": [escaped]})

    traversal = raw_skill()
    traversal["resources"].append(
        {
            "uri": "skill://video-pack-review/%2e%2e/secret.txt",
            "digest": digest(b"secret"),
            "size": 6,
        }
    )
    with pytest.raises(SkillsConformanceError, match="traversal"):
        host().ingest_list({"skills": [traversal]})


def test_manifest_limits_are_enforced_before_reads() -> None:
    oversized = raw_skill()
    oversized["resources"][0]["size"] = 16 * 1024 * 1024 + 1
    with pytest.raises(SkillsConformanceError, match="16 MiB"):
        host().ingest_list({"skills": [oversized]})

    too_many = raw_skill()
    too_many["resources"].extend(
        {
            "uri": f"skill://video-pack-review/references/{index}.md",
            "digest": digest(str(index).encode()),
            "size": len(str(index)),
        }
        for index in range(512)
    )
    with pytest.raises(SkillsConformanceError, match="512-resource"):
        host().ingest_list({"skills": [too_many]})


def test_non_skill_scheme_is_allowed_but_name_rules_still_apply() -> None:
    github_uri = "github://groupthinking/EventRelay/skills/video-pack-review/SKILL.md"
    fixture = raw_skill(uri=github_uri)
    assert host().ingest_list({"skills": [fixture]})[0].uri == github_uri

    invalid_name = raw_skill()
    invalid_name["frontmatter"]["name"] = "Video Pack Review"
    with pytest.raises(SkillsConformanceError, match="Agent Skills"):
        host().ingest_list({"skills": [invalid_name]})


def test_name_collision_is_recorded_without_discarding_entries() -> None:
    current = host()
    nested = raw_skill(uri="skill://team/video-pack-review/SKILL.md")
    entries = current.ingest_list({"skills": [raw_skill(), nested]})
    assert len(entries) == 2
    assert len(current.entries) == 2
    assert [receipt.status for receipt in current.receipts].count("COLLISION") == 2


def test_explicit_content_bound_approval_and_verified_read() -> None:
    current = host()
    entry = current.ingest_list({"skills": [raw_skill()]})[0]
    assert current.approve(entry.identity, explicit=False).status == "DENIED"
    assert current.approve(entry.identity, explicit=True).status == "APPROVED"
    receipt = current.verify_resource(
        entry.identity,
        origin="eventrelay-fixture",
        resource_uri=entry.uri,
        content=SKILL_BYTES,
    )
    assert receipt.status == "VERIFIED"
    assert receipt.actual_digest == digest(SKILL_BYTES)


def test_digest_drift_and_cross_origin_reads_are_denied() -> None:
    current = host()
    entry = current.ingest_list({"skills": [raw_skill()]})[0]
    current.approve(entry.identity, explicit=True)
    drift = current.verify_resource(
        entry.identity,
        origin="eventrelay-fixture",
        resource_uri=entry.uri,
        content=SKILL_BYTES + b"changed",
    )
    assert drift.status == "DENIED"
    assert drift.reason == "size or digest mismatch"
    cross_origin = current.verify_resource(
        entry.identity,
        origin="other-server",
        resource_uri=entry.uri,
        content=SKILL_BYTES,
    )
    assert cross_origin.status == "DENIED"
    assert cross_origin.reason == "cross-origin read"


def test_frontmatter_mismatch_is_denied_even_with_matching_manifest() -> None:
    changed = SKILL_BYTES.replace(b"Review a normalized", b"Execute an untrusted")
    fixture = raw_skill(content=changed)
    current = host()
    entry = current.ingest_list({"skills": [fixture]})[0]
    current.approve(entry.identity, explicit=True)
    receipt = current.verify_resource(
        entry.identity,
        origin="eventrelay-fixture",
        resource_uri=entry.uri,
        content=changed,
    )
    assert receipt.status == "DENIED"
    assert "frontmatter" in receipt.reason


def test_manifest_change_revokes_prior_approval() -> None:
    current = host()
    entry = current.ingest_list({"skills": [raw_skill()]})[0]
    current.approve(entry.identity, explicit=True)
    changed = raw_skill(content=SKILL_BYTES + b"\nUpdate")
    current.ingest_list({"skills": [changed]})
    assert entry.identity not in current.approvals
    assert any(receipt.status == "REVOKED" for receipt in current.receipts)


def test_dynamic_skill_cannot_receive_persisted_approval() -> None:
    fixture = raw_skill()
    fixture["resources"] = "dynamic"
    current = host()
    entry = current.ingest_list({"skills": [fixture]})[0]
    receipt = current.approve(entry.identity, explicit=True)
    assert receipt.status == "DENIED"
    assert "content-bound" in receipt.reason


def test_execution_requires_separate_tool_approval() -> None:
    current = host()
    entry = current.ingest_list({"skills": [raw_skill()]})[0]
    current.approve(entry.identity, explicit=True)
    denied = current.authorize_execution(entry.identity, tool_name="shell")
    assert denied.status == "DENIED"
    approved = current.authorize_execution(
        entry.identity,
        tool_name="shell",
        explicitly_approved_tools=frozenset({"shell"}),
    )
    assert approved.status == "APPROVED"


def test_skills_get_must_match_listed_entry() -> None:
    current = host()
    entry = current.ingest_list({"skills": [raw_skill()]})[0]
    assert current.reconcile_get(entry.identity, {"skill": raw_skill()}) == entry
    mismatched = raw_skill()
    mismatched["frontmatter"]["description"] = "Different"
    with pytest.raises(SkillsConformanceError, match="disagrees"):
        current.reconcile_get(entry.identity, {"skill": mismatched})
