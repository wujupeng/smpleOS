from __future__ import annotations

import re
from typing import Any

import numpy as np

from src.domain.plugins.aerodynamic_database import FourDimLookupTable
from src.domain.plugins.aero_data_import.adapter_interface import (
    AeroDataImportAdapter,
    ConstraintCheck,
    RawAeroData,
)


class OpenVSPAdapter(AeroDataImportAdapter):

    @property
    def format_name(self) -> str:
        return "OpenVSP"

    def parse(self, file_path: str) -> RawAeroData:
        with open(file_path, "r") as f:
            content = f.read()

        alpha_values: list[float] = []
        beta_values: list[float] = []
        mach_values: list[float] = []
        reynolds_values: list[float] = []
        coefficients: dict[str, np.ndarray] = {}
        metadata: dict[str, Any] = {"source": "OpenVSP", "file_path": file_path}
        missing_dimensions: list[str] = []

        header_match = re.search(r"Config:\s*(.+)", content)
        if header_match:
            metadata["config"] = header_match.group(1).strip()

        alpha_pattern = re.compile(r"alpha\s*=\s*([-\d.]+)", re.IGNORECASE)
        mach_pattern = re.compile(r"mach\s*=\s*([\d.]+)", re.IGNORECASE)
        beta_pattern = re.compile(r"beta\s*=\s*([-\d.]+)", re.IGNORECASE)

        for m in alpha_pattern.finditer(content):
            val = float(m.group(1))
            if val not in alpha_values:
                alpha_values.append(val)

        for m in mach_pattern.finditer(content):
            val = float(m.group(1))
            if val not in mach_values:
                mach_values.append(val)

        for m in beta_pattern.finditer(content):
            val = float(m.group(1))
            if val not in beta_values:
                beta_values.append(val)

        if not alpha_values:
            alpha_values = [0.0]
            missing_dimensions.append("alpha")
        if not mach_values:
            mach_values = [0.0]
            missing_dimensions.append("mach")
        if not beta_values:
            beta_values = [0.0]
        if not reynolds_values:
            reynolds_values = [1e7]
            missing_dimensions.append("reynolds")

        alpha_values.sort()
        beta_values.sort()
        mach_values.sort()
        reynolds_values.sort()

        shape = (len(alpha_values), len(beta_values), len(mach_values), len(reynolds_values))
        for coeff_name in ["CL", "CD", "CM", "CY", "Cl", "Cn"]:
            coefficients[coeff_name] = np.zeros(shape, dtype=np.float64)

        coeff_patterns = {
            "CL": re.compile(r"CL\s*=\s*([-\d.eE+]+)", re.IGNORECASE),
            "CD": re.compile(r"CD\s*=\s*([-\d.eE+]+)", re.IGNORECASE),
            "CM": re.compile(r"Cm\s*=\s*([-\d.eE+]+)", re.IGNORECASE),
            "CY": re.compile(r"CY\s*=\s*([-\d.eE+]+)", re.IGNORECASE),
            "Cl": re.compile(r"Cl_roll\s*=\s*([-\d.eE+]+)", re.IGNORECASE),
            "Cn": re.compile(r"Cn_yaw\s*=\s*([-\d.eE+]+)", re.IGNORECASE),
        }

        blocks = re.split(r"(?=alpha\s*=)", content)
        for block in blocks:
            if "alpha" not in block.lower():
                continue

            alpha_m = alpha_pattern.search(block)
            mach_m = mach_pattern.search(block)
            beta_m = beta_pattern.search(block)

            if not alpha_m:
                continue

            alpha_val = float(alpha_m.group(1))
            mach_val = float(mach_m.group(1)) if mach_m else mach_values[0]
            beta_val = float(beta_m.group(1)) if beta_m else beta_values[0]

            i_alpha = self._find_nearest_index(alpha_val, alpha_values)
            i_beta = self._find_nearest_index(beta_val, beta_values)
            i_mach = self._find_nearest_index(mach_val, mach_values)
            i_reynolds = 0

            for coeff_name, pattern in coeff_patterns.items():
                match = pattern.search(block)
                if match:
                    coefficients[coeff_name][i_alpha, i_beta, i_mach, i_reynolds] = float(match.group(1))

        return RawAeroData(
            format_name=self.format_name,
            alpha_values=alpha_values,
            beta_values=beta_values,
            mach_values=mach_values,
            reynolds_values=reynolds_values,
            coefficients=coefficients,
            metadata=metadata,
            missing_dimensions=missing_dimensions,
        )

    def validate_physical_constraints(self, data: RawAeroData) -> ConstraintCheck:
        return self._check_common_constraints(data)

    def convert_to_internal(self, raw: RawAeroData) -> FourDimLookupTable:
        alpha_min, alpha_max = min(raw.alpha_values), max(raw.alpha_values)
        beta_min, beta_max = min(raw.beta_values), max(raw.beta_values)
        mach_min, mach_max = min(raw.mach_values), max(raw.mach_values)
        re_min, re_max = min(raw.reynolds_values), max(raw.reynolds_values)

        alpha_res = self._compute_resolution(raw.alpha_values, alpha_min, alpha_max)
        beta_res = self._compute_resolution(raw.beta_values, beta_min, beta_max)
        mach_res = self._compute_resolution(raw.mach_values, mach_min, mach_max)
        re_res = self._compute_resolution(raw.reynolds_values, re_min, re_max)

        table = FourDimLookupTable(
            database_id=f"ADB-OpenVSP-{raw.metadata.get('config', 'default')}",
            database_name=f"OpenVSP Import ({raw.metadata.get('file_path', 'unknown')})",
            alpha_range=(alpha_min, alpha_max),
            alpha_resolution=alpha_res,
            beta_range=(beta_min, beta_max),
            beta_resolution=beta_res,
            mach_range=(mach_min, mach_max),
            mach_resolution=mach_res,
            reynolds_range=(re_min, re_max),
            reynolds_resolution=re_res,
            coefficient_types=list(raw.coefficients.keys()),
            data_source="OpenVSP",
            quality_status="draft",
            applicable_config=raw.metadata.get("config", ""),
            partial_coverage_dimensions=raw.missing_dimensions,
        )

        for coeff_type, data in raw.coefficients.items():
            table.set_coefficient_data(coeff_type, data)

        return table

    @staticmethod
    def _find_nearest_index(value: float, values: list[float]) -> int:
        if not values:
            return 0
        diffs = [abs(v - value) for v in values]
        return diffs.index(min(diffs))

    @staticmethod
    def _compute_resolution(values: list[float], vmin: float, vmax: float) -> float:
        if len(values) <= 1:
            return 1.0
        sorted_vals = sorted(values)
        diffs = [sorted_vals[i + 1] - sorted_vals[i] for i in range(len(sorted_vals) - 1)]
        valid_diffs = [d for d in diffs if d > 0]
        if not valid_diffs:
            return 1.0
        return min(valid_diffs)