-- AeroForge-X v6.0 Aircraft Core Service Database Migration
-- Configuration Management + Certification + Supplier + Shop Floor Events
-- REQ-CFG-001~022, REQ-CERT-001~026, REQ-SUP-001~024, REQ-FACTORY-019~022

BEGIN;

-- =====================================================
-- V602.1: Block configuration table
-- =====================================================
CREATE TABLE IF NOT EXISTS block_configurations (
    block_id          VARCHAR(64) PRIMARY KEY,
    aircraft_type     VARCHAR(64) NOT NULL,
    block_name        VARCHAR(32) NOT NULL,
    design_config_id  VARCHAR(64),
    manufacturing_config_id VARCHAR(64),
    operational_config_id VARCHAR(64),
    locked            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_block_name UNIQUE (aircraft_type, block_name)
);

-- =====================================================
-- V602.2: Serial number configuration table
-- =====================================================
CREATE TABLE IF NOT EXISTS serial_number_configurations (
    sn_id             VARCHAR(64) PRIMARY KEY,
    tail_number       VARCHAR(16) NOT NULL,
    block_id          VARCHAR(64) NOT NULL REFERENCES block_configurations(block_id),
    design_config_id  VARCHAR(64),
    manufacturing_config_id VARCHAR(64),
    operational_config_id VARCHAR(64),
    sn_modifications  JSONB DEFAULT '[]',
    service_bulletins JSONB DEFAULT '[]',
    repair_alterations JSONB DEFAULT '[]',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tail_number UNIQUE (tail_number)
);

-- =====================================================
-- V602.3: Configuration baseline table
-- =====================================================
CREATE TABLE IF NOT EXISTS configuration_baselines (
    baseline_id       VARCHAR(64) PRIMARY KEY,
    baseline_type     VARCHAR(8) NOT NULL,
    block_id          VARCHAR(64) NOT NULL REFERENCES block_configurations(block_id),
    configuration_snapshot JSONB NOT NULL,
    frozen_items      JSONB NOT NULL DEFAULT '[]',
    milestone         VARCHAR(16) NOT NULL,
    established_by    VARCHAR(128) NOT NULL,
    locked            BOOLEAN NOT NULL DEFAULT TRUE,
    established_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_baseline_type CHECK (baseline_type IN ('FBL','FCL','FSDL'))
);

-- =====================================================
-- V602.4: Configuration change request table
-- =====================================================
CREATE TABLE IF NOT EXISTS configuration_change_requests (
    request_id        VARCHAR(64) PRIMARY KEY,
    block_id          VARCHAR(64) NOT NULL,
    change_class      VARCHAR(8) NOT NULL,
    change_type       VARCHAR(32) NOT NULL,
    description       TEXT NOT NULL,
    requested_by      VARCHAR(128) NOT NULL,
    affected_items    JSONB NOT NULL DEFAULT '[]',
    impact_analysis   JSONB,
    approval          JSONB,
    status            VARCHAR(16) NOT NULL DEFAULT 'Submitted',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_change_class CHECK (change_class IN ('ClassI','ClassII'))
);

-- =====================================================
-- V602.5: Regulatory library table
-- =====================================================
CREATE TABLE IF NOT EXISTS regulatory_libraries (
    regulation_id     VARCHAR(64) PRIMARY KEY,
    regulation_type   VARCHAR(32) NOT NULL,
    title             VARCHAR(512) NOT NULL,
    version           VARCHAR(32) NOT NULL,
    amendment_history JSONB DEFAULT '[]',
    imported_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_regulation_type CHECK (regulation_type IN ('FAA_Part_23','FAA_Part_25','EASA_CS_23','EASA_CS_25'))
);

-- =====================================================
-- V602.6: Compliance checklist table
-- =====================================================
CREATE TABLE IF NOT EXISTS compliance_checklists (
    checklist_id      VARCHAR(64) PRIMARY KEY,
    regulation_id     VARCHAR(64) NOT NULL REFERENCES regulatory_libraries(regulation_id),
    project_id        VARCHAR(64) NOT NULL,
    completion_percentage DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- V602.7: Certification evidence package table
-- =====================================================
CREATE TABLE IF NOT EXISTS certification_evidence_packages (
    package_id        VARCHAR(64) PRIMARY KEY,
    checklist_id      VARCHAR(64) NOT NULL REFERENCES compliance_checklists(checklist_id),
    project_id        VARCHAR(64) NOT NULL,
    is_complete       BOOLEAN NOT NULL DEFAULT FALSE,
    is_locked         BOOLEAN NOT NULL DEFAULT FALSE,
    version           INTEGER NOT NULL DEFAULT 1,
    submitted_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- V602.8: Supplier profile table
-- =====================================================
CREATE TABLE IF NOT EXISTS supplier_profiles (
    supplier_id       VARCHAR(64) PRIMARY KEY,
    company_name      VARCHAR(256) NOT NULL,
    certifications    VARCHAR(64)[] DEFAULT '{}',
    capability_matrix JSONB DEFAULT '{}',
    quality_history   JSONB DEFAULT '{}',
    status            VARCHAR(16) NOT NULL DEFAULT 'Pending',
    registered_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_supplier_status CHECK (status IN ('Pending','Approved','Suspended','Disqualified'))
);

-- =====================================================
-- V602.9: Supplier quality rating table
-- =====================================================
CREATE TABLE IF NOT EXISTS supplier_quality_ratings (
    rating_id         VARCHAR(64) PRIMARY KEY,
    supplier_id       VARCHAR(64) NOT NULL REFERENCES supplier_profiles(supplier_id),
    on_time_delivery_rate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    first_pass_yield  DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    defect_rate       DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    car_responsiveness DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    audit_findings_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    overall_rating    DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    is_below_threshold BOOLEAN NOT NULL DEFAULT FALSE,
    rated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- V602.10: Material lot table
-- =====================================================
CREATE TABLE IF NOT EXISTS material_lots (
    lot_id            VARCHAR(64) PRIMARY KEY,
    supplier_id       VARCHAR(64) NOT NULL REFERENCES supplier_profiles(supplier_id),
    material_specification VARCHAR(256) NOT NULL,
    heat_number       VARCHAR(64) NOT NULL,
    certificate_of_conformance VARCHAR(512),
    test_results      JSONB DEFAULT '{}',
    status            VARCHAR(16) NOT NULL DEFAULT 'Received',
    received_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_lot_status CHECK (status IN ('Received','InProcess','Installed','NonConforming'))
);

-- =====================================================
-- V602.11: NDT record table
-- =====================================================
CREATE TABLE IF NOT EXISTS ndt_records (
    ndt_id            VARCHAR(64) PRIMARY KEY,
    part_id           VARCHAR(64) NOT NULL,
    inspection_method VARCHAR(8) NOT NULL,
    equipment_calibration_data JSONB DEFAULT '{}',
    inspection_procedure_ref VARCHAR(512),
    inspector_certification VARCHAR(256),
    acceptance_criteria TEXT,
    result            VARCHAR(16) NOT NULL,
    linked_lot_id     VARCHAR(64),
    linked_operation_id VARCHAR(64),
    inspected_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_ndt_method CHECK (inspection_method IN ('UT','RT','PT','MT','ET')),
    CONSTRAINT chk_ndt_result CHECK (result IN ('Accept','Reject','Conditional'))
);

-- =====================================================
-- V602.12: Supplier quality issue table
-- =====================================================
CREATE TABLE IF NOT EXISTS supplier_quality_issues (
    issue_id          VARCHAR(64) PRIMARY KEY,
    supplier_id       VARCHAR(64) NOT NULL REFERENCES supplier_profiles(supplier_id),
    issue_type        VARCHAR(32) NOT NULL,
    description       TEXT NOT NULL,
    severity          VARCHAR(16) NOT NULL,
    correlated_lots   VARCHAR(64)[] DEFAULT '{}',
    correlated_ndt_records VARCHAR(64)[] DEFAULT '{}',
    affected_aircraft VARCHAR(16)[] DEFAULT '{}',
    car_id            VARCHAR(64),
    status            VARCHAR(16) NOT NULL DEFAULT 'Reported',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_issue_severity CHECK (severity IN ('Critical','Major','Minor'))
);

-- =====================================================
-- V602.13: Corrective action request table
-- =====================================================
CREATE TABLE IF NOT EXISTS corrective_action_requests (
    car_id            VARCHAR(64) PRIMARY KEY,
    issue_id          VARCHAR(64) NOT NULL REFERENCES supplier_quality_issues(issue_id),
    supplier_id       VARCHAR(64) NOT NULL,
    root_cause        TEXT,
    corrective_action TEXT,
    due_date          TIMESTAMPTZ NOT NULL,
    response_date     TIMESTAMPTZ,
    is_overdue        BOOLEAN NOT NULL DEFAULT FALSE,
    verification_status VARCHAR(16) NOT NULL DEFAULT 'Pending',
    escalation_level  INTEGER NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- V602.14: Shop floor event table
-- =====================================================
CREATE TABLE IF NOT EXISTS shop_floor_events (
    event_id          VARCHAR(64) PRIMARY KEY,
    event_type        VARCHAR(32) NOT NULL,
    source_equipment_id VARCHAR(64),
    payload           JSONB NOT NULL,
    emitted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- V602.15: Indexes
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_block_aircraft ON block_configurations (aircraft_type, block_name);
CREATE INDEX IF NOT EXISTS idx_sn_block ON serial_number_configurations (block_id);
CREATE INDEX IF NOT EXISTS idx_baseline_block ON configuration_baselines (block_id, baseline_type);
CREATE INDEX IF NOT EXISTS idx_ccr_block ON configuration_change_requests (block_id, status);
CREATE INDEX IF NOT EXISTS idx_reg_type ON regulatory_libraries (regulation_type, version);
CREATE INDEX IF NOT EXISTS idx_cl_regulation ON compliance_checklists (regulation_id, project_id);
CREATE INDEX IF NOT EXISTS idx_cep_checklist ON certification_evidence_packages (checklist_id);
CREATE INDEX IF NOT EXISTS idx_supplier_status ON supplier_profiles (status);
CREATE INDEX IF NOT EXISTS idx_sqr_supplier ON supplier_quality_ratings (supplier_id, rated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ml_supplier ON material_lots (supplier_id, status);
CREATE INDEX IF NOT EXISTS idx_ndt_part ON ndt_records (part_id, inspection_method);
CREATE INDEX IF NOT EXISTS idx_sqi_supplier ON supplier_quality_issues (supplier_id, severity);
CREATE INDEX IF NOT EXISTS idx_car_issue ON corrective_action_requests (issue_id, verification_status);
CREATE INDEX IF NOT EXISTS idx_sfe_type ON shop_floor_events (event_type, emitted_at DESC);

COMMIT;