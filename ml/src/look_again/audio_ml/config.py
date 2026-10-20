"""Configuration for Mix audio preprocessing and feature extraction."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AudioPipelineConfig:
    """Hyperparameters and toggles for the speech deepfake feature pipeline."""

    sample_rate: int = 16_000
    n_mfcc: int = 20
    n_fft: int = 512
    hop_length: int = 160
    n_mels: int = 128
    roll_percent: float = 0.85
    n_contrast_bands: int = 6
    normalize_audio: bool = True
    trim_silence: bool = False
    top_db: float = 30.0
    peak_epsilon: float = 1e-8
    min_duration_seconds: float = 0.05
    max_duration_seconds: float | None = None
    random_seed: int = 42
    max_samples: int | None = None
    checkpoint_every: int = 5_000
    n_workers: int = 1
    mfcc_stats: tuple[str, ...] = ("mean", "std")
    scalar_stats: tuple[str, ...] = ("mean", "std", "min", "max")
    contrast_stats: tuple[str, ...] = ("mean", "std")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


# Backward-compatible alias used by earlier training experiments.
AudioFeatureConfig = AudioPipelineConfig
