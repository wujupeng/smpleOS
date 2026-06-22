-- AeroForge-X v6.4 Digital Thread Foundation Tables
-- Material Thread + Quality Thread + Certification Thread
-- DT-REQ-01~17

BEGIN;

-- =====================================================
-- DT01: Material Lot table (Digital Thread)
-- =====================================================
CREATE TABLE IF NOT EXISTS dt_material_lots (
    lot_id            VARCHAR(64) PRIMARY KEY,
    material_code     VARCHAR(64) NOT NULL,
    material_name     VARCHAR(256) NOT NULL,
    supplier_id       VARCHAR(64) NOT NULL,
    manufacture_date  DATE NOT NULL,
    received_date     DATE NOT NULL,
    certificate_no    VARCHAR(128) NOT NULL,
    status            VARCHAR(16) NOT NULL DEFAULT 'received',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_dt_lot_status CHECK (status IN ('received','inspected','accepted','rejected','quarantined'))
);

-- =====================================================
-- DT01: Block-Material association table
-- =====================================================
CREATE TABLE IF NOT EXISTS dt_block_materials (
    block_id          VARCHAR(64) NOT NULL REFERENCES block_configurations(block_id),
    lot_id            VARCHAR(64) NOT NULL REFERENCES dt_material_lots(lot_id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (block_id, lot_id)
);

-- =====================================================
-- DT02: NDT Record table (Digital Thread)
-- =====================================================
CREATE TABLE IF NOT EXISTS dt_ndt_records (
    ndt_record_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_lot_id   VARCHAR(64) NOT NULL REFERENCES dt_material_lots(lot_id),
    test_type         VARCHAR(32) NOT NULL,
    result            VARCHAR(16) NOT NULL,
    inspector         VARCHAR(128) NOT NULL,
    test_date         DATE NOT NULL,
    notes             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_dt_ndt_test_type CHECK (test_type IN ('ultrasonic','radiographic','penetrant','magnetic_particle','eddy_current')),
    CONSTRAINT chk_dt_ndt_result CHECK (result IN ('pass','fail','conditional'))
);

-- =====================================================
-- DT02: Corrective Action Request table (Digital Thread)
-- =====================================================
CREATE TABLE IF NOT EXISTS dt_corrective_actions (
    car_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ndt_record_id     UUID NOT NULL REFERENCES dt_ndt_records(ndt_record_id),
    description       TEXT NOT NULL,
    status            VARCHAR(16) NOT NULL DEFAULT 'open',
    responsible_person VARCHAR(128) NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at         TIMESTAMPTZ,
    CONSTRAINT chk_dt_car_status CHECK (status IN ('open','in_progress','closed'))
);

-- =====================================================
-- DT03: Compliance Requirement table
-- =====================================================
CREATE TABLE IF NOT EXISTS dt_compliance_requirements (
    requirement_id    VARCHAR(64) PRIMARY KEY,
    regulation        VARCHAR(64) NOT NULL,
    description       TEXT NOT NULL,
    compliance_status VARCHAR(16) NOT NULL DEFAULT 'pending',
    responsible_person VARCHAR(128),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_dt_compliance_status CHECK (compliance_status IN ('compliant','non_compliant','partial','pending'))
);

-- =====================================================
-- DT03: Evidence table
-- =====================================================
CREATE TABLE IF NOT EXISTS dt_evidences (
    evidence_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id    VARCHAR(64) NOT NULL REFERENCES dt_compliance_requirements(requirement_id),
    file_id           UUID NOT NULL DEFAULT gen_random_uuid(),
    file_name         VARCHAR(512) NOT NULL,
    bucket            VARCHAR(128) NOT NULL DEFAULT 'aeroforge-cert-evidence',
    content_type      VARCHAR(128) NOT NULL,
    file_size         BIGINT NOT NULL,
    upload_timestamp  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_dt_file_size CHECK (file_size > 0)
);

-- =====================================================
-- DT03: Compliance-Evidence association table
-- =====================================================
CREATE TABLE IF NOT EXISTS dt_compliance_evidences (
    requirement_id    VARCHAR(64) NOT NULL REFERENCES dt_compliance_requirements(requirement_id),
    evidence_id       UUID NOT NULL REFERENCES dt_evidences(evidence_id),
    PRIMARY KEY (requirement_id, evidence_id)
);

-- =====================================================
-- Indexes
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_dt_ml_material_code ON dt_material_lots (material_code);
CREATE INDEX IF NOT EXISTS idx_dt_ml_supplier ON dt_material_lots (supplier_id);
CREATE INDEX IF NOT EXISTS idx_dt_bm_block ON dt_block_materials (block_id);
CREATE INDEX IF NOT EXISTS idx_dt_bm_lot ON dt_block_materials (lot_id);
CREATE INDEX IF NOT EXISTS idx_dt_nr_lot ON dt_ndt_records (material_lot_id);
CREATE INDEX IF NOT EXISTS idx_dt_ca_ndt ON dt_corrective_actions (ndt_record_id);
CREATE INDEX IF NOT EXISTS idx_dt_ev_req ON dt_evidences (requirement_id);

COMMIT;