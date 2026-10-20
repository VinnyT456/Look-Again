"""In-memory JPEG recompression error level analysis features."""

from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image

from .common import to_rgb_array


ELA_STAT_NAMES = (
    "mean",
    "std",
    "variance",
    "maximum",
    "median",
    "p75",
    "p90",
    "p95",
)
CHANNEL_NAMES = ("r", "g", "b")


def extract_ela_residual(
    image: Image.Image | np.ndarray,
    quality: int = 90,
) -> np.ndarray:
    """Return the RGB absolute error map from the configured JPEG recompression."""
    if not 1 <= quality <= 95:
        raise ValueError("ELA JPEG quality must be between 1 and 95")

    rgb = to_rgb_array(image)
    buffer = BytesIO()
    Image.fromarray(rgb, mode="RGB").save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    with Image.open(buffer) as recompressed_image:
        recompressed = np.asarray(recompressed_image.convert("RGB"), dtype=np.int16)
    return np.abs(rgb.astype(np.int16) - recompressed).astype(np.uint8)


def extract_ela_map(
    image: Image.Image | np.ndarray,
    quality: int = 90,
) -> np.ndarray:
    """Return the per-pixel mean RGB ELA magnitude as an 8-bit map."""
    residual = extract_ela_residual(image, quality=quality)
    return np.rint(residual.mean(axis=2)).astype(np.uint8)


def extract_ela_features(
    image: Image.Image | np.ndarray,
    quality: int = 90,
) -> np.ndarray:
    """Return eight absolute-difference statistics for each RGB channel."""
    difference = extract_ela_residual(image, quality=quality).astype(np.float32)
    values: list[float] = []
    for channel in range(3):
        samples = difference[..., channel]
        values.extend(
            (
                float(np.mean(samples)),
                float(np.std(samples)),
                float(np.var(samples)),
                float(np.max(samples)),
                float(np.median(samples)),
                float(np.percentile(samples, 75)),
                float(np.percentile(samples, 90)),
                float(np.percentile(samples, 95)),
            )
        )
    return np.asarray(values, dtype=np.float32)
