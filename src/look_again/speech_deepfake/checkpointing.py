"""Checkpoint persistence for frozen-backbone speech models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch

from .config import CLASS_NAMES, SpeechDeepfakeConfig
from .model import FrozenSpeechDeepfakeModel


def checkpoint_payload(
    model: FrozenSpeechDeepfakeModel,
    config: SpeechDeepfakeConfig,
    *,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "model_name": config.model_name,
        "classifier_state_dict": model.classifier.state_dict(),
        "pooling": "masked_mean",
        "label_mapping": {name: index for index, name in enumerate(CLASS_NAMES)},
        "training_config": config.to_dict(),
        "validation_metrics": metrics,
    }


def save_head_checkpoint(
    path: Path,
    model: FrozenSpeechDeepfakeModel,
    config: SpeechDeepfakeConfig,
    *,
    metrics: dict[str, Any] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint_payload(model, config, metrics=metrics), path)


def load_model_from_checkpoint(
    checkpoint_path: Path,
    *,
    map_location: str | torch.device = "cpu",
) -> FrozenSpeechDeepfakeModel:
    payload = torch.load(checkpoint_path, map_location=map_location, weights_only=False)
    config = SpeechDeepfakeConfig(**payload["training_config"])
    model = FrozenSpeechDeepfakeModel(
        config.model_name,
        hidden_dim=config.hidden_dim,
        dropout=config.dropout,
        activation=config.activation,
    )
    model.classifier.load_state_dict(payload["classifier_state_dict"])
    return model


def write_training_history(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
