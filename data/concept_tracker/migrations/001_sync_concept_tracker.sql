-- Schema concept_tracker for Neon project round-night-95394081, database neondb
CREATE SCHEMA IF NOT EXISTS concept_tracker;

CREATE TABLE IF NOT EXISTS concept_tracker.concepts (
    concept_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    definition TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ASSERTED', 'VERIFIED', 'PARTIAL', 'UNDEFINED', 'REFUTED', 'DISPUTED')),
    owner TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS concept_tracker.term_collisions (
    collision_id TEXT PRIMARY KEY,
    term TEXT NOT NULL,
    entity_a TEXT NOT NULL,
    entity_b TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'SEPARATED',
    notes TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS concept_tracker.claims_with_provenance (
    claim_id TEXT PRIMARY KEY,
    concept_id TEXT REFERENCES concept_tracker.concepts(concept_id),
    claim_text TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ASSERTED', 'VERIFIED', 'PARTIAL', 'UNDEFINED', 'REFUTED', 'DISPUTED')),
    source_url TEXT NOT NULL,
    source_date TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    evidence_summary TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS concept_tracker.relationships (
    relationship_id TEXT PRIMARY KEY,
    source_concept TEXT NOT NULL REFERENCES concept_tracker.concepts(concept_id),
    target_concept TEXT NOT NULL REFERENCES concept_tracker.concepts(concept_id),
    relationship_type TEXT NOT NULL,
    confidence NUMERIC(4,3) NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS concept_tracker.contradictions (
    contradiction_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    incorrect_claim TEXT NOT NULL,
    corrected_fact TEXT NOT NULL,
    prevention_rule TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS concept_tracker.open_review_queue (
    review_id TEXT PRIMARY KEY,
    item_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    priority TEXT NOT NULL,
    reason TEXT NOT NULL,
    assigned_to TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS concept_tracker.execution_receipts (
    receipt_id TEXT PRIMARY KEY,
    source_event_key TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    inputs JSONB NOT NULL,
    evidence JSONB NOT NULL,
    decision TEXT NOT NULL,
    exact_mutation JSONB NOT NULL,
    artifact_url TEXT,
    commit_or_pr TEXT,
    owner TEXT NOT NULL,
    state TEXT NOT NULL,
    verification_result TEXT NOT NULL,
    failures JSONB,
    blockers JSONB,
    next_action TEXT NOT NULL
);

-- Seed Initial Concepts from YC Harness Deep Dive & Invariant Boundaries
INSERT INTO concept_tracker.concepts (concept_id, name, domain, definition, status, owner) VALUES
('concept:qm', 'QM (Quartermaster)', 'agent_orchestration', 'Multiplayer agent harness decoupling reasoning/state from ephemeral execution sandboxes', 'VERIFIED', 'Y Combinator'),
('concept:prime_agent', 'Prime Agent', 'recursive_language_models', 'Open-source self-improving RLM harness with prompt-as-code and L1-L3 cache', 'VERIFIED', 'Prime Intellect'),
('concept:openjarvis', 'OpenJarvis', 'local_agentic_stack', 'Personal AI framework on personal devices optimized via cloud meta-models', 'PARTIAL', 'OpenJarvis'),
('concept:hayden_mhs', 'Hayden MHS', 'user_systems', 'Hayden proprietary Model Harness System', 'VERIFIED', 'Hayden Garvey'),
('concept:anthropic_mhs', 'Anthropic MHS', 'vendor_systems', 'Anthropic Model Harness System', 'VERIFIED', 'Anthropic'),
('concept:google_agentic_video', 'Google Agentic Video', 'video_intelligence', 'Google multimodal video understanding framework', 'VERIFIED', 'Google'),
('concept:mds', 'MDS', 'undefined', 'Undefined acronym / subsystem', 'UNDEFINED', 'Unknown')
ON CONFLICT (concept_id) DO UPDATE SET updated_at = NOW();

-- Term collisions preserved strictly
INSERT INTO concept_tracker.term_collisions (collision_id, term, entity_a, entity_b, status, notes) VALUES
('collision:mhs', 'MHS', 'concept:hayden_mhs', 'concept:anthropic_mhs', 'SEPARATED', 'Hayden MHS and Anthropic MHS must never be merged or conflated.')
ON CONFLICT (collision_id) DO NOTHING;

-- Seed Relationships
INSERT INTO concept_tracker.relationships (relationship_id, source_concept, target_concept, relationship_type, confidence, verified, notes) VALUES
('rel:qm_uvai', 'concept:qm', 'concept:prime_agent', 'pattern_similarity', 0.920, TRUE, 'Both decouple execution from persistent orchestrator state.')
ON CONFLICT (relationship_id) DO NOTHING;
