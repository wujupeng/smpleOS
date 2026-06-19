-- AeroForge-X v2.0 Workflow/Pipeline Engine Schema
-- 关联需求：REQ-WFE-001 ~ REQ-WFE-038

CREATE SCHEMA IF NOT EXISTS workflow_engine;

CREATE TABLE workflow_engine.workflow_definitions (
    definition_id   VARCHAR(64) PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(32) NOT NULL DEFAULT 'Draft',
    nodes           JSONB NOT NULL DEFAULT '[]',
    edges           JSONB NOT NULL DEFAULT '[]',
    parameter_mappings JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_def_status CHECK (status IN ('Draft','Published','Deprecated')),
    CONSTRAINT uq_def_name_version UNIQUE (name, version)
);

CREATE INDEX idx_wf_defs_status ON workflow_engine.workflow_definitions (status);

CREATE TABLE workflow_engine.workflow_instances (
    instance_id         VARCHAR(64) PRIMARY KEY,
    definition_id       VARCHAR(64) NOT NULL REFERENCES workflow_engine.workflow_definitions(definition_id),
    definition_version  INTEGER NOT NULL,
    status              VARCHAR(32) NOT NULL DEFAULT 'Created',
    input_parameters    JSONB DEFAULT '{}',
    output_parameters   JSONB DEFAULT '{}',
    context             JSONB DEFAULT '{}',
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_inst_status CHECK (status IN ('Created','Running','Suspended','Completed','Failed'))
);

CREATE INDEX idx_wf_inst_def ON workflow_engine.workflow_instances (definition_id);
CREATE INDEX idx_wf_inst_status ON workflow_engine.workflow_instances (status);
CREATE INDEX idx_wf_inst_started ON workflow_engine.workflow_instances (started_at);

CREATE TABLE workflow_engine.node_execution_states (
    id              VARCHAR(64) PRIMARY KEY,
    instance_id     VARCHAR(64) NOT NULL REFERENCES workflow_engine.workflow_instances(instance_id) ON DELETE CASCADE,
    node_id         VARCHAR(64) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'Pending',
    input           JSONB DEFAULT '{}',
    output          JSONB DEFAULT '{}',
    retry_count     INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    CONSTRAINT chk_node_status CHECK (status IN ('Pending','Running','Completed','Failed','Skipped'))
);

CREATE INDEX idx_node_states_instance ON workflow_engine.node_execution_states (instance_id);
CREATE INDEX idx_node_states_status ON workflow_engine.node_execution_states (status);

CREATE TABLE workflow_engine.human_tasks (
    task_id         VARCHAR(64) PRIMARY KEY,
    instance_id     VARCHAR(64) NOT NULL REFERENCES workflow_engine.workflow_instances(instance_id) ON DELETE CASCADE,
    node_id         VARCHAR(64) NOT NULL,
    task_type       VARCHAR(32) NOT NULL,
    assignee        VARCHAR(128) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'Pending',
    deadline        TIMESTAMPTZ,
    escalated_to    VARCHAR(128),
    decision        VARCHAR(32),
    comments        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    CONSTRAINT chk_task_type CHECK (task_type IN ('Approval','Review','Decision')),
    CONSTRAINT chk_task_status CHECK (status IN ('Pending','Approved','Rejected','Escalated','Completed'))
);

CREATE INDEX idx_human_tasks_assignee ON workflow_engine.human_tasks (assignee, status);
CREATE INDEX idx_human_tasks_deadline ON workflow_engine.human_tasks (deadline) WHERE status = 'Pending';

CREATE TABLE workflow_engine.event_triggers (
    trigger_id      VARCHAR(64) PRIMARY KEY,
    definition_id   VARCHAR(64) NOT NULL REFERENCES workflow_engine.workflow_definitions(definition_id),
    trigger_type    VARCHAR(32) NOT NULL,
    event_pattern   VARCHAR(256),
    cron_expression VARCHAR(128),
    condition       TEXT,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_trigger_type CHECK (trigger_type IN ('EventDriven','Scheduled','Conditional'))
);

CREATE INDEX idx_triggers_definition ON workflow_engine.event_triggers (definition_id);
CREATE INDEX idx_triggers_enabled ON workflow_engine.event_triggers (enabled) WHERE enabled = TRUE;