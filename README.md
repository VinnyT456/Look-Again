# Look Again: Image and Video Forgery Detection

Research code for face-swap and deepfake image classification, with experiments
for frame-level video evaluation. Training and evaluation runs use local
datasets under `data/` and write checkpoints and reports to dedicated folders.

## Quick start

```bash
uv sync
uv run python -m scripts.train.inception_resnet_v1_140k --help
uv run python -m scripts.evaluate.eval_checkpoint --help
```

Run a model training script from the repository root, for example:

```bash
uv run python -m scripts.train.inception_resnet_v1_140k
uv run python -m scripts.train.efficientnet_b0
uv run python -m scripts.train.mobilenetv3_large
```

Use the video-frame evaluation entry point with a saved checkpoint:

```bash
uv run python -m scripts.evaluate.sdfvd --run-name inception_resnet_v1_140k
```

See [experiment notes](docs/experiments.md) for dataset expectations, training
options, classical baselines, and detailed commands.

Clean up out-of-range clips under `Mix/fake` and `Mix/real` before audio training
(`Mix/info.txt` is ignored):

```bash
uv run python -m scripts.prepare.cleanup_mix_audio --dry-run
uv run python -m scripts.prepare.cleanup_mix_audio --min-seconds 1 --max-seconds 15
```

Rejected files move to `Mix/_duration_rejected/` or `Mix/_duplicate_rejected/` unless you pass `--delete`.
Duplicate detection runs by default (SHA-256, separately within `fake/` and `real/`).
Use `--skip-duplicates` or `--skip-duration` to run only one pass.

## Repository layout

```text
look-again/
├── Mix/                   # Audio: fake/, real/, optional info.txt (ignored by cleanup)
├── data/                  # Local datasets and generated frame/crop data
├── notebooks/             # Exploratory and comparison notebooks
├── scripts/               # Training, evaluation, preparation, and prediction CLIs
├── src/look_again/        # Reusable models, data, preprocessing, and evaluation code
├── tests/                 # Automated tests
├── docs/                  # Experiment and benchmark notes
├── examples/              # Small, visual examples
├── cache/                 # Rebuildable local caches
├── checkpoints/           # Saved model weights
└── results/               # Metrics, plots, and prediction outputs
```

`data/`, `cache/`, `checkpoints/`, and `results/` are local working folders and
are excluded from version control. Add only small metadata or documentation
needed to reproduce a run to Git.
