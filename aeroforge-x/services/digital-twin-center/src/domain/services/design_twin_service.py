from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .digital_twin import DigitalTwin, TwinType
from .twin_domain_service import TwinDomainService

logger = logging.getLogger(__name__)


@dataclass
class ParamChangeRecord:
    param_name: str
    old_value: Any
    new_value: Any
    reason: str
    changed_by: str
    changed_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "param_name": self.param_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at,
        }


class DesignTwinService:
    def __init__(self, twin_service: TwinDomainService) -> None:
        self._twin_service = twin_service
        self._param_history: dict[str, list[ParamChangeRecord]] = {}

    def sync_with_design(
        self,
        aircraft_sn: str,
        design_params: dict[str, Any],
        changed_by: str = "system",
        reason: str = "design_update",
    ) -> DigitalTwin | None:
        twins = self._twin_service.get_twin_by_aircraft_sn(aircraft_sn, TwinType.DESIGN)
        if not twins:
            twin = self._twin_service.create_twin(
                aircraft_serial_number=aircraft_sn,
                twin_type=TwinType.DESIGN,
                entity_id=aircraft_sn,
                entity_type="aircraft_spec",
            )
        else:
            twin = twins[0]

        old_payload = dict(twin.twin_payload)
        self._record_param_changes(twin.id, old_payload, design_params, changed_by, reason)

        twin.sync("design_sync", design_params)
        logger.info("Design twin synced: sn=%s version=%d", aircraft_sn, twin.data_version)
        return twin

    def _record_param_changes(
        self,
        twin_id: str,
        old_params: dict[str, Any],
        new_params: dict[str, Any],
        changed_by: str,
        reason: str,
    ) -> None:
        from datetime import datetime, timezone

        if twin_id not in self._param_history:
            self._param_history[twin_id] = []

        for key, new_val in new_params.items():
            old_val = old_params.get(key)
            if old_val != new_val:
                record = ParamChangeRecord(
                    param_name=key,
                    old_value=old_val,
                    new_value=new_val,
                    reason=reason,
                    changed_by=changed_by,
                    changed_at=datetime.now(timezone.utc).isoformat(),
                )
                self._param_history[twin_id].append(record)

    def get_design_snapshot(self, aircraft_sn: str, as_of: str | None = None) -> dict[str, Any] | None:
        twins = self._twin_service.get_twin_by_aircraft_sn(aircraft_sn, TwinType.DESIGN)
        if not twins:
            return None
        twin = twins[0]
        return {
            "aircraft_sn": aircraft_sn,
            "twin_id": twin.id,
            "data_version": twin.data_version,
            "snapshot": dict(twin.twin_payload),
            "as_of": as_of or twin.updated_at.isoformat(),
        }

    def compare_design_versions(
        self, aircraft_sn: str, version_a: int, version_b: int,
    ) -> dict[str, Any] | None:
        twins = self._twin_service.get_twin_by_aircraft_sn(aircraft_sn, TwinType.DESIGN)
        if not twins:
            return None
        twin = twins[0]
        history = self._param_history.get(twin.id, [])

        changes_a = [c for c in history if c.to_dict().get("param_name")]
        return {
            "aircraft_sn": aircraft_sn,
            "version_a": version_a,
            "version_b": version_b,
            "total_changes": len(changes_a),
            "changes": [c.to_dict() for c in changes_a],
        }

    def get_param_history(self, aircraft_sn: str) -> list[dict[str, Any]]:
        twins = self._twin_service.get_twin_by_aircraft_sn(aircraft_sn, TwinType.DESIGN)
        if not twins:
            return []
        twin = twins[0]
        return [r.to_dict() for r in self._param_history.get(twin.id, [])]