from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.domain.entities.v1.design_twin import DesignTwin, DesignParameter
from src.domain.entities.v1.manufacturing_twin import ManufacturingTwin, DimensionDeviation, ProcessRecord
from src.domain.entities.v1.flight_twin import FlightTwin, FlightParameters, StructuralLoad, SystemStatus
from src.domain.entities.v1.maintenance_twin import MaintenanceTwin, MaintenanceRecord, ComponentReplacement, RemainingLife, HealthIndicator

logger = logging.getLogger(__name__)

DATA_LAG_THRESHOLD_SECONDS = 300


class ConflictResolution:
    PRIORITY_ORDER = ["measured", "design", "inferred"]

    @classmethod
    def resolve(cls, sources: dict[str, Any]) -> str:
        for source in cls.PRIORITY_ORDER:
            if source in sources and sources[source] is not None:
                return source
        return list(sources.keys())[0] if sources else "unknown"


class TwinSyncService:
    def __init__(self, event_publisher: Any | None = None) -> None:
        self._design_twins: dict[str, DesignTwin] = {}
        self._manufacturing_twins: dict[str, ManufacturingTwin] = {}
        self._flight_twins: dict[str, FlightTwin] = {}
        self._maintenance_twins: dict[str, MaintenanceTwin] = {}
        self._event_publisher = event_publisher

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    def _get_or_create_design_twin(self, aircraft_sn: str) -> DesignTwin:
        if aircraft_sn not in self._design_twins:
            self._design_twins[aircraft_sn] = DesignTwin(aircraft_serial_number=aircraft_sn)
        return self._design_twins[aircraft_sn]

    def _get_or_create_manufacturing_twin(self, aircraft_sn: str) -> ManufacturingTwin:
        if aircraft_sn not in self._manufacturing_twins:
            self._manufacturing_twins[aircraft_sn] = ManufacturingTwin(aircraft_serial_number=aircraft_sn)
        return self._manufacturing_twins[aircraft_sn]

    def _get_or_create_flight_twin(self, aircraft_sn: str) -> FlightTwin:
        if aircraft_sn not in self._flight_twins:
            self._flight_twins[aircraft_sn] = FlightTwin(aircraft_serial_number=aircraft_sn)
        return self._flight_twins[aircraft_sn]

    def _get_or_create_maintenance_twin(self, aircraft_sn: str) -> MaintenanceTwin:
        if aircraft_sn not in self._maintenance_twins:
            self._maintenance_twins[aircraft_sn] = MaintenanceTwin(aircraft_serial_number=aircraft_sn)
        return self._maintenance_twins[aircraft_sn]

    async def sync_design_twin(self, aircraft_sn: str, parameters: list[dict[str, Any]], model_version: int) -> DesignTwin:
        twin = self._get_or_create_design_twin(aircraft_sn)
        design_params = [
            DesignParameter(
                name=p["name"],
                value=p["value"],
                unit=p["unit"],
                tolerance=p.get("tolerance", 0.0),
                source=p.get("source", "design"),
            )
            for p in parameters
        ]
        twin.update_from_design_change(design_params, model_version)
        await self._publish_event("twin.data.sync", {
            "twin_type": "design",
            "aircraft_sn": aircraft_sn,
            "model_version": model_version,
            "parameter_count": len(design_params),
            "sync_time": twin.last_sync_time.isoformat() if twin.last_sync_time else None,
        })
        logger.info(f"Design twin synced for {aircraft_sn}, version {model_version}")
        return twin

    async def sync_manufacturing_twin(self, aircraft_sn: str, dimensions: dict[str, float], deviations: list[dict[str, Any]], process_records: list[dict[str, Any]]) -> ManufacturingTwin:
        twin = self._get_or_create_manufacturing_twin(aircraft_sn)
        dev_objects = [
            DimensionDeviation(
                parameter_name=d["parameter_name"],
                design_value=d["design_value"],
                actual_value=d["actual_value"],
                tolerance=d["tolerance"],
                unit=d["unit"],
            )
            for d in deviations
        ]
        pr_objects = [
            ProcessRecord(
                process_step=pr["process_step"],
                operator=pr["operator"],
                timestamp=pr["timestamp"],
                parameters=pr.get("parameters", {}),
                result=pr.get("result", "pass"),
            )
            for pr in process_records
        ]
        twin.sync_from_manufacturing(dimensions, dev_objects, pr_objects)
        await self._publish_event("twin.data.sync", {
            "twin_type": "manufacturing",
            "aircraft_sn": aircraft_sn,
            "deviation_count": len(dev_objects),
            "out_of_tolerance_count": len(twin.get_out_of_tolerance_deviations()),
            "sync_time": twin.last_sync_time.isoformat() if twin.last_sync_time else None,
        })
        logger.info(f"Manufacturing twin synced for {aircraft_sn}")
        return twin

    async def sync_flight_twin(self, aircraft_sn: str, flight_params: dict[str, Any], loads: list[dict[str, Any]] | None = None, systems: list[dict[str, Any]] | None = None) -> FlightTwin:
        twin = self._get_or_create_flight_twin(aircraft_sn)
        params = FlightParameters(**flight_params)
        load_objects = []
        if loads:
            load_objects = [
                StructuralLoad(
                    component_id=l["component_id"],
                    load_type=l["load_type"],
                    load_value=l["load_value"],
                    unit=l["unit"],
                    timestamp=l["timestamp"],
                    exceeds_limit=l.get("exceeds_limit", False),
                )
                for l in loads
            ]
        system_objects = []
        if systems:
            system_objects = [
                SystemStatus(
                    system_name=s["system_name"],
                    status=s["status"],
                    health_percentage=s.get("health_percentage", 100.0),
                    alerts=s.get("alerts", []),
                )
                for s in systems
            ]
        twin.update_flight_data(params, load_objects, system_objects)
        freshness = twin.check_data_freshness()
        if not freshness["is_fresh"]:
            logger.warning(f"Flight twin data lag for {aircraft_sn}: {freshness['lag_seconds']:.0f}s")
        await self._publish_event("twin.data.sync", {
            "twin_type": "flight",
            "aircraft_sn": aircraft_sn,
            "data_fresh": freshness["is_fresh"],
            "exceeded_loads": len(twin.get_exceeded_loads()),
            "sync_time": twin.last_data_time.isoformat() if twin.last_data_time else None,
        })
        return twin

    async def sync_maintenance_twin(self, aircraft_sn: str, records: list[dict[str, Any]], replacements: list[dict[str, Any]], life_updates: list[dict[str, Any]]) -> MaintenanceTwin:
        twin = self._get_or_create_maintenance_twin(aircraft_sn)
        mr_objects = [
            MaintenanceRecord(
                maintenance_id=r["maintenance_id"],
                maintenance_type=r["maintenance_type"],
                description=r["description"],
                performed_date=r["performed_date"],
                technician=r["technician"],
                findings=r.get("findings", []),
                corrective_actions=r.get("corrective_actions", []),
            )
            for r in records
        ]
        cr_objects = [
            ComponentReplacement(
                component_id=rp["component_id"],
                component_name=rp["component_name"],
                old_serial=rp["old_serial"],
                new_serial=rp["new_serial"],
                replacement_date=rp["replacement_date"],
                reason=rp["reason"],
            )
            for rp in replacements
        ]
        rl_objects = [
            RemainingLife(
                component_id=lu["component_id"],
                component_name=lu["component_name"],
                total_life_hours=lu["total_life_hours"],
                consumed_hours=lu["consumed_hours"],
                remaining_hours=lu["remaining_hours"],
                remaining_percentage=lu["remaining_percentage"],
            )
            for lu in life_updates
        ]
        twin.sync_from_maintenance(mr_objects, cr_objects, rl_objects)
        await self._publish_event("twin.data.sync", {
            "twin_type": "maintenance",
            "aircraft_sn": aircraft_sn,
            "status": twin.status.value,
            "components_due": len(twin.get_components_due_for_replacement()),
            "sync_time": twin.last_sync_time.isoformat() if twin.last_sync_time else None,
        })
        logger.info(f"Maintenance twin synced for {aircraft_sn}, status: {twin.status.value}")
        return twin

    def check_data_lag(self, aircraft_sn: str) -> dict[str, Any]:
        results = {}
        if aircraft_sn in self._design_twins:
            dt = self._design_twins[aircraft_sn]
            if dt.last_sync_time:
                elapsed = (datetime.now(timezone.utc) - dt.last_sync_time).total_seconds()
                results["design"] = {"lagged": elapsed > DATA_LAG_THRESHOLD_SECONDS, "lag_seconds": elapsed}
        if aircraft_sn in self._flight_twins:
            ft = self._flight_twins[aircraft_sn]
            freshness = ft.check_data_freshness()
            results["flight"] = {"lagged": not freshness["is_fresh"], "lag_seconds": freshness.get("lag_seconds", 0)}
        if aircraft_sn in self._maintenance_twins:
            mt = self._maintenance_twins[aircraft_sn]
            if mt.last_sync_time:
                elapsed = (datetime.now(timezone.utc) - mt.last_sync_time).total_seconds()
                results["maintenance"] = {"lagged": elapsed > DATA_LAG_THRESHOLD_SECONDS, "lag_seconds": elapsed}
        return {"aircraft_sn": aircraft_sn, "twins": results}

    def resolve_conflict(self, aircraft_sn: str, parameter_name: str, sources: dict[str, float]) -> dict[str, Any]:
        resolved_source = ConflictResolution.resolve({k: True for k, v in sources.items() if v is not None})
        resolved_value = sources.get(resolved_source)
        return {
            "aircraft_sn": aircraft_sn,
            "parameter_name": parameter_name,
            "sources": sources,
            "resolved_source": resolved_source,
            "resolved_value": resolved_value,
        }

    def get_design_twin(self, aircraft_sn: str) -> DesignTwin | None:
        return self._design_twins.get(aircraft_sn)

    def get_manufacturing_twin(self, aircraft_sn: str) -> ManufacturingTwin | None:
        return self._manufacturing_twins.get(aircraft_sn)

    def get_flight_twin(self, aircraft_sn: str) -> FlightTwin | None:
        return self._flight_twins.get(aircraft_sn)

    def get_maintenance_twin(self, aircraft_sn: str) -> MaintenanceTwin | None:
        return self._maintenance_twins.get(aircraft_sn)