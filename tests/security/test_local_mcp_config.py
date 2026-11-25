import importlib.util
import json
import socket
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("audit", ROOT / "scripts/security/audit_local_mcp_configs.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network or process launch forbidden")
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)


@pytest.mark.parametrize("target", ["@scope/pkg", "pkg@latest", "pkg@^1.2.3", "alias@npm:pkg@1.2.3", "https://example.com/pkg", "pkg@1.2"])
def test_mutable_or_unsupported_package(target):
    entry = audit.audit({"mcpServers": {"x": {"command": "npx", "args": ["-y", target]}}}, "fixture")[0]
    assert "MUTABLE_PACKAGE" in entry["findings"]
    assert entry["disposition"] == "BLOCKED"


def test_exact_scoped_pin_is_not_containment_proof():
    entry = audit.audit({"mcpServers": {"x": {"command": "npx", "args": ["-y", "@scope/pkg@1.2.3"]}}}, "fixture")[0]
    assert (entry["package"], entry["version"]) == ("@scope/pkg", "1.2.3")
    assert entry["findings"] == ["CONTAINMENT_UNVERIFIED"]


def test_secret_values_never_enter_receipt():
    marker = "do-not-emit-this-value"
    result = audit.audit({"mcpServers": {"x": {"command": "npx", "args": ["pkg@1.2.3", "--access-token", marker], "env": {"SECRET": marker}}}}, "fixture")
    assert marker not in audit.canonical(result)
    assert "LITERAL_CREDENTIAL" in result[0]["findings"]
    assert "CREDENTIAL_ARGV" in result[0]["findings"]


@pytest.mark.parametrize("url", ["http://host", "https://user:password@host", "https://host?token=secret", "https://[invalid"])
def test_unsafe_remote(url):
    assert audit.audit({"mcpServers": {"x": {"url": url}}}, "fixture")[0]["disposition"] == "BLOCKED"


def test_remote_requires_review_and_does_not_expand_env():
    entry = audit.audit({"mcpServers": {"x": {"url": "https://example.com/mcp", "headers": {"Authorization": "Bearer ${env:TOKEN}"}}}}, "fixture")[0]
    assert entry["disposition"] == "REVIEW_REQUIRED"
    assert entry["network_destinations"] == ["example.com"]


@pytest.mark.parametrize("value", [None, [], {"mcpServers": []}])
def test_bad_config(value):
    with pytest.raises(ValueError):
        audit.audit(value, "fixture")


def test_duplicate_json_keys(tmp_path):
    path = tmp_path / "input.json"
    path.write_text('{"mcpServers":{},"mcpServers":{}}')
    with pytest.raises(ValueError):
        audit.load(path)


def test_catalog_bound_to_identity_and_content():
    tools = {"tools": [{"name": "a", "inputSchema": {}, "description": "GO"}, {"name": "b", "inputSchema": {}}]}
    digest = audit.catalog_digest("server-a", tools)
    assert digest == audit.catalog_digest("server-a", {"tools": list(reversed(tools["tools"]))})
    assert digest != audit.catalog_digest("server-b", tools)
    tools["tools"][0]["description"] = "changed"
    assert digest != audit.catalog_digest("server-a", tools)


def test_deterministic_cli_and_failure_receipt(tmp_path, monkeypatch):
    config, receipt = tmp_path / "input.json", tmp_path / "receipt.json"
    config.write_text(json.dumps({"mcpServers": {"x": {"command": "docker", "args": ["run", "image:latest"]}}}))
    monkeypatch.setattr("sys.argv", ["audit", "--config", str(config), "--receipt", str(receipt)])
    assert audit.main() == 1
    first = receipt.read_bytes()
    assert audit.main() == 1
    assert receipt.read_bytes() == first
    assert json.loads(first)["status"] == "BLOCKED"


def test_credential_url_never_enters_package_receipt():
    marker = 'fixture-secret-value'
    entry = audit.audit({'mcpServers': {'x': {'command': 'npx', 'args': [f'https://example.com/pkg.tgz?access_token={marker}@1.2.3']}}}, 'fixture')[0]
    assert entry['package'] is None
    assert marker not in audit.canonical(entry)
    assert entry['disposition'] == 'BLOCKED'


@pytest.mark.parametrize('value', ['Bearer fixture-secret${env:SUFFIX}', '${env:TOKEN}fixture-secret', 'fixture-secret${env:TOKEN}'])
def test_mixed_literal_placeholder_is_blocked(value):
    entry = audit.audit({'mcpServers': {'x': {'url': 'https://example.com/mcp', 'headers': {'Authorization': value}}}}, 'fixture')[0]
    assert 'LITERAL_CREDENTIAL' in entry['findings']
    assert entry['disposition'] == 'BLOCKED'
    assert 'fixture-secret' not in audit.canonical(entry)


@pytest.mark.parametrize('kind', ['direct', 'symlink', 'hardlink'])
def test_receipt_cannot_overwrite_input(tmp_path, monkeypatch, kind):
    config = tmp_path / 'input.json'
    original = '{"mcpServers": {}}'
    config.write_text(original)
    destination = config
    if kind == 'symlink':
        destination = tmp_path / 'link.json'
        destination.symlink_to(config)
    if kind == 'hardlink':
        destination = tmp_path / 'hard.json'
        destination.hardlink_to(config)
    monkeypatch.setattr('sys.argv', ['audit', '--config', str(config), '--receipt', str(destination)])
    with pytest.raises(SystemExit) as error:
        audit.main()
    assert error.value.code == 2
    assert config.read_text() == original

