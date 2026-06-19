-- AeroForge-X v6.0 TimescaleDB Time-Series Tables
-- Shop Floor Data, Equipment OEE, Twin Deviation, UQ Inference
-- REQ-FACTORY-003, REQ-FACTORY-013, REQ-FACTORY-008, REQ-E-ENH-004

BEGIN;

-- =====================================================
-- V603.1: Shop floor data time-series
-- =====================================================
CREATE TABLE IF NOT EXISTS shop_floor_data_timeseries (
    time            TIMESTAMPTZ NOT NULL,
    equipment_id    VARCHAR(64) NOT NULL,
    data_type       VARCHAR(32) NOT NULL,
    value           DOUBLE PRECISION,
    unit            VARCHAR(16),
    quality_flag    VARCHAR(8) DEFAULT 'Good',
    retention_policy VARCHAR(16) DEFAULT 'raw_90d'
);

SELECT create_hypertable('shop_floor_data_timeseries', 'time', chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_sf_ts_equipment ON shop_floor_data_timeseries (equipment_id, time DESC);

-- =====================================================
-- V603.2: Equipment OEE time-series
-- =====================================================
CREATE TABLE IF NOT EXISTS equipment_oee_timeseries (
    time            TIMESTAMPTZ NOT NULL,
    equipment_id    VARCHAR(64) NOT NULL,
    availability    DOUBLE PRECISION,
    performance     DOUBLE PRECISION,
    quality         DOUBLE PRECISION,
    oee             DOUBLE PRECISION,
    period          VARCHAR(8) DEFAULT 'Shift'
);

SELECT create_hypertable('equipment_oee_timeseries', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_oee_ts_equipment ON equipment_oee_timeseries (equipment_id, time DESC);

-- =====================================================
-- V603.3: Twin deviation time-series
-- =====================================================
CREATE TABLE IF NOT EXISTS twin_deviation_timeseries (
    time            TIMESTAMPTZ NOT NULL,
    equipment_id    VARCHAR(64) NOT NULL,
    parameter_name  VARCHAR(64) NOT NULL,
    twin_predicted  DOUBLE PRECISION,
    physical_actual DOUBLE PRECISION,
    deviation_pct   DOUBLE PRECISION,
    root_cause      VARCHAR(32)
);

SELECT create_hypertable('twin_deviation_timeseries', 'time', chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_dev_ts_equipment ON twin_deviation_timeseries (equipment_id, time DESC);

-- =====================================================
-- V603.4: UQ inference time-series
-- =====================================================
CREATE TABLE IF NOT EXISTS uq_inference_timeseries (
    time            TIMESTAMPTZ NOT NULL,
    model_id        VARCHAR(64) NOT NULL,
    uq_method       VARCHAR(32) NOT NULL,
    coefficient_of_variation DOUBLE PRECISION,
    is_high_uncertainty BOOLEAN DEFAULT FALSE,
    inference_duration_ms DOUBLE PRECISION
);

SELECT create_hypertable('uq_inference_timeseries', 'time', chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_uq_ts_model ON uq_inference_timeseries (model_id, time DESC);

COMMIT;