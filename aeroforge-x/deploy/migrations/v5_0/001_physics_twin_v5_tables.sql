-- AeroForge-X v5.0 Physics Twin Service Database Migration
-- Generative Aircraft Design + Fleet Intelligence tables
-- REQ-DES-001~032, REQ-FLT-001~025

BEGIN;

-- =====================================================
-- V501.1: Design requirements table
-- =====================================================
CREATE TABLE IF NOT EXISTS design_requirements (
    requirement_id   VARCHAR(64) PRIMARY KEY,
    project_id       VARCHAR(64) NOT NULL,
    version          INTEGER NOT NULL DEFAULT 1,
    requirement_text TEXT NOT NULL,
    range_km         DOUBLE PRECISION,
    payload_kg       DOUBLE PRECISION,
    cruise_speed_kmh DOUBLE PRECISION,
    ceiling_m        DOUBLE PRECISION,
    cost_target      DOUBLE PRECISION,
    constraints      JSONB DEFAULT '[]',
    objective_functions JSONB DEFAULT '[]',
    feasibility_status VARCHAR(16) NOT NULL DEFAULT 'Pending',
    conflict_report  JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_feasibility CHECK (feasibility_status IN ('Pending','Feasible','Infeasible','Partial')),
    CONSTRAINT uq_req_version UNIQUE (project_id, version)
);

-- =====================================================
-- V501.2: Parametric geometry table
-- =====================================================
CREATE TABLE IF NOT EXISTS aircraft_geometries (
    geometry_id      VARCHAR(64) PRIMARY KEY,
    requirement_id   VARCHAR(64) REFERENCES design_requirements(requirement_id),
    wing_span        DOUBLE PRECISION NOT NULL CHECK (wing_span > 0 AND wing_span <= 200),
    wing_area        DOUBLE PRECISION NOT NULL CHECK (wing_area > 0 AND wing_area <= 1000),
    wing_aspect_ratio DOUBLE PRECISION NOT NULL CHECK (wing_aspect_ratio > 0 AND wing_aspect_ratio <= 50),
    wing_sweep_angle DOUBLE PRECISION NOT NULL CHECK (wing_sweep_angle >= 0 AND wing_sweep_angle <= 70),
    wing_taper_ratio DOUBLE PRECISION NOT NULL CHECK (wing_taper_ratio > 0 AND wing_taper_ratio <= 1),
    fuselage_length  DOUBLE PRECISION NOT NULL CHECK (fuselage_length > 0 AND fuselage_length <= 150),
    fuselage_diameter DOUBLE PRECISION NOT NULL CHECK (fuselage_diameter > 0 AND fuselage_diameter <= 15),
    horizontal_tail_area DOUBLE PRECISION CHECK (horizontal_tail_area > 0),
    vertical_tail_area DOUBLE PRECISION CHECK (vertical_tail_area > 0),
    engine_count     INTEGER NOT NULL CHECK (engine_count BETWEEN 1 AND 8),
    engine_thrust    DOUBLE PRECISION NOT NULL CHECK (engine_thrust > 0),
    topology_hash    VARCHAR(64) NOT NULL,
    export_formats   VARCHAR(32)[] NOT NULL DEFAULT '{"STEP","IGES","OpenVSP"}',
    minio_ref        VARCHAR(512) NOT NULL,
    manufacturing_check JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- V501.3: CFD surrogate model metadata table
-- =====================================================
CREATE TABLE IF NOT EXISTS cfd_surrogate_model_metadata (
    model_id         VARCHAR(64) PRIMARY KEY,
    architecture     VARCHAR(32) NOT NULL,
    input_dimensions VARCHAR(32)[] NOT NULL DEFAULT '{"alpha","beta","mach","reynolds"}',
    output_dimensions VARCHAR(32)[] NOT NULL DEFAULT '{"CL","CD","CM","CY","Cl","Cn"}',
    training_dataset_ref VARCHAR(512) NOT NULL,
    model_weights_ref VARCHAR(512) NOT NULL,
    quality_status   VARCHAR(32) NOT NULL DEFAULT 'Training',
    r_squared        DOUBLE PRECISION,
    rmse             JSONB,
    prediction_interval_coverage DOUBLE PRECISION,
    test_set_size    INTEGER,
    last_validated_at TIMESTAMPTZ,
    is_active        BOOLEAN NOT NULL DEFAULT FALSE,
    confidence_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.85,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_surrogate_quality CHECK (quality_status IN ('Training','Validated','Deprecated'))
);

-- =====================================================
-- V501.4: MDO optimization run table
-- =====================================================
CREATE TABLE IF NOT EXISTS mdo_runs (
    run_id           VARCHAR(64) PRIMARY KEY,
    requirement_id   VARCHAR(64) NOT NULL REFERENCES design_requirements(requirement_id),
    objectives       JSONB NOT NULL,
    constraints_config JSONB NOT NULL,
    design_variables JSONB NOT NULL,
    population_size  INTEGER NOT NULL DEFAULT 100,
    max_generations  INTEGER NOT NULL DEFAULT 200,
    convergence_status VARCHAR(32) NOT NULL DEFAULT 'Running',
    best_solution_id VARCHAR(64),
    total_evaluated  INTEGER DEFAULT 0,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMPTZ,
    CONSTRAINT chk_mdo_status CHECK (convergence_status IN ('Running','Converged','MaxIterations','Failed'))
);

-- =====================================================
-- V501.5: MDO design solutions table
-- =====================================================
CREATE TABLE IF NOT EXISTS mdo_design_solutions (
    solution_id      VARCHAR(64) PRIMARY KEY,
    run_id           VARCHAR(64) NOT NULL REFERENCES mdo_runs(run_id),
    design_parameters JSONB NOT NULL,
    objective_values JSONB NOT NULL,
    constraint_violations JSONB DEFAULT '[]',
    is_pareto_optimal BOOLEAN NOT NULL DEFAULT FALSE,
    generation       INTEGER NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- V501.6: Aircraft configurations table
-- =====================================================
CREATE TABLE IF NOT EXISTS aircraft_configurations (
    configuration_id VARCHAR(64) PRIMARY KEY,
    geometry_id      VARCHAR(64) NOT NULL REFERENCES aircraft_geometries(geometry_id),
    requirement_id   VARCHAR(64) REFERENCES design_requirements(requirement_id),
    suggestion_id    VARCHAR(64),
    structure_params JSONB NOT NULL DEFAULT '{}',
    propulsion_params JSONB NOT NULL DEFAULT '{}',
    control_params   JSONB NOT NULL DEFAULT '{}',
    overall_score    DOUBLE PRECISION,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- V501.7: Design exploration history table
-- =====================================================
CREATE TABLE IF NOT EXISTS design_exploration_history (
    step_id          VARCHAR(64) PRIMARY KEY,
    requirement_id   VARCHAR(64) NOT NULL,
    action_type      VARCHAR(32) NOT NULL,
    action_params    JSONB NOT NULL,
    result_snapshot  JSONB NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- V501.8: Fleet aircraft registry table
-- =====================================================
CREATE TABLE IF NOT EXISTS fleet_aircraft_registry (
    aircraft_id      VARCHAR(64) PRIMARY KEY,
    tail_number      VARCHAR(16) NOT NULL,
    aircraft_type    VARCHAR(64) NOT NULL,
    operator         VARCHAR(128) NOT NULL,
    region           VARCHAR(64) NOT NULL,
    age_years        DOUBLE PRECISION NOT NULL CHECK (age_years >= 0),
    mission_profile  VARCHAR(64) NOT NULL,
    twin_instance_id VARCHAR(64) NOT NULL,
    registration_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tail_number UNIQUE (tail_number)
);

-- =====================================================
-- V501.9: PHM RUL model registry table
-- =====================================================
CREATE TABLE IF NOT EXISTS phm_rul_model_registry (
    model_id         VARCHAR(64) PRIMARY KEY,
    component_type   VARCHAR(32) NOT NULL,
    model_type       VARCHAR(32) NOT NULL,
    input_features   VARCHAR(128)[] NOT NULL,
    prediction_horizon_hours DOUBLE PRECISION NOT NULL,
    accuracy_metrics JSONB DEFAULT '{}',
    min_confidence_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.7,
    is_active        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_rul_model_type CHECK (model_type IN ('PhysicsBased','DataDriven','Hybrid'))
);

-- =====================================================
-- V501.10: Indexes
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_design_req_project ON design_requirements (project_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_geometry_requirement ON aircraft_geometries (requirement_id);
CREATE INDEX IF NOT EXISTS idx_surrogate_active ON cfd_surrogate_model_metadata (is_active, quality_status);
CREATE INDEX IF NOT EXISTS idx_mdo_req ON mdo_runs (requirement_id);
CREATE INDEX IF NOT EXISTS idx_solution_run ON mdo_design_solutions (run_id, is_pareto_optimal);
CREATE INDEX IF NOT EXISTS idx_config_geometry ON aircraft_configurations (geometry_id);
CREATE INDEX IF NOT EXISTS idx_exploration_req ON design_exploration_history (requirement_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_fleet_type ON fleet_aircraft_registry (aircraft_type);
CREATE INDEX IF NOT EXISTS idx_fleet_operator ON fleet_aircraft_registry (operator, region);
CREATE INDEX IF NOT EXISTS idx_rul_active ON phm_rul_model_registry (component_type, is_active);

COMMIT;