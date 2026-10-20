"""Shared local image dataset loading and identity-safe train/test splitting."""

from __future__ import annotations

import csv
import math
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import torch
from torch.utils.data import Subset
from torchvision.datasets import ImageFolder

from look_again.df40_subset import (
    FACE_CROP_DATASET_PATH as PAIR_CONTROLLED_DATASET_PATH,
    LEGACY_FACE_CROP_DATASET_PATH,
    ensure_face_crop_dataset,
)
from look_again.forensic_preprocessing import ForensicChannelsTransform


DATASET_ID = "Existing DF40 face crops (inswap subset)"
DATASET_PATH = LEGACY_FACE_CROP_DATASET_PATH
TEST_SIZE = 0.3
SEED = 42


@dataclass(frozen=True)
class GroupedImageSplit:
    """ImageFolder subset plus the root and group IDs aligned with subset order."""

    dataset: Subset
    group_ids: tuple[str, ...]
    class_names: tuple[str, ...]
    dataset_root: Path


class _PathAwareImageFolder(ImageFolder):
    """ImageFolder variant that passes source paths to cached transforms."""

    def __getitem__(self, index: int):
        path, target = self.samples[index]
        sample = self.loader(path)
        if self.transform is not None:
            sample = self.transform(sample, source_path=path)
        if self.target_transform is not None:
            target = self.target_transform(target)
        return sample, target


def _make_grouped_split(
    indices: list[int],
    group_ids: tuple[str, ...],
    class_names: tuple[str, ...],
    transform: Callable | None,
    dataset_root: Path,
) -> GroupedImageSplit:
    folder_type = (
        _PathAwareImageFolder
        if isinstance(transform, ForensicChannelsTransform)
        else ImageFolder
    )
    folder = folder_type(root=str(dataset_root), transform=transform)
    return GroupedImageSplit(
        dataset=Subset(folder, indices),
        group_ids=group_ids,
        class_names=class_names,
        dataset_root=dataset_root,
    )


def grouped_split_with_transform(
    grouped: GroupedImageSplit,
    transform: Callable | None = None,
) -> GroupedImageSplit:
    """Reuse exact subset indices with a different ImageFolder transform."""
    indices = list(grouped.dataset.indices)
    return _make_grouped_split(
        indices,
        grouped.group_ids,
        grouped.class_names,
        transform,
        grouped.dataset_root,
    )


def build_image_splits(
    transform: Callable | None = None,
    *,
    train_transform: Callable | None = None,
    test_transform: Callable | None = None,
    dataset_path: str | Path | None = None,
    test_size: float = TEST_SIZE,
    seed: int = SEED,
) -> tuple[GroupedImageSplit, GroupedImageSplit]:
    """Load existing local dataset and split connected identities into train/test."""
    if transform is not None and (
        train_transform is not None or test_transform is not None
    ):
        raise ValueError(
            "Pass either transform or train_transform/test_transform, not both."
        )
    if transform is not None:
        train_transform = transform
        test_transform = transform
    elif test_transform is None:
        test_transform = train_transform

    if not 0 < test_size < 1:
        raise ValueError(f"test_size must be between 0 and 1, got {test_size}")

    dataset_root = (
        Path(dataset_path).expanduser().resolve() if dataset_path else DATASET_PATH
    )
    metadata_path = dataset_root / "metadata.csv"
    if (
        not metadata_path.is_file()
        or any(not (dataset_root / name).is_dir() for name in ("fake", "real"))
    ):
        if dataset_root == PAIR_CONTROLLED_DATASET_PATH.resolve():
            ensure_face_crop_dataset()
        else:
            raise FileNotFoundError(
                f"Expected a local face-crop dataset with metadata.csv, fake/, and "
                f"real/ at {dataset_root}"
            )

    shutil.rmtree(dataset_root / ".cache", ignore_errors=True)

    dataset = ImageFolder(root=str(dataset_root), transform=transform)
    if dataset.classes != ["fake", "real"]:
        raise ValueError(f"Expected fake/real folders, found: {dataset.classes}")

    file_to_pair: dict[str, str] = {}
    pair_identities: dict[str, set[str]] = {}
    pair_video_ids: dict[str, str] = {}
    pair_methods: dict[str, str] = {}
    with metadata_path.open(newline="", encoding="utf-8") as metadata_file:
        for row in csv.DictReader(metadata_file):
            pair_id = row["id"]
            if pair_id in pair_identities:
                raise ValueError(f"Duplicate pair id in metadata: {pair_id}")

            for class_name, field in (("fake", "fake_file"), ("real", "real_file")):
                relative_path = Path(row[field]).as_posix()
                path_parts = Path(relative_path).parts
                if len(path_parts) != 2 or path_parts[0] != class_name:
                    raise ValueError(
                        f"Invalid {class_name} path for pair {pair_id}: {relative_path}"
                    )
                if relative_path in file_to_pair:
                    raise ValueError(f"Image appears in multiple pairs: {relative_path}")
                file_to_pair[relative_path] = pair_id

            pair_identities[pair_id] = {
                row["source_identity"],
                row["target_face"],
            }
            pair_video_ids[pair_id] = row.get("source_video_id") or row.get(
                "target_face", ""
            )
            pair_methods[pair_id] = row.get("method", "")
            if not pair_video_ids[pair_id] or not pair_methods[pair_id]:
                raise ValueError(f"Pair {pair_id} is missing video or method metadata")
            if (
                dataset_root == PAIR_CONTROLLED_DATASET_PATH.resolve()
                and row.get("same_source_crop") != "1"
            ):
                raise ValueError(
                    f"Pair {pair_id} does not use a shared genuine-anchored crop"
                )

    pair_indices: dict[str, dict[int, int]] = {pair_id: {} for pair_id in pair_identities}
    covered_paths: set[str] = set()
    for index, (image_path, label) in enumerate(dataset.samples):
        relative_path = Path(image_path).relative_to(dataset_root).as_posix()
        pair_id = file_to_pair.get(relative_path)
        if pair_id is None:
            continue
        if label in pair_indices[pair_id]:
            raise ValueError(f"Pair {pair_id} has multiple images for class {label}")
        pair_indices[pair_id][label] = index
        covered_paths.add(relative_path)

    missing_files = set(file_to_pair) - covered_paths
    if missing_files:
        raise ValueError(f"Metadata references missing images: {sorted(missing_files)[:5]}")

    expected_labels = {dataset.class_to_idx["fake"], dataset.class_to_idx["real"]}
    for pair_id, indices in pair_indices.items():
        if set(indices) != expected_labels:
            raise ValueError(f"Pair {pair_id} does not contain one fake and one real image")
    if set(pair_indices) != set(file_to_pair.values()):
        raise ValueError("Dataset files and pair metadata do not match")

    # Keep pairs sharing an identity or source video together, including transitive links.
    parent = {pair_id: pair_id for pair_id in pair_indices}

    def find_group(pair_id: str) -> str:
        if parent[pair_id] != pair_id:
            parent[pair_id] = find_group(parent[pair_id])
        return parent[pair_id]

    def union_groups(first: str, second: str) -> None:
        first_root = find_group(first)
        second_root = find_group(second)
        if first_root != second_root:
            parent[second_root] = first_root

    group_key_owner: dict[str, str] = {}
    pair_group_keys: dict[str, set[str]] = {}
    for pair_id, identities in pair_identities.items():
        group_keys = {f"identity:{identity}" for identity in identities}
        group_keys.add(f"video:{pair_video_ids[pair_id]}")
        pair_group_keys[pair_id] = group_keys
    for pair_id, group_keys in pair_group_keys.items():
        for group_key in group_keys:
            owner = group_key_owner.setdefault(group_key, pair_id)
            union_groups(pair_id, owner)

    identity_groups: dict[str, list[str]] = {}
    for pair_id in pair_indices:
        identity_groups.setdefault(find_group(pair_id), []).append(pair_id)

    generator = torch.Generator().manual_seed(seed)
    group_ids = sorted(identity_groups)
    permutation = torch.randperm(len(group_ids), generator=generator).tolist()
    test_group_count = math.ceil(len(group_ids) * test_size)
    test_groups = {group_ids[index] for index in permutation[:test_group_count]}
    test_pair_ids = {
        pair_id
        for group_id in test_groups
        for pair_id in identity_groups[group_id]
    }
    train_pair_ids = set(pair_indices) - test_pair_ids

    train_identity_ids = {
        identity for pair_id in train_pair_ids for identity in pair_identities[pair_id]
    }
    test_identity_ids = {
        identity for pair_id in test_pair_ids for identity in pair_identities[pair_id]
    }
    if train_pair_ids & test_pair_ids or train_identity_ids & test_identity_ids:
        raise RuntimeError("Leak detected between the training and test splits")
    train_video_ids = {pair_video_ids[pair_id] for pair_id in train_pair_ids}
    test_video_ids = {pair_video_ids[pair_id] for pair_id in test_pair_ids}
    if train_video_ids & test_video_ids:
        raise RuntimeError("Source video leaked between the training and test splits")

    class_names = tuple(dataset.classes)

    def make_split(pair_ids: set[str], split_transform: Callable | None) -> GroupedImageSplit:
        indices: list[int] = []
        sample_groups: list[str] = []
        for pair_id in sorted(pair_ids):
            for index in pair_indices[pair_id].values():
                indices.append(index)
                sample_groups.append(find_group(pair_id))
        return _make_grouped_split(
            indices,
            tuple(sample_groups),
            class_names,
            split_transform,
            dataset_root,
        )

    train_split = make_split(train_pair_ids, train_transform)
    test_split = make_split(test_pair_ids, test_transform)
    train_method_counts = Counter(pair_methods[pair_id] for pair_id in train_pair_ids)
    test_method_counts = Counter(pair_methods[pair_id] for pair_id in test_pair_ids)
    print(
        f"Leak-safe split: {len(train_pair_ids)} pairs in train, "
        f"{len(test_pair_ids)} in test; "
        f"{len(identity_groups) - len(test_groups)} train identity/video groups, "
        f"{len(test_groups)} test identity/video groups; "
        f"{len(train_video_ids)} train videos, {len(test_video_ids)} test videos; "
        f"{len(train_identity_ids & test_identity_ids)} shared identities; "
        f"{len(dataset.samples) - len(covered_paths)} images without complete "
        "identity metadata excluded"
    )
    print(
        f"Swap methods | train={dict(train_method_counts)} | test={dict(test_method_counts)}",
        flush=True,
    )
    if len(set(pair_methods.values())) < 2:
        print(
            "Dataset contains one swap method; cross-method generalization cannot be measured with this split.",
            flush=True,
        )
    return train_split, test_split


def hold_out_validation_split(
    train_split: GroupedImageSplit,
    *,
    val_fraction: float = 0.12,
    seed: int = SEED,
) -> tuple[GroupedImageSplit, GroupedImageSplit]:
    """Hold out identity groups from the training split for checkpoint selection."""
    if not 0 < val_fraction < 1:
        raise ValueError(f"val_fraction must be between 0 and 1, got {val_fraction}")

    unique_groups = sorted(set(train_split.group_ids))
    if len(unique_groups) < 2:
        raise ValueError("Need at least two identity groups to hold out validation data.")

    generator = torch.Generator().manual_seed(seed)
    val_group_count = max(1, math.ceil(len(unique_groups) * val_fraction))
    permutation = torch.randperm(len(unique_groups), generator=generator).tolist()
    val_groups = {unique_groups[index] for index in permutation[:val_group_count]}

    train_indices: list[int] = []
    train_groups: list[str] = []
    val_indices: list[int] = []
    val_groups_ordered: list[str] = []
    folder_indices = list(train_split.dataset.indices)
    for subset_index, group_id in enumerate(train_split.group_ids):
        image_index = folder_indices[subset_index]
        if group_id in val_groups:
            val_indices.append(image_index)
            val_groups_ordered.append(group_id)
        else:
            train_indices.append(image_index)
            train_groups.append(group_id)

    train_core = _make_grouped_split(
        train_indices,
        tuple(train_groups),
        train_split.class_names,
        train_split.dataset.dataset.transform,
        train_split.dataset_root,
    )
    val_split = _make_grouped_split(
        val_indices,
        tuple(val_groups_ordered),
        train_split.class_names,
        train_split.dataset.dataset.transform,
        train_split.dataset_root,
    )
    print(
        f"Validation holdout: {len(train_indices)} train images, "
        f"{len(val_indices)} validation images; "
        f"{len(unique_groups) - len(val_groups)} train groups, "
        f"{len(val_groups)} validation groups",
        flush=True,
    )
    return train_core, val_split
