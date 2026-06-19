-- AeroForge-X v4.0 Physics Twin Service Database Migration
-- Aerodynamic Database metadata, Pack Battery configs, Flight Mode Manager configs, Multi-body Dynamics configs

BEGIN;

-- V401.1: Aerodynamic Database metadata table
CREATE TABLE IF NOT EXISTS aero_database_metadata (
    database_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    database_name VARCHAR(255) NOT NULL,
    data_source VARCHAR(100) NOT NULL DEFAULT 'internal',
    quality_status VARCHAR(50) NOT NULL DEFAULT 'draft',
    applicable_config VARCHAR(255),
    data_file_ref TEXT,
    alpha_range_min FLOAT NOT NULL DEFAULT -10.0,
    alpha_range_max FLOAT NOT NULL DEFAULT 25.0,
    alpha_resolution FLOAT NOT NULL DEFAULT 1.0,
    beta_range_min FLOAT NOT NULL DEFAULT -10.0,
    beta_range_max FLOAT NOT NULL DEFAULT 10.0,
    beta_resolution FLOAT NOT NULL DEFAULT 1.0,
    mach_range_min FLOAT NOT NULL DEFAULT 0.0,
    mach_range_max FLOAT NOT NULL DEFAULT 0.9,
    mach_resolution FLOAT NOT NULL DEFAULT 0.05,
    reynolds_range_min FLOAT NOT NULL DEFAULT 1e6,
    reynolds_range_max FLOAT NOT NULL DEFAULT 5e7,
    reynolds_resolution FLOAT NOT NULL DEFAULT 1e6,
    coefficient_types TEXT[] NOT NULL DEFAULT '{"CL","CD","CM","CY","Cl","Cn"}',
    is_partial_coverage BOOLEAN NOT NULL DEFAULT FALSE,
    missing_dimensions TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- V401.2: Aerodynamic data import logs
CREATE TABLE IF NOT EXISTS aero_data_import_logs (
    import_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    database_id UUID REFERENCES aero_database_metadata(database_id),
    source_format VARCHAR(50) NOT NULL,
    source_file_path TEXT NOT NULL,
    import_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    records_imported INTEGER DEFAULT 0,
    constraint_violations INTEGER DEFAULT 0,
    partial_dimensions TEXT[] DEFAULT '{}',
    error_details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- V401.3: Pack Battery configuration table
CREATE TABLE IF NOT EXISTS pack_battery_configs (
    pack_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    series_count INTEGER NOT NULL DEFAULT 1,
    parallel_count INTEGER NOT NULL DEFAULT 1,
    modules_per_parallel INTEGER NOT NULL DEFAULT 1,
    cells_per_module INTEGER NOT NULL DEFAULT 1,
    cell_chemistry VARCHAR(50) NOT NULL DEFAULT 'NMC',
    cell_capacity FLOAT NOT NULL,
    cell_nominal_voltage FLOAT NOT NULL,
    thermal_conductivity FLOAT NOT NULL DEFAULT 0.5,
    cell_spacing FLOAT NOT NULL DEFAULT 0.005,
    bms_ovp_threshold FLOAT NOT NULL DEFAULT 4.25,
    bms_uvp_threshold FLOAT NOT NULL DEFAULT 2.8,
    bms_ocp_threshold FLOAT NOT NULL DEFAULT 200.0,
    bms_otp_threshold FLOAT NOT NULL DEFAULT 60.0,
    bms_balancing_mode VARCHAR(50) NOT NULL DEFAULT 'passive',
    bms_balancing_threshold FLOAT NOT NULL DEFAULT 0.05,
    fault_isolation_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- V401.4: Flight Mode Manager configuration table
CREATE TABLE IF NOT EXISTS flight_mode_manager_configs (
    fmm_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initial_mode VARCHAR(50) NOT NULL DEFAULT 'Takeoff',
    transition_graph JSONB NOT NULL DEFAULT '{
        "Takeoff": ["Climb", "GoAround"],
        "Climb": ["Cruise", "GoAround"],
        "Cruise": ["Approach", "GoAround"],
        "Approach": ["Landing", "GoAround"],
        "Landing": ["GoAround"],
        "GoAround": ["Climb"]
    }',
    blending_time FLOAT NOT NULL DEFAULT 2.0,
    emergency_override_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    control_law_schedule JSONB NOT NULL DEFAULT '{}',
    gain_scheduling_tables JSONB NOT NULL DEFAULT '{}',
    autopilot_mode_map JSONB NOT NULL DEFAULT '{
        "Takeoff": "RotationAndClimb",
        "Climb": "AltitudeAndHeadingHold",
        "Cruise": "AltitudeAndSpeedHold",
        "Approach": "ILSApproach",
        "Landing": "FlareAndRollout",
        "GoAround": "ClimbAndHeadingHold"
    }',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- V401.5: Multi-body model configuration table
CREATE TABLE IF NOT EXISTS multi_body_model_configs (
    mbd_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    body_count INTEGER NOT NULL DEFAULT 1,
    joint_count INTEGER NOT NULL DEFAULT 0,
    bodies_config JSONB NOT NULL DEFAULT '[]',
    joints_config JSONB NOT NULL DEFAULT '[]',
    flexible_body_indices INTEGER[] DEFAULT '{}',
    modal_count_per_body INTEGER NOT NULL DEFAULT 5,
    flutter_analysis_method VARCHAR(50) NOT NULL DEFAULT 'pk',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- V401.6: Flight mode transition history table
CREATE TABLE IF NOT EXISTS flight_mode_transition_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fmm_id UUID REFERENCES flight_mode_manager_configs(fmm_id),
    from_mode VARCHAR(50) NOT NULL,
    to_mode VARCHAR(50) NOT NULL,
    transition_type VARCHAR(50) NOT NULL DEFAULT 'normal',
    flight_state_at_transition JSONB DEFAULT '{}',
    is_rejected BOOLEAN NOT NULL DEFAULT FALSE,
    rejection_reason TEXT,
    transition_duration_ms FLOAT,
    operator_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- V401.7: Indexes
CREATE INDEX IF NOT EXISTS idx_aero_db_source ON aero_database_metadata(data_source);
CREATE INDEX IF NOT EXISTS idx_aero_db_config ON aero_database_metadata(applicable_config);
CREATE INDEX IF NOT EXISTS idx_aero_import_db ON aero_data_import_logs(database_id);
CREATE INDEX IF NOT EXISTS idx_fmm_history_fmm ON flight_mode_transition_history(fmm_id);

COMMIT;