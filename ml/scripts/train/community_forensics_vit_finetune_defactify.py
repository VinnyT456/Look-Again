"""Fine-tune on Rajarshi-Roy-research/Defactify_Image_Dataset (COCO-aligned real vs AI).

Usage (from ``ml/``):

  uv run python -m scripts.train.community_forensics_vit_finetune_defactify
  uv run python -m scripts.train.community_forensics_vit_finetune_defactify --skip-download
  uv run python -m scripts.train.community_forensics_vit_finetune_defactify --hf-splits train validation
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from look_again.community_forensics_finetune import FinetuneConfig, run_finetune
from look_again.hf_binary_dataset import materialize_hf_split
from look_again.paths import DATA_DIR, PROJECT_ROOT

HF_DATASET_ID = "Rajarshi-Roy-research/Defactify_Image_Dataset"
DEFAULT_DATA_ROOT = DATA_DIR / "finetune" / "defactify" / "train"
DEFAULT_RUN_NAME = "defactify"
DEFACTIFY_FAKE = frozenset({1, "1"})
DEFACTIFY_REAL = frozenset({0, "0"})


def main() -> None:
    parser = argparse.ArgumentParser(description="ViT fine-tune on Defactify")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--streaming", action="store_true")
    parser.add_argument("--max-per-class", type=int, default=None, help="Per split, per class")
    parser.add_argument(
        "--hf-splits",
        nargs="+",
        default=["train"],
        metavar="SPLIT",
        help="HF splits to materialize (train, validation, test)",
    )
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--mode", choices=("probe", "backbone", "all"), default="probe")
    parser.add_argument("--rebuild-cache", action="store_true")
    parser.add_argument("--no-mix-base", action="store_true")
    args = parser.parse_args()

    data_root = args.data_root if args.data_root.is_absolute() else (PROJECT_ROOT / args.data_root).resolve()
    if not args.skip_download:
        manifests = []
        for split in args.hf_splits:
            manifests.append(
                materialize_hf_split(
                    dataset_id=HF_DATASET_ID,
                    split=split,
                    output_root=data_root,
                    label_field="Label_A",
                    image_field="Image",
                    fake_labels=DEFACTIFY_FAKE,
                    real_labels=DEFACTIFY_REAL,
                    max_per_class=args.max_per_class,
                    streaming=args.streaming,
                    filename_prefix=f"defactify_{split}_",
                )
            )
        print(json.dumps(manifests, indent=2), file=sys.stderr)

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
