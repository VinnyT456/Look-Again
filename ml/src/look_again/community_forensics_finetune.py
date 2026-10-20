"""Fine-tune CommunityForensics ViT for new data (probe and optional backbone)."""

from __future__ import annotations

import json
import random
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm
from transformers import ViTForImageClassification, ViTImageProcessor

from look_again.community_forensics_vit_probe import (
    MODEL_CACHE,
    PROBE_SPLIT_SEED,
    build_rich_matrix_from_feature_dict,
    fit_universal_rich_linear_probe,
    load_community_forensics_vit,
    load_feature_npz,
    sklearn_linear_probe_weights,
)
from look_again.hf_binary_dataset import IMAGE_EXTENSIONS, is_readable_image
from look_again.paths import CHECKPOINT_DIR, PROJECT_ROOT

Mode = Literal["probe", "backbone", "all"]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "community_forensics_finetune.json"


@dataclass
class BackboneFinetuneConfig:
    epochs: int = 5
    learning_rate: float = 1e-5
    weight_decay: float = 0.01
    train_classifier_only: bool = True


@dataclass
class FinetuneConfig:
    run_name: str = "custom_probe"
    dataset_root: Path | None = None
    fake_dir: str = "fake"
    real_dir: str = "real"
    mode: Mode = "probe"
    mix_base_feature_caches: bool = True
    max_per_class_subsample: int = 1000
    train_val_fraction: float = 0.8
    logistic_c: float = 0.01
    random_seed: int = PROBE_SPLIT_SEED
    batch_size: int = 32
    rebuild_feature_cache: bool = False
    backbone: BackboneFinetuneConfig = field(default_factory=BackboneFinetuneConfig)
    output_dir: Path | None = None

    def resolved_output_dir(self) -> Path:
        if self.output_dir is not None:
            return self.output_dir
        return CHECKPOINT_DIR / "community_forensics_finetune" / self.run_name

    def resolved_dataset_root(self) -> Path:
        if self.dataset_root is None:
            raise ValueError(
                "dataset_root is not set. Copy config/community_forensics_finetune.example.json "
                "to config/community_forensics_finetune.json and set dataset_root to your folder."
            )
        root = Path(self.dataset_root)
        if not root.is_absolute():
            root = (PROJECT_ROOT / root).resolve()
        return root

    def feature_cache_path(self) -> Path:
        return MODEL_CACHE / f"finetune_{self.run_name}_vit_features.npz"


def load_finetune_config(path: Path | None = None) -> FinetuneConfig:
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        raise FileNotFoundError(
            f"Missing config at {config_path}. "
            f"Copy {PROJECT_ROOT / 'config' / 'community_forensics_finetune.example.json'} "
            "and set dataset_root."
        )
    raw: dict[str, Any] = json.loads(config_path.read_text())
    backbone_raw = raw.pop("backbone", {}) or {}
    backbone = BackboneFinetuneConfig(**backbone_raw)
    if raw.get("dataset_root") is not None:
        raw["dataset_root"] = Path(raw["dataset_root"])
    if raw.get("output_dir") is not None:
        raw["output_dir"] = Path(raw["output_dir"])
    return FinetuneConfig(**raw, backbone=backbone)


def list_images(folder: Path) -> list[Path]:
    return sorted(
        path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def load_binary_image_dataset(
    root: Path,
    *,
    fake_dir: str = "fake",
    real_dir: str = "real",
) -> list[tuple[Path, int]]:
    samples: list[tuple[Path, int]] = []
    for label_name, label in ((fake_dir, 1), (real_dir, 0)):
        folder = root / label_name
        if not folder.is_dir():
            raise FileNotFoundError(f"Expected class folder: {folder}")
        paths = list_images(folder)
        for path in tqdm(
            paths,
            desc=f"scan {label_name}",
            unit="img",
            file=sys.stderr,
        ):
            if not is_readable_image(path):
                tqdm.write(f"Skipping unreadable image: {path}", file=sys.stderr)
                continue
            samples.append((path, label))
    if not samples:
        raise ValueError(f"No images found under {root} ({fake_dir}/, {real_dir}/)")
    return samples


def stratified_split(
    samples: list[tuple[Path, int]],
    *,
    train_fraction: float,
    seed: int,
) -> tuple[list[tuple[Path, int]], list[tuple[Path, int]]]:
    by_label: dict[int, list[tuple[Path, int]]] = {0: [], 1: []}
    for path, label in samples:
        by_label[label].append((path, label))
    rng = random.Random(seed)
    train: list[tuple[Path, int]] = []
    val: list[tuple[Path, int]] = []
    for label in (0, 1):
        bucket = by_label[label][:]
        rng.shuffle(bucket)
        n_train = int(len(bucket) * train_fraction)
        train.extend(bucket[:n_train])
        val.extend(bucket[n_train:])
    rng.shuffle(train)
    rng.shuffle(val)
    return train, val


def pick_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def extract_vit_features(
    samples: list[tuple[Path, int]],
    model: ViTForImageClassification,
    processor: ViTImageProcessor,
    device: torch.device,
    *,
    batch_size: int,
    cache_path: Path,
    rebuild_cache: bool,
    desc: str = "extract_vit",
) -> dict[str, np.ndarray]:
    paths = [path for path, _ in samples]
    labels = [label for _, label in samples]
    rel_paths = np.array([str(path.resolve()) for path in paths])
    if cache_path.is_file() and not rebuild_cache:
        data = np.load(cache_path, allow_pickle=False)
        if "paths" in data.files and np.array_equal(data["paths"], rel_paths):
            tqdm.write(f"{desc}: using cache {cache_path}", file=sys.stderr)
            return {key: data[key] for key in data.files}

    n = len(paths)
    hidden_dim = model.config.hidden_size
    cls_orig = np.zeros((n, hidden_dim), dtype=np.float32)
    cls_flip = np.zeros((n, hidden_dim), dtype=np.float32)
    patch_mean = np.zeros((n, hidden_dim), dtype=np.float32)
    patch_std = np.zeros((n, hidden_dim), dtype=np.float32)
    logit_orig = np.zeros(n, dtype=np.float32)
    logit_flip = np.zeros(n, dtype=np.float32)

    for start in tqdm(
        range(0, n, batch_size),
        desc=desc,
        unit="batch",
        file=sys.stderr,
    ):
        end = min(start + batch_size, n)
        batch_paths = paths[start:end]
        images_orig = [Image.open(path).convert("RGB") for path in batch_paths]
        images_expanded: list[Image.Image] = []
        for image in images_orig:
            images_expanded.append(image)
            images_expanded.append(image.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
        inputs = processor(images=images_expanded, return_tensors="pt")
        inputs = {key: value.to(device=device, dtype=torch.float32) for key, value in inputs.items()}
        with torch.inference_mode():
            vit_out = model.vit(**inputs)
            seq = vit_out.last_hidden_state.float()
            cls_tokens = seq[:, 0, :]
            patches = seq[:, 1:, :]
            logits = model.classifier(cls_tokens).squeeze(-1)

            batch_len = end - start
            cls_pair = cls_tokens.reshape(batch_len, 2, hidden_dim)
            patches_pair = patches.reshape(batch_len, 2 * patches.size(1), hidden_dim)
            logits_pair = logits.reshape(batch_len, 2)

            cls_orig[start:end] = cls_pair[:, 0, :].cpu().numpy()
            cls_flip[start:end] = cls_pair[:, 1, :].cpu().numpy()
            patch_mean[start:end] = patches_pair.mean(dim=1).cpu().numpy()
            patch_std[start:end] = patches_pair.std(dim=1).cpu().numpy()
            logit_orig[start:end] = logits_pair[:, 0].cpu().numpy()
            logit_flip[start:end] = logits_pair[:, 1].cpu().numpy()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "paths": rel_paths,
        "labels": np.array(labels, dtype=np.int64),
        "cls_orig": cls_orig,
        "cls_flip": cls_flip,
        "patch_mean": patch_mean,
        "patch_std": patch_std,
        "logit_orig": logit_orig,
        "logit_flip": logit_flip,
    }
    np.savez(cache_path, **payload)
    return payload


FEATURE_PAYLOAD_KEYS = (
    "paths",
    "labels",
    "cls_orig",
    "cls_flip",
    "patch_mean",
    "patch_std",
    "logit_orig",
    "logit_flip",
)


def rich_matrix_from_payload(payload: dict[str, np.ndarray]) -> np.ndarray:
    feats = {key: payload[key] for key in ("cls_orig", "cls_flip", "patch_mean", "patch_std", "logit_orig", "logit_flip")}
    return build_rich_matrix_from_feature_dict(feats)


def merge_feature_payloads(
    existing: dict[str, np.ndarray] | None,
    new: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    if existing is None or len(existing.get("labels", [])) == 0:
        return new
    merged: dict[str, np.ndarray] = {}
    for key in FEATURE_PAYLOAD_KEYS:
        if key not in new:
            continue
        if key not in existing:
            merged[key] = new[key]
            continue
        if key == "paths":
            merged[key] = np.concatenate([existing[key], new[key]])
        else:
            merged[key] = np.concatenate([existing[key], new[key]], axis=0)
    return merged


def load_feature_payload(cache_path: Path) -> dict[str, np.ndarray] | None:
    if not cache_path.is_file():
        return None
    data = np.load(cache_path, allow_pickle=False)
    return {key: data[key] for key in data.files}


def stratified_split_indices(
    labels: np.ndarray,
    *,
    train_fraction: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    by_label: dict[int, list[int]] = {0: [], 1: []}
    for index, label in enumerate(labels.astype(np.int64)):
        by_label[int(label)].append(index)
    rng = random.Random(seed)
    train_idx: list[int] = []
    val_idx: list[int] = []
    for label in (0, 1):
        bucket = by_label[label][:]
        rng.shuffle(bucket)
        n_train = int(len(bucket) * train_fraction)
        train_idx.extend(bucket[:n_train])
        val_idx.extend(bucket[n_train:])
    train_idx.sort()
    val_idx.sort()
    return np.array(train_idx, dtype=np.int64), np.array(val_idx, dtype=np.int64)


def slice_feature_payload(payload: dict[str, np.ndarray], indices: np.ndarray) -> dict[str, np.ndarray]:
    return {key: payload[key][indices] for key in payload}


def run_probe_finetune_from_features(
    config: FinetuneConfig,
    *,
    train_payload: dict[str, np.ndarray],
    val_payload: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Fit rich linear probe from pre-extracted ViT feature caches (no image I/O)."""
    output_dir = config.resolved_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    x_train = rich_matrix_from_payload(train_payload)
    y_train = train_payload["labels"].astype(np.int64)
    x_val = rich_matrix_from_payload(val_payload)
    y_val = val_payload["labels"].astype(np.int64)

    if config.mix_base_feature_caches:
        x_base, y_base = collect_base_cache_training_rows(
            val_fraction=config.train_val_fraction,
            seed=config.random_seed,
            max_per_class_subsample=config.max_per_class_subsample,
        )
        if len(x_base):
            tqdm.write(f"mix base: +{len(x_base)} training rows", file=sys.stderr)
            x_train = np.concatenate([x_train, x_base], axis=0)
            y_train = np.concatenate([y_train, y_base], axis=0)

    tqdm.write(
        f"fitting logistic probe on {len(x_train)} rows ({int(np.sum(y_train == 1))} fake, "
        f"{int(np.sum(y_train == 0))} real)…",
        file=sys.stderr,
    )
    pipeline = fit_probe_pipeline(x_train, y_train, c=config.logistic_c, seed=config.random_seed)
    tqdm.write("scoring validation…", file=sys.stderr)
    val_prob = pipeline.predict_proba(x_val)[:, 1]

    weights_path = output_dir / "community_forensics_vit_rich_probe_weights.npz"
    save_probe_weights(pipeline, weights_path)

    return {
        "val_metrics": probe_metrics(y_val, val_prob),
        "probe_weights": str(weights_path),
        "n_train_features": int(len(y_train)),
        "n_val_features": int(len(y_val)),
    }


def collect_base_cache_training_rows(
    *,
    val_fraction: float,
    seed: int,
    max_per_class_subsample: int,
) -> tuple[np.ndarray, np.ndarray]:
    cache_specs = [
        MODEL_CACHE / "deepfake_vit_features.npz",
        MODEL_CACHE / "cross_sdfvd_face_frames_val_features.npz",
        MODEL_CACHE / "cross_df40_face_crops_unpaired_features.npz",
        MODEL_CACHE / "cross_real_vs_fake_140k_test_features.npz",
    ]
    x_parts: list[np.ndarray] = []
    y_parts: list[np.ndarray] = []
    rng = random.Random(seed)
    for cache_path in tqdm(cache_specs, desc="mix base caches", unit="cache", file=sys.stderr):
        loaded = load_feature_npz(cache_path)
        if loaded is None:
            tqdm.write(f"mix base: skip missing {cache_path.name}", file=sys.stderr)
            continue
        x_all, y_all = loaded
        by_label: dict[int, list[int]] = {0: [], 1: []}
        for idx, label in enumerate(y_all):
            by_label[int(label)].append(idx)
        indices: list[int] = []
        for label in (0, 1):
            bucket = by_label[label][:]
            rng.shuffle(bucket)
            if max_per_class_subsample and len(bucket) > max_per_class_subsample:
                bucket = bucket[:max_per_class_subsample]
            indices.extend(bucket)
        indices.sort()
        x_sub = x_all[indices]
        y_sub = y_all[indices]
        train_idx: list[int] = []
        by_label = {0: [], 1: []}
        for idx, label in enumerate(y_sub):
            by_label[int(label)].append(idx)
        for label in (0, 1):
            bucket = by_label[label][:]
            rng.shuffle(bucket)
            train_idx.extend(bucket[: int(len(bucket) * val_fraction)])
        train_idx.sort()
        x_parts.append(x_sub[train_idx])
        y_parts.append(y_sub[train_idx])
    if not x_parts:
        return np.zeros((0, 1538), dtype=np.float32), np.zeros(0, dtype=np.int64)
    return np.concatenate(x_parts, axis=0), np.concatenate(y_parts, axis=0)


def probe_metrics(y_true: np.ndarray, fake_prob: np.ndarray, threshold: float = 0.5) -> dict[str, float]:
    y_pred = (fake_prob >= threshold).astype(np.int64)
    metrics: dict[str, float] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "n_samples": float(len(y_true)),
    }
    if len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_true, fake_prob))
    return metrics


def fit_probe_pipeline(x_train: np.ndarray, y_train: np.ndarray, *, c: float, seed: int) -> Pipeline:
    return fit_universal_rich_linear_probe(x_train, y_train, c=c, seed=seed)


def save_probe_weights(pipeline: Pipeline, output_path: Path) -> None:
    weights = sklearn_linear_probe_weights(pipeline)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output_path,
        mean=weights.mean,
        scale=weights.scale,
        coef=weights.coef,
        intercept=weights.intercept,
    )


class _LabeledImageDataset(Dataset):
    def __init__(self, samples: list[tuple[Path, int]], processor: ViTImageProcessor) -> None:
        self.samples = samples
        self.processor = processor

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        path, label = self.samples[index]
        image = Image.open(path).convert("RGB")
        pixel_values = self.processor(images=image, return_tensors="pt")["pixel_values"].squeeze(0)
        return pixel_values, torch.tensor(label, dtype=torch.float32)


def finetune_backbone(
    train_samples: list[tuple[Path, int]],
    val_samples: list[tuple[Path, int]],
    config: FinetuneConfig,
    device: torch.device,
) -> Path:
    model, processor = load_community_forensics_vit(device)
    if config.backbone.train_classifier_only:
        for param in model.vit.parameters():
            param.requires_grad = False
    else:
        for param in model.parameters():
            param.requires_grad = True
    for param in model.classifier.parameters():
        param.requires_grad = True

    train_loader = DataLoader(
        _LabeledImageDataset(train_samples, processor),
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=0,
    )
    val_loader = DataLoader(
        _LabeledImageDataset(val_samples, processor),
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=0,
    )
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=config.backbone.learning_rate,
        weight_decay=config.backbone.weight_decay,
    )
    loss_fn = nn.BCEWithLogitsLoss()

    best_val_auc = -1.0
    output_dir = config.resolved_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / "vit_backbone_best.pt"

    for epoch in range(config.backbone.epochs):
        model.train()
        train_loss = 0.0
        for pixel_values, labels in tqdm(
            train_loader,
            desc=f"backbone epoch {epoch + 1}",
            unit="batch",
            file=sys.stderr,
        ):
            pixel_values = pixel_values.to(device)
            labels = labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(pixel_values=pixel_values).logits.squeeze(-1)
            loss = loss_fn(logits, labels)
            loss.backward()
            optimizer.step()
            train_loss += float(loss.item()) * len(labels)
        train_loss /= max(len(train_samples), 1)

        model.eval()
        val_probs: list[float] = []
        val_labels: list[int] = []
        with torch.inference_mode():
            for pixel_values, labels in tqdm(
                val_loader,
                desc=f"backbone val epoch {epoch + 1}",
                unit="batch",
                file=sys.stderr,
            ):
                pixel_values = pixel_values.to(device)
                logits = model(pixel_values=pixel_values).logits.squeeze(-1)
                probs = torch.sigmoid(logits).cpu().numpy().tolist()
                if isinstance(probs, float):
                    probs = [probs]
                val_probs.extend(probs)
                val_labels.extend(labels.int().tolist())
        val_metrics = probe_metrics(np.array(val_labels), np.array(val_probs))
        val_auc = val_metrics.get("roc_auc", val_metrics["accuracy"])
        if val_auc >= best_val_auc:
            best_val_auc = val_auc
            torch.save({"model_state_dict": model.state_dict(), "epoch": epoch}, checkpoint_path)

    return checkpoint_path


def run_finetune(config: FinetuneConfig) -> dict[str, Any]:
    device = pick_device()
    tqdm.write(f"device: {device}", file=sys.stderr)
    dataset_root = config.resolved_dataset_root()
    output_dir = config.resolved_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    tqdm.write(f"indexing images under {dataset_root}", file=sys.stderr)
    samples = load_binary_image_dataset(
        dataset_root,
        fake_dir=config.fake_dir,
        real_dir=config.real_dir,
    )
    train_samples, val_samples = stratified_split(
        samples,
        train_fraction=config.train_val_fraction,
        seed=config.random_seed,
    )

    report: dict[str, Any] = {
        "config": json.loads(json.dumps({**asdict(config), "dataset_root": str(dataset_root)}, default=str)),
        "dataset": {
            "root": str(dataset_root),
            "n_total": len(samples),
            "n_train": len(train_samples),
            "n_val": len(val_samples),
        },
    }

    backbone_ckpt: Path | None = None
    if config.mode in ("backbone", "all"):
        backbone_ckpt = finetune_backbone(train_samples, val_samples, config, device)
        report["backbone_checkpoint"] = str(backbone_ckpt)

    if config.mode in ("probe", "all"):
        tqdm.write("Loading CommunityForensics ViT…", file=sys.stderr)
        model, processor = load_community_forensics_vit(device)
        if backbone_ckpt is not None and backbone_ckpt.is_file():
            state = torch.load(backbone_ckpt, map_location=device, weights_only=True)
            model.load_state_dict(state["model_state_dict"])
        model.eval()

        cache_path = config.feature_cache_path()
        train_payload = extract_vit_features(
            train_samples,
            model,
            processor,
            device,
            batch_size=config.batch_size,
            cache_path=cache_path.with_name(cache_path.stem + "_train.npz"),
            rebuild_cache=config.rebuild_feature_cache,
            desc="extract_vit train",
        )
        val_payload = extract_vit_features(
            val_samples,
            model,
            processor,
            device,
            batch_size=config.batch_size,
            cache_path=cache_path.with_name(cache_path.stem + "_val.npz"),
            rebuild_cache=config.rebuild_feature_cache,
            desc="extract_vit val",
        )

        x_train = rich_matrix_from_payload(train_payload)
        y_train = train_payload["labels"].astype(np.int64)
        x_val = rich_matrix_from_payload(val_payload)
        y_val = val_payload["labels"].astype(np.int64)

        if config.mix_base_feature_caches:
            x_base, y_base = collect_base_cache_training_rows(
                val_fraction=config.train_val_fraction,
                seed=config.random_seed,
                max_per_class_subsample=config.max_per_class_subsample,
            )
            if len(x_base):
                tqdm.write(f"mix base: +{len(x_base)} training rows", file=sys.stderr)
                x_train = np.concatenate([x_train, x_base], axis=0)
                y_train = np.concatenate([y_train, y_base], axis=0)

        tqdm.write(
            f"fitting logistic probe on {len(x_train)} rows ({int(np.sum(y_train == 1))} fake, "
            f"{int(np.sum(y_train == 0))} real)…",
            file=sys.stderr,
        )
        pipeline = fit_probe_pipeline(x_train, y_train, c=config.logistic_c, seed=config.random_seed)
        tqdm.write("scoring validation…", file=sys.stderr)
        val_prob = pipeline.predict_proba(x_val)[:, 1]
        report["val_metrics"] = probe_metrics(y_val, val_prob)

        weights_path = output_dir / "community_forensics_vit_rich_probe_weights.npz"
        save_probe_weights(pipeline, weights_path)
        report["probe_weights"] = str(weights_path)
        report["feature_caches"] = {
            "train": str(cache_path.with_name(cache_path.stem + "_train.npz")),
            "val": str(cache_path.with_name(cache_path.stem + "_val.npz")),
        }

    report_path = output_dir / "finetune_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    report["report_path"] = str(report_path)
    return report
