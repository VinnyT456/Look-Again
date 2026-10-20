"""Audio forgery detection: preprocessing and feature extraction."""

from __future__ import annotations

import os

from look_again.paths import CACHE_DIR

_NUMBA_CACHE = CACHE_DIR / "numba"
_NUMBA_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("NUMBA_CACHE_DIR", str(_NUMBA_CACHE))

from look_again.audio_ml.config import AudioFeatureConfig, AudioPipelineConfig
from look_again.audio_ml.data import load_mix_feature_splits, load_parquet_feature_splits
from look_again.audio_ml.data_loader import AudioSample, discover_audio_samples
from look_again.audio_ml.feature_extraction import (
    extract_features,
    extract_feature_vector,
    feature_column_names,
)
from look_again.audio_ml.pipeline import build_feature_dataset, load_feature_table, process_audio_file
from look_again.audio_ml.preprocessing import load_audio, preprocess_audio

__all__ = [
    "AudioFeatureConfig",
    "AudioPipelineConfig",
    "AudioSample",
    "build_feature_dataset",
    "discover_audio_samples",
    "extract_feature_vector",
    "extract_features",
    "feature_column_names",
    "load_audio",
    "load_feature_table",
    "load_mix_feature_splits",
    "load_parquet_feature_splits",
    "preprocess_audio",
    "process_audio_file",
]
