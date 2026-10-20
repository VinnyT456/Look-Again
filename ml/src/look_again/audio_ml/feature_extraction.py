"""Frame-level acoustic features aggregated to fixed-length vectors."""

from __future__ import annotations

from typing import Literal

import librosa
import numpy as np

from .config import AudioPipelineConfig

StatName = Literal["mean", "std", "min", "max"]


def _stat_value(values: np.ndarray, stat: str) -> float:
    if values.size == 0:
        raise ValueError("Cannot aggregate empty frame sequence")
    if stat == "mean":
        return float(np.mean(values))
    if stat == "std":
        return float(np.std(values, ddof=0))
    if stat == "min":
        return float(np.min(values))
    if stat == "max":
        return float(np.max(values))
    raise ValueError(f"Unknown statistic: {stat}")


def _aggregate_frames(
    frames: np.ndarray,
    prefix: str,
    stats: tuple[str, ...],
    *,
    index_offset: int = 1,
) -> dict[str, float]:
    """Aggregate ``(n_features, time)`` or ``(time,)`` frames into named scalars."""
    if frames.ndim == 1:
        frames = frames[np.newaxis, :]
    features: dict[str, float] = {}
    for feature_index in range(frames.shape[0]):
        for stat in stats:
            name = f"{prefix}_{feature_index + index_offset}_{stat}"
            features[name] = _stat_value(frames[feature_index], stat)
    return features


def _aggregate_scalar_frames(
    frames: np.ndarray,
    prefix: str,
    stats: tuple[str, ...],
) -> dict[str, float]:
    values = frames.reshape(-1)
    return {f"{prefix}_{stat}": _stat_value(values, stat) for stat in stats}


def feature_column_names(config: AudioPipelineConfig | None = None) -> tuple[str, ...]:
    """Ordered feature names excluding ``file_path`` and ``label`` metadata columns."""
    config = config or AudioPipelineConfig()
    names: list[str] = []
    for coeff in range(config.n_mfcc):
        for stat in config.mfcc_stats:
            names.append(f"mfcc_{coeff + 1}_{stat}")
    for stat in config.scalar_stats:
        names.append(f"zcr_{stat}")
    for stat in config.scalar_stats:
        names.append(f"spectral_centroid_{stat}")
    for stat in config.scalar_stats:
        names.append(f"spectral_bandwidth_{stat}")
    for stat in config.scalar_stats:
        names.append(f"spectral_rolloff_{stat}")
    n_contrast_bands = config.n_contrast_bands + 1
    for band in range(n_contrast_bands):
        for stat in config.contrast_stats:
            names.append(f"spectral_contrast_band_{band + 1}_{stat}")
    for stat in config.scalar_stats:
        names.append(f"rms_{stat}")
    return tuple(names)


def extract_mfcc_features(
    waveform: np.ndarray,
    sample_rate: int,
    config: AudioPipelineConfig,
) -> dict[str, float]:
    mfcc = librosa.feature.mfcc(
        y=waveform,
        sr=sample_rate,
        n_mfcc=config.n_mfcc,
        n_fft=config.n_fft,
        hop_length=config.hop_length,
        n_mels=config.n_mels,
    )
    return _aggregate_frames(mfcc, "mfcc", config.mfcc_stats)


def extract_zcr_features(
    waveform: np.ndarray,
    config: AudioPipelineConfig,
) -> dict[str, float]:
    zcr = librosa.feature.zero_crossing_rate(
        y=waveform,
        frame_length=config.n_fft,
        hop_length=config.hop_length,
    )
    return _aggregate_scalar_frames(zcr, "zcr", config.scalar_stats)


def extract_spectral_centroid_features(
    waveform: np.ndarray,
    sample_rate: int,
    config: AudioPipelineConfig,
) -> dict[str, float]:
    centroid = librosa.feature.spectral_centroid(
        y=waveform,
        sr=sample_rate,
        n_fft=config.n_fft,
        hop_length=config.hop_length,
    )
    return _aggregate_scalar_frames(centroid, "spectral_centroid", config.scalar_stats)


def extract_spectral_bandwidth_features(
    waveform: np.ndarray,
    sample_rate: int,
    config: AudioPipelineConfig,
) -> dict[str, float]:
    bandwidth = librosa.feature.spectral_bandwidth(
        y=waveform,
        sr=sample_rate,
        n_fft=config.n_fft,
        hop_length=config.hop_length,
    )
    return _aggregate_scalar_frames(bandwidth, "spectral_bandwidth", config.scalar_stats)


def extract_spectral_rolloff_features(
    waveform: np.ndarray,
    sample_rate: int,
    config: AudioPipelineConfig,
) -> dict[str, float]:
    rolloff = librosa.feature.spectral_rolloff(
        y=waveform,
        sr=sample_rate,
        n_fft=config.n_fft,
        hop_length=config.hop_length,
        roll_percent=config.roll_percent,
    )
    return _aggregate_scalar_frames(rolloff, "spectral_rolloff", config.scalar_stats)


def extract_spectral_contrast_features(
    waveform: np.ndarray,
    sample_rate: int,
    config: AudioPipelineConfig,
) -> dict[str, float]:
    contrast = librosa.feature.spectral_contrast(
        y=waveform,
        sr=sample_rate,
        n_fft=config.n_fft,
        hop_length=config.hop_length,
        n_bands=config.n_contrast_bands,
    )
    return _aggregate_frames(contrast, "spectral_contrast_band", config.contrast_stats)


def extract_rms_features(
    waveform: np.ndarray,
    config: AudioPipelineConfig,
) -> dict[str, float]:
    rms = librosa.feature.rms(
        y=waveform,
        frame_length=config.n_fft,
        hop_length=config.hop_length,
    )
    return _aggregate_scalar_frames(rms, "rms", config.scalar_stats)


def extract_features(
    waveform: np.ndarray,
    sample_rate: int,
    config: AudioPipelineConfig | None = None,
) -> dict[str, float]:
    """Compute the full fixed-length feature dictionary for one waveform."""
    config = config or AudioPipelineConfig()
    if sample_rate != config.sample_rate:
        raise ValueError(
            f"Waveform sample rate {sample_rate} != configured {config.sample_rate}"
        )
    features: dict[str, float] = {}
    features.update(extract_mfcc_features(waveform, sample_rate, config))
    features.update(extract_zcr_features(waveform, config))
    features.update(extract_spectral_centroid_features(waveform, sample_rate, config))
    features.update(extract_spectral_bandwidth_features(waveform, sample_rate, config))
    features.update(extract_spectral_rolloff_features(waveform, sample_rate, config))
    features.update(extract_spectral_contrast_features(waveform, sample_rate, config))
    features.update(extract_rms_features(waveform, config))

    expected = feature_column_names(config)
    if tuple(features.keys()) != expected:
        missing = set(expected) - set(features.keys())
        extra = set(features.keys()) - set(expected)
        raise RuntimeError(f"Feature name mismatch; missing={missing}, extra={extra}")
    vector = np.asarray([features[name] for name in expected], dtype=np.float64)
    if not np.all(np.isfinite(vector)):
        raise RuntimeError("Feature vector contains NaN or infinite values")
    return features


def extract_feature_vector(
    waveform: np.ndarray,
    sample_rate: int,
    config: AudioPipelineConfig | None = None,
) -> np.ndarray:
    """Return features as a float32 vector in canonical column order."""
    config = config or AudioPipelineConfig()
    features = extract_features(waveform, sample_rate, config)
    names = feature_column_names(config)
    return np.asarray([features[name] for name in names], dtype=np.float32)
