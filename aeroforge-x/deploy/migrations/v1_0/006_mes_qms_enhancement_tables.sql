-- ============================================================
-- AeroForge-X v1.0 MES/QMS Enhancement Database Migration
-- Tables: traveler_records, traveler_temperature_profiles,
--         ndt_inspections, ndt_result_images,
--         tool_calibrations, tool_calibration_history,
--         fmea_analyses, fmea_failure_modes,
--         fracas_records, fracas_corrective_actions,
--         reliability_predictions, life_predictions
-- ============================================================

-- Traveler Records
CREATE TABLE IF NOT EXISTS traveler_records (
    traveler_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_order_id     UUID NOT NULL,
    serial_number     VARCHAR(128) NOT NULL,
    process_step      VARCHAR(128) NOT NULL,
    operator_id       UUID,
    curing_oven       VARCHAR(128),
    quality_inspector UUID,
    confirmed_at      TIMESTAMPTZ,
    finalized_at      TIMESTAMPTZ,
    status            VARCHAR(32) NOT NULL DEFAULT 'in_progress',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_traveler_status CHECK (status IN (
        'in_progress', 'confirmed', 'finalized', 'non_conforming'
    ))
);

CREATE INDEX idx_traveler_work_order ON traveler_records(work_order_id);
CREATE INDEX idx_traveler_serial ON traveler_records(serial_number);
CREATE INDEX idx_traveler_status ON traveler_records(status);

-- Traveler Temperature Profiles
CREATE TABLE IF NOT EXISTS traveler_temperature_profiles (
    profile_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    traveler_id       UUID NOT NULL REFERENCES traveler_records(traveler_id) ON DELETE CASCADE,
    timestamp         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    temperature_c     NUMERIC(8,2) NOT NULL,
    target_temp_c     NUMERIC(8,2),
    deviation_c       NUMERIC(8,2),
    is_within_tolerance BOOLEAN DEFAULT TRUE,
    duration_s        NUMERIC(10,1)
);

CREATE INDEX idx_temp_profile_traveler ON traveler_temperature_profiles(traveler_id);
CREATE INDEX idx_temp_profile_deviation ON traveler_temperature_profiles(is_within_tolerance);

-- NDT Inspections
CREATE TABLE IF NOT EXISTS ndt_inspections (
    inspection_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    serial_number     VARCHAR(128) NOT NULL,
    traveler_ref      UUID REFERENCES traveler_records(traveler_id),
    inspection_method VARCHAR(32) NOT NULL,
    result            VARCHAR(32) NOT NULL DEFAULT 'pending',
    defect_description TEXT,
    inspector_id      UUID,
    inspector_level   INTEGER DEFAULT 1,
    reviewed_by       UUID,
    reviewed_at       TIMESTAMPTZ,
    tool_calibration_ref UUID,
    status            VARCHAR(32) NOT NULL DEFAULT 'planned',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_ndt_method CHECK (inspection_method IN (
        'ultrasonic', 'x_ray', 'thermal_imaging', 'eddy_current', 'penetrant', 'magnetic_particle'
    )),
    CONSTRAINT chk_ndt_result CHECK (result IN (
        'pending', 'acceptable', 'marginal', 'unacceptable'
    )),
    CONSTRAINT chk_ndt_status CHECK (status IN (
        'planned', 'in_progress', 'completed', 'reviewed', 'rejected'
    ))
);

CREATE INDEX idx_ndt_serial ON ndt_inspections(serial_number);
CREATE INDEX idx_ndt_traveler ON ndt_inspections(traveler_ref);
CREATE INDEX idx_ndt_result ON ndt_inspections(result);

-- NDT Result Images
CREATE TABLE IF NOT EXISTS ndt_result_images (
    image_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    inspection_id     UUID NOT NULL REFERENCES ndt_inspections(inspection_id) ON DELETE CASCADE,
    image_type        VARCHAR(32) NOT NULL DEFAULT 'c_scan',
    file_path         VARCHAR(512) NOT NULL,
    annotations       JSONB DEFAULT '[]',
    uploaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_image_type CHECK (image_type IN (
        'c_scan', 'b_scan', 'x_ray', 'thermal', 'photograph'
    ))
);

CREATE INDEX idx_ndt_images_inspection ON ndt_result_images(inspection_id);

-- Tool Calibrations
CREATE TABLE IF NOT EXISTS tool_calibrations (
    calibration_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tool_id           VARCHAR(128) NOT NULL,
    tool_name         VARCHAR(256) NOT NULL,
    calibration_date  DATE NOT NULL,
    next_due_date     DATE NOT NULL,
    result            VARCHAR(32) NOT NULL DEFAULT 'pass',
    uncertainty       NUMERIC(10,6),
    certificate_ref   VARCHAR(256),
    calibrated_by     UUID,
    status            VARCHAR(32) NOT NULL DEFAULT 'current',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_cal_result CHECK (result IN ('pass', 'fail', 'conditional')),
    CONSTRAINT chk_cal_status CHECK (status IN ('current', 'expiring_soon', 'expired', 'invalid'))
);

CREATE INDEX idx_tool_cal_tool ON tool_calibrations(tool_id);
CREATE INDEX idx_tool_cal_status ON tool_calibrations(status);
CREATE INDEX idx_tool_cal_due ON tool_calibrations(next_due_date);

-- Tool Calibration History
CREATE TABLE IF NOT EXISTS tool_calibration_history (
    history_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    calibration_id    UUID NOT NULL REFERENCES tool_calibrations(calibration_id) ON DELETE CASCADE,
    action            VARCHAR(64) NOT NULL,
    previous_status   VARCHAR(32),
    new_status        VARCHAR(32),
    performed_by      UUID,
    notes             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cal_history_calibration ON tool_calibration_history(calibration_id);

-- FMEA Analyses
CREATE TABLE IF NOT EXISTS fmea_analyses (
    analysis_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fmea_type         VARCHAR(16) NOT NULL,
    component_id      UUID,
    component_name    VARCHAR(256),
    highest_rpn       INTEGER DEFAULT 0,
    status            VARCHAR(32) NOT NULL DEFAULT 'in_progress',
    created_by        UUID,
    completed_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_fmea_type CHECK (fmea_type IN ('dfmea', 'pfmea')),
    CONSTRAINT chk_fmea_status CHECK (status IN ('in_progress', 'completed', 'reviewed'))
);

CREATE INDEX idx_fmea_type ON fmea_analyses(fmea_type);
CREATE INDEX idx_fmea_status ON fmea_analyses(status);

-- FMEA Failure Modes
CREATE TABLE IF NOT EXISTS fmea_failure_modes (
    mode_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id       UUID NOT NULL REFERENCES fmea_analyses(analysis_id) ON DELETE CASCADE,
    failure_description TEXT NOT NULL,
    severity          INTEGER NOT NULL DEFAULT 5,
    occurrence        INTEGER NOT NULL DEFAULT 5,
    detection         INTEGER NOT NULL DEFAULT 5,
    rpn               INTEGER NOT NULL DEFAULT 125,
    is_safety_critical BOOLEAN DEFAULT FALSE,
    corrective_actions JSONB DEFAULT '[]',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_severity CHECK (severity BETWEEN 1 AND 10),
    CONSTRAINT chk_occurrence CHECK (occurrence BETWEEN 1 AND 10),
    CONSTRAINT chk_detection CHECK (detection BETWEEN 1 AND 10),
    CONSTRAINT chk_rpn CHECK (rpn >= 1 AND rpn <= 1000)
);

CREATE INDEX idx_failure_mode_analysis ON fmea_failure_modes(analysis_id);
CREATE INDEX idx_failure_mode_rpn ON fmea_failure_modes(rpn DESC);
CREATE INDEX idx_failure_mode_critical ON fmea_failure_modes(is_safety_critical);

-- FRACAS Records
CREATE TABLE IF NOT EXISTS fracas_records (
    record_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    failure_description TEXT NOT NULL,
    affected_component VARCHAR(256),
    serial_number     VARCHAR(128),
    failure_mode      VARCHAR(128),
    detection_method  VARCHAR(64),
    root_cause        TEXT,
    is_safety_critical BOOLEAN DEFAULT FALSE,
    status            VARCHAR(32) NOT NULL DEFAULT 'reported',
    reported_by       UUID,
    assigned_to       UUID,
    closed_at         TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_fracas_status CHECK (status IN (
        'reported', 'investigating', 'root_cause_identified',
        'corrective_action_planned', 'corrective_action_implemented',
        'verified', 'closed'
    ))
);

CREATE INDEX idx_fracas_serial ON fracas_records(serial_number);
CREATE INDEX idx_fracas_status ON fracas_records(status);
CREATE INDEX idx_fracas_critical ON fracas_records(is_safety_critical);

-- FRACAS Corrective Actions
CREATE TABLE IF NOT EXISTS fracas_corrective_actions (
    action_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    record_id         UUID NOT NULL REFERENCES fracas_records(record_id) ON DELETE CASCADE,
    action_description TEXT NOT NULL,
    responsible       UUID,
    due_date          DATE,
    implemented_at    TIMESTAMPTZ,
    verified_at       TIMESTAMPTZ,
    verified_by       UUID,
    effectiveness     VARCHAR(16),
    status            VARCHAR(32) NOT NULL DEFAULT 'planned',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_action_effectiveness CHECK (effectiveness IS NULL OR effectiveness IN (
        'effective', 'partially_effective', 'ineffective'
    )),
    CONSTRAINT chk_action_status CHECK (status IN (
        'planned', 'in_progress', 'implemented', 'verified', 'ineffective'
    ))
);

CREATE INDEX idx_corrective_action_record ON fracas_corrective_actions(record_id);

-- Reliability Predictions
CREATE TABLE IF NOT EXISTS reliability_predictions (
    prediction_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component_id      UUID NOT NULL,
    component_name    VARCHAR(256),
    mtbf_hours        NUMERIC(14,2),
    failure_rate_per_million_hours NUMERIC(10,6),
    confidence_level  NUMERIC(3,2) DEFAULT 0.90,
    confidence_interval_hours JSONB DEFAULT '{}',
    data_sources      JSONB DEFAULT '[]',
    status            VARCHAR(32) NOT NULL DEFAULT 'predicted',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_reliability_status CHECK (status IN ('predicted', 'validated', 'updated'))
);

CREATE INDEX idx_reliability_component ON reliability_predictions(component_id);

-- Life Predictions
CREATE TABLE IF NOT EXISTS life_predictions (
    prediction_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component_id      UUID NOT NULL,
    serial_number     VARCHAR(128),
    remaining_useful_life_hours NUMERIC(14,2),
    total_life_hours  NUMERIC(14,2),
    warning_threshold_hours NUMERIC(14,2) DEFAULT 100,
    consumption_pct   NUMERIC(5,2),
    maintenance_suggestion TEXT,
    status            VARCHAR(32) NOT NULL DEFAULT 'active',
    predicted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_life_status CHECK (status IN ('active', 'warning', 'critical', 'replaced'))
);

CREATE INDEX idx_life_component ON life_predictions(component_id);
CREATE INDEX idx_life_serial ON life_predictions(serial_number);
CREATE INDEX idx_life_status ON life_predictions(status);