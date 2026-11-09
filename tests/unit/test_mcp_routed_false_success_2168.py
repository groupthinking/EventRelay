"""Issue #2168: the agent network and pipeline must not report success they did not achieve.

- An MCP route with no transport used to return {"status": "routed"} without
  executing anything, so the pipeline's deploy step (create_repo via
  mcp://github) reported success without deploying.
- VERA gateway / firewall / identity exceptions used to be logged as
  "non-blocking" and the stage ran anyway (fail-open).

No subprocess, network or database is touched: VERA is faked and the network
routes either to the real (unimplemented) MCP path or to a stub.
"""

from __future__ import annotations

import enum
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents import pipeline_orchestrator as po
from agents.mcp_agent_network import MCPAgentNetwork

NOT_IMPLEMENTED = "not_implemented"  # contract: same status scripts/ci/autonomous_video_processing.py uses


class _Emitter:
    def __init__(self):
        self.events = []

    async def emit(self, channel, payload):
        self.events.append((channel, payload))


def _orchestrator(network=None, vera=None, vera_init_error=None):
    orch = object.__new__(po.VideoPipelineOrchestrator)
    orch.network = network or MCPAgentNetwork()
    orch.pipeline_state = {}
    orch.results = {}
    orch.emitter = _Emitter()
    orch._vera = vera
    orch._vera_init_error = vera_init_error
    orch._vera_credentials = {}
    return orch


# ---------------------------------------------------------------------------
# MCP route: not implemented is a failure, never "routed"
# ---------------------------------------------------------------------------


async def test_mcp_route_reports_not_implemented_with_error():
    result = await MCPAgentNetwork()._call_mcp("mcp://github", "create_repo", {})
    assert result["status"] == NOT_IMPLEMENTED
    assert result["executed"] is False
    assert "error" in result
    assert result["status"] != "routed"


async def test_deployer_create_repo_route_is_not_executed():
    result = await MCPAgentNetwork().route_to_agent("deployer", "create_repo", {})
    assert result["status"] == NOT_IMPLEMENTED
    assert "not implemented" in result["error"]


@pytest.mark.parametrize(
    "call",
    [
        lambda n: n._call_http("https://example.invalid", "anything", {}),
        lambda n: n._call_internal("internal://nowhere", "anything", {}),
        lambda n: n._call_vercel_api("get_deployment_status", {}),
    ],
    ids=["http-unknown-endpoint", "internal-unknown-module", "vercel-unhandled-action"],
)
async def test_other_unimplemented_routes_fail_explicitly(call):
    result = await call(MCPAgentNetwork())
    assert result["status"] == NOT_IMPLEMENTED
    assert result["executed"] is False
    assert "error" in result


async def test_pipeline_deploy_stage_fails_when_route_not_executed():
    orch = _orchestrator()
    stage = await orch._execute_agent_stage("deployer")
    assert stage.success is False
    assert "not implemented" in stage.error
    assert stage.data["status"] == NOT_IMPLEMENTED


async def test_pipeline_report_is_not_success_when_deploy_not_executed(monkeypatch):
    monkeypatch.setattr(po, "get_audit_store", None)  # no audit file writes from a unit test
    network = MCPAgentNetwork()
    real_route = network.route_to_agent

    async def route(agent_id, action, payload):
        if agent_id == "deployer":
            return await real_route(agent_id, action, payload)  # the real, unimplemented MCP path
        return {"status": "success"}

    network.route_to_agent = route
    orch = _orchestrator(network=network)
    report = await orch._run_sequential_pipeline("https://youtu.be/x", {"continue_on_error": True})
    assert report["success"] is False
    assert report["stage_results"]["deployer"]["success"] is False
    assert "not implemented" in report["stage_results"]["deployer"]["error"]
    others = {k: v for k, v in report["stage_results"].items() if k != "deployer"}
    assert all(v["success"] for v in others.values())


@pytest.mark.parametrize(
    "result",
    [
        {"status": "failed", "errors": [{"stage": "github", "message": "x"}]},
        {"status": "not_implemented"},
        {"status": "error"},
        None,
    ],
    ids=["deploy-tool-failed-shape", "not-implemented", "error-status", "non-dict"],
)
async def test_failed_status_without_error_key_is_stage_failure(result):
    network = MagicMock(spec=MCPAgentNetwork)
    network.get_agent.return_value = SimpleNamespace(name="Deployment Agent", role="deploy")
    network.route_to_agent = AsyncMock(return_value=result)
    stage = await _orchestrator(network=network)._execute_agent_stage("deployer")
    assert stage.success is False
    assert stage.error


# ---------------------------------------------------------------------------
# VERA: security-check exceptions fail closed
# ---------------------------------------------------------------------------


class _FirewallAction(enum.Enum):
    ALLOW = "allow"
    BLOCK = "block"


@pytest.fixture
def fake_vera_firewall_module(monkeypatch):
    vera_pkg = types.ModuleType("vera")
    firewall_mod = types.ModuleType("vera.firewall")
    firewall_mod.FirewallAction = _FirewallAction
    vera_pkg.firewall = firewall_mod
    monkeypatch.setitem(sys.modules, "vera", vera_pkg)
    monkeypatch.setitem(sys.modules, "vera.firewall", firewall_mod)


def _fake_vera():
    breaker = MagicMock()
    breaker.allow_action.return_value = True
    breakers = MagicMock()
    breakers.get_breaker.return_value = breaker
    identity = MagicMock()
    identity.issue_credential.return_value = ("token", SimpleNamespace(token_id="jti", maturity_level=1))
    maturity = MagicMock()
    maturity.get_level.return_value = 1
    gateway = MagicMock()
    gateway.check_permission.return_value = SimpleNamespace(allowed=True, reason="")
    firewall = MagicMock()
    firewall.scan_input.return_value = SimpleNamespace(action=_FirewallAction.ALLOW)
    return {
        "identity": identity,
        "firewall": firewall,
        "gateway": gateway,
        "proof_store": MagicMock(),
        "ExecutionProof": MagicMock(),
        "hash_data": lambda text: "h",
        "breakers": breakers,
        "maturity": maturity,
        "enforcer": MagicMock(),
    }


def _stub_network():
    network = MagicMock(spec=MCPAgentNetwork)
    network.get_agent.return_value = SimpleNamespace(name="Deployment Agent", role="deploy")
    network.route_to_agent = AsyncMock(return_value={"status": "success"})
    return network


async def test_vera_all_checks_pass_runs_stage(fake_vera_firewall_module):
    """Positive control: with VERA healthy the stage executes."""
    network = _stub_network()
    stage = await _orchestrator(network=network, vera=_fake_vera())._execute_agent_stage("deployer")
    assert stage.success is True
    network.route_to_agent.assert_awaited_once()


async def test_vera_gateway_exception_blocks_stage(fake_vera_firewall_module):
    vera = _fake_vera()
    vera["gateway"].check_permission.side_effect = RuntimeError("policy store unreachable")
    network = _stub_network()
    stage = await _orchestrator(network=network, vera=vera)._execute_agent_stage("deployer")
    assert stage.success is False
    assert "gateway check failed" in stage.error and "fail-closed" in stage.error
    network.route_to_agent.assert_not_awaited()


async def test_vera_firewall_exception_blocks_stage(fake_vera_firewall_module):
    vera = _fake_vera()
    vera["firewall"].scan_input.side_effect = ValueError("scanner crashed")
    network = _stub_network()
    stage = await _orchestrator(network=network, vera=vera)._execute_agent_stage("deployer")
    assert stage.success is False
    assert "firewall scan failed" in stage.error and "fail-closed" in stage.error
    network.route_to_agent.assert_not_awaited()


async def test_vera_credential_issuance_exception_blocks_stage(fake_vera_firewall_module):
    vera = _fake_vera()
    vera["identity"].issue_credential.side_effect = OSError("key file missing")
    network = _stub_network()
    stage = await _orchestrator(network=network, vera=vera)._execute_agent_stage("deployer")
    assert stage.success is False
    assert "credential issuance failed" in stage.error
    network.route_to_agent.assert_not_awaited()


async def test_vera_init_failure_blocks_every_stage():
    network = _stub_network()
    with patch.object(po, "_get_vera", side_effect=po.VeraInitError("RuntimeError: bad key")), patch.object(
        po, "get_agent_network", return_value=network
    ), patch.object(po, "get_emitter", return_value=_Emitter()):
        orch = po.VideoPipelineOrchestrator()
    stage = await orch._execute_agent_stage("deployer")
    assert stage.success is False
    assert "failed to initialize" in stage.error
    network.route_to_agent.assert_not_awaited()


def test_get_vera_raises_when_installed_modules_fail_to_initialize(monkeypatch):
    def boom():
        raise RuntimeError("identity key unreadable")

    modules = {
        "vera": types.ModuleType("vera"),
        "vera.identity": types.ModuleType("vera.identity"),
        "vera.firewall": types.ModuleType("vera.firewall"),
        "vera.gateway": types.ModuleType("vera.gateway"),
        "vera.proof_chain": types.ModuleType("vera.proof_chain"),
        "vera.enforcement": types.ModuleType("vera.enforcement"),
        "vera.maturity": types.ModuleType("vera.maturity"),
        "vera.enforcer": types.ModuleType("vera.enforcer"),
    }
    modules["vera.identity"].get_identity_service = boom
    modules["vera.firewall"].get_firewall = MagicMock()
    modules["vera.gateway"].get_gateway = MagicMock()
    modules["vera.proof_chain"].ExecutionProof = MagicMock()
    modules["vera.proof_chain"].get_proof_store = MagicMock()
    modules["vera.proof_chain"].hash_data = MagicMock()
    modules["vera.enforcement"].get_breaker_manager = MagicMock()
    modules["vera.maturity"].get_maturity_runtime = MagicMock()
    modules["vera.enforcer"].get_enforcer = MagicMock()
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    with pytest.raises(po.VeraInitError, match="identity key unreadable"):
        po._get_vera()
