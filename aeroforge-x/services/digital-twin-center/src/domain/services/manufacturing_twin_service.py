from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .digital_twin import DigitalTwin, TwinType
from .twin_domain_service import TwinDomainService

logger = logging.getLogger(__name__)


@dataclass
class DeviationRecord:
    dimension_name: str
    design_value: float
    actual_value: float
    tolerance: float
    deviation: float
    is_out_of_tolerance: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_name": self.dimension_name,
            "design_value": self.design_value,
            "actual_value": self.actual_value,
            "tolerance": self.tolerance,
            "deviation": self.deviation,
            "is_out_of_tolerance": self.is_out_of_tolerance,
        }


class ManufacturingTwinService:
    def __init__(self, twin_service: TwinDomainService) -> None:
        self._twin_service = twin_service
        self._deviations: dict[str, list[DeviationRecord]] = {}

    def sync_with_measurement(
        self,
        aircraft_sn: str,
        measurement_data: dict[str, float],
        design_data: dict[str, float] | None = None,
        tolerances: dict[str, float] | None = None,
    ) -> DigitalTwin | None:
        twins = self._twin_service.get_twin_by_aircraft_sn(aircraft_sn, TwinType.MANUFACTURING)
        if not twins:
            twin = self._twin_service.create_twin(
                aircraft_serial_number=aircraft_sn,
                twin_type=TwinType.MANUFACTURING,
                entity_id=aircraft_sn,
                entity_type="manufactured_part",
            )
        else:
            twin = twins[0]

        payload: dict[str, Any] = {"actual_dimensions": measurement_data}
        if design_data:
            deviations = self._calculate_deviations(
                twin.id, measurement_data, design_data, tolerances or {}
            )
            payload["deviations"] = [d.to_dict() for d in deviations]
            out_of_tol = [d for d in deviations if d.is_out_of_tolerance]
            if out_of_tol:
                payload["out_of_tolerance_count"] = len(out_of_tol)

        twin.sync("measurement_sync", payload)
        logger.info("Manufacturing twin synced: sn=%s deviations=%d", aircraft_sn, len(self._deviations.get(twin.id, [])))
        return twin

    def _calculate_deviations(
        self,
        twin_id: str,
        actual: dict[str, float],
        design: dict[str, float],
        tolerances: dict[str, float],
    ) -> list[DeviationRecord]:
        deviations = []
        for dim_name, actual_val in actual.items():
            design_val = design.get(dim_name, actual_val)
            tol = tolerances.get(dim_name, abs(design_val * 0.01) if design_val != 0 else 0.1)
            dev = actual_val - design_val
            is_oot = abs(dev) > tol

            record = DeviationRecord(
                dimension_name=dim_name,
                design_value=design_val,
                actual_value=actual_val,
                tolerance=tol,
                deviation=round(dev, 6),
                is_out_of_tolerance=is_oot,
            )
            deviations.append(record)

        self._deviations[twin_id] = deviations
        return deviations

    def get_manufacturing_snapshot(self, aircraft_sn: str) -> dict[str, Any] | None:
        twins = self._twin_service.get_twin_by_aircraft_sn(aircraft_sn, TwinType.MANUFACTURING)
        if not twins:
            return None
        twin = twins[0]
        return {
            "aircraft_sn": aircraft_sn,
            "twin_id": twin.id,
            "data_version": twin.data_version,
            "actual_dimensions": twin.twin_payload.get("actual_dimensions", {}),
            "deviation_count": len(self._deviations.get(twin.id, [])),
            "out_of_tolerance_count": sum(
                1 for d in self._deviations.get(twin.id, []) if d.is_out_of_tolerance
            ),
        }

    def compare_with_design(self, aircraft_sn: str) -> dict[str, Any] | None:
        mfg_twins = self._twin_service.get_twin_by_aircraft_sn(aircraft_sn, TwinType.MANUFACTURING)
        design_twins = self._twin_service.get_twin_by_aircraft_sn(aircraft_sn, TwinType.DESIGN)
        if not mfg_twins:
            return None

        mfg_twin = mfg_twins[0]
        deviations = self._deviations.get(mfg_twin.id, [])

        return {
            "aircraft_sn": aircraft_sn,
            "manufacturing_twin_id": mfg_twin.id,
            "design_twin_id": design_twins[0].id if design_twins else None,
            "total_dimensions_compared": len(deviations),
            "out_of_tolerance_count": sum(1 for d in deviations if d.is_out_of_tolerance),
            "deviations": [d.to_dict() for d in deviations],
        }

    def get_deviation_statistics(self, aircraft_sn: str) -> dict[str, Any]:
        mfg_twins = self._twin_service.get_twin_by_aircraft_sn(aircraft_sn, TwinType.MANUFACTURING)
        if not mfg_twins:
            return {"aircraft_sn": aircraft_sn, "statistics": {}}

        deviations = self._deviations.get(mfg_twins[0].id, [])
        if not deviations:
            return {"aircraft_sn": aircraft_sn, "statistics": {"total": 0}}

        oot_count = sum(1 for d in deviations if d.is_out_of_tolerance)
        avg_dev = sum(abs(d.deviation) for d in deviations) / len(deviations)

        return {
            "aircraft_sn": aircraft_sn,
            "statistics": {
                "total_dimensions": len(deviations),
                "out_of_tolerance": oot_count,
                "in_tolerance": len(deviations) - oot_count,
                "avg_deviation": round(avg_dev, 6),
                "max_deviation": round(max(abs(d.deviation) for d in deviations), 6),
            },
        }