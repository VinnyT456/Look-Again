"""Export CommunityForensics ViT + universal rich linear probe to TFLite (LiteRT).

Trains the probe from cached rich features (multi-dataset 80% slices), fuses it
with the frozen ViT, and writes a float32 .tflite under checkpoints/tflite/.
The flatbuffer runs on Android via LiteRT or the classic TensorFlow Lite interpreter.

Usage (from ml/):
  uv python pin 3.13
  uv sync --extra export-android
  uv run python -m scripts.export.community_forensics_vit_tflite
  uv run python -m scripts.export.community_forensics_vit_tflite --rebuild-features
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
    DEFAULT_TFLITE_DIR,
    TFLITE_MODEL_FILENAME,
    export_probe_tflite,
    save_probe_bundle,
    verify_tflite_matches_torch,
)
from look_again.paths import DATA_DIR
from scripts.export.probe_export_common import build_universal_probe_module, ensure_feature_caches


def main() -> None:
    parser = argparse.ArgumentParser(description="Export ViT rich probe to TFLite / LiteRT")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_TFLITE_DIR,
        help="Directory for .tflite, weights .npz, and metadata .json",
    )
    parser.add_argument(
        "--rebuild-features",
        action="store_true",
        help="Re-extract ViT feature caches before fitting probe (slow)",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip TFLite numerical check",
    )
    parser.add_argument(
        "--sample-image",
        type=Path,
        default=DATA_DIR / "Deepfake" / "fake" / "fake_00003.jpg",
        help="Image for TFLite verification tensor",
    )
    args = parser.parse_args()

    ensure_feature_caches(args.rebuild_features)

    device = torch.device("cpu")
    probe_module, processor, pipeline, y_train = build_universal_probe_module(device)

    paths = save_probe_bundle(
        args.output_dir,
        pipeline,
        processor,
        model_filename=TFLITE_MODEL_FILENAME,
        model_key="tflite",
        runtime={
            "android": "LiteRT / TensorFlow Lite",
            "format": "float32 flatbuffer (.tflite)",
        },
    )
    tflite_path = Path(paths["tflite"])
    export_probe_tflite(probe_module, tflite_path)
    print(f"Wrote TFLite: {tflite_path}", file=sys.stderr)

    if not args.skip_verify:
        image = Image.open(args.sample_image).convert("RGB")
        inputs = processor(images=image, return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(device=device, dtype=torch.float32)
        max_diff = verify_tflite_matches_torch(probe_module, tflite_path, pixel_values)
        print(f"TFLite verification max |diff| = {max_diff:.6f}", file=sys.stderr)

    summary = {
        **paths,
        "n_train": int(len(y_train)),
        "train_fake": int(np.sum(y_train == 1)),
        "train_real": int(np.sum(y_train == 0)),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
