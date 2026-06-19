from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TopologyOptimizationResult:
    def __init__(self, result_id: str, component_type: str):
        self.result_id = result_id
        self.component_type = component_type
        self.load_conditions: dict[str, Any] = {}
        self.material_constraints: dict[str, Any] = {}
        self.optimized_material_distribution: dict[str, Any] = {}
        self.weight_reduction_percentage: float = 0.0
        self.stress_distribution: dict[str, Any] = {}
        self.iteration_count: int = 0
        self.convergence_achieved: bool = False
        self.model_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "component_type": self.component_type,
            "load_conditions": self.load_conditions,
            "material_constraints": self.material_constraints,
            "optimized_material_distribution": self.optimized_material_distribution,
            "weight_reduction_percentage": round(self.weight_reduction_percentage, 2),
            "stress_distribution": self.stress_distribution,
            "iteration_count": self.iteration_count,
            "convergence_achieved": self.convergence_achieved,
            "model_ref": self.model_ref,
        }


class TopologyOptimization:
    def __init__(self, event_publisher: Any | None = None):
        self._event_publisher = event_publisher
        self._results: dict[str, TopologyOptimizationResult] = {}

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    def optimize_topology(self, component_type: str, load_conditions: dict[str, Any], material_constraints: dict[str, Any], volume_fraction: float = 0.3, max_iterations: int = 50) -> TopologyOptimizationResult:
        result = TopologyOptimizationResult(result_id=str(uuid4()), component_type=component_type)
        result.load_conditions = load_conditions
        result.material_constraints = material_constraints

        mesh_resolution = self._get_mesh_resolution(component_type)
        density = self._initialize_density(mesh_resolution, volume_fraction)

        yield_stress = material_constraints.get("yield_stress_mpa", 400.0)
        density_material = material_constraints.get("density_kg_m3", 2700.0)
        penalty_factor = 3.0

        loads = load_conditions.get("loads", [])
        max_load = max((l.get("magnitude", 0) for l in loads), default=100.0)

        for iteration in range(max_iterations):
            compliance = 0.0
            max_stress = 0.0
            new_density = [[0.0] * mesh_resolution for _ in range(mesh_resolution)]

            for i in range(mesh_resolution):
                for j in range(mesh_resolution):
                    effective_stiffness = density[i][j] ** penalty_factor
                    local_stress = max_load * effective_stiffness / max(yield_stress, 1.0)
                    max_stress = max(max_stress, local_stress)
                    compliance += local_stress * density[i][j]

                    if local_stress > yield_stress * 0.8:
                        new_density[i][j] = min(density[i][j] * 1.1, 1.0)
                    elif local_stress < yield_stress * 0.3 and density[i][j] > 0.05:
                        new_density[i][j] = density[i][j] * 0.9
                    else:
                        new_density[i][j] = density[i][j]

            total_material = sum(sum(row) for row in new_density)
            target_material = mesh_resolution * mesh_resolution * volume_fraction
            if total_material > 0:
                scale = target_material / total_material
                for i in range(mesh_resolution):
                    for j in range(mesh_resolution):
                        new_density[i][j] = max(0.01, min(1.0, new_density[i][j] * scale))

            density = new_density

            if iteration > 10 and abs(max_stress - yield_stress * 0.7) / max(yield_stress, 1.0) < 0.05:
                result.convergence_achieved = True
                result.iteration_count = iteration + 1
                break
        else:
            result.iteration_count = max_iterations

        result.optimized_material_distribution = {
            "mesh_resolution": mesh_resolution,
            "volume_fraction": volume_fraction,
            "density_field": density,
            "component_type": component_type,
        }

        original_volume = mesh_resolution * mesh_resolution * 1.0
        optimized_volume = sum(sum(row) for row in density)
        result.weight_reduction_percentage = max(0, (1.0 - optimized_volume / original_volume) * 100)

        result.stress_distribution = {
            "max_stress_mpa": max_stress,
            "yield_stress_mpa": yield_stress,
            "safety_factor": yield_stress / max_stress if max_stress > 0 else float('inf'),
            "compliance": compliance,
        }

        result.model_ref = f"topo_opt_{component_type}_{result.result_id[:8]}"

        self._results[result.result_id] = result
        return result

    def _get_mesh_resolution(self, component_type: str) -> int:
        resolutions = {
            "wing_spar": 20,
            "wing_rib": 15,
            "fuselage_frame": 12,
            "center_wing_box": 18,
            "bracket": 10,
        }
        return resolutions.get(component_type, 15)

    def _initialize_density(self, resolution: int, volume_fraction: float) -> list[list[float]]:
        import random
        density = []
        for i in range(resolution):
            row = []
            for j in range(resolution):
                dist_from_center = ((i - resolution / 2) ** 2 + (j - resolution / 2) ** 2) ** 0.5
                max_dist = resolution / 2
                base = volume_fraction
                if dist_from_center < max_dist * 0.3:
                    base = min(1.0, volume_fraction * 2.0)
                elif dist_from_center > max_dist * 0.8:
                    base = max(0.01, volume_fraction * 0.3)
                row.append(base + random.uniform(-0.05, 0.05))
            density.append(row)
        return density

    def get_result(self, result_id: str) -> TopologyOptimizationResult | None:
        return self._results.get(result_id)