"""Shared external and in-domain evaluation helpers for saved checkpoints."""

from __future__ import annotations

from collections import defaultdict
import random
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, Sequence

import cv2
import numpy as np
import torch
from datasets import Dataset, Video, load_dataset
from PIL import Image
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from torch.utils.data import DataLoader, Dataset as TorchDataset

from look_again.dataset import SEED, build_image_splits
from look_again.paths import PROJECT_ROOT, RESULTS_DIR
from look_again.face_preprocessing import crop_face
from look_again.training import BATCH_SIZE, load_trained_model
from look_again.robustness import (
    EvaluationMetrics,
    build_baseline_test_transform,
    evaluate_model,
    run_robustness_evaluation,
)

# Matches ImageFolder class order in dataset.py: fake=0, real=1.
FAKE_LABEL = 0
REAL_LABEL = 1

CELEB_DF_HF_DATASET_ID = "thenewsupercell/celeb-df-image-dataset"
KENJON_DATASET_ID = "kenjon/deep-fake-face-swap"
SDFVD_DATASET_ID = "Hemgg/SDFVD-video-dataset"
DEFAULT_CELEB_DF_ROOT = PROJECT_ROOT / "data" / "Celeb-DF"

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SDFVD_MIN_CONSECUTIVE_FAKE_FRAMES = 1
SDFVD_MAX_CONSECUTIVE_FAKE_FRAMES = 15


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    metrics: EvaluationMetrics
    positive_label: int
    details: dict[str, str | int | float]


@dataclass(frozen=True)
class SDFVDVideoMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float


@dataclass(frozen=True)
class SDFVDEvaluationResult:
    frame_metrics: EvaluationMetrics
    video_metrics: SDFVDVideoMetrics
    details: dict[str, str | int | float]
    frame_predictions: tuple[dict[str, str | int | float], ...]
    video_predictions: tuple[dict[str, str | int | float], ...]
    video_stats: tuple[dict[str, str | int | float], ...] = ()


class KenjonFaceSwapDataset(TorchDataset):
    """HF face-swap images; dataset card has no real class, so all labels are fake."""

    def __init__(self, split: str, transform: Callable | None = None) -> None:
        self.dataset = load_dataset(KENJON_DATASET_ID, split=split)
        self.transform = transform

    def __len__(self) -> int:
        return len(self.dataset)

    def __getitem__(self, index: int):
        row = self.dataset[index]
        image = row["image"].convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        return image, float(FAKE_LABEL)


class LocalImageListDataset(TorchDataset):
    def __init__(
        self,
        samples: Sequence[tuple[Path, int]],
        transform: Callable | None = None,
    ) -> None:
        self.samples = list(samples)
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        path, label = self.samples[index]
        image = Image.open(path).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        return image, float(label)


class HFCelebDFDataset(TorchDataset):
    def __init__(self, hf_dataset: Dataset, transform: Callable | None = None) -> None:
        self.dataset = hf_dataset
        self.transform = transform

    def __len__(self) -> int:
        return len(self.dataset)

    def __getitem__(self, index: int):
        row = self.dataset[index]
        image = row["image"].convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        return image, float(row["label"])


def _collect_image_paths(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise FileNotFoundError(f"Missing directory: {directory}")
    paths = [
        path
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    ]
    if not paths:
        raise ValueError(f"No images found under {directory}")
    return paths


def resolve_celebdf_local_dirs(root: Path) -> tuple[Path, Path]:
    """Resolve Celeb-DF v2-style fake/real folders under ``root``."""
    candidates = (
        (root / "Celeb-synthesis", root / "Celeb-real"),
        (root / "celeb_synthesis", root / "celeb_real"),
        (root / "fake", root / "real"),
    )
    for fake_dir, real_dir in candidates:
        if fake_dir.is_dir() and real_dir.is_dir():
            return fake_dir, real_dir
    raise FileNotFoundError(
        f"Expected Celeb-DF folders under {root}. "
        "Looked for Celeb-synthesis/Celeb-real or fake/real."
    )


def _subsample_balanced_indices(
    labels: Sequence[int],
    *,
    seed: int,
    max_per_class: int | None,
) -> list[int]:
    fake_indices = [index for index, label in enumerate(labels) if label == FAKE_LABEL]
    real_indices = [index for index, label in enumerate(labels) if label == REAL_LABEL]
    if not fake_indices or not real_indices:
        raise ValueError("Balanced Celeb-DF eval requires both fake and real examples.")

    per_class = min(len(fake_indices), len(real_indices))
    if max_per_class is not None:
        per_class = min(per_class, max_per_class)

    generator = torch.Generator().manual_seed(seed)
    fake_order = torch.randperm(len(fake_indices), generator=generator).tolist()[:per_class]
    real_order = torch.randperm(len(real_indices), generator=generator).tolist()[:per_class]
    selected = [fake_indices[index] for index in fake_order]
    selected.extend(real_indices[index] for index in real_order)
    random.Random(seed).shuffle(selected)
    return selected


def default_celebdf_root() -> Path | None:
    if not DEFAULT_CELEB_DF_ROOT.is_dir():
        return None
    try:
        resolve_celebdf_local_dirs(DEFAULT_CELEB_DF_ROOT)
    except (FileNotFoundError, ValueError):
        return None
    return DEFAULT_CELEB_DF_ROOT


def build_balanced_celebdf_hf_dataset(
    *,
    split: str = "test",
    seed: int = SEED,
    max_per_class: int | None = None,
) -> tuple[Dataset, dict[str, int | str]]:
    full = load_dataset(CELEB_DF_HF_DATASET_ID, split=split)
    labels = full["label"]
    label_counts = {
        FAKE_LABEL: sum(1 for label in labels if label == FAKE_LABEL),
        REAL_LABEL: sum(1 for label in labels if label == REAL_LABEL),
    }
    if label_counts[REAL_LABEL] < 500:
        print(
            "WARNING: HF Celeb-DF mirror is fake-heavy "
            f"(fake={label_counts[FAKE_LABEL]}, real={label_counts[REAL_LABEL]} in split={split}). "
            "Balanced eval uses all available reals. For the standard Celeb-DF benchmark, "
            f"extract official frames under {DEFAULT_CELEB_DF_ROOT} and pass --celeb-root.",
            flush=True,
        )
    selected_indices = _subsample_balanced_indices(
        labels,
        seed=seed,
        max_per_class=max_per_class,
    )
    balanced = full.select(selected_indices)
    fake_count = sum(1 for label in balanced["label"] if label == FAKE_LABEL)
    real_count = len(balanced) - fake_count
    metadata = {
        "source": CELEB_DF_HF_DATASET_ID,
        "split": split,
        "fake_count": fake_count,
        "real_count": real_count,
        "total": len(balanced),
        "available_fake": label_counts[FAKE_LABEL],
        "available_real": label_counts[REAL_LABEL],
    }
    return balanced, metadata


def build_balanced_celebdf_local_dataset(
    root: Path,
    *,
    seed: int = SEED,
    max_per_class: int | None = None,
) -> tuple[LocalImageListDataset, dict[str, int | str]]:
    fake_dir, real_dir = resolve_celebdf_local_dirs(root)
    fake_paths = _collect_image_paths(fake_dir)
    real_paths = _collect_image_paths(real_dir)
    per_class = min(len(fake_paths), len(real_paths))
    if max_per_class is not None:
        per_class = min(per_class, max_per_class)

    generator = torch.Generator().manual_seed(seed)
    fake_order = torch.randperm(len(fake_paths), generator=generator).tolist()[:per_class]
    real_order = torch.randperm(len(real_paths), generator=generator).tolist()[:per_class]
    samples: list[tuple[Path, int]] = [
        (fake_paths[index], FAKE_LABEL) for index in fake_order
    ]
    samples.extend((real_paths[index], REAL_LABEL) for index in real_order)
    random.Random(seed).shuffle(samples)
    metadata = {
        "source": str(root.resolve()),
        "split": "local_balanced",
        "fake_count": per_class,
        "real_count": per_class,
        "total": len(samples),
    }
    return LocalImageListDataset(samples), metadata


def _format_metrics(metrics: EvaluationMetrics, *, positive_label: int) -> str:
    label_name = "fake" if positive_label == FAKE_LABEL else "real"
    return (
        f"accuracy={metrics.accuracy:.2%} | "
        f"{label_name}_precision={metrics.precision:.2%} | "
        f"{label_name}_recall={metrics.recall:.2%} | "
        f"{label_name}_f1={metrics.f1:.2%} | "
        f"roc_auc={metrics.roc_auc:.4f} | loss={metrics.loss:.4f}"
    )


def evaluate_celebdf_balanced(
    model,
    *,
    device: torch.device,
    loss_fn,
    celeb_root: Path | None = None,
    split: str = "test",
    seed: int = SEED,
    max_per_class: int | None = None,
    batch_size: int = BATCH_SIZE,
) -> BenchmarkResult:
    transform = build_baseline_test_transform(model)
    if celeb_root is None:
        celeb_root = default_celebdf_root()
    if celeb_root is not None:
        local_dataset, metadata = build_balanced_celebdf_local_dataset(
            celeb_root,
            seed=seed,
            max_per_class=max_per_class,
        )
        dataset = LocalImageListDataset(local_dataset.samples, transform=transform)
    else:
        hf_dataset, metadata = build_balanced_celebdf_hf_dataset(
            split=split,
            seed=seed,
            max_per_class=max_per_class,
        )
        dataset = HFCelebDFDataset(hf_dataset, transform=transform)

    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    metrics = evaluate_model(
        model,
        dataloader,
        loss_fn,
        device,
        positive_label=FAKE_LABEL,
    )
    print(
        f"Celeb-DF balanced | {metadata['source']} | split={metadata['split']} | "
        f"fake={metadata['fake_count']} real={metadata['real_count']} | "
        f"{_format_metrics(metrics, positive_label=FAKE_LABEL)}",
        flush=True,
    )
    return BenchmarkResult(
        name="celebdf_balanced",
        metrics=metrics,
        positive_label=FAKE_LABEL,
        details={key: str(value) for key, value in metadata.items()},
    )


def evaluate_kenjon_fake_only(
    model,
    *,
    device: torch.device,
    loss_fn,
    split: str = "test",
    batch_size: int = BATCH_SIZE,
) -> BenchmarkResult:
    transform = build_baseline_test_transform(model)
    dataset = KenjonFaceSwapDataset(split=split, transform=transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    metrics = evaluate_model(
        model,
        dataloader,
        loss_fn,
        device,
        positive_label=FAKE_LABEL,
    )
    print(
        f"Kenjon fake-only | {KENJON_DATASET_ID} | split={split} | "
        f"examples={len(dataset)} | "
        f"{_format_metrics(metrics, positive_label=FAKE_LABEL)}",
        flush=True,
    )
    return BenchmarkResult(
        name="kenjon_fake_only",
        metrics=metrics,
        positive_label=FAKE_LABEL,
        details={"split": split, "total": len(dataset)},
    )


def _sdfvd_label_to_int(label: object) -> int:
    if isinstance(label, str):
        normalized = label.strip().lower()
        if normalized in {"fake", "0"}:
            return FAKE_LABEL
        if normalized in {"real", "1"}:
            return REAL_LABEL
    else:
        try:
            numeric_label = int(label)
        except (TypeError, ValueError):
            numeric_label = -1
        if numeric_label in (FAKE_LABEL, REAL_LABEL):
            return numeric_label
    raise ValueError(f"Unexpected SDFVD label: {label!r}; expected fake=0 or real=1")


@contextmanager
def _materialize_video_path(video_value: object) -> Iterator[Path]:
    """Yield a local video path, materializing embedded HF video bytes if needed."""
    if isinstance(video_value, str):
        video_path_value = video_value
        video_bytes = None
    elif isinstance(video_value, dict):
        video_path_value = video_value.get("path")
        video_bytes = video_value.get("bytes")
    else:
        raise TypeError(f"Unsupported SDFVD video value: {type(video_value).__name__}")

    temporary_path: Path | None = None
    if video_path_value and Path(video_path_value).is_file():
        video_path = Path(video_path_value)
    elif video_bytes is not None:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_file.write(video_bytes)
            temporary_path = Path(temp_file.name)
        video_path = temporary_path
    else:
        raise FileNotFoundError(
            f"SDFVD video path is unavailable and has no embedded bytes: {video_path_value!r}"
        )

    try:
        yield video_path
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _iter_video_frames(video_value: object) -> Iterator[tuple[int, Image.Image]]:
    """Decode every readable RGB frame in order from an HF Video value."""
    with _materialize_video_path(video_value) as video_path:
        capture = cv2.VideoCapture(str(video_path))
        frame_index = 0
        try:
            if not capture.isOpened():
                raise ValueError(f"Could not open SDFVD video: {video_path}")
            while True:
                success, frame_bgr = capture.read()
                if not success or frame_bgr is None:
                    break
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                yield frame_index, Image.fromarray(frame_rgb)
                frame_index += 1
        finally:
            capture.release()

        if frame_index == 0:
            raise ValueError(f"SDFVD video contains no readable frames: {video_path}")


def _sdfvd_video_name(row: dict, video_index: int) -> str:
    for key in ("video_id", "id", "filename"):
        if row.get(key) is not None:
            return str(row[key])
    video_value = row.get("video")
    if isinstance(video_value, dict) and video_value.get("path"):
        return Path(video_value["path"]).name
    return f"video_{video_index:03d}"


def _validate_sdfvd_consecutive_threshold(consecutive_fake_frames: int) -> None:
    if not SDFVD_MIN_CONSECUTIVE_FAKE_FRAMES <= consecutive_fake_frames <= SDFVD_MAX_CONSECUTIVE_FAKE_FRAMES:
        raise ValueError(
            "consecutive_fake_frames must be between "
            f"{SDFVD_MIN_CONSECUTIVE_FAKE_FRAMES} and "
            f"{SDFVD_MAX_CONSECUTIVE_FAKE_FRAMES}, got {consecutive_fake_frames}"
        )


def _sdfvd_frame_is_fake(logit_real: float, real_logit_threshold: float) -> bool:
    """Frame is fake when the real-minus-fake logit falls below the threshold."""
    return logit_real < real_logit_threshold


def _relabel_sdfvd_frame_predictions(
    frame_prediction_rows: Sequence[dict[str, str | int | float]],
    *,
    real_logit_threshold: float,
) -> list[dict[str, str | int | float]]:
    """Recompute per-frame fake labels and consecutive runs from stored logits."""
    rows_by_video: dict[int, list[dict[str, str | int | float]]] = defaultdict(list)
    for row in frame_prediction_rows:
        rows_by_video[int(row["video_index"])].append(dict(row))

    relabeled: list[dict[str, str | int | float]] = []
    for video_index in sorted(rows_by_video):
        current_fake_run = 0
        for row in sorted(rows_by_video[video_index], key=lambda item: int(item["frame_index"])):
            logit_value = float(row["logit_real"])
            predicted_fake = _sdfvd_frame_is_fake(logit_value, real_logit_threshold)
            if predicted_fake:
                current_fake_run += 1
            else:
                current_fake_run = 0
            relabeled.append(
                {
                    **row,
                    "predicted_label": "fake" if predicted_fake else "real",
                    "consecutive_fake_frames": current_fake_run,
                    "real_logit_threshold": real_logit_threshold,
                }
            )
    return relabeled


def _longest_consecutive_fake_run(frame_rows: Sequence[dict[str, str | int | float]]) -> int:
    longest = 0
    current = 0
    for row in sorted(frame_rows, key=lambda item: int(item["frame_index"])):
        if row["predicted_label"] == "fake":
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _aggregate_sdfvd_video_predictions(
    frame_prediction_rows: Sequence[dict[str, str | int | float]],
    video_stats: Sequence[dict[str, str | int | float]],
    *,
    consecutive_fake_frames: int,
) -> tuple[SDFVDVideoMetrics, tuple[dict[str, str | int | float], ...], list[int], list[int]]:
    frames_by_video: dict[int, list[dict[str, str | int | float]]] = defaultdict(list)
    for row in frame_prediction_rows:
        frames_by_video[int(row["video_index"])].append(row)

    video_labels: list[int] = []
    video_predictions: list[int] = []
    longest_fake_runs: list[int] = []
    video_prediction_rows: list[dict[str, str | int | float]] = []

    for stats in sorted(video_stats, key=lambda item: int(item["video_index"])):
        video_index = int(stats["video_index"])
        label = FAKE_LABEL if stats["true_label"] == "fake" else REAL_LABEL
        longest_fake_run = _longest_consecutive_fake_run(frames_by_video.get(video_index, ()))
        predicted_video_label = (
            FAKE_LABEL if longest_fake_run >= consecutive_fake_frames else REAL_LABEL
        )
        video_labels.append(label)
        video_predictions.append(predicted_video_label)
        longest_fake_runs.append(longest_fake_run)
        video_prediction_rows.append(
            {
                **stats,
                "predicted_label": (
                    "fake" if predicted_video_label == FAKE_LABEL else "real"
                ),
                "longest_consecutive_fake_run": longest_fake_run,
                "fake_rule_triggered": int(
                    longest_fake_run >= consecutive_fake_frames
                ),
                "consecutive_fake_threshold": consecutive_fake_frames,
            }
        )

    video_label_values = torch.tensor(video_labels, dtype=torch.int64).numpy()
    try:
        video_roc_auc = float(
            roc_auc_score(video_label_values, [-run for run in longest_fake_runs])
        )
    except ValueError:
        video_roc_auc = float("nan")
    video_metrics = SDFVDVideoMetrics(
        accuracy=float(
            (torch.tensor(video_predictions).numpy() == video_label_values).mean()
        ),
        precision=float(
            precision_score(
                video_label_values,
                video_predictions,
                pos_label=FAKE_LABEL,
                zero_division=0,
            )
        ),
        recall=float(
            recall_score(
                video_label_values,
                video_predictions,
                pos_label=FAKE_LABEL,
                zero_division=0,
            )
        ),
        f1=float(
            f1_score(
                video_label_values,
                video_predictions,
                pos_label=FAKE_LABEL,
                zero_division=0,
            )
        ),
        roc_auc=video_roc_auc,
    )
    return video_metrics, tuple(video_prediction_rows), video_labels, video_predictions


def sweep_sdfvd_consecutive_thresholds(
    frame_prediction_rows: Sequence[dict[str, str | int | float]],
    video_stats: Sequence[dict[str, str | int | float]],
    *,
    real_logit_threshold: float = 0.0,
) -> list[tuple[int, SDFVDVideoMetrics]]:
    relabeled = _relabel_sdfvd_frame_predictions(
        frame_prediction_rows,
        real_logit_threshold=real_logit_threshold,
    )
    rows: list[tuple[int, SDFVDVideoMetrics]] = []
    for threshold in range(
        SDFVD_MIN_CONSECUTIVE_FAKE_FRAMES,
        SDFVD_MAX_CONSECUTIVE_FAKE_FRAMES + 1,
    ):
        metrics, _, _, _ = _aggregate_sdfvd_video_predictions(
            relabeled,
            video_stats,
            consecutive_fake_frames=threshold,
        )
        rows.append((threshold, metrics))
    return rows


def sweep_sdfvd_real_logit_thresholds(
    frame_prediction_rows: Sequence[dict[str, str | int | float]],
    video_stats: Sequence[dict[str, str | int | float]],
    *,
    consecutive_fake_frames: int = 1,
    min_threshold: float | None = None,
    max_threshold: float | None = None,
    steps: int = 40,
) -> list[tuple[float, SDFVDVideoMetrics, EvaluationMetrics]]:
    """Sweep frame decision threshold using saved logits (no re-inference)."""
    _validate_sdfvd_consecutive_threshold(consecutive_fake_frames)
    logits = [float(row["logit_real"]) for row in frame_prediction_rows]
    if not logits:
        return []
    low = min_threshold if min_threshold is not None else min(logits)
    high = max_threshold if max_threshold is not None else max(logits)
    if steps < 2:
        raise ValueError(f"steps must be at least 2, got {steps}")
    grid = np.linspace(low, high, steps)
    rows: list[tuple[float, SDFVDVideoMetrics, EvaluationMetrics]] = []
    for real_logit_threshold in grid:
        relabeled = _relabel_sdfvd_frame_predictions(
            frame_prediction_rows,
            real_logit_threshold=float(real_logit_threshold),
        )
        video_metrics, _, _, _ = _aggregate_sdfvd_video_predictions(
            relabeled,
            video_stats,
            consecutive_fake_frames=consecutive_fake_frames,
        )
        frame_metrics = _sdfvd_frame_metrics_from_rows(relabeled)
        rows.append((float(real_logit_threshold), video_metrics, frame_metrics))
    return rows


def _sdfvd_frame_metrics_from_rows(
    frame_prediction_rows: Sequence[dict[str, str | int | float]],
) -> EvaluationMetrics:
    frame_labels = [
        FAKE_LABEL if row["true_label"] == "fake" else REAL_LABEL
        for row in frame_prediction_rows
    ]
    frame_predictions = [
        FAKE_LABEL if row["predicted_label"] == "fake" else REAL_LABEL
        for row in frame_prediction_rows
    ]
    frame_logits = torch.tensor(
        [float(row["logit_real"]) for row in frame_prediction_rows]
    )
    frame_label_values = torch.tensor(frame_labels, dtype=torch.int64).numpy()
    try:
        frame_roc_auc = float(
            roc_auc_score(frame_label_values, torch.sigmoid(frame_logits).numpy())
        )
    except ValueError:
        frame_roc_auc = float("nan")
    return EvaluationMetrics(
        loss=float("nan"),
        accuracy=float(
            (torch.tensor(frame_predictions).numpy() == frame_label_values).mean()
        ),
        precision=float(
            precision_score(
                frame_label_values,
                frame_predictions,
                pos_label=FAKE_LABEL,
                zero_division=0,
            )
        ),
        recall=float(
            recall_score(
                frame_label_values,
                frame_predictions,
                pos_label=FAKE_LABEL,
                zero_division=0,
            )
        ),
        f1=float(
            f1_score(
                frame_label_values,
                frame_predictions,
                pos_label=FAKE_LABEL,
                zero_division=0,
            )
        ),
        roc_auc=frame_roc_auc,
    )


def evaluate_sdfvd_sequential_video_rule(
    model,
    *,
    device: torch.device,
    loss_fn,
    consecutive_fake_frames: int = 5,
    frame_batch_size: int = BATCH_SIZE,
    real_logit_threshold: float = 0.0,
) -> SDFVDEvaluationResult:
    """Score every frame and flag a video fake after a consecutive fake run."""
    _validate_sdfvd_consecutive_threshold(consecutive_fake_frames)
    if frame_batch_size < 1:
        raise ValueError(f"frame_batch_size must be positive, got {frame_batch_size}")

    dataset = load_dataset(SDFVD_DATASET_ID, split="train")
    required_columns = {"video", "label"}
    missing_columns = required_columns - set(dataset.column_names)
    if missing_columns:
        raise ValueError(
            f"SDFVD dataset is missing required columns: {sorted(missing_columns)}"
        )
    dataset = dataset.cast_column("video", Video(decode=False))

    transform = build_baseline_test_transform(model)
    model.eval()
    frame_logits: list[float] = []
    frame_labels: list[int] = []
    frame_prediction_rows: list[dict[str, str | int | float]] = []
    video_stats: list[dict[str, str | int | float]] = []
    total_frame_loss = 0.0
    total_video_frames_seen = 0
    total_frames_without_face = 0

    with torch.inference_mode():
        for video_index, row in enumerate(dataset):
            label = _sdfvd_label_to_int(row["label"])
            video_name = _sdfvd_video_name(row, video_index)
            batch_images: list[torch.Tensor] = []
            batch_frame_indices: list[int] = []
            current_fake_run = 0
            longest_fake_run = 0
            video_frame_count = 0
            video_frames_seen = 0
            video_frames_without_face = 0

            def evaluate_frame_batch() -> None:
                nonlocal current_fake_run, longest_fake_run, total_frame_loss
                if not batch_images:
                    return
                images = torch.stack(batch_images).to(device)
                logits = model(images).reshape(-1)
                targets = torch.full_like(logits, float(label))
                total_frame_loss += float(
                    loss_fn(logits.reshape(-1, 1), targets.reshape(-1, 1)).item()
                ) * len(batch_images)

                for frame_index, logit in zip(batch_frame_indices, logits.detach().cpu()):
                    logit_value = float(logit.item())
                    predicted_fake = _sdfvd_frame_is_fake(logit_value, real_logit_threshold)
                    predicted_label = FAKE_LABEL if predicted_fake else REAL_LABEL
                    if predicted_label == FAKE_LABEL:
                        current_fake_run += 1
                        longest_fake_run = max(longest_fake_run, current_fake_run)
                    else:
                        current_fake_run = 0
                    frame_logits.append(logit_value)
                    frame_labels.append(label)
                    frame_prediction_rows.append(
                        {
                            "video_index": video_index,
                            "video": video_name,
                            "frame_index": frame_index,
                            "true_label": "fake" if label == FAKE_LABEL else "real",
                            "predicted_label": (
                                "fake" if predicted_label == FAKE_LABEL else "real"
                            ),
                            "logit_real": logit_value,
                            "real_logit_threshold": real_logit_threshold,
                            "consecutive_fake_frames": current_fake_run,
                        }
                    )
                batch_images.clear()
                batch_frame_indices.clear()

            for frame_index, frame in _iter_video_frames(row["video"]):
                total_video_frames_seen += 1
                video_frames_seen += 1
                face_crop = crop_face(frame)
                if face_crop is None:
                    evaluate_frame_batch()
                    current_fake_run = 0
                    total_frames_without_face += 1
                    video_frames_without_face += 1
                    continue
                batch_images.append(transform(face_crop.image))
                batch_frame_indices.append(frame_index)
                video_frame_count += 1
                if len(batch_images) >= frame_batch_size:
                    evaluate_frame_batch()
            evaluate_frame_batch()

            video_stats.append(
                {
                    "video_index": video_index,
                    "video": video_name,
                    "true_label": "fake" if label == FAKE_LABEL else "real",
                    "frames_seen": video_frames_seen,
                    "frames_evaluated": video_frame_count,
                    "frames_without_detected_face": video_frames_without_face,
                }
            )

    if not video_stats or not frame_labels:
        raise ValueError("SDFVD did not provide any decodable videos to evaluate")

    video_metrics, video_prediction_rows, video_labels, _video_predictions = (
        _aggregate_sdfvd_video_predictions(
            frame_prediction_rows,
            video_stats,
            consecutive_fake_frames=consecutive_fake_frames,
        )
    )
    frame_label_values = torch.tensor(frame_labels, dtype=torch.int64).numpy()
    frame_prediction_values = [
        FAKE_LABEL if row["predicted_label"] == "fake" else REAL_LABEL
        for row in frame_prediction_rows
    ]
    frame_logit_tensor = torch.tensor(frame_logits)
    try:
        frame_roc_auc = float(
            roc_auc_score(
                frame_label_values,
                torch.sigmoid(frame_logit_tensor).numpy(),
            )
        )
    except ValueError:
        frame_roc_auc = float("nan")
    frame_metrics = EvaluationMetrics(
        loss=total_frame_loss / len(frame_labels),
        accuracy=float(
            (torch.tensor(frame_prediction_values).numpy() == frame_label_values).mean()
        ),
        precision=float(
            precision_score(
                frame_label_values,
                frame_prediction_values,
                pos_label=FAKE_LABEL,
                zero_division=0,
            )
        ),
        recall=float(
            recall_score(
                frame_label_values,
                frame_prediction_values,
                pos_label=FAKE_LABEL,
                zero_division=0,
            )
        ),
        f1=float(
            f1_score(
                frame_label_values,
                frame_prediction_values,
                pos_label=FAKE_LABEL,
                zero_division=0,
            )
        ),
        roc_auc=frame_roc_auc,
    )

    fake_count = sum(label == FAKE_LABEL for label in video_labels)
    real_count = len(video_labels) - fake_count
    total_frames = len(frame_labels)
    face_detection_rate = (
        (total_video_frames_seen - total_frames_without_face) / total_video_frames_seen
        if total_video_frames_seen
        else 0.0
    )
    details: dict[str, str | int | float] = {
        "dataset": SDFVD_DATASET_ID,
        "split": "train",
        "fake_count": fake_count,
        "real_count": real_count,
        "total_videos": len(video_labels),
        "total_frames": total_frames,
        "video_frames_seen": total_video_frames_seen,
        "frames_without_detected_face": total_frames_without_face,
        "face_detection_rate": face_detection_rate,
        "consecutive_fake_frames": consecutive_fake_frames,
        "real_logit_threshold": real_logit_threshold,
    }
    print(
        f"SDFVD frame-level | real_logit_threshold={real_logit_threshold} | "
        f"face-cropped frames={total_frames}/"
        f"{total_video_frames_seen} ({face_detection_rate:.2%} detected) | "
        f"{_format_metrics(frame_metrics, positive_label=FAKE_LABEL)}",
        flush=True,
    )
    print(
        f"SDFVD sequential video-level | fake if >= {consecutive_fake_frames} "
        f"consecutive frames are predicted fake | videos={len(video_labels)} "
        f"(fake={fake_count}, real={real_count}) | "
        f"accuracy={video_metrics.accuracy:.2%} | "
        f"fake_precision={video_metrics.precision:.2%} | "
        f"fake_recall={video_metrics.recall:.2%} | "
        f"fake_f1={video_metrics.f1:.2%} | "
        f"roc_auc={video_metrics.roc_auc:.4f}",
        flush=True,
    )
    return SDFVDEvaluationResult(
        frame_metrics=frame_metrics,
        video_metrics=video_metrics,
        details=details,
        frame_predictions=tuple(frame_prediction_rows),
        video_predictions=video_prediction_rows,
        video_stats=tuple(video_stats),
    )


def evaluate_df40_robustness(
    model,
    *,
    device: torch.device,
    loss_fn,
    run_name: str,
    batch_size: int = BATCH_SIZE,
) -> list[tuple[str, EvaluationMetrics]]:
    transform = build_baseline_test_transform(model)
    _, test_split = build_image_splits(
        train_transform=transform,
        test_transform=transform,
    )
    return run_robustness_evaluation(
        model,
        test_split,
        loss_fn,
        device,
        run_name,
        RESULTS_DIR / "neural",
        batch_size=batch_size,
    )


def save_eval_summary_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    fieldnames = [
        "benchmark",
        "run_name",
        "model_name",
        "positive_label",
        "accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "loss",
        "details",
    ]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def run_full_eval_suite(
    run_name: str,
    *,
    model_name: str | None = None,
    celeb_root: Path | None = None,
    celeb_split: str = "test",
    kenjon_split: str = "test",
    seed: int = SEED,
    max_per_class: int | None = None,
    batch_size: int = BATCH_SIZE,
    skip_celebdf: bool = False,
    skip_kenjon: bool = False,
    skip_robustness: bool = False,
) -> Path:
    import torch.nn as nn

    model, checkpoint = load_trained_model(run_name, model_name=model_name)
    device = next(model.parameters()).device
    loss_fn = nn.BCEWithLogitsLoss()

    print(
        f"Eval suite | run={run_name} | model={checkpoint['model_name']} | "
        f"checkpoint episode={checkpoint['best_epoch']} "
        f"(selection accuracy {checkpoint.get('best_test_accuracy', float('nan')):.2%})",
        flush=True,
    )

    summary_rows: list[dict[str, object]] = []

    if not skip_celebdf:
        celeb_result = evaluate_celebdf_balanced(
            model,
            device=device,
            loss_fn=loss_fn,
            celeb_root=celeb_root,
            split=celeb_split,
            seed=seed,
            max_per_class=max_per_class,
            batch_size=batch_size,
        )
        summary_rows.append(
            {
                "benchmark": celeb_result.name,
                "run_name": run_name,
                "model_name": checkpoint["model_name"],
                "positive_label": celeb_result.positive_label,
                "accuracy": celeb_result.metrics.accuracy,
                "precision": celeb_result.metrics.precision,
                "recall": celeb_result.metrics.recall,
                "f1": celeb_result.metrics.f1,
                "roc_auc": celeb_result.metrics.roc_auc,
                "loss": celeb_result.metrics.loss,
                "details": str(celeb_result.details),
            }
        )

    if not skip_kenjon:
        kenjon_result = evaluate_kenjon_fake_only(
            model,
            device=device,
            loss_fn=loss_fn,
            split=kenjon_split,
            batch_size=batch_size,
        )
        summary_rows.append(
            {
                "benchmark": kenjon_result.name,
                "run_name": run_name,
                "model_name": checkpoint["model_name"],
                "positive_label": kenjon_result.positive_label,
                "accuracy": kenjon_result.metrics.accuracy,
                "precision": kenjon_result.metrics.precision,
                "recall": kenjon_result.metrics.recall,
                "f1": kenjon_result.metrics.f1,
                "roc_auc": kenjon_result.metrics.roc_auc,
                "loss": kenjon_result.metrics.loss,
                "details": str(kenjon_result.details),
            }
        )

    if not skip_robustness:
        robustness_rows = evaluate_df40_robustness(
            model,
            device=device,
            loss_fn=loss_fn,
            run_name=run_name,
            batch_size=batch_size,
        )
        for condition, metrics in robustness_rows:
            summary_rows.append(
                {
                    "benchmark": f"robustness:{condition}",
                    "run_name": run_name,
                    "model_name": checkpoint["model_name"],
                    "positive_label": REAL_LABEL,
                    "accuracy": metrics.accuracy,
                    "precision": metrics.precision,
                    "recall": metrics.recall,
                    "f1": metrics.f1,
                    "roc_auc": metrics.roc_auc,
                    "loss": metrics.loss,
                    "details": str({"condition": condition}),
                }
            )

    summary_dir = RESULTS_DIR / "neural"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / f"{run_name}_eval_summary.csv"
    save_eval_summary_csv(summary_path, summary_rows)
    print(f"Eval summary saved to {summary_path}", flush=True)
    return summary_path
