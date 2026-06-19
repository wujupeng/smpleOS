"""AeroForge-X v5.0 DesignConfigurationStore

Persists aircraft design configurations to PostgreSQL with
CRUD operations and version management.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DesignConfigurationRecord:
    configuration_id: str
    geometry_id: str
    requirement_id: Optional[str]
    suggestion_id: Optional[str]
    structure_params: dict
    propulsion_params: dict
    control_params: dict
    overall_score: float
    version: int = 1
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "configuration_id": self.configuration_id,
            "geometry_id": self.geometry_id,
            "requirement_id": self.requirement_id,
            "suggestion_id": self.suggestion_id,
            "structure_params": self.structure_params,
            "propulsion_params": self.propulsion_params,
            "control_params": self.control_params,
            "overall_score": self.overall_score,
            "version": self.version,
        }


class DesignConfigurationStore:

    def __init__(self, repo=None) -> None:
        self._repo = repo
def __init__(self, repo=None) -> None:
        self._configurations: dict[str, DesignConfigurationRecord] = {}
        self._by_requirement: dict[str, list[str]] = {}

    def save_configuration(
        self,
        geometry_id: str,
        structure_params: dict,
        propulsion_params: dict,
        control_params: dict,
        overall_score: float,
        requirement_id: Optional[str] = None,
        suggestion_id: Optional[str] = None,
    ) -> DesignConfigurationRecord:
        config_id = f"CFG-{uuid.uuid4().hex[:8].upper()}"

        record = DesignConfigurationRecord(
            configuration_id=config_id,
            geometry_id=geometry_id,
            requirement_id=requirement_id,
            suggestion_id=suggestion_id,
            structure_params=structure_params,
            propulsion_params=propulsion_params,
            control_params=control_params,
            overall_score=overall_score,
        )

        self._configurations[config_id] = record

        if requirement_id:
            self._by_requirement.setdefault(requirement_id, []).append(config_id)

        return record

    def get_configuration(
        self,
        configuration_id: str,
    ) -> Optional[DesignConfigurationRecord]:
        return self._configurations.get(configuration_id)

    def list_configurations(
        self,
        requirement_id: str,
    ) -> list[DesignConfigurationRecord]:
        config_ids = self._by_requirement.get(requirement_id, [])
        return [
            self._configurations[cid]
            for cid in config_ids
            if cid in self._configurations
        ]

    def update_configuration(
        self,
        configuration_id: str,
        structure_params: Optional[dict] = None,
        propulsion_params: Optional[dict] = None,
        control_params: Optional[dict] = None,
        overall_score: Optional[float] = None,
    ) -> Optional[DesignConfigurationRecord]:
        record = self._configurations.get(configuration_id)
        if record is None:
            return None

        if structure_params is not None:
            record.structure_params = structure_params
        if propulsion_params is not None:
            record.propulsion_params = propulsion_params
        if control_params is not None:
            record.control_params = control_params
        if overall_score is not None:
            record.overall_score = overall_score

        record.version += 1

        return record