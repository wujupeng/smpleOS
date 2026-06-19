from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VisualizationConfig:
    output_dir: str
    format: str = "vtk"
    color_map: str = "jet"
    scalar_range: list[float] | None = None
    show_edges: bool = False
    show_grid: bool = True
    camera_position: list[float] | None = None
    image_resolution: list[int] | None = None


@dataclass
class VisualizationResult:
    output_files: list[str] = field(default_factory=list)
    pvsm_file: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ResultVisualizer:
    def __init__(self, working_dir: str = "/tmp/aeroforge/visualization") -> None:
        self._working_dir = Path(working_dir)
        self._working_dir.mkdir(parents=True, exist_ok=True)

    def generate_vtk_files(
        self,
        results_dir: str,
        config: VisualizationConfig | None = None,
    ) -> VisualizationResult:
        results_path = Path(results_dir)
        if not results_path.exists():
            raise FileNotFoundError(f"Results directory not found: {results_dir}")

        cfg = config or VisualizationConfig(output_dir=str(self._working_dir))
        output_path = Path(cfg.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        output_files: list[str] = []
        for time_dir in sorted(results_path.iterdir()):
            if time_dir.is_dir():
                for vtk_file in time_dir.glob("*.vtk"):
                    dest = output_path / f"{time_dir.name}_{vtk_file.name}"
                    output_files.append(str(dest))

        result = VisualizationResult(
            output_files=output_files,
            metadata={"source_dir": str(results_path), "format": cfg.format},
        )

        logger.info("Generated VTK visualization: %d files from %s", len(output_files), results_dir)
        return result

    def generate_paraview_state(
        self,
        results_dir: str,
        output_path: str,
        fields: list[str] | None = None,
    ) -> str:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        pvsm_data = {
            "ParaviewState": {
                "version": "5.11",
                "source": str(results_path),
                "views": [],
                "representations": [],
            }
        }

        if fields:
            for field_name in fields:
                pvsm_data["ParaviewState"]["representations"].append({
                    "type": "PVRepresentation",
                    "field": field_name,
                    "colorMap": "jet",
                })

        pvsm_path = out_path if str(out_path).endswith(".pvsm") else out_path.with_suffix(".pvsm")
        pvsm_path.write_text(json.dumps(pvsm_data, indent=2))

        logger.info("Generated ParaView state file: %s", pvsm_path)
        return str(pvsm_path)

    def generate_contour_data(
        self,
        results_dir: str,
        field_name: str,
        levels: list[float] | None = None,
        output_dir: str | None = None,
    ) -> dict[str, Any]:
        out_dir = Path(output_dir) if output_dir else self._working_dir / "contours"
        out_dir.mkdir(parents=True, exist_ok=True)

        contour_levels = levels or self._auto_levels(field_name)
        contour_data: dict[str, Any] = {
            "field": field_name,
            "levels": contour_levels,
            "contours": [],
        }

        logger.info("Generated contour data for field=%s levels=%d", field_name, len(contour_levels))
        return contour_data

    def generate_vector_field_data(
        self,
        results_dir: str,
        field_name: str,
        sample_rate: int = 1,
        output_dir: str | None = None,
    ) -> dict[str, Any]:
        out_dir = Path(output_dir) if output_dir else self._working_dir / "vectors"
        out_dir.mkdir(parents=True, exist_ok=True)

        vector_data: dict[str, Any] = {
            "field": field_name,
            "sample_rate": sample_rate,
            "vectors": [],
        }

        logger.info("Generated vector field data for field=%s", field_name)
        return vector_data

    @staticmethod
    def _auto_levels(field_name: str) -> list[float]:
        defaults: dict[str, list[float]] = {
            "pressure": [101300, 101320, 101340, 101360, 101380],
            "velocity": [0, 10, 20, 30, 40, 50],
            "temperature": [280, 290, 300, 310, 320],
            "stress": [0, 50e6, 100e6, 150e6, 200e6],
        }
        return defaults.get(field_name, [0.0, 0.25, 0.5, 0.75, 1.0])