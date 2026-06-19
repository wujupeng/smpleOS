from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AuditSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ComplianceStandard(str, Enum):
    AS9100D = "AS9100D"
    DO178C = "DO-178C"
    DO254 = "DO-254"
    ARP4754A = "ARP4754A"
    ARP4761 = "ARP4761"
    ISO27001 = "ISO27001"
    NIST800171 = "NIST800-171"


class AuditCategory(str, Enum):
    ACCESS_CONTROL = "access_control"
    DATA_INTEGRITY = "data_integrity"
    CHANGE_MANAGEMENT = "change_management"
    TRACEABILITY = "traceability"
    SAFETY_CRITICAL = "safety_critical"
    DATA_PROTECTION = "data_protection"
    API_SECURITY = "api_security"
    CONFIGURATION_MANAGEMENT = "configuration_management"


@dataclass
class AuditFinding:
    finding_id: str
    category: AuditCategory
    severity: AuditSeverity
    title: str
    description: str
    standard: ComplianceStandard
    clause: str
    remediation: str
    status: str = "open"
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "standard": self.standard.value,
            "clause": self.clause,
            "remediation": self.remediation,
            "status": self.status,
            "evidence": self.evidence,
        }


@dataclass
class AuditReport:
    report_id: str
    audit_type: str
    findings: list[AuditFinding] = field(default_factory=list)
    compliance_score: float = 0.0
    passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "audit_type": self.audit_type,
            "findings": [f.to_dict() for f in self.findings],
            "compliance_score": round(self.compliance_score, 2),
            "passed": self.passed,
            "total_findings": len(self.findings),
            "critical_count": len([f for f in self.findings if f.severity == AuditSeverity.CRITICAL]),
            "warning_count": len([f for f in self.findings if f.severity == AuditSeverity.WARNING]),
            "info_count": len([f for f in self.findings if f.severity == AuditSeverity.INFO]),
        }


SAFETY_CRITICAL_PART_MARKERS = [
    "wing", "spar", "fuselage", "landing_gear", "engine_mount",
    "tail", "rudder", "elevator", "aileron", "flap",
]

REQUIRED_CHANGE_APPROVAL_ROLES = ["chief_engineer", "quality_manager", "design_authority"]

MIN_PASSWORD_LENGTH = 12
MAX_SESSION_DURATION_HOURS = 8
REQUIRED_AUDIT_LOG_RETENTION_DAYS = 365 * 7


class SecurityAuditService:
    def __init__(self) -> None:
        self._finding_counter: int = 0
        self._report_counter: int = 0

    def audit_access_control(self, config: dict[str, Any] | None = None) -> AuditReport:
        self._report_counter += 1
        findings: list[AuditFinding] = []
        config = config or {}

        if not config.get("rbac_enabled", True):
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.ACCESS_CONTROL,
                severity=AuditSeverity.CRITICAL,
                title="RBAC未启用",
                description="基于角色的访问控制(RBAC)未启用，所有用户可能拥有相同权限",
                standard=ComplianceStandard.AS9100D,
                clause="7.2.3",
                remediation="启用RBAC并配置最小权限原则",
            ))

        if not config.get("mfa_enabled", False):
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.ACCESS_CONTROL,
                severity=AuditSeverity.WARNING,
                title="多因素认证未启用",
                description="系统未强制多因素认证(MFA)，增加了未授权访问风险",
                standard=ComplianceStandard.NIST800171,
                clause="3.5.3",
                remediation="为所有用户账户启用MFA",
            ))

        password_policy = config.get("password_policy", {})
        min_length = password_policy.get("min_length", 8)
        if min_length < MIN_PASSWORD_LENGTH:
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.ACCESS_CONTROL,
                severity=AuditSeverity.WARNING,
                title="密码策略不符合要求",
                description=f"最小密码长度为{min_length}，要求至少{MIN_PASSWORD_LENGTH}位",
                standard=ComplianceStandard.NIST800171,
                clause="3.5.7",
                remediation=f"将最小密码长度设置为{MIN_PASSWORD_LENGTH}位",
                evidence={"current_min_length": min_length, "required_min_length": MIN_PASSWORD_LENGTH},
            ))

        session_duration = config.get("max_session_duration_hours", 24)
        if session_duration > MAX_SESSION_DURATION_HOURS:
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.ACCESS_CONTROL,
                severity=AuditSeverity.WARNING,
                title="会话超时时间过长",
                description=f"最大会话时长为{session_duration}小时，要求不超过{MAX_SESSION_DURATION_HOURS}小时",
                standard=ComplianceStandard.NIST800171,
                clause="3.5.11",
                remediation=f"将最大会话时长设置为{MAX_SESSION_DURATION_HOURS}小时",
            ))

        score = max(0, 100 - len([f for f in findings if f.severity == AuditSeverity.CRITICAL]) * 30
                     - len([f for f in findings if f.severity == AuditSeverity.WARNING]) * 10)

        return AuditReport(
            report_id=f"AUDIT-AC-{self._report_counter:06d}",
            audit_type="access_control",
            findings=findings,
            compliance_score=score,
            passed=len([f for f in findings if f.severity == AuditSeverity.CRITICAL]) == 0,
        )

    def audit_data_integrity(self, config: dict[str, Any] | None = None) -> AuditReport:
        self._report_counter += 1
        findings: list[AuditFinding] = []
        config = config or {}

        if not config.get("checksum_verification", True):
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.DATA_INTEGRITY,
                severity=AuditSeverity.CRITICAL,
                title="数据校验和验证未启用",
                description="关键数据传输和存储未启用校验和验证",
                standard=ComplianceStandard.AS9100D,
                clause="7.5.3",
                remediation="对所有关键数据启用SHA-256校验和验证",
            ))

        if not config.get("version_control_enabled", True):
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.DATA_INTEGRITY,
                severity=AuditSeverity.CRITICAL,
                title="版本控制未启用",
                description="设计数据未启用版本控制，无法追踪变更历史",
                standard=ComplianceStandard.ARP4754A,
                clause="5.7",
                remediation="为所有设计数据启用版本控制",
            ))

        if not config.get("audit_trail_enabled", True):
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.DATA_INTEGRITY,
                severity=AuditSeverity.CRITICAL,
                title="审计追踪未启用",
                description="系统操作未记录审计日志",
                standard=ComplianceStandard.AS9100D,
                clause="7.5.5",
                remediation="启用完整的审计追踪功能",
            ))

        retention_days = config.get("audit_log_retention_days", 365)
        if retention_days < REQUIRED_AUDIT_LOG_RETENTION_DAYS:
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.DATA_INTEGRITY,
                severity=AuditSeverity.WARNING,
                title="审计日志保留期不足",
                description=f"审计日志保留{retention_days}天，要求至少{REQUIRED_AUDIT_LOG_RETENTION_DAYS}天",
                standard=ComplianceStandard.AS9100D,
                clause="7.5.5",
                remediation=f"将审计日志保留期设置为至少{REQUIRED_AUDIT_LOG_RETENTION_DAYS}天",
            ))

        score = max(0, 100 - len([f for f in findings if f.severity == AuditSeverity.CRITICAL]) * 30
                     - len([f for f in findings if f.severity == AuditSeverity.WARNING]) * 10)

        return AuditReport(
            report_id=f"AUDIT-DI-{self._report_counter:06d}",
            audit_type="data_integrity",
            findings=findings,
            compliance_score=score,
            passed=len([f for f in findings if f.severity == AuditSeverity.CRITICAL]) == 0,
        )

    def audit_change_management(self, change_records: list[dict[str, Any]] | None = None) -> AuditReport:
        self._report_counter += 1
        findings: list[AuditFinding] = []
        change_records = change_records or []

        unapproved_changes = [r for r in change_records if r.get("status") in ("implemented", "released")
                              and not r.get("approved_by")]
        if unapproved_changes:
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.CHANGE_MANAGEMENT,
                severity=AuditSeverity.CRITICAL,
                title="存在未经批准的变更",
                description=f"发现{len(unapproved_changes)}项已实施但未经批准的变更",
                standard=ComplianceStandard.AS9100D,
                clause="8.5.6",
                remediation="确保所有变更在实施前获得适当批准",
                evidence={"unapproved_count": len(unapproved_changes)},
            ))

        for record in change_records:
            affected_items = record.get("affected_items", [])
            is_safety_critical = any(
                any(marker in item.lower() for marker in SAFETY_CRITICAL_PART_MARKERS)
                for item in affected_items if isinstance(item, str)
            )
            if is_safety_critical:
                approvers = record.get("approvers", [])
                has_required = any(a.get("role") in REQUIRED_CHANGE_APPROVAL_ROLES for a in approvers if isinstance(a, dict))
                if not has_required:
                    self._finding_counter += 1
                    findings.append(AuditFinding(
                        finding_id=f"SA-{self._finding_counter:06d}",
                        category=AuditCategory.SAFETY_CRITICAL,
                        severity=AuditSeverity.CRITICAL,
                        title="安全关键件变更审批不完整",
                        description=f"变更{record.get('title', 'unknown')}涉及安全关键件但缺少必要审批角色",
                        standard=ComplianceStandard.DO178C,
                        clause="6.2.1",
                        remediation="安全关键件变更必须由总工程师、质量经理和设计当局共同批准",
                        evidence={"change_title": record.get("title"), "affected_items": affected_items},
                    ))

        score = max(0, 100 - len([f for f in findings if f.severity == AuditSeverity.CRITICAL]) * 30
                     - len([f for f in findings if f.severity == AuditSeverity.WARNING]) * 10)

        return AuditReport(
            report_id=f"AUDIT-CM-{self._report_counter:06d}",
            audit_type="change_management",
            findings=findings,
            compliance_score=score,
            passed=len([f for f in findings if f.severity == AuditSeverity.CRITICAL]) == 0,
        )

    def audit_traceability(self, bom_data: dict[str, Any] | None = None) -> AuditReport:
        self._report_counter += 1
        findings: list[AuditFinding] = []
        bom_data = bom_data or {}

        ebom_items = bom_data.get("ebom_items", [])
        mbom_items = bom_data.get("mbom_items", [])
        sbom_items = bom_data.get("sbom_items", [])

        ebom_ids = {item.get("part_id") for item in ebom_items if isinstance(item, dict)}
        mbom_ids = {item.get("part_id") for item in mbom_items if isinstance(item, dict)}

        unmapped = ebom_ids - mbom_ids
        if unmapped:
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.TRACEABILITY,
                severity=AuditSeverity.WARNING,
                title="eBOM到mBOM存在未映射项",
                description=f"发现{len(unmapped)}个eBOM项在mBOM中无对应映射",
                standard=ComplianceStandard.AS9100D,
                clause="8.5.2",
                remediation="确保所有eBOM项都有对应的mBOM映射",
                evidence={"unmapped_count": len(unmapped)},
            ))

        items_without_serial = [item for item in mbom_items
                                if isinstance(item, dict) and item.get("safety_critical") and not item.get("serial_tracked")]
        if items_without_serial:
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.TRACEABILITY,
                severity=AuditSeverity.CRITICAL,
                title="安全关键件缺少序列号追踪",
                description=f"发现{len(items_without_serial)}个安全关键件未启用序列号追踪",
                standard=ComplianceStandard.AS9100D,
                clause="8.5.2",
                remediation="所有安全关键件必须启用序列号追踪",
                evidence={"items_without_serial": len(items_without_serial)},
            ))

        score = max(0, 100 - len([f for f in findings if f.severity == AuditSeverity.CRITICAL]) * 30
                     - len([f for f in findings if f.severity == AuditSeverity.WARNING]) * 10)

        return AuditReport(
            report_id=f"AUDIT-TR-{self._report_counter:06d}",
            audit_type="traceability",
            findings=findings,
            compliance_score=score,
            passed=len([f for f in findings if f.severity == AuditSeverity.CRITICAL]) == 0,
        )

    def audit_api_security(self, config: dict[str, Any] | None = None) -> AuditReport:
        self._report_counter += 1
        findings: list[AuditFinding] = []
        config = config or {}

        if not config.get("rate_limiting_enabled", True):
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.API_SECURITY,
                severity=AuditSeverity.WARNING,
                title="API速率限制未启用",
                description="API端点未配置速率限制，存在DDoS风险",
                standard=ComplianceStandard.ISO27001,
                clause="A.12.4.1",
                remediation="为所有API端点配置速率限制",
            ))

        if not config.get("input_validation_enabled", True):
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.API_SECURITY,
                severity=AuditSeverity.CRITICAL,
                title="API输入验证未启用",
                description="API端点未启用输入验证，存在注入攻击风险",
                standard=ComplianceStandard.ISO27001,
                clause="A.14.1.2",
                remediation="为所有API端点启用严格的输入验证",
            ))

        if not config.get("tls_enabled", True):
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.API_SECURITY,
                severity=AuditSeverity.CRITICAL,
                title="TLS加密未启用",
                description="API通信未启用TLS加密，数据可能被窃听",
                standard=ComplianceStandard.NIST800171,
                clause="3.13.8",
                remediation="为所有API通信启用TLS 1.3加密",
            ))

        if not config.get("cors_configured", True):
            self._finding_counter += 1
            findings.append(AuditFinding(
                finding_id=f"SA-{self._finding_counter:06d}",
                category=AuditCategory.API_SECURITY,
                severity=AuditSeverity.WARNING,
                title="CORS策略未配置",
                description="跨域资源共享(CORS)策略未正确配置",
                standard=ComplianceStandard.ISO27001,
                clause="A.14.1.2",
                remediation="配置严格的CORS策略，仅允许受信任的域名",
            ))

        score = max(0, 100 - len([f for f in findings if f.severity == AuditSeverity.CRITICAL]) * 30
                     - len([f for f in findings if f.severity == AuditSeverity.WARNING]) * 10)

        return AuditReport(
            report_id=f"AUDIT-API-{self._report_counter:06d}",
            audit_type="api_security",
            findings=findings,
            compliance_score=score,
            passed=len([f for f in findings if f.severity == AuditSeverity.CRITICAL]) == 0,
        )

    def run_full_audit(
        self,
        access_config: dict[str, Any] | None = None,
        integrity_config: dict[str, Any] | None = None,
        change_records: list[dict[str, Any]] | None = None,
        bom_data: dict[str, Any] | None = None,
        api_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        reports = [
            self.audit_access_control(access_config),
            self.audit_data_integrity(integrity_config),
            self.audit_change_management(change_records),
            self.audit_traceability(bom_data),
            self.audit_api_security(api_config),
        ]

        total_findings = sum(len(r.findings) for r in reports)
        critical_count = sum(len([f for f in r.findings if f.severity == AuditSeverity.CRITICAL]) for r in reports)
        warning_count = sum(len([f for f in r.findings if f.severity == AuditSeverity.WARNING]) for r in reports)

        overall_score = sum(r.compliance_score for r in reports) / max(len(reports), 1)
        overall_passed = all(r.passed for r in reports)

        return {
            "overall_score": round(overall_score, 2),
            "overall_passed": overall_passed,
            "total_findings": total_findings,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "info_count": total_findings - critical_count - warning_count,
            "reports": [r.to_dict() for r in reports],
            "standards_checked": [s.value for s in ComplianceStandard],
        }