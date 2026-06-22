-- AeroForge-X v2.0 Aircraft Core Data Model Schema
-- 关联需求：REQ-ACD-001 ~ REQ-ACD-043

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE SCHEMA IF NOT EXISTS aircraft_core;

CREATE TABLE aircraft_core.aircraft_objects (
    id              VARCHAR(64) PRIMARY KEY,
    object_type     VARCHAR(32) NOT NULL,
    name            VARCHAR(200) NOT NULL,
    lifecycle_state VARCHAR(32) NOT NULL DEFAULT 'Concept',
    design_data     JSONB DEFAULT '{}',
    manufacturing_data JSONB DEFAULT '{}',
    operation_data  JSONB DEFAULT '{}',
    certification_data JSONB DEFAULT '{}',
    optimistic_lock_version INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_object_type CHECK (object_type IN ('Aircraft','System','Subsystem','Component','Part')),
    CONSTRAINT chk_lifecycle_state CHECK (lifecycle_state IN ('Concept','Design','Manufacturing','Test','Operation','Retirement'))
);

CREATE INDEX idx_aircraft_objects_type ON aircraft_core.aircraft_objects (object_type);
CREATE INDEX idx_aircraft_objects_lifecycle ON aircraft_core.aircraft_objects (lifecycle_state);
CREATE INDEX idx_aircraft_objects_name ON aircraft_core.aircraft_objects USING gin (name gin_trgm_ops);
CREATE INDEX idx_aircraft_objects_design_data ON aircraft_core.aircraft_objects USING gin (design_data);
CREATE INDEX idx_aircraft_objects_updated_at ON aircraft_core.aircraft_objects (updated_at);

CREATE TABLE aircraft_core.aircraft_object_versions (
    version_id      VARCHAR(128) PRIMARY KEY,
    object_id       VARCHAR(64) NOT NULL REFERENCES aircraft_core.aircraft_objects(id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL,
    snapshot        JSONB NOT NULL,
    change_summary  VARCHAR(1000) NOT NULL,
    author          VARCHAR(128) NOT NULL,
    baseline_type   VARCHAR(32) NOT NULL DEFAULT 'None',
    is_frozen       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_baseline_type CHECK (baseline_type IN ('None','Frozen','Released')),
    CONSTRAINT uq_object_version UNIQUE (object_id, version_number)
);

CREATE INDEX idx_versions_object_id ON aircraft_core.aircraft_object_versions (object_id);
CREATE INDEX idx_versions_frozen ON aircraft_core.aircraft_object_versions (is_frozen) WHERE is_frozen = TRUE;

CREATE TABLE aircraft_core.aircraft_object_links (
    link_id         VARCHAR(64) PRIMARY KEY,
    source_object_id VARCHAR(64) NOT NULL REFERENCES aircraft_core.aircraft_objects(id) ON DELETE CASCADE,
    target_object_id VARCHAR(64) NOT NULL REFERENCES aircraft_core.aircraft_objects(id) ON DELETE CASCADE,
    link_type       VARCHAR(32) NOT NULL,
    propagation_rule JSONB DEFAULT '{}',
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_link_type CHECK (link_type IN ('contains','depends_on','trace_to','change_propagates_to')),
    CONSTRAINT chk_no_self_reference CHECK (source_object_id != target_object_id)
);

CREATE INDEX idx_links_source ON aircraft_core.aircraft_object_links (source_object_id, link_type);
CREATE INDEX idx_links_target ON aircraft_core.aircraft_object_links (target_object_id, link_type);

CREATE TABLE aircraft_core.property_definitions (
    id                      VARCHAR(64) PRIMARY KEY,
    name                    VARCHAR(100) NOT NULL,
    property_type           VARCHAR(32) NOT NULL,
    data_type               VARCHAR(32) NOT NULL,
    unit                    VARCHAR(64) NOT NULL,
    constraints             JSONB DEFAULT '{}',
    applicable_object_types VARCHAR(32)[] NOT NULL,
    derivation_formula      TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_property_type CHECK (property_type IN ('Geometric','Material','Performance','Certification','Cost')),
    CONSTRAINT chk_data_type CHECK (data_type IN ('Float','Integer','String','Boolean','JSON')),
    CONSTRAINT uq_property_name_type UNIQUE (name, property_type)
);

CREATE TABLE aircraft_core.aircraft_property_values (
    value_id                VARCHAR(64) PRIMARY KEY,
    object_id               VARCHAR(64) NOT NULL REFERENCES aircraft_core.aircraft_objects(id) ON DELETE CASCADE,
    property_definition_id  VARCHAR(64) NOT NULL REFERENCES aircraft_core.property_definitions(id),
    value                   JSONB NOT NULL,
    source_tag              VARCHAR(32) NOT NULL,
    source_detail           VARCHAR(500),
    confidence              FLOAT DEFAULT 1.0,
    version_id              VARCHAR(128) NOT NULL REFERENCES aircraft_core.aircraft_object_versions(version_id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_source_tag CHECK (source_tag IN ('DesignValue','MeasuredValue','InferredValue'))
);

CREATE INDEX idx_property_values_object ON aircraft_core.aircraft_property_values (object_id);
CREATE INDEX idx_property_values_def ON aircraft_core.aircraft_property_values (property_definition_id);
CREATE INDEX idx_property_values_source ON aircraft_core.aircraft_property_values (source_tag);