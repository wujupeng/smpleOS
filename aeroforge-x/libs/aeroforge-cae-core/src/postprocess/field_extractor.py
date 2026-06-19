from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FieldExtractionConfig:
    field_names: list[str]
    time_steps: list[float] | None = None
    region: str | None = None
    output_format: str = "json"
    include_bounds: bool = True


@dataclass
class ExtractedField:
    name: str
    field_type: str
    time_step: float
    data: dict[str, Any] = field(default_factory=dict)
    bounds: dict[str, list[float]] | None = None
    unit: str = ""


class FieldExtractor:
    FIELD_TYPE_MAP: dict[str, str] = {
        "pressure": "scalar",
        "p": "scalar",
        "temperature": "scalar",
        "T": "scalar",
        "k": "scalar",
        "omega": "scalar",
        "velocity": "vector",
        "U": "vector",
        "displacement": "vector",
        "stress": "tensor",
        "sigma": "tensor",
        "strain": "tensor",
        "epsilon": "tensor",
    }

    FIELD_UNIT_MAP: dict[str, str] = {
        "pressure": "Pa",
        "p": "Pa",
        "temperature": "K",
        "T": "K",
        "k": "m2/s2",
        "omega": "1/s",
        "velocity": "m/s",
        "U": "m/s",
        "displacement": "m",
        "stress": "Pa",
        "sigma": "Pa",
        "strain": "",
        "epsilon": "",
    }

    def extract_pressure_field(
        self,
        results_dir: str,
        time_step: float | None = None,
        output_dir: str | None = None,
    ) -> ExtractedField:
        return self._extract_scalar_field(results_dir, "pressure", "p", time_step, output_dir)

    def extract_velocity_field(
        self,
        results_dir: str,
        time_step: float | None = None,
        output_dir: str | None = None,
    ) -> ExtractedField:
        return self._extract_vector_field(results_dir, "velocity", "U", time_step, output_dir)

    def extract_stress_field(
        self,
        results_dir: str,
        time_step: float | None = None,
        output_dir: str | None = None,
    ) -> ExtractedField:
        return self._extract_tensor_field(results_dir, "stress", "sigma", time_step, output_dir)

    def extract_temperature_field(
        self,
        results_dir: str,
        time_step: float | None = None,
        output_dir: str | None = None,
    ) -> ExtractedField:
        return self._extract_scalar_field(results_dir, "temperature", "T", time_step, output_dir)

    def extract_fields(
        self,
        results_dir: str,
        config: FieldExtractionConfig,
    ) -> list[ExtractedField]:
        results_path = Path(results_dir)
        if not results_path.exists():
            raise FileNotFoundError(f"Results directory not found: {results_dir}")

        extracted: list[ExtractedField] = []
        for field_name in config.field_names:
            internal = self._resolve_internal_name(field_name)
            field_type = self.FIELD_TYPE_MAP.get(field_name, "scalar")
            unit = self.FIELD_UNIT_MAP.get(field_name, "")

            if field_type == "scalar":
                f = self._extract_scalar_field(results_dir, field_name, internal, None, None)
            elif field_type == "vector":
                f = self._extract_vector_field(results_dir, field_name, internal, None, None)
            else:
                f = self._extract_tensor_field(results_dir, field_name, internal, None, None)
            extracted.append(f)

        if config.output_format == "json" and output_dir := config.region:
            self._save_extracted_fields(extracted, output_dir)

        logger.info("Extracted %d fields from %s", len(extracted), results_dir)
        return extracted

    def get_available_fields(self, results_dir: str) -> list[str]:
        results_path = Path(results_dir)
        if not results_path.exists():
            return []

        available: list[str] = []
        time_dirs = sorted(
            [d for d in results_path.iterdir() if d.is_dir() and d.name.replace(".", "", 1).isdigit()],
            key=lambda p: float(p.name),
        )
        if not time_dirs:
            return available

        latest = time_dirs[-1]
        for field_dir in latest.iterdir():
            if field_dir.is_dir():
                name = field_dir.name
                for display_name, internal in [("pressure", "p"), ("velocity", "U"),
                                                ("temperature", "T"), ("k", "k"), ("omega", "omega")]:
                    if name == internal and display_name not in available:
                        available.append(display_name)
        return available

    def _extract_scalar_field(
        self,
        results_dir: str,
        display_name: str,
        internal_name: str,
        time_step: float | None,
        output_dir: str | None,
    ) -> ExtractedField:
        return ExtractedField(
            name=display_name,
            field_type="scalar",
            time_step=time_step or 0.0,
            unit=self.FIELD_UNIT_MAP.get(display_name, ""),
        )

    def _extract_vector_field(
        self,
        results_dir: str,
        display_name: str,
        internal_name: str,
        time_step: float | None,
        output_dir: str | None,
    ) -> ExtractedField:
        return ExtractedField(
            name=display_name,
            field_type="vector",
            time_step=time_step or 0.0,
            unit=self.FIELD_UNIT_MAP.get(display_name, ""),
        )

    def _extract_tensor_field(
        self,
        results_dir: str,
        display_name: str,
        internal_name: str,
        time_step: float | None,
        output_dir: str | None,
    ) -> ExtractedField:
        return ExtractedField(
            name=display_name,
            field_type="tensor",
            time_step=time_step or 0.0,
            unit=self.FIELD_UNIT_MAP.get(display_name, ""),
        )

    @staticmethod
    def _resolve_internal_name(field_name: str) -> str:
        mapping = {
            "pressure": "p", "velocity": "U", "temperature": "T",
            "stress": "sigma", "strain": "epsilon", "displacement": "u",
        }
        return mapping.get(field_name, field_name)

    def _save_extracted_fields(self, fields: list[ExtractedField], output_dir: str) -> None:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        data = []
        for f in fields:
            entry = {
                "name": f.name,
                "field_type": f.field_type,
                "time_step": f.time_step,
                "unit": f.unit,
            }
            data.append(entry)
        (out_path / "extracted_fields.json").write_text(json.dumps(data, indent=2))