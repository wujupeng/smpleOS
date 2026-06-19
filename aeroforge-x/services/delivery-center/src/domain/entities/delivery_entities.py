from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent


class TestCategory(str, Enum):
    PERFORMANCE = "performance"
    STABILITY = "stability"
    CONTROLLABILITY = "controllability"
    STRUCTURAL = "structural"
    SYSTEMS = "systems"
    FLUTTER = "flutter"
    STALL = "stall"
    ENGINE = "engine"
    AVIONICS = "avionics"
    ENVIRONMENTAL = "environmental"


class TestPointStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class FlightCondition(str, Enum):
    TAKEOFF = "takeoff"
    CLIMB = "climb"
    CRUISE = "cruise"
    DESCENT = "descent"
    APPROACH = "approach"
    LANDING = "landing"
    HIGH_SPEED = "high_speed"
    LOW_SPEED = "low_speed"
    HIGH_ALTITUDE = "high_altitude"
    LOW_ALTITUDE = "low_altitude"


@dataclass
class TestDataRequirement:
    parameter: str
    unit: str
    sample_rate_hz: float
    accuracy: str = ""
    min_duration_seconds: float = 10.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter": self.parameter,
            "unit": self.unit,
            "sample_rate_hz": self.sample_rate_hz,
            "accuracy": self.accuracy,
            "min_duration_seconds": self.min_duration_seconds,
        }


@dataclass
class SafetyBoundary:
    parameter: str
    min_value: float | None = None
    max_value: float | None = None
    unit: str = ""
    abort_criteria: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter": self.parameter,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "unit": self.unit,
            "abort_criteria": self.abort_criteria,
        }


@dataclass
class TestPoint:
    point_id: str
    name: str
    flight_condition: FlightCondition
    altitude_ft: float = 0
    speed_ktas: float = 0
    weight_kg: float = 0
    cg_position_percent: float = 50.0
    status: TestPointStatus = TestPointStatus.PLANNED
    data_requirements: list[TestDataRequirement] = field(default_factory=list)
    safety_boundaries: list[SafetyBoundary] = field(default_factory=list)
    certification_clause: str = ""
    estimated_duration_minutes: float = 30.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "point_id": self.point_id,
            "name": self.name,
            "flight_condition": self.flight_condition.value,
            "altitude_ft": self.altitude_ft,
            "speed_ktas": self.speed_ktas,
            "weight_kg": self.weight_kg,
            "cg_position_percent": self.cg_position_percent,
            "status": self.status.value,
            "data_requirements": [d.to_dict() for d in self.data_requirements],
            "safety_boundaries": [b.to_dict() for b in self.safety_boundaries],
            "certification_clause": self.certification_clause,
            "estimated_duration_minutes": self.estimated_duration_minutes,
        }


@dataclass
class TestSubject:
    subject_id: str
    category: TestCategory
    objective: str
    method: str
    test_points: list[TestPoint] = field(default_factory=list)
    certification_clauses: list[str] = field(default_factory=list)
    priority: int = 1
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "category": self.category.value,
            "objective": self.objective,
            "method": self.method,
            "test_points": [p.to_dict() for p in self.test_points],
            "certification_clauses": self.certification_clauses,
            "priority": self.priority,
            "dependencies": [d for d in self.dependencies],
        }


class FlightTestPlan(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        project_id: str,
        aircraft_model: str,
        certification_standard: str,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.aircraft_model = aircraft_model
        self.certification_standard = certification_standard
        self.subjects: list[TestSubject] = []
        self.total_flights: int = 0
        self.total_flight_hours: float = 0.0
        self.coverage_percentage: float = 0.0
        self.created_at = datetime.now(timezone.utc)
        self.status = "draft"

    def add_subject(self, subject: TestSubject) -> None:
        self.subjects.append(subject)
        self._recalculate()

    def _recalculate(self) -> None:
        total_points = sum(len(s.test_points) for s in self.subjects)
        total_duration = sum(
            p.estimated_duration_minutes
            for s in self.subjects
            for p in s.test_points
        )
        self.total_flight_hours = round(total_duration / 60, 1)
        self.total_flights = max(1, int(total_points / 8) + 1)

    def calculate_coverage(self, required_clauses: list[str]) -> dict[str, Any]:
        covered: set[str] = set()
        for subject in self.subjects:
            covered.update(subject.certification_clauses)

        required_set = set(required_clauses)
        covered_set = covered & required_set
        uncovered = required_set - covered

        self.coverage_percentage = round(len(covered_set) / len(required_set) * 100, 1) if required_set else 100.0

        return {
            "total_required": len(required_set),
            "covered": len(covered_set),
            "uncovered": len(uncovered),
            "coverage_percentage": self.coverage_percentage,
            "uncovered_clauses": sorted(uncovered),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "aircraft_model": self.aircraft_model,
            "certification_standard": self.certification_standard,
            "subjects": [s.to_dict() for s in self.subjects],
            "total_flights": self.total_flights,
            "total_flight_hours": self.total_flight_hours,
            "coverage_percentage": self.coverage_percentage,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
        }


@dataclass
class DeliveryDocument:
    doc_id: str
    doc_type: str
    name: str
    version: str
    status: str = "pending"
    file_path: str = ""
    pages: int = 0
    required: bool = True
    signatures: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "doc_type": self.doc_type,
            "name": self.name,
            "version": self.version,
            "status": self.status,
            "file_path": self.file_path,
            "pages": self.pages,
            "required": self.required,
            "signatures": self.signatures,
        }


class DeliveryPackage(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        project_id: str,
        aircraft_model: str,
        package_type: str = "full",
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.aircraft_model = aircraft_model
        self.package_type = package_type
        self.documents: list[DeliveryDocument] = []
        self.completeness_score: float = 0.0
        self.missing_items: list[dict[str, Any]] = []
        self.created_at = datetime.now(timezone.utc)
        self.generated_at: datetime | None = None
        self.status = "draft"

    def add_document(self, doc: DeliveryDocument) -> None:
        self.documents.append(doc)

    def validate_completeness(self, required_types: list[str]) -> dict[str, Any]:
        present_types = {d.doc_type for d in self.documents if d.status in ("approved", "final")}
        missing = [t for t in required_types if t not in present_types]

        missing_details = []
        for doc_type in missing:
            missing_details.append({
                "doc_type": doc_type,
                "reason": "Document not found or not approved",
                "suggestion": f"Generate or approve {doc_type} document",
            })

        pending_docs = [d for d in self.documents if d.status == "pending"]
        for doc in pending_docs:
            if doc.required:
                missing_details.append({
                    "doc_type": doc.doc_type,
                    "reason": f"Document '{doc.name}' pending approval",
                    "suggestion": f"Complete approval for {doc.name}",
                })

        self.missing_items = missing_details
        total_required = len(required_types)
        covered = total_required - len([m for m in missing if m])
        self.completeness_score = round(covered / total_required * 100, 1) if total_required > 0 else 100.0

        return {
            "completeness_score": self.completeness_score,
            "total_required_types": total_required,
            "covered_types": covered,
            "missing_items": missing_details,
            "is_complete": len(missing) == 0 and len(pending_docs) == 0,
        }

    def generate_index(self) -> dict[str, Any]:
        by_type: dict[str, list[dict]] = {}
        for doc in self.documents:
            by_type.setdefault(doc.doc_type, []).append(doc.to_dict())

        signature_status = []
        for doc in self.documents:
            for sig in doc.signatures:
                signature_status.append({
                    "document": doc.name,
                    "signer": sig.get("signer", ""),
                    "status": sig.get("status", "pending"),
                })

        return {
            "package_id": self.id,
            "aircraft_model": self.aircraft_model,
            "total_documents": len(self.documents),
            "documents_by_type": by_type,
            "signature_tracking": signature_status,
            "completeness_score": self.completeness_score,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "aircraft_model": self.aircraft_model,
            "package_type": self.package_type,
            "documents": [d.to_dict() for d in self.documents],
            "completeness_score": self.completeness_score,
            "missing_items": self.missing_items,
            "created_at": self.created_at.isoformat(),
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "status": self.status,
        }