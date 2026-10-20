"""Image conversion helpers shared by forensic feature extractors."""

from __future__ import annotations

import numpy as np
from PIL import Image


def to_rgb_array(image: Image.Image | np.ndarray) -> np.ndarray:
    """Convert PIL or array image to contiguous uint8 RGB safely."""
    if isinstance(image, Image.Image):
        return np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    if not isinstance(image, np.ndarray):
        raise TypeError(f"Expected PIL image or numpy array, got {type(image).__name__}")

    array = np.asarray(image)
    if array.ndim == 2:
        array = np.repeat(array[..., None], 3, axis=2)
    elif array.ndim == 3 and array.shape[2] == 1:
        array = np.repeat(array, 3, axis=2)
    elif array.ndim == 3 and array.shape[2] >= 3:
        array = array[..., :3]
    else:
        raise ValueError(f"Expected grayscale or RGB image, got shape {array.shape}")
    if not array.shape[0] or not array.shape[1]:
        raise ValueError("Image dimensions must be non-zero")

    if array.dtype == np.uint8:
        return np.ascontiguousarray(array)
    if not np.all(np.isfinite(array)):
        raise ValueError("Image contains NaN or infinite values")

    values = array.astype(np.float32, copy=False)
    if values.size and values.min() >= 0 and values.max() <= 1:
        values = values * 255.0
    return np.ascontiguousarray(np.clip(np.rint(values), 0, 255).astype(np.uint8))
