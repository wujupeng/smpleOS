-- AeroForge-X v6.0 Physics Twin Service Database Migration
-- UQ Method Registry, 7-Discipline MDO, GD&T, Shop Floor Equipment, Digital Twin Sync
-- REQ-E-ENH-001~020, REQ-FACTORY-001~022

BEGIN;

-- =====================================================
-- V601.1: UQ method registry table
-- =====================================================
CREATE TABLE IF NOT EXISTS uq_method_registry (
    method_id         VARCHAR(64) PRIMARY KEY,
    method_type       VARCHAR(32) NOT NULL,
    surrogate_model_id VARCHAR(64) NOT NULL,
    hyperparameters   JSONB NOT NULL DEFAULT '{}',
    is_active         BOOLEAN NOT NULL DEFAULT FALSE,
    confidence_level  DOUBLE PRECISION NOT NULL DEFAULT 0.95,
    cov_threshold     DOUBLE PRECISION NOT NULL DEFAULT 0.10,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_uq_method_type CHECK (method_type IN ('BayesianPINN','MCDropout','Ensemble'))
);

-- =====================================================
-- V601.2: 7-discipline MDO run table
-- =====================================================
CREATE TABLE IF NOT EXISTS mdo_7discipline_runs (
    run_id            VARCHAR(64) PRIMARY KEY,
    requirement_id    VARCHAR(64) NOT NULL,
    discipline_config JSONB NOT NULL,
    objectives        JSONB NOT NULL,
    constraints_config JSONB NOT NULL,
    design_variables  JSONB NOT NULL,
    population_size   INTEGER NOT NULL DEFAULT 100,
    max_generations   INTEGER NOT NULL DEFAULT 300,
    convergence_status VARCHAR(32) NOT NULL DEFAULT 'Running',
    active_discipline_count INTEGER NOT NULL DEFAULT 7,
    started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at      TIMESTAMPTZ,
    CONSTRAINT chk_mdo7d_status CHECK (convergence_status IN ('Running','Converged','MaxIterations','Failed'))
);

-- =====================================================
-- V601.3: GD&T annotation table
-- =====================================================
CREATE TABLE IF NOT EXISTS gdt_annotations (
    annotation_id     VARCHAR(64) PRIMARY KEY,
    part_id           VARCHAR(64) NOT NULL,
    tolerance_type    VARCHAR(32) NOT NULL,
    tolerance_name    VARCHAR(64) NOT NULL,
    tolerance_value   DOUBLE PRECISION NOT NULL CHECK (tolerance_value > 0),
    unit              VARCHAR(8) NOT NULL DEFAULT 'mm',
    datum_references  VARCHAR(64)[] DEFAULT '{}',
    linked_operation_id VARCHAR(64),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tolerance_type CHECK (tolerance_type IN ('Form','Orientation','Location'))
);

-- =====================================================
-- V601.4: Tolerance chain definition table
-- =====================================================
CREATE TABLE IF NOT EXISTS tolerance_chains (
    chain_id          VARCHAR(64) PRIMARY KEY,
    assembly_id       VARCHAR(64) NOT NULL,
    analysis_method   VARCHAR(32) NOT NULL DEFAULT 'Statistical_RSS',
    target_assembly_tolerance DOUBLE PRECISION NOT NULL,
    worst_case_result DOUBLE PRECISION,
    statistical_result DOUBLE PRECISION,
    is_within_tolerance BOOLEAN,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_analysis_method CHECK (analysis_method IN ('WorstCase','Statistical_RSS'))
);

-- =====================================================
-- V601.5: Shop floor equipment registration table
-- =====================================================
CREATE TABLE IF NOT EXISTS shop_floor_equipment (
    equipment_id      VARCHAR(64) PRIMARY KEY,
    equipment_name    VARCHAR(256) NOT NULL,
    equipment_type    VARCHAR(32) NOT NULL,
    protocol          VARCHAR(16) NOT NULL,
    sampling_rate_ms  INTEGER NOT NULL DEFAULT 1000,
    location          VARCHAR(256) NOT NULL,
    status            VARCHAR(16) NOT NULL DEFAULT 'Offline',
    connection_config JSONB NOT NULL DEFAULT '{}',
    registered_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_equipment_type CHECK (equipment_type IN ('PLC','CNC','Robot','AGV','IoTSensor')),
    CONSTRAINT chk_protocol CHECK (protocol IN ('OPC-UA','MQTT'))
);

-- =====================================================
-- V601.6: Digital twin sync log table
-- =====================================================
CREATE TABLE IF NOT EXISTS digital_twin_sync_log (
    sync_id           VARCHAR(64) PRIMARY KEY,
    equipment_id      VARCHAR(64) NOT NULL,
    twin_state_hash   VARCHAR(64) NOT NULL,
    physical_state_hash VARCHAR(64) NOT NULL,
    is_synchronized   BOOLEAN NOT NULL,
    deviation_items   JSONB DEFAULT '[]',
    sync_duration_ms  DOUBLE PRECISION,
    synced_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- V601.7: Indexes
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_uq_active ON uq_method_registry (is_active, method_type);
CREATE INDEX IF NOT EXISTS idx_mdo7d_req ON mdo_7discipline_runs (requirement_id);
CREATE INDEX IF NOT EXISTS idx_gdt_part ON gdt_annotations (part_id, tolerance_type);
CREATE INDEX IF NOT EXISTS idx_tc_assembly ON tolerance_chains (assembly_id);
CREATE INDEX IF NOT EXISTS idx_sfe_type_status ON shop_floor_equipment (equipment_type, status);
CREATE INDEX IF NOT EXISTS idx_dt_sync_equipment ON digital_twin_sync_log (equipment_id, synced_at DESC);

COMMIT;