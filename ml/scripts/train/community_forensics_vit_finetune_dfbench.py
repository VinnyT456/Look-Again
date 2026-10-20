"""Fine-tune CommunityForensics ViT on DFBench/DFBench_Image25.

Materializes images to ``data/finetune/dfbench_image25/{fake,real}/``, then probe fine-tune.

Usage (from ``ml/``):

  uv run python -m scripts.train.community_forensics_vit_finetune_dfbench
  uv run python -m scripts.train.community_forensics_vit_finetune_dfbench --skip-download
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from look_again.community_forensics_finetune import FinetuneConfig, run_finetune
from look_again.hf_binary_dataset import materialize_hf_split
from look_again.paths import DATA_DIR, PROJECT_ROOT

HF_DATASET_ID = "DFBench/DFBench_Image25"
DEFAULT_DATA_ROOT = DATA_DIR / "finetune" / "dfbench_image25"
DEFAULT_RUN_NAME = "dfbench_image25"


def main() -> None:
    parser = argparse.ArgumentParser(description="ViT fine-tune on DFBench Image25")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Local fake/real folder root",
    )
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--streaming", action="store_true")
    parser.add_argument("--max-per-class", type=int, default=None)
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--mode", choices=("probe", "backbone", "all"), default="probe")
    parser.add_argument("--rebuild-cache", action="store_true")
    parser.add_argument("--no-mix-base", action="store_true")
    parser.add_argument(
        "--hf-split",
        default="train",
        help="HF split name (DFBench Image25 uses train)",
    )
    args = parser.parse_args()

    data_root = args.data_root if args.data_root.is_absolute() else (PROJECT_ROOT / args.data_root).resolve()
    if not args.skip_download:
        manifest = materialize_hf_split(
            dataset_id=HF_DATASET_ID,
            split=args.hf_split,
            output_root=data_root,
            filename_field="filename",
            max_per_class=args.max_per_class,
            streaming=args.streaming,
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
