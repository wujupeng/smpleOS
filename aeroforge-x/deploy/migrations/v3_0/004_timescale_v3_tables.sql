-- AeroForge-X v3.0 TimescaleDB Time-Series Tables
-- Program-B: Real Physics Twin - Simulation Results

-- 6DOF simulation time-series
CREATE TABLE IF NOT EXISTS physics_twin.sim_dof6_timeseries (
    time TIMESTAMPTZ NOT NULL,
    simulation_id UUID NOT NULL,
    position_x DOUBLE PRECISION DEFAULT 0,
    position_y DOUBLE PRECISION DEFAULT 0,
    position_z DOUBLE PRECISION DEFAULT 0,
    velocity_x DOUBLE PRECISION DEFAULT 0,
    velocity_y DOUBLE PRECISION DEFAULT 0,
    velocity_z DOUBLE PRECISION DEFAULT 0,
    roll DOUBLE PRECISION DEFAULT 0,
    pitch DOUBLE PRECISION DEFAULT 0,
    yaw DOUBLE PRECISION DEFAULT 0,
    roll_rate DOUBLE PRECISION DEFAULT 0,
    pitch_rate DOUBLE PRECISION DEFAULT 0,
    yaw_rate DOUBLE PRECISION DEFAULT 0
);

SELECT create_hypertable('physics_twin.sim_dof6_timeseries', 'time', chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);

-- Battery simulation time-series
CREATE TABLE IF NOT EXISTS physics_twin.sim_battery_timeseries (
    time TIMESTAMPTZ NOT NULL,
    simulation_id UUID NOT NULL,
    terminal_voltage DOUBLE PRECISION DEFAULT 0,
    current DOUBLE PRECISION DEFAULT 0,
    soc DOUBLE PRECISION DEFAULT 1.0,
    soh DOUBLE PRECISION DEFAULT 1.0,
    temperature DOUBLE PRECISION DEFAULT 25.0,
    v_rc1 DOUBLE PRECISION DEFAULT 0,
    v_rc2 DOUBLE PRECISION DEFAULT 0
);

SELECT create_hypertable('physics_twin.sim_battery_timeseries', 'time', chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);

-- Control simulation time-series
CREATE TABLE IF NOT EXISTS physics_twin.sim_control_timeseries (
    time TIMESTAMPTZ NOT NULL,
    simulation_id UUID NOT NULL,
    elevator_cmd DOUBLE PRECISION DEFAULT 0,
    aileron_cmd DOUBLE PRECISION DEFAULT 0,
    rudder_cmd DOUBLE PRECISION DEFAULT 0,
    throttle_cmd DOUBLE PRECISION DEFAULT 0,
    autopilot_mode VARCHAR(20) DEFAULT 'OFF'
);

SELECT create_hypertable('physics_twin.sim_control_timeseries', 'time', chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_dof6_sim ON physics_twin.sim_dof6_timeseries (simulation_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_battery_sim ON physics_twin.sim_battery_timeseries (simulation_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_control_sim ON physics_twin.sim_control_timeseries (simulation_id, time DESC);