"""Optional Celeb-DF (HF train split) images for neural training only."""

from __future__ import annotations

from typing import Callable

from torch.utils.data import Dataset

from look_again.dataset import SEED
from look_again.eval_benchmarks import HFCelebDFDataset, build_balanced_celebdf_hf_dataset


def build_celeb_train_supplement(
    transform: Callable | None,
    *,
    max_per_class: int = 750,
    seed: int = SEED,
) -> tuple[Dataset, dict[str, int | str]]:
    """Balanced Celeb-DF HF train images; keep out of DF40 identity splits."""
    hf_dataset, metadata = build_balanced_celebdf_hf_dataset(
        split="train",
        seed=seed,
        max_per_class=max_per_class,
    )
    metadata = dict(metadata)
    metadata["role"] = "train_supplement_only"
    return HFCelebDFDataset(hf_dataset, transform=transform), metadata
