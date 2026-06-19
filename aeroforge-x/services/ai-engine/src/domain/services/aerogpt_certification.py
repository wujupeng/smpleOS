from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ComplianceItem:
    def __init__(self, item_id: str, requirement: str, section: str, category: str):
        self.item_id = item_id
        self.requirement = requirement
        self.section = section
        self.category = category
        self.compliance_status: str = "pending"
        self.evidence_ref: str | None = None
        self.evidence_gap: bool = False
        self.suggested_evidence_source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "requirement": self.requirement,
            "section": self.section,
            "category": self.category,
            "compliance_status": self.compliance_status,
            "evidence_ref": self.evidence_ref,
            "evidence_gap": self.evidence_gap,
            "suggested_evidence_source": self.suggested_evidence_source,
        }


class ComplianceMatrix:
    def __init__(self, matrix_id: str, aircraft_type: str, regulation: str):
        self.matrix_id = matrix_id
        self.aircraft_type = aircraft_type
        self.regulation = regulation
        self.items: list[ComplianceItem] = []
        self.coverage_percentage: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "matrix_id": self.matrix_id,
            "aircraft_type": self.aircraft_type,
            "regulation": self.regulation,
            "items": [i.to_dict() for i in self.items],
            "coverage_percentage": self.coverage_percentage,
            "total_items": len(self.items),
            "compliant_items": sum(1 for i in self.items if i.compliance_status == "compliant"),
            "gap_items": sum(1 for i in self.items if i.evidence_gap),
        }


class CertificationPlan:
    def __init__(self, plan_id: str, aircraft_type: str):
        self.plan_id = plan_id
        self.aircraft_type = aircraft_type
        self.phases: list[dict[str, Any]] = []
        self.milestones: list[dict[str, Any]] = []
        self.estimated_duration_months: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "aircraft_type": self.aircraft_type,
            "phases": self.phases,
            "milestones": self.milestones,
            "estimated_duration_months": self.estimated_duration_months,
        }


class EvidenceCrossReference:
    def __init__(self, ref_id: str, matrix_id: str):
        self.ref_id = ref_id
        self.matrix_id = matrix_id
        self.cross_references: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "ref_id": self.ref_id,
            "matrix_id": self.matrix_id,
            "cross_references": self.cross_references,
        }


FAR25_REQUIREMENTS = [
    {"section": "25.301", "requirement": "Loads - General", "category": "structural"},
    {"section": "25.303", "requirement": "Factor of Safety", "category": "structural"},
    {"section": "25.305", "requirement": "Strength and Deformation", "category": "structural"},
    {"section": "25.307", "requirement": "Proof of Structure", "category": "structural"},
    {"section": "25.321", "requirement": "Flight Loads - General", "category": "flight"},
    {"section": "25.331", "requirement": "Symmetric Flight Conditions", "category": "flight"},
    {"section": "25.341", "requirement": "Gust and Turbulence Loads", "category": "flight"},
    {"section": "25.361", "requirement": "Engine Torque", "category": "flight"},
    {"section": "25.471", "requirement": "Landing Loads - General", "category": "landing"},
    {"section": "25.491", "requirement": "Taxi, Takeoff and Landing Roll", "category": "landing"},
    {"section": "25.561", "requirement": "Emergency Landing Conditions", "category": "emergency"},
    {"section": "25.562", "requirement": "Emergency Landing Dynamic Conditions", "category": "emergency"},
    {"section": "25.571", "requirement": "Damage Tolerance and Fatigue", "category": "structural"},
    {"section": "25.601", "requirement": "General - Structure", "category": "structural"},
    {"section": "25.603", "requirement": "Materials", "category": "materials"},
    {"section": "25.605", "requirement": "Fabrication Methods", "category": "manufacturing"},
    {"section": "25.609", "requirement": "Protection of Structure", "category": "structural"},
    {"section": "25.613", "requirement": "Material Strength Properties", "category": "materials"},
    {"section": "25.701", "requirement": "Flap and Slat Interconnection", "category": "systems"},
    {"section": "25.721", "requirement": "Landing Gear - General", "category": "landing"},
    {"section": "25.771", "requirement": "Pilot Compartment - General", "category": "systems"},
    {"section": "25.773", "requirement": "Pilot Compartment View", "category": "systems"},
    {"section": "25.783", "requirement": "Doors", "category": "systems"},
    {"section": "25.801", "requirement": "Ditching", "category": "emergency"},
    {"section": "25.807", "requirement": "Emergency Exits", "category": "emergency"},
    {"section": "25.813", "requirement": "Emergency Exit Access", "category": "emergency"},
    {"section": "25.851", "requirement": "Fire Extinguishers", "category": "fire"},
    {"section": "25.901", "requirement": "Installation - Powerplant", "category": "powerplant"},
    {"section": "25.903", "requirement": "Engines", "category": "powerplant"},
    {"section": "25.1181", "requirement": "Designated Fire Zones", "category": "fire"},
    {"section": "25.1301", "requirement": "Function and Installation", "category": "systems"},
    {"section": "25.1309", "requirement": "Equipment, Systems and Installations", "category": "systems"},
    {"section": "25.1321", "requirement": "Arrangement and Visibility", "category": "systems"},
    {"section": "25.1351", "requirement": "Electrical Systems - General", "category": "systems"},
    {"section": "25.1419", "requirement": "Ice Protection", "category": "systems"},
    {"section": "25.1435", "requirement": "Hydraulic Systems", "category": "systems"},
    {"section": "25.1461", "requirement": "Equipment in Designated Fire Zones", "category": "fire"},
    {"section": "25.1521", "requirement": "Operating Limitations", "category": "operational"},
    {"section": "25.1529", "requirement": "Instructions for Continued Airworthiness", "category": "maintenance"},
    {"section": "25.1581", "requirement": "Airplane Flight Manual - General", "category": "documentation"},
]


class AeroGPTCertification:
    def __init__(self, event_publisher: Any | None = None):
        self._event_publisher = event_publisher
        self._matrices: dict[str, ComplianceMatrix] = {}
        self._plans: dict[str, CertificationPlan] = {}
        self._cross_refs: dict[str, EvidenceCrossReference] = {}

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    def generate_compliance_matrix(self, aircraft_type: str, regulation: str = "FAR-25", existing_evidence: dict[str, str] | None = None) -> ComplianceMatrix:
        matrix = ComplianceMatrix(matrix_id=str(uuid4()), aircraft_type=aircraft_type, regulation=regulation)
        evidence = existing_evidence or {}

        requirements = FAR25_REQUIREMENTS
        for idx, req in enumerate(requirements):
            item = ComplianceItem(
                item_id=f"CI-{idx + 1:03d}",
                requirement=req["requirement"],
                section=req["section"],
                category=req["category"],
            )

            if req["section"] in evidence:
                item.evidence_ref = evidence[req["section"]]
                item.compliance_status = "compliant"
                item.evidence_gap = False
            else:
                item.compliance_status = "open"
                item.evidence_gap = True
                item.suggested_evidence_source = self._suggest_evidence_source(req["category"])

            matrix.items.append(item)

        compliant = sum(1 for i in matrix.items if i.compliance_status == "compliant")
        matrix.coverage_percentage = (compliant / len(matrix.items) * 100) if matrix.items else 0.0

        self._matrices[matrix.matrix_id] = matrix
        return matrix

    def generate_certification_plan(self, aircraft_type: str, compliance_matrix_id: str | None = None) -> CertificationPlan:
        plan = CertificationPlan(plan_id=str(uuid4()), aircraft_type=aircraft_type)

        plan.phases = [
            {
                "phase": "Phase 1 - Certification Basis",
                "duration_months": 6,
                "activities": [
                    "Establish certification basis and special conditions",
                    "Issue G-1 letter (certification plan agreement with authority)",
                    "Define means of compliance",
                ],
            },
            {
                "phase": "Phase 2 - Design and Analysis",
                "duration_months": 12,
                "activities": [
                    "Submit compliance documentation",
                    "Conduct structural analysis and testing",
                    "Conduct systems analysis and testing",
                ],
            },
            {
                "phase": "Phase 3 - Integration and Ground Test",
                "duration_months": 8,
                "activities": [
                    "Ground test campaign",
                    "Systems integration testing",
                    "Conformity inspections",
                ],
            },
            {
                "phase": "Phase 4 - Flight Test",
                "duration_months": 10,
                "activities": [
                    "Flight test campaign",
                    "Function and reliability testing",
                    "Type inspection authorization",
                ],
            },
            {
                "phase": "Phase 5 - Type Certification",
                "duration_months": 4,
                "activities": [
                    "Final compliance findings",
                    "Type certificate data sheet preparation",
                    "Type certificate issuance",
                ],
            },
        ]

        plan.milestones = [
            {"name": "G-1 Letter Issued", "phase": 1, "month": 6},
            {"name": "Design Review Complete", "phase": 2, "month": 18},
            {"name": "Ground Test Complete", "phase": 3, "month": 26},
            {"name": "First Flight", "phase": 4, "month": 28},
            {"name": "Flight Test Complete", "phase": 4, "month": 36},
            {"name": "Type Certificate Issued", "phase": 5, "month": 40},
        ]

        plan.estimated_duration_months = sum(p["duration_months"] for p in plan.phases)

        if compliance_matrix_id:
            matrix = self._matrices.get(compliance_matrix_id)
            if matrix:
                gap_count = sum(1 for i in matrix.items if i.evidence_gap)
                plan.phases[1]["activities"].append(f"Address {gap_count} compliance evidence gaps")

        self._plans[plan.plan_id] = plan
        return plan

    def generate_evidence_cross_reference(self, matrix_id: str, evidence_map: dict[str, list[str]] | None = None) -> EvidenceCrossReference:
        matrix = self._matrices.get(matrix_id)
        if not matrix:
            raise ValueError(f"Compliance matrix {matrix_id} not found")

        ref = EvidenceCrossReference(ref_id=str(uuid4()), matrix_id=matrix_id)
        ev_map = evidence_map or {}

        for item in matrix.items:
            evidence_refs = ev_map.get(item.section, [])
            ref.cross_references.append({
                "compliance_item_id": item.item_id,
                "section": item.section,
                "requirement": item.requirement,
                "evidence_documents": evidence_refs,
                "is_covered": len(evidence_refs) > 0,
            })

        self._cross_refs[ref.ref_id] = ref
        return ref

    def _suggest_evidence_source(self, category: str) -> str:
        suggestions = {
            "structural": "Structural analysis report (FEA) + static test results",
            "flight": "Flight loads analysis + flight test data",
            "landing": "Landing gear test report + drop test results",
            "emergency": "Crash test data + evacuation demonstration",
            "materials": "Material qualification test reports",
            "manufacturing": "Process qualification reports + NDT results",
            "systems": "System test reports + safety assessment (FTA/FMEA)",
            "fire": "Fire test reports + flammability test results",
            "powerplant": "Engine type certificate + installation test data",
            "operational": "Aircraft Flight Manual + operating limitations document",
            "maintenance": "ICAs (Instructions for Continued Airworthiness)",
            "documentation": "Airplane Flight Manual + approved documentation",
        }
        return suggestions.get(category, "Engineering analysis report + test evidence")

    def get_matrix(self, matrix_id: str) -> ComplianceMatrix | None:
        return self._matrices.get(matrix_id)

    def get_plan(self, plan_id: str) -> CertificationPlan | None:
        return self._plans.get(plan_id)