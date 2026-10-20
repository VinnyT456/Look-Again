"""Fine-tune CommunityForensics ViT on a custom fake/real image folder.

1. Copy config/community_forensics_finetune.example.json → config/community_forensics_finetune.json
2. Set ``dataset_root`` to your folder (``fake/`` and ``real/`` subdirs).
3. Run from ``ml/``:

   uv run python -m scripts.train.community_forensics_vit_finetune
   uv run python -m scripts.train.community_forensics_vit_finetune --rebuild-cache
   uv run python -m scripts.train.community_forensics_vit_finetune --mode backbone
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from look_again.community_forensics_finetune import (
    DEFAULT_CONFIG_PATH,
    FinetuneConfig,
    load_finetune_config,
    run_finetune,
)
from look_again.paths import PROJECT_ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune CommunityForensics ViT on custom data")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"JSON config (default: {DEFAULT_CONFIG_PATH.relative_to(PROJECT_ROOT)})",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=None,
        help="Override dataset_root from config",
    )
    parser.add_argument(
        "--mode",
        choices=("probe", "backbone", "all"),
        default=None,
        help="Override config mode",
    )
    parser.add_argument(
        "--run-name",
        default=None,
        help="Override config run_name (output under checkpoints/community_forensics_finetune/)",
    )
    parser.add_argument(
        "--rebuild-cache",
        action="store_true",
        help="Re-extract ViT features for the custom dataset",
    )
    parser.add_argument(
        "--no-mix-base",
        action="store_true",
        help="Train probe only on the custom dataset (no universal cache mix)",
    )
    args = parser.parse_args()

    try:
        config = load_finetune_config(args.config)
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        sys.exit(1)

    if args.dataset_root is not None:
        config.dataset_root = args.dataset_root
    if args.mode is not None:
        config.mode = args.mode
    if args.run_name is not None:
        config.run_name = args.run_name
    if args.rebuild_cache:
        config.rebuild_feature_cache = True
    if args.no_mix_base:
        config.mix_base_feature_caches = False

    try:
        config.resolved_dataset_root()
    except ValueError as error:
        print(error, file=sys.stderr)
        sys.exit(1)

    print(f"Starting fine-tune run_name={config.run_name!r} …", file=sys.stderr)
    report = run_finetune(config)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
