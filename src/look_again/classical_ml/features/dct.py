"""Compact radial-band frequency features from a two-dimensional DCT."""

from __future__ import annotations

import numpy as np
from PIL import Image
from scipy.fft import dctn

from .common import to_rgb_array


BANDS = ("low", "mid", "high")
STATS = ("energy", "mean_magnitude", "std_magnitude")
DCT_FEATURE_NAMES = tuple(f"dct_{band}_{stat}" for band in BANDS for stat in STATS) + (
    "dct_high_to_low_energy_ratio",
    "dct_mid_to_low_energy_ratio",
    "dct_spectral_entropy",
)


def extract_dct_features(
    image: Image.Image | np.ndarray,
    size: int = 64,
) -> np.ndarray:
    """Return 12 low/mid/high radial-frequency statistics with fixed size."""
    if size < 8:
        raise ValueError("DCT image size must be at least 8")

    rgb = to_rgb_array(image)
    gray = Image.fromarray(rgb, mode="RGB").convert("L")
    gray = gray.resize((size, size), Image.Resampling.BILINEAR)
    coefficients = dctn(np.asarray(gray, dtype=np.float64), type=2, norm="ortho")

    rows, columns = np.indices(coefficients.shape)
    radius = np.sqrt(rows.astype(np.float64) ** 2 + columns.astype(np.float64) ** 2)
    maximum_radius = float(np.sqrt(2) * (size - 1))
    normalized_radius = radius / maximum_radius
    masks = (
        normalized_radius <= 0.25,
        (normalized_radius > 0.25) & (normalized_radius <= 0.60),
        normalized_radius > 0.60,
    )

    magnitude = np.abs(coefficients)
    energy = np.square(coefficients)
    features: list[float] = []
    band_energies: list[float] = []
    for mask in masks:
        band_magnitude = magnitude[mask]
        band_energy = float(np.sum(energy[mask]))
        band_energies.append(band_energy)
        features.extend(
            (
                band_energy,
                float(np.mean(band_magnitude)),
                float(np.std(band_magnitude)),
            )
        )

    epsilon = np.finfo(np.float64).eps
    low_energy, mid_energy, high_energy = band_energies
    features.extend((high_energy / (low_energy + epsilon), mid_energy / (low_energy + epsilon)))

    all_energy = float(np.sum(energy))
    if all_energy <= epsilon:
        entropy = 0.0
    else:
        probabilities = energy.ravel() / all_energy
        probabilities = probabilities[probabilities > 0]
        entropy = float(-np.sum(probabilities * np.log(probabilities)) / np.log(energy.size))
    features.append(entropy)
    return np.nan_to_num(np.asarray(features, dtype=np.float32), copy=False)
