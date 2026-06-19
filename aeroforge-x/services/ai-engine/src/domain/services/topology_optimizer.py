from __future__ import annotations

import logging
import math
import random
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from .entities.topology_task import (
    TopologyOptimizationTask, TopologyMethod, TopologyStatus,
    LoadCase, LoadCaseType, BoundaryCondition, DesignRegion, TopologyResult,
)

logger = logging.getLogger(__name__)

BUILTIN_LOAD_CASES: dict[str, LoadCase] = {
    "wing_bending": LoadCase(
        name="wing_bending", load_case_type=LoadCaseType.BENDING,
        force_z=-5000.0, description="机翼弯曲载荷",
    ),
    "wing_torsion": LoadCase(
        name="wing_torsion", load_case_type=LoadCaseType.TORSION,
        moment_x=2000.0, description="机翼扭转载荷",
    ),
    "fuselage_compression": LoadCase(
        name="fuselage_compression", load_case_type=LoadCaseType.COMPRESSION,
        force_x=-10000.0, description="机身压缩载荷",
    ),
    "landing_impact": LoadCase(
        name="landing_impact", load_case_type=LoadCaseType.COMBINED,
        force_z=-15000.0, force_x=3000.0, description="着陆冲击载荷",
    ),
    "gust_load": LoadCase(
        name="gust_load", load_case_type=LoadCaseType.BENDING,
        force_z=-8000.0, moment_y=1500.0, description="阵风载荷",
    ),
}

BUILTIN_BOUNDARY_CONDITIONS: dict[str, BoundaryCondition] = {
    "wing_root_fixed": BoundaryCondition(
        name="wing_root_fixed", constrained_dofs=["x", "y", "z", "rx", "ry"],
        region="wing_root", description="机翼根部固定",
    ),
    "fuselage_support": BoundaryCondition(
        name="fuselage_support", constrained_dofs=["y", "z"],
        region="fuselage_frame", description="机身支撑点",
    ),
    "symmetry_plane": BoundaryCondition(
        name="symmetry_plane", constrained_dofs=["x"],
        region="symmetry", description="对称面约束",
    ),
}

BUILTIN_DESIGN_REGIONS: dict[str, DesignRegion] = {
    "wing_box": DesignRegion(
        name="wing_box", volume_fraction=0.3, min_member_size=3.0,
        mesh_element_size=2.0, material_id="aluminum_7075",
    ),
    "fuselage_frame": DesignRegion(
        name="fuselage_frame", volume_fraction=0.25, min_member_size=2.5,
        mesh_element_size=1.5, material_id="aluminum_6061",
    ),
    "rib_structure": DesignRegion(
        name="rib_structure", volume_fraction=0.35, min_member_size=1.5,
        mesh_element_size=1.0, material_id="composite_cf",
    ),
    "landing_gear_mount": DesignRegion(
        name="landing_gear_mount", volume_fraction=0.4, min_member_size=4.0,
        mesh_element_size=2.5, material_id="steel_4340",
    ),
}


class TopologyOptimizer:
    def __init__(self) -> None:
        self._tasks: dict[str, TopologyOptimizationTask] = {}

    def create_topology_task(
        self,
        project_id: str,
        tenant_id: str,
        design_region_names: list[str],
        load_case_names: list[str],
        boundary_condition_names: list[str],
        method: TopologyMethod = TopologyMethod.SIMP,
        max_iterations: int = 50,
        convergence_tolerance: float = 1e-4,
        penalty_factor: float = 3.0,
        filter_radius: float = 1.5,
    ) -> TopologyOptimizationTask:
        design_regions = [BUILTIN_DESIGN_REGIONS[n] for n in design_region_names if n in BUILTIN_DESIGN_REGIONS]
        if not design_regions:
            design_regions = [BUILTIN_DESIGN_REGIONS["wing_box"]]

        load_cases = [BUILTIN_LOAD_CASES[n] for n in load_case_names if n in BUILTIN_LOAD_CASES]
        if not load_cases:
            load_cases = [BUILTIN_LOAD_CASES["wing_bending"]]

        boundary_conditions = [BUILTIN_BOUNDARY_CONDITIONS[n] for n in boundary_condition_names if n in BUILTIN_BOUNDARY_CONDITIONS]
        if not boundary_conditions:
            boundary_conditions = [BUILTIN_BOUNDARY_CONDITIONS["wing_root_fixed"]]

        task = TopologyOptimizationTask(
            project_id=project_id,
            tenant_id=tenant_id,
            method=method,
            design_regions=design_regions,
            load_cases=load_cases,
            boundary_conditions=boundary_conditions,
            max_iterations=max_iterations,
            convergence_tolerance=convergence_tolerance,
            penalty_factor=penalty_factor,
            filter_radius=filter_radius,
        )

        self._tasks[task.id] = task

        task.add_domain_event(DomainEvent(
            event_type="topology_optimization.queued",
            aggregate_id=task.id,
            payload={"task_id": task.id, "method": method.value},
        ))

        logger.info("Created topology optimization task %s with method %s", task.id, method.value)
        return task

    def run_topology_optimization(self, task_id: str) -> TopologyOptimizationTask | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None

        try:
            task.start_meshing()
            element_count = self._generate_mesh(task)

            task.start_optimization()
            result = self._run_simp(task, element_count)

            task.start_post_processing()
            self._post_process(result)

            task.complete(result)
            logger.info("Topology optimization task %s completed, mass reduction: %.1f%%",
                        task_id, result.mass_reduction_pct)
        except Exception as e:
            task.fail(str(e))
            logger.error("Topology optimization task %s failed: %s", task_id, e)

        return task

    def get_task(self, task_id: str) -> TopologyOptimizationTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self, project_id: str | None = None) -> list[TopologyOptimizationTask]:
        tasks = list(self._tasks.values())
        if project_id:
            tasks = [t for t in tasks if t.project_id == project_id]
        return tasks

    def _generate_mesh(self, task: TopologyOptimizationTask) -> int:
        total_elements = 0
        for region in task.design_regions:
            region_volume = 100.0
            element_volume = task.filter_radius ** 3
            n_elements = int(region_volume / max(element_volume, 0.01))
            total_elements += max(n_elements, 100)
        return total_elements

    def _run_simp(self, task: TopologyOptimizationTask, element_count: int) -> TopologyResult:
        density = [1.0] * element_count
        target_fraction = task.design_regions[0].volume_fraction if task.design_regions else 0.3

        compliance_prev = 0.0
        converged = False

        for iteration in range(task.max_iterations):
            compliance = self._compute_compliance(density, task)
            stress = self._compute_stress(density, task)

            sensitivity = self._compute_sensitivity(density, compliance, task)

            density = self._update_density(density, sensitivity, target_fraction, task.penalty_factor)

            density = self._apply_filter(density, task.filter_radius)

            current_fraction = sum(1 for d in density if d > 0.5) / max(len(density), 1)

            if iteration > 0 and abs(compliance - compliance_prev) < task.convergence_tolerance:
                converged = True

            compliance_prev = compliance

            task.iteration_history.append({
                "iteration": iteration + 1,
                "compliance": round(compliance, 4),
                "volume_fraction": round(current_fraction, 4),
                "max_stress": round(max(stress), 2),
                "converged": converged,
            })

            if converged:
                break

        final_fraction = sum(1 for d in density if d > 0.5) / max(len(density), 1)
        mass_reduction = (1.0 - final_fraction) * 100.0

        return TopologyResult(
            iteration_count=len(task.iteration_history),
            final_volume_fraction=round(final_fraction, 4),
            compliance=round(compliance_prev, 4),
            max_stress=round(max(self._compute_stress(density, task)), 2),
            mass_reduction_pct=round(mass_reduction, 2),
            density_field=density[:1000],
            element_count=element_count,
            converged=converged,
        )

    def _compute_compliance(self, density: list[float], task: TopologyOptimizationTask) -> float:
        total_force = 0.0
        for lc in task.load_cases:
            total_force += math.sqrt(lc.force_x**2 + lc.force_y**2 + lc.force_z**2)
            total_force += abs(lc.moment_x) + abs(lc.moment_y) + abs(lc.moment_z)
            total_force += abs(lc.pressure) * 10

        active = sum(1 for d in density if d > 0.5)
        if active == 0:
            return total_force

        avg_density = sum(density) / max(len(density), 1)
        penalty = avg_density ** task.penalty_factor
        return total_force / max(penalty, 0.01)

    def _compute_stress(self, density: list[float], task: TopologyOptimizationTask) -> list[float]:
        total_force = 0.0
        for lc in task.load_cases:
            total_force += math.sqrt(lc.force_x**2 + lc.force_y**2 + lc.force_z**2)

        base_stress = total_force / max(len(density), 1) * 10
        return [base_stress / max(d ** task.penalty_factor, 0.01) for d in density[:100]]

    def _compute_sensitivity(self, density: list[float], compliance: float, task: TopologyOptimizationTask) -> list[float]:
        return [
            -task.penalty_factor * (d ** (task.penalty_factor - 1)) * compliance / max(d, 0.01)
            for d in density
        ]

    def _update_density(
        self, density: list[float], sensitivity: list[float],
        target_fraction: float, penalty: float,
    ) -> list[float]:
        sorted_density = sorted(density, reverse=True)
        threshold_idx = max(0, min(int(len(sorted_density) * target_fraction), len(sorted_density) - 1))
        threshold = sorted_density[threshold_idx]

        new_density = []
        for i, d in enumerate(density):
            if sensitivity[i] < 0:
                new_d = d + 0.1 * abs(sensitivity[i]) / max(abs(sensitivity[i]) + 1, 1)
            else:
                new_d = d - 0.05 * sensitivity[i] / max(sensitivity[i] + 1, 1)

            if d > threshold:
                new_d = min(new_d + 0.02, 1.0)
            else:
                new_d = max(new_d - 0.02, 0.01)

            new_density.append(max(0.01, min(1.0, new_d)))

        current_fraction = sum(1 for d in new_density if d > 0.5) / max(len(new_density), 1)
        if current_fraction > target_fraction + 0.05:
            new_density = [max(d - 0.01, 0.01) for d in new_density]
        elif current_fraction < target_fraction - 0.05:
            new_density = [min(d + 0.01, 1.0) for d in new_density]

        return new_density

    def _apply_filter(self, density: list[float], radius: float) -> list[float]:
        filtered = []
        filter_weight = 1.0 / (1.0 + radius * 0.1)
        for d in density:
            filtered_d = d * filter_weight + (1 - filter_weight) * 0.5
            filtered.append(max(0.01, min(1.0, filtered_d)))
        return filtered

    def _post_process(self, result: TopologyResult) -> None:
        pass