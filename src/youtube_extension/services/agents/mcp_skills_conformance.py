"""Fixture-only host conformance for the accepted MCP Skills extension.

This module does not enable remote skills in production.  It models the host
obligations in SEP-2640 so Agent Factory can test discovery, compound identity,
content-bound approval, origin binding, digest verification, and denial receipts
before a runtime adapter is connected.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping
from urllib.parse import unquote, urlparse

import yaml


EXTENSION_ID = "io.modelcontextprotocol/skills"
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_RESOURCES = 512
MAX_TOTAL_SIZE = 16 * 1024 * 1024


class SkillsConformanceError(ValueError):
    """Raised when a fixture violates a normative extension requirement."""


@dataclass(frozen=True)
class SkillResource:
    uri: str
    digest: str
    size: int


@dataclass(frozen=True)
class SkillEntry:
    server_identity: str
    uri: str
    frontmatter: dict[str, Any]
    resources: tuple[SkillResource, ...] | str

    @property
    def identity(self) -> tuple[str, str]:
        return self.server_identity, self.uri

    @property
    def name(self) -> str:
        return str(self.frontmatter["name"])

    def approval_fingerprint(self) -> str | None:
        if self.resources == "dynamic":
            return None
        manifest = [
            {"uri": item.uri, "digest": item.digest, "size": item.size}
            for item in sorted(self.resources, key=lambda item: item.uri)
        ]
        encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()


@dataclass(frozen=True)
class SkillReceipt:
    event: str
    status: str
    server_identity: str
    skill_uri: str | None
    reason: str
    resource_uri: str | None = None
    expected_digest: str | None = None
    actual_digest: str | None = None


@dataclass
class SkillsConformanceHost:
    """In-memory conformance harness for a single host-assigned server origin."""

    server_identity: str
    capabilities: Mapping[str, Any]
    entries: dict[tuple[str, str], SkillEntry] = field(default_factory=dict)
    approvals: dict[tuple[str, str], str] = field(default_factory=dict)
    receipts: list[SkillReceipt] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.server_identity.strip():
            raise SkillsConformanceError("server_identity must be host assigned")
        capabilities = self.capabilities.get("capabilities", self.capabilities)
        if "resources" not in capabilities:
            raise SkillsConformanceError("Skills requires the resources capability")
        extensions = capabilities.get("extensions") or {}
        if EXTENSION_ID not in extensions:
            raise SkillsConformanceError("server did not declare the Skills extension")

    @property
    def directory_read_enabled(self) -> bool:
        capabilities = self.capabilities.get("capabilities", self.capabilities)
        options = (capabilities.get("extensions") or {}).get(EXTENSION_ID) or {}
        return options.get("directoryRead") is True

    @staticmethod
    def list_request(request_id: int, cursor: str | None = None) -> dict[str, Any]:
        params = {} if cursor is None else {"cursor": cursor}
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "skills/list",
            "params": params,
        }

    @staticmethod
    def get_request(request_id: int, uri: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "skills/get",
            "params": {"uri": uri},
        }

    @staticmethod
    def read_request(request_id: int, uri: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "resources/read",
            "params": {"uri": uri},
        }

    def directory_request(self, request_id: int, uri: str) -> dict[str, Any]:
        if not self.directory_read_enabled:
            raise SkillsConformanceError("directoryRead was not declared")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "resources/directory/read",
            "params": {"uri": uri},
        }

    def ingest_list(self, result: Mapping[str, Any]) -> tuple[SkillEntry, ...]:
        """Validate one complete listing and retain every compound identity."""
        raw_skills = result.get("skills")
        if not isinstance(raw_skills, list):
            raise SkillsConformanceError("skills/list result must contain skills")

        next_entries: dict[tuple[str, str], SkillEntry] = {}
        names: dict[str, list[tuple[str, str]]] = {}
        for raw in raw_skills:
            entry = self._parse_entry(raw)
            if entry.identity in next_entries:
                raise SkillsConformanceError("duplicate server + URI identity")
            next_entries[entry.identity] = entry
            names.setdefault(entry.name, []).append(entry.identity)

        for identity, old in self.entries.items():
            new = next_entries.get(identity)
            if (
                identity in self.approvals
                and (new is None or new.approval_fingerprint() != old.approval_fingerprint())
            ):
                self.approvals.pop(identity, None)
                self._record("approval", "REVOKED", old.uri, "manifest changed")

        self.entries = next_entries
        for name, identities in names.items():
            if len(identities) > 1:
                for identity in identities:
                    self._record(
                        "discovery",
                        "COLLISION",
                        identity[1],
                        f"name {name!r} is ambiguous within origin",
                    )
        self._record("skills/list", "VERIFIED", None, f"{len(next_entries)} skills")
        return tuple(next_entries.values())

    def reconcile_get(
        self, identity: tuple[str, str], result: Mapping[str, Any]
    ) -> SkillEntry:
        """Require skills/get to describe the same entry held from skills/list."""
        if identity[0] != self.server_identity:
            raise SkillsConformanceError("cross-origin skills/get denied")
        entry = self._parse_entry(result.get("skill"))
        if entry.identity != identity:
            raise SkillsConformanceError("skills/get returned a different identity")
        listed = self.entries.get(identity)
        if listed is None or listed != entry:
            raise SkillsConformanceError("skills/get disagrees with skills/list")
        self._record("skills/get", "VERIFIED", entry.uri, "entry matches listing")
        return entry

    def approve(self, identity: tuple[str, str], *, explicit: bool) -> SkillReceipt:
        entry = self._entry(identity)
        fingerprint = entry.approval_fingerprint()
        if not explicit:
            return self._record("approval", "DENIED", entry.uri, "explicit approval absent")
        if fingerprint is None:
            return self._record(
                "approval", "DENIED", entry.uri, "dynamic manifest cannot be content-bound"
            )
        self.approvals[identity] = fingerprint
        return self._record("approval", "APPROVED", entry.uri, fingerprint)

    def verify_resource(
        self,
        identity: tuple[str, str],
        *,
        origin: str,
        resource_uri: str,
        content: bytes,
    ) -> SkillReceipt:
        entry = self._entry(identity)
        if origin != self.server_identity:
            return self._record(
                "resources/read",
                "DENIED",
                entry.uri,
                "cross-origin read",
                resource_uri,
            )
        if identity not in self.approvals:
            return self._record(
                "resources/read",
                "DENIED",
                entry.uri,
                "skill is not approved",
                resource_uri,
            )
        if entry.resources == "dynamic":
            return self._record(
                "resources/read", "DENIED", entry.uri, "dynamic manifest", resource_uri
            )
        resource = next((item for item in entry.resources if item.uri == resource_uri), None)
        if resource is None:
            return self._record(
                "resources/read",
                "DENIED",
                entry.uri,
                "resource is outside approved manifest",
                resource_uri,
            )

        actual = "sha256:" + hashlib.sha256(content).hexdigest()
        if len(content) != resource.size or actual != resource.digest:
            return self._record(
                "resources/read",
                "DENIED",
                entry.uri,
                "size or digest mismatch",
                resource_uri,
                resource.digest,
                actual,
            )
        if resource_uri == entry.uri:
            parsed = _frontmatter(content)
            if parsed != entry.frontmatter:
                return self._record(
                    "resources/read",
                    "DENIED",
                    entry.uri,
                    "SKILL.md frontmatter differs from entry",
                    resource_uri,
                    resource.digest,
                    actual,
                )
        return self._record(
            "resources/read",
            "VERIFIED",
            entry.uri,
            "size, digest, origin, and approval verified",
            resource_uri,
            resource.digest,
            actual,
        )

    def authorize_execution(
        self,
        identity: tuple[str, str],
        *,
        tool_name: str,
        explicitly_approved_tools: frozenset[str] = frozenset(),
    ) -> SkillReceipt:
        entry = self._entry(identity)
        if identity not in self.approvals or tool_name not in explicitly_approved_tools:
            return self._record(
                "execution",
                "DENIED",
                entry.uri,
                f"tool {tool_name!r} lacks explicit per-skill approval",
            )
        return self._record(
            "execution", "APPROVED", entry.uri, f"tool {tool_name!r} approved"
        )

    def _entry(self, identity: tuple[str, str]) -> SkillEntry:
        if identity[0] != self.server_identity:
            raise SkillsConformanceError("identity belongs to another server")
        try:
            return self.entries[identity]
        except KeyError as exc:
            raise SkillsConformanceError("unknown skill identity") from exc

    def _parse_entry(self, raw: Any) -> SkillEntry:
        if not isinstance(raw, Mapping):
            raise SkillsConformanceError("skill entry must be an object")
        uri = raw.get("uri")
        frontmatter = raw.get("frontmatter")
        resources = raw.get("resources")
        if not isinstance(uri, str) or not _skill_name_from_uri(uri):
            raise SkillsConformanceError("skill URI must end in /SKILL.md")
        if not isinstance(frontmatter, Mapping):
            raise SkillsConformanceError("frontmatter must be an object")
        if not isinstance(frontmatter.get("name"), str) or not isinstance(
            frontmatter.get("description"), str
        ):
            raise SkillsConformanceError("frontmatter requires name and description")
        if not _SKILL_NAME.fullmatch(frontmatter["name"]):
            raise SkillsConformanceError("frontmatter name violates Agent Skills rules")
        if frontmatter["name"] != _skill_name_from_uri(uri):
            raise SkillsConformanceError("frontmatter name does not match URI path")
        if resources == "dynamic":
            parsed_resources: tuple[SkillResource, ...] | str = "dynamic"
        elif isinstance(resources, list):
            parsed_resources = self._parse_resources(uri, resources)
        else:
            raise SkillsConformanceError("resources must be a manifest or dynamic")
        return SkillEntry(
            server_identity=self.server_identity,
            uri=uri,
            frontmatter=dict(frontmatter),
            resources=parsed_resources,
        )

    @staticmethod
    def _parse_resources(
        skill_uri: str, resources: list[Any]
    ) -> tuple[SkillResource, ...]:
        root = skill_uri.removesuffix("/SKILL.md")
        _validate_resource_uri(skill_uri)
        if len(resources) > MAX_RESOURCES:
            raise SkillsConformanceError("manifest exceeds 512-resource host limit")
        parsed: list[SkillResource] = []
        seen: set[str] = set()
        total_size = 0
        for raw in resources:
            if not isinstance(raw, Mapping):
                raise SkillsConformanceError("manifest item must be an object")
            uri, digest, size = raw.get("uri"), raw.get("digest"), raw.get("size")
            if not isinstance(uri, str):
                raise SkillsConformanceError("resource URI is malformed")
            _validate_resource_uri(uri)
            if not uri.startswith(root + "/"):
                raise SkillsConformanceError("resource is outside skill root")
            if uri in seen:
                raise SkillsConformanceError("duplicate resource URI")
            if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
                raise SkillsConformanceError("resource digest is malformed")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise SkillsConformanceError("resource size is malformed")
            total_size += size
            if total_size > MAX_TOTAL_SIZE:
                raise SkillsConformanceError("manifest exceeds 16 MiB host limit")
            seen.add(uri)
            parsed.append(SkillResource(uri=uri, digest=digest, size=size))
        if skill_uri not in seen:
            raise SkillsConformanceError("manifest omits its SKILL.md")
        return tuple(parsed)

    def _record(
        self,
        event: str,
        status: str,
        skill_uri: str | None,
        reason: str,
        resource_uri: str | None = None,
        expected_digest: str | None = None,
        actual_digest: str | None = None,
    ) -> SkillReceipt:
        receipt = SkillReceipt(
            event=event,
            status=status,
            server_identity=self.server_identity,
            skill_uri=skill_uri,
            reason=reason,
            resource_uri=resource_uri,
            expected_digest=expected_digest,
            actual_digest=actual_digest,
        )
        self.receipts.append(receipt)
        return receipt


def _skill_name_from_uri(uri: str) -> str | None:
    try:
        _validate_resource_uri(uri)
    except SkillsConformanceError:
        return None
    parsed = urlparse(uri)
    if not uri.endswith("/SKILL.md"):
        return None
    segments = [part for part in ([parsed.netloc] + parsed.path.split("/")) if part]
    return segments[-2] if len(segments) >= 2 and segments[-1] == "SKILL.md" else None


def _validate_resource_uri(uri: str) -> None:
    parsed = urlparse(uri)
    if not parsed.scheme or parsed.params or parsed.query or parsed.fragment:
        raise SkillsConformanceError("resource URI is malformed")
    if "//" in parsed.path:
        raise SkillsConformanceError("resource URI is malformed")
    raw_segments = [parsed.netloc, *parsed.path.split("/")]
    segments = [part for part in raw_segments if part]
    if not segments:
        raise SkillsConformanceError("resource URI is malformed")
    for raw in segments:
        decoded = unquote(raw)
        if decoded in {".", ".."} or "/" in decoded or "\\" in decoded:
            raise SkillsConformanceError("resource URI contains path traversal")


def _frontmatter(content: bytes) -> dict[str, Any]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SkillsConformanceError("SKILL.md frontmatter is malformed") from exc
    if not text.startswith("---\n"):
        raise SkillsConformanceError("SKILL.md lacks YAML frontmatter")
    try:
        block = text.split("---\n", 2)[1]
        parsed = yaml.safe_load(block)
    except (yaml.YAMLError, IndexError) as exc:
        raise SkillsConformanceError("SKILL.md frontmatter is malformed") from exc
    if not isinstance(parsed, dict):
        raise SkillsConformanceError("SKILL.md frontmatter must be an object")
    return parsed
