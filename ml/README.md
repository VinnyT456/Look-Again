# Look Again — ML / research

Gen-AI and forgery **image** detection on **CommunityForensics ViT** + a **rich linear probe**
(frozen backbone, trainable scaler + logistic on ViT features). Ships to iOS/Android as Core ML /
TFLite with an optional per-patch heatmap.

All commands below run from **`ml/`**.

## Quick start

```bash
cd ml
uv sync
uv run test_community_forensics_vit.py --eval-deepfake
uv run python -m scripts.predict.community_forensics_vit_predict_image path/to/photo.jpg
```

Build universal probe caches (for `mix_base` and stock export):

```bash
uv run test_community_forensics_vit.py --eval-deepfake --rebuild-cache
uv run test_community_forensics_vit.py --eval-cross-dataset --rebuild-cache
```

## Models

### Backbone (Hugging Face)

| ID | Role |
|----|------|
| [`buildborderless/CommunityForensics-DeepfakeDet-ViT`](https://huggingface.co/buildborderless/CommunityForensics-DeepfakeDet-ViT) | Frozen ViT + stock classifier head; cached under `cache/community-forensics-vit/` |

### On-device artifacts (`checkpoints/coreml/`, `checkpoints/tflite/`)

| File | Role |
|------|------|
| `community_forensics_vit_rich_probe_weights.npz` | Probe weights (ship this after finetune) |
| `community_forensics_vit_rich_probe_heatmap.mlpackage` | Core ML: `fake_prob` + `patch_map` → copy to iOS as `WildcatDetector.mlpackage` |
| `community_forensics_vit_rich_probe.mlpackage` | Decision-only Core ML (refreshed by heatmap export) |
| `community_forensics_vit_rich_probe_heatmap.tflite` | Android heatmap model |

**Do not** use `community_forensics_vit_coreml.py` after a custom finetune — it **refits** the universal
probe from caches. Copy your finetune `.npz` into `checkpoints/coreml/`, then run
`scripts/export/community_forensics_vit_heatmap_coreml.py`.

### Finetuned probes (`checkpoints/community_forensics_finetune/<run_name>/`)

Each run writes `community_forensics_vit_rich_probe_weights.npz` and `finetune_report.json`.

| `run_name` | Source |
|------------|--------|
| `julienlucas_midjourney_dalle_sd` | `julienlucas/midjourney-dalle-sd-dataset` |
| `julienlucas_nanobanana` | `julienlucas/midjourney-dalle-sd-nanobananapro-dataset` |
| `julienlucas_genai_combined` | Both julienlucas gen-AI sets |
| `cifake` | `batgre/CIFAKE` |
| `defactify` | `Rajarshi-Roy-research/Defactify_Image_Dataset` |
| `cifake_defactify_balance` | CIFAKE + Defactify (real-heavy caps) |
| `dfbench_image25` | `DFBench/DFBench_Image25` |
| `so_fake_probe` | `saberzl/So-Fake-Set` (chunked stream) |
| `so_fake_probe_v2` | So-Fake long run (parquet shards; recommended) |
| `genai_plus_balance` | Custom merge: julienlucas fakes + balance reals (manual folders) |
| *(config)* | `community_forensics_vit_finetune` + `config/community_forensics_finetune.json` |

**Snapshot:** `checkpoints/community_forensics_finetune/snapshots/so_fake_probe_baseline/` —
saved baseline probe + feature accum.

**Mix-base training:** when `mix_base_feature_caches` is true, probe fit also uses ViT feature
caches from `data/Deepfake/`, SDFVD, DF40, and 140k test (if built via `test_community_forensics_vit.py`).

### Legacy (`old_models/`)

Archived CNN face-swap trainers (Inception-ResNet, EfficientNet, MobileNet), audio classical
models, and speech-deepfake heads. See `old_models/README.md` and `docs/experiments.md`.

## Datasets

### Hugging Face (preset train scripts)

| Hugging Face dataset | Train module |
|---------------------|--------------|
| `julienlucas/midjourney-dalle-sd-dataset` | `community_forensics_vit_finetune_julienlucas` |
| `julienlucas/midjourney-dalle-sd-nanobananapro-dataset` | `community_forensics_vit_finetune_julienlucas_nanobanana` |
| Both julienlucas (above) | `community_forensics_vit_finetune_julienlucas_genai_combined` |
| `batgre/CIFAKE` | `community_forensics_vit_finetune_cifake` |
| `Rajarshi-Roy-research/Defactify_Image_Dataset` | `community_forensics_vit_finetune_defactify` |
| CIFAKE + Defactify (balanced) | `community_forensics_vit_finetune_cifake_defactify_balance` |
| `DFBench/DFBench_Image25` | `community_forensics_vit_finetune_dfbench` |
| `saberzl/So-Fake-Set` | `community_forensics_vit_finetune_sofake` (`full_synthetic` + `tampered` → fake) |
| `saberzl/So-Fake-Set` (3-class) | `community_forensics_vit_finetune_sofake_tertiary` → `checkpoints/community_forensics_sofake_tertiary/` |

Related (eval, not wired to train CLI): `saberzl/So-Fake-OOD`.

Materialized images default to `data/finetune/<name>/train/{fake,real}/` (gitignored).

### Local (universal probe / cross-eval)

| Path (under `ml/data/`) | Use |
|-------------------------|-----|
| `Deepfake/` | Train & eval universal rich probe |
| `real-vs-fake/test` | 140k-style cross-eval |
| `DF40_face_crops_unpaired` | Cross-eval |
| `140k-real-and-fake-faces/` | Legacy CNN 140k (see `docs/experiments.md`) |

### Custom folder

`fake/` + `real/` with any supported image extension — see
[docs/community_forensics_finetune.md](docs/community_forensics_finetune.md).

## Train

Custom folder:

```bash
cp config/community_forensics_finetune.example.json config/community_forensics_finetune.json
# set dataset_root, run_name
uv run python -m scripts.train.community_forensics_vit_finetune
```

HF presets (examples):

```bash
uv run python -m scripts.train.community_forensics_vit_finetune_julienlucas_genai_combined
uv run python -m scripts.train.community_forensics_vit_finetune_cifake_defactify_balance
uv run python -m scripts.train.community_forensics_vit_finetune_sofake \
  --run-name so_fake_probe_v2 --clear-accum --chunks 30
```

So-Fake: chunked stream, deletes images after feature extract; resume via
`cache/.../finetune_<run>_sofake_accum.npz` + `.stream.json` (no `--clear-accum`). Default
`--parquet-shards` iterates one HF parquet file at a time for long runs.

Full finetune docs: [docs/community_forensics_finetune.md](docs/community_forensics_finetune.md).

## Predict (local PyTorch)

```bash
uv run python -m scripts.predict.community_forensics_vit_predict_image path/to/photo.jpg
uv run python -m scripts.predict.community_forensics_vit_predict_image --run-name so_fake_probe path/to/photo.jpg
uv run python -m scripts.predict.community_forensics_vit_predict_image \
  --weights checkpoints/coreml/community_forensics_vit_rich_probe_weights.npz path/to/photo.jpg
```

Threshold **0.5** matches iOS/Android (`fake_prob` ≥ 0.5 → Likely AI).

## Export to mobile

After copying finetune weights to `checkpoints/coreml/community_forensics_vit_rich_probe_weights.npz`:

```bash
uv sync --extra export
uv run python -m scripts.export.community_forensics_vit_heatmap_coreml \
  --sample-image ../apps/ios/WildcatVerify/WildcatVerifyTests/Fixtures/gradient.png
```

Copy `community_forensics_vit_rich_probe_heatmap.mlpackage` →
`apps/ios/WildcatVerify/WildcatVerify/Resources/Models/WildcatDetector.mlpackage`.

Android:

```bash
uv sync --extra export-android
uv run python -m scripts.export.community_forensics_vit_heatmap_tflite
```

Stock universal probe only (overwrites coreml npz):

```bash
uv run python -m scripts.export.community_forensics_vit_coreml
```

## Layout

```text
ml/
├── config/                # community_forensics_finetune.json (local, gitignored)
├── data/                  # datasets (gitignored)
├── cache/community-forensics-vit/   # ViT + finetune feature caches (gitignored)
├── checkpoints/
│   ├── coreml/            # ship weights + mlpackage (gitignored)
│   ├── tflite/
│   └── community_forensics_finetune/<run_name>/
├── scripts/train/         # ViT finetune CLIs
├── scripts/export/        # Core ML / TFLite
├── scripts/predict/
├── src/look_again/
├── old_models/            # legacy CNN / audio
├── docs/
└── test_community_forensics_vit.py
```

`look_again.paths.PROJECT_ROOT` resolves to this `ml/` directory.

## More

- [community_forensics_finetune.md](docs/community_forensics_finetune.md) — config, ship workflow, So-Fake
- [experiments.md](docs/experiments.md) — legacy baselines and eval commands
