from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from src.domain.entities.ai_proposal import AIProposal, ProposalStatus, RiskMarker, RiskSeverity

logger = logging.getLogger(__name__)


class StructureComponent:
    def __init__(self, component_id: str, component_type: str, name: str, parameters: dict[str, Any], material: str = "aluminum_7075"):
        self.component_id = component_id
        self.component_type = component_type
        self.name = name
        self.parameters = parameters
        self.material = material
        self.interferences: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type,
            "name": self.name,
            "parameters": self.parameters,
            "material": self.material,
            "interferences": self.interferences,
        }


class StructureResult:
    def __init__(self, result_id: str, proposal_id: str):
        self.result_id = result_id
        self.proposal_id = proposal_id
        self.components: list[StructureComponent] = []
        self.interferences: list[dict[str, Any]] = []
        self.parameter_links: dict[str, list[str]] = {}
        self.baseline_frozen_violations: list[str] = []
        self.status: str = "generated"

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "proposal_id": self.proposal_id,
            "components": [c.to_dict() for c in self.components],
            "interferences": self.interferences,
            "parameter_links": self.parameter_links,
            "baseline_frozen_violations": self.baseline_frozen_violations,
            "status": self.status,
        }


class AeroGPTEngineer:
    def __init__(self, event_publisher: Any | None = None):
        self._event_publisher = event_publisher
        self._results: dict[str, StructureResult] = {}
        self._frozen_baselines: set[str] = set()

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    def freeze_baseline(self, proposal_id: str) -> None:
        self._frozen_baselines.add(proposal_id)

    def unfreeze_baseline(self, proposal_id: str) -> None:
        self._frozen_baselines.discard(proposal_id)

    def generate_structure(self, proposal_id: str, spec: dict[str, Any]) -> StructureResult:
        if proposal_id in self._frozen_baselines:
            result = StructureResult(str(uuid4()), proposal_id)
            result.baseline_frozen_violations.append(
                f"Proposal {proposal_id} has a frozen baseline. Submit an ECR to modify."
            )
            result.status = "blocked"
            self._results[result.result_id] = result
            return result

        result = StructureResult(str(uuid4()), proposal_id)
        wingspan = spec.get("wingspan_m", 35.8)
        fuselage_length = spec.get("fuselage_length_m", 40.0)
        mtow = spec.get("mtow_kg", 80000)

        wing_spar = StructureComponent(
            component_id=f"COMP-{uuid4().hex[:8]}",
            component_type="wing_spar",
            name="Main Wing Spar",
            parameters={
                "length_m": wingspan * 0.45,
                "height_m": 0.35,
                "thickness_m": 0.02,
                "position": "25% chord",
                "load_capacity_kn": mtow * 9.81 * 2.5 / 1000,
            },
            material="composite_cfrp",
        )
        result.components.append(wing_spar)

        rib_count = max(int(wingspan / 0.6), 10)
        for i in range(rib_count):
            rib = StructureComponent(
                component_id=f"COMP-{uuid4().hex[:8]}",
                component_type="wing_rib",
                name=f"Wing Rib #{i + 1}",
                parameters={
                    "spanwise_position": (i / (rib_count - 1)) * wingspan * 0.45,
                    "chord_fraction": 1.0 - 0.3 * (i / (rib_count - 1)),
                    "height_m": 0.25 * (1.0 - 0.4 * i / rib_count),
                    "thickness_m": 0.003,
                },
                material="aluminum_7075",
            )
            result.components.append(rib)

        frame_count = max(int(fuselage_length / 0.5), 20)
        for i in range(frame_count):
            frame = StructureComponent(
                component_id=f"COMP-{uuid4().hex[:8]}",
                component_type="fuselage_frame",
                name=f"Fuselage Frame #{i + 1}",
                parameters={
                    "station_m": i * 0.5,
                    "diameter_m": fuselage_length * 0.1,
                    "height_m": 0.12,
                    "thickness_m": 0.002,
                },
                material="aluminum_2024",
            )
            result.components.append(frame)

        center_wing_box = StructureComponent(
            component_id=f"COMP-{uuid4().hex[:8]}",
            component_type="center_wing_box",
            name="Center Wing Box",
            parameters={
                "width_m": fuselage_length * 0.1,
                "length_m": wingspan * 0.15,
                "height_m": 0.5,
                "thickness_m": 0.015,
            },
            material="composite_cfrp",
        )
        result.components.append(center_wing_box)

        result.parameter_links = {
            "wingspan_m": [wing_spar.component_id] + [r.component_id for r in result.components if r.component_type == "wing_rib"],
            "fuselage_length_m": [f.component_id for f in result.components if f.component_type == "fuselage_frame"] + [center_wing_box.component_id],
            "mtow_kg": [wing_spar.component_id],
        }

        self._detect_interferences(result)
        self._results[result.result_id] = result
        return result

    def optimize_structure(self, result_id: str, fea_results: dict[str, Any]) -> StructureResult:
        result = self._results.get(result_id)
        if not result:
            raise ValueError(f"Structure result {result_id} not found")

        if result.proposal_id in self._frozen_baselines:
            result.baseline_frozen_violations.append(
                f"Cannot auto-optimize: proposal {result.proposal_id} has a frozen baseline. Submit an ECR."
            )
            return result

        for component in result.components:
            stress_key = f"{component.component_id}_max_stress"
            if stress_key in fea_results:
                max_stress = fea_results[stress_key]
                yield_stress = self._get_yield_stress(component.material)
                safety_factor = yield_stress / max_stress if max_stress > 0 else 10.0

                if safety_factor > 2.0:
                    reduction = min(0.15, (safety_factor - 1.5) / safety_factor * 0.3)
                    if "thickness_m" in component.parameters:
                        component.parameters["thickness_m"] *= (1.0 - reduction)
                elif safety_factor < 1.5:
                    increase = min(0.2, (1.5 - safety_factor) / 1.5 * 0.3)
                    if "thickness_m" in component.parameters:
                        component.parameters["thickness_m"] *= (1.0 + increase)

        self._detect_interferences(result)
        result.status = "optimized"
        return result

    def _detect_interferences(self, result: StructureResult) -> None:
        result.interferences = []
        components = result.components
        for i in range(len(components)):
            for j in range(i + 1, len(components)):
                ci = components[i]
                cj = components[j]
                if ci.component_type == "wing_spar" and cj.component_type == "wing_rib":
                    continue
                if ci.component_type == "fuselage_frame" and cj.component_type == "center_wing_box":
                    ci_station = ci.parameters.get("station_m", 0)
                    cj_length = cj.parameters.get("length_m", 0)
                    cj_width = cj.parameters.get("width_m", 0)
                    if abs(ci_station - fuselage_length * 0.45) < cj_length / 2:
                        result.interferences.append({
                            "component_a": ci.component_id,
                            "component_b": cj.component_id,
                            "type": "spatial_overlap",
                            "description": f"Frame at station {ci_station:.1f}m overlaps with center wing box",
                            "auto_resolved": True,
                        })

    def _get_yield_stress(self, material: str) -> float:
        material_props = {
            "aluminum_7075": 503.0,
            "aluminum_2024": 345.0,
            "composite_cfrp": 600.0,
            "titanium_6al4v": 880.0,
        }
        return material_props.get(material, 400.0)

    def update_from_design_change(self, result_id: str, changed_params: dict[str, Any]) -> StructureResult:
        result = self._results.get(result_id)
        if not result:
            raise ValueError(f"Structure result {result_id} not found")

        if result.proposal_id in self._frozen_baselines:
            result.baseline_frozen_violations.append(
                f"Cannot auto-update: proposal {result.proposal_id} has a frozen baseline. Submit an ECR."
            )
            return result

        for param_name, new_value in changed_params.items():
            if param_name in result.parameter_links:
                for comp_id in result.parameter_links[param_name]:
                    for comp in result.components:
                        if comp.component_id == comp_id:
                            if param_name == "wingspan_m" and comp.component_type == "wing_spar":
                                comp.parameters["length_m"] = new_value * 0.45
                                comp.parameters["load_capacity_kn"] = changed_params.get("mtow_kg", 80000) * 9.81 * 2.5 / 1000
                            elif param_name == "fuselage_length_m" and comp.component_type == "fuselage_frame":
                                pass

        self._detect_interferences(result)
        result.status = "updated"
        return result

    def get_result(self, result_id: str) -> StructureResult | None:
        return self._results.get(result_id)