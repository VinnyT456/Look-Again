"""CIFAKE + Defactify fine-tune with extra **real** exposure (social / photo reals).

Default caps: 2000 fake / 5000 real per source split (Defactify train + validation).
Good follow-up after gen-AI-heavy julienlucas runs.

Usage (from ``ml/``):

  uv run python -m scripts.train.community_forensics_vit_finetune_cifake_defactify_balance
  uv run python -m scripts.train.community_forensics_vit_finetune_cifake_defactify_balance --skip-download
  uv run python -m scripts.train.community_forensics_vit_finetune_cifake_defactify_balance --real-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from look_again.community_forensics_finetune import FinetuneConfig, run_finetune
from look_again.hf_binary_dataset import materialize_hf_split
from look_again.paths import DATA_DIR, PROJECT_ROOT

from look_again.hf_binary_dataset import CIFAKE_HF_ID

CIFAKE_ID = CIFAKE_HF_ID
DEFACTIFY_ID = "Rajarshi-Roy-research/Defactify_Image_Dataset"
DEFACTIFY_FAKE = frozenset({1, "1"})
DEFACTIFY_REAL = frozenset({0, "0"})

DEFAULT_DATA_ROOT = DATA_DIR / "finetune" / "cifake_defactify_balance" / "train"
DEFAULT_RUN_NAME = "cifake_defactify_balance"


def materialize_balance(
    output_root: Path,
    *,
    max_fake: int | None,
    max_real: int | None,
    streaming: bool,
    export_fake: bool,
    export_real: bool,
) -> list[dict]:
    manifests: list[dict] = []
    common = {
        "output_root": output_root,
        "max_fake_per_class": max_fake,
        "max_real_per_class": max_real,
        "streaming": streaming,
        "export_fake": export_fake,
        "export_real": export_real,
    }
    manifests.append(
        materialize_hf_split(
            dataset_id=CIFAKE_ID,
            split="train",
            filename_prefix="cifake_train_",
            **common,
        )
    )
    for split in ("train", "validation"):
        manifests.append(
            materialize_hf_split(
                dataset_id=DEFACTIFY_ID,
                split=split,
                label_field="Label_A",
                image_field="Image",
                fake_labels=DEFACTIFY_FAKE,
                real_labels=DEFACTIFY_REAL,
                filename_prefix=f"defactify_{split}_",
                **common,
            )
        )
    return manifests


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ViT fine-tune on CIFAKE + Defactify with real-heavy caps",
    )
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--streaming", action="store_true")
    parser.add_argument("--max-fake-per-source", type=int, default=2000)
    parser.add_argument("--max-real-per-source", type=int, default=5000)
    parser.add_argument(
        "--real-only",
        action="store_true",
        help="Only export real/ folders (adds real negatives without more fakes)",
    )
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--mode", choices=("probe", "backbone", "all"), default="probe")
    parser.add_argument("--rebuild-cache", action="store_true")
    parser.add_argument("--no-mix-base", action="store_true")
    args = parser.parse_args()

    data_root = args.data_root if args.data_root.is_absolute() else (PROJECT_ROOT / args.data_root).resolve()
    if not args.skip_download:
        manifests = materialize_balance(
            data_root,
            max_fake=args.max_fake_per_source if not args.real_only else 0,
            max_real=args.max_real_per_source,
            streaming=args.streaming,
            export_fake=not args.real_only,
            export_real=True,
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
