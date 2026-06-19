"""AeroForge-X v5.0 CFD Surrogate Model Architecture Interface

Defines the pluggable interface for CFD surrogate model architectures.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ISurrogateModelArchitecture(ABC):

    @abstractmethod
    def build_model(self, input_dim: int, output_dim: int, **kwargs: Any) -> Any:
        ...

    @abstractmethod
    def train_epoch(
        self,
        model: Any,
        train_data: Any,
        val_data: Any,
        epoch: int,
        **kwargs: Any,
    ) -> dict:
        ...

    @abstractmethod
    def predict(self, model: Any, inputs: Any) -> Any:
        ...

    @abstractmethod
    def compute_loss(self, predictions: Any, targets: Any, **kwargs: Any) -> Any:
        ...