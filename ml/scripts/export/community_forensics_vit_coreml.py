"""Export CommunityForensics ViT + universal rich linear probe to Core ML.

Trains the probe from cached rich features (multi-dataset 80% slices), fuses it
with the frozen ViT, and writes an .mlpackage under checkpoints/coreml/.

Usage (from ml/):
  uv sync --extra export
  uv run python -m scripts.export.community_forensics_vit_coreml
  uv run python -m scripts.export.community_forensics_vit_coreml --rebuild-features
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from look_again.community_forensics_vit_probe import (
    DEFAULT_COREML_DIR,
    export_probe_coreml,
    save_probe_bundle,
    verify_coreml_matches_torch,
)
from look_again.paths import DATA_DIR
from scripts.export.probe_export_common import build_universal_probe_module, ensure_feature_caches


def main() -> None:
    parser = argparse.ArgumentParser(description="Export ViT rich probe to Core ML")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_COREML_DIR,
        help="Directory for .mlpackage, weights .npz, and metadata .json",
    )
    parser.add_argument(
        "--rebuild-features",
        action="store_true",
        help="Re-extract ViT feature caches before fitting probe (slow)",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip Core ML numerical check",
    )
    parser.add_argument(
        "--sample-image",
        type=Path,
        default=DATA_DIR / "Deepfake" / "fake" / "fake_00003.jpg",
        help="Image for Core ML verification tensor",
    )
    args = parser.parse_args()

    ensure_feature_caches(args.rebuild_features)

    device = torch.device("cpu")
    probe_module, processor, pipeline, y_train = build_universal_probe_module(device)

    paths = save_probe_bundle(
        args.output_dir,
        pipeline,
        processor,
        model_filename="community_forensics_vit_rich_probe.mlpackage",
        model_key="coreml",
        runtime={"ios": "Core ML"},
    )
    coreml_path = Path(paths["coreml"])
    export_probe_coreml(probe_module, coreml_path)
    print(f"Wrote Core ML: {coreml_path}", file=sys.stderr)

    if not args.skip_verify:
        image = Image.open(args.sample_image).convert("RGB")
        inputs = processor(images=image, return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(device=device, dtype=torch.float32)
        max_diff = verify_coreml_matches_torch(probe_module, coreml_path, pixel_values)
        print(f"Core ML verification max |diff| = {max_diff:.6f}", file=sys.stderr)

    summary = {
        **paths,
        "n_train": int(len(y_train)),
        "train_fake": int(np.sum(y_train == 1)),
        "train_real": int(np.sum(y_train == 0)),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
