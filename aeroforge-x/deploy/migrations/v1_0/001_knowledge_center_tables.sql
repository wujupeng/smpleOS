-- ============================================================
-- AeroForge-X v1.0 Knowledge Center Database Migration
-- Tables: knowledge_graphs, knowledge_nodes, knowledge_links,
--         graph_snapshots, impact_analysis_results,
--         inference_results, knowledge_quality_metrics,
--         knowledge_anomalies
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Knowledge Graphs (aggregate root)
CREATE TABLE IF NOT EXISTS knowledge_graphs (
    graph_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name           VARCHAR(255) NOT NULL,
    description    TEXT,
    version        INTEGER NOT NULL DEFAULT 1,
    status         VARCHAR(32) NOT NULL DEFAULT 'draft',
    node_count     INTEGER NOT NULL DEFAULT 0,
    link_count     INTEGER NOT NULL DEFAULT 0,
    metadata       JSONB DEFAULT '{}',
    created_by     UUID,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_knowledge_graphs_status ON knowledge_graphs(status);
CREATE INDEX idx_knowledge_graphs_created_by ON knowledge_graphs(created_by);

-- Knowledge Nodes (7 types: requirement, design, structure, material,
--                  manufacturing, flight, maintenance)
CREATE TABLE IF NOT EXISTS knowledge_nodes (
    node_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    graph_id       UUID NOT NULL REFERENCES knowledge_graphs(graph_id) ON DELETE CASCADE,
    node_type      VARCHAR(64) NOT NULL,
    name           VARCHAR(512) NOT NULL,
    properties     JSONB DEFAULT '{}',
    tags           TEXT[] DEFAULT '{}',
    embedding      VECTOR(1536),
    confidence     DECIMAL(5,4) DEFAULT 1.0,
    source         VARCHAR(128) NOT NULL DEFAULT 'manual',
    source_ref     UUID,
    version        INTEGER NOT NULL DEFAULT 1,
    is_inferred    BOOLEAN NOT NULL DEFAULT FALSE,
    created_by     UUID,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_node_graph_type_name UNIQUE (graph_id, node_type, name),
    CONSTRAINT chk_node_type CHECK (node_type IN (
        'requirement', 'design', 'structure', 'material',
        'manufacturing', 'flight', 'maintenance'
    )),
    CONSTRAINT chk_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

CREATE INDEX idx_knowledge_nodes_graph ON knowledge_nodes(graph_id);
CREATE INDEX idx_knowledge_nodes_type ON knowledge_nodes(node_type);
CREATE INDEX idx_knowledge_nodes_source ON knowledge_nodes(source);
CREATE INDEX idx_knowledge_nodes_tags ON knowledge_nodes USING GIN(tags);
CREATE INDEX idx_knowledge_nodes_embedding ON knowledge_nodes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Knowledge Links (7 relation types: derives_from, constrains, implements,
--                  uses_material, produced_by, monitored_by, maintained_by)
CREATE TABLE IF NOT EXISTS knowledge_links (
    link_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    graph_id         UUID NOT NULL REFERENCES knowledge_graphs(graph_id) ON DELETE CASCADE,
    source_node_id   UUID NOT NULL REFERENCES knowledge_nodes(node_id) ON DELETE CASCADE,
    target_node_id   UUID NOT NULL REFERENCES knowledge_nodes(node_id) ON DELETE CASCADE,
    link_type        VARCHAR(64) NOT NULL,
    weight           DECIMAL(5,4) DEFAULT 1.0,
    properties       JSONB DEFAULT '{}',
    confidence       DECIMAL(5,4) DEFAULT 1.0,
    bidirectional    BOOLEAN NOT NULL DEFAULT FALSE,
    is_inferred      BOOLEAN NOT NULL DEFAULT FALSE,
    version          INTEGER NOT NULL DEFAULT 1,
    created_by       UUID,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_link_source_target_type UNIQUE (source_node_id, target_node_id, link_type),
    CONSTRAINT chk_link_type CHECK (link_type IN (
        'derives_from', 'constrains', 'implements', 'uses_material',
        'produced_by', 'monitored_by', 'maintained_by',
        'affects', 'depends_on', 'verified_by', 'supersedes'
    )),
    CONSTRAINT chk_link_confidence CHECK (confidence >= 0 AND confidence <= 1),
    CONSTRAINT chk_link_no_self REFERENCE CHECK (source_node_id != target_node_id)
);

CREATE INDEX idx_knowledge_links_graph ON knowledge_links(graph_id);
CREATE INDEX idx_knowledge_links_source ON knowledge_links(source_node_id);
CREATE INDEX idx_knowledge_links_target ON knowledge_links(target_node_id);
CREATE INDEX idx_knowledge_links_type ON knowledge_links(link_type);

-- Graph Snapshots
CREATE TABLE IF NOT EXISTS graph_snapshots (
    snapshot_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    graph_id       UUID NOT NULL REFERENCES knowledge_graphs(graph_id) ON DELETE CASCADE,
    graph_version  INTEGER NOT NULL,
    name           VARCHAR(255) NOT NULL,
    description    TEXT,
    node_count     INTEGER NOT NULL DEFAULT 0,
    link_count     INTEGER NOT NULL DEFAULT 0,
    checksum       VARCHAR(128) NOT NULL,
    snapshot_data  JSONB,
    created_by     UUID,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_graph_snapshots_graph ON graph_snapshots(graph_id);
CREATE INDEX idx_graph_snapshots_version ON graph_snapshots(graph_version);

-- Impact Analysis Results
CREATE TABLE IF NOT EXISTS impact_analysis_results (
    result_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    graph_id           UUID NOT NULL REFERENCES knowledge_graphs(graph_id) ON DELETE CASCADE,
    source_node_id     UUID NOT NULL REFERENCES knowledge_nodes(node_id) ON DELETE CASCADE,
    propagation_depth  INTEGER NOT NULL DEFAULT 3,
    affected_nodes     JSONB NOT NULL DEFAULT '[]',
    impact_paths       JSONB NOT NULL DEFAULT '[]',
    total_impact_score DECIMAL(10,6) DEFAULT 0,
    is_partial         BOOLEAN NOT NULL DEFAULT FALSE,
    warnings           TEXT[] DEFAULT '{}',
    computation_ms     INTEGER,
    created_by         UUID,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_impact_results_graph ON impact_analysis_results(graph_id);
CREATE INDEX idx_impact_results_source ON impact_analysis_results(source_node_id);

-- Inference Results
CREATE TABLE IF NOT EXISTS inference_results (
    inference_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    graph_id        UUID NOT NULL REFERENCES knowledge_graphs(graph_id) ON DELETE CASCADE,
    input_node_ids  UUID[] NOT NULL,
    inferred_links  JSONB NOT NULL DEFAULT '[]',
    confidence      DECIMAL(5,4) NOT NULL,
    reasoning_type  VARCHAR(64) NOT NULL DEFAULT 'transitive',
    explanation     TEXT,
    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_reasoning_type CHECK (reasoning_type IN (
        'transitive', 'analogical', 'statistical', 'rule_based'
    ))
);

CREATE INDEX idx_inference_results_graph ON inference_results(graph_id);

-- Knowledge Quality Metrics
CREATE TABLE IF NOT EXISTS knowledge_quality_metrics (
    metric_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    graph_id       UUID NOT NULL REFERENCES knowledge_graphs(graph_id) ON DELETE CASCADE,
    completeness   DECIMAL(5,4) DEFAULT 0,
    consistency    DECIMAL(5,4) DEFAULT 0,
    timeliness     DECIMAL(5,4) DEFAULT 0,
    connectivity   DECIMAL(5,4) DEFAULT 0,
    coverage       DECIMAL(5,4) DEFAULT 0,
    freshness      DECIMAL(5,4) DEFAULT 0,
    overall_score  DECIMAL(5,4) DEFAULT 0,
    assessed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_quality_metrics_graph ON knowledge_quality_metrics(graph_id);

-- Knowledge Anomalies
CREATE TABLE IF NOT EXISTS knowledge_anomalies (
    anomaly_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    graph_id         UUID NOT NULL REFERENCES knowledge_graphs(graph_id) ON DELETE CASCADE,
    anomaly_type     VARCHAR(64) NOT NULL,
    affected_node_ids UUID[] NOT NULL DEFAULT '{}',
    severity         VARCHAR(16) NOT NULL DEFAULT 'medium',
    description      TEXT NOT NULL,
    remediation      TEXT,
    status           VARCHAR(32) NOT NULL DEFAULT 'open',
    resolved_by      UUID,
    resolved_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_anomaly_type CHECK (anomaly_type IN (
        'contradiction', 'orphan', 'stale', 'duplicate', 'circular', 'weak_confidence'
    )),
    CONSTRAINT chk_anomaly_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT chk_anomaly_status CHECK (status IN ('open', 'acknowledged', 'resolved', 'dismissed'))
);

CREATE INDEX idx_knowledge_anomalies_graph ON knowledge_anomalies(graph_id);
CREATE INDEX idx_knowledge_anomalies_status ON knowledge_anomalies(status);
CREATE INDEX idx_knowledge_anomalies_severity ON knowledge_anomalies(severity);