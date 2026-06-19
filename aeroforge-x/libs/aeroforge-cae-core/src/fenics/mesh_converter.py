from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MeshFormat(str, Enum):
    STEP = "step"
    STL = "stl"
    GMSH = "msh"
    VTK = "vtk"
    XDMF = "xdmf"
    FENICS_XML = "xml"


@dataclass
class MeshConversionResult:
    input_path: str
    output_path: str
    input_format: MeshFormat
    output_format: MeshFormat
    node_count: int = 0
    element_count: int = 0
    bounding_box: dict[str, list[float]] | None = None


class MeshConverter:
    SUPPORTED_CONVERSIONS: dict[str, list[str]] = {
        "step": ["stl", "msh", "xdmf"],
        "stl": ["msh", "xdmf"],
        "msh": ["xdmf", "xml", "vtk"],
        "vtk": ["xdmf"],
    }

    def convert(
        self,
        input_path: str,
        output_format: MeshFormat,
        output_dir: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> MeshConversionResult:
        in_path = Path(input_path)
        if not in_path.exists():
            raise FileNotFoundError(f"Input mesh file not found: {input_path}")

        input_format = self._detect_format(in_path)
        if input_format is None:
            raise ValueError(f"Unsupported input format: {in_path.suffix}")

        available = self.SUPPORTED_CONVERSIONS.get(input_format.value, [])
        if output_format.value not in available:
            raise ValueError(
                f"Conversion {input_format.value} -> {output_format.value} not supported. "
                f"Available: {available}"
            )

        out_dir = Path(output_dir) if output_dir else in_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{in_path.stem}.{output_format.value}"

        conversion_params = params or {}
        result = MeshConversionResult(
            input_path=str(in_path),
            output_path=str(output_path),
            input_format=input_format,
            output_format=output_format,
        )

        logger.info(
            "Mesh conversion: %s -> %s (params=%s)",
            input_format.value, output_format.value, conversion_params,
        )

        return result

    def _detect_format(self, path: Path) -> MeshFormat | None:
        suffix_map: dict[str, MeshFormat] = {
            ".step": MeshFormat.STEP,
            ".stp": MeshFormat.STEP,
            ".stl": MeshFormat.STL,
            ".msh": MeshFormat.GMSH,
            ".vtk": MeshFormat.VTK,
            ".xdmf": MeshFormat.XDMF,
            ".xml": MeshFormat.FENICS_XML,
        }
        return suffix_map.get(path.suffix.lower())

    def get_supported_output_formats(self, input_format: MeshFormat) -> list[str]:
        return self.SUPPORTED_CONVERSIONS.get(input_format.value, [])

    def estimate_conversion_resources(
        self,
        input_path: str,
        output_format: MeshFormat,
    ) -> dict[str, Any]:
        in_path = Path(input_path)
        file_size_mb = in_path.stat().st_size / (1024 * 1024) if in_path.exists() else 0
        estimated_memory_mb = file_size_mb * 10
        estimated_time_seconds = file_size_mb * 2

        return {
            "input_file_size_mb": round(file_size_mb, 2),
            "estimated_memory_mb": round(estimated_memory_mb, 2),
            "estimated_time_seconds": round(estimated_time_seconds, 2),
        }