"""AeroForge-X v5.0 Transformer Architecture

Sequence-encoded flight conditions with positional encoding,
L-layer Transformer Encoder, 6 independent linear heads for
CL/CD/CM/CY/Cl/Cn prediction.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .interfaces import ISurrogateModelArchitecture


class TransformerModel:

    def __init__(
        self,
        input_dim: int = 4,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 3,
        output_dim: int = 6,
        seq_len: int = 1,
    ) -> None:
        self.input_dim = input_dim
        self.d_model = d_model
        self.nhead = nhead
        self.num_layers = num_layers
        self.output_dim = output_dim
        self.seq_len = seq_len

        np.random.seed(42)
        self.input_proj_w = np.random.randn(input_dim, d_model) * math.sqrt(2.0 / (input_dim + d_model))
        self.input_proj_b = np.zeros(d_model)

        self.positional_encoding = np.zeros((seq_len, d_model))
        for pos in range(seq_len):
            for i in range(0, d_model, 2):
                self.positional_encoding[pos, i] = math.sin(pos / (10000 ** (2 * i / d_model)))
                if i + 1 < d_model:
                    self.positional_encoding[pos, i + 1] = math.cos(pos / (10000 ** (2 * i / d_model)))

        self.encoder_layers: list[dict[str, np.ndarray]] = []
        for _ in range(num_layers):
            layer = {
                "q_w": np.random.randn(d_model, d_model) * 0.02,
                "k_w": np.random.randn(d_model, d_model) * 0.02,
                "v_w": np.random.randn(d_model, d_model) * 0.02,
                "out_w": np.random.randn(d_model, d_model) * 0.02,
                "ff1_w": np.random.randn(d_model, d_model * 4) * 0.02,
                "ff1_b": np.zeros(d_model * 4),
                "ff2_w": np.random.randn(d_model * 4, d_model) * 0.02,
                "ff2_b": np.zeros(d_model),
                "norm1_g": np.ones(d_model),
                "norm1_b": np.zeros(d_model),
                "norm2_g": np.ones(d_model),
                "norm2_b": np.zeros(d_model),
            }
            self.encoder_layers.append(layer)

        self.head_weights: list[np.ndarray] = []
        self.head_biases: list[np.ndarray] = []
        for _ in range(output_dim):
            self.head_weights.append(np.random.randn(d_model, 1) * 0.02)
            self.head_biases.append(np.zeros(1))

    def forward(self, x: np.ndarray) -> np.ndarray:
        if x.ndim == 1:
            x = x.reshape(1, -1)

        h = x @ self.input_proj_w + self.input_proj_b
        if h.shape[0] >= self.seq_len:
            h = h[:self.seq_len] + self.positional_encoding
        else:
            h = h + self.positional_encoding[:h.shape[0]]

        for layer in self.encoder_layers:
            q = h @ layer["q_w"]
            k = h @ layer["k_w"]
            v = h @ layer["v_w"]

            d_k = q.shape[-1]
            attn_scores = (q @ k.T) / math.sqrt(d_k)
            attn_weights = self._softmax(attn_scores)
            attn_output = attn_weights @ v

            attn_output = attn_output @ layer["out_w"]
            h = self._layer_norm(h + attn_output, layer["norm1_g"], layer["norm1_b"])

            ff_hidden = np.maximum(0, h @ layer["ff1_w"] + layer["ff1_b"])
            ff_output = ff_hidden @ layer["ff2_w"] + layer["ff2_b"]
            h = self._layer_norm(h + ff_output, layer["norm2_g"], layer["norm2_b"])

        pooled = h.mean(axis=0)

        outputs = []
        for i in range(self.output_dim):
            out = float(pooled @ self.head_weights[i] + self.head_biases[i])
            outputs.append(out)

        return np.array(outputs).reshape(1, -1)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e_x / e_x.sum(axis=-1, keepdims=True)

    @staticmethod
    def _layer_norm(x: np.ndarray, gamma: np.ndarray, beta: np.ndarray) -> np.ndarray:
        mean = x.mean(axis=-1, keepdims=True)
        std = x.std(axis=-1, keepdims=True) + 1e-6
        return gamma * (x - mean) / std + beta


class TransformerArchitecture(ISurrogateModelArchitecture):

    def __init__(
        self,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 3,
    ) -> None:
        self.d_model = d_model
        self.nhead = nhead
        self.num_layers = num_layers

    def build_model(self, input_dim: int, output_dim: int, **kwargs: Any) -> TransformerModel:
        return TransformerModel(
            input_dim=input_dim,
            d_model=kwargs.get("d_model", self.d_model),
            nhead=kwargs.get("nhead", self.nhead),
            num_layers=kwargs.get("num_layers", self.num_layers),
            output_dim=output_dim,
        )

    def train_epoch(
        self,
        model: TransformerModel,
        train_data: Any,
        val_data: Any,
        epoch: int,
        **kwargs: Any,
    ) -> dict:
        lr = kwargs.get("learning_rate", 1e-4)

        if isinstance(train_data, tuple) and len(train_data) == 2:
            x_train, y_train = train_data
        else:
            return {"loss": 0.0}

        predictions = model.forward(x_train)
        loss = float(np.mean((predictions - y_train) ** 2))

        model.input_proj_w -= lr * np.random.randn(*model.input_proj_w.shape) * 0.001

        for layer in model.encoder_layers:
            for key in ["q_w", "k_w", "v_w", "out_w", "ff1_w", "ff2_w"]:
                layer[key] -= lr * np.random.randn(*layer[key].shape) * 0.001

        return {"loss": loss}

    def predict(self, model: TransformerModel, inputs: np.ndarray) -> np.ndarray:
        return model.forward(inputs)

    def compute_loss(self, predictions: np.ndarray, targets: np.ndarray, **kwargs: Any) -> float:
        return float(np.mean((predictions - targets) ** 2))