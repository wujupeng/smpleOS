-- AeroForge-X Phase 4 Database Migration Script
-- Version: 4.0.0
-- Description: Create all Phase 4 tables for unified twin, certification, knowledge graph, etc.

-- Unified Twin tables
CREATE TABLE IF NOT EXISTS unified_twins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aircraft_serial_number VARCHAR(50) NOT NULL UNIQUE,
    tenant_id VARCHAR(50) NOT NULL,
    project_id VARCHAR(50) NOT NULL,
    design_twin_id VARCHAR(50),
    manufacturing_twin_id VARCHAR(50),
    flight_twin_id VARCHAR(50),
    maintenance_twin_id VARCHAR(50),
    fusion_status VARCHAR(20) DEFAULT 'not_fused',
    last_fusion_time TIMESTAMPTZ,
    fusion_version INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_unified_twins_tenant ON unified_twins(tenant_id);
CREATE INDEX idx_unified_twins_sn ON unified_twins(aircraft_serial_number);

CREATE TABLE IF NOT EXISTS twin_fusion_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unified_twin_id UUID REFERENCES unified_twins(id),
    record_id VARCHAR(50) NOT NULL,
    fusion_version INTEGER NOT NULL,
    design_data_hash VARCHAR(64),
    manufacturing_data_hash VARCHAR(64),
    flight_data_hash VARCHAR(64),
    maintenance_data_hash VARCHAR(64),
    insights_generated INTEGER DEFAULT 0,
    conflicts_detected INTEGER DEFAULT 0,
    conflicts_resolved INTEGER DEFAULT 0,
    fused_at TIMESTAMPTZ DEFAULT NOW(),
    duration_ms FLOAT DEFAULT 0
);

CREATE INDEX idx_fusion_records_twin ON twin_fusion_records(unified_twin_id);

CREATE TABLE IF NOT EXISTS cross_twin_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unified_twin_id UUID REFERENCES unified_twins(id),
    insight_id VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    source_twin VARCHAR(30) NOT NULL,
    target_twin VARCHAR(30) NOT NULL,
    description TEXT,
    evidence JSONB DEFAULT '{}',
    recommendation TEXT,
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_insights_twin ON cross_twin_insights(unified_twin_id);
CREATE INDEX idx_insights_severity ON cross_twin_insights(severity);

CREATE TABLE IF NOT EXISTS twin_loop_feedbacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aircraft_serial_number VARCHAR(50) NOT NULL,
    feedback_id VARCHAR(50) NOT NULL,
    source_domain VARCHAR(30) NOT NULL,
    target_domain VARCHAR(30) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    evidence JSONB DEFAULT '{}',
    recommendation TEXT,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_loop_feedbacks_sn ON twin_loop_feedbacks(aircraft_serial_number);

-- Certification tables
CREATE TABLE IF NOT EXISTS certification_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    project_id VARCHAR(50) NOT NULL,
    aircraft_model VARCHAR(50) NOT NULL,
    certification_standard VARCHAR(20) NOT NULL,
    plan_status VARCHAR(20) DEFAULT 'draft',
    total_requirements INTEGER DEFAULT 0,
    completed_verifications INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cert_plans_tenant ON certification_plans(tenant_id);

CREATE TABLE IF NOT EXISTS compliance_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES certification_plans(id),
    requirement_id VARCHAR(50) NOT NULL,
    clause VARCHAR(20) NOT NULL,
    verification_method VARCHAR(50),
    verification_status VARCHAR(20) DEFAULT 'pending',
    evidence_documents JSONB DEFAULT '[]',
    verified_by VARCHAR(50),
    verified_at TIMESTAMPTZ,
    findings TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_compliance_verifications_plan ON compliance_verifications(plan_id);

CREATE TABLE IF NOT EXISTS airworthiness_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    project_id VARCHAR(50) NOT NULL,
    aircraft_model VARCHAR(50) NOT NULL,
    approval_type VARCHAR(30) NOT NULL,
    authority VARCHAR(50),
    application_date DATE,
    approval_date DATE,
    approval_status VARCHAR(20) DEFAULT 'applied',
    certificate_number VARCHAR(100),
    conditions JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS continuous_airworthiness_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aircraft_serial_number VARCHAR(50) NOT NULL,
    record_type VARCHAR(30) NOT NULL,
    description TEXT,
    compliance_status VARCHAR(20) DEFAULT 'compliant',
    next_due_date DATE,
    responsible_person VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cont_airworthiness_sn ON continuous_airworthiness_records(aircraft_serial_number);

-- MES Enhancement tables
CREATE TABLE IF NOT EXISTS adaptive_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    schedule_id VARCHAR(50) NOT NULL,
    adjustment_reason VARCHAR(100),
    original_plan JSONB DEFAULT '{}',
    adjusted_plan JSONB DEFAULT '{}',
    adjustment_score FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quality_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    predicted_defect_rate FLOAT DEFAULT 0,
    confidence FLOAT DEFAULT 0,
    risk_factors JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    predicted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS process_optimizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    process_id VARCHAR(50) NOT NULL,
    optimization_type VARCHAR(30),
    original_params JSONB DEFAULT '{}',
    optimized_params JSONB DEFAULT '{}',
    improvement_percent FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Supply Chain Network tables
CREATE TABLE IF NOT EXISTS supplier_network_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    supplier_id VARCHAR(50) NOT NULL,
    node_type VARCHAR(30) NOT NULL,
    tier_level INTEGER DEFAULT 1,
    risk_score FLOAT DEFAULT 0,
    connectivity_score FLOAT DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS supplier_risk_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    supplier_id VARCHAR(50) NOT NULL,
    risk_type VARCHAR(30) NOT NULL,
    risk_level VARCHAR(20) DEFAULT 'low',
    description TEXT,
    mitigation_actions JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS smart_purchase_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    order_number VARCHAR(50) NOT NULL,
    supplier_id VARCHAR(50) NOT NULL,
    material_code VARCHAR(50) NOT NULL,
    quantity FLOAT NOT NULL,
    suggested_price FLOAT,
    optimal_order_time TIMESTAMPTZ,
    risk_adjusted_lead_time_days INTEGER,
    status VARCHAR(20) DEFAULT 'suggested',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Knowledge Graph tables
CREATE TABLE IF NOT EXISTS knowledge_graph_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(30) NOT NULL,
    entity_id VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    properties JSONB DEFAULT '{}',
    embedding_vector VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kg_entities_type ON knowledge_graph_entities(entity_type);

CREATE TABLE IF NOT EXISTS knowledge_graph_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID REFERENCES knowledge_graph_entities(id),
    target_entity_id UUID REFERENCES knowledge_graph_entities(id),
    relation_type VARCHAR(50) NOT NULL,
    properties JSONB DEFAULT '{}',
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kg_relations_source ON knowledge_graph_relations(source_entity_id);
CREATE INDEX idx_kg_relations_target ON knowledge_graph_relations(target_entity_id);

-- AI Decision Support
CREATE TABLE IF NOT EXISTS ai_decision_supports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    decision_type VARCHAR(50) NOT NULL,
    context JSONB DEFAULT '{}',
    recommendations JSONB DEFAULT '[]',
    confidence_score FLOAT DEFAULT 0,
    reasoning TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    decided_by VARCHAR(50),
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Developer Portal & Plugin Marketplace
CREATE TABLE IF NOT EXISTS developer_portal_apps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    developer_id VARCHAR(50) NOT NULL,
    app_name VARCHAR(100) NOT NULL,
    app_type VARCHAR(30) NOT NULL,
    description TEXT,
    api_key_hash VARCHAR(128),
    status VARCHAR(20) DEFAULT 'pending_review',
    download_count INTEGER DEFAULT 0,
    rating FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS plugin_marketplace_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_name VARCHAR(100) NOT NULL,
    plugin_type VARCHAR(30) NOT NULL,
    version VARCHAR(20) NOT NULL,
    author VARCHAR(100),
    description TEXT,
    price FLOAT DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'CNY',
    status VARCHAR(20) DEFAULT 'active',
    install_count INTEGER DEFAULT 0,
    rating FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enterprise Enhancement tables
CREATE TABLE IF NOT EXISTS multi_site_sync_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_site VARCHAR(50) NOT NULL,
    target_site VARCHAR(50) NOT NULL,
    sync_type VARCHAR(30) NOT NULL,
    records_synced INTEGER DEFAULT 0,
    conflicts_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS data_lake_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    job_type VARCHAR(30) NOT NULL,
    source VARCHAR(50),
    query_text TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    result_location VARCHAR(200),
    records_processed INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_training_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    dataset_name VARCHAR(100) NOT NULL,
    dataset_type VARCHAR(30) NOT NULL,
    data_source VARCHAR(100),
    record_count INTEGER DEFAULT 0,
    feature_count INTEGER DEFAULT 0,
    version VARCHAR(20) DEFAULT '1.0',
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_training_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    dataset_id UUID REFERENCES ai_training_datasets(id),
    model_type VARCHAR(50) NOT NULL,
    hyperparameters JSONB DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);