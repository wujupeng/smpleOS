-- AeroForge-X v1.0 Certification Center Tables
-- Migration: 009_certification_center_tables.sql

CREATE TABLE IF NOT EXISTS certification_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id VARCHAR(64) UNIQUE NOT NULL,
    project_id VARCHAR(64) NOT NULL,
    aircraft_type VARCHAR(64) NOT NULL,
    certification_standard VARCHAR(64) NOT NULL DEFAULT 'FAR-25',
    certification_authority VARCHAR(64) NOT NULL DEFAULT 'FAA',
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    milestones JSONB,
    created_by VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cert_plans_project ON certification_plans(project_id);
CREATE INDEX idx_cert_plans_status ON certification_plans(status);

CREATE TABLE IF NOT EXISTS compliance_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id VARCHAR(64) UNIQUE NOT NULL,
    plan_id VARCHAR(64) NOT NULL REFERENCES certification_plans(plan_id),
    regulation_clause VARCHAR(32) NOT NULL,
    clause_title TEXT NOT NULL,
    compliance_method VARCHAR(16),
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    evidence_refs JSONB,
    responsible_person VARCHAR(64),
    due_date DATE,
    evidence_gap BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_compliance_items_plan ON compliance_items(plan_id);
CREATE INDEX idx_compliance_items_status ON compliance_items(status);
CREATE INDEX idx_compliance_items_gap ON compliance_items(evidence_gap);

CREATE TABLE IF NOT EXISTS compliance_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    verification_id VARCHAR(64) UNIQUE NOT NULL,
    item_id VARCHAR(64) NOT NULL REFERENCES compliance_items(item_id),
    verification_type VARCHAR(32) NOT NULL,
    result VARCHAR(32) NOT NULL DEFAULT 'pending',
    evidence_documents JSONB,
    verified_by VARCHAR(64),
    verified_at TIMESTAMPTZ,
    findings TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_compliance_ver_item ON compliance_verifications(item_id);
CREATE INDEX idx_compliance_ver_type ON compliance_verifications(verification_type);

CREATE TABLE IF NOT EXISTS airworthiness_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_id VARCHAR(64) UNIQUE NOT NULL,
    certification_plan_id VARCHAR(64) NOT NULL REFERENCES certification_plans(plan_id),
    approval_type VARCHAR(64) NOT NULL,
    review_status VARCHAR(32) NOT NULL DEFAULT 'submitted',
    conditions JSONB,
    certificate_number VARCHAR(64),
    approval_date DATE,
    expiry_date DATE,
    submitted_by VARCHAR(64),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by VARCHAR(64)
);

CREATE INDEX idx_aw_approvals_plan ON airworthiness_approvals(certification_plan_id);
CREATE INDEX idx_aw_approvals_status ON airworthiness_approvals(review_status);

CREATE TABLE IF NOT EXISTS review_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id VARCHAR(64) UNIQUE NOT NULL,
    approval_id VARCHAR(64) NOT NULL REFERENCES airworthiness_approvals(approval_id),
    finding_type VARCHAR(32) NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'minor',
    description TEXT NOT NULL,
    corrective_action TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    due_date DATE,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_review_findings_approval ON review_findings(approval_id);
CREATE INDEX idx_review_findings_status ON review_findings(status);

CREATE TABLE IF NOT EXISTS continuous_airworthiness_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_id VARCHAR(64) UNIQUE NOT NULL,
    aircraft_sn VARCHAR(64) NOT NULL,
    record_type VARCHAR(32) NOT NULL,
    description TEXT NOT NULL,
    compliance_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    due_date DATE,
    completed_date DATE,
    responsible_person VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cont_aw_aircraft ON continuous_airworthiness_records(aircraft_sn);
CREATE INDEX idx_cont_aw_type ON continuous_airworthiness_records(record_type);
CREATE INDEX idx_cont_aw_status ON continuous_airworthiness_records(compliance_status);

CREATE TABLE IF NOT EXISTS airworthiness_directives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ad_number VARCHAR(64) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    authority VARCHAR(32) NOT NULL DEFAULT 'FAA',
    effective_date DATE NOT NULL,
    compliance_required_by DATE,
    applicability TEXT,
    description TEXT NOT NULL,
    compliance_action TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    affected_aircraft JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ad_status ON airworthiness_directives(status);
CREATE INDEX idx_ad_effective ON airworthiness_directives(effective_date);

CREATE TABLE IF NOT EXISTS service_bulletins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sb_number VARCHAR(64) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    issuer VARCHAR(64) NOT NULL,
    issue_date DATE NOT NULL,
    priority VARCHAR(16) NOT NULL DEFAULT 'advisory',
    applicability TEXT,
    description TEXT NOT NULL,
    compliance_action TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    affected_aircraft JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sb_status ON service_bulletins(status);
CREATE INDEX idx_sb_priority ON service_bulletins(priority);