-- AeroForge-X v5.0 Aircraft Core Service Database Migration
-- Manufacturing Digital Thread + Fleet Intelligence tables
-- REQ-MFG-001~028, REQ-FLT-019~025

BEGIN;

-- =====================================================
-- V502.1: EBOM records table
-- =====================================================
CREATE TABLE IF NOT EXISTS ebom_records (
    bom_id           VARCHAR(64) PRIMARY KEY,
    project_id       VARCHAR(64) NOT NULL,
    version          INTEGER NOT NULL DEFAULT 1,
    root_node_id     VARCHAR(64) NOT NULL,
    locked           BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ebom_version UNIQUE (project_id, version)
);

-- =====================================================
-- V502.2: MBOM records table
-- =====================================================
CREATE TABLE IF NOT EXISTS mbom_records (
    bom_id           VARCHAR(64) PRIMARY KEY,
    source_ebom_id   VARCHAR(64) NOT NULL REFERENCES ebom_records(bom_id),
    version          INTEGER NOT NULL DEFAULT 1,
    root_node_id     VARCHAR(64) NOT NULL,
    manufacturing_rules_applied VARCHAR(64)[] DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- V502.3: SBOM records table
-- =====================================================
CREATE TABLE IF NOT EXISTS sbom_records (
    bom_id           VARCHAR(64) PRIMARY KEY,
    source_mbom_id   VARCHAR(64) NOT NULL REFERENCES mbom_records(bom_id),
    version          INTEGER NOT NULL DEFAULT 1,
    root_node_id     VARCHAR(64) NOT NULL,
    service_rules_applied VARCHAR(64)[] DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- V502.4: BOM nodes table (shared by EBOM/MBOM/SBOM)
-- =====================================================
CREATE TABLE IF NOT EXISTS bom_nodes (
    node_id          VARCHAR(64) PRIMARY KEY,
    bom_id           VARCHAR(64) NOT NULL,
    bom_type         VARCHAR(8) NOT NULL,
    parent_node_id   VARCHAR(64) REFERENCES bom_nodes(node_id),
    part_number      VARCHAR(128) NOT NULL,
    part_name        VARCHAR(256) NOT NULL,
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    unit             VARCHAR(16) NOT NULL DEFAULT 'EA',
    material         VARCHAR(128),
    make_or_buy      VARCHAR(8) NOT NULL DEFAULT 'Make',
    specifications   JSONB DEFAULT '{}',
    sort_order       INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT chk_bom_type CHECK (bom_type IN ('EBOM','MBOM','SBOM'))
);

-- =====================================================
-- V502.5: EBOM change records table
-- =====================================================
CREATE TABLE IF NOT EXISTS ebom_change_records (
    change_id        VARCHAR(64) PRIMARY KEY,
    ebom_id          VARCHAR(64) NOT NULL REFERENCES ebom_records(bom_id),
    change_type      VARCHAR(32) NOT NULL,
    affected_node_id VARCHAR(64),
    new_values       JSONB NOT NULL,
    reason           TEXT NOT NULL,
    requested_by     VARCHAR(128) NOT NULL,
    propagation_result JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- V502.6: Process plans table
-- =====================================================
CREATE TABLE IF NOT EXISTS process_plans (
    plan_id          VARCHAR(64) PRIMARY KEY,
    mbom_id          VARCHAR(64) NOT NULL REFERENCES mbom_records(bom_id),
    version          INTEGER NOT NULL DEFAULT 1,
    total_lead_time_hours DOUBLE PRECISION,
    resource_requirements JSONB DEFAULT '{}',
    status           VARCHAR(16) NOT NULL DEFAULT 'Draft',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_plan_status CHECK (status IN ('Draft','Validated','Optimized','Released'))
);

-- =====================================================
-- V502.7: Manufacturing operations table
-- =====================================================
CREATE TABLE IF NOT EXISTS manufacturing_operations (
    operation_id     VARCHAR(64) PRIMARY KEY,
    plan_id          VARCHAR(64) NOT NULL REFERENCES process_plans(plan_id),
    operation_type   VARCHAR(32) NOT NULL,
    sequence_number  INTEGER NOT NULL,
    part_number      VARCHAR(128) NOT NULL,
    description      TEXT NOT NULL,
    estimated_time_hours DOUBLE PRECISION NOT NULL CHECK (estimated_time_hours > 0),
    resource_assignments JSONB DEFAULT '{}',
    predecessor_ids  VARCHAR(64)[] DEFAULT '{}',
    quality_gates    VARCHAR(64)[] DEFAULT '{}'
);

-- =====================================================
-- V502.8: FRACAS failure reports table
-- =====================================================
CREATE TABLE IF NOT EXISTS fracas_failure_reports (
    report_id        VARCHAR(64) PRIMARY KEY,
    failure_date     TIMESTAMPTZ NOT NULL,
    component_part_number VARCHAR(128) NOT NULL,
    failure_mode     VARCHAR(256) NOT NULL,
    failure_effect   TEXT,
    severity         VARCHAR(16) NOT NULL,
    aircraft_tail_number VARCHAR(16),
    flight_hours_at_failure DOUBLE PRECISION,
    root_cause       TEXT,
    corrective_action TEXT,
    verification_status VARCHAR(16) NOT NULL DEFAULT 'Pending',
    airworthiness_clause VARCHAR(32),
    locked           BOOLEAN NOT NULL DEFAULT FALSE,
    causal_graph_ref VARCHAR(128),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_severity CHECK (severity IN ('Critical','Major','Minor')),
    CONSTRAINT chk_verification CHECK (verification_status IN ('Pending','Verified','NotEffective'))
);

-- =====================================================
-- V502.9: Feedback loop instances table
-- =====================================================
CREATE TABLE IF NOT EXISTS feedback_loop_instances (
    instance_id      VARCHAR(64) PRIMARY KEY,
    trigger_type     VARCHAR(32) NOT NULL,
    trigger_data     JSONB NOT NULL,
    current_stage    VARCHAR(32) NOT NULL,
    stage_history    JSONB DEFAULT '[]',
    design_update    JSONB,
    cae_rerun_result JSONB,
    bom_update_result JSONB,
    mes_update_result JSONB,
    status           VARCHAR(16) NOT NULL DEFAULT 'Running',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMPTZ,
    CONSTRAINT chk_fbl_status CHECK (status IN ('Running','Paused','Completed','Failed'))
);

-- =====================================================
-- V502.10: Design feedback tickets table
-- =====================================================
CREATE TABLE IF NOT EXISTS design_feedback_tickets (
    ticket_id        VARCHAR(64) PRIMARY KEY,
    trend_id         VARCHAR(64) NOT NULL,
    component_type   VARCHAR(64) NOT NULL,
    trend_direction  VARCHAR(32) NOT NULL,
    statistical_significance DOUBLE PRECISION,
    affected_aircraft_count INTEGER NOT NULL DEFAULT 0,
    operational_data_summary JSONB NOT NULL,
    potential_design_improvement TEXT,
    design_update_reference VARCHAR(64),
    status           VARCHAR(16) NOT NULL DEFAULT 'Open',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at      TIMESTAMPTZ,
    CONSTRAINT chk_dft_status CHECK (status IN ('Open','InReview','DesignUpdated','Verified','Closed'))
);

-- =====================================================
-- V502.11: Fleet schedules table
-- =====================================================
CREATE TABLE IF NOT EXISTS fleet_schedules (
    schedule_id      VARCHAR(64) PRIMARY KEY,
    aircraft_assignments JSONB NOT NULL,
    maintenance_windows JSONB NOT NULL DEFAULT '[]',
    total_operational_aircraft INTEGER NOT NULL DEFAULT 0,
    constraint_violations JSONB DEFAULT '[]',
    optimization_score DOUBLE PRECISION,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- V502.12: Indexes
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_bom_node_bom ON bom_nodes (bom_id, bom_type);
CREATE INDEX IF NOT EXISTS idx_bom_node_parent ON bom_nodes (parent_node_id);
CREATE INDEX IF NOT EXISTS idx_bom_node_part ON bom_nodes (part_number);
CREATE INDEX IF NOT EXISTS idx_ebom_change ON ebom_change_records (ebom_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mfg_op_plan ON manufacturing_operations (plan_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_fracas_severity ON fracas_failure_reports (severity, failure_date DESC);
CREATE INDEX IF NOT EXISTS idx_fracas_component ON fracas_failure_reports (component_part_number);
CREATE INDEX IF NOT EXISTS idx_fracas_airworthiness ON fracas_failure_reports (airworthiness_clause) WHERE airworthiness_clause IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fbl_status ON feedback_loop_instances (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dft_status ON design_feedback_tickets (status, component_type);

COMMIT;