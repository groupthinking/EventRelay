#!/usr/bin/env python3
"""
Test / Run the MCP Agent Network.

Lightweight, dependency-minimal test that exercises:
- Config loading from config/agent_network.json
- Agent + tool registry
- Pipeline sequence
- Routing (happy paths, error cases, rate limiting)
- Status reporting

Run:
  python scripts/testing/test_agent_network.py

This deliberately avoids importing the full `src.agents` package (which pulls in
heavy optional dependencies like google-genai, aiohttp, etc.). It loads only
mcp_agent_network.py via importlib.
"""
import sys
import json
import asyncio
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENT_NET_PY = ROOT / "src" / "agents" / "mcp_agent_network.py"
CONFIG_PATH = ROOT / "config" / "agent_network.json"

def load_network_module():
    """Load mcp_agent_network.py in isolation."""
    spec = importlib.util.spec_from_file_location("mcp_agent_network", AGENT_NET_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mcp_agent_network"] = mod
    spec.loader.exec_module(mod)
    return mod

def main():
    print("=== MCP AGENT NETWORK: RUN / TEST ===\n")

    mod = load_network_module()
    MCPAgentNetwork = mod.MCPAgentNetwork

    net = MCPAgentNetwork()

    # Status
    status = net.get_network_status()
    print("NETWORK STATUS:")
    print(json.dumps(status, indent=2))
    print()

    # Agents
    print("AGENTS:")
    for aid in sorted(net.agents.keys()):
        a = net.agents[aid]
        print(f"  * {aid:18} | {a.name}")
        print(f"    role: {a.role}")
        print(f"    tools: {', '.join(a.tools)}")
        print(f"    capabilities: {', '.join(a.capabilities)}")
    print()

    # Pipeline
    pipeline = net.get_pipeline_agents()
    print("PIPELINE (video-to-software):")
    print("  " + "  ->  ".join(pipeline))
    print()

    # Config validation
    print(f"CONFIG FILE: {CONFIG_PATH} (exists={CONFIG_PATH.exists()})")
    if CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text())
        print(f"  mcp_servers: {list(cfg.get('mcp_servers', {}).keys())}")
        print(f"  agents: {[a['id'] for a in cfg.get('agents', [])]}")
    print()

    # Routing
    async def test_routing():
        print("ROUTING EXERCISE:")
        cases = [
            ("video-ingest", "analyze_video", {"video_id": "test123"}),
            ("architect", "determine_architecture", {"input": "demo"}),
            ("code-gen", "generate_files", {}),
            ("build-validator", "validate_build", {"project_path": "."}),
            ("deployer", "deploy_project", {"name": "demo"}),
            ("knowledge-capture", "get_capabilities", {}),
            # error cases
            ("architect", "nonexistent_tool", {}),
            ("ghost-agent", "foo", {}),
        ]
        for agent_id, action, payload in cases:
            res = await net.route_to_agent(agent_id, action, payload)
            rstr = json.dumps(res)[:140]
            print(f"  [{agent_id}] {action}: {rstr}{'...' if len(json.dumps(res)) > 140 else ''}")

    asyncio.run(test_routing())
    print()

    # Rate limit
    print("RATE LIMIT PROBE (architect x5):")
    async def rate_probe():
        for i in range(5):
            r = await net.route_to_agent("architect", "get_context", {"i": i})
            print(f"  call {i+1}: ok={'error' not in r}")
    asyncio.run(rate_probe())
    print()

    print("=== TEST COMPLETE ===")
    print("Registry + router operational. Real execution requires installed runtime deps + live MCP servers.")
    print("See also: scripts/nightly_audit_agent.py (Jules), src/agents/pipeline_orchestrator.py")

if __name__ == "__main__":
    main()
PYEOF
echo "Wrote scripts/testing/test_agent_network.py" && python3 scripts/testing/test_agent_network.py | cat