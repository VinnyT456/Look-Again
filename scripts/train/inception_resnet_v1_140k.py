"""Train FaceNet Inception-ResNet-v1 on the 140K real/fake face dataset."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import time
from pathlib import Path
from typing import Sequence

from look_again.paths import CHECKPOINT_DIR, MPLCONFIG_DIR, RESULTS_DIR as PROJECT_RESULTS_DIR
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIG_DIR))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset, Subset
from torchvision import datasets, transforms

from look_again.dataset_140k import resolve_140k_dataset_root
from look_again.models.inception_resnet_v1 import InceptionResnetV1


RESULTS_DIR = PROJECT_RESULTS_DIR / "neural"
IMAGE_SIZE = 160
SEED = 42
FAKE_CLASS_NAMES = {"fake", "fakes", "generated", "synthetic"}
REAL_CLASS_NAMES = {"real", "reals", "authentic"}


class FixedFaceNetStandardization:
    """Apply FaceNet's fixed (pixel - 127.5) / 128 RGB normalization."""

    def __call__(self, image: torch.Tensor) -> torch.Tensor:
        return (image * 255.0 - 127.5) / 128.0


class BinaryFaceFolder(datasets.ImageFolder):
    """ImageFolder with stable labels: fake=0, real=1."""

    def find_classes(self, directory: str) -> tuple[list[str], dict[str, int]]:
        path = Path(directory)
        subdirectories = [
            child.name
            for child in path.iterdir()
            if child.is_dir() and not child.name.startswith(".")
        ]
        fake_dirs = [name for name in subdirectories if name.casefold() in FAKE_CLASS_NAMES]
        real_dirs = [name for name in subdirectories if name.casefold() in REAL_CLASS_NAMES]
        if len(fake_dirs) != 1 or len(real_dirs) != 1 or len(subdirectories) != 2:
            raise ValueError(
                f"Expected exactly one fake and one real class folder in {directory}; "
                f"found {subdirectories}"
            )
        classes = [fake_dirs[0], real_dirs[0]]
        return classes, {classes[0]: 0, classes[1]: 1}


def build_transforms() -> tuple[transforms.Compose, transforms.Compose]:
    normalize = FixedFaceNetStandardization()
    train = transforms.Compose(
        [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE), antialias=True),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.ToTensor(),
            normalize,
        ]
    )
    evaluate = transforms.Compose(
        [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE), antialias=True),
            transforms.ToTensor(),
            normalize,
        ]
    )
    return train, evaluate


def _valid_class_folders(path: Path) -> bool:
    if not path.is_dir():
        return False
    try:
        BinaryFaceFolder.find_classes(None, str(path))
    except (OSError, ValueError):
        return False
    return True


def _split_layout(path: Path) -> tuple[Path, Path | None, Path] | None:
    children = {child.name.casefold(): child for child in path.iterdir() if child.is_dir()}
    train = children.get("train")
    test = children.get("test")
    validation = next(
        (children[name] for name in ("validation", "valid", "val") if name in children),
        None,
    )
    if train is not None and test is not None and _valid_class_folders(train) and _valid_class_folders(test):
        if validation is not None and not _valid_class_folders(validation):
            raise ValueError(f"Validation split at {validation} does not contain fake/real folders")
        return train, validation, test
    return None


def resolve_dataset_layout(dataset_root: Path) -> tuple[str, Path | tuple[Path, Path | None, Path]]:
    root = dataset_root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(
            f"Dataset folder does not exist: {root}\n"
            "Download/extract the 140K real-and-fake-faces dataset there, or pass "
            "--dataset-root with its current location."
        )

    candidates = [root]
    first_level = sorted(
        (path for path in root.iterdir() if path.is_dir() and not path.name.startswith(".")),
        key=lambda path: path.name,
    )
    candidates.extend(first_level)
    for path in first_level:
        candidates.extend(
            sorted(
                (child for child in path.iterdir() if child.is_dir() and not child.name.startswith(".")),
                key=lambda child: child.name,
            )
        )

    for candidate in candidates:
        split_dirs = _split_layout(candidate)
        if split_dirs is not None:
            return "predefined", split_dirs
        if _valid_class_folders(candidate):
            return "flat", candidate

    raise ValueError(
        f"Could not find fake/real class folders under {root}. Expected either "
        "fake/ and real/ directories, or train/, validation/, and test/ splits "
        "that each contain fake/ and real/."
    )


def _targets(folder: Dataset) -> list[int]:
    if not isinstance(folder, BinaryFaceFolder):
        raise TypeError("Expected BinaryFaceFolder")
    return list(folder.targets)


def _split_indices(
    targets: Sequence[int],
    *,
    validation_fraction: float,
    test_fraction: float,
    seed: int,
) -> tuple[list[int], list[int], list[int]]:
    if validation_fraction <= 0 or test_fraction <= 0 or validation_fraction + test_fraction >= 1:
        raise ValueError("Validation and test fractions must be positive and sum to less than 1")
    indices = np.arange(len(targets))
    train_indices, held_out_indices = train_test_split(
        indices,
        test_size=validation_fraction + test_fraction,
        stratify=targets,
        random_state=seed,
    )
    relative_test_fraction = test_fraction / (validation_fraction + test_fraction)
    validation_indices, test_indices = train_test_split(
        held_out_indices,
        test_size=relative_test_fraction,
        stratify=np.asarray(targets)[held_out_indices],
        random_state=seed,
    )
    return train_indices.tolist(), validation_indices.tolist(), test_indices.tolist()


def _split_train_validation(
    targets: Sequence[int], *, validation_fraction: float, seed: int
) -> tuple[list[int], list[int]]:
    if validation_fraction <= 0 or validation_fraction >= 1:
        raise ValueError("Validation fraction must be greater than 0 and less than 1")
    train_indices, validation_indices = train_test_split(
        np.arange(len(targets)),
        test_size=validation_fraction,
        stratify=targets,
        random_state=seed,
    )
    return train_indices.tolist(), validation_indices.tolist()


def _subset_for_indices(
    train_folder: BinaryFaceFolder,
    eval_folder: BinaryFaceFolder,
    train_indices: list[int],
    validation_indices: list[int],
    test_indices: list[int],
) -> tuple[Dataset, Dataset, Dataset]:
    return (
        Subset(train_folder, train_indices),
        Subset(eval_folder, validation_indices),
        Subset(eval_folder, test_indices),
    )


def _assert_disjoint_paths(splits: Sequence[Dataset]) -> None:
    path_sets: list[set[str]] = []
    for split in splits:
        if isinstance(split, Subset):
            folder = split.dataset
            indices = split.indices
        else:
            folder = split
            indices = range(len(split))
        if not isinstance(folder, BinaryFaceFolder):
            raise TypeError("Expected subsets of BinaryFaceFolder")
        paths = {str(Path(folder.samples[index][0]).resolve()) for index in indices}
        path_sets.append(paths)
    for left_index, left in enumerate(path_sets):
        for right in path_sets[left_index + 1 :]:
            shared = left & right
            if shared:
                raise ValueError(f"Train/validation/test path overlap detected ({len(shared)} images)")


def build_datasets(
    dataset_root: Path,
    *,
    train_transform: transforms.Compose,
    eval_transform: transforms.Compose,
    validation_fraction: float,
    test_fraction: float,
    seed: int,
) -> tuple[Dataset, Dataset, Dataset, dict[str, object]]:
    layout, resolved = resolve_dataset_layout(dataset_root)
    if layout == "predefined":
        train_dir, validation_dir, test_dir = resolved  # type: ignore[misc]
        train_fit = BinaryFaceFolder(str(train_dir), transform=train_transform)
        train_eval = BinaryFaceFolder(str(train_dir), transform=eval_transform)
        test_dataset = BinaryFaceFolder(str(test_dir), transform=eval_transform)
        if validation_dir is not None:
            train_dataset = train_fit
            validation_dataset = BinaryFaceFolder(str(validation_dir), transform=eval_transform)
            split_description = "predefined train/validation/test folders"
        else:
            train_indices, validation_indices = _split_train_validation(
                _targets(train_eval),
                validation_fraction=validation_fraction,
                seed=seed,
            )
            train_dataset = Subset(train_fit, train_indices)
            validation_dataset = Subset(train_eval, validation_indices)
            split_description = "predefined train/test; validation held out from train"
    else:
        flat_dir = resolved  # type: ignore[assignment]
        train_folder = BinaryFaceFolder(str(flat_dir), transform=train_transform)
        eval_folder = BinaryFaceFolder(str(flat_dir), transform=eval_transform)
        train_indices, validation_indices, test_indices = _split_indices(
            _targets(train_folder),
            validation_fraction=validation_fraction,
            test_fraction=test_fraction,
            seed=seed,
        )
        train_dataset, validation_dataset, test_dataset = _subset_for_indices(
            train_folder,
            eval_folder,
            train_indices,
            validation_indices,
            test_indices,
        )
        split_description = (
            f"seeded stratified split from flat class folders "
            f"(train={1-validation_fraction-test_fraction:.0%}, "
            f"validation={validation_fraction:.0%}, test={test_fraction:.0%})"
        )

    _assert_disjoint_paths([train_dataset, validation_dataset, test_dataset])
    metadata = {
        "layout": layout,
        "split_description": split_description,
        "train_examples": len(train_dataset),
        "validation_examples": len(validation_dataset),
        "test_examples": len(test_dataset),
        "class_to_idx": {"fake": 0, "real": 1},
        "dataset_root": str(dataset_root.expanduser().resolve()),
    }
    return train_dataset, validation_dataset, test_dataset, metadata


def build_dataloaders(args: argparse.Namespace, device: torch.device):
    train_transform, eval_transform = build_transforms()
    train_dataset, validation_dataset, test_dataset, metadata = build_datasets(
        args.dataset_root,
        train_transform=train_transform,
        eval_transform=eval_transform,
        validation_fraction=args.validation_fraction,
        test_fraction=args.test_fraction,
        seed=args.seed,
    )
    loader_options = {
        "batch_size": args.batch_size,
        "num_workers": args.num_workers,
        "pin_memory": device.type == "cuda",
    }
    train_loader = DataLoader(train_dataset, shuffle=True, **loader_options)
    validation_loader = DataLoader(validation_dataset, shuffle=False, **loader_options)
    test_loader = DataLoader(test_dataset, shuffle=False, **loader_options)
    return train_loader, validation_loader, test_loader, metadata


def choose_device(requested: str) -> torch.device:
    if requested != "auto":
        if requested == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("MPS was requested but is not available in this PyTorch environment")
        if requested == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available")
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None = None,
) -> tuple[float, float, list[int], list[float], list[int]]:
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    total_correct = 0
    total_examples = 0
    labels_all: list[int] = []
    fake_scores: list[float] = []
    predictions_all: list[int] = []

    for images, labels in loader:
        images = images.to(device, non_blocking=device.type == "cuda")
        labels = labels.to(device=device, dtype=torch.long, non_blocking=device.type == "cuda")
        if training:
            optimizer.zero_grad(set_to_none=True)
        with torch.set_grad_enabled(training):
            logits = model(images)
            loss = criterion(logits, labels)
            if training:
                loss.backward()
                optimizer.step()
        batch_size = labels.size(0)
        probabilities = torch.softmax(logits.detach(), dim=1)
        predictions = probabilities.argmax(dim=1)
        total_loss += loss.item() * batch_size
        total_correct += (predictions == labels).sum().item()
        total_examples += batch_size
        labels_all.extend(labels.detach().cpu().tolist())
        predictions_all.extend(predictions.cpu().tolist())
        fake_scores.extend(probabilities[:, 0].cpu().tolist())

    return (
        total_loss / max(total_examples, 1),
        total_correct / max(total_examples, 1),
        labels_all,
        fake_scores,
        predictions_all,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=None,
        help=(
            "140K dataset root (train/valid/test or flat fake/real). "
            "Default: data/real-vs-fake or data/140k-real-and-fake-faces."
        ),
    )
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
        help="FaceNet initialization; pretrained weights download on the first run.",
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
    axes[0].plot(epochs, [row["validation_loss"] for row in history], label="Validation")
    axes[0].set(title="Loss", xlabel="Epoch", ylabel="Cross-entropy loss")
    axes[0].legend()
    axes[1].plot(epochs, [row["train_accuracy"] for row in history], label="Train")
    axes[1].plot(epochs, [row["validation_accuracy"] for row in history], label="Validation")
    axes[1].set(title="Accuracy", xlabel="Epoch", ylabel="Accuracy", ylim=(0, 1))
    axes[1].legend()
    figure.suptitle("Inception-ResNet-v1 — 140K real/fake faces")
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    args = parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.num_workers < 0:
        raise ValueError("epochs and batch size must be positive; num-workers cannot be negative")
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    device = choose_device(args.device)
    args.dataset_root = resolve_140k_dataset_root(args.dataset_root)
    train_loader, validation_loader, test_loader, split_metadata = build_dataloaders(args, device)
    pretrained = None if args.pretrained == "none" else args.pretrained
    model = InceptionResnetV1(pretrained=pretrained, classify=True, num_classes=2).to(device)
    optimizer = torch.optim.Adam(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )
    criterion = nn.CrossEntropyLoss()
    parameter_count = sum(parameter.numel() for parameter in model.parameters())

    run_name = "inception_resnet_v1_140k"
    checkpoint_path = CHECKPOINT_DIR / f"{run_name}_best.pt"
    history_path = RESULTS_DIR / f"{run_name}_training.csv"
    plot_path = RESULTS_DIR / f"{run_name}_training.png"
    summary_path = RESULTS_DIR / f"{run_name}_summary.json"
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Model: Inception-ResNet-v1 ({parameter_count / 1_000_000:.2f}M parameters)")
    print(f"Device: {device}; pretrained weights: {args.pretrained}")
    print(f"Dataset: {split_metadata['dataset_root']} ({split_metadata['split_description']})")
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
                    "state_dict": model.state_dict(),
                    "best_epoch": best_epoch,
                    "best_validation_accuracy": best_accuracy,
                    "best_validation_loss": best_loss,
                    "class_to_idx": {"fake": 0, "real": 1},
                    "image_size": IMAGE_SIZE,
                    "pretrained": args.pretrained,
                    "split_metadata": split_metadata,
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
        _save_training_plot(history, plot_path)

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["state_dict"])
    test_loss, test_accuracy, labels, fake_scores, predictions = run_epoch(
        model, test_loader, criterion, device
    )
    fake_targets = [int(label == 0) for label in labels]
    test_summary: dict[str, object] = {
        "model": "Inception-ResNet-v1",
        "dataset_root": split_metadata["dataset_root"],
        "best_epoch": best_epoch,
        "test_loss": test_loss,
        "test_accuracy": test_accuracy,
        "test_fake_precision": precision_score(fake_targets, [int(pred == 0) for pred in predictions], zero_division=0),
        "test_fake_recall": recall_score(fake_targets, [int(pred == 0) for pred in predictions], zero_division=0),
        "test_macro_f1": f1_score(labels, predictions, average="macro", zero_division=0),
        "test_roc_auc": roc_auc_score(fake_targets, fake_scores),
        "test_examples": len(labels),
        "split_metadata": split_metadata,
        "arguments": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "pretrained": args.pretrained,
            "seed": args.seed,
        },
    }
    summary_path.write_text(json.dumps(test_summary, indent=2) + "\n", encoding="utf-8")
    print(
        f"Best epoch {best_epoch} | held-out test loss: {test_loss:.4f}, "
        f"accuracy: {accuracy_score(labels, predictions):.2%}, "
        f"macro F1: {test_summary['test_macro_f1']:.4f}, "
        f"fake ROC-AUC: {test_summary['test_roc_auc']:.4f}",
        flush=True,
    )
    print(f"Checkpoint: {checkpoint_path}")
    print(f"Training metrics: {history_path}")
    print(f"Summary: {summary_path}")
    print(f"Training plot: {plot_path}")


if __name__ == "__main__":
    main()
