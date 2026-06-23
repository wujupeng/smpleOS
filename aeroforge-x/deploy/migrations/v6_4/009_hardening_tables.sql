-- AeroForge-X v6.4 Event Contract + Identity + Trace Graph Tables
-- EV-4.6 Digital Thread Hardening
-- DH-REQ-01~28

BEGIN;

-- =====================================================
-- H01: Event Contract Versions table
-- =====================================================
CREATE TABLE IF NOT EXISTS event_contract_versions (
    contract_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type      VARCHAR(64) NOT NULL,
    schema_version  VARCHAR(16) NOT NULL DEFAULT '1.0.0',
    schema_content  JSONB NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- H01: Consumer Idempotency Records table
-- =====================================================
CREATE TABLE IF NOT EXISTS consumer_idempotency_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consumer_name   VARCHAR(128) NOT NULL,
    event_id        VARCHAR(128) NOT NULL,
    event_type      VARCHAR(64) NOT NULL,
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_consumer_event UNIQUE (consumer_name, event_id)
);

-- =====================================================
-- H02: Configuration Identities table (dt_ prefix to avoid conflict)
-- =====================================================
CREATE TABLE IF NOT EXISTS dt_configuration_identities (
    identity_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label           VARCHAR(256) NOT NULL,
    node_type       VARCHAR(64) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- H02: Identity Mappings table
-- =====================================================
CREATE TABLE IF NOT EXISTS dt_identity_mappings (
    mapping_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id     UUID NOT NULL REFERENCES dt_configuration_identities(identity_id),
    domain          VARCHAR(64) NOT NULL,
    domain_id       VARCHAR(128) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_dt_domain_mapping UNIQUE (domain, domain_id)
);

-- =====================================================
-- H03: Trace Nodes table
-- =====================================================
CREATE TABLE IF NOT EXISTS dt_trace_nodes (
    node_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id     UUID REFERENCES dt_configuration_identities(identity_id),
    node_type       VARCHAR(64) NOT NULL,
    label           VARCHAR(256) NOT NULL,
    properties      JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- H03: Trace Edges table
-- =====================================================
CREATE TABLE IF NOT EXISTS dt_trace_edges (
    edge_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id  UUID NOT NULL REFERENCES dt_trace_nodes(node_id),
    target_node_id  UUID NOT NULL REFERENCES dt_trace_nodes(node_id),
    edge_type       VARCHAR(64) NOT NULL,
    properties      JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- Indexes
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_ecv_event_type ON event_contract_versions (event_type, is_active);
CREATE INDEX IF NOT EXISTS idx_cir_consumer ON consumer_idempotency_records (consumer_name, event_id);
CREATE INDEX IF NOT EXISTS idx_ci_node_type ON dt_configuration_identities (node_type);
CREATE INDEX IF NOT EXISTS idx_im_identity ON dt_identity_mappings (identity_id);
CREATE INDEX IF NOT EXISTS idx_im_domain ON dt_identity_mappings (domain, domain_id);
CREATE INDEX IF NOT EXISTS idx_tn_identity ON dt_trace_nodes (identity_id);
CREATE INDEX IF NOT EXISTS idx_tn_node_type ON dt_trace_nodes (node_type);
CREATE INDEX IF NOT EXISTS idx_te_source ON dt_trace_edges (source_node_id);
CREATE INDEX IF NOT EXISTS idx_te_target ON dt_trace_edges (target_node_id);
CREATE INDEX IF NOT EXISTS idx_te_edge_type ON dt_trace_edges (edge_type);

COMMIT;
