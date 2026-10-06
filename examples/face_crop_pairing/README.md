# Paired vs unpaired face crops

Both strategies feed **one face crop at a time** into the classifier. The model never sees real and fake together in a single forward pass.

## Paired crops (`data/DF40_face_crops/`)

1. Detect the face on the **real** image.
2. Build a square crop window from that detection.
3. Apply the **same normalized window** to the paired **fake** image (scaled if resolutions differ).
4. Resize both crops to 256×256.

The fake crop is anchored to the real face geometry so both tiles show the same cheek/jaw region. That reduces easy shortcuts from different zoom or framing.

## Unpaired crops (`data/DF40_face_crops_unpaired/`)

1. Detect and crop the **real** image on its own.
2. Detect and crop the **fake** image on its own.
3. Each side keeps only pairs where **both** detections succeed.

This matches **video inference** (`crop_face` on every frame) and is what we use for the unpaired Inception training run.

## Files in this folder

| File | Description |
|------|-------------|
| `generate_example.py` | Builds visual comparison from one DF40 swap pair |
| `output/` | Generated images (safe to regenerate) |

Regenerate the illustration:

```bash
uv run python examples/face_crop_pairing/generate_example.py
```

Open `output/comparison.png` for a side-by-side view of full frames, crop windows, and final crops.

Train unpaired Inception on DF40 unpaired crops:

```bash
uv run python -m scripts.train.inception_resnet_v1_unpaired_crops
```

Build only the unpaired crop dataset:

```bash
uv run python -m scripts.prepare.prepare_df40 --build-face-crops unpaired
```
