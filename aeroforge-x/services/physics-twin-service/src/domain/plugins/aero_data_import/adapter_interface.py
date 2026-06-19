from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.domain.plugins.aerodynamic_database import FourDimLookupTable


@dataclass
class RawAeroData:
    format_name: str
    alpha_values: list[float] = field(default_factory=list)
    beta_values: list[float] = field(default_factory=list)
    mach_values: list[float] = field(default_factory=list)
    reynolds_values: list[float] = field(default_factory=list)
    coefficients: dict[str, np.ndarray] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    missing_dimensions: list[str] = field(default_factory=list)
    stability_derivatives: dict[str, float] = field(default_factory=dict)


@dataclass
class ConstraintCheck:
    is_valid: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class AeroDataImportAdapter(ABC):

    @property
    @abstractmethod
    def format_name(self) -> str:
        pass

    @abstractmethod
    def parse(self, file_path: str) -> RawAeroData:
        pass

    @abstractmethod
    def validate_physical_constraints(self, data: RawAeroData) -> ConstraintCheck:
        pass

    @abstractmethod
    def convert_to_internal(self, raw: RawAeroData) -> FourDimLookupTable:
        pass

    def _check_common_constraints(self, data: RawAeroData) -> ConstraintCheck:
        violations: list[str] = []
        warnings: list[str] = []

        if "CD" in data.coefficients:
            cd_data = data.coefficients["CD"]
            neg_count = int((cd_data < 0).sum())
            if neg_count > 0:
                violations.append(f"Negative drag coefficient found in {neg_count} data points")
            nan_count = int(np.isnan(cd_data).sum())
            if nan_count > 0:
                violations.append(f"NaN values found in CD: {nan_count}")

        for coeff_name, coeff_arr in data.coefficients.items():
            nan_count = int(np.isnan(coeff_arr).sum())
            inf_count = int(np.isinf(coeff_arr).sum())
            if nan_count > 0:
                violations.append(f"NaN values found in {coeff_name}: {nan_count}")
            if inf_count > 0:
                violations.append(f"Inf values found in {coeff_name}: {inf_count}")

        if len(data.missing_dimensions) > 0:
            warnings.append(f"Missing dimensions: {data.missing_dimensions} — will be filled with defaults")

        if not data.alpha_values:
            violations.append("No alpha values provided")
        if not data.mach_values:
            warnings.append("No Mach values provided — will use default range")

        return ConstraintCheck(
            is_valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
        )