-- ============================================================
-- AeroForge-X v1.0 PLM/BOM Center Database Migration
-- Tables: product_structures, design_objects, design_object_versions,
--         design_baselines, engineering_change_requests,
--         engineering_change_orders, engineering_change_notices,
--         eboms, mboms, sboms, bom_lines, bom_transformations,
--         bom_sync_records
-- ============================================================

-- Product Structures
CREATE TABLE IF NOT EXISTS product_structures (
    structure_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id     UUID NOT NULL,
    product_name   VARCHAR(512) NOT NULL,
    parent_id      UUID,
    children       JSONB DEFAULT '[]',
    status         VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_product_structures_product ON product_structures(product_id);
CREATE INDEX idx_product_structures_parent ON product_structures(parent_id);

-- Design Objects
CREATE TABLE IF NOT EXISTS design_objects (
    object_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    object_number   VARCHAR(128) NOT NULL,
    object_type     VARCHAR(64) NOT NULL,
    object_name     VARCHAR(512) NOT NULL,
    current_version INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',
    owner_id        UUID,
    properties      JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_design_object_number UNIQUE (object_number),
    CONSTRAINT chk_design_object_type CHECK (object_type IN (
        'assembly', 'part', 'drawing', 'specification', 'document', 'model'
    ))
);

CREATE INDEX idx_design_objects_type ON design_objects(object_type);
CREATE INDEX idx_design_objects_status ON design_objects(status);

-- Design Object Versions
CREATE TABLE IF NOT EXISTS design_object_versions (
    version_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    object_id       UUID NOT NULL REFERENCES design_objects(object_id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL,
    change_summary  TEXT,
    properties      JSONB DEFAULT '{}',
    author_id       UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_design_object_version UNIQUE (object_id, version_number)
);

CREATE INDEX idx_design_object_versions_object ON design_object_versions(object_id);

-- Design Baselines
CREATE TABLE IF NOT EXISTS design_baselines (
    baseline_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    baseline_name   VARCHAR(255) NOT NULL,
    baseline_type   VARCHAR(64) NOT NULL DEFAULT 'development',
    object_versions JSONB NOT NULL DEFAULT '[]',
    status          VARCHAR(32) NOT NULL DEFAULT 'open',
    frozen_at       TIMESTAMPTZ,
    frozen_by       UUID,
    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_baseline_type CHECK (baseline_type IN (
        'development', 'functional', 'allocated', 'product', 'production'
    ))
);

CREATE INDEX idx_design_baselines_status ON design_baselines(status);

-- Engineering Change Requests
CREATE TABLE IF NOT EXISTS engineering_change_requests (
    ecr_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ecr_number      VARCHAR(64) NOT NULL,
    change_type     VARCHAR(64) NOT NULL,
    title           VARCHAR(512) NOT NULL,
    description     TEXT NOT NULL,
    impact_analysis JSONB DEFAULT '{}',
    approval_status VARCHAR(32) NOT NULL DEFAULT 'draft',
    approver_id     UUID,
    approved_at     TIMESTAMPTZ,
    priority        VARCHAR(16) NOT NULL DEFAULT 'medium',
    safety_critical BOOLEAN NOT NULL DEFAULT FALSE,
    requested_by    UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ecr_number UNIQUE (ecr_number),
    CONSTRAINT chk_ecr_type CHECK (change_type IN (
        'correction', 'improvement', 'safety_mandated', 'enhancement',
        'deviation', 'waiver', 'engineering_change'
    )),
    CONSTRAINT chk_ecr_status CHECK (approval_status IN (
        'draft', 'submitted', 'under_review', 'approved', 'rejected', 'cancelled'
    ))
);

CREATE INDEX idx_ecr_status ON engineering_change_requests(approval_status);
CREATE INDEX idx_ecr_priority ON engineering_change_requests(priority);

-- Engineering Change Orders
CREATE TABLE IF NOT EXISTS engineering_change_orders (
    eco_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ecr_id          UUID NOT NULL REFERENCES engineering_change_requests(ecr_id),
    eco_number      VARCHAR(64) NOT NULL,
    implementation_plan TEXT,
    status          VARCHAR(32) NOT NULL DEFAULT 'planned',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_eco_number UNIQUE (eco_number)
);

-- Engineering Change Notices
CREATE TABLE IF NOT EXISTS engineering_change_notices (
    ecn_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    eco_id          UUID NOT NULL REFERENCES engineering_change_orders(eco_id),
    ecn_number      VARCHAR(64) NOT NULL,
    description     TEXT,
    effective_date  DATE,
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ecn_number UNIQUE (ecn_number)
);

-- Engineering BOM
CREATE TABLE IF NOT EXISTS eboms (
    bom_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bom_number      VARCHAR(128) NOT NULL,
    product_id      UUID NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ebom_number UNIQUE (bom_number)
);

-- Manufacturing BOM
CREATE TABLE IF NOT EXISTS mboms (
    bom_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bom_number      VARCHAR(128) NOT NULL,
    product_id      UUID NOT NULL,
    ebom_ref        UUID REFERENCES eboms(bom_id),
    version         INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mbom_number UNIQUE (bom_number)
);

-- Service BOM
CREATE TABLE IF NOT EXISTS sboms (
    bom_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bom_number      VARCHAR(128) NOT NULL,
    product_id      UUID NOT NULL,
    ebom_ref        UUID REFERENCES eboms(bom_id),
    version         INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_sbom_number UNIQUE (bom_number)
);

-- BOM Lines
CREATE TABLE IF NOT EXISTS bom_lines (
    line_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bom_id          UUID NOT NULL,
    bom_type        VARCHAR(16) NOT NULL,
    parent_line_id  UUID,
    part_number     VARCHAR(128) NOT NULL,
    part_name       VARCHAR(512) NOT NULL,
    quantity        DECIMAL(12,4) NOT NULL DEFAULT 1,
    unit            VARCHAR(32) DEFAULT 'ea',
    material_ref    UUID,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    properties      JSONB DEFAULT '{}',
    CONSTRAINT chk_bom_type CHECK (bom_type IN ('ebom', 'mbom', 'sbom'))
);

CREATE INDEX idx_bom_lines_bom ON bom_lines(bom_id);
CREATE INDEX idx_bom_lines_parent ON bom_lines(parent_line_id);
CREATE INDEX idx_bom_lines_part ON bom_lines(part_number);

-- BOM Transformations
CREATE TABLE IF NOT EXISTS bom_transformations (
    transform_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_bom_id   UUID NOT NULL,
    source_type     VARCHAR(16) NOT NULL,
    target_bom_id   UUID,
    target_type     VARCHAR(16) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'pending',
    unmapped_items  JSONB DEFAULT '[]',
    transform_log   JSONB DEFAULT '[]',
    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    CONSTRAINT chk_transform_source CHECK (source_type IN ('ebom', 'mbom')),
    CONSTRAINT chk_transform_target CHECK (target_type IN ('mbom', 'sbom'))
);

-- BOM Sync Records
CREATE TABLE IF NOT EXISTS bom_sync_records (
    sync_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ebom_id         UUID NOT NULL REFERENCES eboms(bom_id),
    target_bom_id   UUID NOT NULL,
    target_type     VARCHAR(16) NOT NULL,
    differences     JSONB DEFAULT '[]',
    sync_status     VARCHAR(32) NOT NULL DEFAULT 'pending',
    synced_by       UUID,
    synced_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);