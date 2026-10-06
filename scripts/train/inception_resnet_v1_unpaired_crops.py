"""Train Inception-ResNet-v1 on DF40 face crops with independent per-image detection."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import time
from pathlib import Path

from look_again.paths import MPLCONFIG_DIR

os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIG_DIR))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

from look_again.df40_subset import UNPAIRED_FACE_CROP_DATASET_PATH, ensure_unpaired_face_crop_dataset
from scripts.train.inception_resnet_v1_140k import (
    CHECKPOINT_DIR,
    RESULTS_DIR,
    SEED,
    build_dataloaders,
    choose_device,
    run_epoch,
)
from look_again.models.inception_resnet_v1 import InceptionResnetV1

RUN_NAME = "inception_resnet_v1_unpaired_crops"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=UNPAIRED_FACE_CROP_DATASET_PATH)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-5)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument("--test-fraction", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda", "mps"), default="auto")
    parser.add_argument(
        "--pretrained",
        choices=("vggface2", "casia-webface", "none"),
        default="vggface2",
    )
    parser.add_argument(
        "--rebuild-unpaired-crops",
        action="store_true",
        help="Re-run independent face detection over DF40 before training.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_unpaired_face_crop_dataset(force=args.rebuild_unpaired_crops)
    if not args.dataset_root.is_dir():
        raise FileNotFoundError(f"Unpaired crop dataset missing: {args.dataset_root}")

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    device = choose_device(args.device)
    train_loader, validation_loader, test_loader, split_metadata = build_dataloaders(args, device)
    pretrained = None if args.pretrained == "none" else args.pretrained
    model = InceptionResnetV1(pretrained=pretrained, classify=True, num_classes=2).to(device)
    optimizer = torch.optim.Adam(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )
    criterion = nn.CrossEntropyLoss()

    checkpoint_path = CHECKPOINT_DIR / f"{RUN_NAME}_best.pt"
    history_path = RESULTS_DIR / f"{RUN_NAME}_training.csv"
    plot_path = RESULTS_DIR / f"{RUN_NAME}_training.png"
    summary_path = RESULTS_DIR / f"{RUN_NAME}_summary.json"
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Run: {RUN_NAME} | crop_strategy=independent_per_image_v1")
    print(f"Dataset: {split_metadata['dataset_root']}")
    print(
        f"Examples: train={len(train_loader.dataset):,}, "
        f"validation={len(validation_loader.dataset):,}, test={len(test_loader.dataset):,}",
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
        validation_loss, validation_accuracy, *_ = run_epoch(
            model, validation_loader, criterion, device
        )
        elapsed = time.perf_counter() - started
        row = {
            "epoch": epoch,
            "train_loss": train_loss,
            "train_accuracy": train_accuracy,
            "validation_loss": validation_loss,
            "validation_accuracy": validation_accuracy,
            "seconds": elapsed,
        }
        history.append(row)
        with history_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(history[0]))
            writer.writeheader()
            writer.writerows(history)

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
                    "image_size": 160,
                    "pretrained": args.pretrained,
                    "split_metadata": split_metadata,
                    "crop_strategy": "independent_per_image_v1",
                },
                checkpoint_path,
            )
        print(
            f"Epoch {epoch:02d}/{args.epochs} | "
            f"train loss: {train_loss:.4f}, train accuracy: {train_accuracy:.2%} | "
            f"val loss: {validation_loss:.4f}, val accuracy: {validation_accuracy:.2%} | "
            f"{elapsed:.1f}s" + (" | best" if is_best else ""),
            flush=True,
        )
        epochs = [item["epoch"] for item in history]
        figure, axes = plt.subplots(1, 2, figsize=(12, 4.5))
        axes[0].plot(epochs, [item["train_loss"] for item in history], label="Train")
        axes[0].plot(epochs, [item["validation_loss"] for item in history], label="Validation")
        axes[0].set(title="Loss", xlabel="Epoch")
        axes[0].legend()
        axes[1].plot(epochs, [item["train_accuracy"] for item in history], label="Train")
        axes[1].plot(epochs, [item["validation_accuracy"] for item in history], label="Validation")
        axes[1].set(title="Accuracy", xlabel="Epoch", ylim=(0, 1))
        axes[1].legend()
        figure.suptitle("Inception-ResNet-v1 — unpaired DF40 face crops")
        figure.tight_layout()
        figure.savefig(plot_path, dpi=160, bbox_inches="tight")
        plt.close(figure)

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["state_dict"])
    test_loss, test_accuracy, labels, fake_scores, predictions = run_epoch(
        model, test_loader, criterion, device
    )
    fake_targets = [int(label == 0) for label in labels]
    test_summary = {
        "model": "Inception-ResNet-v1",
        "run_name": RUN_NAME,
        "dataset_root": split_metadata["dataset_root"],
        "crop_strategy": "independent_per_image_v1",
        "best_epoch": best_epoch,
        "test_loss": test_loss,
        "test_accuracy": test_accuracy,
        "test_fake_precision": precision_score(
            fake_targets, [int(pred == 0) for pred in predictions], zero_division=0
        ),
        "test_fake_recall": recall_score(
            fake_targets, [int(pred == 0) for pred in predictions], zero_division=0
        ),
        "test_macro_f1": f1_score(labels, predictions, average="macro", zero_division=0),
        "test_roc_auc": roc_auc_score(fake_targets, fake_scores),
        "test_examples": len(labels),
        "split_metadata": split_metadata,
        "arguments": vars(args),
    }
    summary_path.write_text(json.dumps(test_summary, indent=2, default=str) + "\n", encoding="utf-8")
    print(
        f"Best epoch {best_epoch} | test accuracy: {accuracy_score(labels, predictions):.2%}, "
        f"macro F1: {test_summary['test_macro_f1']:.4f}",
        flush=True,
    )
    print(f"Checkpoint: {checkpoint_path}")
    print(f"SDFVD eval: uv run python -m scripts.evaluate.sdfvd --run-name {RUN_NAME}")


if __name__ == "__main__":
    main()
