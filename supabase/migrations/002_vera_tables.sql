-- VERA Security Tables
-- Migration: 002_vera_tables.sql
-- Description: Creates tables for the VERA Zero Trust security layer.
-- Tables: execution_proofs (append-only), firewall_scan_logs, agent_registry, agent_maturity

-- ============================================================
-- 1. execution_proofs — Append-only proof-of-execution chain
-- ============================================================
-- Each row is a cryptographically chained proof. Rows are NEVER updated
-- or deleted — the chain_hash includes the previous row's hash, so
-- tampering with any row breaks the chain from that point forward.

CREATE TABLE IF NOT EXISTS execution_proofs (
    proof_id       TEXT PRIMARY KEY,          -- "poe:<uuid>"
    chain_prev     TEXT NOT NULL,             -- hash of previous proof (or "genesis")
    chain_hash     TEXT NOT NULL,             -- SHA-256 hash of this proof + prev
    agent_id       TEXT NOT NULL,
    agent_credential_jti TEXT NOT NULL DEFAULT '',
    maturity_level INTEGER NOT NULL DEFAULT 0,
    timestamp      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Action details
    action_type    TEXT NOT NULL,             -- e.g. "tool_call", "decision", "delegation"
    tool           TEXT NOT NULL DEFAULT '',
    operation      TEXT NOT NULL DEFAULT '',
    input_hash     TEXT NOT NULL DEFAULT '',  -- SHA-256 of input (privacy-preserving)
    output_hash    TEXT NOT NULL DEFAULT '',
    input_summary  TEXT NOT NULL DEFAULT '',  -- Truncated plain-text summary (max 200 chars)
    output_summary TEXT NOT NULL DEFAULT '',
    duration_ms    REAL NOT NULL DEFAULT 0,

    -- Authorization context
    policy_ref     TEXT NOT NULL DEFAULT '',
    capability_used TEXT NOT NULL DEFAULT '',
    authorization_approved BOOLEAN NOT NULL DEFAULT true,

    -- Correlation
    session_id     TEXT NOT NULL DEFAULT '',
    correlation_id TEXT NOT NULL DEFAULT '',
    signature      TEXT NOT NULL DEFAULT '',

    -- Indexing
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_proofs_agent_id ON execution_proofs (agent_id);
CREATE INDEX IF NOT EXISTS idx_proofs_timestamp ON execution_proofs (timestamp);
CREATE INDEX IF NOT EXISTS idx_proofs_agent_timestamp ON execution_proofs (agent_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_proofs_correlation ON execution_proofs (correlation_id);
CREATE INDEX IF NOT EXISTS idx_proofs_session ON execution_proofs (session_id);

-- Row-Level Security: agents can only read their own proofs
ALTER TABLE execution_proofs ENABLE ROW LEVEL SECURITY;

CREATE POLICY proofs_read_own ON execution_proofs
    FOR SELECT
    USING (agent_id = current_setting('vera.current_agent_id', true));

-- Service role can read/write all proofs (for verification and admin)
CREATE POLICY proofs_service_all ON execution_proofs
    FOR ALL
    USING (current_setting('role', true) = 'service_role');


-- ============================================================
-- 2. firewall_scan_logs — Input firewall scan history
-- ============================================================

CREATE TABLE IF NOT EXISTS firewall_scan_logs (
    scan_id        TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    timestamp      TIMESTAMPTZ NOT NULL DEFAULT now(),
    input_hash     TEXT NOT NULL,             -- SHA-256 of input (never store raw input)
    action         TEXT NOT NULL,             -- allow, modify, block, alert
    threat_level   TEXT NOT NULL,             -- none, low, medium, high, critical
    patterns_matched TEXT[] NOT NULL DEFAULT '{}',
    context        TEXT NOT NULL DEFAULT '',  -- where the input came from
    scan_time_ms   REAL NOT NULL DEFAULT 0,
    mode           TEXT NOT NULL DEFAULT 'monitor',  -- enforce, monitor, disabled
    details        TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_firewall_timestamp ON firewall_scan_logs (timestamp);
CREATE INDEX IF NOT EXISTS idx_firewall_threat ON firewall_scan_logs (threat_level);
CREATE INDEX IF NOT EXISTS idx_firewall_action ON firewall_scan_logs (action);


-- ============================================================
-- 3. agent_registry — Known agent identities
-- ============================================================

CREATE TABLE IF NOT EXISTS agent_registry (
    agent_id       TEXT PRIMARY KEY,
    agent_name     TEXT NOT NULL,
    description    TEXT NOT NULL DEFAULT '',
    capability_ref TEXT NOT NULL DEFAULT '',  -- reference to capability manifest
    org_id         TEXT NOT NULL DEFAULT 'eventrelay',
    environment    TEXT NOT NULL DEFAULT 'development',
    is_active      BOOLEAN NOT NULL DEFAULT true,
    revoked_at     TIMESTAMPTZ,
    revocation_reason TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_registry_active ON agent_registry (is_active);


-- ============================================================
-- 4. agent_maturity — Agent maturity level tracking
-- ============================================================

CREATE TABLE IF NOT EXISTS agent_maturity (
    agent_id       TEXT PRIMARY KEY REFERENCES agent_registry(agent_id),
    current_level  INTEGER NOT NULL DEFAULT 0 CHECK (current_level BETWEEN 0 AND 3),
    promoted_at    TIMESTAMPTZ,
    demoted_at     TIMESTAMPTZ,
    demotion_reason TEXT,
    total_promotions INTEGER NOT NULL DEFAULT 0,
    total_demotions  INTEGER NOT NULL DEFAULT 0,
    registered_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ============================================================
-- 5. enforcement_events — Escalation and kill switch log
-- ============================================================

CREATE TABLE IF NOT EXISTS enforcement_events (
    event_id       TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    timestamp      TIMESTAMPTZ NOT NULL DEFAULT now(),
    agent_id       TEXT NOT NULL,
    event_type     TEXT NOT NULL,             -- e.g. "auth_failure", "chain_broken"
    severity       TEXT NOT NULL,             -- low, medium, high, critical
    source_pillar  TEXT NOT NULL,             -- identity, proof, firewall, gateway, enforcement
    escalation_tier INTEGER NOT NULL,         -- 0=observe, 1=warn, 2=throttle, 3=break, 4=kill
    kill_id        TEXT,                      -- non-null if kill switch activated
    details        TEXT NOT NULL DEFAULT '',
    history_snapshot JSONB                    -- recent escalation history at decision time
);

CREATE INDEX IF NOT EXISTS idx_enforcement_agent ON enforcement_events (agent_id);
CREATE INDEX IF NOT EXISTS idx_enforcement_timestamp ON enforcement_events (timestamp);
CREATE INDEX IF NOT EXISTS idx_enforcement_severity ON enforcement_events (severity);
CREATE INDEX IF NOT EXISTS idx_enforcement_tier ON enforcement_events (escalation_tier);
