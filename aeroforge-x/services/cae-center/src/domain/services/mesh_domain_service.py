from __future__ import annotations

import logging
from typing import Any

from aeroforge_cae_core.mesh.generator_base import (
    MeshGenerationParams,
    MeshType as CoreMeshType,
)
from aeroforge_cae_core.mesh.structured import StructuredMeshGenerator
from aeroforge_cae_core.mesh.unstructured import UnstructuredMeshGenerator
from aeroforge_cae_core.mesh.quality import MeshQualityChecker, QualityThresholds

from .mesh_task import MeshTask, MeshType, MeshTaskStatus

logger = logging.getLogger(__name__)


class MeshDomainService:
    def __init__(
        self,
        working_dir: str = "/tmp/aeroforge/mesh",
    ) -> None:
        self._structured_gen = StructuredMeshGenerator(working_dir=f"{working_dir}/structured")
        self._unstructured_gen = UnstructuredMeshGenerator(working_dir=f"{working_dir}/unstructured")
        self._quality_checker = MeshQualityChecker()

    def generate_mesh(self, task: MeshTask, params: dict[str, Any] | None = None) -> MeshTask:
        task.start_meshing()

        try:
            gen_params = MeshGenerationParams(
                source_geometry=task.model_id,
                mesh_type=CoreMeshType(task.mesh_type.value),
                target_element_size=task.target_element_size,
                extra_params=params or {},
            )

            if task.mesh_type == MeshType.STRUCTURED:
                result = self._structured_gen.generate(gen_params)
            else:
                result = self._unstructured_gen.generate(gen_params)

            quality = None
            if result.quality_metrics is not None:
                from .mesh_task import MeshQualityMetrics
                quality = MeshQualityMetrics(
                    orthogonality_min=result.quality_metrics.orthogonality_min,
                    orthogonality_avg=result.quality_metrics.orthogonality_avg,
                    skewness_max=result.quality_metrics.skewness_max,
                    skewness_avg=result.quality_metrics.skewness_avg,
                    aspect_ratio_max=result.quality_metrics.aspect_ratio_max,
                    aspect_ratio_avg=result.quality_metrics.aspect_ratio_avg,
                )

            task.complete(
                element_count=result.element_count,
                node_count=result.node_count,
                output_path=result.output_path,
                quality=quality,
            )

        except Exception as exc:
            logger.error("Mesh generation failed for task %s: %s", task.id, exc)
            task.fail(str(exc))

        return task

    def validate_geometry(self, geometry_path: str) -> dict[str, Any]:
        result = self._structured_gen.validate_geometry(geometry_path)
        issues: list[str] = []
        if not result.get("valid", True):
            issues.append("Geometry validation failed")
        return {
            "valid": result.get("valid", True),
            "issues": issues,
            "file_size_mb": result.get("file_size_mb", 0.0),
        }

    def repair_geometry(self, geometry_path: str) -> dict[str, Any]:
        logger.info("Geometry repair requested for %s", geometry_path)
        return {
            "geometry_path": geometry_path,
            "repaired": True,
            "repairs_applied": [],
        }

    def estimate_mesh_size(self, task: MeshTask) -> dict[str, Any]:
        gen_params = MeshGenerationParams(
            source_geometry=task.model_id,
            mesh_type=CoreMeshType(task.mesh_type.value),
            target_element_size=task.target_element_size,
        )
        if task.mesh_type == MeshType.STRUCTURED:
            return self._structured_gen.estimate_mesh_size(gen_params)
        return self._unstructured_gen.estimate_mesh_size(gen_params)

    def check_mesh_quality(self, metrics: dict[str, Any]) -> dict[str, Any]:
        report = self._quality_checker.check_quality(metrics)
        return self._quality_checker.get_quality_summary(report)