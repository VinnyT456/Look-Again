"""Discover labeled Mix audio files without loading waveforms into memory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from look_again.audio_cleanup import MIX_CLASS_DIR_NAMES, iter_audio_files, validate_mix_layout
from look_again.paths import MIX_AUDIO_DIR

CLASS_LABELS = ("fake", "real")


@dataclass(frozen=True)
class AudioSample:
    """One labeled clip with paths preserved for traceability and future group splits."""

    absolute_path: Path
    file_path: str
    label: str
    class_index: int


def label_from_path(path: Path, dataset_root: Path) -> tuple[str, int]:
    relative = path.relative_to(dataset_root)
    class_name = relative.parts[0]
    if class_name not in MIX_CLASS_DIR_NAMES:
        raise ValueError(f"Unexpected class folder for {path}")
    return class_name, CLASS_LABELS.index(class_name)


def discover_audio_samples(
    dataset_root: Path | None = None,
    *,
    max_samples: int | None = None,
    random_seed: int = 42,
) -> list[AudioSample]:
    """List all Mix clips, optionally subsampling with approximate class balance."""
    root = (dataset_root or MIX_AUDIO_DIR).expanduser().resolve()
    validate_mix_layout(root)
    paths = iter_audio_files(root)
    if not paths:
        raise ValueError(f"No audio files found under {root}")

    samples: list[AudioSample] = []
    for path in paths:
        label, class_index = label_from_path(path, root)
        samples.append(
            AudioSample(
                absolute_path=path,
                file_path=path.relative_to(root).as_posix(),
                label=label,
                class_index=class_index,
            )
        )
    if max_samples is None or len(samples) <= max_samples:
        return samples
    return stratified_subsample(samples, max_samples=max_samples, random_seed=random_seed)


def stratified_subsample(
    samples: list[AudioSample],
    *,
    max_samples: int,
    random_seed: int,
) -> list[AudioSample]:
    """Keep class proportions while drawing at most ``max_samples`` clips."""
    if max_samples <= 0:
        raise ValueError("max_samples must be positive")
    if len(samples) <= max_samples:
        return samples

    generator = np.random.default_rng(random_seed)
    by_class: dict[str, list[AudioSample]] = {label: [] for label in CLASS_LABELS}
    for sample in samples:
        by_class[sample.label].append(sample)

    total = len(samples)
    selected: list[AudioSample] = []
    for label in CLASS_LABELS:
        pool = by_class[label]
        if not pool:
            continue
        class_cap = max(1, int(round(max_samples * len(pool) / total)))
        class_cap = min(class_cap, len(pool))
        indices = generator.choice(len(pool), size=class_cap, replace=False)
        selected.extend(pool[int(index)] for index in indices)

    if len(selected) > max_samples:
        indices = generator.choice(len(selected), size=max_samples, replace=False)
        selected = [selected[int(index)] for index in indices]
    return sorted(selected, key=lambda sample: sample.file_path)
