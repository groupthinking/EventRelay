"""
VERA — Verifiable Enforcement for Runtime Agents

Zero Trust security layer for EventRelay's AI agent pipeline.
Every agent action is verified, every tool call is permitted (not assumed),
and every execution leaves a cryptographic receipt.

Five pillars:
  1. Identity      — JWT agent credentials (passport)
  2. Behavioral    — Proof-of-execution chains (flight recorder)
  3. Sovereignty   — Input firewall + injection defense (customs)
  4. Segmentation  — Capability-based permissions (security clearance)
  5. Enforcement   — Circuit breakers + kill switch (air marshal)
"""

from .config import VeraConfig, get_vera_config
from .identity import AgentCredential, IdentityService, get_identity_service
from .proof_chain import ExecutionProof, ProofChainStore, get_proof_store, hash_data
from .firewall import InputFirewall, ScanResult, ThreatLevel, get_firewall
from .gateway import CapabilityGateway, PermissionDecision, get_gateway
from .enforcement import (
    BreakerManager,
    BreakerState,
    CircuitBreaker,
    EscalationTier,
    KillSwitchResult,
    get_breaker_manager,
    kill_agent,
    select_escalation_tier,
)
from .maturity import MaturityLevel, MaturityRuntime, get_maturity_runtime
from .enforcer import VeraEnforcer, get_enforcer

__all__ = [
    # Config
    "VeraConfig", "get_vera_config",
    # Pillar 1: Identity
    "AgentCredential", "IdentityService", "get_identity_service",
    # Pillar 2: Behavioral Proof
    "ExecutionProof", "ProofChainStore", "get_proof_store", "hash_data",
    # Pillar 3: Sovereignty
    "InputFirewall", "ScanResult", "ThreatLevel", "get_firewall",
    # Pillar 4: Segmentation
    "CapabilityGateway", "PermissionDecision", "get_gateway",
    # Pillar 5: Enforcement
    "BreakerManager", "BreakerState", "CircuitBreaker", "EscalationTier",
    "KillSwitchResult", "get_breaker_manager", "kill_agent", "select_escalation_tier",
    # Maturity
    "MaturityLevel", "MaturityRuntime", "get_maturity_runtime",
    # Enforcer
    "VeraEnforcer", "get_enforcer",
]
