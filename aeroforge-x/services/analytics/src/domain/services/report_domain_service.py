from __future__ import annotations

import logging
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from ..entities.report import Report, ReportFormat, ReportStatus, ReportTemplate
from ..services.analytics_domain_service import AnalyticsDomainService

logger = logging.getLogger(__name__)

TEMPLATE_DEFINITIONS: dict[str, dict[str, Any]] = {
    ReportTemplate.PROJECT_WEEKLY: {
        "name": "项目进度周报",
        "description": "项目设计进度、CAE分析完成率、迭代统计",
        "domains": ["design"],
        "default_format": ReportFormat.PDF,
    },
    ReportTemplate.QUALITY_MONTHLY: {
        "name": "质量月报",
        "description": "IQC合格率、CAPA关闭率、SPC过程能力指数",
        "domains": ["quality"],
        "default_format": ReportFormat.PDF,
    },
    ReportTemplate.SUPPLIER_QUARTERLY: {
        "name": "供应商绩效季报",
        "description": "供应商绩效排名、采购准时率、库存周转率",
        "domains": ["supply_chain"],
        "default_format": ReportFormat.EXCEL,
    },
    ReportTemplate.PRODUCTION_DAILY: {
        "name": "生产效率日报",
        "description": "工单完成率、工位利用率、制造偏差",
        "domains": ["manufacturing"],
        "default_format": ReportFormat.HTML,
    },
    ReportTemplate.TRACE_AUDIT: {
        "name": "追溯完整性审计报告",
        "description": "追溯链完整性、查询响应时间、批次召回范围",
        "domains": ["traceability"],
        "default_format": ReportFormat.PDF,
    },
}


class ReportDomainService:
    def __init__(self) -> None:
        self._reports: dict[str, Report] = {}
        self._analytics = AnalyticsDomainService()

    def create_report(
        self,
        tenant_id: str,
        name: str,
        report_type: str,
        template_id: str = "",
        parameters: dict[str, Any] | None = None,
        format: ReportFormat = ReportFormat.PDF,
        generated_by: str = "",
    ) -> Report:
        report = Report(
            tenant_id=tenant_id,
            name=name,
            report_type=report_type,
            template_id=template_id,
            parameters=parameters or {},
            format=format,
            generated_by=generated_by,
        )

        self._reports[report.id] = report

        report.add_domain_event(DomainEvent(
            event_type="report.created",
            aggregate_id=report.id,
            payload={"report_id": report.id, "name": name},
        ))

        logger.info("Created report %s: %s", report.id, name)
        return report

    def generate_report(self, report_id: str) -> Report | None:
        report = self._reports.get(report_id)
        if report is None:
            return None

        report.status = ReportStatus.GENERATING

        try:
            data = self._fetch_report_data(report)
            content = self._render_report(report, data)
            file_key = f"reports/{report.tenant_id}/{report.id}.{report.format.value}"
            file_size = len(content.encode('utf-8')) if isinstance(content, str) else len(content)

            report.complete(file_key, file_size)
            logger.info("Report %s generated: %s (%d bytes)", report_id, file_key, file_size)
        except Exception as e:
            report.fail(str(e))
            logger.error("Report %s generation failed: %s", report_id, e)

        return report

    def schedule_report(self, report_id: str, cron_expression: str) -> Report | None:
        report = self._reports.get(report_id)
        if report is None:
            return None
        report.schedule_cron = cron_expression
        return report

    def share_report(self, report_id: str) -> Report | None:
        report = self._reports.get(report_id)
        if report is None:
            return None
        import secrets
        report.share_token = secrets.token_urlsafe(16)
        return report

    def get_report(self, report_id: str) -> Report | None:
        return self._reports.get(report_id)

    def list_reports(
        self,
        tenant_id: str | None = None,
        report_type: str | None = None,
        status: ReportStatus | None = None,
    ) -> list[Report]:
        reports = list(self._reports.values())
        if tenant_id:
            reports = [r for r in reports if r.tenant_id == tenant_id]
        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        if status:
            reports = [r for r in reports if r.status == status]
        return reports

    def get_templates(self) -> dict[str, dict[str, Any]]:
        return TEMPLATE_DEFINITIONS

    def _fetch_report_data(self, report: Report) -> dict[str, Any]:
        template = TEMPLATE_DEFINITIONS.get(report.template_id, {})
        domains = template.get("domains", [])
        project_id = report.parameters.get("project_id")
        data: dict[str, Any] = {}

        if "design" in domains:
            data["design"] = self._analytics.query_design_metrics(project_id)
        if "manufacturing" in domains:
            data["manufacturing"] = self._analytics.query_manufacturing_metrics(project_id)
        if "quality" in domains:
            data["quality"] = self._analytics.query_quality_metrics(project_id)
        if "traceability" in domains:
            data["traceability"] = self._analytics.query_traceability_metrics(project_id)
        if "supply_chain" in domains:
            data["supply_chain"] = self._analytics.query_supply_chain_metrics(project_id)

        if not domains:
            data = self._analytics.cross_domain_analysis(project_id)

        return data

    def _render_report(self, report: Report, data: dict[str, Any]) -> str:
        if report.format == ReportFormat.HTML:
            return self._render_html(report, data)
        elif report.format == ReportFormat.EXCEL:
            return self._render_csv(report, data)
        else:
            return self._render_html(report, data)

    def _render_html(self, report: Report, data: dict[str, Any]) -> str:
        lines = [
            "<!DOCTYPE html>",
            "<html><head>",
            f"<title>{report.name}</title>",
            "<style>body{font-family:sans-serif;margin:20px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:8px;text-align:left}th{background:#f5f5f5}</style>",
            "</head><body>",
            f"<h1>{report.name}</h1>",
            f"<p>生成时间: {datetime.now(timezone.utc).isoformat()}</p>",
        ]

        for domain, metrics in data.items():
            if isinstance(metrics, dict):
                lines.append(f"<h2>{domain}</h2>")
                lines.append("<table><tr><th>指标</th><th>值</th></tr>")
                for key, value in metrics.items():
                    if not isinstance(value, (list, dict)):
                        lines.append(f"<tr><td>{key}</td><td>{value}</td></tr>")
                lines.append("</table>")

        lines.append("</body></html>")
        return "\n".join(lines)

    def _render_csv(self, report: Report, data: dict[str, Any]) -> str:
        lines = [f"# {report.name}", f"# Generated: {datetime.now(timezone.utc).isoformat()}", ""]
        for domain, metrics in data.items():
            if isinstance(metrics, dict):
                lines.append(f"## {domain}")
                for key, value in metrics.items():
                    if not isinstance(value, (list, dict)):
                        lines.append(f"{key},{value}")
                lines.append("")
        return "\n".join(lines)


from datetime import datetime, timezone  # noqa: E402