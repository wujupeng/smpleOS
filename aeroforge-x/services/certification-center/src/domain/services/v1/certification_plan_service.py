from __future__ import annotations

import logging
from typing import Any

from src.domain.entities.v1.certification_plan import CertificationPlan, PlanStatus
from src.domain.entities.v1.compliance_item import ComplianceItem, ComplianceMethod, ComplianceStatus

logger = logging.getLogger(__name__)

FAR25_COMPLIANCE_ITEMS = [
    {"clause": "25.301", "title": "Loads - General", "method": ComplianceMethod.MOC1},
    {"clause": "25.303", "title": "Factor of Safety", "method": ComplianceMethod.MOC1},
    {"clause": "25.305", "title": "Strength and Deformation", "method": ComplianceMethod.MOC1},
    {"clause": "25.307", "title": "Proof of Structure", "method": ComplianceMethod.MOC3},
    {"clause": "25.321", "title": "Flight Loads - General", "method": ComplianceMethod.MOC1},
    {"clause": "25.337", "title": "Limit Maneuvering Loads", "method": ComplianceMethod.MOC1},
    {"clause": "25.341", "title": "Gust and Turbulence Loads", "method": ComplianceMethod.MOC1},
    {"clause": "25.471", "title": "Landing Loads - General", "method": ComplianceMethod.MOC1},
    {"clause": "25.491", "title": "Taxi, Takeoff and Landing Roll", "method": ComplianceMethod.MOC3},
    {"clause": "25.561", "title": "Emergency Landing Conditions", "method": ComplianceMethod.MOC3},
    {"clause": "25.571", "title": "Damage Tolerance and Fatigue", "method": ComplianceMethod.MOC1},
    {"clause": "25.603", "title": "Materials", "method": ComplianceMethod.MOC2},
    {"clause": "25.605", "title": "Fabrication Methods", "method": ComplianceMethod.MOC2},
    {"clause": "25.613", "title": "Material Strength Properties", "method": ComplianceMethod.MOC2},
    {"clause": "25.783", "title": "Doors", "method": ComplianceMethod.MOC3},
    {"clause": "25.807", "title": "Emergency Exits", "method": ComplianceMethod.MOC3},
    {"clause": "25.901", "title": "Installation - Powerplant", "method": ComplianceMethod.MOC1},
    {"clause": "25.903", "title": "Engines", "method": ComplianceMethod.MOC3},
    {"clause": "25.1309", "title": "Equipment, Systems and Installations", "method": ComplianceMethod.MOC1},
    {"clause": "25.1351", "title": "Electrical Systems - General", "method": ComplianceMethod.MOC1},
    {"clause": "25.1419", "title": "Ice Protection", "method": ComplianceMethod.MOC3},
    {"clause": "25.1435", "title": "Hydraulic Systems", "method": ComplianceMethod.MOC1},
    {"clause": "25.1521", "title": "Operating Limitations", "method": ComplianceMethod.MOC4},
    {"clause": "25.1529", "title": "Instructions for Continued Airworthiness", "method": ComplianceMethod.MOC4},
    {"clause": "25.1581", "title": "Airplane Flight Manual - General", "method": ComplianceMethod.MOC4},
]


class CertificationPlanService:
    def __init__(self, event_publisher: Any | None = None):
        self._event_publisher = event_publisher
        self._plans: dict[str, CertificationPlan] = {}
        self._items: dict[str, ComplianceItem] = {}

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    async def create_certification_plan(self, project_id: str, aircraft_type: str, standard: str = "FAR-25", authority: str = "FAA", created_by: str = "") -> CertificationPlan:
        plan = CertificationPlan(project_id=project_id, aircraft_type=aircraft_type)
        plan.certification_standard = standard
        plan.certification_authority = authority
        plan.created_by = created_by

        items = FAR25_COMPLIANCE_ITEMS
        if standard == "CS-25":
            pass

        for item_def in items:
            item = ComplianceItem(
                plan_id=plan.plan_id,
                regulation_clause=item_def["clause"],
                clause_title=item_def["title"],
            )
            item.assign_compliance_method(item_def["method"])
            self._items[item.item_id] = item
            plan.add_compliance_item(item.to_dict())

        plan.milestones = [
            {"name": "G-1 Letter", "target_date": None, "status": "pending"},
            {"name": "Design Review", "target_date": None, "status": "pending"},
            {"name": "Ground Test Complete", "target_date": None, "status": "pending"},
            {"name": "First Flight", "target_date": None, "status": "pending"},
            {"name": "Type Certificate", "target_date": None, "status": "pending"},
        ]

        self._plans[plan.plan_id] = plan
        await self._publish_event("cert.plan.created", {"plan_id": plan.plan_id, "project_id": project_id})
        logger.info(f"Certification plan created: {plan.plan_id}")
        return plan

    def assign_compliance_method(self, item_id: str, method: ComplianceMethod) -> ComplianceItem:
        item = self._items.get(item_id)
        if not item:
            raise ValueError(f"Compliance item {item_id} not found")
        item.assign_compliance_method(method)
        plan = self._plans.get(item.plan_id)
        if plan:
            for ci in plan.compliance_items:
                if ci.get("item_id") == item_id:
                    ci["compliance_method"] = method.value
        return item

    def track_compliance_progress(self, plan_id: str) -> dict[str, Any]:
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        progress = plan.get_progress()
        items_by_status = {}
        for ci in plan.compliance_items:
            status = ci.get("status", "open")
            items_by_status[status] = items_by_status.get(status, 0) + 1
        gaps = [ci for ci in plan.compliance_items if ci.get("evidence_gap")]
        return {
            "plan_id": plan_id,
            "progress": progress,
            "items_by_status": items_by_status,
            "evidence_gaps": len(gaps),
            "gap_items": [{"item_id": g["item_id"], "clause": g["regulation_clause"]} for g in gaps],
        }

    def generate_certification_plan_document(self, plan_id: str) -> dict[str, Any]:
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        return {
            "document_type": "certification_plan",
            "plan_id": plan_id,
            "project_id": plan.project_id,
            "aircraft_type": plan.aircraft_type,
            "standard": plan.certification_standard,
            "authority": plan.certification_authority,
            "compliance_items_count": len(plan.compliance_items),
            "milestones": plan.milestones,
            "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }

    def get_plan(self, plan_id: str) -> CertificationPlan | None:
        return self._plans.get(plan_id)

    def get_item(self, item_id: str) -> ComplianceItem | None:
        return self._items.get(item_id)