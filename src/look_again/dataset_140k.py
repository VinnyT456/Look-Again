"""140K / real-vs-fake still-image datasets (predefined or flat fake/real layout)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from torchvision.datasets import ImageFolder

from look_again.dataset import GroupedImageSplit, _make_grouped_split
from look_again.paths import DATA_DIR

KAGGLE_140K_DIR = DATA_DIR / "140k-real-and-fake-faces"
REAL_VS_FAKE_DIR = DATA_DIR / "real-vs-fake"
DATASET_140K_ID = "140k-real-and-fake-faces (Kaggle / real-vs-fake)"


def resolve_140k_dataset_root(explicit: Path | str | None = None) -> Path:
    """Pick the on-disk 140K dataset root (explicit path wins, then known folders)."""
    if explicit is not None:
        root = Path(explicit).expanduser().resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"140K dataset folder does not exist: {root}")
        return root
    for candidate in (KAGGLE_140K_DIR, REAL_VS_FAKE_DIR):
        if candidate.is_dir():
            return candidate.resolve()
    raise FileNotFoundError(
        "No 140K dataset found. Extract it under "
        f"{KAGGLE_140K_DIR} or {REAL_VS_FAKE_DIR}, or pass --dataset-root."
    )


def is_140k_style_dataset(dataset_root: Path) -> bool:
    """True when root uses train/test splits or flat fake/real without DF40 metadata."""
    root = dataset_root.expanduser().resolve()
    if (root / "metadata.csv").is_file() and (root / "fake").is_dir():
        return False
    if (root / "train" / "fake").is_dir() and (root / "train" / "real").is_dir():
        return True
    if (root / "fake").is_dir() and (root / "real").is_dir():
        return True
    return False


def _split_dir_has_classes(split_dir: Path) -> bool:
    return (split_dir / "fake").is_dir() and (split_dir / "real").is_dir()


def _imagefolder_grouped_split(
    split_dir: Path,
    transform: Callable | None,
) -> GroupedImageSplit:
    if not _split_dir_has_classes(split_dir):
        raise ValueError(f"Expected fake/ and real/ under {split_dir}")
    folder = ImageFolder(root=str(split_dir), transform=transform)
    if folder.classes != ["fake", "real"]:
        raise ValueError(f"Expected fake/real class folders, found {folder.classes} in {split_dir}")
    group_ids = tuple(
        Path(path).relative_to(split_dir).as_posix() for path, _label in folder.samples
    )
    indices = list(range(len(folder)))
    return _make_grouped_split(
        indices,
        group_ids,
        tuple(folder.classes),
        transform,
        split_dir.resolve(),
    )


def try_build_140k_grouped_splits(
    dataset_root: Path,
    *,
    train_transform: Callable | None,
    eval_transform: Callable | None,
) -> tuple[GroupedImageSplit, GroupedImageSplit | None, GroupedImageSplit] | None:
    """Return train, optional val, and test splits for a 140K-style layout."""
    root = dataset_root.expanduser().resolve()
    if not is_140k_style_dataset(root):
        return None

    train_dir = root / "train"
    test_dir = root / "test"
    val_dir = root / "valid"
    if not val_dir.is_dir():
        val_dir = root / "validation"
    if not val_dir.is_dir():
        val_dir = root / "val"

    if _split_dir_has_classes(train_dir) and _split_dir_has_classes(test_dir):
        train_split = _imagefolder_grouped_split(train_dir, train_transform)
        test_split = _imagefolder_grouped_split(test_dir, eval_transform)
        val_split = None
        if _split_dir_has_classes(val_dir):
            val_split = _imagefolder_grouped_split(val_dir, eval_transform)
        print(
            f"140K predefined split at {root} | train={len(train_split.dataset)} "
            f"val={len(val_split.dataset) if val_split else 0} "
            f"test={len(test_split.dataset)}",
            flush=True,
        )
        return train_split, val_split, test_split

    if _split_dir_has_classes(root):
        # Flat fake/real — caller may stratify; expose all images as one folder split.
        flat = _imagefolder_grouped_split(root, eval_transform)
        print(
            f"140K flat layout at {root} | examples={len(flat.dataset)} "
            "(stratified train/val/test split required)",
            flush=True,
        )
        return None

    raise ValueError(
        f"140K-style folder at {root} is missing train/fake, train/real, test/fake, and test/real."
    )


def resolve_inception_140k_root(explicit: Path | str | None = None) -> Path:
    """Same as resolve_140k_dataset_root; kept for Inception train script imports."""
    return resolve_140k_dataset_root(explicit)
