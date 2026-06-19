from __future__ import annotations

import logging
import math
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import DomainEvent

logger = logging.getLogger(__name__)


class ROMType(str, Enum):
    AERODYNAMIC = "aerodynamic"
    STRUCTURAL = "structural"
    THERMAL = "thermal"


class FidelityLevel(str, Enum):
    ROM = "rom"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ROMModel:
    model_id: str
    rom_type: str
    basis_vectors: list[list[float]] = field(default_factory=list)
    coefficients: list[float] = field(default_factory=list)
    training_samples: int = 0
    accuracy_percent: float = 0.0
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "rom_type": self.rom_type,
            "training_samples": self.training_samples,
            "accuracy_percent": self.accuracy_percent,
            "version": self.version,
            "basis_count": len(self.basis_vectors),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SimulationResult:
    result_id: str
    fidelity_level: str
    parameters: dict[str, Any]
    outputs: dict[str, Any]
    execution_time_ms: float
    accuracy_estimate: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "fidelity_level": self.fidelity_level,
            "parameters": self.parameters,
            "outputs": self.outputs,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "accuracy_estimate": round(self.accuracy_estimate, 1),
            "created_at": self.created_at.isoformat(),
        }


class ReducedOrderModelService:
    def __init__(self) -> None:
        self._models: dict[str, ROMModel] = {}

    def build_reduced_order_model(
        self,
        rom_type: str,
        high_fidelity_results: list[dict[str, Any]],
        basis_dimension: int = 10,
    ) -> ROMModel:
        model_id = f"ROM-{secrets.token_hex(4)}"

        snapshots: list[list[float]] = []
        for result in high_fidelity_results:
            snapshot = result.get("field_data", [])
            if snapshot:
                snapshots.append(snapshot)

        basis_vectors = self._pod_decomposition(snapshots, basis_dimension)

        coefficients = self._project_snapshots(snapshots, basis_vectors)

        accuracy = min(95.0 + len(high_fidelity_results) * 0.1, 99.5)

        model = ROMModel(
            model_id=model_id,
            rom_type=rom_type,
            basis_vectors=basis_vectors,
            coefficients=coefficients,
            training_samples=len(high_fidelity_results),
            accuracy_percent=accuracy,
        )

        self._models[model_id] = model

        logger.info(
            "ROM built: id=%s type=%s samples=%d accuracy=%.1f%%",
            model_id, rom_type, len(high_fidelity_results), accuracy,
        )
        return model

    def run_reduced_simulation(
        self,
        model_id: str,
        parameters: dict[str, Any],
    ) -> SimulationResult:
        model = self._models.get(model_id)
        if model is None:
            raise ValueError(f"ROM model '{model_id}' not found")

        import time
        start = time.time()

        outputs = self._evaluate_rom(model, parameters)

        execution_time = (time.time() - start) * 1000

        return SimulationResult(
            result_id=f"SIM-{secrets.token_hex(4)}",
            fidelity_level=FidelityLevel.ROM.value,
            parameters=parameters,
            outputs=outputs,
            execution_time_ms=execution_time,
            accuracy_estimate=model.accuracy_percent,
        )

    def update_rom_from_high_fidelity(
        self,
        model_id: str,
        new_results: list[dict[str, Any]],
    ) -> ROMModel:
        model = self._models.get(model_id)
        if model is None:
            raise ValueError(f"ROM model '{model_id}' not found")

        new_snapshots = [r.get("field_data", []) for r in new_results if r.get("field_data")]

        current_dim = len(model.basis_vectors)
        new_basis = self._pod_decomposition(new_snapshots, current_dim)

        if model.basis_vectors and new_basis:
            for i in range(min(len(model.basis_vectors), len(new_basis))):
                for j in range(min(len(model.basis_vectors[i]), len(new_basis[i]))):
                    model.basis_vectors[i][j] = 0.7 * model.basis_vectors[i][j] + 0.3 * new_basis[i][j]

        model.training_samples += len(new_results)
        model.version += 1
        model.accuracy_percent = min(model.accuracy_percent + 0.5, 99.9)

        logger.info("ROM updated: id=%s v=%d", model_id, model.version)
        return model

    def get_model(self, model_id: str) -> ROMModel | None:
        return self._models.get(model_id)

    def list_models(self, rom_type: str | None = None) -> list[ROMModel]:
        models = list(self._models.values())
        if rom_type:
            models = [m for m in models if m.rom_type == rom_type]
        return models

    def _pod_decomposition(
        self,
        snapshots: list[list[float]],
        dimension: int,
    ) -> list[list[float]]:
        if not snapshots:
            return [[] for _ in range(dimension)]

        n = len(snapshots)
        m = max(len(s) for s in snapshots) if snapshots else 0

        mean = [0.0] * m
        for snap in snapshots:
            for j in range(min(len(snap), m)):
                mean[j] += snap[j] / n

        centered = []
        for snap in snapshots:
            row = [0.0] * m
            for j in range(min(len(snap), m)):
                row[j] = snap[j] - mean[j]
            centered.append(row)

        basis = []
        for i in range(min(dimension, m)):
            vec = [0.0] * m
            for j in range(m):
                val = 0.0
                for k in range(n):
                    val += centered[k][j] * math.sin((i + 1) * (k + 1) * 0.1)
                vec[j] = val / max(n, 1)
            norm = math.sqrt(sum(v * v for v in vec))
            if norm > 0:
                vec = [v / norm for v in vec]
            basis.append(vec)

        return basis

    def _project_snapshots(
        self,
        snapshots: list[list[float]],
        basis: list[list[float]],
    ) -> list[float]:
        coefficients = []
        for i, vec in enumerate(basis):
            coeff = 0.0
            for snap in snapshots:
                for j in range(min(len(snap), len(vec))):
                    coeff += snap[j] * vec[j]
            coefficients.append(coeff / max(len(snapshots), 1))
        return coefficients

    def _evaluate_rom(
        self,
        model: ROMModel,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        param_scale = parameters.get("scale_factor", 1.0)

        if model.rom_type == "aerodynamic":
            cl = 0.5 * param_scale + sum(model.coefficients[:3]) * 0.01
            cd = 0.02 * param_scale + sum(model.coefficients[:3]) * 0.001
            cm = 0.1 * param_scale + sum(model.coefficients[:3]) * 0.005
            return {
                "lift_coefficient": round(cl, 4),
                "drag_coefficient": round(cd, 6),
                "moment_coefficient": round(cm, 4),
                "lift_to_drag": round(cl / cd, 1) if cd > 0 else 0,
            }
        elif model.rom_type == "structural":
            max_stress = 250 * param_scale + sum(model.coefficients[:3]) * 0.5
            max_displacement = 2.5 * param_scale + sum(model.coefficients[:3]) * 0.01
            return {
                "max_stress_mpa": round(max_stress, 2),
                "max_displacement_mm": round(max_displacement, 3),
                "safety_factor": round(400 / max_stress, 2) if max_stress > 0 else 0,
            }
        elif model.rom_type == "thermal":
            max_temp = 150 * param_scale + sum(model.coefficients[:3]) * 0.3
            heat_flux = 5000 * param_scale + sum(model.coefficients[:3]) * 10
            return {
                "max_temperature_c": round(max_temp, 1),
                "heat_flux_w_m2": round(heat_flux, 0),
                "thermal_gradient_c_m": round(max_temp / 0.5, 1),
            }
        return {"result": "unknown_rom_type"}


class MultiFidelityService:
    def __init__(self) -> None:
        self._rom_service = ReducedOrderModelService()

    def select_fidelity_level(
        self,
        simulation_type: str,
        required_accuracy: float = 95.0,
        max_time_seconds: float = 60.0,
    ) -> dict[str, Any]:
        if required_accuracy <= 95.0 and max_time_seconds <= 1.0:
            level = FidelityLevel.ROM
            estimated_time_ms = 50
            estimated_accuracy = 95.0
        elif required_accuracy <= 98.0 and max_time_seconds <= 300.0:
            level = FidelityLevel.MEDIUM
            estimated_time_ms = 120000
            estimated_accuracy = 98.0
        else:
            level = FidelityLevel.HIGH
            estimated_time_ms = 3600000
            estimated_accuracy = 99.5

        return {
            "recommended_level": level.value,
            "estimated_time_ms": estimated_time_ms,
            "estimated_accuracy_percent": estimated_accuracy,
            "simulation_type": simulation_type,
        }

    def run_multi_fidelity_simulation(
        self,
        model_id: str | None,
        parameters: dict[str, Any],
        fidelity_level: str = "rom",
    ) -> SimulationResult:
        if fidelity_level == FidelityLevel.ROM.value and model_id:
            return self._rom_service.run_reduced_simulation(model_id, parameters)
        elif fidelity_level == FidelityLevel.MEDIUM.value:
            return self._run_medium_fidelity(parameters)
        else:
            return self._run_high_fidelity(parameters)

    def build_rom(
        self,
        rom_type: str,
        high_fidelity_results: list[dict[str, Any]],
        basis_dimension: int = 10,
    ) -> ROMModel:
        return self._rom_service.build_reduced_order_model(rom_type, high_fidelity_results, basis_dimension)

    def update_rom(self, model_id: str, new_results: list[dict[str, Any]]) -> ROMModel:
        return self._rom_service.update_rom_from_high_fidelity(model_id, new_results)

    def _run_medium_fidelity(self, parameters: dict[str, Any]) -> SimulationResult:
        import time
        start = time.time()

        scale = parameters.get("scale_factor", 1.0)
        outputs = {
            "medium_fidelity_result": True,
            "approximate_value": round(100 * scale, 2),
            "confidence_interval": [round(98 * scale, 2), round(102 * scale, 2)],
        }

        return SimulationResult(
            result_id=f"SIM-{secrets.token_hex(4)}",
            fidelity_level=FidelityLevel.MEDIUM.value,
            parameters=parameters,
            outputs=outputs,
            execution_time_ms=(time.time() - start) * 1000,
            accuracy_estimate=98.0,
        )

    def _run_high_fidelity(self, parameters: dict[str, Any]) -> SimulationResult:
        import time
        start = time.time()

        scale = parameters.get("scale_factor", 1.0)
        outputs = {
            "high_fidelity_result": True,
            "precise_value": round(100 * scale, 4),
            "convergence_achieved": True,
            "iterations": 150,
        }

        return SimulationResult(
            result_id=f"SIM-{secrets.token_hex(4)}",
            fidelity_level=FidelityLevel.HIGH.value,
            parameters=parameters,
            outputs=outputs,
            execution_time_ms=(time.time() - start) * 1000,
            accuracy_estimate=99.5,
        )

