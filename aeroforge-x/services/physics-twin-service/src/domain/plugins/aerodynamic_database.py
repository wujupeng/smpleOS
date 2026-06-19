from __future__ import annotations

import math
import uuid
import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.domain.enums import FidelityLevel
from src.domain.plugins.interfaces import (
    DOF6Output, DOF6State, IPhysicsModelPlugin, StabilityCheck,
)


@dataclass
class AeroCoefficients:
    CL: float = 0.0
    CD: float = 0.0
    CM: float = 0.0
    CY: float = 0.0
    Cl: float = 0.0
    Cn: float = 0.0
    is_extrapolated: bool = False
    extrapolation_warning: str = ""
    nearest_boundary_alpha: float | None = None
    nearest_boundary_beta: float | None = None


class FourDimLookupTable:

    def __init__(
        self,
        database_id: str,
        database_name: str,
        alpha_range: tuple[float, float],
        alpha_resolution: float,
        beta_range: tuple[float, float],
        beta_resolution: float,
        mach_range: tuple[float, float],
        mach_resolution: float,
        reynolds_range: tuple[float, float],
        reynolds_resolution: float,
        coefficient_types: list[str] | None = None,
        data_source: str = "internal",
        quality_status: str = "draft",
        applicable_config: str = "",
        partial_coverage_dimensions: list[str] | None = None,
    ):
        self.database_id = database_id
        self.database_name = database_name
        self.alpha_range = alpha_range
        self.alpha_resolution = alpha_resolution
        self.beta_range = beta_range
        self.beta_resolution = beta_resolution
        self.mach_range = mach_range
        self.mach_resolution = mach_resolution
        self.reynolds_range = reynolds_range
        self.reynolds_resolution = reynolds_resolution
        self.coefficient_types = coefficient_types or ["CL", "CD", "CM", "CY", "Cl", "Cn"]
        self.data_source = data_source
        self.quality_status = quality_status
        self.applicable_config = applicable_config
        self.partial_coverage_dimensions = partial_coverage_dimensions or []
        self.is_partial_coverage = len(self.partial_coverage_dimensions) > 0

        self._alpha_axis = np.arange(alpha_range[0], alpha_range[1] + alpha_resolution * 0.5, alpha_resolution)
        self._beta_axis = np.arange(beta_range[0], beta_range[1] + beta_resolution * 0.5, beta_resolution)
        self._mach_axis = np.arange(mach_range[0], mach_range[1] + mach_resolution * 0.5, mach_resolution)
        self._reynolds_axis = np.arange(reynolds_range[0], reynolds_range[1] + reynolds_resolution * 0.5, reynolds_resolution)

        shape = (len(self._alpha_axis), len(self._beta_axis), len(self._mach_axis), len(self._reynolds_axis))
        self._data: dict[str, np.ndarray] = {}
        for ct in self.coefficient_types:
            self._data[ct] = np.zeros(shape, dtype=np.float64)

    def set_coefficient_data(self, coefficient_type: str, data: np.ndarray) -> None:
        if coefficient_type not in self.coefficient_types:
            raise ValueError(f"Unknown coefficient type: {coefficient_type}")
        expected_shape = (len(self._alpha_axis), len(self._beta_axis), len(self._mach_axis), len(self._reynolds_axis))
        if data.shape != expected_shape:
            raise ValueError(f"Data shape {data.shape} does not match expected {expected_shape}")
        self._data[coefficient_type] = data

    def get_coefficient(self, coefficient_type: str, alpha: float, beta: float, mach: float, reynolds: float) -> float:
        if coefficient_type not in self._data:
            return 0.0
        result = self._interpolate_single(coefficient_type, alpha, beta, mach, reynolds)
        return float(result)

    def query_all(self, alpha: float, beta: float, mach: float, reynolds: float) -> AeroCoefficients:
        is_extrapolated = not self.is_within_range(alpha, beta, mach, reynolds)
        warning = ""
        nearest_alpha = None
        nearest_beta = None

        if is_extrapolated:
            warning = f"Query point (alpha={alpha:.2f}, beta={beta:.2f}, mach={mach:.3f}, Re={reynolds:.2e}) is outside database range"
            nearest_alpha = float(np.clip(alpha, self.alpha_range[0], self.alpha_range[1]))
            nearest_beta = float(np.clip(beta, self.beta_range[0], self.beta_range[1]))

        clamped_alpha = float(np.clip(alpha, self.alpha_range[0], self.alpha_range[1]))
        clamped_beta = float(np.clip(beta, self.beta_range[0], self.beta_range[1]))
        clamped_mach = float(np.clip(mach, self.mach_range[0], self.mach_range[1]))
        clamped_reynolds = float(np.clip(reynolds, self.reynolds_range[0], self.reynolds_range[1]))

        return AeroCoefficients(
            CL=self._interpolate_single("CL", clamped_alpha, clamped_beta, clamped_mach, clamped_reynolds),
            CD=self._interpolate_single("CD", clamped_alpha, clamped_beta, clamped_mach, clamped_reynolds),
            CM=self._interpolate_single("CM", clamped_alpha, clamped_beta, clamped_mach, clamped_reynolds),
            CY=self._interpolate_single("CY", clamped_alpha, clamped_beta, clamped_mach, clamped_reynolds),
            Cl=self._interpolate_single("Cl", clamped_alpha, clamped_beta, clamped_mach, clamped_reynolds),
            Cn=self._interpolate_single("Cn", clamped_alpha, clamped_beta, clamped_mach, clamped_reynolds),
            is_extrapolated=is_extrapolated,
            extrapolation_warning=warning,
            nearest_boundary_alpha=nearest_alpha,
            nearest_boundary_beta=nearest_beta,
        )

    def is_within_range(self, alpha: float, beta: float, mach: float, reynolds: float) -> bool:
        return (
            self.alpha_range[0] <= alpha <= self.alpha_range[1]
            and self.beta_range[0] <= beta <= self.beta_range[1]
            and self.mach_range[0] <= mach <= self.mach_range[1]
            and self.reynolds_range[0] <= reynolds <= self.reynolds_range[1]
        )

    def get_boundary_values(self, alpha: float, beta: float, mach: float, reynolds: float) -> dict[str, float]:
        return {
            "nearest_alpha": float(np.clip(alpha, self.alpha_range[0], self.alpha_range[1])),
            "nearest_beta": float(np.clip(beta, self.beta_range[0], self.beta_range[1])),
            "nearest_mach": float(np.clip(mach, self.mach_range[0], self.mach_range[1])),
            "nearest_reynolds": float(np.clip(reynolds, self.reynolds_range[0], self.reynolds_range[1])),
        }

    def _interpolate_single(self, coeff_type: str, alpha: float, beta: float, mach: float, reynolds: float) -> float:
        data = self._data.get(coeff_type)
        if data is None:
            return 0.0

        i_alpha = self._find_fractional_index(alpha, self._alpha_axis)
        i_beta = self._find_fractional_index(beta, self._beta_axis)
        i_mach = self._find_fractional_index(mach, self._mach_axis)
        i_reynolds = self._find_fractional_index(reynolds, self._reynolds_axis)

        i0 = int(np.floor(i_alpha))
        j0 = int(np.floor(i_beta))
        k0 = int(np.floor(i_mach))
        l0 = int(np.floor(i_reynolds))

        i0 = max(0, min(i0, len(self._alpha_axis) - 2))
        j0 = max(0, min(j0, len(self._beta_axis) - 2))
        k0 = max(0, min(k0, len(self._mach_axis) - 2))
        l0 = max(0, min(l0, len(self._reynolds_axis) - 2))

        da = i_alpha - i0
        db = i_beta - j0
        dm = i_mach - k0
        dr = i_reynolds - l0

        da = max(0.0, min(1.0, da))
        db = max(0.0, min(1.0, db))
        dm = max(0.0, min(1.0, dm))
        dr = max(0.0, min(1.0, dr))

        result = 0.0
        for ia in range(2):
            for jb in range(2):
                for kb in range(2):
                    for lb in range(2):
                        w = (
                            (da if ia else 1 - da)
                            * (db if jb else 1 - db)
                            * (dm if kb else 1 - dm)
                            * (dr if lb else 1 - dr)
                        )
                        result += w * data[i0 + ia, j0 + jb, k0 + kb, l0 + lb]

        return float(result)

    @staticmethod
    def _find_fractional_index(value: float, axis: np.ndarray) -> float:
        if len(axis) < 2:
            return 0.0
        if value <= axis[0]:
            return 0.0
        if value >= axis[-1]:
            return float(len(axis) - 1)
        idx = np.searchsorted(axis, value, side="right") - 1
        idx = max(0, min(idx, len(axis) - 2))
        if axis[idx + 1] == axis[idx]:
            return float(idx)
        return float(idx + (value - axis[idx]) / (axis[idx + 1] - axis[idx]))

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "database_id": self.database_id,
            "database_name": self.database_name,
            "alpha_range": self.alpha_range,
            "alpha_resolution": self.alpha_resolution,
            "beta_range": self.beta_range,
            "beta_resolution": self.beta_resolution,
            "mach_range": self.mach_range,
            "mach_resolution": self.mach_resolution,
            "reynolds_range": self.reynolds_range,
            "reynolds_resolution": self.reynolds_resolution,
            "coefficient_types": self.coefficient_types,
            "data_source": self.data_source,
            "quality_status": self.quality_status,
            "applicable_config": self.applicable_config,
            "is_partial_coverage": self.is_partial_coverage,
            "partial_coverage_dimensions": self.partial_coverage_dimensions,
            "alpha_points": len(self._alpha_axis),
            "beta_points": len(self._beta_axis),
            "mach_points": len(self._mach_axis),
            "reynolds_points": len(self._reynolds_axis),
        }


@dataclass
class LoadResult:
    success: bool
    database_id: str
    message: str
    coefficient_count: int = 0
    is_partial_coverage: bool = False


@dataclass
class SwitchResult:
    success: bool
    previous_database_id: str | None
    new_database_id: str | None
    message: str


@dataclass
class HotReloadResult:
    success: bool
    database_id: str
    message: str
    old_version_active: bool = False


@dataclass
class IntegrityCheck:
    is_valid: bool
    database_id: str
    nan_count: int = 0
    inf_count: int = 0
    negative_drag_count: int = 0
    warnings: list[str] = field(default_factory=list)


class AerodynamicDatabase(IPhysicsModelPlugin):

    def __init__(self, database_id: str = "", database_name: str = ""):
        self.database_id = database_id
        self.database_name = database_name
        self.loaded_databases: dict[str, FourDimLookupTable] = {}
        self.active_database_id: str | None = None
        self.import_adapter_registry: dict[str, Any] = {}
        self.fallback_to_linearized: bool = True
        self._params: dict[str, Any] = {}
        self._wingspan: float = 10.0
        self._wing_area: float = 16.0
        self._chord_length: float = 1.6
        self._time: float = 0.0
        self._linearized_state: DOF6State = DOF6State()
        self._last_coefficients: AeroCoefficients = AeroCoefficients()
        self._cfd_surrogate_ref: Any = None
        self._cfd_surrogate_fallback_events: list[dict] = []

    def initialize(self, params: dict[str, Any]) -> None:
        self._params = params
        self._wingspan = params.get("wingspan", 10.0)
        self._wing_area = params.get("wing_area", 16.0)
        self._chord_length = params.get("chord_length", 1.6)
        self._time = 0.0
        self._linearized_state = DOF6State(
            position=[0.0, 0.0, params.get("initial_altitude", 1000.0)],
            velocity=[params.get("initial_speed", 50.0), 0.0, 0.0],
            attitude=[0.0, 0.0, 0.0],
            angular_rates=[0.0, 0.0, 0.0],
        )

    def step(self, dt: float, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        inputs = inputs or {}
        if self.active_database_id and self.active_database_id in self.loaded_databases:
            return self._step_with_database(dt, inputs)
        if self.fallback_to_linearized:
            return self._step_linearized_fallback(dt, inputs)
        return {"error": "No aerodynamic database loaded and fallback disabled"}

    def _step_with_database(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        alpha = inputs.get("alpha", 0.0)
        beta = inputs.get("beta", 0.0)
        mach = inputs.get("mach", 0.0)
        reynolds = inputs.get("reynolds", 1e7)

        coeffs = self.query_coefficients(alpha, beta, mach, reynolds)
        self._last_coefficients = coeffs

        rho = inputs.get("air_density", self._isa_density(inputs.get("altitude", 1000.0)))
        V = inputs.get("airspeed", 50.0)
        q_s = 0.5 * rho * V ** 2 * self._wing_area

        L = q_s * coeffs.CL
        D = q_s * coeffs.CD
        Y = q_s * coeffs.CY
        M = q_s * self._chord_length * coeffs.CM
        N = q_s * self._wingspan * coeffs.Cn
        l = q_s * self._wingspan * coeffs.Cl

        self._time += dt

        return {
            "aero_coefficients": coeffs,
            "forces": [0.0, Y, L],
            "moments": [l, M, N],
            "drag_force": D,
            "is_extrapolated": coeffs.is_extrapolated,
            "extrapolation_warning": coeffs.extrapolation_warning,
            "time": self._time,
        }

    def _step_linearized_fallback(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        m = self._params.get("mass", 1500.0)
        S = self._wing_area
        V = max(math.sqrt(sum(v ** 2 for v in self._linearized_state.velocity)), 1.0)
        rho = self._isa_density(self._linearized_state.position[2])
        q_s = 0.5 * rho * V ** 2 * S

        alpha = self._compute_alpha_from_state()
        CL_alpha = self._params.get("CL_alpha", 5.0)
        CD_0 = self._params.get("CD_0", 0.02)
        k = self._params.get("k_induced", 0.05)

        CL = CL_alpha * alpha
        CD = CD_0 + k * CL ** 2
        CY = 0.0
        CM = self._params.get("Cm_alpha", -0.5) * alpha
        Cl = 0.0
        Cn = 0.0

        elevator = inputs.get("elevator_cmd", 0.0)
        CL += elevator * 0.01

        L = q_s * CL
        D = q_s * CD
        Y = q_s * CY
        M_moment = q_s * self._chord_length * CM
        N_moment = q_s * self._wingspan * Cn
        l_moment = q_s * self._wingspan * Cl

        T = inputs.get("thrust", self._params.get("max_thrust", 5000.0))
        phi, theta, psi = self._linearized_state.attitude
        u, v, w = self._linearized_state.velocity
        p, q, r = self._linearized_state.angular_rates

        du = (T * math.cos(alpha) - D) / m - q * w + r * v
        dv = 0.0 - r * u + p * w
        dw = (-T * math.sin(alpha) + L - m * 9.81 * math.cos(theta)) / m - p * v + q * u

        u_new = u + du * dt
        v_new = v + dv * dt
        w_new = w + dw * dt

        x_new = self._linearized_state.position[0] + u_new * dt
        y_new = self._linearized_state.position[1] + v_new * dt
        z_new = self._linearized_state.position[2] - w_new * dt

        self._linearized_state = DOF6State(
            position=[x_new, y_new, z_new],
            velocity=[u_new, v_new, w_new],
            attitude=self._linearized_state.attitude,
            angular_rates=self._linearized_state.angular_rates,
        )
        self._time += dt

        fallback_coeffs = AeroCoefficients(CL=CL, CD=CD, CM=CM, CY=CY, Cl=Cl, Cn=Cn)

        warnings.warn(
            "AerodynamicDatabase: Fallback to v3.0 linearized model — no database loaded",
            stacklevel=2,
        )

        return {
            "aero_coefficients": fallback_coeffs,
            "forces": [0.0, Y, L],
            "moments": [l_moment, M_moment, N_moment],
            "drag_force": D,
            "is_fallback": True,
            "fallback_reason": "No aerodynamic database loaded",
            "time": self._time,
        }

    def query_coefficients(
        self, alpha: float, beta: float, mach: float, reynolds: float
    ) -> AeroCoefficients:
        if self._cfd_surrogate_ref is not None:
            try:
                from src.domain.services.generative_design.cfd_surrogate_model_service import FlightCondition
                condition = FlightCondition(
                    alpha=alpha, beta=beta, mach=mach, reynolds=reynolds,
                )
                prediction = self._cfd_surrogate_ref.predict_aero_coefficients(condition)
                if prediction.confidence >= 0.85 and not prediction.is_fallback:
                    return AeroCoefficients(
                        CL=prediction.CL, CD=prediction.CD, CM=prediction.CM,
                        CY=prediction.CY, Cl=prediction.Cl, Cn=prediction.Cn,
                        is_extrapolated=False,
                        extrapolation_warning="CFD surrogate model prediction",
                    )
                else:
                    self._cfd_surrogate_fallback_events.append({
                        "model_id": self._cfd_surrogate_ref.get_active_model_id(),
                        "alpha": alpha, "beta": beta, "mach": mach, "reynolds": reynolds,
                        "confidence": prediction.confidence,
                        "fallback_reason": prediction.fallback_reason,
                    })
            except Exception:
                self._cfd_surrogate_fallback_events.append({
                    "alpha": alpha, "beta": beta, "mach": mach, "reynolds": reynolds,
                    "fallback_reason": "Surrogate model exception",
                })

        if not self.active_database_id or self.active_database_id not in self.loaded_databases:
            if self.fallback_to_linearized:
                return self._linearized_query(alpha, beta, mach, reynolds)
            raise ValueError("No active aerodynamic database loaded")
        table = self.loaded_databases[self.active_database_id]
        return table.query_all(alpha, beta, mach, reynolds)

    def _linearized_query(
        self, alpha: float, beta: float, mach: float, reynolds: float
    ) -> AeroCoefficients:
        CL_alpha = self._params.get("CL_alpha", 5.0)
        CD_0 = self._params.get("CD_0", 0.02)
        k = self._params.get("k_induced", 0.05)
        Cm_alpha = self._params.get("Cm_alpha", -0.5)

        CL = CL_alpha * alpha
        CD = CD_0 + k * CL ** 2
        CM = Cm_alpha * alpha
        CY = 0.0
        Cl = 0.0
        Cn = 0.0

        return AeroCoefficients(
            CL=CL, CD=CD, CM=CM, CY=CY, Cl=Cl, Cn=Cn,
            is_extrapolated=True,
            extrapolation_warning="Linearized fallback — no database loaded",
        )

    def set_cfd_surrogate_ref(self, surrogate_service: Any) -> None:
        self._cfd_surrogate_ref = surrogate_service

    def get_fallback_events(self) -> list[dict]:
        return list(self._cfd_surrogate_fallback_events)

    def clear_fallback_events(self) -> None:
        self._cfd_surrogate_fallback_events.clear()

    def load_database(
        self,
        database_id: str,
        database_name: str,
        alpha_range: tuple[float, float],
        alpha_resolution: float,
        beta_range: tuple[float, float],
        beta_resolution: float,
        mach_range: tuple[float, float],
        mach_resolution: float,
        reynolds_range: tuple[float, float],
        reynolds_resolution: float,
        coefficient_data: dict[str, np.ndarray] | None = None,
        coefficient_types: list[str] | None = None,
        data_source: str = "internal",
        quality_status: str = "draft",
        applicable_config: str = "",
        partial_coverage_dimensions: list[str] | None = None,
    ) -> LoadResult:
        table = FourDimLookupTable(
            database_id=database_id,
            database_name=database_name,
            alpha_range=alpha_range,
            alpha_resolution=alpha_resolution,
            beta_range=beta_range,
            beta_resolution=beta_resolution,
            mach_range=mach_range,
            mach_resolution=mach_resolution,
            reynolds_range=reynolds_range,
            reynolds_resolution=reynolds_resolution,
            coefficient_types=coefficient_types,
            data_source=data_source,
            quality_status=quality_status,
            applicable_config=applicable_config,
            partial_coverage_dimensions=partial_coverage_dimensions,
        )

        if coefficient_data:
            for coeff_type, data in coefficient_data.items():
                integrity = self._check_array_integrity(data, coeff_type)
                if not integrity["is_valid"]:
                    return LoadResult(
                        success=False,
                        database_id=database_id,
                        message=f"Data integrity check failed for {coeff_type}: {integrity['reason']}",
                    )
                table.set_coefficient_data(coeff_type, data)

        total_points = 1
        for ct in table.coefficient_types:
            total_points = len(table._alpha_axis) * len(table._beta_axis) * len(table._mach_axis) * len(table._reynolds_axis)
            break

        self.loaded_databases[database_id] = table

        if self.active_database_id is None:
            self.active_database_id = database_id

        return LoadResult(
            success=True,
            database_id=database_id,
            message=f"Database '{database_name}' loaded successfully with {total_points} points per coefficient",
            coefficient_count=total_points * len(table.coefficient_types),
            is_partial_coverage=table.is_partial_coverage,
        )

    def load_database_from_table(self, table: FourDimLookupTable) -> LoadResult:
        integrity = self.validate_data_integrity(table.database_id)
        if not integrity.is_valid and integrity.nan_count > 0:
            return LoadResult(
                success=False,
                database_id=table.database_id,
                message=f"Data integrity check failed: {integrity.nan_count} NaN values, {integrity.inf_count} Inf values",
            )

        self.loaded_databases[table.database_id] = table

        if self.active_database_id is None:
            self.active_database_id = table.database_id

        total_points = len(table._alpha_axis) * len(table._beta_axis) * len(table._mach_axis) * len(table._reynolds_axis)

        return LoadResult(
            success=True,
            database_id=table.database_id,
            message=f"Database '{table.database_name}' loaded from table object",
            coefficient_count=total_points * len(table.coefficient_types),
            is_partial_coverage=table.is_partial_coverage,
        )

    def switch_database(self, database_id: str) -> SwitchResult:
        if database_id not in self.loaded_databases:
            return SwitchResult(
                success=False,
                previous_database_id=self.active_database_id,
                new_database_id=None,
                message=f"Database '{database_id}' not found in loaded databases",
            )

        previous = self.active_database_id
        self.active_database_id = database_id

        return SwitchResult(
            success=True,
            previous_database_id=previous,
            new_database_id=database_id,
            message=f"Switched from '{previous}' to '{database_id}'",
        )

    def hot_reload_database(
        self, database_id: str, new_table: FourDimLookupTable
    ) -> HotReloadResult:
        if database_id not in self.loaded_databases:
            return HotReloadResult(
                success=False,
                database_id=database_id,
                message=f"Database '{database_id}' not found — use load_database first",
            )

        old_table = self.loaded_databases[database_id]
        self.loaded_databases[database_id] = new_table

        return HotReloadResult(
            success=True,
            database_id=database_id,
            message=f"Database '{database_id}' hot-reloaded; in-flight simulations continue with old data until next step",
            old_version_active=True,
        )

    def validate_data_integrity(self, database_id: str) -> IntegrityCheck:
        if database_id not in self.loaded_databases:
            return IntegrityCheck(
                is_valid=False,
                database_id=database_id,
                warnings=[f"Database '{database_id}' not found"],
            )

        table = self.loaded_databases[database_id]
        nan_count = 0
        inf_count = 0
        negative_drag_count = 0
        all_warnings: list[str] = []

        for coeff_type in table.coefficient_types:
            data = table._data.get(coeff_type)
            if data is None:
                all_warnings.append(f"Coefficient type '{coeff_type}' has no data")
                continue

            nan_in_arr = int(np.isnan(data).sum())
            inf_in_arr = int(np.isinf(data).sum())
            nan_count += nan_in_arr
            inf_count += inf_in_arr

            if nan_in_arr > 0:
                all_warnings.append(f"'{coeff_type}' contains {nan_in_arr} NaN values")
            if inf_in_arr > 0:
                all_warnings.append(f"'{coeff_type}' contains {inf_in_arr} Inf values")

            if coeff_type == "CD":
                neg_count = int((data < 0).sum())
                negative_drag_count += neg_count
                if neg_count > 0:
                    all_warnings.append(f"'CD' contains {neg_count} negative drag values (physically invalid)")

        is_valid = nan_count == 0 and inf_count == 0 and negative_drag_count == 0

        return IntegrityCheck(
            is_valid=is_valid,
            database_id=database_id,
            nan_count=nan_count,
            inf_count=inf_count,
            negative_drag_count=negative_drag_count,
            warnings=all_warnings,
        )

    def get_state(self) -> dict[str, Any]:
        active_meta = None
        if self.active_database_id and self.active_database_id in self.loaded_databases:
            active_meta = self.loaded_databases[self.active_database_id].metadata

        return {
            "database_id": self.database_id,
            "database_name": self.database_name,
            "active_database_id": self.active_database_id,
            "loaded_database_ids": list(self.loaded_databases.keys()),
            "fallback_to_linearized": self.fallback_to_linearized,
            "last_coefficients": {
                "CL": self._last_coefficients.CL,
                "CD": self._last_coefficients.CD,
                "CM": self._last_coefficients.CM,
                "CY": self._last_coefficients.CY,
                "Cl": self._last_coefficients.Cl,
                "Cn": self._last_coefficients.Cn,
                "is_extrapolated": self._last_coefficients.is_extrapolated,
            },
            "active_database_metadata": active_meta,
            "time": self._time,
        }

    def reset(self) -> None:
        self._time = 0.0
        self._linearized_state = DOF6State()
        self._last_coefficients = AeroCoefficients()

    def get_supported_fidelities(self) -> list[str]:
        return [FidelityLevel.Low.value, FidelityLevel.Mid.value, FidelityLevel.High.value]

    def get_schema_references(self) -> list[str]:
        return ["AircraftGeometry"]

    def validate_numerical_stability(self) -> StabilityCheck:
        if not self.active_database_id or self.active_database_id not in self.loaded_databases:
            return StabilityCheck(
                is_stable=True,
                message="No database loaded — linearized fallback has no numerical stability issues",
            )

        integrity = self.validate_data_integrity(self.active_database_id)
        if not integrity.is_valid:
            return StabilityCheck(
                is_stable=False,
                message=f"Data integrity issues in active database: {'; '.join(integrity.warnings)}",
            )

        return StabilityCheck(is_stable=True, message="Active database passes integrity checks")

    @staticmethod
    def _isa_density(altitude: float) -> float:
        if altitude < 0:
            altitude = 0.0
        T0 = 288.15
        P0 = 101325.0
        L = 0.0065
        g = 9.80665
        R = 287.058
        if altitude <= 11000.0:
            T = T0 - L * altitude
            P = P0 * (T / T0) ** (g / (L * R))
        else:
            T11 = T0 - L * 11000.0
            P11 = P0 * (T11 / T0) ** (g / (L * R))
            T = T11
            P = P11 * math.exp(-g * (altitude - 11000.0) / (R * T11))
        return P / (R * T)

    def _compute_alpha_from_state(self) -> float:
        u, v, w = self._linearized_state.velocity
        V = math.sqrt(u ** 2 + v ** 2 + w ** 2)
        if V < 1e-6:
            return 0.0
        return math.atan2(w, u)

    @staticmethod
    def _check_array_integrity(data: np.ndarray, coeff_type: str) -> dict[str, Any]:
        nan_count = int(np.isnan(data).sum())
        inf_count = int(np.isinf(data).sum())
        if nan_count > 0:
            return {"is_valid": False, "reason": f"{nan_count} NaN values in {coeff_type}"}
        if inf_count > 0:
            return {"is_valid": False, "reason": f"{inf_count} Inf values in {coeff_type}"}
        if coeff_type == "CD" and int((data < 0).sum()) > 0:
            return {"is_valid": False, "reason": f"Negative drag coefficients in {coeff_type}"}
        return {"is_valid": True, "reason": ""}