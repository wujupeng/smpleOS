from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent


class FusionStatus(str, Enum):
    PARTIAL_FUSION = "partial_fusion"
    FULL_FUSION = "full_fusion"
    SYNC_LOST = "sync_lost"
    NOT_FUSED = "not_fused"


class InsightSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class InsightCategory(str, Enum):
    DESIGN_DEVIATION = "design_deviation"
    MANUFACTURING_IMPACT = "manufacturing_impact"
    FLIGHT_PERFORMANCE = "flight_performance"
    MAINTENANCE_RECOMMENDATION = "maintenance_recommendation"
    CROSS_DOMAIN = "cross_domain"


class ConflictResolution(str, Enum):
    MEASURED_WINS = "measured_wins"
    DESIGN_WINS = "design_wins"
    INFERRED_WINS = "inferred_wins"
    MANUAL_REVIEW = "manual_review"
    PENDING = "pending"


@dataclass
class TwinReference:
    twin_id: str
    twin_type: str
    status: str = "active"
    last_sync: datetime | None = None
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "twin_id": self.twin_id,
            "twin_type": self.twin_type,
            "status": self.status,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "version": self.version,
            "metadata": self.metadata,
        }


@dataclass
class CrossTwinInsight:
    insight_id: str
    category: InsightCategory
    severity: InsightSeverity
    source_twin: str
    target_twin: str
    description: str
    evidence: dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "source_twin": self.source_twin,
            "target_twin": self.target_twin,
            "description": self.description,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
        }


@dataclass
class TwinDataConflict:
    conflict_id: str
    parameter: str
    design_value: Any = None
    measured_value: Any = None
    inferred_value: Any = None
    deviation_percent: float = 0.0
    resolution: ConflictResolution = ConflictResolution.PENDING
    resolved_value: Any = None
    resolved_by: str = ""
    resolved_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "parameter": self.parameter,
            "design_value": self.design_value,
            "measured_value": self.measured_value,
            "inferred_value": self.inferred_value,
            "deviation_percent": self.deviation_percent,
            "resolution": self.resolution.value,
            "resolved_value": self.resolved_value,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class FusionRecord:
    record_id: str
    fusion_version: int
    design_data_hash: str = ""
    manufacturing_data_hash: str = ""
    flight_data_hash: str = ""
    maintenance_data_hash: str = ""
    insights_generated: int = 0
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    fused_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "fusion_version": self.fusion_version,
            "design_data_hash": self.design_data_hash,
            "manufacturing_data_hash": self.manufacturing_data_hash,
            "flight_data_hash": self.flight_data_hash,
            "maintenance_data_hash": self.maintenance_data_hash,
            "insights_generated": self.insights_generated,
            "conflicts_detected": self.conflicts_detected,
            "conflicts_resolved": self.conflicts_resolved,
            "fused_at": self.fused_at.isoformat(),
            "duration_ms": self.duration_ms,
        }


class UnifiedTwin(AggregateRoot):
    def __init__(
        self,
        aircraft_serial_number: str,
        tenant_id: str,
        project_id: str,
    ) -> None:
        super().__init__()
        self.aircraft_serial_number = aircraft_serial_number
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.design_twin_ref: TwinReference | None = None
        self.manufacturing_twin_ref: TwinReference | None = None
        self.flight_twin_ref: TwinReference | None = None
        self.maintenance_twin_ref: TwinReference | None = None
        self.fusion_status = FusionStatus.NOT_FUSED
        self.last_fusion_time: datetime | None = None
        self.fusion_version: int = 0
        self.cross_twin_insights: list[CrossTwinInsight] = []
        self.conflicts: list[TwinDataConflict] = []
        self.fusion_records: list[FusionRecord] = []
        self.created_at = datetime.now(timezone.utc)

    def set_twin_reference(self, twin_type: str, ref: TwinReference) -> None:
        refs = {
            "design": "design_twin_ref",
            "manufacturing": "manufacturing_twin_ref",
            "flight": "flight_twin_ref",
            "maintenance": "maintenance_twin_ref",
        }
        attr = refs.get(twin_type)
        if attr:
            setattr(self, attr, ref)

    def get_active_twin_count(self) -> int:
        count = 0
        for ref in [self.design_twin_ref, self.manufacturing_twin_ref,
                     self.flight_twin_ref, self.maintenance_twin_ref]:
            if ref and ref.status == "active":
                count += 1
        return count

    def add_insight(self, insight: CrossTwinInsight) -> None:
        self.cross_twin_insights.append(insight)

    def add_conflict(self, conflict: TwinDataConflict) -> None:
        self.conflicts.append(conflict)

    def add_fusion_record(self, record: FusionRecord) -> None:
        self.fusion_records.append(record)
        self.fusion_version = record.fusion_version
        self.last_fusion_time = record.fused_at

    def update_fusion_status(self) -> None:
        active = self.get_active_twin_count()
        if active == 4:
            self.fusion_status = FusionStatus.FULL_FUSION
        elif active > 0:
            self.fusion_status = FusionStatus.PARTIAL_FUSION
        else:
            self.fusion_status = FusionStatus.SYNC_LOST

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "aircraft_serial_number": self.aircraft_serial_number,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "design_twin_ref": self.design_twin_ref.to_dict() if self.design_twin_ref else None,
            "manufacturing_twin_ref": self.manufacturing_twin_ref.to_dict() if self.manufacturing_twin_ref else None,
            "flight_twin_ref": self.flight_twin_ref.to_dict() if self.flight_twin_ref else None,
            "maintenance_twin_ref": self.maintenance_twin_ref.to_dict() if self.maintenance_twin_ref else None,
            "fusion_status": self.fusion_status.value,
            "last_fusion_time": self.last_fusion_time.isoformat() if self.last_fusion_time else None,
            "fusion_version": self.fusion_version,
            "active_twin_count": self.get_active_twin_count(),
            "insights_count": len(self.cross_twin_insights),
            "conflicts_count": len(self.conflicts),
            "created_at": self.created_at.isoformat(),
        }

    def to_detail_dict(self) -> dict[str, Any]:
        base = self.to_dict()
        base.update({
            "cross_twin_insights": [i.to_dict() for i in self.cross_twin_insights],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "fusion_records": [r.to_dict() for r in self.fusion_records],
        })
        return base