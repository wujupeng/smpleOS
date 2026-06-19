-- AeroForge-X v1.0 AI Engine Tables
-- Migration: 008_ai_engine_tables.sql

-- AI方案表
CREATE TABLE IF NOT EXISTS aerogpt_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id VARCHAR(64) UNIQUE NOT NULL,
    agent_type VARCHAR(32) NOT NULL,
    input_description TEXT,
    generated_spec JSONB,
    generated_model_ref VARCHAR(256),
    feasibility_assessment JSONB,
    clarification_questions JSONB,
    status VARCHAR(32) NOT NULL DEFAULT 'pending_review',
    created_by VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by VARCHAR(64),
    review_comment TEXT
);

CREATE INDEX idx_proposals_agent_type ON aerogpt_proposals(agent_type);
CREATE INDEX idx_proposals_status ON aerogpt_proposals(status);
CREATE INDEX idx_proposals_created_at ON aerogpt_proposals(created_at);

-- 方案审核表
CREATE TABLE IF NOT EXISTS aerogpt_proposal_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id VARCHAR(64) UNIQUE NOT NULL,
    proposal_id VARCHAR(64) NOT NULL REFERENCES aerogpt_proposals(proposal_id),
    reviewer VARCHAR(64) NOT NULL,
    decision VARCHAR(32) NOT NULL,
    comment TEXT,
    conditions JSONB,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reviews_proposal_id ON aerogpt_proposal_reviews(proposal_id);

-- 优化任务表
CREATE TABLE IF NOT EXISTS optimization_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(64) UNIQUE NOT NULL,
    optimization_type VARCHAR(32) NOT NULL,
    objectives JSONB NOT NULL,
    constraints JSONB,
    design_variables JSONB NOT NULL,
    baseline_frozen BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    created_by VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_opt_tasks_type ON optimization_tasks(optimization_type);
CREATE INDEX idx_opt_tasks_status ON optimization_tasks(status);

-- 优化结果表
CREATE TABLE IF NOT EXISTS optimization_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id VARCHAR(64) UNIQUE NOT NULL,
    task_id VARCHAR(64) NOT NULL REFERENCES optimization_tasks(task_id),
    pareto_front JSONB NOT NULL,
    infeasible_regions JSONB,
    best_compromise JSONB,
    iteration_count INTEGER NOT NULL DEFAULT 0,
    convergence_achieved BOOLEAN NOT NULL DEFAULT FALSE,
    computation_time_seconds FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_opt_results_task_id ON optimization_results(task_id);

-- 拓扑优化结果表
CREATE TABLE IF NOT EXISTS topology_optimization_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id VARCHAR(64) UNIQUE NOT NULL,
    component_type VARCHAR(64) NOT NULL,
    load_conditions JSONB NOT NULL,
    material_constraints JSONB NOT NULL,
    optimized_material_distribution JSONB,
    weight_reduction_percentage FLOAT,
    stress_distribution JSONB,
    iteration_count INTEGER NOT NULL DEFAULT 0,
    convergence_achieved BOOLEAN NOT NULL DEFAULT FALSE,
    model_ref VARCHAR(256),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_topology_component_type ON topology_optimization_results(component_type);

-- 模型训练任务表
CREATE TABLE IF NOT EXISTS model_training_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id VARCHAR(64) UNIQUE NOT NULL,
    model_name VARCHAR(128) NOT NULL,
    model_type VARCHAR(32) NOT NULL,
    training_config JSONB NOT NULL,
    dataset_ref VARCHAR(256),
    gpu_hours_used FLOAT,
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    metrics JSONB,
    created_by VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_training_jobs_status ON model_training_jobs(status);
CREATE INDEX idx_training_jobs_model_type ON model_training_jobs(model_type);

-- 模型注册表
CREATE TABLE IF NOT EXISTS model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id VARCHAR(64) UNIQUE NOT NULL,
    model_name VARCHAR(128) NOT NULL,
    model_type VARCHAR(32) NOT NULL,
    version VARCHAR(32) NOT NULL,
    framework VARCHAR(32) NOT NULL,
    artifact_path VARCHAR(512) NOT NULL,
    metrics JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    registered_by VARCHAR(64),
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_model_registry_type ON model_registry(model_type);
CREATE INDEX idx_model_registry_active ON model_registry(is_active);

-- 特征存储表
CREATE TABLE IF NOT EXISTS feature_store (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_name VARCHAR(128) NOT NULL,
    feature_group VARCHAR(64) NOT NULL,
    feature_type VARCHAR(32) NOT NULL,
    description TEXT,
    source_table VARCHAR(128),
    transformation_logic TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feature_store_group ON feature_store(feature_group);
CREATE INDEX idx_feature_store_name ON feature_store(feature_name);
CREATE UNIQUE INDEX idx_feature_store_name_version ON feature_store(feature_name, version);