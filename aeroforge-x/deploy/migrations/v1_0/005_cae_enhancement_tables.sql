-- ============================================================
-- AeroForge-X v1.0 CAE Enhancement Database Migration
-- Tables: stability_analyses, flight_dynamics_analyses,
--         control_synthesis_results, flight_envelope_analyses,
--         simulation_workflows
-- ============================================================

-- Stability Analyses
CREATE TABLE IF NOT EXISTS stability_analyses (
    analysis_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aircraft_config     JSONB NOT NULL DEFAULT '{}',
    longitudinal_result JSONB DEFAULT '{}',
    lateral_result      JSONB DEFAULT '{}',
    directional_result  JSONB DEFAULT '{}',
    suggestions         JSONB DEFAULT '[]',
    is_statically_unstable BOOLEAN DEFAULT FALSE,
    status              VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_by          UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_stability_status CHECK (status IN (
        'pending', 'running', 'completed', 'failed'
    ))
);

CREATE INDEX idx_stability_analyses_status ON stability_analyses(status);
CREATE INDEX idx_stability_analyses_unstable ON stability_analyses(is_statically_unstable);

-- Flight Dynamics Analyses
CREATE TABLE IF NOT EXISTS flight_dynamics_analyses (
    analysis_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aircraft_config         JSONB NOT NULL DEFAULT '{}',
    trim_results            JSONB DEFAULT '{}',
    simulation_results      JSONB DEFAULT '{}',
    dynamic_response_results JSONB DEFAULT '{}',
    is_uncontrollable       BOOLEAN DEFAULT FALSE,
    trim_converged          BOOLEAN DEFAULT TRUE,
    simulation_diverged     BOOLEAN DEFAULT FALSE,
    status                  VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_by              UUID,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_flight_dynamics_status CHECK (status IN (
        'pending', 'running', 'completed', 'failed'
    ))
);

CREATE INDEX idx_flight_dynamics_status ON flight_dynamics_analyses(status);
CREATE INDEX idx_flight_dynamics_uncontrollable ON flight_dynamics_analyses(is_uncontrollable);

-- Control Synthesis Results
CREATE TABLE IF NOT EXISTS control_synthesis_results (
    result_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aircraft_config     JSONB NOT NULL DEFAULT '{}',
    control_type        VARCHAR(16) NOT NULL,
    pid_params          JSONB DEFAULT '{}',
    lqr_params          JSONB DEFAULT '{}',
    mpc_params          JSONB DEFAULT '{}',
    stability_margins   JSONB DEFAULT '{}',
    gain_margin_db      NUMERIC(6,2),
    phase_margin_deg    NUMERIC(6,2),
    is_margins_satisfied BOOLEAN DEFAULT FALSE,
    iteration_count     INTEGER DEFAULT 0,
    status              VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_by          UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_control_type CHECK (control_type IN (
        'pid', 'lqr', 'mpc'
    )),
    CONSTRAINT chk_control_status CHECK (status IN (
        'pending', 'synthesizing', 'validating', 'completed', 'failed'
    ))
);

CREATE INDEX idx_control_synthesis_type ON control_synthesis_results(control_type);
CREATE INDEX idx_control_synthesis_status ON control_synthesis_results(status);
CREATE INDEX idx_control_synthesis_margins ON control_synthesis_results(is_margins_satisfied);

-- Flight Envelope Analyses
CREATE TABLE IF NOT EXISTS flight_envelope_analyses (
    analysis_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aircraft_config     JSONB NOT NULL DEFAULT '{}',
    limit_speeds        JSONB DEFAULT '{}',
    limit_load_factors  JSONB DEFAULT '{}',
    vn_diagram          JSONB DEFAULT '{}',
    gust_envelope       JSONB DEFAULT '{}',
    violations          JSONB DEFAULT '[]',
    is_airworthy        BOOLEAN DEFAULT TRUE,
    status              VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_by          UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_envelope_status CHECK (status IN (
        'pending', 'running', 'completed', 'failed'
    ))
);

CREATE INDEX idx_flight_envelope_status ON flight_envelope_analyses(status);
CREATE INDEX idx_flight_envelope_airworthy ON flight_envelope_analyses(is_airworthy);

-- Simulation Workflows
CREATE TABLE IF NOT EXISTS simulation_workflows (
    workflow_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_name       VARCHAR(256) NOT NULL,
    steps               JSONB NOT NULL DEFAULT '[]',
    current_step        INTEGER DEFAULT 0,
    status              VARCHAR(32) NOT NULL DEFAULT 'created',
    dependencies        JSONB DEFAULT '[]',
    results             JSONB DEFAULT '{}',
    created_by          UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_workflow_status CHECK (status IN (
        'created', 'running', 'paused', 'completed', 'failed', 'cancelled'
    ))
);

CREATE INDEX idx_simulation_workflows_status ON simulation_workflows(status);