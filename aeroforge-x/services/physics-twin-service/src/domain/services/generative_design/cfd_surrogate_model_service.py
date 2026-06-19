"""AeroForge-X v5.0 CFDSurrogateModelService

Manages CFD surrogate model lifecycle: training, inference, online update,
model switching, hot-swap, and degradation fallback to v4.0 FourDimLookupTable.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any


class Architecture(str, Enum):
    PINN = "PINN"
    DEEPONET = "DeepONet"
    TRANSFORMER = "Transformer"


class QualityStatus(str, Enum):
    TRAINING = "Training"
    VALIDATED = "Validated"
    DEPRECATED = "Deprecated"


@dataclass(frozen=True)
class FlightCondition:
    alpha: float
    beta: float
    mach: float
    reynolds: float
    altitude: float = 0.0
    dynamic_pressure: float = 0.0


@dataclass(frozen=True)
class AeroCoefficientsPrediction:
    CL: float
    CD: float
    CM: float
    CY: float = 0.0
    Cl: float = 0.0
    Cn: float = 0.0
    confidence: float = 1.0
    prediction_interval: dict = field(default_factory=dict)
    is_fallback: bool = False
    fallback_reason: str = ""


@dataclass(frozen=True)
class SurrogateModelSpec:
    model_id: str
    architecture: Architecture
    input_dimensions: list[str] = field(default_factory=lambda: ["alpha", "beta", "mach", "reynolds"])
    output_dimensions: list[str] = field(default_factory=lambda: ["CL", "CD", "CM", "CY", "Cl", "Cn"])
    training_dataset_ref: str = ""
    model_weights_ref: str = ""
    quality_status: QualityStatus = QualityStatus.TRAINING


@dataclass(frozen=True)
class ModelQualityMetrics:
    model_id: str
    r_squared: float
    rmse: dict
    prediction_interval_coverage: float
    test_set_size: int
    last_validated_at: Optional[str] = None


@dataclass(frozen=True)
class TrainingResult:
    model_id: str
    success: bool
    r_squared: float
    rmse: dict
    training_duration_s: float
    message: str = ""


@dataclass(frozen=True)
class UpdateResult:
    model_id: str
    success: bool
    previous_r_squared: float
    new_r_squared: float
    message: str = ""


@dataclass(frozen=True)
class SwitchResult:
    previous_model_id: str
    new_model_id: str
    success: bool


@dataclass(frozen=True)
class HotSwapResult:
    model_id: str
    success: bool
    previous_weights_ref: str
    new_weights_ref: str


@dataclass
class SurrogateModelRegistry:
    registry_id: str
    registered_models: dict[str, SurrogateModelSpec] = field(default_factory=dict)
    active_model_id: Optional[str] = None
    fallback_model_id: Optional[str] = None


class CFDSurrogateModelService:

    def __init__(self, fallback_lookup_table: Any = None) -> None:
        self._registry = SurrogateModelRegistry(
            registry_id=f"SMR-{uuid.uuid4().hex[:8].upper()}",
        )
        self._fallback_table = fallback_lookup_table
        self._quality_metrics: dict[str, ModelQualityMetrics] = {}
        self._model_weights: dict[str, Any] = {}
        self._consecutive_failures: dict[str, int] = {}
        self._circuit_open: dict[str, bool] = {}
        self._circuit_open_time: dict[str, float] = {}
        self._CIRCUIT_THRESHOLD = 3
        self._CIRCUIT_RECOVERY_S = 300.0

    def train_model(
        self,
        spec: SurrogateModelSpec,
        dataset_path: str,
    ) -> TrainingResult:
        start = time.time()
        model_id = spec.model_id

        self._registry.registered_models[model_id] = spec

        r_squared = 0.0
        rmse = {}
        try:
            r_squared, rmse = self._simulate_training(spec, dataset_path)
            quality = QualityStatus.VALIDATED if r_squared >= 0.95 else QualityStatus.TRAINING

            updated_spec = SurrogateModelSpec(
                model_id=spec.model_id,
                architecture=spec.architecture,
                input_dimensions=spec.input_dimensions,
                output_dimensions=spec.output_dimensions,
                training_dataset_ref=dataset_path,
                model_weights_ref=f"aeroforge/models/{model_id}/weights.pt",
                quality_status=quality,
            )
            self._registry.registered_models[model_id] = updated_spec

            self._quality_metrics[model_id] = ModelQualityMetrics(
                model_id=model_id,
                r_squared=r_squared,
                rmse=rmse,
                prediction_interval_coverage=0.90,
                test_set_size=1000,
                last_validated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

            if self._registry.active_model_id is None and quality == QualityStatus.VALIDATED:
                self._registry.active_model_id = model_id

            duration = time.time() - start
            return TrainingResult(
                model_id=model_id,
                success=True,
                r_squared=r_squared,
                rmse=rmse,
                training_duration_s=duration,
            )
        except Exception as e:
            duration = time.time() - start
            return TrainingResult(
                model_id=model_id,
                success=False,
                r_squared=0.0,
                rmse={},
                training_duration_s=duration,
                message=str(e),
            )

    def predict_aero_coefficients(
        self,
        condition: FlightCondition,
    ) -> AeroCoefficientsPrediction:
        active_id = self._registry.active_model_id

        if active_id is not None and not self._is_circuit_open(active_id):
            spec = self._registry.registered_models.get(active_id)
            if spec is not None and spec.quality_status == QualityStatus.VALIDATED:
                try:
                    prediction = self._simulate_inference(active_id, condition)
                    if prediction.confidence >= 0.85:
                        self._consecutive_failures[active_id] = 0
                        return prediction
                    else:
                        return self._fallback_predict(condition, f"Low confidence: {prediction.confidence:.3f}")
                except Exception:
                    self._record_failure(active_id)
                    if self._consecutive_failures.get(active_id, 0) >= self._CIRCUIT_THRESHOLD:
                        self._open_circuit(active_id)
                    return self._fallback_predict(condition, "Surrogate model inference failed")

        return self._fallback_predict(condition, "No active surrogate model available")

    def online_update(self, model_id: str, new_data_path: str) -> UpdateResult:
        spec = self._registry.registered_models.get(model_id)
        if spec is None:
            return UpdateResult(
                model_id=model_id,
                success=False,
                previous_r_squared=0.0,
                new_r_squared=0.0,
                message=f"Model {model_id} not found",
            )

        metrics = self._quality_metrics.get(model_id)
        previous_r2 = metrics.r_squared if metrics else 0.0

        new_r2, _ = self._simulate_training(spec, new_data_path)

        if new_r2 > previous_r2:
            updated_spec = SurrogateModelSpec(
                model_id=spec.model_id,
                architecture=spec.architecture,
                input_dimensions=spec.input_dimensions,
                output_dimensions=spec.output_dimensions,
                training_dataset_ref=new_data_path,
                model_weights_ref=spec.model_weights_ref,
                quality_status=QualityStatus.VALIDATED,
            )
            self._registry.registered_models[model_id] = updated_spec

            self._quality_metrics[model_id] = ModelQualityMetrics(
                model_id=model_id,
                r_squared=new_r2,
                rmse=metrics.rmse if metrics else {},
                prediction_interval_coverage=0.92,
                test_set_size=(metrics.test_set_size if metrics else 0) + 100,
                last_validated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        return UpdateResult(
            model_id=model_id,
            success=True,
            previous_r_squared=previous_r2,
            new_r_squared=new_r2,
        )

    def get_model_quality_metrics(self, model_id: str) -> Optional[ModelQualityMetrics]:
        return self._quality_metrics.get(model_id)

    def switch_model(self, model_id: str) -> SwitchResult:
        spec = self._registry.registered_models.get(model_id)
        if spec is None:
            return SwitchResult(
                previous_model_id=self._registry.active_model_id or "",
                new_model_id=model_id,
                success=False,
            )

        if spec.quality_status != QualityStatus.VALIDATED:
            return SwitchResult(
                previous_model_id=self._registry.active_model_id or "",
                new_model_id=model_id,
                success=False,
            )

        previous = self._registry.active_model_id or ""
        self._registry.active_model_id = model_id
        return SwitchResult(
            previous_model_id=previous,
            new_model_id=model_id,
            success=True,
        )

    def hot_swap_model(self, model_id: str, new_model_path: str) -> HotSwapResult:
        spec = self._registry.registered_models.get(model_id)
        if spec is None:
            return HotSwapResult(
                model_id=model_id,
                success=False,
                previous_weights_ref="",
                new_weights_ref=new_model_path,
            )

        previous_ref = spec.model_weights_ref
        updated_spec = SurrogateModelSpec(
            model_id=spec.model_id,
            architecture=spec.architecture,
            input_dimensions=spec.input_dimensions,
            output_dimensions=spec.output_dimensions,
            training_dataset_ref=spec.training_dataset_ref,
            model_weights_ref=new_model_path,
            quality_status=spec.quality_status,
        )
        self._registry.registered_models[model_id] = updated_spec

        return HotSwapResult(
            model_id=model_id,
            success=True,
            previous_weights_ref=previous_ref,
            new_weights_ref=new_model_path,
        )

    def get_active_model_id(self) -> Optional[str]:
        return self._registry.active_model_id

    def _simulate_training(
        self,
        spec: SurrogateModelSpec,
        dataset_path: str,
    ) -> tuple[float, dict[str, float]]:
        r_squared = 0.96 + (hash(spec.model_id) % 100) / 10000.0
        rmse = {
            "CL": 0.005 + (hash(spec.model_id) % 10) / 10000.0,
            "CD": 0.002 + (hash(spec.model_id) % 10) / 10000.0,
            "CM": 0.003 + (hash(spec.model_id) % 10) / 10000.0,
        }
        return r_squared, rmse

    def _simulate_inference(
        self,
        model_id: str,
        condition: FlightCondition,
    ) -> AeroCoefficientsPrediction:
        alpha = condition.alpha
        beta = condition.beta
        mach = condition.mach

        cl = 2 * 3.14159265 * alpha / 180.0 * (1.0 + 0.05 * mach)
        cd = 0.02 + 0.05 * alpha / 180.0 + 0.1 * (alpha / 180.0) ** 2
        cm = -0.5 * alpha / 180.0
        cy = -0.01 * beta / 180.0

        confidence = 0.95 - 0.001 * abs(alpha) - 0.002 * abs(beta) - 0.01 * abs(mach)

        return AeroCoefficientsPrediction(
            CL=cl,
            CD=cd,
            CM=cm,
            CY=cy,
            Cl=0.0,
            Cn=0.0,
            confidence=max(0.0, confidence),
            is_fallback=False,
        )

    def _fallback_predict(
        self,
        condition: FlightCondition,
        reason: str,
    ) -> AeroCoefficientsPrediction:
        if self._fallback_table is not None:
            try:
                result = self._fallback_table.query_coefficients(
                    alpha=condition.alpha,
                    beta=condition.beta,
                    mach=condition.mach,
                    reynolds=condition.reynolds,
                )
                if hasattr(result, "CL"):
                    return AeroCoefficientsPrediction(
                        CL=result.CL,
                        CD=result.CD,
                        CM=result.CM,
                        confidence=0.7,
                        is_fallback=True,
                        fallback_reason=reason,
                    )
            except Exception:
                pass

        alpha = condition.alpha
        beta = condition.beta
        return AeroCoefficientsPrediction(
            CL=2 * 3.14159265 * alpha / 180.0,
            CD=0.02 + 0.05 * alpha / 180.0,
            CM=-0.5 * alpha / 180.0,
            CY=-0.01 * beta / 180.0,
            confidence=0.5,
            is_fallback=True,
            fallback_reason=reason,
        )

    def _is_circuit_open(self, model_id: str) -> bool:
        if not self._circuit_open.get(model_id, False):
            return False
        open_time = self._circuit_open_time.get(model_id, 0.0)
        if time.time() - open_time > self._CIRCUIT_RECOVERY_S:
            self._circuit_open[model_id] = False
            self._consecutive_failures[model_id] = 0
            return False
        return True

    def _record_failure(self, model_id: str) -> None:
        self._consecutive_failures[model_id] = self._consecutive_failures.get(model_id, 0) + 1

    def _open_circuit(self, model_id: str) -> None:
        self._circuit_open[model_id] = True
        self._circuit_open_time[model_id] = time.time()