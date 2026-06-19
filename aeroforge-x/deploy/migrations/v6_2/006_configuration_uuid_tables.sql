-- AeroForge-X V6.2 Configuration UUID Table
-- Unified primary key threading through all domains
-- Prevents Configuration Drift (per PM directive)

BEGIN;

CREATE TABLE IF NOT EXISTS configuration_identities (
    config_uuid        VARCHAR(32) PRIMARY KEY,
    aircraft_type      VARCHAR(64) NOT NULL,
    block_id           VARCHAR(64) NOT NULL,
    origin             VARCHAR(64) NOT NULL,
    parent_config_uuid VARCHAR(32),
    status             VARCHAR(16) NOT NULL DEFAULT 'Active',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_config_uuid_format CHECK (config_uuid ~ '^CFG-\d{4}-\d{6}$'),
    CONSTRAINT chk_config_status CHECK (status IN ('Active','Superseded','Obsolete'))
);

CREATE INDEX IF NOT EXISTS idx_ci_aircraft ON configuration_identities (aircraft_type, block_id);
CREATE INDEX IF NOT EXISTS idx_ci_parent ON configuration_identities (parent_config_uuid);
CREATE INDEX IF NOT EXISTS idx_ci_origin ON configuration_identities (origin, status);

-- Link configuration UUID to existing domain objects
CREATE TABLE IF NOT EXISTS configuration_identity_links (
    link_id            VARCHAR(64) PRIMARY KEY,
    config_uuid        VARCHAR(32) NOT NULL REFERENCES configuration_identities(config_uuid),
    domain_object_type VARCHAR(32) NOT NULL,
    domain_object_id   VARCHAR(64) NOT NULL,
    linked_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_domain_type CHECK (domain_object_type IN (
        'Requirement', 'EBOM', 'MBOM', 'SBOM', 'CAD', 'CAE', 'MDO',
        'Simulation', 'Certification', 'Supplier', 'Factory', 'Fleet',
        'GDT', 'UQ', 'NDT', 'CAR', 'Evidence', 'Checklist'
    ))
);

CREATE INDEX IF NOT EXISTS idx_cil_config ON configuration_identity_links (config_uuid);
CREATE INDEX IF NOT EXISTS idx_cil_domain ON configuration_identity_links (domain_object_type, domain_object_id);

COMMIT;