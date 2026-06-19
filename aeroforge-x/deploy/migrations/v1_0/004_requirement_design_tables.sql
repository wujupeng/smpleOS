-- ============================================================
-- AeroForge-X v1.0 Requirement/Design Center Database Migration
-- Tables: aircraft_specs, spec_parameters, requirement_traces,
--         sensitivity_analyses, parametric_models, design_rules,
--         airframe_models, structure_models, powertrain_models,
--         wire_harness_models
-- ============================================================

-- Aircraft Specs
CREATE TABLE IF NOT EXISTS aircraft_specs (
    spec_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    spec_number     VARCHAR(128) NOT NULL,
    aircraft_type   VARCHAR(64) NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',
    payload_kg      NUMERIC(10,2),
    range_km        NUMERIC(10,2),
    cruise_speed_kmh NUMERIC(10,2),
    takeoff_distance_m NUMERIC(10,2),
    power_type      VARCHAR(32),
    budget_cny      NUMERIC(14,2),
    material_id     UUID,
    certification_level_id UUID,
    derived_constraints JSONB DEFAULT '{}',
    created_by      UUID,
    approved_by     UUID,
    confirmed_at    TIMESTAMPTZ,
    frozen_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_aircraft_spec_number UNIQUE (spec_number),
    CONSTRAINT chk_spec_aircraft_type CHECK (aircraft_type IN (
        'fixed_wing', 'glider', 'evtol', 'uav'
    )),
    CONSTRAINT chk_spec_status CHECK (status IN (
        'draft', 'submitted', 'approved', 'confirmed', 'frozen', 'rejected'
    )),
    CONSTRAINT chk_spec_power_type CHECK (power_type IS NULL OR power_type IN (
        'electric', 'hybrid', 'gasoline', 'diesel'
    ))
);

CREATE INDEX idx_aircraft_specs_type ON aircraft_specs(aircraft_type);
CREATE INDEX idx_aircraft_specs_status ON aircraft_specs(status);
CREATE INDEX idx_aircraft_specs_created_by ON aircraft_specs(created_by);

-- Spec Parameters
CREATE TABLE IF NOT EXISTS spec_parameters (
    parameter_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    spec_id         UUID NOT NULL REFERENCES aircraft_specs(spec_id) ON DELETE CASCADE,
    name            VARCHAR(256) NOT NULL,
    category        VARCHAR(64) NOT NULL,
    value           NUMERIC(14,4),
    unit            VARCHAR(32),
    tolerance       NUMERIC(10,4),
    priority        VARCHAR(16) NOT NULL DEFAULT 'medium',
    is_required     BOOLEAN NOT NULL DEFAULT FALSE,
    validation_rules JSONB DEFAULT '[]',
    dependencies    JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_param_category CHECK (category IN (
        'performance', 'structural', 'aerodynamic', 'propulsion',
        'avionics', 'environmental', 'operational', 'certification'
    )),
    CONSTRAINT chk_param_priority CHECK (priority IN (
        'critical', 'high', 'medium', 'low'
    ))
);

CREATE INDEX idx_spec_parameters_spec ON spec_parameters(spec_id);
CREATE INDEX idx_spec_parameters_category ON spec_parameters(category);

-- Requirement Traces
CREATE TABLE IF NOT EXISTS requirement_traces (
    trace_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type     VARCHAR(64) NOT NULL,
    source_id       UUID NOT NULL,
    target_type     VARCHAR(64) NOT NULL,
    target_id       UUID NOT NULL,
    trace_type      VARCHAR(32) NOT NULL,
    confidence      NUMERIC(3,2) DEFAULT 1.00,
    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_trace_source_type CHECK (source_type IN (
        'spec', 'requirement', 'design_object', 'test_case', 'certification_item'
    )),
    CONSTRAINT chk_trace_target_type CHECK (target_type IN (
        'spec', 'requirement', 'design_object', 'test_case', 'certification_item'
    )),
    CONSTRAINT chk_trace_type CHECK (trace_type IN (
        'satisfies', 'verifies', 'derives', 'traces_to', 'implemented_by'
    )),
    CONSTRAINT chk_trace_confidence CHECK (confidence >= 0.0 AND confidence <= 1.00)
);

CREATE INDEX idx_requirement_traces_source ON requirement_traces(source_type, source_id);
CREATE INDEX idx_requirement_traces_target ON requirement_traces(target_type, target_id);
CREATE INDEX idx_requirement_traces_type ON requirement_traces(trace_type);

-- Sensitivity Analyses
CREATE TABLE IF NOT EXISTS sensitivity_analyses (
    analysis_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    spec_id         UUID NOT NULL REFERENCES aircraft_specs(spec_id) ON DELETE CASCADE,
    parameter_id    UUID REFERENCES spec_parameters(parameter_id) ON DELETE SET NULL,
    parameter_name  VARCHAR(256) NOT NULL,
    baseline_value  NUMERIC(14,4),
    perturbation    NUMERIC(10,4),
    sensitivity_index NUMERIC(10,6),
    influence_rank  INTEGER,
    performance_impact JSONB DEFAULT '{}',
    analysis_method VARCHAR(32) NOT NULL DEFAULT 'finite_difference',
    analysis_date   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID,
    CONSTRAINT chk_sensitivity_method CHECK (analysis_method IN (
        'finite_difference', 'morris', 'sobol', 'regression'
    ))
);

CREATE INDEX idx_sensitivity_analyses_spec ON sensitivity_analyses(spec_id);
CREATE INDEX idx_sensitivity_analyses_rank ON sensitivity_analyses(influence_rank);

-- Parametric Models
CREATE TABLE IF NOT EXISTS parametric_models (
    model_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    spec_ref        UUID REFERENCES aircraft_specs(spec_id),
    model_name      VARCHAR(256) NOT NULL,
    model_type      VARCHAR(64) NOT NULL,
    parameters      JSONB NOT NULL DEFAULT '{}',
    constraints     JSONB DEFAULT '[]',
    version         INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',
    geometry_data   JSONB,
    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_param_model_type CHECK (model_type IN (
        'airframe', 'structure', 'powertrain', 'wire_harness', 'full_assembly'
    )),
    CONSTRAINT chk_param_model_status CHECK (status IN (
        'draft', 'generated', 'validated', 'approved', 'released', 'archived'
    ))
);

CREATE INDEX idx_parametric_models_spec ON parametric_models(spec_ref);
CREATE INDEX idx_parametric_models_type ON parametric_models(model_type);
CREATE INDEX idx_parametric_models_status ON parametric_models(status);

-- Design Rules
CREATE TABLE IF NOT EXISTS design_rules (
    rule_id         VARCHAR(64) PRIMARY KEY,
    rule_name       VARCHAR(256) NOT NULL,
    rule_type       VARCHAR(32) NOT NULL,
    domain          VARCHAR(64) NOT NULL,
    condition_expr  TEXT NOT NULL,
    action_expr     TEXT,
    priority        INTEGER NOT NULL DEFAULT 50,
    severity        VARCHAR(16) NOT NULL DEFAULT 'warning',
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    description     TEXT,
    category        VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_rule_type CHECK (rule_type IN (
        'range', 'consistency', 'compliance', 'interference', 'manufacturability'
    )),
    CONSTRAINT chk_rule_severity CHECK (severity IN (
        'info', 'warning', 'error', 'critical'
    ))
);

CREATE INDEX idx_design_rules_domain ON design_rules(domain);
CREATE INDEX idx_design_rules_enabled ON design_rules(enabled);
CREATE INDEX idx_design_rules_type ON design_rules(rule_type);

-- Airframe Models
CREATE TABLE IF NOT EXISTS airframe_models (
    airframe_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_ref       UUID REFERENCES parametric_models(model_id) ON DELETE CASCADE,
    fuselage_params JSONB NOT NULL DEFAULT '{}',
    wing_params     JSONB NOT NULL DEFAULT '{}',
    tail_params     JSONB NOT NULL DEFAULT '{}',
    landing_gear_params JSONB DEFAULT '{}',
    geometry_data   JSONB,
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_airframe_status CHECK (status IN (
        'draft', 'generated', 'validated', 'approved', 'released'
    ))
);

CREATE INDEX idx_airframe_models_model ON airframe_models(model_ref);

-- Structure Models
CREATE TABLE IF NOT EXISTS structure_models (
    structure_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    airframe_ref    UUID REFERENCES airframe_models(airframe_id) ON DELETE CASCADE,
    component_type  VARCHAR(64) NOT NULL,
    material        VARCHAR(128),
    geometry        JSONB NOT NULL DEFAULT '{}',
    load_cases      JSONB DEFAULT '[]',
    fasteners       JSONB DEFAULT '[]',
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_structure_component CHECK (component_type IN (
        'spar', 'rib', 'frame', 'skin_panel', 'stringer', 'bulkhead', 'fitting'
    )),
    CONSTRAINT chk_structure_status CHECK (status IN (
        'draft', 'generated', 'validated', 'approved', 'released'
    ))
);

CREATE INDEX idx_structure_models_airframe ON structure_models(airframe_ref);
CREATE INDEX idx_structure_models_component ON structure_models(component_type);

-- Powertrain Models
CREATE TABLE IF NOT EXISTS powertrain_models (
    powertrain_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_ref       UUID REFERENCES parametric_models(model_id) ON DELETE CASCADE,
    motor_spec      JSONB NOT NULL DEFAULT '{}',
    battery_spec    JSONB DEFAULT '{}',
    esc_spec        JSONB DEFAULT '{}',
    cable_routing   JSONB DEFAULT '[]',
    thrust_params   JSONB DEFAULT '{}',
    fuel_system     JSONB DEFAULT '{}',
    propeller_params JSONB DEFAULT '{}',
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_powertrain_status CHECK (status IN (
        'draft', 'configured', 'validated', 'approved', 'released'
    ))
);

CREATE INDEX idx_powertrain_models_model ON powertrain_models(model_ref);

-- Wire Harness Models
CREATE TABLE IF NOT EXISTS wire_harness_models (
    harness_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_ref       UUID REFERENCES parametric_models(model_id) ON DELETE CASCADE,
    harness_type    VARCHAR(64) NOT NULL,
    wire_list       JSONB NOT NULL DEFAULT '[]',
    connector_list  JSONB NOT NULL DEFAULT '[]',
    routing_paths   JSONB NOT NULL DEFAULT '[]',
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_harness_type CHECK (harness_type IN (
        'primary', 'secondary', 'avionics_bus', 'power_distribution', 'sensor_harness'
    )),
    CONSTRAINT chk_harness_status CHECK (status IN (
        'draft', 'routed', 'validated', 'approved', 'released'
    ))
);

CREATE INDEX idx_wire_harness_models_model ON wire_harness_models(model_ref);