-- AeroForge-X v4.0 TimescaleDB Time-Series Tables
-- Pack Battery, Multi-body Dynamics, Flight Mode, Benchmark time-series

BEGIN;

-- V403.1: Pack Battery simulation time-series
CREATE TABLE IF NOT EXISTS sim_pack_battery_timeseries (
    time TIMESTAMPTZ NOT NULL,
    simulation_id UUID NOT NULL,
    pack_voltage FLOAT,
    pack_current FLOAT,
    pack_soc FLOAT,
    pack_soh FLOAT,
    pack_temperature FLOAT,
    bms_status VARCHAR(50),
    remaining_flight_time_min FLOAT
);

SELECT create_hypertable('sim_pack_battery_timeseries', 'time', chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_pack_battery_sim ON sim_pack_battery_timeseries(simulation_id, time DESC);

-- V403.2: Multi-body dynamics simulation time-series
CREATE TABLE IF NOT EXISTS sim_multi_body_timeseries (
    time TIMESTAMPTZ NOT NULL,
    simulation_id UUID NOT NULL,
    body_id INTEGER NOT NULL,
    position_x FLOAT,
    position_y FLOAT,
    position_z FLOAT,
    modal_coord_1 FLOAT,
    modal_coord_2 FLOAT,
    modal_coord_3 FLOAT,
    constraint_force_magnitude FLOAT
);

SELECT create_hypertable('sim_multi_body_timeseries', 'time', chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_multi_body_sim ON sim_multi_body_timeseries(simulation_id, body_id, time DESC);

-- V403.3: Flight mode state time-series
CREATE TABLE IF NOT EXISTS sim_flight_mode_timeseries (
    time TIMESTAMPTZ NOT NULL,
    simulation_id UUID NOT NULL,
    current_mode VARCHAR(50),
    blending_progress FLOAT DEFAULT 0.0,
    pid_kp FLOAT,
    pid_ki FLOAT,
    pid_kd FLOAT,
    autopilot_sub_mode VARCHAR(50)
);

SELECT create_hypertable('sim_flight_mode_timeseries', 'time', chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_flight_mode_sim ON sim_flight_mode_timeseries(simulation_id, time DESC);

-- V403.4: Benchmark time-series
CREATE TABLE IF NOT EXISTS benchmark_timeseries (
    time TIMESTAMPTZ NOT NULL,
    kpi_name VARCHAR(255) NOT NULL,
    kpi_value FLOAT NOT NULL,
    code_version VARCHAR(100),
    environment VARCHAR(100)
);

SELECT create_hypertable('benchmark_timeseries', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_benchmark_ts_kpi ON benchmark_timeseries(kpi_name, time DESC);

COMMIT;