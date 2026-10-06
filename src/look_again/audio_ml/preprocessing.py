"""Load and normalize waveforms for classical speech features."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from .config import AudioPipelineConfig


@dataclass(frozen=True)
class PreprocessResult:
    waveform: np.ndarray
    sample_rate: int


@dataclass(frozen=True)
class PreprocessFailure:
    reason: str


def load_audio(path: Path, config: AudioPipelineConfig) -> PreprocessResult | PreprocessFailure:
    """Load one file to mono float waveform at ``config.sample_rate``."""
    try:
        waveform, source_sr = sf.read(str(path), always_2d=False)
        if waveform.ndim > 1:
            waveform = waveform.mean(axis=1)
        waveform = waveform.astype(np.float32, copy=False)
        if source_sr != config.sample_rate:
            waveform = librosa.resample(
                waveform,
                orig_sr=source_sr,
                target_sr=config.sample_rate,
            ).astype(np.float32, copy=False)
    except Exception as error:  # noqa: BLE001 — collect and continue pipeline
        try:
            waveform, _sample_rate = librosa.load(
                str(path),
                sr=config.sample_rate,
                mono=True,
                dtype=np.float32,
            )
        except Exception as fallback_error:  # noqa: BLE001
            return PreprocessFailure(f"decode_error: {fallback_error} ({error})")
    if waveform.size == 0:
        return PreprocessFailure("empty_audio")
    if not np.all(np.isfinite(waveform)):
        return PreprocessFailure("non_finite_samples")
    return PreprocessResult(waveform=waveform, sample_rate=config.sample_rate)


def preprocess_audio(
    waveform: np.ndarray,
    config: AudioPipelineConfig,
) -> PreprocessResult | PreprocessFailure:
    """Optional trim/normalize and duration checks without denoising."""
    signal = np.asarray(waveform, dtype=np.float32)
    if signal.size == 0:
        return PreprocessFailure("empty_audio")
    if not np.all(np.isfinite(signal)):
        return PreprocessFailure("non_finite_samples")

    if config.trim_silence:
        try:
            trimmed, _index = librosa.effects.trim(signal, top_db=config.top_db)
            if trimmed.size > 0:
                signal = trimmed.astype(np.float32, copy=False)
        except Exception as error:  # noqa: BLE001
            return PreprocessFailure(f"trim_error: {error}")

    min_samples = max(1, int(config.min_duration_seconds * config.sample_rate))
    if signal.size < min_samples:
        return PreprocessFailure(
            f"too_short: {signal.size} samples < {min_samples} required"
        )

    if config.max_duration_seconds is not None:
        max_samples = int(config.max_duration_seconds * config.sample_rate)
        if signal.size > max_samples:
            start = (signal.size - max_samples) // 2
            signal = signal[start : start + max_samples]

    if config.normalize_audio:
        peak = float(np.max(np.abs(signal)))
        if peak <= config.peak_epsilon:
            return PreprocessFailure("silent_after_trim")
        signal = (signal / (peak + config.peak_epsilon)).astype(np.float32, copy=False)

    if not np.all(np.isfinite(signal)):
        return PreprocessFailure("non_finite_after_preprocess")
    return PreprocessResult(waveform=signal, sample_rate=config.sample_rate)
