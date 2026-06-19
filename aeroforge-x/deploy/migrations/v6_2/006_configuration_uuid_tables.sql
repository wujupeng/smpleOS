-- AeroForge-X V6.2 Configuration UUID Table
-- Unified primary key threading through all domains
-- Prevents Configuration Drift (per PM directive)

BEGIN;

CREATE TABLE IF NOT EXISTS configuration_identities (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_code     VARCHAR(32) NOT NULL UNIQUE,
    aircraft_type     VARCHAR(64) NOT NULL,
    block_id          VARCHAR(64) NOT NULL,
    origin            VARCHAR(64) NOT NULL,
    parent_id         UUID REFERENCES configuration_identities(id),
    status            VARCHAR(16) NOT NULL DEFAULT 'Active',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_business_code_format CHECK (business_code ~ '^CFG-\d{4}-\d{6}$'),
    CONSTRAINT chk_config_status CHECK (status IN ('Active','Superseded','Obsolete'))
);

CREATE INDEX IF NOT EXISTS idx_ci_aircraft ON configuration_identities (aircraft_type, block_id);
CREATE INDEX IF NOT EXISTS idx_ci_parent ON configuration_identities (parent_id);
CREATE INDEX IF NOT EXISTS idx_ci_origin ON configuration_identities (origin, status);

CREATE TABLE IF NOT EXISTS configuration_identity_links (
    link_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id          UUID NOT NULL REFERENCES configuration_identities(id),
    domain_object_type VARCHAR(32) NOT NULL,
    domain_object_id   VARCHAR(64) NOT NULL,
    linked_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_domain_type CHECK (domain_object_type IN (
        'Requirement', 'EBOM', 'MBOM', 'SBOM', 'CAD', 'CAE', 'MDO',
        'Simulation', 'Certification', 'Supplier', 'Factory', 'Fleet',
        'GDT', 'UQ', 'NDT', 'CAR', 'Evidence', 'Checklist'
    ))
);

CREATE INDEX IF NOT EXISTS idx_cil_config ON configuration_identity_links (config_id);
CREATE INDEX IF NOT EXISTS idx_cil_domain ON configuration_identity_links (domain_object_type, domain_object_id);

COMMIT;