-- ============================================================
-- AeroForge-X v1.0 Configuration Management Center Database Migration
-- Tables: config_items, config_item_versions, config_baselines,
--         config_baseline_items, config_changes,
--         config_change_propagations, config_compatibility_rules
-- ============================================================

-- Configuration Items (aggregate root)
CREATE TABLE IF NOT EXISTS config_items (
    item_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_number    VARCHAR(128) NOT NULL,
    item_name      VARCHAR(512) NOT NULL,
    item_type      VARCHAR(64) NOT NULL,
    description    TEXT,
    current_version INTEGER NOT NULL DEFAULT 1,
    status         VARCHAR(32) NOT NULL DEFAULT 'draft',
    lifecycle      VARCHAR(32) NOT NULL DEFAULT 'development',
    owner_id       UUID,
    properties     JSONB DEFAULT '{}',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_config_item_number UNIQUE (item_number),
    CONSTRAINT chk_config_item_type CHECK (item_type IN (
        'aircraft', 'wing', 'tail', 'fuselage', 'powertrain',
        'flight_control', 'avionics', 'wire_harness', 'battery',
        'motor', 'esc', 'propeller', 'sensor', 'software', 'hardware'
    )),
    CONSTRAINT chk_config_item_status CHECK (status IN (
        'draft', 'released', 'baselined', 'obsolete'
    )),
    CONSTRAINT chk_config_lifecycle CHECK (lifecycle IN (
        'development', 'production', 'service', 'retired'
    ))
);

CREATE INDEX idx_config_items_type ON config_items(item_type);
CREATE INDEX idx_config_items_status ON config_items(status);
CREATE INDEX idx_config_items_lifecycle ON config_items(lifecycle);
CREATE INDEX idx_config_items_owner ON config_items(owner_id);

-- Configuration Item Versions
CREATE TABLE IF NOT EXISTS config_item_versions (
    version_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id        UUID NOT NULL REFERENCES config_items(item_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    change_summary TEXT,
    properties     JSONB DEFAULT '{}',
    author_id      UUID,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_config_item_version UNIQUE (item_id, version_number)
);

CREATE INDEX idx_config_item_versions_item ON config_item_versions(item_id);

-- Configuration Baselines (aggregate root)
CREATE TABLE IF NOT EXISTS config_baselines (
    baseline_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    baseline_name  VARCHAR(255) NOT NULL,
    baseline_type  VARCHAR(64) NOT NULL,
    description    TEXT,
    version        INTEGER NOT NULL DEFAULT 1,
    status         VARCHAR(32) NOT NULL DEFAULT 'open',
    frozen_at      TIMESTAMPTZ,
    frozen_by      UUID,
    aircraft_config VARCHAR(128),
    created_by     UUID,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_baseline_type CHECK (baseline_type IN (
        'functional', 'allocated', 'product', 'development', 'production'
    )),
    CONSTRAINT chk_baseline_status CHECK (status IN (
        'open', 'frozen', 'released', 'archived'
    ))
);

CREATE INDEX idx_config_baselines_type ON config_baselines(baseline_type);
CREATE INDEX idx_config_baselines_status ON config_baselines(status);

-- Baseline-ConfigItem Association
CREATE TABLE IF NOT EXISTS config_baseline_items (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    baseline_id    UUID NOT NULL REFERENCES config_baselines(baseline_id) ON DELETE CASCADE,
    item_id        UUID NOT NULL REFERENCES config_items(item_id) ON DELETE CASCADE,
    item_version   INTEGER NOT NULL,
    added_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_baseline_item UNIQUE (baseline_id, item_id)
);

CREATE INDEX idx_baseline_items_baseline ON config_baseline_items(baseline_id);
CREATE INDEX idx_baseline_items_item ON config_baseline_items(item_id);

-- Configuration Changes (aggregate root)
CREATE TABLE IF NOT EXISTS config_changes (
    change_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    change_type    VARCHAR(64) NOT NULL,
    title          VARCHAR(512) NOT NULL,
    description    TEXT NOT NULL,
    affected_items JSONB NOT NULL DEFAULT '[]',
    propagation_map JSONB DEFAULT '{}',
    status         VARCHAR(32) NOT NULL DEFAULT 'proposed',
    priority       VARCHAR(16) NOT NULL DEFAULT 'medium',
    impact_level   VARCHAR(16) NOT NULL DEFAULT 'minor',
    approver_id    UUID,
    approved_at    TIMESTAMPTZ,
    implemented_at TIMESTAMPTZ,
    requested_by   UUID,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_change_type CHECK (change_type IN (
        'deviation', 'waiver', 'engineering_change', 'correction',
        'improvement', 'safety_mandated'
    )),
    CONSTRAINT chk_change_status CHECK (status IN (
        'proposed', 'under_review', 'approved', 'rejected',
        'implementing', 'completed', 'cancelled'
    )),
    CONSTRAINT chk_change_priority CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT chk_change_impact CHECK (impact_level IN ('minor', 'moderate', 'major', 'critical'))
);

CREATE INDEX idx_config_changes_type ON config_changes(change_type);
CREATE INDEX idx_config_changes_status ON config_changes(status);
CREATE INDEX idx_config_changes_priority ON config_changes(priority);

-- Change Propagations
CREATE TABLE IF NOT EXISTS config_change_propagations (
    propagation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    change_id      UUID NOT NULL REFERENCES config_changes(change_id) ON DELETE CASCADE,
    source_item_id UUID NOT NULL REFERENCES config_items(item_id),
    target_item_id UUID NOT NULL REFERENCES config_items(item_id),
    action         VARCHAR(64) NOT NULL,
    status         VARCHAR(32) NOT NULL DEFAULT 'pending',
    propagated_at  TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_propagation_action CHECK (action IN (
        'update_version', 'add_item', 'remove_item', 'modify_property',
        'change_supplier', 'retest', 'revalidate', 'notify'
    )),
    CONSTRAINT chk_propagation_status CHECK (status IN (
        'pending', 'in_progress', 'completed', 'failed', 'skipped'
    ))
);

CREATE INDEX idx_change_propagations_change ON config_change_propagations(change_id);
CREATE INDEX idx_change_propagations_source ON config_change_propagations(source_item_id);
CREATE INDEX idx_change_propagations_target ON config_change_propagations(target_item_id);

-- Compatibility Rules
CREATE TABLE IF NOT EXISTS config_compatibility_rules (
    rule_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_name      VARCHAR(255) NOT NULL,
    rule_type      VARCHAR(64) NOT NULL,
    source_type    VARCHAR(64) NOT NULL,
    target_type    VARCHAR(64) NOT NULL,
    rule_expression JSONB NOT NULL,
    severity       VARCHAR(16) NOT NULL DEFAULT 'error',
    description    TEXT,
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_rule_type CHECK (rule_type IN (
        'incompatible', 'requires', 'excludes', 'recommends', 'conflicts'
    )),
    CONSTRAINT chk_rule_severity CHECK (severity IN ('info', 'warning', 'error', 'blocker'))
);

CREATE INDEX idx_compatibility_rules_source ON config_compatibility_rules(source_type);
CREATE INDEX idx_compatibility_rules_target ON config_compatibility_rules(target_type);
CREATE INDEX idx_compatibility_rules_active ON config_compatibility_rules(is_active);