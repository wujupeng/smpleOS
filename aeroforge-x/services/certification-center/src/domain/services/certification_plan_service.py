from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ..entities.certification_plan import (
    ApplicantInfo,
    CertificationAuthority,
    CertificationMilestone,
    CertificationPlan,
    CertificationStandard,
    ComplianceItem,
    ComplianceMethod,
    EvidenceRef,
    ItemStatus,
    PlanStatus,
)

_FAR_23_CLAUSES = [
    ("§23.201", "Wings lift"),
    ("§23.207", "Stall warning"),
    ("§23.221", "Spin recovery"),
    ("§23.301", "Loads"),
    ("§23.305", "Strength and deformation"),
    ("§23.307", "Proof of structure"),
    ("§23.321", "Flight load factors"),
    ("§23.337", "Limit maneuvering load factors"),
    ("§23.341", "Gust load factors"),
    ("§23.601", "General structure"),
    ("§23.603", "Materials"),
    ("§23.605", "Fabrication methods"),
    ("§23.609", "Protection of structure"),
    ("§23.613", "Material strength properties"),
    ("§23.901", "Powerplant installation"),
    ("§23.903", "Engines"),
    ("§23.1125", "Exhaust system"),
    ("§23.1301", "Function and installation"),
    ("§23.1309", "Equipment, systems, and installations"),
    ("§23.1321", "Arrangement and visibility"),
    ("§23.1351", "Electrical systems"),
    ("§23.1521", "Operating limitations"),
    ("§23.1581", "Airplane flight manual"),
]

_FAR_25_CLAUSES = [
    ("§25.201", "Stall demonstration"),
    ("§25.207", "Stall warning"),
    ("§25.301", "Loads"),
    ("§25.303", "Factor of safety"),
    ("§25.305", "Strength and deformation"),
    ("§25.307", "Proof of structure"),
    ("§25.321", "Flight load factors"),
    ("§25.337", "Limit maneuvering load factors"),
    ("§25.341", "Gust and turbulence loads"),
    ("§25.471", "Landing load conditions"),
    ("§25.601", "General structure"),
    ("§25.603", "Materials"),
    ("§25.605", "Fabrication methods"),
    ("§25.609", "Protection of structure"),
    ("§25.613", "Material strength properties"),
    ("§25.783", "Fuselage doors"),
    ("§25.801", "Ditching"),
    ("§25.901", "Powerplant installation"),
    ("§25.903", "Engines"),
    ("§25.1125", "Exhaust system"),
    ("§25.1301", "Function and installation"),
    ("§25.1309", "Equipment, systems, and installations"),
    ("§25.1351", "Electrical systems"),
    ("§25.1521", "Operating limitations"),
    ("§25.1581", "Airplane flight manual"),
]

_DEFAULT_MOC_MAP: dict[str, ComplianceMethod] = {
    "lift": ComplianceMethod.MOC2,
    "stall": ComplianceMethod.MOC6,
    "spin": ComplianceMethod.MOC6,
    "loads": ComplianceMethod.MOC2,
    "strength": ComplianceMethod.MOC2,
    "deformation": ComplianceMethod.MOC2,
    "gust": ComplianceMethod.MOC2,
    "material": ComplianceMethod.MOC7,
    "fabrication": ComplianceMethod.MOC7,
    "protection": ComplianceMethod.MOC7,
    "powerplant": ComplianceMethod.MOC4,
    "engine": ComplianceMethod.MOC4,
    "exhaust": ComplianceMethod.MOC4,
    "electrical": ComplianceMethod.MOC9,
    "equipment": ComplianceMethod.MOC9,
    "flight": ComplianceMethod.MOC6,
    "operating": ComplianceMethod.MOC1,
    "landing": ComplianceMethod.MOC2,
    "door": ComplianceMethod.MOC7,
    "ditching": ComplianceMethod.MOC6,
}


def _guess_moc(clause_title: str) -> ComplianceMethod:
    title_lower = clause_title.lower()
    for keyword, moc in _DEFAULT_MOC_MAP.items():
        if keyword in title_lower:
            return moc
    return ComplianceMethod.MOC0


class CertificationPlanService:
    def __init__(self) -> None:
        self._plans: dict[str, CertificationPlan] = {}

    def create_certification_plan(
        self,
        tenant_id: str,
        project_id: str,
        aircraft_type: str,
        certification_standard: CertificationStandard,
        certification_authority: CertificationAuthority,
    ) -> CertificationPlan:
        plan = CertificationPlan(
            tenant_id=tenant_id,
            project_id=project_id,
            aircraft_type=aircraft_type,
            certification_standard=certification_standard,
            certification_authority=certification_authority,
        )

        clauses = self._get_clauses_for_standard(certification_standard)
        for clause_num, clause_title in clauses:
            item = ComplianceItem(
                item_id=str(uuid.uuid4()),
                plan_id=plan.id,
                regulation_clause=clause_num,
                clause_title=clause_title,
                compliance_method=_guess_moc(clause_title),
                status=ItemStatus.NOT_STARTED,
            )
            plan.add_compliance_item(item)

        milestones = self._generate_default_milestones(certification_authority)
        for ms in milestones:
            plan.add_milestone(ms)

        self._plans[plan.id] = plan
        return plan

    def assign_compliance_method(
        self,
        plan_id: str,
        item_id: str,
        compliance_method: ComplianceMethod,
    ) -> CertificationPlan | None:
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        plan.update_compliance_item(item_id, compliance_method=compliance_method)
        return plan

    def update_item_status(
        self,
        plan_id: str,
        item_id: str,
        status: ItemStatus,
    ) -> CertificationPlan | None:
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        plan.update_compliance_item(item_id, status=status)
        return plan

    def link_evidence(
        self,
        plan_id: str,
        item_id: str,
        evidence_id: str,
        evidence_type: str,
        title: str,
        reference: str = "",
    ) -> CertificationPlan | None:
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        evidence = EvidenceRef(
            evidence_id=evidence_id,
            evidence_type=evidence_type,
            title=title,
            reference=reference,
        )
        plan.add_evidence_to_item(item_id, evidence)
        return plan

    def track_compliance_progress(self, plan_id: str) -> dict[str, Any] | None:
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        return plan.get_compliance_progress()

    def submit_plan(self, plan_id: str) -> CertificationPlan | None:
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        plan.submit()
        return plan

    def approve_plan(self, plan_id: str) -> CertificationPlan | None:
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        plan.approve()
        return plan

    def generate_certification_plan_document(self, plan_id: str) -> dict[str, Any] | None:
        plan = self._plans.get(plan_id)
        if not plan:
            return None

        progress = plan.get_compliance_progress()
        return {
            "document_type": "Certification_Plan",
            "plan_id": plan.id,
            "aircraft_type": plan.aircraft_type,
            "certification_standard": plan.certification_standard.value,
            "certification_authority": plan.certification_authority.value,
            "applicant": plan.applicant_info.to_dict(),
            "compliance_items": [i.to_dict() for i in plan.compliance_items],
            "milestones": [m.to_dict() for m in plan.milestones],
            "compliance_progress": progress,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "format": "PDF",
        }

    def get_plan(self, plan_id: str) -> CertificationPlan | None:
        return self._plans.get(plan_id)

    def _get_clauses_for_standard(
        self, standard: CertificationStandard
    ) -> list[tuple[str, str]]:
        if standard in (CertificationStandard.FAR_23, CertificationStandard.CCAR_23, CertificationStandard.CS_23):
            return _FAR_23_CLAUSES
        return _FAR_25_CLAUSES

    def _generate_default_milestones(
        self, authority: CertificationAuthority
    ) -> list[CertificationMilestone]:
        base_date = datetime.now(timezone.utc)
        return [
            CertificationMilestone(
                milestone_id=str(uuid.uuid4()),
                name="Certification Plan Submission",
                planned_date=(base_date.replace(month=base_date.month % 12 + 1)).strftime("%Y-%m-%d"),
            ),
            CertificationMilestone(
                milestone_id=str(uuid.uuid4()),
                name="Familiarization Meeting",
                planned_date=(base_date.replace(month=(base_date.month % 12) + 3)).strftime("%Y-%m-%d"),
            ),
            CertificationMilestone(
                milestone_id=str(uuid.uuid4()),
                name="Compliance Demonstration",
                planned_date=(base_date.replace(month=(base_date.month % 12) + 6)).strftime("%Y-%m-%d"),
            ),
            CertificationMilestone(
                milestone_id=str(uuid.uuid4()),
                name="Type Inspection",
                planned_date=(base_date.replace(month=(base_date.month % 12) + 9)).strftime("%Y-%m-%d"),
            ),
            CertificationMilestone(
                milestone_id=str(uuid.uuid4()),
                name="Type Certificate Issuance",
                planned_date=(base_date.replace(month=(base_date.month % 12) + 12)).strftime("%Y-%m-%d"),
            ),
        ]