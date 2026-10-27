"""Run the ViT + 3-class rich probe (real / synthetic / tampered) on image(s).

Usage (from ``ml/``):

  uv run python -m scripts.predict.community_forensics_vit_predict_image_tertiary photo.jpg
  uv run python -m scripts.predict.community_forensics_vit_predict_image_tertiary --run-name so_fake_tertiary_probe a.png b.png
  uv run python -m scripts.predict.community_forensics_vit_predict_image_tertiary --weights checkpoints/community_forensics_sofake_tertiary/so_fake_tertiary_probe/community_forensics_vit_rich_probe_tertiary_weights.npz photo.jpg
  uv run python -m scripts.predict.community_forensics_vit_predict_image_tertiary --json photo.jpg
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

from look_again.community_forensics_finetune_multiclass import (
    TertiaryProbeWeights,
    classify_tertiary_image,
    default_tertiary_weights_path,
)
from look_again.paths import PROJECT_ROOT

DEFAULT_RUN_NAME = "so_fake_tertiary_probe"


def resolve_weights_path(weights: Path | None, run_name: str | None) -> Path:
    if weights is not None:
        resolved = weights if weights.is_absolute() else (PROJECT_ROOT / weights).resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"Weights not found: {resolved}")
        return resolved
    name = run_name or DEFAULT_RUN_NAME
    path = default_tertiary_weights_path(name)
    if not path.is_file():
        raise FileNotFoundError(f"No tertiary probe for run_name={name!r}: {path}")
    return path


def pick_device(requested: str | None) -> torch.device:
    if requested:
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def main() -> None:
    parser = argparse.ArgumentParser(description="3-class ViT + rich probe on image(s)")
    parser.add_argument("images", type=Path, nargs="+", help="Image path(s)")
    parser.add_argument("--weights", type=Path, default=None, help="Tertiary probe .npz")
    parser.add_argument(
        "--run-name",
        default=None,
        help=f"Load from checkpoints/community_forensics_sofake_tertiary/<run_name>/ (default: {DEFAULT_RUN_NAME})",
    )
    parser.add_argument("--device", default=None, help="cpu | mps | cuda (default: auto)")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    args = parser.parse_args()

    weights_path = resolve_weights_path(args.weights, args.run_name)
    weights = TertiaryProbeWeights.from_npz(weights_path)
    device = pick_device(args.device)

    results: list[dict] = []
    for image_arg in args.images:
        image_path = image_arg if image_arg.is_absolute() else (PROJECT_ROOT / image_arg).resolve()
        if not image_path.is_file():
            print(f"Image not found: {image_path}", file=sys.stderr)
            sys.exit(1)
        out = classify_tertiary_image(image_path, weights, device)
        out["weights"] = str(weights_path.resolve())
        results.append(out)

    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], indent=2))
        return

    for result in results:
        print(f"image:       {result['image']}")
        print(f"weights:     {result['weights']}")
        print(f"verdict:     {result['verdict']} ({result['predicted_class']})")
        print(f"confidence:  {result['confidence']:.2%}")
        print(
            f"probs:       real={result['prob_real']:.4f}  "
            f"synthetic={result['prob_synthetic']:.4f}  "
            f"tampered={result['prob_tampered']:.4f}"
        )
        if len(results) > 1:
            print()


if __name__ == "__main__":
    main()
