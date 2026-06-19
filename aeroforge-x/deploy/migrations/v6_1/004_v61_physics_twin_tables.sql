-- AeroForge-X V6.1 Physics Twin Database Migration
-- Dataset Governance + PHM Model Confidence tables
-- REQ-DG-001~013, REQ-MC-001~009

BEGIN;

-- Dataset version management (REQ-DG-001~004)
CREATE TABLE IF NOT EXISTS physics_twin.dataset_versions (
    dataset_version_id VARCHAR(64) PRIMARY KEY,
    dataset_id VARCHAR(64) NOT NULL,
    major INT NOT NULL DEFAULT 1,
    minor INT NOT NULL DEFAULT 0,
    patch INT NOT NULL DEFAULT 0,
    source VARCHAR(256) NOT NULL DEFAULT '',
    sample_count INT NOT NULL DEFAULT 0,
    feature_schema JSONB NOT NULL DEFAULT '{}',
    change_summary TEXT NOT NULL DEFAULT '',
    fingerprint JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(dataset_id, major, minor, patch)
);

CREATE TABLE IF NOT EXISTS physics_twin.model_dataset_links (
    link_id VARCHAR(64) PRIMARY KEY,
    model_id VARCHAR(64) NOT NULL,
    dataset_version_id VARCHAR(64) NOT NULL REFERENCES physics_twin.dataset_versions(dataset_version_id),
    linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(model_id, dataset_version_id)
);

-- Dataset drift detection (REQ-DG-005~009)
CREATE TABLE IF NOT EXISTS physics_twin.dataset_drift_records (
    drift_id VARCHAR(64) PRIMARY KEY,
    dataset_id VARCHAR(64) NOT NULL,
    reference_dataset_id VARCHAR(64) NOT NULL,
    drift_type VARCHAR(32) NOT NULL DEFAULT 'Feature',
    ks_statistic DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    ks_p_value DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    psi_value DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    concept_drift_magnitude DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    is_drift_detected BOOLEAN NOT NULL DEFAULT FALSE,
    affected_features TEXT[] NOT NULL DEFAULT '{}',
    recommended_action TEXT NOT NULL DEFAULT '',
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Dataset quality scoring (REQ-DG-010~013)
CREATE TABLE IF NOT EXISTS physics_twin.dataset_quality_assessments (
    assessment_id VARCHAR(64) PRIMARY KEY,
    dataset_id VARCHAR(64) NOT NULL,
    overall_score DOUBLE PRECISION NOT NULL DEFAULT 0.0 CHECK (overall_score >= 0 AND overall_score <= 100),
    completeness_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    consistency_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    timeliness_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    representativeness_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    improvement_recommendations TEXT NOT NULL DEFAULT '',
    assessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- PHM model confidence (REQ-MC-001~004)
CREATE TABLE IF NOT EXISTS physics_twin.phm_confidence_predictions (
    prediction_id VARCHAR(64) PRIMARY KEY,
    component_id VARCHAR(64) NOT NULL,
    rul_point_estimate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    confidence_lower DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    confidence_upper DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    data_quality_score DOUBLE PRECISION NOT NULL DEFAULT 100.0 CHECK (data_quality_score >= 0 AND data_quality_score <= 100),
    is_low_confidence BOOLEAN NOT NULL DEFAULT FALSE,
    confidence_level DOUBLE PRECISION NOT NULL DEFAULT 0.95,
    predicted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Maintenance decision audit (REQ-MC-005~007)
CREATE TABLE IF NOT EXISTS physics_twin.maintenance_decision_audits (
    audit_id VARCHAR(64) PRIMARY KEY,
    prediction_id VARCHAR(64) NOT NULL,
    rul_point_estimate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    confidence_lower DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    confidence_upper DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    data_quality_score DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    decision_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    decision_outcome VARCHAR(64) NOT NULL DEFAULT '',
    engineer_approval VARCHAR(128) NOT NULL DEFAULT '',
    review_required BOOLEAN NOT NULL DEFAULT FALSE,
    review_decision VARCHAR(64) NOT NULL DEFAULT '',
    reviewer VARCHAR(128) NOT NULL DEFAULT '',
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_dv_dataset ON physics_twin.dataset_versions(dataset_id);
CREATE INDEX IF NOT EXISTS idx_mdl_model ON physics_twin.model_dataset_links(model_id);
CREATE INDEX IF NOT EXISTS idx_ddr_dataset ON physics_twin.dataset_drift_records(dataset_id);
CREATE INDEX IF NOT EXISTS idx_dqa_dataset ON physics_twin.dataset_quality_assessments(dataset_id);
CREATE INDEX IF NOT EXISTS idx_pcp_component ON physics_twin.phm_confidence_predictions(component_id);
CREATE INDEX IF NOT EXISTS idx_mda_prediction ON physics_twin.maintenance_decision_audits(prediction_id);

COMMIT;