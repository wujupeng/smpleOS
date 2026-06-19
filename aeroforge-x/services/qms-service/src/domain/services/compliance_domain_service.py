from __future__ import annotations

import logging
import secrets
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from ..entities.compliance import (
    CheckCategory,
    CheckSeverity,
    ComplianceCheck,
    ComplianceCheckResult,
    ComplianceReport,
    ComplianceRequirement,
    ComplianceStandard,
    ComplianceStatus,
)

logger = logging.getLogger(__name__)


class ComplianceDomainService:
    def __init__(self) -> None:
        self._checks: dict[str, ComplianceCheck] = {}
        self._reports: dict[str, ComplianceReport] = {}
        self._requirements_registry: dict[str, list[ComplianceRequirement]] = {}
        self._init_standard_requirements()

    def _init_standard_requirements(self) -> None:
        far23_reqs = [
            ComplianceRequirement("FAR23-001", ComplianceStandard.FAR_23, "23.21", "Proof of compliance", CheckCategory.DESIGN, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR23-002", ComplianceStandard.FAR_23, "23.23", "Load distribution limits", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR23-003", ComplianceStandard.FAR_23, "23.25", "Weight limits", CheckCategory.DESIGN, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR23-004", ComplianceStandard.FAR_23, "23.301", "Loads", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR23-005", ComplianceStandard.FAR_23, "23.305", "Strength and deformation", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR23-006", ComplianceStandard.FAR_23, "23.337", "Limit maneuvering load factors", CheckCategory.STRUCTURAL, CheckSeverity.MAJOR),
            ComplianceRequirement("FAR23-007", ComplianceStandard.FAR_23, "23.601", "General: structure", CheckCategory.STRUCTURAL, CheckSeverity.MAJOR),
            ComplianceRequirement("FAR23-008", ComplianceStandard.FAR_23, "23.603", "Materials and workmanship", CheckCategory.MATERIAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR23-009", ComplianceStandard.FAR_23, "23.609", "Protection of structure", CheckCategory.DESIGN, CheckSeverity.MAJOR),
            ComplianceRequirement("FAR23-010", ComplianceStandard.FAR_23, "23.613", "Material strength properties", CheckCategory.MATERIAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR23-011", ComplianceStandard.FAR_23, "23.771", "Pilot compartment", CheckCategory.DESIGN, CheckSeverity.MAJOR),
            ComplianceRequirement("FAR23-012", ComplianceStandard.FAR_23, "23.1309", "Equipment, systems, and installations", CheckCategory.SYSTEMS, CheckSeverity.CRITICAL),
        ]
        self._requirements_registry[ComplianceStandard.FAR_23.value] = far23_reqs

        far25_reqs = [
            ComplianceRequirement("FAR25-001", ComplianceStandard.FAR_25, "25.21", "Proof of compliance", CheckCategory.DESIGN, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR25-002", ComplianceStandard.FAR_25, "25.23", "Load distribution limits", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR25-003", ComplianceStandard.FAR_25, "25.25", "Weight limits", CheckCategory.DESIGN, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR25-004", ComplianceStandard.FAR_25, "25.301", "Loads", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR25-005", ComplianceStandard.FAR_25, "25.305", "Strength and deformation", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR25-006", ComplianceStandard.FAR_25, "25.307", "Proof of structure", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR25-007", ComplianceStandard.FAR_25, "25.321", "Flight loads", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR25-008", ComplianceStandard.FAR_25, "25.337", "Limit maneuvering load factors", CheckCategory.STRUCTURAL, CheckSeverity.MAJOR),
            ComplianceRequirement("FAR25-009", ComplianceStandard.FAR_25, "25.571", "Damage tolerance and fatigue", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR25-010", ComplianceStandard.FAR_25, "25.601", "General: structure", CheckCategory.STRUCTURAL, CheckSeverity.MAJOR),
            ComplianceRequirement("FAR25-011", ComplianceStandard.FAR_25, "25.603", "Materials and workmanship", CheckCategory.MATERIAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR25-012", ComplianceStandard.FAR_25, "25.609", "Protection of structure", CheckCategory.DESIGN, CheckSeverity.MAJOR),
            ComplianceRequirement("FAR25-013", ComplianceStandard.FAR_25, "25.613", "Material strength properties", CheckCategory.MATERIAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR25-014", ComplianceStandard.FAR_25, "25.771", "Pilot compartment", CheckCategory.DESIGN, CheckSeverity.MAJOR),
            ComplianceRequirement("FAR25-015", ComplianceStandard.FAR_25, "25.1309", "Equipment, systems, and installations", CheckCategory.SYSTEMS, CheckSeverity.CRITICAL),
            ComplianceRequirement("FAR25-016", ComplianceStandard.FAR_25, "25.1529", "Instructions for continued airworthiness", CheckCategory.AIRWORTHINESS, CheckSeverity.CRITICAL),
        ]
        self._requirements_registry[ComplianceStandard.FAR_25.value] = far25_reqs

        ccr23_reqs = [
            ComplianceRequirement("CCAR23-001", ComplianceStandard.CCAR_23, "23.21", "符合性证明", CheckCategory.DESIGN, CheckSeverity.CRITICAL),
            ComplianceRequirement("CCAR23-002", ComplianceStandard.CCAR_23, "23.23", "载荷分布限制", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("CCAR23-003", ComplianceStandard.CCAR_23, "23.25", "重量限制", CheckCategory.DESIGN, CheckSeverity.CRITICAL),
            ComplianceRequirement("CCAR23-004", ComplianceStandard.CCAR_23, "23.301", "载荷", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("CCAR23-005", ComplianceStandard.CCAR_23, "23.305", "强度与变形", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
        ]
        self._requirements_registry[ComplianceStandard.CCAR_23.value] = ccr23_reqs

        ccr25_reqs = [
            ComplianceRequirement("CCAR25-001", ComplianceStandard.CCAR_25, "25.21", "符合性证明", CheckCategory.DESIGN, CheckSeverity.CRITICAL),
            ComplianceRequirement("CCAR25-002", ComplianceStandard.CCAR_25, "25.23", "载荷分布限制", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("CCAR25-003", ComplianceStandard.CCAR_25, "25.25", "重量限制", CheckCategory.DESIGN, CheckSeverity.CRITICAL),
            ComplianceRequirement("CCAR25-004", ComplianceStandard.CCAR_25, "25.301", "载荷", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
            ComplianceRequirement("CCAR25-005", ComplianceStandard.CCAR_25, "25.305", "强度与变形", CheckCategory.STRUCTURAL, CheckSeverity.CRITICAL),
        ]
        self._requirements_registry[ComplianceStandard.CCAR_25.value] = ccr25_reqs

    def check_design_compliance(
        self,
        tenant_id: str,
        project_id: str,
        aircraft_model: str,
        standards: list[ComplianceStandard],
        design_parameters: dict[str, Any],
    ) -> ComplianceCheck:
        check = ComplianceCheck(
            tenant_id=tenant_id,
            project_id=project_id,
            aircraft_model=aircraft_model,
            standards=standards,
            check_type=CheckCategory.DESIGN,
        )

        for standard in standards:
            requirements = self._requirements_registry.get(standard.value, [])
            for req in requirements:
                if req.category not in (CheckCategory.DESIGN, CheckCategory.STRUCTURAL, CheckCategory.SYSTEMS, CheckCategory.MATERIAL):
                    continue
                result = self._evaluate_design_requirement(req, design_parameters)
                check.add_result(result)

        check.complete()
        self._checks[check.id] = check

        logger.info(
            "Design compliance check: project=%s model=%s status=%s checks=%d",
            project_id, aircraft_model, check.overall_status.value, len(check.results),
        )
        return check

    def check_manufacturing_compliance(
        self,
        tenant_id: str,
        project_id: str,
        aircraft_model: str,
        standards: list[ComplianceStandard],
        manufacturing_data: dict[str, Any],
    ) -> ComplianceCheck:
        check = ComplianceCheck(
            tenant_id=tenant_id,
            project_id=project_id,
            aircraft_model=aircraft_model,
            standards=standards,
            check_type=CheckCategory.MANUFACTURING,
        )

        for standard in standards:
            requirements = self._requirements_registry.get(standard.value, [])
            for req in requirements:
                if req.category not in (CheckCategory.MANUFACTURING, CheckCategory.QUALITY, CheckCategory.MATERIAL, CheckCategory.TRACEABILITY):
                    continue
                result = self._evaluate_manufacturing_requirement(req, manufacturing_data)
                check.add_result(result)

        traceability_result = self._check_traceability(manufacturing_data)
        check.add_result(traceability_result)

        check.complete()
        self._checks[check.id] = check

        logger.info(
            "Manufacturing compliance check: project=%s model=%s status=%s",
            project_id, aircraft_model, check.overall_status.value,
        )
        return check

    def generate_compliance_report(
        self,
        tenant_id: str,
        project_id: str,
        aircraft_model: str,
        standards: list[ComplianceStandard],
        design_check_id: str | None = None,
        manufacturing_check_id: str | None = None,
        generated_by: str = "",
    ) -> ComplianceReport:
        design_check = self._checks.get(design_check_id) if design_check_id else None
        mfg_check = self._checks.get(manufacturing_check_id) if manufacturing_check_id else None

        design_compliance = design_check.get_summary() if design_check else {"overall_status": "not_assessed", "total_requirements": 0}
        manufacturing_compliance = mfg_check.get_summary() if mfg_check else {"overall_status": "not_assessed", "total_requirements": 0}

        quality_compliance = self._assess_quality_compliance(design_check, mfg_check)
        traceability_compliance = self._assess_traceability_compliance(design_check, mfg_check)

        non_compliant_items = []
        for check in [design_check, mfg_check]:
            if check:
                for r in check.results:
                    if r.status == ComplianceStatus.NON_COMPLIANT:
                        non_compliant_items.append({
                            "requirement_id": r.requirement_id,
                            "findings": r.findings,
                            "recommendations": r.recommendations,
                        })

        recommendations = self._generate_recommendations(non_compliant_items)

        overall_statuses = []
        if design_check:
            overall_statuses.append(design_check.overall_status)
        if mfg_check:
            overall_statuses.append(mfg_check.overall_status)

        if any(s == ComplianceStatus.NON_COMPLIANT for s in overall_statuses):
            overall_status = ComplianceStatus.NON_COMPLIANT
        elif any(s == ComplianceStatus.PARTIALLY_COMPLIANT for s in overall_statuses):
            overall_status = ComplianceStatus.PARTIALLY_COMPLIANT
        elif overall_statuses:
            overall_status = ComplianceStatus.COMPLIANT
        else:
            overall_status = ComplianceStatus.NOT_ASSESSED

        report = ComplianceReport(
            report_id=f"RPT-{secrets.token_hex(4)}",
            tenant_id=tenant_id,
            project_id=project_id,
            aircraft_model=aircraft_model,
            standards=standards,
            overall_status=overall_status,
            design_compliance=design_compliance,
            manufacturing_compliance=manufacturing_compliance,
            quality_compliance=quality_compliance,
            traceability_compliance=traceability_compliance,
            non_compliant_items=non_compliant_items,
            recommendations=recommendations,
            generated_by=generated_by,
        )

        self._reports[report.report_id] = report

        logger.info(
            "Compliance report generated: project=%s status=%s non_compliant=%d",
            project_id, overall_status.value, len(non_compliant_items),
        )
        return report

    def get_check(self, check_id: str) -> ComplianceCheck | None:
        return self._checks.get(check_id)

    def get_report(self, report_id: str) -> ComplianceReport | None:
        return self._reports.get(report_id)

    def list_checks(self, tenant_id: str, project_id: str | None = None) -> list[ComplianceCheck]:
        checks = [c for c in self._checks.values() if c.tenant_id == tenant_id]
        if project_id:
            checks = [c for c in checks if c.project_id == project_id]
        return checks

    def list_reports(self, tenant_id: str, project_id: str | None = None) -> list[ComplianceReport]:
        reports = [r for r in self._reports.values() if r.tenant_id == tenant_id]
        if project_id:
            reports = [r for r in reports if r.project_id == project_id]
        return reports

    def get_requirements(self, standard: ComplianceStandard) -> list[ComplianceRequirement]:
        return self._requirements_registry.get(standard.value, [])

    def _evaluate_design_requirement(
        self,
        requirement: ComplianceRequirement,
        design_parameters: dict[str, Any],
    ) -> ComplianceCheckResult:
        findings: list[str] = []
        recommendations: list[str] = []
        status = ComplianceStatus.COMPLIANT
        evidence = ""

        if requirement.category == CheckCategory.STRUCTURAL:
            safety_factor = design_parameters.get("safety_factor", 0)
            if safety_factor < 1.5:
                status = ComplianceStatus.NON_COMPLIANT
                findings.append(f"Safety factor {safety_factor} below minimum 1.5")
                recommendations.append("Increase structural safety factor to at least 1.5")
            else:
                evidence = f"Safety factor {safety_factor} meets requirement >= 1.5"

            max_stress = design_parameters.get("max_stress_mpa", 0)
            yield_stress = design_parameters.get("yield_stress_mpa", 0)
            if yield_stress > 0 and max_stress > yield_stress:
                status = ComplianceStatus.NON_COMPLIANT
                findings.append(f"Max stress {max_stress} MPa exceeds yield stress {yield_stress} MPa")
                recommendations.append("Redesign to reduce stress or use higher-strength material")

        elif requirement.category == CheckCategory.DESIGN:
            max_takeoff_weight = design_parameters.get("max_takeoff_weight_kg", 0)
            design_weight_limit = design_parameters.get("weight_limit_kg", 0)
            if design_weight_limit > 0 and max_takeoff_weight > design_weight_limit:
                status = ComplianceStatus.NON_COMPLIANT
                findings.append(f"MTOW {max_takeoff_weight} kg exceeds design limit {design_weight_limit} kg")
                recommendations.append("Reduce aircraft weight or increase design limit")

            wing_loading = design_parameters.get("wing_loading_kg_m2", 0)
            if wing_loading > 0:
                evidence = f"Wing loading: {wing_loading} kg/m²"

        elif requirement.category == CheckCategory.MATERIAL:
            material_certified = design_parameters.get("materials_certified", True)
            if not material_certified:
                status = ComplianceStatus.NON_COMPLIANT
                findings.append("One or more materials lack certification")
                recommendations.append("Use only certified aviation materials")

        elif requirement.category == CheckCategory.SYSTEMS:
            redundancy_level = design_parameters.get("system_redundancy", "single")
            if redundancy_level == "single" and requirement.severity == CheckSeverity.CRITICAL:
                status = ComplianceStatus.NON_COMPLIANT
                findings.append("Critical system lacks redundancy")
                recommendations.append("Implement redundant system architecture")

        return ComplianceCheckResult(
            requirement_id=requirement.requirement_id,
            status=status,
            evidence=evidence,
            findings=findings,
            recommendations=recommendations,
        )

    def _evaluate_manufacturing_requirement(
        self,
        requirement: ComplianceRequirement,
        manufacturing_data: dict[str, Any],
    ) -> ComplianceCheckResult:
        findings: list[str] = []
        recommendations: list[str] = []
        status = ComplianceStatus.COMPLIANT
        evidence = ""

        if requirement.category == CheckCategory.MANUFACTURING:
            process_qualified = manufacturing_data.get("processes_qualified", True)
            if not process_qualified:
                status = ComplianceStatus.NON_COMPLIANT
                findings.append("Manufacturing process not qualified")
                recommendations.append("Complete process qualification before production")

            ndt_coverage = manufacturing_data.get("ndt_coverage_percent", 100)
            if ndt_coverage < 100:
                status = ComplianceStatus.PARTIALLY_COMPLIANT
                findings.append(f"NDT coverage {ndt_coverage}% below 100%")
                recommendations.append("Increase NDT coverage to 100% for critical components")

        elif requirement.category == CheckCategory.QUALITY:
            inspection_complete = manufacturing_data.get("all_inspections_complete", True)
            if not inspection_complete:
                status = ComplianceStatus.NON_COMPLIANT
                findings.append("Not all required inspections completed")
                recommendations.append("Complete all required quality inspections")

            first_article_inspected = manufacturing_data.get("first_article_inspected", True)
            if not first_article_inspected:
                status = ComplianceStatus.NON_COMPLIANT
                findings.append("First article inspection not completed")
                recommendations.append("Complete first article inspection before production")

        elif requirement.category == CheckCategory.MATERIAL:
            material_traceability = manufacturing_data.get("material_traceability", True)
            if not material_traceability:
                status = ComplianceStatus.NON_COMPLIANT
                findings.append("Material traceability incomplete")
                recommendations.append("Ensure full material traceability from source to finished part")

        return ComplianceCheckResult(
            requirement_id=requirement.requirement_id,
            status=status,
            evidence=evidence,
            findings=findings,
            recommendations=recommendations,
        )

    def _check_traceability(self, manufacturing_data: dict[str, Any]) -> ComplianceCheckResult:
        trace_chain_complete = manufacturing_data.get("trace_chain_complete", True)
        batch_records_complete = manufacturing_data.get("batch_records_complete", True)

        findings: list[str] = []
        recommendations: list[str] = []
        status = ComplianceStatus.COMPLIANT

        if not trace_chain_complete:
            status = ComplianceStatus.NON_COMPLIANT
            findings.append("Traceability chain has gaps")
            recommendations.append("Complete traceability chain from raw material to finished product")

        if not batch_records_complete:
            status = ComplianceStatus.NON_COMPLIANT if status != ComplianceStatus.NON_COMPLIANT else status
            findings.append("Batch records incomplete")
            recommendations.append("Complete all batch records")

        return ComplianceCheckResult(
            requirement_id="TRACE-001",
            status=status,
            evidence="Traceability assessment",
            findings=findings,
            recommendations=recommendations,
        )

    def _assess_quality_compliance(
        self,
        design_check: ComplianceCheck | None,
        mfg_check: ComplianceCheck | None,
    ) -> dict[str, Any]:
        total = 0
        compliant = 0
        for check in [design_check, mfg_check]:
            if check:
                for r in check.results:
                    if r.status in (ComplianceStatus.COMPLIANT, ComplianceStatus.NON_COMPLIANT):
                        total += 1
                        if r.status == ComplianceStatus.COMPLIANT:
                            compliant += 1

        return {
            "total_quality_checks": total,
            "compliant": compliant,
            "compliance_rate": round(compliant / total * 100, 1) if total > 0 else 0,
        }

    def _assess_traceability_compliance(
        self,
        design_check: ComplianceCheck | None,
        mfg_check: ComplianceCheck | None,
    ) -> dict[str, Any]:
        trace_results = []
        for check in [design_check, mfg_check]:
            if check:
                for r in check.results:
                    if r.requirement_id.startswith("TRACE"):
                        trace_results.append(r)

        return {
            "traceability_checks": len(trace_results),
            "all_passing": all(r.status == ComplianceStatus.COMPLIANT for r in trace_results) if trace_results else True,
        }

    def _generate_recommendations(self, non_compliant_items: list[dict[str, Any]]) -> list[str]:
        recommendations = []
        for item in non_compliant_items:
            for rec in item.get("recommendations", []):
                if rec not in recommendations:
                    recommendations.append(rec)

        if non_compliant_items:
            recommendations.insert(0, "Address all non-compliant items before proceeding to certification")

        return recommendations