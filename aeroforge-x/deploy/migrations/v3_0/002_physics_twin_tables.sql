-- AeroForge-X v3.0 Physics Twin Tables
-- Program-B: Real Physics Twin

-- Model parameters storage
CREATE TABLE IF NOT EXISTS physics_twin.model_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES physics_twin.physics_models(model_id) ON DELETE CASCADE,
    parameter_name VARCHAR(100) NOT NULL,
    parameter_value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(30),
    fidelity_level VARCHAR(20) NOT NULL DEFAULT 'Low' CHECK (fidelity_level IN ('Low', 'Mid', 'High', 'Detail')),
    schema_ref VARCHAR(100),
    source VARCHAR(50) NOT NULL DEFAULT 'user' CHECK (source IN ('user', 'schema', 'calibration', 'rom')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(model_id, parameter_name, fidelity_level)
);

-- Simulation results detail
CREATE TABLE IF NOT EXISTS physics_twin.simulation_results_detail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_id UUID NOT NULL REFERENCES physics_twin.physics_simulations(simulation_id) ON DELETE CASCADE,
    result_type VARCHAR(30) NOT NULL CHECK (result_type IN ('6DOF', 'Battery', 'Control', 'Coupled')),
    variable_name VARCHAR(100) NOT NULL,
    time_series_data JSONB,
    scalar_value DOUBLE PRECISION,
    unit VARCHAR(30),
    fidelity_level VARCHAR(20) NOT NULL DEFAULT 'Low',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Model plugin registry
CREATE TABLE IF NOT EXISTS physics_twin.model_plugin_registry (
    plugin_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    model_type VARCHAR(30) NOT NULL CHECK (model_type IN ('6DOF', 'Battery', 'Control')),
    supported_fidelities VARCHAR(20)[] NOT NULL DEFAULT '{"Low"}',
    associated_schema_ref VARCHAR(100),
    interface_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    plugin_path TEXT NOT NULL,
    checksum VARCHAR(64),
    status VARCHAR(20) NOT NULL DEFAULT 'Registered' CHECK (status IN ('Registered', 'Loaded', 'Error', 'Deprecated')),
    loaded_at TIMESTAMPTZ,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_hot_reload TIMESTAMPTZ
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_model_params_model ON physics_twin.model_parameters (model_id);
CREATE INDEX IF NOT EXISTS idx_model_params_fidelity ON physics_twin.model_parameters (fidelity_level);
CREATE INDEX IF NOT EXISTS idx_sim_results_detail_sim ON physics_twin.simulation_results_detail (simulation_id);
CREATE INDEX IF NOT EXISTS idx_sim_results_detail_type ON physics_twin.simulation_results_detail (result_type);
CREATE INDEX IF NOT EXISTS idx_plugin_registry_type ON physics_twin.model_plugin_registry (model_type);
CREATE INDEX IF NOT EXISTS idx_plugin_registry_status ON physics_twin.model_plugin_registry (status);