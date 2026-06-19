from __future__ import annotations

from typing import Any

from ..domain.entities.aircraft_spec import AircraftSpec
from ..domain.services.spec_domain_service import SpecDomainService
from ..infrastructure.persistence.spec_repository import SpecRepository


class SpecApplicationService:
    def __init__(self, repo: SpecRepository) -> None:
        self._repo = repo
        self._domain_service = SpecDomainService()

    async def create_spec(self, params: dict[str, Any], created_by: str) -> AircraftSpec:
        spec = AircraftSpec(
            aircraft_type=params.get("aircraft_type", "fixed_wing"),
            payload_kg=params.get("payload_kg", 0.0),
            range_km=params.get("range_km", 0.0),
            cruise_speed_kmh=params.get("cruise_speed_kmh", 0.0),
            takeoff_distance_m=params.get("takeoff_distance_m", 0.0),
            power_type=params.get("power_type", "electric"),
            budget_cny=params.get("budget_cny"),
            material_id=params.get("material_id"),
            certification_level_id=params.get("certification_level_id"),
            created_by=created_by,
        )
        self._domain_service.generate_spec_document(spec)
        await self._repo.save(spec)
        return spec

    async def get_spec(self, spec_id: str) -> dict[str, Any] | None:
        return await self._repo.find_by_id(spec_id)

    async def list_specs(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        offset = (page - 1) * page_size
        items = await self._repo.find_all(offset=offset, limit=page_size)
        total = await self._repo.count()
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_spec(self, spec_id: str, params: dict[str, Any]) -> dict[str, Any] | None:
        existing = await self._repo.find_by_id(spec_id)
        if existing is None:
            return None
        spec = AircraftSpec(
            spec_id=existing["id"],
            aircraft_type=existing["aircraft_type"],
            payload_kg=existing["payload_kg"],
            range_km=existing["range_km"],
            cruise_speed_kmh=existing["cruise_speed_kmh"],
            takeoff_distance_m=existing["takeoff_distance_m"],
            power_type=existing["power_type"],
            budget_cny=existing["budget_cny"],
            material_id=existing["material_id"],
            certification_level_id=existing["certification_level_id"],
            created_by=existing["created_by"],
        )
        spec.spec_code = existing["spec_code"]
        spec.status = existing["status"]
        spec.update_parameters(
            payload_kg=params.get("payload_kg"),
            range_km=params.get("range_km"),
            cruise_speed_kmh=params.get("cruise_speed_kmh"),
            takeoff_distance_m=params.get("takeoff_distance_m"),
            power_type=params.get("power_type"),
            budget_cny=params.get("budget_cny"),
            material_id=params.get("material_id"),
            certification_level_id=params.get("certification_level_id"),
            aircraft_type=params.get("aircraft_type"),
        )
        self._domain_service.generate_spec_document(spec)
        await self._repo.save(spec)
        return spec.to_dict()

    async def confirm_spec(self, spec_id: str) -> dict[str, Any] | None:
        existing = await self._repo.find_by_id(spec_id)
        if existing is None:
            return None
        spec = AircraftSpec(
            spec_id=existing["id"],
            aircraft_type=existing["aircraft_type"],
            payload_kg=existing["payload_kg"],
            range_km=existing["range_km"],
            cruise_speed_kmh=existing["cruise_speed_kmh"],
            takeoff_distance_m=existing["takeoff_distance_m"],
            power_type=existing["power_type"],
            budget_cny=existing["budget_cny"],
            material_id=existing["material_id"],
            certification_level_id=existing["certification_level_id"],
            created_by=existing["created_by"],
        )
        spec.spec_code = existing["spec_code"]
        spec.status = existing["status"]
        spec.confirm()
        await self._repo.save(spec)
        return {"spec": spec.to_dict(), "events": [e.to_dict() for e in spec.domain_events]}

    async def validate_spec(self, spec_id: str) -> dict[str, Any] | None:
        existing = await self._repo.find_by_id(spec_id)
        if existing is None:
            return None
        violations = self._domain_service.validate_parameters(existing)
        return {"valid": len(violations) == 0, "violations": violations}