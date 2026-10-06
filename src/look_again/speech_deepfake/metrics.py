"""Metrics and plots for binary speech deepfake classification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from .config import CLASS_NAMES


def resolve_device(prefer_amp: bool = True) -> tuple[torch.device, bool]:
    if torch.cuda.is_available():
        return torch.device("cuda"), prefer_amp
    if torch.backends.mps.is_available():
        return torch.device("mps"), False
    return torch.device("cpu"), False


@torch.no_grad()
def collect_predictions(
    model: nn.Module,
    dataloader,
    device: torch.device,
    *,
    use_embeddings: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    model.eval()
    labels: list[int] = []
    preds: list[int] = []
    probs: list[float] = []
    for batch in dataloader:
        batch_labels = batch["labels"].to(device)
        if use_embeddings:
            logits = model.classifier(batch["embeddings"].to(device))
        else:
            logits = model(
                batch["input_values"].to(device),
                batch.get("attention_mask").to(device) if batch.get("attention_mask") is not None else None,
            )
        if not torch.all(torch.isfinite(logits)):
            raise RuntimeError("Non-finite logits during evaluation")
        probabilities = torch.softmax(logits, dim=-1)[:, 1]
        predictions = torch.argmax(logits, dim=-1)
        labels.extend(batch_labels.cpu().tolist())
        preds.extend(predictions.cpu().tolist())
        probs.extend(probabilities.cpu().tolist())
    return (
        np.asarray(labels, dtype=np.int64),
        np.asarray(preds, dtype=np.int64),
        np.asarray(probs, dtype=np.float64),
    )


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    *,
    split_name: str,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "split": split_name,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "class_names": list(CLASS_NAMES),
    }
    if len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
    else:
        metrics["roc_auc"] = None
    return metrics


def save_confusion_matrix_plot(metrics: dict[str, Any], output_path: Path, *, title: str) -> None:
    matrix = np.asarray(metrics["confusion_matrix"], dtype=int)
    figure, axis = plt.subplots(figsize=(4.5, 4.0))
    image = axis.imshow(matrix, cmap="Blues")
    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    axis.set(
        xticks=[0, 1],
        yticks=[0, 1],
        xticklabels=CLASS_NAMES,
        yticklabels=CLASS_NAMES,
        xlabel="Predicted",
        ylabel="Actual",
        title=title,
    )
    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            axis.text(col, row, str(matrix[row, col]), ha="center", va="center", color="black")
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(figure)


def save_roc_curve_plot(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    output_path: Path,
    *,
    title: str,
) -> None:
    if len(np.unique(y_true)) < 2:
        return
    false_positive_rate, true_positive_rate, _thresholds = roc_curve(y_true, y_prob)
    figure, axis = plt.subplots(figsize=(4.5, 4.0))
    axis.plot(false_positive_rate, true_positive_rate, label="ROC")
    axis.plot([0, 1], [0, 1], linestyle="--", color="gray")
    axis.set(xlabel="False positive rate", ylabel="True positive rate", title=title)
    axis.legend(loc="lower right")
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(figure)


def write_metrics_bundle(
    metrics_by_split: dict[str, dict[str, Any]],
    probabilities_by_split: dict[str, tuple[np.ndarray, np.ndarray]],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics_by_split, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for split_name, metrics in metrics_by_split.items():
        save_confusion_matrix_plot(
            metrics,
            output_dir / "confusion_matrix.png"
            if split_name == "test"
            else output_dir / f"confusion_matrix_{split_name}.png",
            title=f"{split_name} confusion matrix",
        )
        y_true, y_prob = probabilities_by_split[split_name]
        roc_name = "roc_curve.png" if split_name == "test" else f"roc_curve_{split_name}.png"
        save_roc_curve_plot(
            y_true,
            y_prob,
            output_dir / roc_name,
            title=f"{split_name} ROC curve",
        )
