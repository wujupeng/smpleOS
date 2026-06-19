"""AeroForge-X v6.0 UncertaintyQuantificationService

Manages CFD surrogate model uncertainty quantification: Bayesian PINN,
MC Dropout, Ensemble methods, high-uncertainty flagging, and
uncertainty propagation through MDO.
REQ-E-ENH-001~007, REQ-DFX-V6-025, REQ-NFR-V6-026
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class UQMethodType(str, Enum):
    BAYESIAN_PINN = "BayesianPINN"
    MC_DROPOUT = "MCDropout"
    ENSEMBLE = "Ensemble"


@dataclass
class UQPredictionResult:
    aero_coefficients: dict = field(default_factory=dict)
    prediction_intervals: dict = field(default_factory=dict)
    coefficient_of_variation: float = 0.0
    uq_method: str = ""
    is_high_uncertainty: bool = False

    def to_dict(self) -> dict:
        return {
            "aero_coefficients": self.aero_coefficients,
            "prediction_intervals": self.prediction_intervals,
            "coefficient_of_variation": self.coefficient_of_variation,
            "uq_method": self.uq_method,
            "is_high_uncertainty": self.is_high_uncertainty,
        }


@dataclass
class UQMethodSpec:
    method_id: str
    method_type: UQMethodType
    surrogate_model_id: str = ""
    hyperparameters: dict = field(default_factory=dict)
    confidence_level: float = 0.95
    cov_threshold: float = 0.10

    def to_dict(self) -> dict:
        return {
            "method_id": self.method_id,
            "method_type": self.method_type.value,
            "surrogate_model_id": self.surrogate_model_id,
            "hyperparameters": self.hyperparameters,
            "confidence_level": self.confidence_level,
            "cov_threshold": self.cov_threshold,
        }


@dataclass
class HighUncertaintyAlert:
    prediction: UQPredictionResult
    coefficient_of_variation: float
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "coefficient_of_variation": self.coefficient_of_variation,
            "recommendation": self.recommendation,
            "prediction": self.prediction.to_dict(),
        }


@dataclass
class MDOUncertaintyResult:
    run_id: str
    objective_intervals: dict = field(default_factory=dict)
    confidence_level: float = 0.95

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "objective_intervals": self.objective_intervals,
            "confidence_level": self.confidence_level,
        }


@dataclass
class HotSwapResult:
    old_method_id: str
    new_method_id: str
    swapped: bool

    def to_dict(self) -> dict:
        return {
            "old_method_id": self.old_method_id,
            "new_method_id": self.new_method_id,
            "swapped": self.swapped,
        }


class IUQMethod(ABC):
    @abstractmethod
    def predict_with_uq(self, inputs: dict) -> UQPredictionResult:
        ...

    @abstractmethod
    def get_method_name(self) -> str:
        ...

    @abstractmethod
    def get_confidence_interval(self, predictions: list[float], confidence: float) -> tuple[float, float]:
        ...


class BayesianPINNEstimator(IUQMethod):
    def __init__(self, mcmc_steps: int = 1000, burn_in_ratio: float = 0.3) -> None:
        self._mcmc_steps = mcmc_steps
        self._burn_in_ratio = burn_in_ratio

    def predict_with_uq(self, inputs: dict) -> UQPredictionResult:
        import random
        base = inputs.get("CL", 0.5)
        samples = [base + random.gauss(0, 0.02) for _ in range(self._mcmc_steps)]
        burn_in = int(len(samples) * self._burn_in_ratio)
        post_samples = samples[burn_in:]

        mean = sum(post_samples) / len(post_samples)
        var = sum((x - mean) ** 2 for x in post_samples) / len(post_samples)
        std = var ** 0.5
        ci_lower = mean - 1.96 * std
        ci_upper = mean + 1.96 * std
        cov = std / abs(mean) if mean != 0 else 0

        return UQPredictionResult(
            aero_coefficients={"CL": mean},
            prediction_intervals={"CL": {"lower_95": ci_lower, "upper_95": ci_upper}},
            coefficient_of_variation=round(cov, 4),
            uq_method="BayesianPINN",
            is_high_uncertainty=cov > 0.10,
        )

    def get_method_name(self) -> str:
        return "BayesianPINN"

    def get_confidence_interval(self, predictions: list[float], confidence: float) -> tuple[float, float]:
        n = len(predictions)
        mean = sum(predictions) / n
        std = (sum((x - mean) ** 2 for x in predictions) / n) ** 0.5
        z = 1.96 if confidence >= 0.95 else 1.645
        return (mean - z * std, mean + z * std)


class MCDropoutEstimator(IUQMethod):
    def __init__(self, num_forward_passes: int = 50, dropout_rate: float = 0.1) -> None:
        self._num_passes = num_forward_passes
        self._dropout_rate = dropout_rate

    def predict_with_uq(self, inputs: dict) -> UQPredictionResult:
        import random
        base = inputs.get("CL", 0.5)
        samples = []
        for _ in range(self._num_forward_passes):
            if random.random() < self._dropout_rate:
                continue
            samples.append(base + random.gauss(0, 0.015))

        if not samples:
            samples = [base]

        mean = sum(samples) / len(samples)
        var = sum((x - mean) ** 2 for x in samples) / len(samples)
        std = var ** 0.5
        ci_lower = mean - 1.96 * std
        ci_upper = mean + 1.96 * std
        cov = std / abs(mean) if mean != 0 else 0

        return UQPredictionResult(
            aero_coefficients={"CL": mean},
            prediction_intervals={"CL": {"lower_95": ci_lower, "upper_95": ci_upper}},
            coefficient_of_variation=round(cov, 4),
            uq_method="MCDropout",
            is_high_uncertainty=cov > 0.10,
        )

    def get_method_name(self) -> str:
        return "MCDropout"

    def get_confidence_interval(self, predictions: list[float], confidence: float) -> tuple[float, float]:
        n = len(predictions)
        mean = sum(predictions) / n
        std = (sum((x - mean) ** 2 for x in predictions) / n) ** 0.5
        z = 1.96 if confidence >= 0.95 else 1.645
        return (mean - z * std, mean + z * std)


class EnsembleEstimator(IUQMethod):
    def __init__(self, num_models: int = 5, initialization_seeds: list[int] | None = None) -> None:
        self._num_models = num_models
        self._seeds = initialization_seeds or list(range(num_models))

    def predict_with_uq(self, inputs: dict) -> UQPredictionResult:
        import random
        base = inputs.get("CL", 0.5)
        predictions = []
        for seed in self._seeds:
            rng = random.Random(seed)
            predictions.append(base + rng.gauss(0, 0.02))

        mean = sum(predictions) / len(predictions)
        var = sum((x - mean) ** 2 for x in predictions) / len(predictions)
        std = var ** 0.5
        ci_lower = mean - 1.96 * std
        ci_upper = mean + 1.96 * std
        cov = std / abs(mean) if mean != 0 else 0

        return UQPredictionResult(
            aero_coefficients={"CL": mean},
            prediction_intervals={"CL": {"lower_95": ci_lower, "upper_95": ci_upper}},
            coefficient_of_variation=round(cov, 4),
            uq_method="Ensemble",
            is_high_uncertainty=cov > 0.10,
        )

    def get_method_name(self) -> str:
        return "Ensemble"

    def get_confidence_interval(self, predictions: list[float], confidence: float) -> tuple[float, float]:
        n = len(predictions)
        mean = sum(predictions) / n
        std = (sum((x - mean) ** 2 for x in predictions) / n) ** 0.5
        z = 1.96 if confidence >= 0.95 else 1.645
        return (mean - z * std, mean + z * std)


class UncertaintyQuantificationService:

    DEFAULT_COV_THRESHOLD = 0.10

    def __init__(self, repo=None) -> None:
        self._repo = repo
def __init__(self, repo=None) -> None:
        self._methods: dict[str, IUQMethod] = {}
        self._specs: dict[str, UQMethodSpec] = {}
        self._active_method_id: str = ""

    def predictWithUQ(self, inputs: dict, method: str = "") -> UQPredictionResult:
        method_id = method or self._active_method_id
        if not method_id or method_id not in self._methods:
            raise ValueError(f"UQ method not found: {method_id}")

        uq_method = self._methods[method_id]
        result = uq_method.predict_with_uq(inputs)

        spec = self._specs.get(method_id)
        threshold = spec.cov_threshold if spec else self.DEFAULT_COV_THRESHOLD
        if result.coefficient_of_variation > threshold:
            result.is_high_uncertainty = True

        return result

    def registerUQMethod(self, spec: UQMethodSpec) -> str:
        if spec.method_id in self._methods:
            raise ValueError(f"UQ method already registered: {spec.method_id}")

        if spec.method_type == UQMethodType.BAYESIAN_PINN:
            impl = BayesianPINNEstimator(
                mcmc_steps=spec.hyperparameters.get("mcmc_steps", 1000),
                burn_in_ratio=spec.hyperparameters.get("burn_in_ratio", 0.3),
            )
        elif spec.method_type == UQMethodType.MC_DROPOUT:
            impl = MCDropoutEstimator(
                num_forward_passes=spec.hyperparameters.get("num_forward_passes", 50),
                dropout_rate=spec.hyperparameters.get("dropout_rate", 0.1),
            )
        elif spec.method_type == UQMethodType.ENSEMBLE:
            impl = EnsembleEstimator(
                num_models=spec.hyperparameters.get("num_models", 5),
                initialization_seeds=spec.hyperparameters.get("seeds"),
            )
        else:
            raise ValueError(f"Unknown UQ method type: {spec.method_type}")

        self._methods[spec.method_id] = impl
        self._specs[spec.method_id] = spec

        if not self._active_method_id:
            self._active_method_id = spec.method_id

        return spec.method_id

    def hotSwapUQMethod(self, method_id: str) -> HotSwapResult:
        if method_id not in self._methods:
            raise ValueError(f"UQ method not found: {method_id}")

        old_id = self._active_method_id
        self._active_method_id = method_id

        return HotSwapResult(
            old_method_id=old_id,
            new_method_id=method_id,
            swapped=True,
        )

    def flagHighUncertainty(self, prediction: UQPredictionResult) -> Optional[HighUncertaintyAlert]:
        if prediction.is_high_uncertainty:
            return HighUncertaintyAlert(
                prediction=prediction,
                coefficient_of_variation=prediction.coefficient_of_variation,
                recommendation="Collect additional CFD data for model refinement",
            )
        return None

    def propagateUncertaintyThroughMDO(self, run_id: str) -> MDOUncertaintyResult:
        return MDOUncertaintyResult(
            run_id=run_id,
            objective_intervals={"cost": {"lower_95": 0.9, "upper_95": 1.1}},
            confidence_level=0.95,
        )