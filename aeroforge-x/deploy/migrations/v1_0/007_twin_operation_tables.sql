-- ============================================================
-- AeroForge-X v1.0 Twin/Operation Center Database Migration
-- Tables: design_twins, manufacturing_twins, flight_twins,
--         maintenance_twins, fleet_twins, fleet_anomaly_reports,
--         fleet_reliability_analyses, fleet_maintenance_optimizations,
--         aircraft_registrations, operation_analytics,
--         maintenance_schedules, flight_sensor_data, fleet_operation_metrics
-- ============================================================

-- Design Twins
CREATE TABLE IF NOT EXISTS design_twins (
    twin_id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aircraft_serial_number VARCHAR(128) NOT NULL,
    design_parameters      JSONB NOT NULL DEFAULT '{}',
    model_version          INTEGER NOT NULL DEFAULT 1,
    last_sync_time         TIMESTAMPTZ,
    data_status            VARCHAR(32) DEFAULT 'current',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_design_twin_sn UNIQUE (aircraft_serial_number)
);

-- Manufacturing Twins
CREATE TABLE IF NOT EXISTS manufacturing_twins (
    twin_id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aircraft_serial_number VARCHAR(128) NOT NULL UNIQUE,
    actual_dimensions      JSONB DEFAULT '{}',
    deviations             JSONB DEFAULT '[]',
    process_records        JSONB DEFAULT '[]',
    last_sync_time         TIMESTAMPTZ,
    data_status            VARCHAR(32) DEFAULT 'current',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Flight Twins
CREATE TABLE IF NOT EXISTS flight_twins (
    twin_id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aircraft_serial_number VARCHAR(128) NOT NULL UNIQUE,
    flight_parameters      JSONB DEFAULT '{}',
    structural_loads       JSONB DEFAULT '{}',
    system_status          JSONB DEFAULT '{}',
    last_data_time         TIMESTAMPTZ,
    data_status            VARCHAR(32) DEFAULT 'current',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Maintenance Twins
CREATE TABLE IF NOT EXISTS maintenance_twins (
    twin_id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aircraft_serial_number VARCHAR(128) NOT NULL UNIQUE,
    maintenance_history    JSONB DEFAULT '[]',
    component_replacements JSONB DEFAULT '[]',
    remaining_life         JSONB DEFAULT '{}',
    health_indicators      JSONB DEFAULT '{}',
    last_sync_time         TIMESTAMPTZ,
    data_status            VARCHAR(32) DEFAULT 'current',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fleet Twins
CREATE TABLE IF NOT EXISTS fleet_twins (
    fleet_twin_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fleet_id               VARCHAR(128) NOT NULL UNIQUE,
    aircraft_count         INTEGER DEFAULT 0,
    fault_statistics       JSONB DEFAULT '{}',
    life_statistics        JSONB DEFAULT '{}',
    maintenance_statistics JSONB DEFAULT '{}',
    status                 VARCHAR(32) DEFAULT 'active',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fleet Anomaly Reports
CREATE TABLE IF NOT EXISTS fleet_anomaly_reports (
    report_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fleet_id               VARCHAR(128) NOT NULL,
    anomaly_type           VARCHAR(64) NOT NULL,
    affected_aircraft      JSONB DEFAULT '[]',
    description            TEXT,
    severity               VARCHAR(16) DEFAULT 'warning',
    status                 VARCHAR(32) DEFAULT 'open',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fleet_anomaly_fleet ON fleet_anomaly_reports(fleet_id);
CREATE INDEX idx_fleet_anomaly_severity ON fleet_anomaly_reports(severity);

-- Fleet Reliability Analyses
CREATE TABLE IF NOT EXISTS fleet_reliability_analyses (
    analysis_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fleet_id               VARCHAR(128) NOT NULL,
    fleet_mtbf_hours       NUMERIC(14,2),
    dispatch_reliability_pct NUMERIC(5,2),
    analysis_date          DATE NOT NULL DEFAULT CURRENT_DATE,
    details                JSONB DEFAULT '{}',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fleet_reliability_fleet ON fleet_reliability_analyses(fleet_id);

-- Fleet Maintenance Optimizations
CREATE TABLE IF NOT EXISTS fleet_maintenance_optimizations (
    optimization_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fleet_id               VARCHAR(128) NOT NULL,
    optimization_type      VARCHAR(64) NOT NULL,
    current_plan           JSONB DEFAULT '{}',
    recommended_plan       JSONB DEFAULT '{}',
    estimated_savings_pct  NUMERIC(5,2),
    status                 VARCHAR(32) DEFAULT 'proposed',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Aircraft Registrations
CREATE TABLE IF NOT EXISTS aircraft_registrations (
    registration_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aircraft_serial_number VARCHAR(128) NOT NULL UNIQUE,
    model                  VARCHAR(128) NOT NULL,
    registration_date      DATE NOT NULL,
    total_flight_hours     NUMERIC(10,2) DEFAULT 0,
    next_maintenance_date  DATE,
    status                 VARCHAR(32) DEFAULT 'active',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_aircraft_reg_status ON aircraft_registrations(status);

-- Operation Analytics
CREATE TABLE IF NOT EXISTS operation_analytics (
    analytics_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fleet_id               VARCHAR(128) NOT NULL,
    period_start           DATE NOT NULL,
    period_end             DATE NOT NULL,
    utilization_rate_pct   NUMERIC(5,2),
    dispatch_reliability_pct NUMERIC(5,2),
    maintenance_cost_cny   NUMERIC(14,2),
    flight_hours_total     NUMERIC(10,2),
    details                JSONB DEFAULT '{}',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_operation_analytics_fleet ON operation_analytics(fleet_id);

-- Maintenance Schedules
CREATE TABLE IF NOT EXISTS maintenance_schedules (
    schedule_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aircraft_serial_number VARCHAR(128) NOT NULL,
    maintenance_type       VARCHAR(64) NOT NULL,
    planned_date           DATE NOT NULL,
    estimated_duration_hours NUMERIC(6,1),
    actual_start           TIMESTAMPTZ,
    actual_end             TIMESTAMPTZ,
    status                 VARCHAR(32) DEFAULT 'planned',
    notes                  TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_maint_status CHECK (status IN ('planned', 'in_progress', 'completed', 'deferred', 'cancelled'))
);

CREATE INDEX idx_maint_schedule_aircraft ON maintenance_schedules(aircraft_serial_number);
CREATE INDEX idx_maint_schedule_date ON maintenance_schedules(planned_date);

-- Flight Sensor Data (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS flight_sensor_data (
    time                  TIMESTAMPTZ NOT NULL,
    aircraft_serial_number VARCHAR(128) NOT NULL,
    sensor_id             VARCHAR(64) NOT NULL,
    value                 NUMERIC(14,6),
    unit                  VARCHAR(32),
    quality               VARCHAR(16) DEFAULT 'good'
);

SELECT create_hypertable('flight_sensor_data', 'time', if_not_exists => TRUE);
CREATE INDEX idx_sensor_data_aircraft ON flight_sensor_data(aircraft_serial_number, time DESC);

-- Fleet Operation Metrics (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS fleet_operation_metrics (
    time                  TIMESTAMPTZ NOT NULL,
    fleet_id              VARCHAR(128) NOT NULL,
    metric_name           VARCHAR(64) NOT NULL,
    metric_value          NUMERIC(14,4),
    unit                  VARCHAR(32)
);

SELECT create_hypertable('fleet_operation_metrics', 'time', if_not_exists => TRUE);
CREATE INDEX idx_fleet_metrics_fleet ON fleet_operation_metrics(fleet_id, time DESC);