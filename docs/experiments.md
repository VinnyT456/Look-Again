# Classical image-forensics experiments

The runner reuses the project’s local dataset download and identity-safe train/test split from `look_again.dataset`. It holds out validation identity groups from the existing training split. `--model all` compares models on validation and does not extract or score test features. A single-model command fits on train plus validation, then evaluates the untouched test split.

Feature extraction reads original images as PIL data; no neural network preprocessing or model runs in this pipeline.

Dataset currently provides two classes: `fake` and `real`. The runner preserves folder names and numeric IDs. It cannot train a `Cheapfake` class until examples for that class are added.

Run from the project root:

```bash
uv run python -m scripts.train.classical_ml --model logistic
uv run python -m scripts.train.classical_ml --model decision_tree
uv run python -m scripts.train.classical_ml --model random_forest
uv run python -m scripts.train.classical_ml --model svm
uv run python -m scripts.train.classical_ml --model hard_voting
uv run python -m scripts.train.classical_ml --model soft_voting
uv run python -m scripts.train.classical_ml --model weighted_soft_voting
uv run python -m scripts.train.classical_ml --model stacking
uv run python -m scripts.train.classical_ml --model all
```

Use grouped GridSearchCV to tune the base classifiers with macro F1 as the
selection score:

```bash
uv run python -m scripts.train.classical_ml --model random_forest --tune
uv run python -m scripts.train.classical_ml --model all --tune --cv-folds 3
```

Search folds are split by identity group and use only the current fitting split.
In `--model all` mode, tuning sees the training partition and reports the
validation partition afterward; the held-out test partition is not loaded. For a
single-model run, tuning uses train plus validation and evaluates the untouched
test partition. GridSearchCV tunes the base classifiers; ensemble comparisons
use their configured members. Candidate scores and best parameters are saved
beside the model results. Grid search can take several minutes, especially for
XGBoost and random forests.

Run the XGBoost command after installing its optional dependency:

```bash
uv sync --extra xgboost
uv run python -m scripts.train.classical_ml --model xgboost
```

`--model all` evaluates candidate models on validation. After choosing one, run its single-model command for final test evaluation. Use the saved model bundle for prediction:

```bash
uv run python -m scripts.predict.classical_ml \
  --model results/classical_ml/lbp-ela-dct-noise/models/random_forest.joblib \
  --image data/DF40/fake/fake_00000.jpg
```

Install optional XGBoost with `uv sync --extra xgboost`. Feature extraction caches under `cache/classical_ml/`; metrics, confusion matrices, feature-importance charts, model-comparison/ROC/runtime plots, grid-search plots, and model bundles go under `results/`.

Feature ablations use the same identity-safe split and cache separately:

```bash
uv run python -m scripts.train.classical_ml --model all --features lbp
uv run python -m scripts.train.classical_ml --model all --features ela
uv run python -m scripts.train.classical_ml --model all --features lbp ela
uv run python -m scripts.train.classical_ml --model all --features lbp ela dct noise
```

Pass a JSON file with per-model parameters using `--config`. Example:

```json
{
  "random_forest": {"n_estimators": 300, "max_depth": 24},
  "weighted_soft_voting": {
    "members": ["logistic", "random_forest", "svm"],
    "weights": {"logistic": 1, "random_forest": 1, "svm": 1}
  }
}
```

The default reports use actual dataset class names. Run `--model all` for validation comparisons, choose a model/configuration, then run that single model to produce final test metrics. The weighted-vote helper accepts candidate weights evaluated only on validation data; it never invents default weights.

RBF SVM and stacking cost more CPU time on this dataset. The first run also computes and caches image features; later runs with the same feature configuration reuse that cache.

## Neural-network backbones

These scripts use the shared timm setup, binary classifier head, identity-safe image split, training
loop, checkpointing, and optional robustness evaluation in `src/look_again/`.

| Backbone | Run |
| --- | --- |
| EfficientNet-B0 | `uv run python -m scripts.train.efficientnet_b0` |
| MobileNetV3-Large | `uv run python -m scripts.train.mobilenetv3_large` |
| MobileNetV3-Small | `uv run python -m scripts.train.mobilenetv3_small` |

`efficientnet_b0.py` fine-tunes an existing checkpoint when present, mixes DF40 with
Celeb-DF (350/class) and Kenjon train (800 fakes) using balanced source sampling,
train-time augmentation, a leak-safe validation holdout, and saves the best weights
by validation accuracy minus validation loss (50 epochs, lr=1e-4).

After training, run external/benchmark eval on a saved checkpoint:

```bash
uv run python -m scripts.evaluate.eval_checkpoint --run-name efficientnet_b0
```

Each neural run saves `{run_name}_best.pt` under `checkpoints/` and puts its
episode-level loss/accuracy plot under `results/neural/`. Benchmark,
robustness, Kenjon, and SDFVD reports are saved in the same results folder.

## Inception-ResNet-v1 on 140K real/fake faces

The dedicated FaceNet Inception-ResNet-v1 runner fine-tunes the VGGFace2
pretrained model by default. It auto-detects `data/real-vs-fake/` or
`data/140k-real-and-fake-faces/` (or pass `--dataset-root`). Expected layout:
`train/`, `valid/` (or `validation/`), and `test/` each with `fake/` and `real/`,
or a flat `{fake,real}` directory for a seeded 70/15/15 split. When a validation
folder is present, it is used for checkpoint selection; the test split is scored
once after training.

```bash
uv sync
uv run python -m scripts.train.inception_resnet_v1_140k
```

The first pretrained run downloads FaceNet's VGGFace2 weights (about 107 MB).
The model implementation is included locally so it uses the project's current
PyTorch/torchvision versions without downgrading them. To initialize
without pretrained weights, pass `--pretrained none`. Useful options include
`--epochs`, `--batch-size`, `--learning-rate`, `--num-workers`, and
`--dataset-root`. Checkpoints go to `checkpoints/`; epoch metrics, a plot, and
the final held-out test summary go to `results/neural/`.

EfficientNet-B0 on the same 140K baseline (no DF40 / Celeb / Kenjon mix):

```bash
uv run python -m scripts.train.efficientnet_b0_140k
```

Run the shared Celeb-DF, Kenjon, and DF40 robustness benchmarks (160×160 FaceNet
normalization, two-class logits mapped to fake/real):

```bash
uv run python -m scripts.evaluate.eval_checkpoint --run-name inception_resnet_v1_140k
uv run python -m scripts.evaluate.eval_checkpoint --run-name efficientnet_b0_140k
```

## Mix audio — feature extraction (preprocessing only)

Labeled clips: `Mix/fake/` and `Mix/real/` (`info.txt` ignored). Librosa loads mono 16 kHz audio; optional peak normalization; silence trim off by default. Frame features (MFCC, ZCR, spectral centroid/bandwidth/rolloff, spectral contrast, RMS) aggregate to a **fixed-length vector per file**. Output tabular dataset (no train/test split here):

```bash
# Dev: 100 clips
uv run python -m scripts.prepare.build_audio_features --max-samples 100 --no-resume

# 10k / 50k / full Mix (~147k)
uv run python -m scripts.prepare.build_audio_features --max-samples 10000 --no-resume
uv run python -m scripts.prepare.build_audio_features --max-samples 50000 --no-resume
uv run python -m scripts.prepare.build_audio_features --workers 8

# Reload + validate an existing Parquet export
uv run python -m scripts.prepare.build_audio_features --validate-only data/processed/audio_features.parquet
```

Writes `data/processed/audio_features.parquet`, skip log `audio_features_skipped.csv`, run summary JSON. Checkpoints every 5k rows; `--no-resume` for a clean rebuild.

## Mix audio — classifiers (RF / SVM / XGBoost)

Train on `data/processed/audio_features.parquet` (build features first). Checkpoints: `checkpoints/audio_{model}_best.joblib`.

```bash
uv sync --extra xgboost   # optional, for XGBoost

uv run python -m scripts.train.audio_classical_ml --model random_forest
uv run python -m scripts.train.audio_classical_ml --model svm
uv run python -m scripts.train.audio_classical_ml --model xgboost
uv run python -m scripts.train.audio_classical_ml --model all

uv run python -m scripts.train.audio_classical_ml --model all --tune --cv-folds 3
uv run python -m scripts.train.audio_classical_ml --model svm --eval-test

# Smoke run on a small feature table
uv run python -m scripts.train.audio_classical_ml --model all \
  --features-parquet data/processed/audio_features_smoke.parquet --max-samples 100
```

Legacy alias: `scripts.train.audio_random_forest` → same as `--model random_forest`.

Results under `results/classical_ml/audio/<model>/`.

Prepare/clean Mix audio first if needed:

```bash
uv run python -m scripts.prepare.cleanup_mix_audio --dry-run
```

## Mix audio — frozen Wav2Vec2 / WavLM (PyTorch)

Raw 16 kHz waveforms; frozen Hugging Face encoder; trainable head only (`0=real`, `1=fake`).

```bash
uv run python -m scripts.validate.speech_deepfake_smoke
uv run python -m scripts.train.speech_deepfake --model-name facebook/wav2vec2-base-960h
uv run python -m scripts.train.speech_deepfake --model-name microsoft/wavlm-base-plus
uv run python -m scripts.train.speech_deepfake --max-samples 1000 --epochs 2
uv run python -m scripts.train.speech_deepfake --full-dataset
uv run python -m scripts.train.speech_deepfake --cache-embeddings --max-samples 5000
uv run python -m scripts.evaluate.speech_deepfake_compare
```

Head checkpoints: `checkpoints/speech_deepfake/{wav2vec2,wavlm}/best_head.pt`. Metrics: `results/speech_deepfake/{wav2vec2,wavlm}/`.
