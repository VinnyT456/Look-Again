"""Fine-tune CommunityForensics ViT on julienlucas/midjourney-dalle-sd-dataset.

Downloads the HF train split into ``data/finetune/julienlucas/train/{fake,real}/``,
then runs probe fine-tuning (optional backbone) with universal cache mix.

Usage (from ``ml/``):

  uv run python -m scripts.train.community_forensics_vit_finetune_julienlucas
  uv run python -m scripts.train.community_forensics_vit_finetune_julienlucas --skip-download
  uv run python -m scripts.train.community_forensics_vit_finetune_julienlucas --mode all --rebuild-cache
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from look_again.community_forensics_finetune import FinetuneConfig, run_finetune
from look_again.hf_binary_dataset import materialize_hf_split
from look_again.paths import DATA_DIR, PROJECT_ROOT

HF_DATASET_ID = "julienlucas/midjourney-dalle-sd-dataset"
DEFAULT_DATA_ROOT = DATA_DIR / "finetune" / "julienlucas" / "train"
DEFAULT_RUN_NAME = "julienlucas_midjourney_dalle_sd"


def main() -> None:
    parser = argparse.ArgumentParser(description="ViT fine-tune on julienlucas Midjourney/DALL-E/SD dataset")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Local fake/real folder root (default: data/finetune/julienlucas/train)",
    )
    parser.add_argument("--skip-download", action="store_true", help="Use existing materialized images")
    parser.add_argument("--streaming", action="store_true", help="Stream HF rows instead of full download")
    parser.add_argument("--max-per-class", type=int, default=None, help="Cap images per class when exporting")
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--mode", choices=("probe", "backbone", "all"), default="probe")
    parser.add_argument("--rebuild-cache", action="store_true")
    parser.add_argument("--no-mix-base", action="store_true", help="Train probe only on this dataset")
    args = parser.parse_args()

    data_root = args.data_root if args.data_root.is_absolute() else (PROJECT_ROOT / args.data_root).resolve()
    if not args.skip_download:
        manifest = materialize_hf_split(
            dataset_id=HF_DATASET_ID,
            split="train",
            output_root=data_root,
            max_per_class=args.max_per_class,
            streaming=args.streaming,
            filename_prefix="mjdsd_",
        )
        print(json.dumps(manifest, indent=2), file=sys.stderr)

    config = FinetuneConfig(
        run_name=args.run_name,
        dataset_root=data_root,
        mode=args.mode,
        mix_base_feature_caches=not args.no_mix_base,
        rebuild_feature_cache=args.rebuild_cache,
    )
    report = run_finetune(config)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
