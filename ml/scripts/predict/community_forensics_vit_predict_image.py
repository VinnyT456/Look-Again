"""Run the ViT + rich linear probe on a single image (local PyTorch).

Uses the same preprocessing and 0.5 threshold as the iOS/Android apps.

Usage (from ``ml/``):

  uv run python -m scripts.predict.community_forensics_vit_predict_image path/to/image.jpg
  uv run python -m scripts.predict.community_forensics_vit_predict_image --run-name julienlucas_genai_combined photo.png
  uv run python -m scripts.predict.community_forensics_vit_predict_image --weights checkpoints/coreml/community_forensics_vit_rich_probe_weights.npz photo.png
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
    CommunityForensicsViTProbe,
    load_community_forensics_vit,
    load_probe_module_from_npz,
)
from look_again.paths import CHECKPOINT_DIR, PROJECT_ROOT

THRESHOLD = 0.5
DEFAULT_WEIGHTS = DEFAULT_COREML_DIR / "community_forensics_vit_rich_probe_weights.npz"


def resolve_weights_path(weights: Path | None, run_name: str | None) -> Path:
    if run_name:
        path = CHECKPOINT_DIR / "community_forensics_finetune" / run_name / "community_forensics_vit_rich_probe_weights.npz"
        if not path.is_file():
            raise FileNotFoundError(f"No probe weights for run_name={run_name!r}: {path}")
        return path
    if weights is None:
        return DEFAULT_WEIGHTS
    resolved = weights if weights.is_absolute() else (PROJECT_ROOT / weights).resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Weights not found: {resolved}")
    return resolved


def pick_device(requested: str | None) -> torch.device:
    if requested:
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def classify_image(
    image_path: Path,
    weights_path: Path,
    device: torch.device,
) -> dict[str, float | str]:
    image = Image.open(image_path).convert("RGB")
    module = load_probe_module_from_npz(weights_path, device, CommunityForensicsViTProbe)
    _, processor = load_community_forensics_vit(device)
    pixels = processor(images=image, return_tensors="pt")["pixel_values"].float().to(device)
    with torch.inference_mode():
        fake_prob = float(module(pixels).reshape(-1)[0].cpu())
    fake_prob = float(np.clip(fake_prob, 0.0, 1.0))
    is_fake = fake_prob >= THRESHOLD
    return {
        "image": str(image_path.resolve()),
        "weights": str(weights_path.resolve()),
        "fake_prob": fake_prob,
        "verdict": "Likely AI" if is_fake else "Likely real",
        "confidence": fake_prob if is_fake else 1.0 - fake_prob,
        "threshold": THRESHOLD,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify one image with ViT + rich probe weights")
    parser.add_argument("image", type=Path, help="Path to image file")
    parser.add_argument(
        "--weights",
        type=Path,
        default=None,
        help=f"Probe .npz (default: {DEFAULT_WEIGHTS.relative_to(PROJECT_ROOT)})",
    )
    parser.add_argument(
        "--run-name",
        default=None,
        help="Load weights from checkpoints/community_forensics_finetune/<run_name>/",
    )
    parser.add_argument("--device", default=None, help="cpu | mps | cuda (default: auto)")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    args = parser.parse_args()

    image_path = args.image if args.image.is_absolute() else (PROJECT_ROOT / args.image).resolve()
    if not image_path.is_file():
        print(f"Image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    weights_path = resolve_weights_path(args.weights, args.run_name)
    device = pick_device(args.device)
    result = classify_image(image_path, weights_path, device)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"image:      {result['image']}")
    print(f"weights:    {result['weights']}")
    print(f"fake_prob:  {result['fake_prob']:.4f}")
    print(f"verdict:    {result['verdict']}")
    print(f"confidence: {result['confidence']:.2%}")


if __name__ == "__main__":
    main()
