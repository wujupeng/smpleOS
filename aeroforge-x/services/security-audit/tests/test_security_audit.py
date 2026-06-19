import pytest

from services.security_audit.src.security_audit_service import (
    SecurityAuditService, AuditSeverity, AuditCategory, ComplianceStandard,
)


class TestAccessControlAudit:
    def test_default_config_passes(self) -> None:
        service = SecurityAuditService()
        report = service.audit_access_control()
        assert report.passed is True
        assert report.compliance_score >= 80

    def test_no_rbac_fails(self) -> None:
        service = SecurityAuditService()
        report = service.audit_access_control({"rbac_enabled": False})
        assert report.passed is False
        assert any(f.severity == AuditSeverity.CRITICAL for f in report.findings)

    def test_no_mfa_warning(self) -> None:
        service = SecurityAuditService()
        report = service.audit_access_control({"mfa_enabled": False})
        assert any(f.title == "多因素认证未启用" for f in report.findings)

    def test_weak_password_policy(self) -> None:
        service = SecurityAuditService()
        report = service.audit_access_control({"password_policy": {"min_length": 6}})
        assert any("密码策略" in f.title for f in report.findings)

    def test_long_session_duration(self) -> None:
        service = SecurityAuditService()
        report = service.audit_access_control({"max_session_duration_hours": 48})
        assert any("会话超时" in f.title for f in report.findings)


class TestDataIntegrityAudit:
    def test_default_config_passes(self) -> None:
        service = SecurityAuditService()
        report = service.audit_data_integrity()
        assert report.passed is True

    def test_no_checksum_fails(self) -> None:
        service = SecurityAuditService()
        report = service.audit_data_integrity({"checksum_verification": False})
        assert report.passed is False

    def test_no_version_control_fails(self) -> None:
        service = SecurityAuditService()
        report = service.audit_data_integrity({"version_control_enabled": False})
        assert report.passed is False

    def test_insufficient_log_retention(self) -> None:
        service = SecurityAuditService()
        report = service.audit_data_integrity({"audit_log_retention_days": 180})
        assert any("保留期" in f.title for f in report.findings)


class TestChangeManagementAudit:
    def test_no_unapproved_changes(self) -> None:
        service = SecurityAuditService()
        report = service.audit_change_management([
            {"title": "Test Change", "status": "implemented", "approved_by": "chief", "affected_items": ["interior-001"]},
        ])
        assert report.passed is True

    def test_unapproved_change_detected(self) -> None:
        service = SecurityAuditService()
        report = service.audit_change_management([
            {"title": "Unapproved", "status": "implemented", "approved_by": None, "affected_items": []},
        ])
        assert report.passed is False
        assert any("未经批准" in f.title for f in report.findings)

    def test_safety_critical_without_required_approver(self) -> None:
        service = SecurityAuditService()
        report = service.audit_change_management([
            {
                "title": "Wing Material Change",
                "status": "implemented",
                "approved_by": "eng-1",
                "affected_items": ["wing-spar-001"],
                "approvers": [{"role": "engineer"}],
            },
        ])
        assert any(f.category == AuditCategory.SAFETY_CRITICAL for f in report.findings)

    def test_safety_critical_with_required_approvers(self) -> None:
        service = SecurityAuditService()
        report = service.audit_change_management([
            {
                "title": "Wing Material Change",
                "status": "implemented",
                "approved_by": "chief",
                "affected_items": ["wing-spar-001"],
                "approvers": [
                    {"role": "chief_engineer"},
                    {"role": "quality_manager"},
                    {"role": "design_authority"},
                ],
            },
        ])
        assert not any(f.category == AuditCategory.SAFETY_CRITICAL for f in report.findings)


class TestTraceabilityAudit:
    def test_full_traceability(self) -> None:
        service = SecurityAuditService()
        report = service.audit_traceability({
            "ebom_items": [{"part_id": "wing-001"}, {"part_id": "fuse-001"}],
            "mbom_items": [{"part_id": "wing-001"}, {"part_id": "fuse-001"}],
            "sbom_items": [{"part_id": "wing-001"}],
        })
        assert report.passed is True

    def test_unmapped_ebom_items(self) -> None:
        service = SecurityAuditService()
        report = service.audit_traceability({
            "ebom_items": [{"part_id": "wing-001"}, {"part_id": "fuse-001"}],
            "mbom_items": [{"part_id": "wing-001"}],
        })
        assert any("未映射" in f.title for f in report.findings)

    def test_safety_critical_without_serial(self) -> None:
        service = SecurityAuditService()
        report = service.audit_traceability({
            "ebom_items": [],
            "mbom_items": [{"part_id": "wing-001", "safety_critical": True, "serial_tracked": False}],
        })
        assert any("序列号追踪" in f.title for f in report.findings)


class TestAPISecurityAudit:
    def test_default_config_passes(self) -> None:
        service = SecurityAuditService()
        report = service.audit_api_security()
        assert report.passed is True

    def test_no_input_validation_fails(self) -> None:
        service = SecurityAuditService()
        report = service.audit_api_security({"input_validation_enabled": False})
        assert report.passed is False

    def test_no_tls_fails(self) -> None:
        service = SecurityAuditService()
        report = service.audit_api_security({"tls_enabled": False})
        assert report.passed is False


class TestFullAudit:
    def test_full_audit_with_defaults(self) -> None:
        service = SecurityAuditService()
        result = service.run_full_audit()
        assert "overall_score" in result
        assert "overall_passed" in result
        assert "reports" in result
        assert len(result["reports"]) == 5
        assert result["overall_passed"] is True

    def test_full_audit_with_issues(self) -> None:
        service = SecurityAuditService()
        result = service.run_full_audit(
            access_config={"rbac_enabled": False},
            integrity_config={"checksum_verification": False},
            api_config={"tls_enabled": False},
        )
        assert result["overall_passed"] is False
        assert result["critical_count"] >= 3