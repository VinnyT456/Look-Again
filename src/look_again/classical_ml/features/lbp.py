"""Local binary pattern texture features."""

from __future__ import annotations

import numpy as np
from PIL import Image
from skimage.feature import local_binary_pattern

from .common import to_rgb_array


def extract_lbp_map(
    image: Image.Image | np.ndarray,
    points: int = 8,
    radius: float = 1.0,
) -> np.ndarray:
    """Return the per-pixel uniform-LBP codes used by the histogram extractor."""
    if points < 1:
        raise ValueError("LBP points must be positive")
    if radius <= 0:
        raise ValueError("LBP radius must be positive")

    rgb = to_rgb_array(image)
    gray = np.asarray(Image.fromarray(rgb).convert("L"), dtype=np.uint8)
    lbp = local_binary_pattern(gray, P=points, R=radius, method="uniform")
    return np.clip(np.rint(lbp), 0, points + 1).astype(np.uint8)


def extract_lbp_features(
    image: Image.Image | np.ndarray,
    points: int = 8,
    radius: float = 1.0,
) -> np.ndarray:
    """Return normalized uniform-LBP histogram with ``points + 2`` bins."""
    if points < 1:
        raise ValueError("LBP points must be positive")
    if radius <= 0:
        raise ValueError("LBP radius must be positive")

    lbp = extract_lbp_map(image, points=points, radius=radius)
    bins = points + 2
    histogram, _ = np.histogram(lbp, bins=np.arange(bins + 1, dtype=np.float64))
    histogram = histogram.astype(np.float32)
    total = float(histogram.sum())
    if total:
        histogram /= total
    return histogram
