#!/usr/bin/env bash
# Export so_fake (or other) probe weights to Core ML + TFLite and copy into iOS/Android apps.
# Run from anywhere:  bash ml/scripts/export_and_copy_mobile.sh
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
ml="$root/ml"
run_name="${1:-so_fake_probe_v2}"
sample="$root/apps/ios/WildcatVerify/WildcatVerifyTests/Fixtures/gradient.png"
ios_dest="$root/apps/ios/WildcatVerify/WildcatVerify/Resources/Models/WildcatDetector.mlpackage"
coreml_out="$ml/checkpoints/coreml/community_forensics_vit_rich_probe_heatmap.mlpackage"
weights_src="$ml/checkpoints/community_forensics_finetune/$run_name/community_forensics_vit_rich_probe_weights.npz"
weights_coreml="$ml/checkpoints/coreml/community_forensics_vit_rich_probe_weights.npz"
litert_py="$ml/.venv-litert/bin/python"

if [[ ! -f "$weights_src" ]]; then
  echo "Missing weights: $weights_src" >&2
  exit 1
fi
if [[ ! -f "$sample" ]]; then
  echo "Missing sample image: $sample" >&2
  exit 1
fi
if [[ ! -x "$litert_py" ]]; then
  echo "Missing LiteRT venv: $litert_py (see ml/scripts/export/community_forensics_vit_heatmap_tflite.py)" >&2
  exit 1
fi

cp "$weights_src" "$weights_coreml"
echo "Weights: $run_name -> checkpoints/coreml/"

cd "$ml"
uv sync --extra export
uv run python -m scripts.export.community_forensics_vit_heatmap_coreml \
  --sample-image "$sample"

rm -rf "$ios_dest"
cp -R "$coreml_out" "$ios_dest"
echo "iOS: $ios_dest"

"$litert_py" -m scripts.export.community_forensics_vit_heatmap_tflite \
  --weights "$weights_coreml" \
  --sample-image "$sample"

bash "$root/apps/android/scripts/copy_model.sh"
echo "Done."
