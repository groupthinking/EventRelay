import json
from pathlib import Path


def test_mcpc_registry_points_to_canonical_server():
    repo_root = Path(__file__).resolve().parents[1]
    registry_path = repo_root / "src" / "mcp" / "mcp_registry.json"

    data = json.loads(registry_path.read_text())
    tools = data.get("tools", [])

    assert len(tools) == 1, "Registry should expose a single MCPC entry"

    mcpc = tools[0]
    assert mcpc["name"] == "mcpc-unified"
    assert mcpc["transport"] == "stdio"

    command = mcpc["command"]
    assert len(command) == 2 and command[0] == "python3"

    server_path = repo_root / command[1]
    assert server_path.exists(), f"MCPC server not found at {server_path}"
    assert server_path.is_file()


def test_mcpc_ios_platform_placeholder_exists():
    repo_root = Path(__file__).resolve().parents[1]
    ios_dir = repo_root / "mcp-servers" / "mcpc" / "platforms" / "ios"
    assert ios_dir.exists() and ios_dir.is_dir()
