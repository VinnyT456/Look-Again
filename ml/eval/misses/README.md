# Track probe misses (manual eval set)

Keep a **fixed list** of images where the shipped **binary** probe was wrong (or borderline), plus what you think the truth is. Re-run after each training/export to see if things improved.

## Setup

1. Copy the example manifest and edit it:

   ```bash
   mkdir -p data/eval_misses
   cp eval/misses/manifest.example.json data/eval_misses/manifest.json
   ```

2. Add rows: path (relative to `ml/` or absolute), `expected` class, optional `note`.

   **expected** (aliases OK): `real` | `synthetic` / `ai` / `fake` | `tampered` / `edited`

3. Put images anywhere on disk; paths in the manifest point to them.

**Or** use folder layout (no manifest):

```text
data/eval_misses/
  real/
  synthetic/    # or fake/
  tampered/     # or edited/
```

## Run

```bash
cd ml
uv run python -m scripts.eval.community_forensics_vit_eval_misses \
  --manifest data/eval_misses/manifest.json

uv run python -m scripts.eval.community_forensics_vit_eval_misses \
  --dataset-root data/eval_misses

uv run python -m scripts.eval.community_forensics_vit_eval_misses \
  --manifest data/eval_misses/manifest.json \
  --binary-run-name so_fake_probe \
  --tertiary-run-name so_fake_tertiary_probe \
  --output results/misses_report.json
```

## Output

- Prints a table: expected vs binary vs tertiary, flags **binary_miss**, **tertiary_miss**, **tertiary_fixed** (binary wrong, tertiary right).
- Writes JSON report (default `results/misses_<timestamp>.json`).

Grow the manifest from Bluesky failures, screenshots, and ChatGPT exports — that set is your real scorecard, not So-Fake val recall alone.
