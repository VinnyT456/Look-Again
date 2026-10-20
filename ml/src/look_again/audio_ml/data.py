"""Load Mix audio clips, split by file, and cache traditional feature matrices."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import GroupShuffleSplit

from look_again.audio_cleanup import MIX_CLASS_DIR_NAMES, iter_audio_files, validate_mix_layout
from look_again.paths import DEFAULT_AUDIO_FEATURES_PARQUET, MIX_AUDIO_DIR

from .config import AudioPipelineConfig
from .data_loader import AudioSample, label_from_path
from .feature_extraction import feature_column_names
from .pipeline import process_audio_file

AudioFeatureConfig = AudioPipelineConfig
feature_names = feature_column_names

CLASS_NAMES = ("fake", "real")


@dataclass(frozen=True)
class AudioFeatureDataset:
    X: np.ndarray
    y: np.ndarray
    group_ids: np.ndarray
    class_names: tuple[str, ...]
    feature_names: tuple[str, ...]
    sample_paths: tuple[str, ...]


def _label_for_path(path: Path, mix_root: Path) -> int:
    relative = path.relative_to(mix_root)
    class_name = relative.parts[0]
    if class_name not in MIX_CLASS_DIR_NAMES:
        raise ValueError(f"Unexpected class directory for {path}")
    return CLASS_NAMES.index(class_name)


def _subsample_stratified(
    paths: list[Path],
    labels: np.ndarray,
    groups: np.ndarray,
    *,
    max_clips: int,
    seed: int,
) -> tuple[list[Path], np.ndarray, np.ndarray]:
    if max_clips <= 0 or len(paths) <= max_clips:
        return paths, labels, groups
    generator = np.random.default_rng(seed)
    selected_indices: list[int] = []
    for class_index in range(len(CLASS_NAMES)):
        class_indices = np.flatnonzero(labels == class_index)
        if class_indices.size == 0:
            continue
        class_cap = max(1, int(round(max_clips * class_indices.size / len(paths))))
        class_cap = min(class_cap, class_indices.size)
        chosen = generator.choice(class_indices, size=class_cap, replace=False)
        selected_indices.extend(int(value) for value in chosen)
    if len(selected_indices) > max_clips:
        selected_indices = generator.choice(
            np.asarray(selected_indices, dtype=int),
            size=max_clips,
            replace=False,
        ).tolist()
    selected_indices = sorted(set(selected_indices))
    index_array = np.asarray(selected_indices, dtype=int)
    return (
        [paths[index] for index in index_array],
        labels[index_array],
        groups[index_array],
    )


def list_mix_samples(mix_root: Path | None = None) -> tuple[list[Path], np.ndarray, np.ndarray]:
    root = (mix_root or MIX_AUDIO_DIR).expanduser().resolve()
    validate_mix_layout(root)
    paths = iter_audio_files(root)
    if not paths:
        raise ValueError(f"No audio files found under {root}")
    labels = np.asarray([_label_for_path(path, root) for path in paths], dtype=np.int64)
    groups = np.asarray(
        [path.relative_to(root).as_posix() for path in paths],
        dtype=str,
    )
    return paths, labels, groups


def _split_groups(
    labels: np.ndarray,
    groups: np.ndarray,
    *,
    test_size: float,
    validation_size: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")
    if not 0 < validation_size < 1:
        raise ValueError("validation_size must be between 0 and 1")
    unique_groups = np.unique(groups)
    if unique_groups.size < 3:
        raise ValueError("Need at least three distinct clips for train/validation/test splits")

    test_splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_val_indices, test_indices = next(test_splitter.split(labels, labels, groups))
    train_val_groups = groups[train_val_indices]
    relative_val_size = validation_size / (1.0 - test_size)
    val_splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=relative_val_size,
        random_state=seed + 1,
    )
    train_indices_local, val_indices_local = next(
        val_splitter.split(
            labels[train_val_indices],
            labels[train_val_indices],
            train_val_groups,
        )
    )
    train_indices = train_val_indices[train_indices_local]
    validation_indices = train_val_indices[val_indices_local]
    for name, left, right in (
        ("train", train_indices, validation_indices),
        ("train", train_indices, test_indices),
        ("validation", validation_indices, test_indices),
    ):
        if set(groups[left]) & set(groups[right]):
            raise RuntimeError(f"Clip leaked between {name} and held-out split")
    all_indices = np.concatenate((train_indices, validation_indices, test_indices))
    if all_indices.size != labels.size or np.unique(all_indices).size != labels.size:
        raise RuntimeError("Split indices do not partition the dataset")
    return train_indices, validation_indices, test_indices


def _pick_stratified_row_indices(
    labels: np.ndarray,
    *,
    max_samples: int,
    seed: int,
) -> np.ndarray:
    if max_samples <= 0 or len(labels) <= max_samples:
        return np.arange(len(labels), dtype=np.int64)
    generator = np.random.default_rng(seed)
    selected: list[int] = []
    total = len(labels)
    for class_index in range(len(CLASS_NAMES)):
        class_indices = np.flatnonzero(labels == class_index)
        if class_indices.size == 0:
            continue
        class_cap = max(1, int(round(max_samples * class_indices.size / total)))
        class_cap = min(class_cap, class_indices.size)
        chosen = generator.choice(class_indices, size=class_cap, replace=False)
        selected.extend(int(value) for value in chosen)
    if len(selected) > max_samples:
        selected = generator.choice(
            np.asarray(selected, dtype=int),
            size=max_samples,
            replace=False,
        ).tolist()
    return np.asarray(sorted(set(selected)), dtype=np.int64)


def _dataset_from_dataframe(
    frame: pd.DataFrame,
    feature_names_list: tuple[str, ...],
    row_indices: np.ndarray,
) -> AudioFeatureDataset:
    subset = frame.iloc[row_indices]
    matrix = subset.loc[:, list(feature_names_list)].to_numpy(dtype=np.float32, copy=False)
    label_values = subset["label"].astype(str).tolist()
    unknown = sorted(set(label_values) - set(CLASS_NAMES))
    if unknown:
        raise ValueError(f"Unexpected labels in feature table: {unknown}")
    y = np.asarray([CLASS_NAMES.index(value) for value in label_values], dtype=np.int64)
    groups = subset["file_path"].astype(str).to_numpy()
    paths = tuple(subset["file_path"].astype(str).tolist())
    if not np.all(np.isfinite(matrix)):
        raise ValueError("Feature table contains non-finite values")
    return AudioFeatureDataset(
        matrix,
        y,
        groups,
        CLASS_NAMES,
        feature_names_list,
        paths,
    )


def load_parquet_feature_splits(
    parquet_path: Path | None = None,
    *,
    test_size: float = 0.2,
    validation_size: float = 0.15,
    seed: int = 42,
    max_samples: int | None = None,
    include_test: bool = True,
) -> tuple[AudioFeatureDataset, AudioFeatureDataset, AudioFeatureDataset | None]:
    """Load precomputed Mix features and split by clip path (no leakage)."""
    path = (parquet_path or DEFAULT_AUDIO_FEATURES_PARQUET).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(
            f"Feature table not found: {path}. "
            "Run `uv run python -m scripts.prepare.build_audio_features` first."
        )
    frame = pd.read_parquet(path)
    if "file_path" not in frame.columns or "label" not in frame.columns:
        raise ValueError("Feature table must contain file_path and label columns")
    meta_columns = {"file_path", "label"}
    feature_names_list = tuple(
        column for column in frame.columns if column not in meta_columns
    )
    if not feature_names_list:
        raise ValueError(f"No feature columns found in {path}")

    labels = np.asarray(
        [CLASS_NAMES.index(str(value)) for value in frame["label"].astype(str)],
        dtype=np.int64,
    )
    groups = frame["file_path"].astype(str).to_numpy()
    if max_samples is not None and len(frame) > max_samples:
        row_indices = _pick_stratified_row_indices(labels, max_samples=max_samples, seed=seed)
        frame = frame.iloc[row_indices].reset_index(drop=True)
        labels = labels[row_indices]
        groups = groups[row_indices]

    train_idx, val_idx, test_idx = _split_groups(
        labels,
        groups,
        test_size=test_size,
        validation_size=validation_size,
        seed=seed,
    )
    train = _dataset_from_dataframe(frame, feature_names_list, train_idx)
    validation = _dataset_from_dataframe(frame, feature_names_list, val_idx)
    test = (
        _dataset_from_dataframe(frame, feature_names_list, test_idx) if include_test else None
    )
    return train, validation, test


def _manifest_rows(
    paths: list[Path],
    labels: np.ndarray,
    groups: np.ndarray,
    indices: np.ndarray,
    mix_root: Path,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in indices:
        path = paths[int(index)]
        stat = path.stat()
        rows.append(
            {
                "path": path.relative_to(mix_root).as_posix(),
                "label": int(labels[index]),
                "group": str(groups[index]),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        )
    return rows


def _extract_one(path: Path, mix_root: Path, config: AudioPipelineConfig) -> np.ndarray:
    label, class_index = label_from_path(path, mix_root)
    sample = AudioSample(
        absolute_path=path,
        file_path=path.relative_to(mix_root).as_posix(),
        label=label,
        class_index=class_index,
    )
    processed, skipped = process_audio_file(sample, config)
    if processed is None:
        reason = skipped.reason if skipped else "unknown"
        raise RuntimeError(f"Failed to featurize {path}: {reason}")
    names = feature_column_names(config)
    return np.asarray([processed.features[name] for name in names], dtype=np.float32)


def _extract_rows(
    paths: list[Path],
    labels: np.ndarray,
    groups: np.ndarray,
    indices: np.ndarray,
    config: AudioFeatureConfig,
    *,
    mix_root: Path,
    progress_interval: int,
    split_name: str,
    extract_jobs: int,
) -> AudioFeatureDataset:
    ordered = [int(index) for index in indices]
    extract_paths = [paths[index] for index in ordered]
    if extract_jobs != 1:
        rows = Parallel(n_jobs=extract_jobs, prefer="processes")(
            delayed(_extract_one)(path, mix_root, config) for path in extract_paths
        )
        print(f"Extracted {split_name} features: {len(rows)}/{len(ordered)}", flush=True)
    else:
        rows = []
        for position, (index, path) in enumerate(zip(ordered, extract_paths, strict=True)):
            rows.append(_extract_one(path, mix_root, config))
            if (position + 1) % progress_interval == 0 or position + 1 == len(ordered):
                print(f"Extracted {split_name} features: {position + 1}/{len(ordered)}", flush=True)
    y_rows = [int(labels[index]) for index in ordered]
    path_rows = [paths[index].relative_to(mix_root).as_posix() for index in ordered]
    group_rows = [str(groups[index]) for index in ordered]
    matrix = np.stack(rows).astype(np.float32, copy=False)
    return AudioFeatureDataset(
        matrix,
        np.asarray(y_rows, dtype=np.int64),
        np.asarray(group_rows, dtype=str),
        CLASS_NAMES,
        feature_names(config),
        tuple(path_rows),
    )


def extract_split(
    paths: list[Path],
    labels: np.ndarray,
    groups: np.ndarray,
    indices: np.ndarray,
    split_name: str,
    config: AudioFeatureConfig,
    *,
    mix_root: Path,
    cache_dir: Path | None,
    use_cache: bool,
    progress_interval: int,
    extract_jobs: int,
) -> AudioFeatureDataset:
    manifest = _manifest_rows(paths, labels, groups, indices, mix_root)
    manifest_payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    manifest_hash = hashlib.sha256(manifest_payload.encode()).hexdigest()
    config_payload = json.dumps(config.to_dict(), sort_keys=True, separators=(",", ":"))
    cache_key = hashlib.sha256(f"{config_payload}:{manifest_hash}".encode()).hexdigest()[:20]
    cache_path = cache_dir / f"{split_name}_{cache_key}.npz" if cache_dir else None
    expected_metadata = {
        "format_version": 1,
        "split_name": split_name,
        "config": config.to_dict(),
        "manifest_sha256": manifest_hash,
        "class_names": list(CLASS_NAMES),
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
            sample_paths = tuple(str(value) for value in archive["sample_paths"].tolist())
        print(f"Loaded {split_name} features from {cache_path}")
        return AudioFeatureDataset(
            X,
            y,
            group_ids,
            CLASS_NAMES,
            feature_names(config),
            sample_paths,
        )

    dataset = _extract_rows(
        paths,
        labels,
        groups,
        indices,
        config,
        mix_root=mix_root,
        progress_interval=progress_interval,
        split_name=split_name,
        extract_jobs=extract_jobs,
    )
    if use_cache and cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=cache_path.parent,
                prefix=f".{cache_path.name}.",
                delete=False,
            ) as temporary_file:
                temp_path = Path(temporary_file.name)
                np.savez_compressed(
                    temporary_file,
                    X=dataset.X,
                    y=dataset.y,
                    group_ids=dataset.group_ids,
                    sample_paths=np.asarray(dataset.sample_paths, dtype=str),
                    metadata=np.asarray(json.dumps(expected_metadata, sort_keys=True)),
                )
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temp_path, cache_path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()
        print(f"Cached {split_name} features to {cache_path}")
    return dataset


def load_mix_feature_splits(
    config: AudioFeatureConfig | None = None,
    *,
    mix_root: Path | None = None,
    cache_dir: Path | None = None,
    use_cache: bool = True,
    test_size: float = 0.2,
    validation_size: float = 0.15,
    seed: int = 42,
    progress_interval: int = 50,
    include_test: bool = True,
    max_clips: int = 0,
    extract_jobs: int = 1,
) -> tuple[AudioFeatureDataset, AudioFeatureDataset, AudioFeatureDataset | None]:
    root = (mix_root or MIX_AUDIO_DIR).expanduser().resolve()
    config = config or AudioFeatureConfig()
    paths, labels, groups = list_mix_samples(root)
    paths, labels, groups = _subsample_stratified(
        paths,
        labels,
        groups,
        max_clips=max_clips,
        seed=seed,
    )
    train_idx, val_idx, test_idx = _split_groups(
        labels,
        groups,
        test_size=test_size,
        validation_size=validation_size,
        seed=seed,
    )
    train = extract_split(
        paths,
        labels,
        groups,
        train_idx,
        "train",
        config,
        mix_root=root,
        cache_dir=cache_dir,
        use_cache=use_cache,
        progress_interval=progress_interval,
        extract_jobs=extract_jobs,
    )
    validation = extract_split(
        paths,
        labels,
        groups,
        val_idx,
        "validation",
        config,
        mix_root=root,
        cache_dir=cache_dir,
        use_cache=use_cache,
        progress_interval=progress_interval,
        extract_jobs=extract_jobs,
    )
    test = None
    if include_test:
        test = extract_split(
            paths,
            labels,
            groups,
            test_idx,
            "test",
            config,
            mix_root=root,
            cache_dir=cache_dir,
            use_cache=use_cache,
            progress_interval=progress_interval,
            extract_jobs=extract_jobs,
        )
    return train, validation, test
