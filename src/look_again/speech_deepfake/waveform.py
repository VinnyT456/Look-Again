"""Waveform loading for Hugging Face speech encoders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from look_again.audio_ml.config import AudioPipelineConfig
from look_again.audio_ml.preprocessing import PreprocessFailure, load_audio, preprocess_audio


@dataclass(frozen=True)
class WaveformExample:
    waveform: np.ndarray
    sample_rate: int


def load_waveform_example(
    path: Path,
    *,
    sample_rate: int = 16_000,
    max_audio_seconds: float = 5.0,
) -> WaveformExample | PreprocessFailure:
    """Load mono speech at ``sample_rate`` with optional center crop."""
    config = AudioPipelineConfig(
        sample_rate=sample_rate,
        normalize_audio=False,
        trim_silence=False,
        max_duration_seconds=max_audio_seconds,
        min_duration_seconds=0.05,
    )
    loaded = load_audio(path, config)
    if isinstance(loaded, PreprocessFailure):
        return loaded
    processed = preprocess_audio(loaded.waveform, config)
    if isinstance(processed, PreprocessFailure):
        return processed
    return WaveformExample(processed.waveform, processed.sample_rate)
