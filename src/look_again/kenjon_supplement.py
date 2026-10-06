"""Kenjon HF train split as fake-only training supplement (never use test split here)."""

from __future__ import annotations

from typing import Callable

import torch
from torch.utils.data import Dataset, Subset

from look_again.dataset import SEED
from look_again.eval_benchmarks import KenjonFaceSwapDataset


def build_kenjon_train_supplement(
    transform: Callable | None,
    *,
    max_samples: int = 800,
    seed: int = SEED,
) -> tuple[Dataset, dict[str, int | str]]:
    dataset = KenjonFaceSwapDataset(split="train", transform=transform)
    sample_count = min(len(dataset), max_samples)
    generator = torch.Generator().manual_seed(seed)
    selected = torch.randperm(len(dataset), generator=generator).tolist()[:sample_count]
    metadata = {
        "source": "kenjon/deep-fake-face-swap",
        "split": "train",
        "samples": sample_count,
        "role": "train_supplement_only",
    }
    return Subset(dataset, selected), metadata
