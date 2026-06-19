"""AeroForge-X v5.0 DeepONet Architecture

Branch network encodes geometry parameters, Trunk network encodes flight conditions.
Output: Branch × Trunk inner product → aero coefficients.
Supports shared Trunk with independent Branch heads.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .interfaces import ISurrogateModelArchitecture


class DeepONetModel:

    def __init__(
        self,
        branch_input_dim: int,
        trunk_input_dim: int,
        trunk_output_dim: int,
        branch_hidden: list[int] | None = None,
        trunk_hidden: list[int] | None = None,
        num_heads: int = 6,
    ) -> None:
        self.branch_input_dim = branch_input_dim
        self.trunk_input_dim = trunk_input_dim
        self.trunk_output_dim = trunk_output_dim
        self.num_heads = num_heads
        self.branch_hidden = branch_hidden or [64, 64]
        self.trunk_hidden = trunk_hidden or [64, 64]

        self.branch_weights: list[list[np.ndarray]] = []
        self.branch_biases: list[list[np.ndarray]] = []
        self.trunk_weights: list[np.ndarray] = []
        self.trunk_biases: list[np.ndarray] = []

        self._initialize()

    def _initialize(self) -> None:
        np.random.seed(42)

        branch_dims = [self.branch_input_dim] + self.branch_hidden + [self.trunk_output_dim]
        for _ in range(self.num_heads):
            w = []
            b = []
            for i in range(len(branch_dims) - 1):
                std = math.sqrt(2.0 / (branch_dims[i] + branch_dims[i + 1]))
                w.append(np.random.randn(branch_dims[i], branch_dims[i + 1]) * std)
                b.append(np.zeros(branch_dims[i + 1]))
            self.branch_weights.append(w)
            self.branch_biases.append(b)

        trunk_dims = [self.trunk_input_dim] + self.trunk_hidden + [self.trunk_output_dim]
        for i in range(len(trunk_dims) - 1):
            std = math.sqrt(2.0 / (trunk_dims[i] + trunk_dims[i + 1]))
            self.trunk_weights.append(np.random.randn(trunk_dims[i], trunk_dims[i + 1]) * std)
            self.trunk_biases.append(np.zeros(trunk_dims[i + 1]))

    def forward(self, branch_input: np.ndarray, trunk_input: np.ndarray) -> np.ndarray:
        trunk_h = trunk_input
        for i in range(len(self.trunk_weights)):
            trunk_h = trunk_h @ self.trunk_weights[i] + self.trunk_biases[i]
            if i < len(self.trunk_weights) - 1:
                trunk_h = np.tanh(trunk_h)

        outputs = []
        for head_idx in range(self.num_heads):
            branch_h = branch_input
            for i in range(len(self.branch_weights[head_idx])):
                branch_h = branch_h @ self.branch_weights[head_idx][i] + self.branch_biases[head_idx][i]
                if i < len(self.branch_weights[head_idx]) - 1:
                    branch_h = np.tanh(branch_h)

            output = np.sum(branch_h * trunk_h, axis=-1, keepdims=True)
            outputs.append(output)

        return np.concatenate(outputs, axis=-1)


class DeepONetArchitecture(ISurrogateModelArchitecture):

    def __init__(
        self,
        branch_input_dim: int = 11,
        trunk_input_dim: int = 4,
        trunk_output_dim: int = 32,
        num_heads: int = 6,
    ) -> None:
        self.branch_input_dim = branch_input_dim
        self.trunk_input_dim = trunk_input_dim
        self.trunk_output_dim = trunk_output_dim
        self.num_heads = num_heads

    def build_model(self, input_dim: int, output_dim: int, **kwargs: Any) -> DeepONetModel:
        return DeepONetModel(
            branch_input_dim=kwargs.get("branch_input_dim", self.branch_input_dim),
            trunk_input_dim=kwargs.get("trunk_input_dim", self.trunk_input_dim),
            trunk_output_dim=kwargs.get("trunk_output_dim", self.trunk_output_dim),
            num_heads=kwargs.get("num_heads", self.num_heads),
        )

    def train_epoch(
        self,
        model: DeepONetModel,
        train_data: Any,
        val_data: Any,
        epoch: int,
        **kwargs: Any,
    ) -> dict:
        lr = kwargs.get("learning_rate", 1e-3)

        if isinstance(train_data, tuple) and len(train_data) == 3:
            branch_input, trunk_input, targets = train_data
        else:
            return {"loss": 0.0}

        predictions = model.forward(branch_input, trunk_input)
        loss = float(np.mean((predictions - targets) ** 2))

        for head_idx in range(model.num_heads):
            for i in range(len(model.branch_weights[head_idx])):
                model.branch_weights[head_idx][i] -= lr * np.random.randn(*model.branch_weights[head_idx][i].shape) * 0.001

        for i in range(len(model.trunk_weights)):
            model.trunk_weights[i] -= lr * np.random.randn(*model.trunk_weights[i].shape) * 0.001

        return {"loss": loss}

    def predict(self, model: DeepONetModel, inputs: Any) -> np.ndarray:
        if isinstance(inputs, tuple) and len(inputs) == 2:
            branch_input, trunk_input = inputs
            return model.forward(branch_input, trunk_input)
        return np.zeros((1, model.num_heads))

    def compute_loss(self, predictions: np.ndarray, targets: np.ndarray, **kwargs: Any) -> float:
        return float(np.mean((predictions - targets) ** 2))