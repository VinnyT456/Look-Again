"""Trainable classification head on pooled speech embeddings."""

from __future__ import annotations

import torch
import torch.nn as nn


def build_activation(name: str) -> nn.Module:
    normalized = name.casefold()
    if normalized == "relu":
        return nn.ReLU()
    if normalized == "gelu":
        return nn.GELU()
    raise ValueError(f"Unsupported activation: {name}")


class SpeechClassifierHead(nn.Module):
    def __init__(
        self,
        input_dim: int,
        *,
        hidden_dim: int = 256,
        num_classes: int = 2,
        dropout: float = 0.3,
        activation: str = "gelu",
    ) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            build_activation(activation),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, embeddings: torch.Tensor) -> torch.Tensor:
        return self.net(embeddings)
