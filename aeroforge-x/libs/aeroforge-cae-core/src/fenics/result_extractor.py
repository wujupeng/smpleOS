from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FieldData:
    name: str
    field_type: str
    component_count: int
    data_shape: list[int]
    min_value: float
    max_value: float
    unit: str = ""


@dataclass
class ExtractionResult:
    fields: list[FieldData] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    output_path: str | None = None


class ResultExtractor:
    FIELD_PATTERNS: dict[str, list[str]] = {
        "stress": ["sigma", "von_mises", "principal_stress", "cauchy_stress"],
        "displacement": ["u", "displacement", "deformation"],
        "strain": ["epsilon", "strain", "green_strain"],
        "temperature": ["T", "temperature", "thermal"],
        "heat_flux": ["q", "heat_flux", "flux"],
        "pressure": ["p", "pressure"],
        "velocity": ["U", "velocity"],
    }

    def extract_fields(
        self,
        results_dir: str,
        field_names: list[str] | None = None,
        output_dir: str | None = None,
    ) -> ExtractionResult:
        results_path = Path(results_dir)
        if not results_path.exists():
            raise FileNotFoundError(f"Results directory not found: {results_dir}")

        target_fields = field_names or list(self.FIELD_PATTERNS.keys())
        extracted: list[FieldData] = []

        for field_name in target_fields:
            field_data = self._extract_single_field(results_path, field_name)
            if field_data is not None:
                extracted.append(field_data)

        result = ExtractionResult(
            fields=extracted,
            metadata={"source_dir": str(results_path), "field_count": len(extracted)},
        )

        if output_dir is not None:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            result.output_path = self._save_extraction(out_path, result)

        logger.info("Extracted %d fields from %s", len(extracted), results_dir)
        return result

    def _extract_single_field(self, results_path: Path, field_name: str) -> FieldData | None:
        patterns = self.FIELD_PATTERNS.get(field_name, [field_name])

        for pattern in patterns:
            for p in results_path.rglob(f"*{pattern}*"):
                if p.is_file():
                    return FieldData(
                        name=field_name,
                        field_type=self._infer_field_type(field_name),
                        component_count=self._infer_component_count(field_name),
                        data_shape=[0],
                        min_value=0.0,
                        max_value=0.0,
                        unit=self._infer_unit(field_name),
                    )

        return None

    def extract_stress(self, results_dir: str) -> dict[str, Any]:
        result = self.extract_fields(results_dir, ["stress"])
        return {"fields": [f.__dict__ for f in result.fields], "metadata": result.metadata}

    def extract_displacement(self, results_dir: str) -> dict[str, Any]:
        result = self.extract_fields(results_dir, ["displacement"])
        return {"fields": [f.__dict__ for f in result.fields], "metadata": result.metadata}

    def extract_temperature(self, results_dir: str) -> dict[str, Any]:
        result = self.extract_fields(results_dir, ["temperature"])
        return {"fields": [f.__dict__ for f in result.fields], "metadata": result.metadata}

    def get_available_fields(self, results_dir: str) -> list[str]:
        results_path = Path(results_dir)
        if not results_path.exists():
            return []
        available: list[str] = []
        for field_name, patterns in self.FIELD_PATTERNS.items():
            for pattern in patterns:
                if any(results_path.rglob(f"*{pattern}*")):
                    available.append(field_name)
                    break
        return available

    @staticmethod
    def _infer_field_type(field_name: str) -> str:
        scalar_fields = {"stress", "temperature", "pressure", "heat_flux"}
        vector_fields = {"displacement", "velocity", "strain"}
        if field_name in scalar_fields:
            return "scalar"
        if field_name in vector_fields:
            return "vector"
        return "scalar"

    @staticmethod
    def _infer_component_count(field_name: str) -> int:
        vector_fields = {"displacement", "velocity"}
        tensor_fields = {"stress", "strain"}
        if field_name in vector_fields:
            return 3
        if field_name in tensor_fields:
            return 6
        return 1

    @staticmethod
    def _infer_unit(field_name: str) -> str:
        units: dict[str, str] = {
            "stress": "Pa",
            "displacement": "m",
            "strain": "",
            "temperature": "K",
            "heat_flux": "W/m2",
            "pressure": "Pa",
            "velocity": "m/s",
        }
        return units.get(field_name, "")

    def _save_extraction(self, output_dir: Path, result: ExtractionResult) -> str:
        data = {
            "fields": [
                {
                    "name": f.name,
                    "field_type": f.field_type,
                    "component_count": f.component_count,
                    "data_shape": f.data_shape,
                    "min_value": f.min_value,
                    "max_value": f.max_value,
                    "unit": f.unit,
                }
                for f in result.fields
            ],
            "metadata": result.metadata,
        }
        out_file = output_dir / "field_extraction.json"
        out_file.write_text(json.dumps(data, indent=2))
        return str(out_file)