"""Shared helpers for ViT rich-probe mobile exports."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.pipeline import Pipeline
from transformers import ViTImageProcessor

from look_again.community_forensics_vit_probe import (
    MODEL_CACHE,
    CommunityForensicsViTProbe,
    collect_universal_probe_training_arrays,
    fit_universal_rich_linear_probe,
    load_community_forensics_vit,
    sklearn_linear_probe_weights,
)
from look_again.paths import PROJECT_ROOT


def ensure_feature_caches(rebuild: bool) -> None:
    if rebuild:
        subprocess.run(
            ["uv", "run", "test_community_forensics_vit.py", "--eval-deepfake", "--rebuild-cache"],
            cwd=PROJECT_ROOT,
            check=True,
        )
        subprocess.run(
            ["uv", "run", "test_community_forensics_vit.py", "--eval-cross-dataset", "--rebuild-cache"],
            cwd=PROJECT_ROOT,
            check=True,
        )
        return

    cache = MODEL_CACHE / "deepfake_vit_features.npz"
    if not cache.is_file():
        print(
            "Missing feature cache. Run:\n"
            "  uv run test_community_forensics_vit.py --eval-deepfake\n"
            "  uv run test_community_forensics_vit.py --eval-cross-dataset\n"
            "or pass --rebuild-features",
            file=sys.stderr,
        )
        sys.exit(1)


def build_universal_probe_module(
    device: torch.device | None = None,
) -> tuple[CommunityForensicsViTProbe, ViTImageProcessor, Pipeline, np.ndarray]:
    device = device or torch.device("cpu")
    backbone, processor = load_community_forensics_vit(device)
    x_train, y_train = collect_universal_probe_training_arrays()
    print(f"Fitting universal rich linear probe on {len(y_train)} samples...", file=sys.stderr)
    pipeline = fit_universal_rich_linear_probe(x_train, y_train)
    weights = sklearn_linear_probe_weights(pipeline)
    probe_module = CommunityForensicsViTProbe(
        backbone,
        feature_mean=torch.from_numpy(weights.mean),
        feature_scale=torch.from_numpy(weights.scale),
        probe_weight=torch.from_numpy(weights.coef),
        probe_bias=torch.from_numpy(weights.intercept),
    )
    probe_module.eval()
    return probe_module, processor, pipeline, y_train
