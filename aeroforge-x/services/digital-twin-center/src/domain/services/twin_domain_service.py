from __future__ import annotations

import logging
from typing import Any

from .digital_twin import DigitalTwin, SyncStatus, TwinType

logger = logging.getLogger(__name__)


class TwinDomainService:
    def __init__(self) -> None:
        self._twins: dict[str, DigitalTwin] = {}

    def create_twin(
        self,
        aircraft_serial_number: str,
        twin_type: TwinType = TwinType.DESIGN,
        entity_id: str = "",
        entity_type: str = "",
    ) -> DigitalTwin:
        twin = DigitalTwin(
            aircraft_serial_number=aircraft_serial_number,
            twin_type=twin_type,
            entity_id=entity_id,
            entity_type=entity_type,
        )
        self._twins[twin.id] = twin
        logger.info("Created twin: id=%s sn=%s type=%s", twin.id, aircraft_serial_number, twin_type.value)
        return twin

    def sync_twin(self, twin_id: str, sync_type: str, payload: dict[str, Any] | None = None) -> DigitalTwin | None:
        twin = self._twins.get(twin_id)
        if twin is None:
            return None
        twin.sync(sync_type, payload)
        logger.info("Synced twin: id=%s type=%s version=%d", twin.id, sync_type, twin.data_version)
        return twin

    def get_twin(self, twin_id: str) -> DigitalTwin | None:
        return self._twins.get(twin_id)

    def get_twin_by_aircraft_sn(self, aircraft_sn: str, twin_type: TwinType | None = None) -> list[DigitalTwin]:
        results = []
        for twin in self._twins.values():
            if twin.aircraft_serial_number == aircraft_sn:
                if twin_type is None or twin.twin_type == twin_type:
                    results.append(twin)
        return results

    def check_sync_status(self, twin_id: str) -> dict[str, Any] | None:
        twin = self._twins.get(twin_id)
        if twin is None:
            return None
        return twin.detect_data_lag()

    def restrict_safety_decisions(self, twin_id: str) -> dict[str, Any] | None:
        twin = self._twins.get(twin_id)
        if twin is None:
            return None
        return twin.restrict_safety_decisions()

    def list_twins(self, twin_type: TwinType | None = None) -> list[DigitalTwin]:
        if twin_type is None:
            return list(self._twins.values())
        return [t for t in self._twins.values() if t.twin_type == twin_type]