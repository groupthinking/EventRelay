"""Offline, fail-closed MCP launcher inventory. Never resolves environment values."""
import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

EXACT = re.compile(r"(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*@(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)$")
PLACEHOLDER = re.compile(r"\$(?:\{env:([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
SENSITIVE = re.compile(r"token|secret|password|authorization|api[_-]?key", re.I)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def catalog_digest(identity, response):
    if not isinstance(identity, str) or not identity or not isinstance(response, dict):
        raise ValueError("invalid catalog")
    tools = response.get("tools")
    if not isinstance(tools, list) or any(not isinstance(t, dict) or not isinstance(t.get("name"), str) or not isinstance(t.get("inputSchema"), dict) for t in tools):
        raise ValueError("invalid tools")
    if len({t["name"] for t in tools}) != len(tools):
        raise ValueError("duplicate tool")
    return hashlib.sha256(canonical({"identity": identity, "tools": sorted(tools, key=lambda t: t["name"])}).encode()).hexdigest()


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def catalog_record(identity, response):
    """Hash an offline, complete capture; evidence never grants approval."""
    full_digest = catalog_digest(identity, response)
    if response.get("nextCursor") is not None:
        raise ValueError("incomplete catalog")
    records = []
    for tool in response["tools"]:
        if not tool["name"] or ("description" in tool and not isinstance(tool["description"], str)):
            raise ValueError("invalid tool")
        for key in ("annotations", "outputSchema"):
            if key in tool and not isinstance(tool[key], dict):
                raise ValueError("invalid tool")
        # Hash every field for enforcement. Split digests are diagnostics only.
        # Omitted description differs from an explicitly empty description.
        records.append({
            "name_digest": digest(tool["name"]),
            "schema_digest": digest({key: tool[key] for key in ("inputSchema", "outputSchema") if key in tool}),
            "description_digest": digest({"description": tool["description"]} if "description" in tool else {}),
            "tool_digest": digest(tool),
        })
    return {"schema_version": 1, "approved": False,
            "identity_digest": digest(identity), "catalog_digest": full_digest,
            "tools": sorted(records, key=lambda item: item["name_digest"])}


def compare_catalog(identity, response, approval):
    """Compare against a separately reviewed pin; emit hashes/codes only."""
    observed = catalog_record(identity, response)
    fields = {"schema_version", "approved", "identity_digest", "catalog_digest", "tools"}
    tool_fields = {"name_digest", "schema_digest", "description_digest", "tool_digest"}
    def valid_hash(value):
        return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    if (not isinstance(approval, dict) or set(approval) != fields
            or type(approval["schema_version"]) is not int or approval["schema_version"] != 1
            or type(approval["approved"]) is not bool
            or not all(valid_hash(approval[key]) for key in ("identity_digest", "catalog_digest"))
            or not isinstance(approval["tools"], list)
            or any(not isinstance(item, dict) or set(item) != tool_fields
                   or not all(valid_hash(value) for value in item.values()) for item in approval["tools"])):
        raise ValueError("invalid approval")
    old = {item["name_digest"]: item for item in approval["tools"]}
    if len(old) != len(approval["tools"]):
        raise ValueError("duplicate approval tool")
    new = {item["name_digest"]: item for item in observed["tools"]}
    findings = []
    if approval["approved"] is not True:
        findings.append("UNAPPROVED_CATALOG")
    if approval["identity_digest"] != observed["identity_digest"]:
        findings.append("SERVER_IDENTITY_CHANGED")
    if approval["catalog_digest"] != observed["catalog_digest"]:
        findings.append("CATALOG_CHANGED")
    changes = []
    for name in sorted(old.keys() | new.keys()):
        codes = []
        if name not in old:
            codes.append("TOOL_ADDED")
        elif name not in new:
            codes.append("TOOL_REMOVED")
        else:
            for field, code in (("schema_digest", "SCHEMA_CHANGED"),
                                ("description_digest", "DESCRIPTION_CHANGED"),
                                ("tool_digest", "TOOL_CONTRACT_CHANGED")):
                if old[name][field] != new[name][field]:
                    codes.append(code)
        if codes:
            changes.append({"name_digest": name, "codes": codes})
    return {"schema_version": 1, "status": "BLOCKED" if findings or changes else "MATCH",
            "findings": findings, "changes": changes, "observed": observed}


def audit(config, label):
    if not isinstance(config, dict) or not isinstance(config.get("mcpServers"), dict):
        raise ValueError("invalid config")
    entries = []
    for name, server in sorted(config["mcpServers"].items()):
        findings = []
        if not isinstance(server, dict):
            server = {}
            findings.append("INVALID_SERVER")
        args = server.get("args", [])
        env = server.get("env", {})
        headers = server.get("headers", {})
        if not isinstance(args, list) or any(not isinstance(a, str) for a in args) or not isinstance(env, dict) or not isinstance(headers, dict):
            args, env, headers = [], {}, {}
            findings.append("INVALID_SHAPE")
        command = server.get("command")
        url = server.get("url")
        package = version = destination = None
        credentials = set()
        for key, value in list(env.items()) + list(headers.items()):
            if SENSITIVE.search(str(key)):
                credentials.add(str(key))
                placeholder = isinstance(value, str) and PLACEHOLDER.fullmatch(value) is not None
                if isinstance(value, str) and str(key).lower() == 'authorization':
                    prefix = re.fullmatch(r'(?:Bearer|Basic) (.+)', value, re.I)
                    placeholder = placeholder or (prefix is not None and PLACEHOLDER.fullmatch(prefix[1]) is not None)
                if not placeholder:
                    findings.append("LITERAL_CREDENTIAL")
        for arg in args:
            credentials.update(a or b for a, b in PLACEHOLDER.findall(arg) if SENSITIVE.search(a or b))
            if SENSITIVE.search(arg):
                findings.append("CREDENTIAL_ARGV")
        transport = "remote" if url is not None else "stdio"
        executable = None
        if url is not None:
            if command is not None or not isinstance(url, str):
                findings.append("INVALID_TRANSPORT")
            else:
                try:
                    parsed = urlsplit(url)
                    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                        findings.append("UNSAFE_REMOTE_URL")
                    else:
                        destination = parsed.hostname
                except ValueError:
                    findings.append("UNSAFE_REMOTE_URL")
        elif not isinstance(command, str):
            findings.append("INVALID_COMMAND")
        else:
            executable = Path(command).name
            if executable == "npx":
                candidates = [a for a in args if not a.startswith("-")]
                target = candidates[0] if candidates else ""
                match = EXACT.fullmatch(target)
                if match:
                    package, version = target.rsplit("@", 1)
                else:
                    findings.append("MUTABLE_PACKAGE")
                if any(a.startswith(("--package", "-p", "--call", "-c")) for a in args):
                    findings.append("UNSUPPORTED_NPX_MODE")
            else:
                findings.append("LOCAL_LAUNCHER_REQUIRES_REVIEW")
            findings.append("CONTAINMENT_UNVERIFIED")
        # Values, argv, raw URLs and arbitrary metadata are deliberately excluded.
        entries.append({"config": label, "server": name, "transport": transport,
                        "executable": executable, "package": package, "version": version,
                        "publisher_source": None, "credential_names": sorted(credentials),
                        "filesystem_roots": None, "network_destinations": [destination] if destination else [],
                        "tool_catalog_digest": None, "findings": sorted(set(findings)),
                        "disposition": "BLOCKED" if findings else "REVIEW_REQUIRED"})
    return entries


def load(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", action="append", required=True)
    parser.add_argument("--receipt", required=True)
    options = parser.parse_args()
    destination = Path(options.receipt)
    for config_path in options.config:
        source = Path(config_path)
        if destination.resolve() == source.resolve() or (
            destination.exists() and source.exists() and destination.samefile(source)
        ):
            parser.error('receipt must not overwrite an input configuration')
    entries, errors = [], []
    for path in sorted(set(options.config)):
        try:
            entries.extend(audit(load(path), path))
        except (OSError, ValueError, TypeError):
            errors.append({"config": path, "code": "INVALID_CONFIG"})
    receipt = {"schema_version": 1, "entries": entries, "errors": errors,
               "status": "BLOCKED" if errors or any(e["disposition"] == "BLOCKED" for e in entries) else "REVIEW_REQUIRED"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement never follows a destination symlink during the write.
    with tempfile.NamedTemporaryFile(mode='w', dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(canonical(receipt) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    # No static config alone proves provenance, containment or authorization.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

