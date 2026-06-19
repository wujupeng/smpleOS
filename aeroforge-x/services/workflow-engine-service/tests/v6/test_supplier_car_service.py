"""AeroForge-X V6.0/V6.1 Unit Tests - Supplier CAR Service
REQ-VP-031, REQ-SUP-019~024
"""

import pytest

from src.domain.services.supplier.supplier_car_service import (
    SupplierCARService,
    SupplierQualityIssue,
    CorrectiveActionRequest,
    IssueSeverity,
    IssueStatus,
    CARVerificationStatus,
)


@pytest.fixture
def service():
    return SupplierCARService()


def _make_issue(supplier_id: str = "SUP-001", severity: IssueSeverity = IssueSeverity.MAJOR) -> SupplierQualityIssue:
    return SupplierQualityIssue(
        issue_id=f"ISS-{supplier_id}-001",
        supplier_id=supplier_id,
        issue_type="DimensionalNonConformance",
        description="Out of tolerance",
        severity=severity,
    )


class TestQualityIssueCreation:

    def test_create_quality_issue(self, service):
        issue = _make_issue()
        result = service.createQualityIssue(issue)
        assert result.issue_id == issue.issue_id
        assert result.status == IssueStatus.REPORTED

    def test_create_duplicate_issue_raises(self, service):
        issue = _make_issue()
        service.createQualityIssue(issue)
        with pytest.raises(ValueError, match="already exists"):
            service.createQualityIssue(issue)


class TestCARManagement:

    def test_create_car(self, service):
        issue = _make_issue()
        service.createQualityIssue(issue)
        car = service.createCAR(issue.issue_id)
        assert car.supplier_id == "SUP-001"
        assert car.verification_status == CARVerificationStatus.PENDING

    def test_create_car_nonexistent_issue_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.createCAR("ISS-FAKE")

    def test_car_timeliness(self, service):
        issue = _make_issue()
        service.createQualityIssue(issue)
        car = service.createCAR(issue.issue_id)
        status = service.trackCARTimeliness(car.car_id)
        assert status.car_id == car.car_id


class TestCARVerification:

    def test_verify_car_effective(self, service):
        issue = _make_issue()
        service.createQualityIssue(issue)
        car = service.createCAR(issue.issue_id)
        result = service.verifyCorrectiveAction(car.car_id, is_effective=True)
        assert result.is_effective is True
        assert result.issue_reopened is False
        assert result.supplier_rating_updated is True

    def test_verify_car_not_effective(self, service):
        issue = _make_issue()
        service.createQualityIssue(issue)
        car = service.createCAR(issue.issue_id)
        result = service.verifyCorrectiveAction(car.car_id, is_effective=False)
        assert result.is_effective is False
        assert result.issue_reopened is True
        assert result.enhanced_inspection_triggered is True

    def test_verify_car_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.verifyCorrectiveAction("CAR-FAKE", True)


class TestQualityDashboard:

    def test_generate_dashboard_empty(self, service):
        dashboard = service.generateQualityDashboard()
        assert len(dashboard.top_defect_categories) == 0

    def test_generate_dashboard_with_issues(self, service):
        for i in range(3):
            issue = SupplierQualityIssue(
                issue_id=f"ISS-SUP-{i:03d}",
                supplier_id="SUP-001",
                issue_type="DimensionalNonConformance",
                description=f"Issue {i}",
                severity=IssueSeverity.MAJOR,
            )
            service.createQualityIssue(issue)
        dashboard = service.generateQualityDashboard()
        assert len(dashboard.top_defect_categories) > 0