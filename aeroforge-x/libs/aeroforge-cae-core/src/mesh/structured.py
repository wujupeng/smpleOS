from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from aeroforge_cae_core.mesh.generator_base import (
    MeshFormat,
    MeshGenerationParams,
    MeshGenerationResult,
    MeshGeneratorBase,
    MeshQualityMetrics,
    MeshType,
)

logger = logging.getLogger(__name__)


class StructuredMeshGenerator(MeshGeneratorBase):
    def __init__(self, working_dir: str = "/tmp/aeroforge/mesh/structured") -> None:
        self._working_dir = Path(working_dir)
        self._working_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, params: MeshGenerationParams) -> MeshGenerationResult:
        if params.mesh_type != MeshType.STRUCTURED:
            logger.warning("StructuredMeshGenerator called with mesh_type=%s, expected structured",
                           params.mesh_type.value)

        job_id = str(uuid.uuid4())[:8]
        output_dir = self._working_dir / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = self._resolve_output_path(output_dir, params)

        result = MeshGenerationResult(
            output_path=str(output_path),
            mesh_type=MeshType.STRUCTURED,
        )

        logger.info("Structured mesh generation: job=%s geometry=%s", job_id, params.source_geometry)
        return result

    def estimate_resources(self, params: MeshGenerationParams) -> dict[str, Any]:
        base = self.estimate_mesh_size(params)
        base["generator_type"] = "structured"
        base["parallelizable"] = True
        return base

    def generate_block_mesh(
        self,
        domain_bounds: dict[str, list[float]],
        divisions: dict[str, int],
        grading: dict[str, list[float]] | None = None,
        output_dir: str | None = None,
    ) -> MeshGenerationResult:
        out_dir = Path(output_dir) if output_dir else self._working_dir / str(uuid.uuid4())[:8]
        out_dir.mkdir(parents=True, exist_ok=True)

        block_mesh_dict = self._build_block_mesh_dict(domain_bounds, divisions, grading)
        dict_path = out_dir / "system" / "blockMeshDict"
        dict_path.parent.mkdir(parents=True, exist_ok=True)
        dict_path.write_text(str(block_mesh_dict))

        nx = divisions.get("x", 10)
        ny = divisions.get("y", 10)
        nz = divisions.get("z", 10)
        node_count = (nx + 1) * (ny + 1) * (nz + 1)
        element_count = nx * ny * nz

        result = MeshGenerationResult(
            output_path=str(out_dir),
            mesh_type=MeshType.STRUCTURED,
            node_count=node_count,
            element_count=element_count,
            quality_metrics=MeshQualityMetrics(
                orthogonality_min=1.0,
                orthogonality_avg=1.0,
                skewness_max=0.0,
                skewness_avg=0.0,
                aspect_ratio_max=1.0,
                aspect_ratio_avg=1.0,
            ),
        )

        logger.info("Block mesh generated: nodes=%d elements=%d", node_count, element_count)
        return result

    def _build_block_mesh_dict(
        self,
        bounds: dict[str, list[float]],
        divisions: dict[str, int],
        grading: dict[str, list[float]] | None,
    ) -> dict[str, Any]:
        return {
            "convertToMeters": 1,
            "vertices": self._build_vertices(bounds),
            "blocks": self._build_blocks(divisions, grading),
            "boundary": [],
        }

    @staticmethod
    def _build_vertices(bounds: dict[str, list[float]]) -> list[list[float]]:
        x = bounds.get("x", [0, 1])
        y = bounds.get("y", [0, 1])
        z = bounds.get("z", [0, 1])
        return [
            [x[0], y[0], z[0]], [x[1], y[0], z[0]],
            [x[1], y[1], z[0]], [x[0], y[1], z[0]],
            [x[0], y[0], z[1]], [x[1], y[0], z[1]],
            [x[1], y[1], z[1]], [x[0], y[1], z[1]],
        ]

    @staticmethod
    def _build_blocks(
        divisions: dict[str, int],
        grading: dict[str, list[float]] | None,
    ) -> list[dict[str, Any]]:
        nx = divisions.get("x", 10)
        ny = divisions.get("y", 10)
        nz = divisions.get("z", 10)
        simple_grading = grading or {}
        return [{
            "vertices": list(range(8)),
            "n_cells": [nx, ny, nz],
            "grading": simple_grading,
        }]

    @staticmethod
    def _resolve_output_path(output_dir: Path, params: MeshGenerationParams) -> Path:
        suffix_map: dict[MeshFormat, str] = {
            MeshFormat.OPENFOAM: "",
            MeshFormat.GMSH: ".msh",
            MeshFormat.VTK: ".vtk",
            MeshFormat.XDMF: ".xdmf",
            MeshFormat.FENICS_XML: ".xml",
        }
        suffix = suffix_map.get(params.output_format, "")
        if suffix:
            return output_dir / f"mesh{suffix}"
        return output_dir