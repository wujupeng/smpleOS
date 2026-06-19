-- AeroForge-X v5.0 TimescaleDB Time-Series Tables
-- CFD Surrogate Inference, MDO Progress, Fleet Health, PHM RUL, Fleet Fatigue
-- REQ-DES-012, REQ-DES-017, REQ-FLT-002, REQ-FLT-006, REQ-FLT-012

BEGIN;

-- =====================================================
-- V503.1: CFD surrogate model inference time-series
-- =====================================================
CREATE TABLE IF NOT EXISTS cfd_surrogate_inference_timeseries (
    time            TIMESTAMPTZ NOT NULL,
    model_id        VARCHAR(64) NOT NULL,
    alpha           DOUBLE PRECISION,
    beta            DOUBLE PRECISION,
    mach            DOUBLE PRECISION,
    reynolds        DOUBLE PRECISION,
    CL              DOUBLE PRECISION,
    CD              DOUBLE PRECISION,
    CM              DOUBLE PRECISION,
    confidence      DOUBLE PRECISION,
    is_fallback     BOOLEAN DEFAULT FALSE,
    inference_duration_ms DOUBLE PRECISION
);

SELECT create_hypertable('cfd_surrogate_inference_timeseries', 'time', chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_surrogate_ts_model ON cfd_surrogate_inference_timeseries (model_id, time DESC);

-- =====================================================
-- V503.2: MDO optimization progress time-series
-- =====================================================
CREATE TABLE IF NOT EXISTS mdo_progress_timeseries (
    time            TIMESTAMPTZ NOT NULL,
    run_id          VARCHAR(64) NOT NULL,
    generation      INTEGER NOT NULL,
    hypervolume     DOUBLE PRECISION,
    pareto_size     INTEGER,
    best_objectives JSONB,
    convergence_metric DOUBLE PRECISION
);

SELECT create_hypertable('mdo_progress_timeseries', 'time', chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_mdo_progress_run ON mdo_progress_timeseries (run_id, time DESC);

-- =====================================================
-- V503.3: Fleet health aggregation time-series
-- =====================================================
CREATE TABLE IF NOT EXISTS fleet_health_timeseries (
    time            TIMESTAMPTZ NOT NULL,
    filter_hash     VARCHAR(64) NOT NULL,
    total_aircraft  INTEGER,
    healthy_count   INTEGER,
    warning_count   INTEGER,
    critical_count  INTEGER,
    average_rul_engine_hours DOUBLE PRECISION,
    average_rul_battery_hours DOUBLE PRECISION,
    average_fatigue_consumption DOUBLE PRECISION,
    is_sampled      BOOLEAN DEFAULT FALSE,
    sample_size     INTEGER
);

SELECT create_hypertable('fleet_health_timeseries', 'time', chunk_time_interval => INTERVAL '5 minutes', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_fleet_health_filter ON fleet_health_timeseries (filter_hash, time DESC);

-- =====================================================
-- V503.4: PHM RUL prediction time-series
-- =====================================================
CREATE TABLE IF NOT EXISTS phm_rul_prediction_timeseries (
    time            TIMESTAMPTZ NOT NULL,
    aircraft_id     VARCHAR(64) NOT NULL,
    component_type  VARCHAR(32) NOT NULL,
    predicted_rul_hours DOUBLE PRECISION,
    confidence      DOUBLE PRECISION,
    model_id        VARCHAR(64) NOT NULL,
    is_low_confidence BOOLEAN DEFAULT FALSE
);

SELECT create_hypertable('phm_rul_prediction_timeseries', 'time', chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_rul_ts_aircraft ON phm_rul_prediction_timeseries (aircraft_id, component_type, time DESC);

-- =====================================================
-- V503.5: Fleet fatigue damage time-series
-- =====================================================
CREATE TABLE IF NOT EXISTS fleet_fatigue_timeseries (
    time            TIMESTAMPTZ NOT NULL,
    aircraft_id     VARCHAR(64) NOT NULL,
    cumulative_damage DOUBLE PRECISION,
    remaining_fatigue_life_hours DOUBLE PRECISION,
    consumption_rate_per_flight_hour DOUBLE PRECISION,
    flight_hours_accumulated DOUBLE PRECISION,
    is_warning      BOOLEAN DEFAULT FALSE
);

SELECT create_hypertable('fleet_fatigue_timeseries', 'time', chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_fatigue_ts_aircraft ON fleet_fatigue_timeseries (aircraft_id, time DESC);

COMMIT;