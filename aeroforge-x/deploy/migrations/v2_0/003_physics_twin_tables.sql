-- AeroForge-X v2.0 Physics Twin Core Schema
-- 关联需求：REQ-PTC-001 ~ REQ-PTC-042

CREATE SCHEMA IF NOT EXISTS physics_twin;

CREATE TABLE physics_twin.physics_models (
    model_id            VARCHAR(64) PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    model_type          VARCHAR(32) NOT NULL,
    hierarchy_level     VARCHAR(32) NOT NULL,
    fidelity_level      VARCHAR(32) NOT NULL,
    aircraft_object_id  VARCHAR(64) NOT NULL,
    parameter_mappings  JSONB DEFAULT '[]',
    geometry_ref        VARCHAR(256),
    status              VARCHAR(32) NOT NULL DEFAULT 'Draft',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_model_type CHECK (model_type IN ('FEA','CFD','Thermodynamics','MultiBodyDynamics','Electromagnetics')),
    CONSTRAINT chk_hierarchy CHECK (hierarchy_level IN ('FullAircraft','System','Component','Detail')),
    CONSTRAINT chk_fidelity CHECK (fidelity_level IN ('Low','Mid','High')),
    CONSTRAINT chk_model_status CHECK (status IN ('Draft','Validated','Deployed','Deprecated'))
);

CREATE INDEX idx_models_type ON physics_twin.physics_models (model_type, fidelity_level);
CREATE INDEX idx_models_object ON physics_twin.physics_models (aircraft_object_id);
CREATE INDEX idx_models_status ON physics_twin.physics_models (status);

CREATE TABLE physics_twin.physics_simulations (
    simulation_id       VARCHAR(64) PRIMARY KEY,
    model_id            VARCHAR(64) NOT NULL REFERENCES physics_twin.physics_models(model_id),
    solver_type         VARCHAR(32) NOT NULL,
    config              JSONB DEFAULT '{}',
    boundary_conditions JSONB DEFAULT '{}',
    status              VARCHAR(32) NOT NULL DEFAULT 'Queued',
    field_data_ref      VARCHAR(512),
    scalar_results      JSONB DEFAULT '{}',
    convergence_history JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    CONSTRAINT chk_solver_type CHECK (solver_type IN ('OpenFOAM','FEniCS','Custom')),
    CONSTRAINT chk_sim_status CHECK (status IN ('Queued','Running','Completed','Failed'))
);

CREATE INDEX idx_simulations_model ON physics_twin.physics_simulations (model_id);
CREATE INDEX idx_simulations_status ON physics_twin.physics_simulations (status);

CREATE TABLE physics_twin.reduced_order_models (
    rom_id              VARCHAR(64) PRIMARY KEY,
    source_model_id     VARCHAR(64) NOT NULL REFERENCES physics_twin.physics_models(model_id),
    reduction_method    VARCHAR(32) NOT NULL,
    accuracy            FLOAT,
    validation_error    FLOAT,
    validation_status   VARCHAR(32) NOT NULL DEFAULT 'Pending',
    deployment_status   VARCHAR(32) NOT NULL DEFAULT 'NotDeployed',
    deployed_ref        VARCHAR(256),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_reduction_method CHECK (reduction_method IN ('POD','SVD','NeuralNetwork')),
    CONSTRAINT chk_validation_status CHECK (validation_status IN ('Pending','Passed','Failed')),
    CONSTRAINT chk_deployment_status CHECK (deployment_status IN ('NotDeployed','Deployed','Deprecated'))
);

CREATE INDEX idx_rom_source ON physics_twin.reduced_order_models (source_model_id);
CREATE INDEX idx_rom_validation ON physics_twin.reduced_order_models (validation_status);

CREATE TABLE physics_twin.twin_runtimes (
    runtime_id              VARCHAR(64) PRIMARY KEY,
    aircraft_object_id      VARCHAR(64) NOT NULL,
    active_models           JSONB DEFAULT '[]',
    active_fidelity         VARCHAR(32) NOT NULL DEFAULT 'Low',
    current_state           JSONB DEFAULT '{}',
    health_indicators       JSONB DEFAULT '{}',
    rul_predictions         JSONB DEFAULT '[]',
    data_lagged             BOOLEAN NOT NULL DEFAULT FALSE,
    last_sensor_timestamp   TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_active_fidelity CHECK (active_fidelity IN ('Low','Mid','High'))
);

CREATE INDEX idx_runtimes_object ON physics_twin.twin_runtimes (aircraft_object_id);
CREATE INDEX idx_runtimes_lagged ON physics_twin.twin_runtimes (data_lagged) WHERE data_lagged = TRUE;

CREATE TABLE physics_twin.twin_calibrations (
    calibration_id          VARCHAR(64) PRIMARY KEY,
    runtime_id              VARCHAR(64) NOT NULL REFERENCES physics_twin.twin_runtimes(runtime_id),
    model_id                VARCHAR(64) NOT NULL REFERENCES physics_twin.physics_models(model_id),
    parameter_adjustments   JSONB DEFAULT '{}',
    validation_results      JSONB DEFAULT '{}',
    status                  VARCHAR(32) NOT NULL DEFAULT 'Pending',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    CONSTRAINT chk_cal_status CHECK (status IN ('Pending','InProgress','Completed','Failed'))
);

CREATE INDEX idx_calibrations_runtime ON physics_twin.twin_calibrations (runtime_id);
CREATE INDEX idx_calibrations_model ON physics_twin.twin_calibrations (model_id);