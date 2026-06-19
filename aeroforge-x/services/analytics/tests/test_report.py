import pytest

from services.analytics.src.domain.entities.report import Report, ReportFormat, ReportStatus, ReportTemplate
from services.analytics.src.domain.services.report_domain_service import ReportDomainService


class TestReportEntity:
    def test_create_report(self) -> None:
        report = Report(name="Test Report", report_type="quality_monthly")
        assert report.status == ReportStatus.GENERATING
        assert report.format == ReportFormat.PDF

    def test_complete_report(self) -> None:
        report = Report(name="Test")
        report.complete("reports/t-001/r-001.pdf", 1024)
        assert report.status == ReportStatus.COMPLETED
        assert report.file_key == "reports/t-001/r-001.pdf"
        assert report.file_size_bytes == 1024
        assert len(report.domain_events) == 1

    def test_fail_report(self) -> None:
        report = Report(name="Test")
        report.fail("generation error")
        assert report.status == ReportStatus.FAILED

    def test_report_to_dict(self) -> None:
        report = Report(name="Test", tenant_id="t-001", format=ReportFormat.HTML)
        d = report.to_dict()
        assert d["name"] == "Test"
        assert d["format"] == "html"


class TestReportDomainService:
    def test_create_report(self) -> None:
        service = ReportDomainService()
        report = service.create_report(
            tenant_id="t-001",
            name="Quality Monthly Report",
            report_type="quality_monthly",
            template_id="quality_monthly",
            format=ReportFormat.PDF,
        )
        assert report.name == "Quality Monthly Report"
        assert len(report.domain_events) == 1

    def test_generate_report_html(self) -> None:
        service = ReportDomainService()
        report = service.create_report(
            "t-001", "Test Report", "project_weekly",
            template_id="project_weekly",
            format=ReportFormat.HTML,
        )
        result = service.generate_report(report.id)
        assert result is not None
        assert result.status == ReportStatus.COMPLETED
        assert result.file_key != ""
        assert result.file_size_bytes > 0

    def test_generate_report_pdf(self) -> None:
        service = ReportDomainService()
        report = service.create_report(
            "t-001", "PDF Report", "quality_monthly",
            template_id="quality_monthly",
            format=ReportFormat.PDF,
        )
        result = service.generate_report(report.id)
        assert result is not None
        assert result.status == ReportStatus.COMPLETED

    def test_generate_report_excel(self) -> None:
        service = ReportDomainService()
        report = service.create_report(
            "t-001", "Excel Report", "supplier_quarterly",
            template_id="supplier_quarterly",
            format=ReportFormat.EXCEL,
        )
        result = service.generate_report(report.id)
        assert result is not None
        assert result.status == ReportStatus.COMPLETED

    def test_generate_report_not_found(self) -> None:
        service = ReportDomainService()
        result = service.generate_report("nonexistent")
        assert result is None

    def test_schedule_report(self) -> None:
        service = ReportDomainService()
        report = service.create_report("t-001", "Scheduled", "production_daily")
        scheduled = service.schedule_report(report.id, "0 8 * * *")
        assert scheduled is not None
        assert scheduled.schedule_cron == "0 8 * * *"

    def test_share_report(self) -> None:
        service = ReportDomainService()
        report = service.create_report("t-001", "Shared", "trace_audit")
        service.generate_report(report.id)
        shared = service.share_report(report.id)
        assert shared is not None
        assert shared.share_token != ""

    def test_list_reports(self) -> None:
        service = ReportDomainService()
        service.create_report("t-001", "Report A", "project_weekly")
        service.create_report("t-002", "Report B", "quality_monthly")
        assert len(service.list_reports()) == 2
        assert len(service.list_reports(tenant_id="t-001")) == 1

    def test_get_templates(self) -> None:
        service = ReportDomainService()
        templates = service.get_templates()
        assert "project_weekly" in templates
        assert "quality_monthly" in templates
        assert "supplier_quarterly" in templates
        assert "production_daily" in templates
        assert "trace_audit" in templates