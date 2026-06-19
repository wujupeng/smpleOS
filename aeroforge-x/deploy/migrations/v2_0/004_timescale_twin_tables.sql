-- AeroForge-X v2.0 TimescaleDB Twin Sensor/Prediction/Health Tables
-- 关联需求：REQ-PTC-026, REQ-PTC-028, REQ-PTC-029

CREATE TABLE physics_twin.twin_sensor_data (
    time            TIMESTAMPTZ NOT NULL,
    runtime_id      VARCHAR(64) NOT NULL,
    sensor_id       VARCHAR(64) NOT NULL,
    sensor_type     VARCHAR(32) NOT NULL,
    value           DOUBLE PRECISION NOT NULL,
    unit            VARCHAR(32) NOT NULL,
    quality         VARCHAR(16) NOT NULL DEFAULT 'Good'
);

SELECT create_hypertable('physics_twin.twin_sensor_data', 'time', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_sensor_data_runtime ON physics_twin.twin_sensor_data (runtime_id, time DESC);

CREATE TABLE physics_twin.twin_predictions (
    time            TIMESTAMPTZ NOT NULL,
    runtime_id      VARCHAR(64) NOT NULL,
    component_id    VARCHAR(64) NOT NULL,
    prediction_type VARCHAR(32) NOT NULL,
    predicted_value DOUBLE PRECISION NOT NULL,
    measured_value  DOUBLE PRECISION,
    deviation       DOUBLE PRECISION,
    confidence      FLOAT NOT NULL DEFAULT 1.0
);

SELECT create_hypertable('physics_twin.twin_predictions', 'time', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_predictions_runtime ON physics_twin.twin_predictions (runtime_id, time DESC);

CREATE TABLE physics_twin.twin_health_metrics (
    time            TIMESTAMPTZ NOT NULL,
    runtime_id      VARCHAR(64) NOT NULL,
    component_id    VARCHAR(64) NOT NULL,
    health_score    INTEGER NOT NULL,
    health_status   VARCHAR(16) NOT NULL DEFAULT 'Healthy'
);

SELECT create_hypertable('physics_twin.twin_health_metrics', 'time', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_health_runtime ON physics_twin.twin_health_metrics (runtime_id, time DESC);

CREATE MATERIALIZED VIEW physics_twin.twin_health_metrics_5min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS bucket,
    runtime_id,
    component_id,
    AVG(health_score) AS avg_health_score,
    MIN(health_score) AS min_health_score
FROM physics_twin.twin_health_metrics
GROUP BY bucket, runtime_id, component_id;