-- AeroForge-X v4.0 Aircraft Core Service Database Migration
-- Test Evidence Center tables: test results, coverage records, benchmark records, evidence traceability

BEGIN;

-- V402.1: Test results table
CREATE TABLE IF NOT EXISTS test_results (
    test_result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_case_id VARCHAR(500) NOT NULL,
    execution_status VARCHAR(50) NOT NULL DEFAULT 'unknown',
    execution_duration_ms FLOAT,
    code_version VARCHAR(100),
    environment VARCHAR(100),
    service_id VARCHAR(255) NOT NULL,
    module_name VARCHAR(255),
    result_data JSONB DEFAULT '{}',
    evidence_locked BOOLEAN NOT NULL DEFAULT FALSE,
    checksum VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- V402.2: Coverage records table
CREATE TABLE IF NOT EXISTS coverage_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id VARCHAR(255) NOT NULL,
    code_version VARCHAR(100) NOT NULL,
    line_coverage FLOAT NOT NULL DEFAULT 0.0,
    branch_coverage FLOAT NOT NULL DEFAULT 0.0,
    function_coverage FLOAT NOT NULL DEFAULT 0.0,
    module_coverages JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- V402.3: Benchmark records table
CREATE TABLE IF NOT EXISTS benchmark_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kpi_name VARCHAR(255) NOT NULL,
    kpi_value FLOAT NOT NULL,
    kpi_unit VARCHAR(50) NOT NULL DEFAULT 'ms',
    code_version VARCHAR(100) NOT NULL,
    environment VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- V402.4: Coverage targets table
CREATE TABLE IF NOT EXISTS coverage_targets (
    target_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope VARCHAR(50) NOT NULL DEFAULT 'service',
    scope_name VARCHAR(255) NOT NULL,
    criticality VARCHAR(50) NOT NULL DEFAULT 'normal',
    line_coverage_target FLOAT NOT NULL DEFAULT 0.8,
    branch_coverage_target FLOAT NOT NULL DEFAULT 0.7,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- V402.5: Evidence traceability links table
CREATE TABLE IF NOT EXISTS evidence_traceability_links (
    link_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_case_id VARCHAR(500) NOT NULL,
    test_result_id UUID REFERENCES test_results(test_result_id),
    airworthiness_clause VARCHAR(100) NOT NULL,
    compliance_method VARCHAR(100),
    verification_evidence_id VARCHAR(500),
    link_status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- V402.6: Benchmark targets table
CREATE TABLE IF NOT EXISTS benchmark_targets (
    target_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kpi_name VARCHAR(255) NOT NULL,
    service_criticality VARCHAR(50) NOT NULL DEFAULT 'normal',
    target_value FLOAT NOT NULL,
    regression_threshold_pct FLOAT NOT NULL DEFAULT 20.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- V402.7: Indexes
CREATE INDEX IF NOT EXISTS idx_test_results_case ON test_results(test_case_id);
CREATE INDEX IF NOT EXISTS idx_test_results_version ON test_results(code_version);
CREATE INDEX IF NOT EXISTS idx_test_results_service ON test_results(service_id);
CREATE INDEX IF NOT EXISTS idx_coverage_service ON coverage_records(service_id, code_version);
CREATE INDEX IF NOT EXISTS idx_benchmark_kpi ON benchmark_records(kpi_name, code_version);
CREATE INDEX IF NOT EXISTS idx_evidence_link_clause ON evidence_traceability_links(airworthiness_clause);
CREATE INDEX IF NOT EXISTS idx_evidence_link_case ON evidence_traceability_links(test_case_id);
CREATE INDEX IF NOT EXISTS idx_evidence_link_result ON evidence_traceability_links(test_result_id);

COMMIT;