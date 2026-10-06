"""Test-time image degradations and post-training robustness evaluation."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable, Sequence

import matplotlib.pyplot as plt
import seaborn as sns
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from torch.utils.data import DataLoader
from torchvision import transforms

from look_again.dataset import grouped_split_with_transform
from look_again.forensic_preprocessing import ForensicChannelsTransform


class JPEGCompression:
    def __init__(self, quality: int) -> None:
        self.quality = quality

    def __call__(self, image: Image.Image) -> Image.Image:
        buffer = BytesIO()
        rgb_image = image.convert("RGB")
        rgb_image.save(buffer, format="JPEG", quality=self.quality)
        buffer.seek(0)
        reloaded = Image.open(buffer)
        reloaded.load()
        return reloaded.convert("RGB")


class RandomJPEGCompression:
    """Apply class-independent JPEG degradation during face-swap training."""

    def __init__(
        self,
        *,
        probability: float = 0.35,
        qualities: tuple[int, ...] = (65, 75, 85, 95),
    ) -> None:
        if not 0.0 <= probability <= 1.0:
            raise ValueError("JPEG augmentation probability must be in [0, 1]")
        if not qualities or any(not 1 <= quality <= 95 for quality in qualities):
            raise ValueError("JPEG augmentation qualities must be in [1, 95]")
        self.probability = probability
        self.qualities = qualities

    def __call__(self, image: Image.Image) -> Image.Image:
        if torch.rand(()).item() >= self.probability:
            return image
        index = int(torch.randint(len(self.qualities), ()).item())
        return JPEGCompression(self.qualities[index])(image)


class HalfDownscale:
    def __call__(self, image: Image.Image) -> Image.Image:
        width, height = image.size
        new_width = max(1, int(width * 0.5))
        new_height = max(1, int(height * 0.5))
        return image.resize((new_width, new_height), Image.BILINEAR)


@dataclass(frozen=True)
class EvaluationMetrics:
    loss: float
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float


ROBUSTNESS_CONDITIONS: tuple[tuple[str, tuple[Callable, ...]], ...] = (
    ("Original", ()),
    ("JPEG Q90", (JPEGCompression(90),)),
    ("JPEG Q70", (JPEGCompression(70),)),
    ("JPEG Q50", (JPEGCompression(50),)),
    ("JPEG Q30", (JPEGCompression(30),)),
    ("Gaussian Blur", (transforms.GaussianBlur(kernel_size=5),)),
    ("50% Downscale", (HalfDownscale(),)),
)


def model_preprocess_config(model) -> tuple[tuple[int, int], tuple[float, ...], tuple[float, ...]]:
    input_size = tuple(model.default_cfg.get("input_size", (3, 224, 224))[-2:])
    mean = tuple(model.default_cfg["mean"])
    std = tuple(model.default_cfg["std"])
    return input_size, mean, std


def build_baseline_test_transform(model) -> Callable:
    if getattr(model, "uses_forensic_channels", False):
        return ForensicChannelsTransform(model)
    if getattr(model, "uses_facenet_standardization", False):
        from look_again.inception_resnet_v1_checkpoint import build_facenet_test_transform

        return build_facenet_test_transform(model)
    input_size, mean, std = model_preprocess_config(model)
    return transforms.Compose(
        [
            transforms.Resize(input_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ]
    )


def build_test_transform_with_degradations(
    model,
    degradations: Sequence[Callable],
) -> Callable:
    if getattr(model, "uses_forensic_channels", False):
        return transforms.Compose(
            [*degradations, ForensicChannelsTransform(model)]
        )
    if getattr(model, "uses_facenet_standardization", False):
        from look_again.inception_resnet_v1_checkpoint import (
            FixedFaceNetStandardization,
            build_facenet_test_transform,
        )

        input_size = tuple(model.default_cfg.get("input_size", (3, 160, 160))[-2:])
        steps: list[Callable] = list(degradations)
        steps.extend(
            [
                transforms.Resize(input_size, antialias=True),
                transforms.ToTensor(),
                FixedFaceNetStandardization(),
            ]
        )
        return transforms.Compose(steps)
    input_size, mean, std = model_preprocess_config(model)
    steps: list[Callable] = list(degradations)
    steps.extend(
        [
            transforms.Resize(input_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ]
    )
    return transforms.Compose(steps)


def evaluate_model(
    model: nn.Module,
    dataloader: DataLoader,
    loss_fn: nn.Module,
    device: torch.device,
    *,
    positive_label: int = 1,
) -> EvaluationMetrics:
    model.eval()
    total_loss = 0.0
    total_examples = 0
    all_logits: list[torch.Tensor] = []
    all_labels: list[torch.Tensor] = []

    with torch.no_grad():
        for images, labels in dataloader:
            images = images.to(device)
            labels = labels.to(device=device, dtype=torch.float32)

            logits = model(images).squeeze(1)
            label_matrix = labels.unsqueeze(1)
            loss = loss_fn(logits.unsqueeze(1), label_matrix)

            batch_size = labels.size(0)
            total_loss += loss.item() * batch_size
            total_examples += batch_size
            all_logits.append(logits.detach().cpu())
            all_labels.append(labels.detach().cpu())

    logits_tensor = torch.cat(all_logits)
    labels_tensor = torch.cat(all_labels)
    predictions = (logits_tensor >= 0).to(torch.int64)
    label_ints = labels_tensor.to(torch.int64)
    probabilities = torch.sigmoid(logits_tensor).numpy()
    label_numpy = label_ints.numpy()
    prediction_numpy = predictions.numpy()

    accuracy = (predictions == label_ints).float().mean().item()
    precision = precision_score(
        label_numpy,
        prediction_numpy,
        pos_label=positive_label,
        zero_division=0,
    )
    recall = recall_score(
        label_numpy,
        prediction_numpy,
        pos_label=positive_label,
        zero_division=0,
    )
    f1 = f1_score(
        label_numpy,
        prediction_numpy,
        pos_label=positive_label,
        zero_division=0,
    )
    try:
        roc_auc = roc_auc_score(label_numpy, probabilities)
    except ValueError:
        roc_auc = float("nan")

    return EvaluationMetrics(
        loss=total_loss / total_examples,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1=f1,
        roc_auc=roc_auc,
    )


def _print_robustness_table(rows: Sequence[tuple[str, EvaluationMetrics]]) -> None:
    print("\nRobustness Evaluation")
    print("-" * 79)
    print(
        f"{'Condition':<16}{'Accuracy':>12}{'Precision':>12}{'Recall':>10}"
        f"{'F1':>10}{'ROC-AUC':>10}{'Loss':>10}"
    )
    for condition, metrics in rows:
        print(
            f"{condition:<16}"
            f"{metrics.accuracy:>12.2%}"
            f"{metrics.precision:>12.2%}"
            f"{metrics.recall:>10.2%}"
            f"{metrics.f1:>10.2%}"
            f"{metrics.roc_auc:>10.4f}"
            f"{metrics.loss:>10.4f}"
        )


def _save_robustness_csv(
    rows: Sequence[tuple[str, EvaluationMetrics]],
    csv_path: Path,
) -> None:
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "condition",
                "accuracy",
                "precision",
                "recall",
                "f1",
                "roc_auc",
                "loss",
            ],
        )
        writer.writeheader()
        for condition, metrics in rows:
            writer.writerow(
                {
                    "condition": condition,
                    "accuracy": metrics.accuracy,
                    "precision": metrics.precision,
                    "recall": metrics.recall,
                    "f1": metrics.f1,
                    "roc_auc": metrics.roc_auc,
                    "loss": metrics.loss,
                }
            )


def _save_robustness_plot(
    rows: Sequence[tuple[str, EvaluationMetrics]],
    plot_path: Path,
) -> None:
    condition_names = [condition for condition, _ in rows]
    accuracies = [metrics.accuracy for _, metrics in rows]
    original_accuracy = next(
        metrics.accuracy for condition, metrics in rows if condition == "Original"
    )

    jpeg_quality_map = {
        "JPEG Q90": 90,
        "JPEG Q70": 70,
        "JPEG Q50": 50,
        "JPEG Q30": 30,
    }
    jpeg_qualities = []
    jpeg_accuracies = []
    for condition, metrics in rows:
        quality = jpeg_quality_map.get(condition)
        if quality is not None:
            jpeg_qualities.append(quality)
            jpeg_accuracies.append(metrics.accuracy)

    sns.set_theme(style="whitegrid")
    figure, axes = plt.subplots(1, 2, figsize=(13, 5))

    axes[0].bar(condition_names, accuracies, color="steelblue")
    axes[0].set_title("Accuracy by Degradation Condition")
    axes[0].set_ylabel("Accuracy")
    axes[0].set_ylim(0, 1)
    axes[0].tick_params(axis="x", rotation=35)
    for tick, accuracy in zip(axes[0].get_xticks(), accuracies):
        axes[0].text(tick, accuracy + 0.02, f"{accuracy:.1%}", ha="center", fontsize=8)

    axes[1].plot(jpeg_qualities, jpeg_accuracies, marker="o", label="JPEG quality sweep")
    axes[1].axhline(
        original_accuracy,
        color="crimson",
        linestyle="--",
        linewidth=1.5,
        label=f"Original ({original_accuracy:.1%})",
    )
    axes[1].set_title("JPEG Robustness")
    axes[1].set_xlabel("JPEG quality")
    axes[1].set_ylabel("Accuracy")
    axes[1].set_xticks(jpeg_qualities)
    axes[1].set_ylim(0, 1)
    axes[1].legend()
    axes[1].invert_xaxis()

    figure.tight_layout()
    figure.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(figure)


def run_robustness_evaluation(
    model: nn.Module,
    test_split,
    loss_fn: nn.Module,
    device: torch.device,
    run_name: str,
    project_root: Path,
    *,
    batch_size: int,
) -> list[tuple[str, EvaluationMetrics]]:
    membership_reference = grouped_split_with_transform(test_split, transform=None)
    reference_indices = list(membership_reference.dataset.indices)

    rows: list[tuple[str, EvaluationMetrics]] = []
    for condition, degradations in ROBUSTNESS_CONDITIONS:
        transform = build_test_transform_with_degradations(model, degradations)
        degraded_split = grouped_split_with_transform(test_split, transform)
        if list(degraded_split.dataset.indices) != reference_indices:
            raise RuntimeError(
                f"Test membership changed for robustness condition: {condition}"
            )
        dataloader = DataLoader(
            degraded_split.dataset,
            batch_size=batch_size,
            shuffle=False,
        )
        metrics = evaluate_model(model, dataloader, loss_fn, device)
        rows.append((condition, metrics))

    _print_robustness_table(rows)
    project_root.mkdir(parents=True, exist_ok=True)
    csv_path = project_root / f"{run_name}_robustness_results.csv"
    plot_path = project_root / f"{run_name}_robustness.png"
    _save_robustness_csv(rows, csv_path)
    _save_robustness_plot(rows, plot_path)
    print(f"Robustness CSV saved to {csv_path}")
    print(f"Robustness plot saved to {plot_path}")
    return rows
