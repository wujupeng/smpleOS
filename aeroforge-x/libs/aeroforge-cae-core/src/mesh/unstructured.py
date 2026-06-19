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


class UnstructuredMeshGenerator(MeshGeneratorBase):
    def __init__(self, working_dir: str = "/tmp/aeroforge/mesh/unstructured") -> None:
        self._working_dir = Path(working_dir)
        self._working_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, params: MeshGenerationParams) -> MeshGenerationResult:
        if params.mesh_type != MeshType.UNSTRUCTURED:
            logger.warning(
                "UnstructuredMeshGenerator called with mesh_type=%s, expected unstructured",
                params.mesh_type.value,
            )

        job_id = str(uuid.uuid4())[:8]
        output_dir = self._working_dir / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = self._resolve_output_path(output_dir, params)

        result = MeshGenerationResult(
            output_path=str(output_path),
            mesh_type=MeshType.UNSTRUCTURED,
        )

        logger.info(
            "Unstructured mesh generation: job=%s geometry=%s element_size=%.4f",
            job_id, params.source_geometry, params.target_element_size,
        )
        return result

    def estimate_resources(self, params: MeshGenerationParams) -> dict[str, Any]:
        base = self.estimate_mesh_size(params)
        base["generator_type"] = "unstructured"
        base["parallelizable"] = True
        base["requires_surface_mesh"] = True
        return base

    def generate_snappy_hex_mesh(
        self,
        geometry_path: str,
        case_dir: str,
        params: dict[str, Any] | None = None,
        n_proc: int = 1,
    ) -> MeshGenerationResult:
        case_path = Path(case_dir)
        case_path.mkdir(parents=True, exist_ok=True)
        for subdir in ("system", "constant", "0"):
            (case_path / subdir).mkdir(parents=True, exist_ok=True)

        mesh_params = params or {}
        snappy_dict = self._build_snappy_hex_mesh_dict(geometry_path, mesh_params)
        dict_path = case_path / "system" / "snappyHexMeshDict"
        dict_path.parent.mkdir(parents=True, exist_ok=True)
        dict_path.write_text(str(snappy_dict))

        surface_dict = self._build_surface_transport_dict(geometry_path)
        surf_path = case_path / "system" / "surfaceTransportDict"
        surf_path.write_text(str(surface_dict))

        result = MeshGenerationResult(
            output_path=str(case_path),
            mesh_type=MeshType.UNSTRUCTURED,
        )

        logger.info("snappyHexMesh config generated at %s", dict_path)
        return result

    def generate_gmsh_mesh(
        self,
        geometry_path: str,
        output_dir: str,
        element_size: float = 0.01,
        algorithm: str = "Delaunay",
        params: dict[str, Any] | None = None,
    ) -> MeshGenerationResult:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        geo_path = Path(geometry_path)
        if not geo_path.exists():
            raise FileNotFoundError(f"Geometry file not found: {geometry_path}")

        output_file = out_path / f"{geo_path.stem}.msh"

        result = MeshGenerationResult(
            output_path=str(output_file),
            mesh_type=MeshType.UNSTRUCTURED,
        )

        logger.info(
            "GMSH mesh generation: geometry=%s algorithm=%s element_size=%.4f",
            geometry_path, algorithm, element_size,
        )
        return result

    def _build_snappy_hex_mesh_dict(
        self, geometry_path: str, params: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "castellatedMesh": True,
            "snap": True,
            "addLayers": params.get("add_layers", True),
            "geometry": {
                Path(geometry_path).stem: {
                    "type": "triSurfaceMesh",
                    "name": Path(geometry_path).stem,
                },
            },
            "castellatedMeshControls": {
                "maxLocalCells": params.get("max_local_cells", 1000000),
                "maxGlobalCells": params.get("max_global_cells", 5000000),
                "minRefinementCells": params.get("min_refinement_cells", 0),
                "nCellsBetweenLevels": params.get("n_cells_between_levels", 3),
                "features": [],
                "refinementSurfaces": {
                    Path(geometry_path).stem: {
                        "level": params.get("surface_refinement_level", [5, 6]),
                    },
                },
                "resolveFeatureAngle": params.get("resolve_feature_angle", 30),
                "refinementRegions": {},
                "locationInMesh": params.get("location_in_mesh", [0, 0, 0]),
            },
            "snapControls": {
                "nSmoothPatch": params.get("n_smooth_patch", 3),
                "tolerance": params.get("snap_tolerance", 1.0),
                "nSolveIter": params.get("n_solve_iter", 100),
                "nRelaxIter": params.get("n_relax_iter", 5),
            },
            "addLayersControls": {
                "relativeSizes": True,
                "layers": {
                    Path(geometry_path).stem: {
                        "nSurfaceLayers": params.get("boundary_layer_count", 5),
                    },
                },
                "expansionRatio": params.get("expansion_ratio", 1.2),
                "finalLayerThickness": params.get("final_layer_thickness", 0.3),
                "minThickness": params.get("min_thickness", 0.1),
                "nGrow": params.get("n_grow", 0),
                "featureAngle": params.get("feature_angle", 30),
                "nRelaxIter": params.get("layer_relax_iter", 5),
                "nSmoothSurfaceNormals": params.get("n_smooth_normals", 1),
            },
            "mergeTolerance": params.get("merge_tolerance", 1e-6),
        }

    @staticmethod
    def _build_surface_transport_dict(geometry_path: str) -> dict[str, Any]:
        return {
            "surfaces": {
                Path(geometry_path).stem: {
                    "type": "triSurfaceMesh",
                    "file": geometry_path,
                },
            },
        }

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