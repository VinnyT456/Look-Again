"""Quantize the Android detector's weights to int8 (activations stay float).

Dynamic-range int8 makes the model ~4× smaller and lets LiteRT's XNNPACK use
its int8 matrix kernels, which is roughly twice as fast on phone CPUs. Before
writing anything, it checks on real images that the quantized model keeps the
float model's decisions and heatmaps.

Usage (Python 3.12 env with ai-edge-quantizer and ai-edge-litert):

  .venv-litert/bin/python scripts/export/quantize_tflite.py \
      --images data/Deepfake/fake --images data/Deepfake/real --per-folder 40

Then copy the int8 file to apps/android/app/src/main/assets/wildcat_detector.tflite.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

DEFAULT_INPUT = _PROJECT_ROOT / "checkpoints" / "tflite" / "community_forensics_vit_rich_probe_heatmap.tflite"


def preprocess(path: Path, processor) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    return processor(images=image, return_tensors="np")["pixel_values"].astype(np.float32)


def run(interpreter, pixels: np.ndarray) -> tuple[float, np.ndarray]:
    interpreter.set_tensor(interpreter.get_input_details()[0]["index"], pixels)
    interpreter.invoke()
    prob, patch_map = None, None
    for detail in interpreter.get_output_details():
        value = interpreter.get_tensor(detail["index"])
        if value.size == 1:
            prob = float(value.reshape(-1)[0])
        elif value.size == 576:
            patch_map = value.reshape(-1)
    return prob, patch_map


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--recipe", default="dynamic_wi8_afp32")
    parser.add_argument("--images", type=Path, action="append", default=[], help="Folder(s) of images to verify on")
    parser.add_argument("--per-folder", type=int, default=40)
    args = parser.parse_args()
    output = args.output or args.input.with_name(args.input.stem + "_int8.tflite")

    from ai_edge_litert.interpreter import Interpreter
    from ai_edge_quantizer import quantizer, recipe
    from transformers import ViTImageProcessor

    from look_again.community_forensics_vit_probe import MODEL_CACHE, MODEL_ID

    q = quantizer.Quantizer(str(args.input))
    q.load_quantization_recipe(getattr(recipe, args.recipe)())
    result = q.quantize()
    output.write_bytes(result.quantized_model)
    print(f"Wrote {output} ({output.stat().st_size / 1e6:.1f} MB)", file=sys.stderr)

    processor = ViTImageProcessor.from_pretrained(MODEL_ID, cache_dir=MODEL_CACHE)
    float_model = Interpreter(model_path=str(args.input), num_threads=8)
    int8_model = Interpreter(model_path=str(output), num_threads=8)
    float_model.allocate_tensors()
    int8_model.allocate_tensors()

    rng = random.Random(0)
    paths: list[Path] = []
    for folder in args.images:
        files = sorted(p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
        paths += rng.sample(files, min(args.per_folder, len(files)))

    diffs, flips, corrs = [], 0, []
    for path in paths:
        pixels = preprocess(path, processor)
        fp, fmap = run(float_model, pixels)
        qp, qmap = run(int8_model, pixels)
        diffs.append(abs(fp - qp))
        flips += (fp >= 0.5) != (qp >= 0.5)
        if np.std(fmap) > 0 and np.std(qmap) > 0:
            corrs.append(float(np.corrcoef(fmap, qmap)[0, 1]))

    report = {
        "images": len(paths),
        "decision_flips": int(flips),
        "prob_abs_diff_mean": float(np.mean(diffs)) if diffs else None,
        "prob_abs_diff_max": float(np.max(diffs)) if diffs else None,
        "heatmap_corr_min": float(np.min(corrs)) if corrs else None,
        "heatmap_corr_mean": float(np.mean(corrs)) if corrs else None,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
