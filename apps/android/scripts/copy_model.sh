#!/usr/bin/env bash
# Copies the detector from ml/ into the app's assets. The heatmap export
# (fake_prob + patch_map) is preferred; the plain export (fake_prob only) works
# too, the app just shows no heatmap.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
src_dir="$here/../../ml/checkpoints/tflite"
dest="$here/app/src/main/assets/wildcat_detector.tflite"
for name in community_forensics_vit_rich_probe_heatmap.tflite community_forensics_vit_rich_probe.tflite; do
  if [[ -f "$src_dir/$name" ]]; then
    mkdir -p "$(dirname "$dest")"
    cp "$src_dir/$name" "$dest"
    echo "Copied $name -> $dest"
    exit 0
  fi
done
echo "No .tflite found in $src_dir. Export one first (see ml/README.md)." >&2
exit 1
