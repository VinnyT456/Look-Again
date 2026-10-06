"""Lightweight Gaussian-blur residual statistics."""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from .common import to_rgb_array


NOISE_STAT_NAMES = (
    "mean",
    "std",
    "variance",
    "mean_absolute",
    "median_absolute",
    "rms",
    "absolute_p75",
    "absolute_p90",
    "absolute_p95",
    "skewness",
    "excess_kurtosis",
)
CHANNEL_NAMES = ("r", "g", "b")


def extract_noise_residual(
    image: Image.Image | np.ndarray,
    kernel_size: int = 5,
) -> np.ndarray:
    """Return the signed RGB high-frequency residual after Gaussian blur."""
    if kernel_size < 1 or kernel_size % 2 == 0:
        raise ValueError("Gaussian kernel size must be a positive odd number")
    rgb = to_rgb_array(image).astype(np.float32)
    blurred = cv2.GaussianBlur(rgb, (kernel_size, kernel_size), sigmaX=0)
    return rgb - blurred


def extract_noise_map(
    image: Image.Image | np.ndarray,
    kernel_size: int = 5,
) -> np.ndarray:
    """Return a per-pixel mean absolute RGB blur-residual map as uint8."""
    residual = extract_noise_residual(image, kernel_size=kernel_size)
    magnitude = np.mean(np.abs(residual), axis=2)
    return np.clip(np.rint(magnitude), 0, 255).astype(np.uint8)


def extract_noise_features(
    image: Image.Image | np.ndarray,
    kernel_size: int = 5,
) -> np.ndarray:
    """Return 11 residual statistics per RGB channel after Gaussian blur."""
    residual = extract_noise_residual(image, kernel_size=kernel_size)
    values: list[float] = []
    epsilon = np.finfo(np.float32).eps
    for channel in range(3):
        samples = residual[..., channel].astype(np.float64).ravel()
        absolute = np.abs(samples)
        mean = float(np.mean(samples))
        centered = samples - mean
        variance = float(np.mean(np.square(centered)))
        std = float(np.sqrt(variance))
        skewness = float(np.mean(centered**3) / (std**3)) if std > epsilon else 0.0
        kurtosis = float(np.mean(centered**4) / (variance**2) - 3) if variance > epsilon else 0.0
        values.extend(
            (
                mean,
                std,
                variance,
                float(np.mean(absolute)),
                float(np.median(absolute)),
                float(np.sqrt(np.mean(np.square(samples)))),
                float(np.percentile(absolute, 75)),
                float(np.percentile(absolute, 90)),
                float(np.percentile(absolute, 95)),
                skewness,
                kurtosis,
            )
        )
    return np.nan_to_num(np.asarray(values, dtype=np.float32), copy=False)
