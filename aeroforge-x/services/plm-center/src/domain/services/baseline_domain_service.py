from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent
from aeroforge_common.utils.helpers import generate_code

logger = logging.getLogger(__name__)


class BaselineObjectRef:
    def __init__(
        self,
        object_id: str,
        object_type: str,
        version: str,
        name: str = "",
        is_immutable: bool = False,
    ) -> None:
        self.object_id = object_id
        self.object_type = object_type
        self.version = version
        self.name = name
        self.is_immutable = is_immutable

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "object_type": self.object_type,
            "version": self.version,
            "name": self.name,
            "is_immutable": self.is_immutable,
        }


class Baseline(AggregateRoot):
    def __init__(
        self,
        name: str,
        description: str = "",
        created_by: str = "",
    ) -> None:
        super().__init__()
        self.baseline_code: str = generate_code("AAF-BL")
        self.name = name
        self.description = description
        self.status: str = "open"
        self.objects: list[BaselineObjectRef] = []
        self.created_by = created_by
        self.frozen_at: datetime | None = None
        self.unfrozen_at: datetime | None = None
        self.created_at: datetime = datetime.now(timezone.utc)

    def add_object(self, obj: BaselineObjectRef) -> None:
        if self.status == "frozen":
            raise ValueError("Cannot add objects to a frozen baseline")
        existing = next((o for o in self.objects if o.object_id == obj.object_id), None)
        if existing:
            existing.version = obj.version
            existing.name = obj.name
        else:
            self.objects.append(obj)

    def remove_object(self, object_id: str) -> bool:
        if self.status == "frozen":
            raise ValueError("Cannot remove objects from a frozen baseline")
        for i, obj in enumerate(self.objects):
            if obj.object_id == object_id:
                self.objects.pop(i)
                return True
        return False

    def freeze(self) -> None:
        if self.status == "frozen":
            raise ValueError("Baseline is already frozen")
        if not self.objects:
            raise ValueError("Cannot freeze empty baseline")
        self.status = "frozen"
        self.frozen_at = datetime.now(timezone.utc)
        for obj in self.objects:
            obj.is_immutable = True
        self.add_domain_event(DomainEvent(
            event_type="design.baseline.frozen",
            aggregate_id=self.id,
            payload={
                "baseline_id": self.id,
                "baseline_code": self.baseline_code,
                "object_count": len(self.objects),
                "frozen_at": self.frozen_at.isoformat(),
            },
        ))
        logger.info("Baseline frozen: %s (%d objects)", self.baseline_code, len(self.objects))

    def unfreeze(self, approved_by: str = "") -> None:
        if self.status != "frozen":
            raise ValueError("Baseline is not frozen")
        self.status = "open"
        self.unfrozen_at = datetime.now(timezone.utc)
        for obj in self.objects:
            obj.is_immutable = False
        self.add_domain_event(DomainEvent(
            event_type="design.baseline.unfrozen",
            aggregate_id=self.id,
            payload={
                "baseline_id": self.id,
                "baseline_code": self.baseline_code,
                "approved_by": approved_by,
            },
        ))
        logger.info("Baseline unfrozen: %s by %s", self.baseline_code, approved_by)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "baseline_code": self.baseline_code,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "objects": [o.to_dict() for o in self.objects],
            "object_count": len(self.objects),
            "created_by": self.created_by,
            "frozen_at": self.frozen_at.isoformat() if self.frozen_at else None,
            "unfrozen_at": self.unfrozen_at.isoformat() if self.unfrozen_at else None,
            "created_at": self.created_at.isoformat(),
        }


class BaselineDomainService:
    def __init__(self) -> None:
        self._baselines: dict[str, Baseline] = {}

    def establish_baseline(
        self,
        name: str,
        description: str = "",
        created_by: str = "",
        objects: list[dict[str, Any]] | None = None,
    ) -> Baseline:
        baseline = Baseline(name=name, description=description, created_by=created_by)

        if objects:
            for obj_data in objects:
                ref = BaselineObjectRef(
                    object_id=obj_data["object_id"],
                    object_type=obj_data.get("object_type", "design_object"),
                    version=obj_data.get("version", "1.0"),
                    name=obj_data.get("name", ""),
                )
                baseline.add_object(ref)

        self._baselines[baseline.id] = baseline
        logger.info("Baseline established: %s with %d objects", baseline.baseline_code, len(baseline.objects))
        return baseline

    def freeze_baseline(self, baseline_id: str) -> Baseline | None:
        baseline = self._baselines.get(baseline_id)
        if baseline is None:
            return None
        baseline.freeze()
        return baseline

    def unfreeze_baseline(self, baseline_id: str, approved_by: str = "") -> Baseline | None:
        baseline = self._baselines.get(baseline_id)
        if baseline is None:
            return None
        baseline.unfreeze(approved_by)
        return baseline

    def get_baseline(self, baseline_id: str) -> Baseline | None:
        return self._baselines.get(baseline_id)

    def list_baselines(self) -> list[Baseline]:
        return list(self._baselines.values())

    def check_baseline_integrity(self, baseline_id: str) -> dict[str, Any]:
        baseline = self._baselines.get(baseline_id)
        if baseline is None:
            return {"baseline_id": baseline_id, "exists": False}

        missing_versions = [
            o.to_dict() for o in baseline.objects
            if not o.version or o.version == "0.0"
        ]

        return {
            "baseline_id": baseline_id,
            "baseline_code": baseline.baseline_code,
            "status": baseline.status,
            "exists": True,
            "total_objects": len(baseline.objects),
            "objects_with_versions": len(baseline.objects) - len(missing_versions),
            "missing_versions": missing_versions,
            "is_intact": len(missing_versions) == 0,
        }