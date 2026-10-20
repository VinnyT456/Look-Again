"""Fine-tune on both julienlucas gen-AI datasets (MJ / DALL·E / SD + Nano Banana Pro).

Materializes **train** into one folder (~15k images) for probe training. Optionally
materializes HF **test** splits into ``eval/`` for holdout checks (not used in training).

Usage (from ``ml/``):

  uv run python -m scripts.train.community_forensics_vit_finetune_julienlucas_genai_combined
  uv run python -m scripts.train.community_forensics_vit_finetune_julienlucas_genai_combined --skip-download
  uv run python -m scripts.train.community_forensics_vit_finetune_julienlucas_genai_combined --materialize-test
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from look_again.community_forensics_finetune import FinetuneConfig, run_finetune
from look_again.hf_binary_dataset import materialize_hf_split
from look_again.paths import DATA_DIR, PROJECT_ROOT

GENAI_TRAIN_SOURCES: tuple[tuple[str, str], ...] = (
    ("mjdsd_", "julienlucas/midjourney-dalle-sd-dataset"),
    ("nanobanana_", "julienlucas/midjourney-dalle-sd-nanobananapro-dataset"),
)

DEFAULT_DATA_ROOT = DATA_DIR / "finetune" / "julienlucas_genai_combined" / "train"
DEFAULT_EVAL_ROOT = DATA_DIR / "finetune" / "julienlucas_genai_combined" / "eval"
DEFAULT_RUN_NAME = "julienlucas_genai_combined"


def materialize_sources(
    *,
    output_root: Path,
    split: str,
    streaming: bool,
    max_per_class: int | None,
) -> list[dict]:
    manifests: list[dict] = []
    for prefix, dataset_id in GENAI_TRAIN_SOURCES:
        manifests.append(
            materialize_hf_split(
                dataset_id=dataset_id,
                split=split,
                output_root=output_root,
                max_per_class=max_per_class,
                streaming=streaming,
                filename_prefix=prefix,
            )
        )
    return manifests


def main() -> None:
    parser = argparse.ArgumentParser(description="ViT fine-tune on combined julienlucas gen-AI HF datasets")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--eval-root", type=Path, default=DEFAULT_EVAL_ROOT)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--materialize-test", action="store_true", help="Also export HF test splits to eval/")
    parser.add_argument("--streaming", action="store_true")
    parser.add_argument("--max-per-class", type=int, default=None, help="Per dataset, per class")
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--mode", choices=("probe", "backbone", "all"), default="probe")
    parser.add_argument("--rebuild-cache", action="store_true")
    parser.add_argument("--no-mix-base", action="store_true")
    args = parser.parse_args()

    data_root = args.data_root if args.data_root.is_absolute() else (PROJECT_ROOT / args.data_root).resolve()
    eval_root = args.eval_root if args.eval_root.is_absolute() else (PROJECT_ROOT / args.eval_root).resolve()

    if not args.skip_download:
        train_manifests = materialize_sources(
            output_root=data_root,
            split="train",
            streaming=args.streaming,
            max_per_class=args.max_per_class,
        )
        print(json.dumps({"train": train_manifests}, indent=2), file=sys.stderr)
        if args.materialize_test:
            eval_manifests = materialize_sources(
                output_root=eval_root,
                split="test",
                streaming=args.streaming,
                max_per_class=args.max_per_class,
            )
            print(json.dumps({"eval": eval_manifests}, indent=2), file=sys.stderr)

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
