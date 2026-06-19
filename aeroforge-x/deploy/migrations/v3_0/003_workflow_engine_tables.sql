-- AeroForge-X v3.0 Workflow Engine Tables
-- Program-C: Automatic Propagation

-- Propagation chain definitions
CREATE TABLE IF NOT EXISTS workflow_engine.propagation_chains (
    chain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    chain_type VARCHAR(30) NOT NULL CHECK (chain_type IN ('DesignToCAE', 'EBOMToMBOM', 'TwinToFRACAS')),
    trigger_event_pattern VARCHAR(200) NOT NULL,
    workflow_definition_id UUID,
    handler_bindings JSONB NOT NULL DEFAULT '[]',
    human_task_gates JSONB NOT NULL DEFAULT '[]',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Handler execution logs
CREATE TABLE IF NOT EXISTS workflow_engine.handler_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instance_id UUID NOT NULL,
    node_id VARCHAR(100) NOT NULL,
    handler_name VARCHAR(100) NOT NULL,
    input_snapshot JSONB NOT NULL DEFAULT '{}',
    output_snapshot JSONB NOT NULL DEFAULT '{}',
    schema_refs_used TEXT[] DEFAULT '{}',
    execution_duration_ms INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'Running' CHECK (status IN ('Running', 'Completed', 'Failed', 'Compensated')),
    error_message TEXT,
    operator_id VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Activity handler registry
CREATE TABLE IF NOT EXISTS workflow_engine.activity_handler_registry (
    handler_name VARCHAR(100) PRIMARY KEY,
    handler_type VARCHAR(50) NOT NULL,
    schema_references TEXT[] DEFAULT '{}',
    handler_path TEXT NOT NULL,
    interface_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    checksum VARCHAR(64),
    status VARCHAR(20) NOT NULL DEFAULT 'Registered' CHECK (status IN ('Registered', 'Active', 'Error', 'Deprecated')),
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_hot_reload TIMESTAMPTZ
);

-- ALTER event_triggers table
ALTER TABLE workflow_engine.event_triggers
ADD COLUMN IF NOT EXISTS propagation_chain_id UUID REFERENCES workflow_engine.propagation_chains(chain_id);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_propagation_chains_type ON workflow_engine.propagation_chains (chain_type);
CREATE INDEX IF NOT EXISTS idx_propagation_chains_active ON workflow_engine.propagation_chains (is_active);
CREATE INDEX IF NOT EXISTS idx_handler_logs_instance ON workflow_engine.handler_execution_logs (instance_id);
CREATE INDEX IF NOT EXISTS idx_handler_logs_handler ON workflow_engine.handler_execution_logs (handler_name);
CREATE INDEX IF NOT EXISTS idx_handler_logs_status ON workflow_engine.handler_execution_logs (status);
CREATE INDEX IF NOT EXISTS idx_handler_registry_type ON workflow_engine.activity_handler_registry (handler_type);
CREATE INDEX IF NOT EXISTS idx_handler_registry_status ON workflow_engine.activity_handler_registry (status);