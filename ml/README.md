# Look Again — ML / research

Face-swap and deepfake image classification, video-frame evaluation, classical
forensics baselines, and CommunityForensics ViT experiments.

All Python commands below are run from **`ml/`** (this directory).

## Quick start

```bash
cd ml
uv sync
uv run test_community_forensics_vit.py --help
uv run python -m scripts.train.community_forensics_vit_finetune --help
```

CommunityForensics ViT:

```bash
cd ml
uv run test_community_forensics_vit.py --eval-deepfake
uv run test_community_forensics_vit.py --eval-cross-dataset
```

Fine-tune on a custom fake/real folder (probe and optional backbone):

```bash
cd ml
cp config/community_forensics_finetune.example.json config/community_forensics_finetune.json
# edit dataset_root in the JSON, then:
uv run python -m scripts.train.community_forensics_vit_finetune
```

See [community_forensics_finetune.md](docs/community_forensics_finetune.md).

Preset HF fine-tunes:

```bash
cd ml
uv run python -m scripts.train.community_forensics_vit_finetune_cifake_defactify_balance
uv run python -m scripts.train.community_forensics_vit_finetune_julienlucas_genai_combined --materialize-test
uv run python -m scripts.train.community_forensics_vit_finetune_dfbench
uv run python -m scripts.train.community_forensics_vit_finetune_sofake --chunks 10
```

Legacy CNN/audio checkpoints and scripts: `old_models/`.

Export fused ViT + universal rich linear probe (C=0.01) to Core ML:

```bash
cd ml
uv python pin 3.13   # coremltools native wheels; 3.14 not supported yet
uv sync --extra export
uv run python -m scripts.export.community_forensics_vit_coreml
```

Writes `checkpoints/coreml/community_forensics_vit_rich_probe.mlpackage` plus JSON
metadata and probe weights. Model input: `pixel_values` float32 `[1, 3, 384, 384]`
after the same `ViTImageProcessor` preprocessing as training.

Android (`.tflite` via [LiteRT-Torch](https://ai.google.dev/edge/litert), runs on LiteRT / TFLite):

```bash
cd ml
uv python pin 3.13
uv sync --extra export-android
# Converter needs Python 3.12 + litert-torch (once per machine):
uv pip install --python python3.12 litert-torch
uv run python -m scripts.export.community_forensics_vit_tflite
```

Optional: `export LITERT_PYTHON=/path/to/python3.12` if `python3.12` is not on `PATH`.

Writes `checkpoints/tflite/community_forensics_vit_rich_probe.tflite` with the same
JSON metadata and probe weights. Preprocessing matches iOS (NCHW `pixel_values` → `fake_prob`).

See [experiment notes](docs/experiments.md) for datasets, baselines, and commands.

## Layout

```text
ml/
├── data/                  # Local datasets (gitignored)
├── Mix/                   # Audio fake/real clips (gitignored)
├── notebooks/
├── scripts/               # ViT train + export
├── old_models/            # Archived CNN/audio scripts + checkpoints
├── src/look_again/        # Library code
├── tests/
├── docs/
├── examples/
├── cache/                 # gitignored
├── checkpoints/           # gitignored (ViT Core ML / TFLite)
└── results/               # gitignored
```

`look_again.paths.PROJECT_ROOT` resolves to this `ml/` directory.
