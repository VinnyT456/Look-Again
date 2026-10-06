"""Compatibility helpers for older audio training experiments."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from look_again.paths import MIX_AUDIO_DIR

from .config import AudioFeatureConfig, AudioPipelineConfig
from .data_loader import AudioSample, label_from_path
from .feature_extraction import feature_column_names
from .pipeline import process_audio_file

feature_names = feature_column_names


def extract_traditional_features(
    path: Path,
    config: AudioPipelineConfig | None = None,
) -> np.ndarray:
    """Extract the canonical feature vector for one on-disk clip."""
    config = config or AudioPipelineConfig()
    resolved = path.expanduser().resolve()
    try:
        label, class_index = label_from_path(resolved, MIX_AUDIO_DIR)
        file_path = resolved.relative_to(MIX_AUDIO_DIR).as_posix()
    except ValueError:
        label, class_index = "fake", 0
        file_path = resolved.name
    sample = AudioSample(resolved, file_path, label, class_index)
    processed, skipped = process_audio_file(sample, config)
    if processed is None:
        reason = skipped.reason if skipped else "unknown"
        raise RuntimeError(f"Failed to featurize {path}: {reason}")
    names = feature_column_names(config)
    return np.asarray([processed.features[name] for name in names], dtype=np.float32)


__all__ = [
    "AudioFeatureConfig",
    "AudioPipelineConfig",
    "extract_traditional_features",
    "feature_column_names",
    "feature_names",
]
