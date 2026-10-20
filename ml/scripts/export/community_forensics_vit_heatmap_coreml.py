"""Export the ViT rich probe to Core ML with a per-patch heatmap output.

Rebuilds the probe from the already-exported weights (no refitting), so the
decision is identical to ``community_forensics_vit_rich_probe.mlpackage``; adds
``patch_map`` (1×24×24, logit units) for the iOS app's Highlight view.

Checks before writing anything the app uses:
  1. fake_prob matches the original probe module exactly.
  2. patch_map sums to the patch_std term of the logit (the decomposition is exact).
  3. Core ML outputs match PyTorch on each sample image.

Usage (from ml/):
  uv run python -m scripts.export.community_forensics_vit_heatmap_coreml \
      --sample-image path/a.png --sample-image path/b.png
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
    CommunityForensicsViTProbeHeatmap,
    export_heatmap_coreml,
    export_probe_coreml,
    load_community_forensics_vit,
    load_probe_module_from_npz,
)

WEIGHTS_NAME = "community_forensics_vit_rich_probe_weights.npz"
BASE_NAME = "community_forensics_vit_rich_probe.mlpackage"
OUTPUT_NAME = "community_forensics_vit_rich_probe_heatmap.mlpackage"


def patch_std_term(module: CommunityForensicsViTProbeHeatmap, pixel_values: torch.Tensor) -> torch.Tensor:
    """Σ_d c_d · std_d, computed the plain way, to check the map against."""
    flipped = torch.flip(pixel_values, dims=[-1])
    seq_orig = module.vit(pixel_values=pixel_values).last_hidden_state
    seq_flip = module.vit(pixel_values=flipped).last_hidden_state
    pairs = torch.cat([seq_orig[:, 1:, :], seq_flip[:, 1:, :]], dim=1)
    hidden = seq_orig.shape[-1]
    weight = module.probe.weight.view(-1) / module.feature_scale.view(-1)
    std = pairs.std(dim=1, unbiased=False)
    return (std * weight[3 * hidden : 4 * hidden]).sum(-1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export ViT rich probe + patch heatmap to Core ML")
    parser.add_argument("--coreml-dir", type=Path, default=DEFAULT_COREML_DIR)
    parser.add_argument("--sample-image", type=Path, action="append", default=[], help="Image(s) to verify with")
    parser.add_argument(
        "--no-refresh-base",
        action="store_true",
        help="Do not rebuild community_forensics_vit_rich_probe.mlpackage from the .npz first",
    )
    parser.add_argument(
        "--skip-coreml-verify",
        action="store_true",
        help="Write .mlpackage without Core ML vs PyTorch checks",
    )
    args = parser.parse_args()

    device = torch.device("cpu")
    weights = args.coreml_dir / WEIGHTS_NAME
    heatmap_module = load_probe_module_from_npz(weights, device, CommunityForensicsViTProbeHeatmap)
    base_module = load_probe_module_from_npz(weights, device, CommunityForensicsViTProbe)
    _, processor = load_community_forensics_vit(device)

    samples = [torch.randn(1, 3, 384, 384)]
    for path in args.sample_image:
        image = Image.open(path).convert("RGB")
        samples.append(processor(images=image, return_tensors="pt")["pixel_values"].float())

    with torch.inference_mode():
        for index, pixels in enumerate(samples):
            prob, patch_map = heatmap_module(pixels)
            base_prob = base_module(pixels)
            prob_diff = float((prob - base_prob).abs().max())
            sum_diff = float((patch_map.sum(dim=(-1, -2)) - patch_std_term(heatmap_module, pixels)).abs().max())
            print(f"[torch] sample {index}: fake_prob {float(prob):.5f}  |Δ vs base| {prob_diff:.2e}  "
                  f"|Σmap − std term| {sum_diff:.2e}", file=sys.stderr)
            if prob_diff > 1e-5:
                raise RuntimeError("Heatmap module changed the decision")
            if sum_diff > 1e-3:
                raise RuntimeError("patch_map does not decompose the patch_std term")

    base_path = args.coreml_dir / BASE_NAME
    if not args.no_refresh_base:
        export_probe_coreml(base_module, base_path)
        print(f"Refreshed base Core ML from weights: {base_path}", file=sys.stderr)

    output = args.coreml_dir / OUTPUT_NAME
    export_heatmap_coreml(heatmap_module, output)
    print(f"Wrote {output}", file=sys.stderr)

    import coremltools as ct

    report: list[dict[str, float | int]] = []
    if not args.skip_coreml_verify:
        mlmodel = ct.models.MLModel(str(output))
        original = ct.models.MLModel(str(base_path))
        with torch.inference_mode():
            for index, pixels in enumerate(samples):
                torch_prob, torch_map = heatmap_module(pixels)
                out = mlmodel.predict({"pixel_values": pixels.numpy().astype(np.float32)})
                cm_prob = float(np.asarray(out["fake_prob"]).reshape(-1)[0])
                cm_map = np.asarray(out["patch_map"]).reshape(24, 24)
                t_map = torch_map.numpy().reshape(24, 24)
                corr = float(np.corrcoef(cm_map.ravel(), t_map.ravel())[0, 1])
                original_prob = float(
                    np.asarray(
                        original.predict({"pixel_values": pixels.numpy().astype(np.float32)})["fake_prob"]
                    ).reshape(-1)[0]
                )
                torch_f = float(torch_prob)
                base_drift = abs(original_prob - torch_f)
                heatmap_drift = abs(cm_prob - torch_f)
                report.append({
                    "sample": index,
                    "torch_prob": torch_f,
                    "coreml_prob": cm_prob,
                    "original_coreml_prob": original_prob,
                    "map_correlation": corr,
                    "base_torch_drift": base_drift,
                    "heatmap_torch_drift": heatmap_drift,
                })
                print(
                    f"[coreml] sample {index}: prob {cm_prob:.5f} "
                    f"(base Core ML {original_prob:.5f}, torch {torch_f:.5f}); "
                    f"map corr {corr:.4f}; drift vs torch base {base_drift:.4f} heatmap {heatmap_drift:.4f}",
                    file=sys.stderr,
                )
                if abs(cm_prob - original_prob) > 1e-3:
                    raise RuntimeError(
                        "Heatmap export changed fake_prob relative to the base Core ML model "
                        f"(sample {index}: heatmap {cm_prob:.5f} vs base {original_prob:.5f})"
                    )
                # Core ML uses reduced precision; heatmap must not drift more than the base export.
                if heatmap_drift > base_drift + 5e-3:
                    raise RuntimeError(
                        "Core ML heatmap fake_prob drifts more than base export vs PyTorch "
                        f"(sample {index}: heatmap drift {heatmap_drift:.4f} > base {base_drift:.4f} + 5e-3)"
                    )
                if corr < 0.98:
                    raise RuntimeError(f"Core ML patch_map correlation too low on sample {index}: {corr:.4f}")

    metadata = json.loads((args.coreml_dir / "community_forensics_vit_rich_probe.json").read_text())
    metadata["output_name"] = ["fake_prob", "patch_map"]
    metadata["patch_map"] = {
        "shape": [1, 24, 24],
        "units": "logit contribution; positive pushes toward fake",
        "covers": "the 384x384 center crop (short edge resized to 440)",
        "excludes": "global CLS terms and the spatially uniform patch_mean·weight term",
    }
    (args.coreml_dir / OUTPUT_NAME.replace(".mlpackage", ".json")).write_text(json.dumps(metadata, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
