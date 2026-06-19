"""AeroForge-X v5.0 AeroGPTDesignerService

AI design assistant that provides generative design suggestions based on
historical design library and physical constraints, with traceable reasoning.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from .requirement_parser_service import DesignRequirement, FeasibilityStatus
from .parametric_geometry_service import (
    DesignParameters,
    ParametricGeometryService,
    AircraftGeometry,
)


@dataclass(frozen=True)
class DesignSuggestion:
    suggestion_id: str
    requirement_id: str
    configuration: dict
    compliance_score: float
    satisfied_constraints: list[str]
    violated_constraints: list[str]
    reasoning: list[str]
    source_designs: list[str]


@dataclass
class AircraftConfiguration:
    configuration_id: str
    geometry: Optional[AircraftGeometry]
    structure_params: dict
    propulsion_params: dict
    control_params: dict
    overall_score: float = 0.0
    geometry_id: Optional[str] = None
    requirement_id: Optional[str] = None
    suggestion_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "configuration_id": self.configuration_id,
            "geometry_id": self.geometry_id,
            "requirement_id": self.requirement_id,
            "structure_params": self.structure_params,
            "propulsion_params": self.propulsion_params,
            "control_params": self.control_params,
            "overall_score": self.overall_score,
        }


@dataclass(frozen=True)
class ExplanationResult:
    suggestion_id: str
    satisfied_constraints: list[str]
    violated_constraints: list[str]
    reasoning: list[str]
    source_design_references: list[str]


_HISTORICAL_DESIGNS: list[dict] = [
    {
        "design_id": "HD-001",
        "range_km": 3000,
        "payload_kg": 5000,
        "cruise_speed_kmh": 900,
        "ceiling_m": 12000,
        "wing_span": 28.0,
        "wing_area": 80.0,
        "wing_aspect_ratio": 9.8,
        "wing_sweep_angle": 25.0,
        "wing_taper_ratio": 0.3,
        "fuselage_length": 35.0,
        "fuselage_diameter": 3.5,
        "engine_count": 2,
        "engine_thrust": 28000.0,
    },
    {
        "design_id": "HD-002",
        "range_km": 5500,
        "payload_kg": 8000,
        "cruise_speed_kmh": 850,
        "ceiling_m": 11000,
        "wing_span": 34.0,
        "wing_area": 120.0,
        "wing_aspect_ratio": 9.6,
        "wing_sweep_angle": 28.0,
        "wing_taper_ratio": 0.28,
        "fuselage_length": 42.0,
        "fuselage_diameter": 4.0,
        "engine_count": 2,
        "engine_thrust": 45000.0,
    },
    {
        "design_id": "HD-003",
        "range_km": 1500,
        "payload_kg": 2000,
        "cruise_speed_kmh": 600,
        "ceiling_m": 8000,
        "wing_span": 16.0,
        "wing_area": 30.0,
        "wing_aspect_ratio": 8.5,
        "wing_sweep_angle": 5.0,
        "wing_taper_ratio": 0.45,
        "fuselage_length": 14.0,
        "fuselage_diameter": 1.8,
        "engine_count": 2,
        "engine_thrust": 8000.0,
    },
    {
        "design_id": "HD-004",
        "range_km": 10000,
        "payload_kg": 15000,
        "cruise_speed_kmh": 920,
        "ceiling_m": 13000,
        "wing_span": 60.0,
        "wing_area": 360.0,
        "wing_aspect_ratio": 10.0,
        "wing_sweep_angle": 35.0,
        "wing_taper_ratio": 0.25,
        "fuselage_length": 65.0,
        "fuselage_diameter": 6.2,
        "engine_count": 4,
        "engine_thrust": 80000.0,
    },
]


class AeroGPTDesignerService:

    def __init__(self, geometry_service: ParametricGeometryService | None = None) -> None:
        self._geometry_service = geometry_service or ParametricGeometryService()
        self._suggestions: dict[str, DesignSuggestion] = {}
        self._configurations: dict[str, AircraftConfiguration] = {}
        self._historical = list(_HISTORICAL_DESIGNS)

    def suggest_designs(
        self,
        requirement: DesignRequirement,
        max_suggestions: int = 5,
    ) -> list[DesignSuggestion]:
        scored = []
        for design in self._historical:
            similarity = self._compute_similarity(requirement, design)
            scored.append((similarity, design))

        scored.sort(key=lambda x: x[0], reverse=True)

        suggestions = []
        for similarity, design in scored[:max_suggestions]:
            satisfied, violated, reasoning = self._evaluate_compliance(requirement, design)

            suggestion_id = f"DSG-{uuid.uuid4().hex[:8].upper()}"
            suggestion = DesignSuggestion(
                suggestion_id=suggestion_id,
                requirement_id=requirement.requirement_id,
                configuration=self._design_to_config(design),
                compliance_score=similarity,
                satisfied_constraints=satisfied,
                violated_constraints=violated,
                reasoning=reasoning,
                source_designs=[design["design_id"]],
            )
            self._suggestions[suggestion_id] = suggestion
            suggestions.append(suggestion)

        return suggestions

    def evaluate_alternatives(
        self,
        suggestions: list[DesignSuggestion],
    ) -> list[DesignSuggestion]:
        scored = []
        for s in suggestions:
            score = s.compliance_score
            score -= len(s.violated_constraints) * 0.1
            score += len(s.satisfied_constraints) * 0.05
            scored.append((score, s))

        scored.sort(key=lambda x: x[0], reverse=True)

        result = []
        for rank, (score, s) in enumerate(scored):
            updated = DesignSuggestion(
                suggestion_id=s.suggestion_id,
                requirement_id=s.requirement_id,
                configuration=s.configuration,
                compliance_score=score,
                satisfied_constraints=s.satisfied_constraints,
                violated_constraints=s.violated_constraints,
                reasoning=s.reasoning,
                source_designs=s.source_designs,
            )
            result.append(updated)

        return result

    def explain_suggestion(self, suggestion_id: str) -> Optional[ExplanationResult]:
        suggestion = self._suggestions.get(suggestion_id)
        if suggestion is None:
            return None

        return ExplanationResult(
            suggestion_id=suggestion_id,
            satisfied_constraints=suggestion.satisfied_constraints,
            violated_constraints=suggestion.violated_constraints,
            reasoning=suggestion.reasoning,
            source_design_references=suggestion.source_designs,
        )

    def instantiate_design(self, suggestion_id: str) -> Optional[AircraftConfiguration]:
        suggestion = self._suggestions.get(suggestion_id)
        if suggestion is None:
            return None

        config = suggestion.configuration
        params = DesignParameters(
            wing_span=config.get("wing_span", 20.0),
            wing_area=config.get("wing_area", 50.0),
            wing_aspect_ratio=config.get("wing_aspect_ratio", 9.0),
            wing_sweep_angle=config.get("wing_sweep_angle", 25.0),
            wing_taper_ratio=config.get("wing_taper_ratio", 0.3),
            fuselage_length=config.get("fuselage_length", 30.0),
            fuselage_diameter=config.get("fuselage_diameter", 3.0),
            horizontal_tail_area=config.get("horizontal_tail_area"),
            vertical_tail_area=config.get("vertical_tail_area"),
            engine_count=int(config.get("engine_count", 2)),
            engine_thrust=config.get("engine_thrust", 25000.0),
        )

        geometry = self._geometry_service.generate_geometry(
            parameters=params,
            requirement_id=suggestion.requirement_id,
        )

        configuration = AircraftConfiguration(
            configuration_id=f"CFG-{uuid.uuid4().hex[:8].upper()}",
            geometry=geometry,
            geometry_id=geometry.geometry_id,
            structure_params={
                "wing_weight_kg": config.get("wing_area", 50) * 15,
                "fuselage_weight_kg": config.get("fuselage_length", 30) * 200,
            },
            propulsion_params={
                "engine_count": config.get("engine_count", 2),
                "engine_thrust": config.get("engine_thrust", 25000.0),
                "total_thrust_N": config.get("engine_thrust", 25000.0) * config.get("engine_count", 2),
            },
            control_params={
                "horizontal_tail_area": config.get("horizontal_tail_area", 10.0),
                "vertical_tail_area": config.get("vertical_tail_area", 8.0),
            },
            overall_score=suggestion.compliance_score,
            requirement_id=suggestion.requirement_id,
            suggestion_id=suggestion_id,
        )

        self._configurations[configuration.configuration_id] = configuration
        return configuration

    def iterate_design(
        self,
        configuration_id: str,
        modifications: dict,
    ) -> Optional[AircraftConfiguration]:
        existing = self._configurations.get(configuration_id)
        if existing is None:
            return None

        new_structure = {**existing.structure_params, **modifications.get("structure_params", {})}
        new_propulsion = {**existing.propulsion_params, **modifications.get("propulsion_params", {})}
        new_control = {**existing.control_params, **modifications.get("control_params", {})}

        new_geometry = existing.geometry
        if "geometry" in modifications:
            geo_mods = modifications["geometry"]
            if existing.geometry is not None:
                old_params = existing.geometry.parameters
                new_params = DesignParameters(
                    wing_span=geo_mods.get("wing_span", old_params.wing_span),
                    wing_area=geo_mods.get("wing_area", old_params.wing_area),
                    wing_aspect_ratio=geo_mods.get("wing_aspect_ratio", old_params.wing_aspect_ratio),
                    wing_sweep_angle=geo_mods.get("wing_sweep_angle", old_params.wing_sweep_angle),
                    wing_taper_ratio=geo_mods.get("wing_taper_ratio", old_params.wing_taper_ratio),
                    fuselage_length=geo_mods.get("fuselage_length", old_params.fuselage_length),
                    fuselage_diameter=geo_mods.get("fuselage_diameter", old_params.fuselage_diameter),
                    horizontal_tail_area=geo_mods.get("horizontal_tail_area", old_params.horizontal_tail_area),
                    vertical_tail_area=geo_mods.get("vertical_tail_area", old_params.vertical_tail_area),
                    engine_count=int(geo_mods.get("engine_count", old_params.engine_count)),
                    engine_thrust=geo_mods.get("engine_thrust", old_params.engine_thrust),
                )
                new_geometry = self._geometry_service.regenerate_geometry(
                    existing.geometry.geometry_id,
                    new_params,
                )

        updated = AircraftConfiguration(
            configuration_id=configuration_id,
            geometry=new_geometry,
            geometry_id=new_geometry.geometry_id if new_geometry else existing.geometry_id,
            structure_params=new_structure,
            propulsion_params=new_propulsion,
            control_params=new_control,
            overall_score=existing.overall_score * 0.95,
            requirement_id=existing.requirement_id,
            suggestion_id=existing.suggestion_id,
        )

        self._configurations[configuration_id] = updated
        return updated

    def get_configuration(self, configuration_id: str) -> Optional[AircraftConfiguration]:
        return self._configurations.get(configuration_id)

    def _compute_similarity(self, requirement: DesignRequirement, design: dict) -> float:
        score = 0.0
        total_weight = 0.0

        if requirement.range_km is not None and "range_km" in design:
            diff = abs(requirement.range_km - design["range_km"]) / max(requirement.range_km, 1)
            score += max(0, 1.0 - diff)
            total_weight += 1.0

        if requirement.payload_kg is not None and "payload_kg" in design:
            diff = abs(requirement.payload_kg - design["payload_kg"]) / max(requirement.payload_kg, 1)
            score += max(0, 1.0 - diff)
            total_weight += 1.0

        if requirement.cruise_speed_kmh is not None and "cruise_speed_kmh" in design:
            diff = abs(requirement.cruise_speed_kmh - design["cruise_speed_kmh"]) / max(requirement.cruise_speed_kmh, 1)
            score += max(0, 1.0 - diff)
            total_weight += 1.0

        if requirement.ceiling_m is not None and "ceiling_m" in design:
            diff = abs(requirement.ceiling_m - design["ceiling_m"]) / max(requirement.ceiling_m, 1)
            score += max(0, 1.0 - diff)
            total_weight += 1.0

        return score / total_weight if total_weight > 0 else 0.0

    def _evaluate_compliance(
        self,
        requirement: DesignRequirement,
        design: dict,
    ) -> tuple[list[str], list[str], list[str]]:
        satisfied: list[str] = []
        violated: list[str] = []
        reasoning: list[str] = []

        if requirement.range_km is not None and "range_km" in design:
            if design["range_km"] >= requirement.range_km * 0.9:
                satisfied.append("range_km")
                reasoning.append(f"Design range {design['range_km']}km meets requirement {requirement.range_km}km")
            else:
                violated.append("range_km")
                reasoning.append(f"Design range {design['range_km']}km below requirement {requirement.range_km}km")

        if requirement.payload_kg is not None and "payload_kg" in design:
            if design["payload_kg"] >= requirement.payload_kg * 0.9:
                satisfied.append("payload_kg")
                reasoning.append(f"Design payload {design['payload_kg']}kg meets requirement {requirement.payload_kg}kg")
            else:
                violated.append("payload_kg")
                reasoning.append(f"Design payload {design['payload_kg']}kg below requirement {requirement.payload_kg}kg")

        if requirement.cruise_speed_kmh is not None and "cruise_speed_kmh" in design:
            if abs(design["cruise_speed_kmh"] - requirement.cruise_speed_kmh) / requirement.cruise_speed_kmh < 0.15:
                satisfied.append("cruise_speed_kmh")
            else:
                violated.append("cruise_speed_kmh")

        if requirement.ceiling_m is not None and "ceiling_m" in design:
            if design["ceiling_m"] >= requirement.ceiling_m * 0.85:
                satisfied.append("ceiling_m")
            else:
                violated.append("ceiling_m")

        return satisfied, violated, reasoning

    def _design_to_config(self, design: dict) -> dict:
        return {
            "wing_span": design.get("wing_span", 20.0),
            "wing_area": design.get("wing_area", 50.0),
            "wing_aspect_ratio": design.get("wing_aspect_ratio", 9.0),
            "wing_sweep_angle": design.get("wing_sweep_angle", 25.0),
            "wing_taper_ratio": design.get("wing_taper_ratio", 0.3),
            "fuselage_length": design.get("fuselage_length", 30.0),
            "fuselage_diameter": design.get("fuselage_diameter", 3.0),
            "engine_count": design.get("engine_count", 2),
            "engine_thrust": design.get("engine_thrust", 25000.0),
        }