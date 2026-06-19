from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MeshType(str, Enum):
    STRUCTURED = "structured"
    UNSTRUCTURED = "unstructured"
    HYBRID = "hybrid"


class MeshFormat(str, Enum):
    OPENFOAM = "openfoam"
    GMSH = "gmsh"
    VTK = "vtk"
    XDMF = "xdmf"
    FENICS_XML = "fenics_xml"


@dataclass
class MeshGenerationParams:
    source_geometry: str
    mesh_type: MeshType
    output_format: MeshFormat = MeshFormat.OPENFOAM
    target_element_size: float = 0.01
    min_element_size: float = 0.001
    max_element_size: float = 0.1
    growth_rate: float = 1.2
    boundary_layer_layers: int = 5
    boundary_layer_first_layer_thickness: float = 0.0001
    boundary_layer_growth_rate: float = 1.2
    n_proc: int = 1
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class MeshQualityMetrics:
    orthogonality_min: float = 0.0
    orthogonality_avg: float = 0.0
    skewness_max: float = 0.0
    skewness_avg: float = 0.0
    aspect_ratio_max: float = 0.0
    aspect_ratio_avg: float = 0.0
    non_orthogonal_count: int = 0
    highly_skewed_count: int = 0


@dataclass
class MeshGenerationResult:
    output_path: str
    mesh_type: MeshType
    node_count: int = 0
    element_count: int = 0
    boundary_face_count: int = 0
    quality_metrics: MeshQualityMetrics | None = None
    generation_time_seconds: float = 0.0
    memory_peak_mb: float = 0.0
    error_message: str | None = None


class MeshGeneratorBase(ABC):
    @abstractmethod
    def generate(self, params: MeshGenerationParams) -> MeshGenerationResult:
        ...

    @abstractmethod
    def estimate_resources(self, params: MeshGenerationParams) -> dict[str, Any]:
        ...

    def validate_geometry(self, geometry_path: str) -> dict[str, Any]:
        path = Path(geometry_path)
        if not path.exists():
            raise FileNotFoundError(f"Geometry file not found: {geometry_path}")
        result: dict[str, Any] = {
            "valid": True,
            "issues": [],
            "file_size_mb": round(path.stat().st_size / (1024 * 1024), 2),
        }
        logger.info("Geometry validation for %s: valid=%s", geometry_path, result["valid"])
        return result

    def estimate_mesh_size(self, params: MeshGenerationParams) -> dict[str, Any]:
        geo_path = Path(params.source_geometry)
        file_size_mb = geo_path.stat().st_size / (1024 * 1024) if geo_path.exists() else 1.0
        volume_factor = (1.0 / params.target_element_size) ** 3
        estimated_elements = int(file_size_mb * 1000 * volume_factor * 0.1)
        estimated_nodes = int(estimated_elements * 0.8)
        estimated_memory_mb = estimated_elements * 200 / (1024 * 1024)

        return {
            "estimated_node_count": estimated_nodes,
            "estimated_element_count": estimated_elements,
            "estimated_memory_mb": round(estimated_memory_mb, 2),
            "estimated_time_seconds": round(estimated_elements * 0.001, 2),
        }