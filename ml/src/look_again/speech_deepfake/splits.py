"""Speaker-/clip-disjoint dataset splits."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from .metadata import SpeechRecord


@dataclass(frozen=True)
class SpeechSplit:
    train: list[SpeechRecord]
    validation: list[SpeechRecord]
    test: list[SpeechRecord]


def _split_counts(records: list[SpeechRecord]) -> dict[str, int]:
    counts = {"real": 0, "fake": 0}
    for record in records:
        counts[record.label_name] += 1
    return counts


def split_records(
    records: list[SpeechRecord],
    *,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    random_seed: int = 42,
) -> SpeechSplit:
    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
        raise ValueError("Split ratios must sum to 1.0")
    if len(records) < 3:
        raise ValueError("Need at least three clips for train/validation/test splits")

    labels = np.asarray([record.label for record in records], dtype=np.int64)
    groups = np.asarray([record.group_id for record in records], dtype=str)
    indices = np.arange(len(records), dtype=np.int64)

    test_splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=test_ratio,
        random_state=random_seed,
    )
    train_val_indices, test_indices = next(test_splitter.split(indices, labels, groups))
    train_val_groups = groups[train_val_indices]
    relative_val_size = val_ratio / (train_ratio + val_ratio)
    val_splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=relative_val_size,
        random_state=random_seed + 1,
    )
    train_local, val_local = next(
        val_splitter.split(
            train_val_indices,
            labels[train_val_indices],
            train_val_groups,
        )
    )
    train_indices = train_val_indices[train_local]
    val_indices = train_val_indices[val_local]

    for left_name, left, right in (
        ("train", train_indices, val_indices),
        ("train", train_indices, test_indices),
        ("validation", val_indices, test_indices),
    ):
        if set(groups[left]) & set(groups[right]):
            raise RuntimeError(f"Group leaked between {left_name} and another split")

    train = [records[int(index)] for index in train_indices]
    validation = [records[int(index)] for index in val_indices]
    test = [records[int(index)] for index in test_indices]
    return SpeechSplit(train=train, validation=validation, test=test)


def format_split_summary(split: SpeechSplit) -> dict[str, dict[str, int]]:
    return {
        "train": _split_counts(split.train),
        "validation": _split_counts(split.validation),
        "test": _split_counts(split.test),
    }
