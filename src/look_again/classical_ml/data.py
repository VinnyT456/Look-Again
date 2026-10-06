"""Feature extraction over the repository's existing identity-safe split."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

import numpy as np
from PIL import Image

from .features import FeatureConfig, extract_features, feature_names

if TYPE_CHECKING:
    from look_again.dataset import GroupedImageSplit


@dataclass(frozen=True)
class FeatureDataset:
    """Feature matrix and labels aligned with the dataset's original class IDs."""

    X: np.ndarray
    y: np.ndarray
    group_ids: np.ndarray
    class_names: tuple[str, ...]
    feature_names: tuple[str, ...]
    sample_paths: tuple[str, ...]


def extract_image_collection(
    images: Iterable[Image.Image | np.ndarray],
    labels: Iterable[int],
    config: FeatureConfig | None = None,
    *,
    group_ids: Iterable[str] | None = None,
) -> FeatureDataset:
    """Transform in-memory images to ``X``, ``y`` while retaining optional groups."""
    config = config or FeatureConfig()
    image_list = list(images)
    label_array = np.asarray(list(labels), dtype=np.int64)
    if len(image_list) != len(label_array):
        raise ValueError("Number of images and labels must match")
    if not image_list:
        raise ValueError("At least one image is required")
    groups = (
        np.asarray(list(group_ids), dtype=str)
        if group_ids is not None
        else np.arange(len(image_list)).astype(str)
    )
    if len(groups) != len(image_list):
        raise ValueError("Number of group IDs must match number of images")

    rows = [extract_features(image, config) for image in image_list]
    matrix = np.stack(rows).astype(np.float32, copy=False)
    if not np.all(np.isfinite(matrix)):
        raise RuntimeError("Feature matrix contains NaN or infinite values")
    return FeatureDataset(
        X=matrix,
        y=label_array,
        group_ids=groups,
        class_names=(),
        feature_names=feature_names(config),
        sample_paths=(),
    )


def _split_manifest(split: GroupedImageSplit) -> list[dict[str, object]]:
    base_dataset = split.dataset.dataset
    rows = []
    for position, (dataset_index, group_id) in enumerate(
        zip(split.dataset.indices, split.group_ids, strict=True)
    ):
        path, label = base_dataset.samples[dataset_index]
        file_path = Path(path)
        stat = file_path.stat()
        rows.append(
            {
                "path": file_path.relative_to(base_dataset.root).as_posix(),
                "label": int(label),
                "group": group_id,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "position": position,
            }
        )
    return rows


def split_training_validation(
    train_split: GroupedImageSplit,
    validation_size: float = 0.15,
    seed: int = 42,
) -> tuple[GroupedImageSplit, GroupedImageSplit]:
    """Hold out validation identity groups from train, leaving original test intact."""
    if not 0 < validation_size < 1:
        raise ValueError("validation_size must be between 0 and 1")
    group_order = sorted(set(train_split.group_ids))
    if len(group_order) < 2:
        raise ValueError("At least two identity groups are required for validation")
    generator = np.random.default_rng(seed)
    permutation = generator.permutation(len(group_order))
    validation_count = min(
        len(group_order) - 1,
        max(1, int(np.ceil(len(group_order) * validation_size))),
    )
    validation_groups = {group_order[index] for index in permutation[:validation_count]}

    from look_again.dataset import GroupedImageSplit
    from torch.utils.data import Subset

    train_indices: list[int] = []
    validation_indices: list[int] = []
    train_groups: list[str] = []
    validation_group_ids: list[str] = []
    for dataset_index, group_id in zip(
        train_split.dataset.indices, train_split.group_ids, strict=True
    ):
        if group_id in validation_groups:
            validation_indices.append(dataset_index)
            validation_group_ids.append(group_id)
        else:
            train_indices.append(dataset_index)
            train_groups.append(group_id)

    base_dataset = train_split.dataset.dataset
    final_train = GroupedImageSplit(
        Subset(base_dataset, train_indices),
        tuple(train_groups),
        train_split.class_names,
        train_split.dataset_root,
    )
    validation = GroupedImageSplit(
        Subset(base_dataset, validation_indices),
        tuple(validation_group_ids),
        train_split.class_names,
        train_split.dataset_root,
    )
    if set(final_train.group_ids) & set(validation.group_ids):
        raise RuntimeError("Identity group leaked between train and validation")
    return final_train, validation


def extract_split_features(
    split: GroupedImageSplit,
    split_name: str,
    config: FeatureConfig | None = None,
    *,
    cache_dir: str | Path | None = None,
    use_cache: bool = True,
    progress_interval: int = 250,
) -> FeatureDataset:
    """Extract or load features for an existing train/test split."""
    if split_name not in {"train", "test", "validation"}:
        raise ValueError(f"Unknown split name: {split_name}")
    if progress_interval < 1:
        raise ValueError("progress_interval must be positive")
    config = config or FeatureConfig()
    manifest = _split_manifest(split)
    manifest_payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    manifest_hash = hashlib.sha256(manifest_payload.encode()).hexdigest()
    config_payload = json.dumps(config.to_dict(), sort_keys=True, separators=(",", ":"))
    cache_key = hashlib.sha256(f"{config_payload}:{manifest_hash}".encode()).hexdigest()[:20]
    cache_path = Path(cache_dir) / f"{split_name}_{cache_key}.npz" if cache_dir else None
    expected_metadata = {
        "format_version": 1,
        "split_name": split_name,
        "config": config.to_dict(),
        "manifest_sha256": manifest_hash,
        "class_names": list(split.class_names),
        "feature_names": list(feature_names(config)),
    }

    if use_cache and cache_path and cache_path.is_file():
        with np.load(cache_path, allow_pickle=False) as archive:
            metadata = json.loads(str(archive["metadata"].item()))
            if metadata != expected_metadata:
                raise ValueError(f"Feature cache metadata mismatch: {cache_path}")
            X = archive["X"].astype(np.float32, copy=False)
            y = archive["y"].astype(np.int64, copy=False)
            group_ids = archive["group_ids"].astype(str, copy=False)
        if X.shape != (len(manifest), len(expected_metadata["feature_names"])):
            raise ValueError(f"Feature cache has invalid shape: {cache_path}")
        if len(y) != len(manifest) or len(group_ids) != len(manifest):
            raise ValueError(f"Feature cache has invalid row count: {cache_path}")
        if not np.all(np.isfinite(X)):
            raise ValueError(f"Feature cache contains non-finite values: {cache_path}")
        print(f"Loaded {split_name} features from {cache_path}")
        return FeatureDataset(
            X,
            y,
            group_ids,
            split.class_names,
            feature_names(config),
            tuple(str(row["path"]) for row in manifest),
        )

    base_dataset = split.dataset.dataset
    X_rows: list[np.ndarray] = []
    y_rows: list[int] = []
    paths: list[str] = []
    for position, row in enumerate(manifest):
        dataset_index = split.dataset.indices[position]
        path, label = base_dataset.samples[dataset_index]
        with Image.open(path) as source:
            image = source.copy()
        X_rows.append(extract_features(image, config))
        y_rows.append(int(label))
        paths.append(str(row["path"]))
        if (position + 1) % progress_interval == 0 or position + 1 == len(manifest):
            print(f"Extracted {split_name} features: {position + 1}/{len(manifest)}", flush=True)

    X = np.stack(X_rows).astype(np.float32, copy=False)
    y = np.asarray(y_rows, dtype=np.int64)
    group_ids = np.asarray(split.group_ids, dtype=str)
    if X.shape[1] != len(feature_names(config)) or not np.all(np.isfinite(X)):
        raise RuntimeError("Extracted feature matrix has invalid dimensions or values")

    if use_cache and cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=cache_path.parent, prefix=f".{cache_path.name}.", delete=False
            ) as temporary_file:
                temp_path = Path(temporary_file.name)
                np.savez_compressed(
                    temporary_file,
                    X=X,
                    y=y,
                    group_ids=group_ids,
                    metadata=np.asarray(json.dumps(expected_metadata, sort_keys=True)),
                )
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temp_path, cache_path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()
        print(f"Cached {split_name} features to {cache_path}")

    return FeatureDataset(
        X,
        y,
        group_ids,
        split.class_names,
        feature_names(config),
        tuple(paths),
    )


def load_and_extract_dataset(
    config: FeatureConfig | None = None,
    *,
    cache_dir: str | Path | None = None,
    use_cache: bool = True,
    test_size: float = 0.3,
    validation_size: float = 0.15,
    seed: int = 42,
    progress_interval: int = 250,
    include_test: bool = True,
) -> tuple[FeatureDataset, FeatureDataset, FeatureDataset | None]:
    """Reuse shared train/test split and derive validation only from train groups."""
    from look_again.dataset import build_image_splits

    original_train_split, test_split = build_image_splits(test_size=test_size, seed=seed)
    train_split, validation_split = split_training_validation(
        original_train_split, validation_size=validation_size, seed=seed
    )
    train = extract_split_features(
        train_split,
        "train",
        config,
        cache_dir=cache_dir,
        use_cache=use_cache,
        progress_interval=progress_interval,
    )
    validation = extract_split_features(
        validation_split,
        "validation",
        config,
        cache_dir=cache_dir,
        use_cache=use_cache,
        progress_interval=progress_interval,
    )
    test = None
    if include_test:
        test = extract_split_features(
            test_split,
            "test",
            config,
            cache_dir=cache_dir,
            use_cache=use_cache,
            progress_interval=progress_interval,
        )
    if set(train.group_ids) & set(validation.group_ids):
        raise RuntimeError("Identity group leaked between train and validation")
    if test is not None and (
        set(train.group_ids) & set(test.group_ids)
        or set(validation.group_ids) & set(test.group_ids)
    ):
        raise RuntimeError("Identity group leaked across train/validation/test splits")
    return train, validation, test
