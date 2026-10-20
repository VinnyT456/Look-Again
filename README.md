# Look Again

Research and mobile apps for **AI-generated / manipulated image** detection (CommunityForensics ViT +
rich linear probe). Primary product: **WildcatVerify** (iOS/Android).

## Layout

```text
look-again/
├── ml/          # Training, finetune, export, predict (see ml/README.md)
├── apps/
│   ├── ios/WildcatVerify/
│   └── android/
├── PRODUCT.md
├── DESIGN.md
└── README.md
```

## ML

```bash
cd ml
uv sync
uv run python -m scripts.predict.community_forensics_vit_predict_image path/to/photo.jpg
```

- **Models & datasets:** [ml/README.md](ml/README.md) (backbone, finetune `run_name`s, HF presets, ship artifacts)
- **Fine-tuning:** [ml/docs/community_forensics_finetune.md](ml/docs/community_forensics_finetune.md)
- **Legacy CNN/audio:** `ml/old_models/`

Ship path: finetune probe → copy `.npz` to `ml/checkpoints/coreml/` →
`community_forensics_vit_heatmap_coreml` → `apps/ios/.../WildcatDetector.mlpackage`.

## Mobile

- iOS: [apps/ios/WildcatVerify/README.md](apps/ios/WildcatVerify/README.md)
- Android: [apps/android/README.md](apps/android/README.md)

Models are exported from `ml/checkpoints/coreml/` and `ml/checkpoints/tflite/` (gitignored locally).
