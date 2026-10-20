"""Export the ViT rich probe to TFLite (LiteRT) with a per-patch heatmap output.

Android counterpart of ``community_forensics_vit_heatmap_coreml``. Rebuilds the
probe from the saved weights (no refitting), so the decision matches the iOS
model, and adds ``patch_map`` (1×24×24, logit units) for the Android app's
Highlight view.

Checks before writing anything the app uses:
  1. fake_prob matches the original probe module exactly.
  2. patch_map sums to the patch_std term of the logit (the decomposition is exact).
  3. TFLite outputs match PyTorch on each sample image.

Needs Python 3.12 with litert-torch (the main ml/ env is 3.13):

  uv venv --python 3.12 .venv-litert
  uv pip install --python .venv-litert/bin/python litert-torch transformers scikit-learn pillow ai-edge-litert
  .venv-litert/bin/python scripts/export/community_forensics_vit_heatmap_tflite.py \
      --sample-image path/a.png --sample-image path/b.png

Then copy the .tflite to apps/android/app/src/main/assets/wildcat_detector.tflite.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from PIL import Image  # noqa: E402

from look_again.community_forensics_vit_probe import (  # noqa: E402
    DEFAULT_COREML_DIR,
    DEFAULT_TFLITE_DIR,
    CommunityForensicsViTProbe,
    CommunityForensicsViTProbeHeatmap,
    load_community_forensics_vit,
    load_probe_module_from_npz,
)
from scripts.export.community_forensics_vit_heatmap_coreml import patch_std_term  # noqa: E402

WEIGHTS_NAME = "community_forensics_vit_rich_probe_weights.npz"
OUTPUT_NAME = "community_forensics_vit_rich_probe_heatmap.tflite"


def run_tflite(path: Path, pixels: np.ndarray) -> tuple[float, np.ndarray]:
    """Returns (fake_prob, 24×24 patch_map), telling the outputs apart by size."""
    from ai_edge_litert.interpreter import Interpreter

    interpreter = Interpreter(model_path=str(path))
    interpreter.allocate_tensors()
    interpreter.set_tensor(interpreter.get_input_details()[0]["index"], pixels.astype(np.float32))
    interpreter.invoke()
    prob, patch_map = None, None
    for detail in interpreter.get_output_details():
        value = interpreter.get_tensor(detail["index"])
        if value.size == 1:
            prob = float(value.reshape(-1)[0])
        elif value.size == 24 * 24:
            patch_map = value.reshape(24, 24)
    if prob is None or patch_map is None:
        raise RuntimeError("TFLite model is missing fake_prob or patch_map")
    return prob, patch_map


def main() -> None:
    parser = argparse.ArgumentParser(description="Export ViT rich probe + patch heatmap to TFLite")
    parser.add_argument("--weights", type=Path, default=DEFAULT_COREML_DIR / WEIGHTS_NAME,
                        help="Probe weights (defaults to the ones the iOS model was built from)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_TFLITE_DIR)
    parser.add_argument("--sample-image", type=Path, action="append", default=[], help="Image(s) to verify with")
    args = parser.parse_args()

    import litert_torch

    device = torch.device("cpu")
    heatmap_module = load_probe_module_from_npz(args.weights, device, CommunityForensicsViTProbeHeatmap)
    base_module = load_probe_module_from_npz(args.weights, device, CommunityForensicsViTProbe)
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

    output = args.output_dir / OUTPUT_NAME
    output.parent.mkdir(parents=True, exist_ok=True)
    with torch.inference_mode():
        edge = litert_torch.convert(heatmap_module, (torch.randn(1, 3, 384, 384),))
    edge.export(str(output))
    print(f"Wrote {output}", file=sys.stderr)

    report = []
    with torch.inference_mode():
        for index, pixels in enumerate(samples):
            torch_prob, torch_map = heatmap_module(pixels)
            tf_prob, tf_map = run_tflite(output, pixels.numpy())
            t_map = torch_map.numpy().reshape(24, 24)
            corr = float(np.corrcoef(tf_map.ravel(), t_map.ravel())[0, 1])
            report.append({"sample": index, "torch_prob": float(torch_prob), "tflite_prob": tf_prob,
                           "map_correlation": corr, "map_max_abs_diff": float(np.abs(tf_map - t_map).max())})
            print(f"[tflite] sample {index}: prob {tf_prob:.5f} (torch {float(torch_prob):.5f}); map corr {corr:.4f}",
                  file=sys.stderr)
            # float32 end to end, so this should agree far tighter than Core ML's float16.
            if abs(tf_prob - float(torch_prob)) > 1e-3 or corr < 0.999:
                raise RuntimeError("TFLite heatmap export does not match PyTorch")

    metadata = json.loads((args.output_dir / "community_forensics_vit_rich_probe.json").read_text())
    metadata["output_name"] = ["fake_prob", "patch_map"]
    metadata["patch_map"] = {
        "shape": [1, 24, 24],
        "units": "logit contribution; positive pushes toward fake",
        "covers": "the 384x384 center crop (short edge resized to 440)",
        "excludes": "global CLS terms and the spatially uniform patch_mean·weight term",
    }
    (args.output_dir / OUTPUT_NAME.replace(".tflite", ".json")).write_text(json.dumps(metadata, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
