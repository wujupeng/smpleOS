-- AeroForge-X V6.1 Aircraft Core Database Migration
-- Incremental Propagation + Encryption tables
-- REQ-IC-001~010, REQ-ENG-012~017

BEGIN;

-- BOM incremental propagation log (REQ-IC-010)
CREATE TABLE IF NOT EXISTS aircraft_core.bom_incremental_propagation_log (
    log_id VARCHAR(64) PRIMARY KEY,
    change_id VARCHAR(64) NOT NULL,
    affected_node_count INT NOT NULL DEFAULT 0,
    propagation_duration_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    is_incremental BOOLEAN NOT NULL DEFAULT TRUE,
    fallback_triggered BOOLEAN NOT NULL DEFAULT FALSE,
    inconsistent_nodes TEXT[] NOT NULL DEFAULT '{}',
    propagated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- BOM propagation consistency verification (REQ-IC-005)
CREATE TABLE IF NOT EXISTS aircraft_core.bom_propagation_consistency_verifications (
    verification_id VARCHAR(64) PRIMARY KEY,
    change_id VARCHAR(64) NOT NULL,
    is_consistent BOOLEAN NOT NULL DEFAULT TRUE,
    full_tree_result_hash VARCHAR(128) NOT NULL DEFAULT '',
    incremental_result_hash VARCHAR(128) NOT NULL DEFAULT '',
    inconsistent_nodes JSONB NOT NULL DEFAULT '[]',
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Encryption keys (REQ-ENG-013)
CREATE TABLE IF NOT EXISTS aircraft_core.encryption_keys (
    key_id VARCHAR(64) PRIMARY KEY,
    algorithm VARCHAR(32) NOT NULL DEFAULT 'AES-256-GCM',
    encrypted_key_material BYTEA NOT NULL,
    key_hash VARCHAR(128) NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    rotation_due_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deactivated_at TIMESTAMPTZ
);

-- Encrypted payloads (REQ-ENG-014~015)
CREATE TABLE IF NOT EXISTS aircraft_core.encrypted_payloads_v61 (
    payload_id VARCHAR(64) PRIMARY KEY,
    ciphertext BYTEA NOT NULL,
    nonce BYTEA NOT NULL,
    auth_tag BYTEA NOT NULL,
    key_id VARCHAR(64) NOT NULL REFERENCES aircraft_core.encryption_keys(key_id),
    associated_data BYTEA,
    encrypted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_bipl_change ON aircraft_core.bom_incremental_propagation_log(change_id);
CREATE INDEX IF NOT EXISTS idx_bpcv_change ON aircraft_core.bom_propagation_consistency_verifications(change_id);
CREATE INDEX IF NOT EXISTS idx_ek_active ON aircraft_core.encryption_keys(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_ep_key ON aircraft_core.encrypted_payloads_v61(key_id);

COMMIT;