# CommunityForensics ViT fine-tuning (custom data)

Fine-tune on a new fake/real folder without changing the mobile export scripts yet.
Outputs live under `checkpoints/community_forensics_finetune/<run_name>/`.

## Dataset layout

Point `dataset_root` at a directory with two class folders (names configurable in JSON):

```text
/path/to/your/dataset/
├── fake/    # label 1 (AI / manipulated — your positive class)
│   └── ...
└── real/    # label 0
    └── ...
```

Supported extensions: `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`.

`ml/data/` is gitignored; keep datasets anywhere on disk and set an absolute or
`ml/`-relative path in config.

## Config

```bash
cd ml
cp config/community_forensics_finetune.example.json config/community_forensics_finetune.json
```

Edit `community_forensics_finetune.json`:

| Field | Purpose |
|-------|---------|
| `dataset_root` | **Required** — path to the folder above |
| `run_name` | Output subdirectory name |
| `mode` | `probe` (default), `backbone`, or `all` |
| `mix_base_feature_caches` | When true, probe training also mixes in existing universal feature caches (Deepfake, SDFVD, DF40, 140k) if present |
| `logistic_c` | Rich linear probe regularization (default `0.01`; try `0.05` for weaker L2) |
| `train_val_fraction` | Fraction of each class used for **training** (rest is validation metrics) |
| `backbone.*` | Optional ViT fine-tune before probe (`train_classifier_only` default true) |
| `backbone.unfreeze_encoder_layers` | With `train_classifier_only: true`, also train the last N ViT encoder blocks (e.g. `2`) |

## Commands

Custom folder (manual `dataset_root`):

```bash
cd ml
uv run python -m scripts.train.community_forensics_vit_finetune
uv run python -m scripts.train.community_forensics_vit_finetune --dataset-root /path/to/dataset
uv run python -m scripts.train.community_forensics_vit_finetune --rebuild-cache
uv run python -m scripts.train.community_forensics_vit_finetune --mode all
uv run python -m scripts.train.community_forensics_vit_finetune --no-mix-base
```

Hugging Face presets (download → `data/finetune/…` → fine-tune):

```bash
cd ml
uv run python -m scripts.train.community_forensics_vit_finetune_julienlucas
uv run python -m scripts.train.community_forensics_vit_finetune_julienlucas_nanobanana
uv run python -m scripts.train.community_forensics_vit_finetune_julienlucas_genai_combined --materialize-test
uv run python -m scripts.train.community_forensics_vit_finetune_cifake_defactify_balance
uv run python -m scripts.train.community_forensics_vit_finetune_cifake
uv run python -m scripts.train.community_forensics_vit_finetune_defactify --hf-splits train validation
uv run python -m scripts.train.community_forensics_vit_finetune_dfbench
uv run python -m scripts.train.community_forensics_vit_finetune_sofake
uv run python -m scripts.train.community_forensics_vit_finetune_sofake --chunks 5 --chunk-fake 200 --chunk-real 400
```

**So-Fake (streaming chunks):** `community_forensics_vit_finetune_sofake` streams
`saberzl/So-Fake-Set`, writes a capped chunk to a temp folder, extracts ViT features,
deletes images, and appends to `cache/community-forensics-vit/finetune_<run>_sofake_accum.npz`.
`full_synthetic` and `tampered` → fake; `real` → real. Use `--clear-accum` to restart accumulation.
Default `--parquet-shards` walks one HF parquet file at a time (long runs). Baseline probe snapshot:
`checkpoints/community_forensics_finetune/snapshots/so_fake_probe_baseline/`. Long run example:
`--run-name so_fake_probe_v2 --clear-accum --chunks 30`.

**So-Fake three-way (real / synthetic / tampered):** separate checkpoint tree, no binary
`mix_base`. Streams **500 + 500 + 500** per chunk by default (`full_synthetic` → synthetic,
`tampered` → tampered, `real` → real). Outputs under
`checkpoints/community_forensics_sofake_tertiary/<run_name>/`.

```bash
cd ml
uv run python -m scripts.train.community_forensics_vit_finetune_sofake_tertiary
uv run python -m scripts.train.community_forensics_vit_finetune_sofake_tertiary --chunks 30 --clear-accum
```

Local inference:

```bash
cd ml
uv run python -m scripts.predict.community_forensics_vit_predict_image_tertiary path/to/photo.jpg
uv run python -m scripts.predict.community_forensics_vit_predict_image_tertiary --run-name so_fake_tertiary_probe --json photo.jpg
```

**Track misses** (binary vs tertiary on your Bluesky failures): see [eval/misses/README.md](../eval/misses/README.md).

```bash
cd ml
cp eval/misses/manifest.example.json data/eval_misses/manifest.json   # edit paths
uv run python -m scripts.eval.community_forensics_vit_eval_misses --manifest data/eval_misses/manifest.json
```

Mobile export for the 3-class probe is not wired yet; compare tampered recall vs the binary probe on your own images.

Use `--skip-download` after the first materialization. Legacy CNN/audio trainers live under `old_models/`.

**Rebalance toward real photos** after gen-AI-heavy runs: `community_forensics_vit_finetune_cifake_defactify_balance` (Defactify = COCO-style reals; CIFAKE = extra real/fake pairs, low-res CIFAR source). Use `--real-only` to add reals without new fakes. Keep `mix_base_feature_caches: true`.

### Single-image check (local PyTorch)

```bash
cd ml
uv run python -m scripts.predict.community_forensics_vit_predict_image path/to/photo.jpg
uv run python -m scripts.predict.community_forensics_vit_predict_image --run-name julienlucas_genai_combined path/to/photo.jpg
uv run python -m scripts.predict.community_forensics_vit_predict_image --json --weights checkpoints/coreml/community_forensics_vit_rich_probe_weights.npz path/to/photo.jpg
```

## Outputs

- `community_forensics_vit_rich_probe_weights.npz` — probe weights (same format as `checkpoints/coreml/`)
- `finetune_report.json` — sample counts, validation accuracy / ROC-AUC
- `vit_backbone_best.pt` — only when `mode` is `backbone` or `all`
- Feature caches under `cache/community-forensics-vit/finetune_<run_name>_vit_features_{train,val}.npz`

## Ship to apps

After you are happy with validation metrics:

1. Copy the new `.npz` over `checkpoints/coreml/community_forensics_vit_rich_probe_weights.npz` (or point export scripts at the finetune output).
2. Re-run Core ML / TFLite export (`scripts/export/community_forensics_vit_*`).

Universal base caches: run `uv run test_community_forensics_vit.py --eval-deepfake` and
`--eval-cross-dataset` first if you want `mix_base_feature_caches` to include them.
