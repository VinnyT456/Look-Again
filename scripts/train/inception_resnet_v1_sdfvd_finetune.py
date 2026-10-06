"""Fine-tune Inception-ResNet-v1 on cached SDFVD face frames plus a still-image base mix."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import time
from pathlib import Path

from look_again.paths import DATA_DIR, MPLCONFIG_DIR

os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIG_DIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from torch.utils.data import ConcatDataset, DataLoader

from look_again.dataset_140k import resolve_140k_dataset_root
from scripts.train.inception_resnet_v1_140k import (
    CHECKPOINT_DIR,
    IMAGE_SIZE,
    RESULTS_DIR,
    SEED,
    build_datasets,
    build_transforms,
    choose_device,
    run_epoch,
)
from look_again.models.inception_resnet_v1 import InceptionResnetV1
from look_again.mixed_sampling import build_balanced_source_sampler
from look_again.sdfvd_frame_dataset import CACHE_ROOT, build_sdfvd_frame_datasets

BASE_RUN_NAME = "inception_resnet_v1_140k"
RUN_NAME = "inception_resnet_v1_sdfvd_finetune"
LEGACY_FACE_CROP_ROOT = DATA_DIR / "DF40_face_crops"


def resolve_base_dataset_root(requested: Path | None) -> Path:
    if requested is not None:
        return requested.expanduser().resolve()
    if LEGACY_FACE_CROP_ROOT.is_dir():
        return LEGACY_FACE_CROP_ROOT
    return resolve_140k_dataset_root()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=None,
        help="Still-image base (default: DF40_face_crops if present, else 140K path).",
    )
    parser.add_argument(
        "--init-checkpoint",
        type=Path,
        default=CHECKPOINT_DIR / f"{BASE_RUN_NAME}_best.pt",
        help="Weights to fine-tune from.",
    )
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--weight-decay", type=float, default=1e-5)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument("--test-fraction", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda", "mps"), default="auto")
    parser.add_argument("--sdfvd-cache-root", type=Path, default=CACHE_ROOT)
    parser.add_argument("--sdfvd-val-video-fraction", type=float, default=0.2)
    parser.add_argument("--sdfvd-train-frame-stride", type=int, default=2)
    parser.add_argument("--sdfvd-max-train-frames-per-video", type=int, default=48)
    parser.add_argument(
        "--rebuild-sdfvd-cache",
        action="store_true",
        help="Re-decode HF videos and rebuild cached crops.",
    )
    return parser.parse_args()


def _write_history(path: Path, history: list[dict[str, float | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(history[0]))
        writer.writeheader()
        writer.writerows(history)


def _save_training_plot(history: list[dict[str, float | int]], path: Path) -> None:
    epochs = [row["epoch"] for row in history]
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].plot(epochs, [row["train_loss"] for row in history], label="Train")
    axes[0].plot(epochs, [row["validation_loss"] for row in history], label="SDFVD val")
    axes[0].set(title="Loss", xlabel="Epoch", ylabel="Cross-entropy loss")
    axes[0].legend()
    axes[1].plot(epochs, [row["train_accuracy"] for row in history], label="Train")
    axes[1].plot(epochs, [row["validation_accuracy"] for row in history], label="SDFVD val")
    axes[1].set(title="Accuracy", xlabel="Epoch", ylim=(0, 1))
    axes[1].legend()
    figure.suptitle("Inception-ResNet-v1 — SDFVD frame fine-tune")
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    args = parse_args()
    base_root = resolve_base_dataset_root(args.dataset_root)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    device = choose_device(args.device)
    train_transform, eval_transform = build_transforms()

    base_train, base_validation, base_test, base_metadata = build_datasets(
        base_root,
        train_transform=train_transform,
        eval_transform=eval_transform,
        validation_fraction=args.validation_fraction,
        test_fraction=args.test_fraction,
        seed=args.seed,
    )
    sdfvd_train, sdfvd_validation, sdfvd_metadata = build_sdfvd_frame_datasets(
        cache_root=args.sdfvd_cache_root,
        transform_train=train_transform,
        transform_eval=eval_transform,
        val_video_fraction=args.sdfvd_val_video_fraction,
        train_frame_stride=args.sdfvd_train_frame_stride,
        max_train_frames_per_video=args.sdfvd_max_train_frames_per_video,
        seed=args.seed,
        force_rebuild_cache=args.rebuild_sdfvd_cache,
    )

    mixed_train = ConcatDataset([base_train, sdfvd_train])
    source_lengths = [len(base_train), len(sdfvd_train)]
    train_sampler = build_balanced_source_sampler(source_lengths)
    loader_options = {
        "batch_size": args.batch_size,
        "num_workers": args.num_workers,
        "pin_memory": device.type == "cuda",
    }
    train_loader = DataLoader(
        mixed_train,
        sampler=train_sampler,
        **loader_options,
    )
    validation_loader = DataLoader(
        sdfvd_validation,
        shuffle=False,
        **loader_options,
    )

    init_path = args.init_checkpoint.expanduser().resolve()
    if not init_path.is_file():
        raise FileNotFoundError(f"Init checkpoint not found: {init_path}")
    init_ckpt = torch.load(init_path, map_location=device, weights_only=False)
    pretrained = init_ckpt.get("pretrained", "vggface2")
    if pretrained == "none":
        pretrained = None
    model = InceptionResnetV1(pretrained=pretrained, classify=True, num_classes=2).to(device)
    model.load_state_dict(init_ckpt["state_dict"])
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
    )
    criterion = nn.CrossEntropyLoss()

    checkpoint_path = CHECKPOINT_DIR / f"{RUN_NAME}_best.pt"
    history_path = RESULTS_DIR / f"{RUN_NAME}_training.csv"
    plot_path = RESULTS_DIR / f"{RUN_NAME}_training.png"
    summary_path = RESULTS_DIR / f"{RUN_NAME}_summary.json"
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fine-tune run: {RUN_NAME}")
    print(f"Init checkpoint: {init_path} (epoch {init_ckpt.get('best_epoch', '?')})")
    print(f"Device: {device}")
    print(f"Base still images: {base_root} ({base_metadata['split_description']})")
    print(
        f"Base examples: train={len(base_train):,} val={len(base_validation):,} "
        f"test={len(base_test):,}",
        flush=True,
    )
    print(
        f"SDFVD cached frames: train={sdfvd_metadata['train_frames']:,} "
        f"({sdfvd_metadata['train_videos']} videos) | "
        f"val={sdfvd_metadata['val_frames']:,} ({sdfvd_metadata['val_videos']} videos)",
        flush=True,
    )
    print(
        f"Mixed train batches sample base vs SDFVD 50/50 ({len(mixed_train):,} total rows)",
        flush=True,
    )

    history: list[dict[str, float | int]] = []
    best_accuracy = -1.0
    best_loss = float("inf")
    best_epoch = 0

    for epoch in range(1, args.epochs + 1):
        started = time.perf_counter()
        train_loss, train_accuracy, *_ = run_epoch(
            model, train_loader, criterion, device, optimizer
        )
        validation_loss, validation_accuracy, val_labels, val_fake_scores, val_predictions = (
            run_epoch(model, validation_loader, criterion, device)
        )
        elapsed = time.perf_counter() - started
        row: dict[str, float | int] = {
            "epoch": epoch,
            "train_loss": train_loss,
            "train_accuracy": train_accuracy,
            "validation_loss": validation_loss,
            "validation_accuracy": validation_accuracy,
            "seconds": elapsed,
        }
        history.append(row)
        _write_history(history_path, history)

        is_best = validation_accuracy > best_accuracy or (
            validation_accuracy == best_accuracy and validation_loss < best_loss
        )
        if is_best:
            best_accuracy = validation_accuracy
            best_loss = validation_loss
            best_epoch = epoch
            torch.save(
                {
                    "model_name": "inception_resnet_v1",
                    "run_name": RUN_NAME,
                    "state_dict": model.state_dict(),
                    "best_epoch": best_epoch,
                    "best_validation_accuracy": best_accuracy,
                    "best_validation_loss": best_loss,
                    "class_to_idx": {"fake": 0, "real": 1},
                    "image_size": IMAGE_SIZE,
                    "pretrained": init_ckpt.get("pretrained", "vggface2"),
                    "init_checkpoint": str(init_path),
                    "base_split_metadata": base_metadata,
                    "sdfvd_metadata": sdfvd_metadata,
                    "finetune": True,
                },
                checkpoint_path,
            )

        print(
            f"Epoch {epoch:02d}/{args.epochs} | "
            f"train loss: {train_loss:.4f}, acc: {train_accuracy:.2%} | "
            f"SDFVD val loss: {validation_loss:.4f}, acc: {validation_accuracy:.2%} | "
            f"{elapsed:.1f}s" + (" | best" if is_best else ""),
            flush=True,
        )
        _save_training_plot(history, plot_path)

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["state_dict"])
    val_loss, val_accuracy, labels, fake_scores, predictions = run_epoch(
        model, validation_loader, criterion, device
    )
    fake_targets = [int(label == 0) for label in labels]
    summary: dict[str, object] = {
        "model": "Inception-ResNet-v1",
        "run_name": RUN_NAME,
        "init_checkpoint": str(init_path),
        "best_epoch": best_epoch,
        "sdfvd_val_loss": val_loss,
        "sdfvd_val_accuracy": val_accuracy,
        "sdfvd_val_fake_precision": precision_score(
            fake_targets, [int(pred == 0) for pred in predictions], zero_division=0
        ),
        "sdfvd_val_fake_recall": recall_score(
            fake_targets, [int(pred == 0) for pred in predictions], zero_division=0
        ),
        "sdfvd_val_macro_f1": f1_score(labels, predictions, average="macro", zero_division=0),
        "sdfvd_val_roc_auc": roc_auc_score(fake_targets, fake_scores),
        "sdfvd_val_examples": len(labels),
        "base_split_metadata": base_metadata,
        "sdfvd_metadata": sdfvd_metadata,
        "arguments": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "seed": args.seed,
            "sdfvd_val_video_fraction": args.sdfvd_val_video_fraction,
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        f"Best epoch {best_epoch} | SDFVD val accuracy: "
        f"{accuracy_score(labels, predictions):.2%}, macro F1: {summary['sdfvd_val_macro_f1']:.4f}, "
        f"fake ROC-AUC: {summary['sdfvd_val_roc_auc']:.4f}",
        flush=True,
    )
    print(f"Checkpoint: {checkpoint_path}")
    print(f"Eval video: uv run python -m scripts.evaluate.sdfvd --run-name {RUN_NAME}")


if __name__ == "__main__":
    main()
