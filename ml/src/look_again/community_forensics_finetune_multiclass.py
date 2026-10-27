"""Three-class CommunityForensics ViT fine-tune (real / synthetic / tampered).

Uses the same frozen ViT rich features as binary fine-tune, but fits a multinomial
logistic probe (3-way head). Checkpoints live under
``checkpoints/community_forensics_sofake_tertiary/<run_name>/`` — separate from
binary ``community_forensics_finetune/``.

Label convention (So-Fake):
  0 = real
  1 = full_synthetic (gen-AI)
  2 = tampered
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm

from look_again.community_forensics_finetune import (
    list_images,
    rich_matrix_from_payload,
)
from look_again.community_forensics_vit_probe import PROBE_SPLIT_SEED, sklearn_linear_probe_weights
from look_again.hf_binary_dataset import IMAGE_EXTENSIONS
from look_again.paths import CHECKPOINT_DIR, PROJECT_ROOT

TERTIARY_CHECKPOINT_ROOT = CHECKPOINT_DIR / "community_forensics_sofake_tertiary"
TERTIARY_WEIGHTS_FILENAME = "community_forensics_vit_rich_probe_tertiary_weights.npz"
CLASS_NAMES = ("real", "synthetic", "tampered")
VERDICT_LABELS = ("Likely real", "Likely AI", "Likely edited")


@dataclass(frozen=True)
class TertiaryProbeWeights:
    mean: np.ndarray
    scale: np.ndarray
    coef: np.ndarray
    intercept: np.ndarray
    class_names: tuple[str, ...]

    @classmethod
    def from_npz(cls, path: Path) -> TertiaryProbeWeights:
        data = np.load(path, allow_pickle=False)
        if "class_names" in data.files:
            names = tuple(str(x) for x in data["class_names"].tolist())
        else:
            names = CLASS_NAMES
        coef = np.asarray(data["coef"], dtype=np.float32)
        intercept = np.asarray(data["intercept"], dtype=np.float32).reshape(-1)
        if coef.ndim == 1:
            coef = coef.reshape(1, -1)
        return cls(
            mean=np.asarray(data["mean"], dtype=np.float32),
            scale=np.asarray(data["scale"], dtype=np.float32),
            coef=coef,
            intercept=intercept,
            class_names=names,
        )


def default_tertiary_weights_path(run_name: str) -> Path:
    return TERTIARY_CHECKPOINT_ROOT / run_name / TERTIARY_WEIGHTS_FILENAME


def softmax_probs(logits: np.ndarray) -> np.ndarray:
    logits = logits.astype(np.float64)
    logits = logits - logits.max(axis=-1, keepdims=True)
    exp = np.exp(logits)
    return (exp / exp.sum(axis=-1, keepdims=True)).astype(np.float32)


def predict_probs_from_features(x: np.ndarray, weights: TertiaryProbeWeights) -> np.ndarray:
    """``x`` shape (n, feature_dim) → (n, n_classes) probabilities."""
    scaled = (x - weights.mean) / weights.scale
    logits = scaled @ weights.coef.T + weights.intercept
    return softmax_probs(logits)


def classify_tertiary_image(
    image_path: Path,
    weights: TertiaryProbeWeights,
    device: torch.device,
) -> dict[str, Any]:
    from look_again.community_forensics_vit_probe import load_community_forensics_vit, rich_features_torch

    image = Image.open(image_path).convert("RGB")
    backbone, processor = load_community_forensics_vit(device)
    pixels = processor(images=image, return_tensors="pt")["pixel_values"].float().to(device)
    with torch.inference_mode():
        features = rich_features_torch(backbone.vit, backbone.classifier, pixels)
    x = features.cpu().numpy()
    probs = predict_probs_from_features(x, weights)[0]
    class_index = int(np.argmax(probs))
    name = weights.class_names[class_index] if class_index < len(weights.class_names) else CLASS_NAMES[class_index]
    verdict = VERDICT_LABELS[class_index] if class_index < len(VERDICT_LABELS) else name
    return {
        "image": str(image_path.resolve()),
        "verdict": verdict,
        "predicted_class": name,
        "class_index": class_index,
        "confidence": float(probs[class_index]),
        "prob_real": float(probs[0]),
        "prob_synthetic": float(probs[1]),
        "prob_tampered": float(probs[2]) if probs.size > 2 else None,
        "probabilities": {weights.class_names[i]: float(probs[i]) for i in range(len(probs))},
    }


@dataclass
class TertiaryFinetuneConfig:
    run_name: str = "so_fake_tertiary_probe"
    logistic_c: float = 0.01
    train_val_fraction: float = 0.8
    random_seed: int = PROBE_SPLIT_SEED
    output_dir: Path | None = None

    def resolved_output_dir(self) -> Path:
        if self.output_dir is not None:
            return self.output_dir
        return TERTIARY_CHECKPOINT_ROOT / self.run_name


def load_tertiary_image_dataset(
    root: Path,
    *,
    real_dir: str = "real",
    synthetic_dir: str = "fake",
    tampered_dir: str = "tampered",
) -> list[tuple[Path, int]]:
    samples: list[tuple[Path, int]] = []
    for label_name, label in (
        (real_dir, 0),
        (synthetic_dir, 1),
        (tampered_dir, 2),
    ):
        folder = root / label_name
        if not folder.is_dir():
            raise FileNotFoundError(f"Expected class folder: {folder}")
        paths = list_images(folder)
        tqdm.write(f"scan {label_name}: {len(paths)} images", file=sys.stderr)
        for path in paths:
            if path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            samples.append((path, label))
    return samples


def stratified_split_indices_tertiary(
    labels: np.ndarray,
    *,
    train_fraction: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    by_label: dict[int, list[int]] = {0: [], 1: [], 2: []}
    for index, label in enumerate(labels.astype(np.int64)):
        by_label[int(label)].append(index)
    rng = random.Random(seed)
    train_idx: list[int] = []
    val_idx: list[int] = []
    for label in (0, 1, 2):
        bucket = by_label[label][:]
        rng.shuffle(bucket)
        n_train = int(len(bucket) * train_fraction)
        train_idx.extend(bucket[:n_train])
        val_idx.extend(bucket[n_train:])
    train_idx.sort()
    val_idx.sort()
    return np.array(train_idx, dtype=np.int64), np.array(val_idx, dtype=np.int64)


def fit_tertiary_probe_pipeline(
    x_train: np.ndarray,
    y_train: np.ndarray,
    *,
    c: float,
    seed: int,
) -> Pipeline:
    pipeline = Pipeline(
        [
            ("standardscaler", StandardScaler()),
            (
                "logisticregression",
                # sklearn 1.5+: no multi_class; lbfgs uses multinomial when n_classes > 2.
                LogisticRegression(
                    C=c,
                    max_iter=4000,
                    random_state=seed,
                    solver="lbfgs",
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)
    return pipeline


def tertiary_probe_metrics(y_true: np.ndarray, y_prob: np.ndarray) -> dict[str, Any]:
    """``y_prob`` shape (n, 3) in class order 0,1,2."""
    y_pred = np.argmax(y_prob, axis=1)
    metrics: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "n_samples": int(len(y_true)),
    }
    per_class_recall = recall_score(
        y_true,
        y_pred,
        labels=[0, 1, 2],
        average=None,
        zero_division=0,
    )
    for class_index, name in enumerate(CLASS_NAMES):
        if class_index < len(per_class_recall):
            metrics[f"recall_{name}"] = float(per_class_recall[class_index])
    return metrics


def save_tertiary_probe_weights(pipeline: Pipeline, output_path: Path) -> None:
    weights = sklearn_linear_probe_weights(pipeline)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output_path,
        mean=weights.mean,
        scale=weights.scale,
        coef=weights.coef,
        intercept=weights.intercept,
        num_classes=np.array([len(CLASS_NAMES)], dtype=np.int64),
        class_names=np.array(CLASS_NAMES),
    )


def run_tertiary_probe_finetune_from_features(
    config: TertiaryFinetuneConfig,
    *,
    train_payload: dict[str, np.ndarray],
    val_payload: dict[str, np.ndarray],
) -> dict[str, Any]:
    output_dir = config.resolved_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    x_train = rich_matrix_from_payload(train_payload)
    y_train = train_payload["labels"].astype(np.int64)
    x_val = rich_matrix_from_payload(val_payload)
    y_val = val_payload["labels"].astype(np.int64)

    counts = {name: int(np.sum(y_train == i)) for i, name in enumerate(CLASS_NAMES)}
    tqdm.write(
        f"fitting 3-class probe on {len(x_train)} rows "
        f"(real={counts['real']}, synthetic={counts['synthetic']}, tampered={counts['tampered']})…",
        file=sys.stderr,
    )
    pipeline = fit_tertiary_probe_pipeline(
        x_train,
        y_train,
        c=config.logistic_c,
        seed=config.random_seed,
    )
    tqdm.write("scoring validation…", file=sys.stderr)
    val_prob = pipeline.predict_proba(x_val)

    weights_path = output_dir / "community_forensics_vit_rich_probe_tertiary_weights.npz"
    save_tertiary_probe_weights(pipeline, weights_path)

    meta = {
        "task": "tertiary_real_synthetic_tampered",
        "class_names": list(CLASS_NAMES),
        "label_map": {"real": 0, "synthetic": 1, "tampered": 2},
        "feature_dim": int(x_train.shape[1]),
        "logistic_C": config.logistic_c,
        "project_root": str(PROJECT_ROOT),
    }
    (output_dir / "probe_tertiary_meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    return {
        "val_metrics": tertiary_probe_metrics(y_val, val_prob),
        "probe_weights": str(weights_path),
        "n_train_features": int(len(y_train)),
        "n_val_features": int(len(y_val)),
        "train_label_counts": counts,
    }


def label_counts_from_payload(labels: np.ndarray) -> dict[str, int]:
    labels = labels.astype(np.int64)
    return {name: int(np.sum(labels == i)) for i, name in enumerate(CLASS_NAMES)}
