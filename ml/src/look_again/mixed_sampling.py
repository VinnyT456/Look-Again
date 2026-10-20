"""Batch sampling helpers for multi-source training mixes."""

from __future__ import annotations

from collections.abc import Sequence

from torch.utils.data import WeightedRandomSampler


def build_balanced_source_sampler(
    source_lengths: Sequence[int],
) -> WeightedRandomSampler:
    """Sample so each source is equally likely, regardless of dataset size."""
    if not source_lengths or any(length <= 0 for length in source_lengths):
        raise ValueError(f"Invalid source lengths: {source_lengths}")

    weights: list[float] = []
    for length in source_lengths:
        per_example_weight = 1.0 / length
        weights.extend([per_example_weight] * length)
    return WeightedRandomSampler(
        weights=weights,
        num_samples=len(weights),
        replacement=True,
    )
