"""After re-exporting the detector, refresh the Core ML test reference in
WildcatVerifyTests/Fixtures/reference.json from the app's current model.

Usage (from the repo root):
  ml/.venv/bin/python -I apps/ios/WildcatVerify/Design/regen_test_reference.py \
      apps/ios/WildcatVerify ml
"""
import json
import sys
from pathlib import Path

import coremltools as ct
import numpy as np
from PIL import Image

app = Path(sys.argv[1])
sys.path.insert(0, str(Path(sys.argv[2]) / "src"))
from look_again.community_forensics_vit_probe import load_community_forensics_vit

_, processor = load_community_forensics_vit("cpu")
model = ct.models.MLModel(str(app / "WildcatVerify/Resources/Models/WildcatDetector.mlpackage"))
fixtures = app / "WildcatVerifyTests/Fixtures"
ref_path = fixtures / "reference.json"
ref = json.loads(ref_path.read_text())
for name in ref:
    img = Image.open(fixtures / f"{name}.png").convert("RGB")
    pixels = processor(img, return_tensors="np")["pixel_values"].astype(np.float32)
    out = model.predict({"pixel_values": pixels})
    old = ref[name]["fake_prob"]
    ref[name]["fake_prob"] = round(float(np.asarray(out["fake_prob"]).reshape(-1)[0]), 5)
    ref[name]["patch_map"] = [round(float(v), 6) for v in np.asarray(out["patch_map"]).reshape(-1)]
    print(name, "old", old, "new", ref[name]["fake_prob"],
          "tensor_mean", round(float(pixels.mean()), 5), "vs", ref[name]["tensor_mean"])
ref_path.write_text(json.dumps(ref, indent=2) + "\n")
