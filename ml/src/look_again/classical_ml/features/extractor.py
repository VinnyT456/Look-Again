"""Composable forensic feature vector and metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np
from PIL import Image

from .dct import DCT_FEATURE_NAMES, extract_dct_features
from .ela import CHANNEL_NAMES as ELA_CHANNELS
from .ela import ELA_STAT_NAMES, extract_ela_features
from .lbp import extract_lbp_features
from .noise import CHANNEL_NAMES as NOISE_CHANNELS
from .noise import NOISE_STAT_NAMES, extract_noise_features


FEATURE_ORDER = ("lbp", "ela", "dct", "noise")
FeatureName = Literal["lbp", "ela", "dct", "noise"]


@dataclass(frozen=True)
class FeatureConfig:
    """Settings that affect extracted values and cache identity."""

    features: tuple[FeatureName, ...] = FEATURE_ORDER
    lbp_points: int = 8
    lbp_radius: float = 1.0
    ela_quality: int = 90
    dct_size: int = 64
    noise_kernel_size: int = 5

    def __post_init__(self) -> None:
        unknown = set(self.features) - set(FEATURE_ORDER)
        if unknown:
            raise ValueError(f"Unknown feature families: {sorted(unknown)}")
        if not self.features:
            raise ValueError("At least one feature family must be enabled")
        if len(set(self.features)) != len(self.features):
            raise ValueError("Feature families must not be repeated")
        object.__setattr__(
            self,
            "features",
            tuple(family for family in FEATURE_ORDER if family in self.features),
        )
        if self.lbp_points < 1 or self.lbp_radius <= 0:
            raise ValueError("LBP points and radius must be positive")
        if not 1 <= self.ela_quality <= 95:
            raise ValueError("ELA JPEG quality must be between 1 and 95")
        if self.dct_size < 8:
            raise ValueError("DCT image size must be at least 8")
        if self.noise_kernel_size < 1 or self.noise_kernel_size % 2 == 0:
            raise ValueError("Gaussian kernel size must be a positive odd number")

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["features"] = list(self.features)
        return result


def feature_names(config: FeatureConfig | None = None) -> tuple[str, ...]:
    """List names in the stable order used by feature extraction."""
    config = config or FeatureConfig()
    names: list[str] = []
    for family in FEATURE_ORDER:
        if family not in config.features:
            continue
        if family == "lbp":
            names.extend(f"lbp_bin_{index:02d}" for index in range(config.lbp_points + 2))
        elif family == "ela":
            names.extend(
                f"ela_{channel}_{stat}"
                for channel in ELA_CHANNELS
                for stat in ELA_STAT_NAMES
            )
        elif family == "dct":
            names.extend(DCT_FEATURE_NAMES)
        elif family == "noise":
            names.extend(
                f"noise_{channel}_{stat}"
                for channel in NOISE_CHANNELS
                for stat in NOISE_STAT_NAMES
            )
    return tuple(names)


def feature_family_slices(config: FeatureConfig | None = None) -> dict[str, slice]:
    """Map each enabled feature family to its contiguous feature columns."""
    config = config or FeatureConfig()
    result: dict[str, slice] = {}
    start = 0
    for family in FEATURE_ORDER:
        if family not in config.features:
            continue
        if family == "lbp":
            count = config.lbp_points + 2
        elif family == "ela":
            count = len(ELA_CHANNELS) * len(ELA_STAT_NAMES)
        elif family == "dct":
            count = len(DCT_FEATURE_NAMES)
        else:
            count = len(NOISE_CHANNELS) * len(NOISE_STAT_NAMES)
        result[family] = slice(start, start + count)
        start += count
    return result


def extract_features_with_names(
    image: Image.Image | np.ndarray,
    config: FeatureConfig | None = None,
) -> tuple[np.ndarray, tuple[str, ...]]:
    """Return concatenated float32 vector and aligned human-readable names."""
    config = config or FeatureConfig()
    blocks: list[np.ndarray] = []
    for family in FEATURE_ORDER:
        if family not in config.features:
            continue
        if family == "lbp":
            block = extract_lbp_features(image, config.lbp_points, config.lbp_radius)
        elif family == "ela":
            block = extract_ela_features(image, config.ela_quality)
        elif family == "dct":
            block = extract_dct_features(image, config.dct_size)
        else:
            block = extract_noise_features(image, config.noise_kernel_size)
        blocks.append(np.asarray(block, dtype=np.float32).reshape(-1))

    vector = np.concatenate(blocks).astype(np.float32, copy=False)
    if not np.all(np.isfinite(vector)):
        raise RuntimeError("Feature extraction produced NaN or infinite values")
    names = feature_names(config)
    if vector.size != len(names):
        raise RuntimeError(f"Feature/name count mismatch: {vector.size} values, {len(names)} names")
    return vector, names


def extract_features(
    image: Image.Image | np.ndarray,
    config: FeatureConfig | None = None,
) -> np.ndarray:
    """Return one fixed-order 1D forensic feature vector."""
    return extract_features_with_names(image, config)[0]
