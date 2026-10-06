"""Run Celeb-DF, Kenjon, and DF40 robustness evals on a saved checkpoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from look_again.dataset import SEED
from look_again.eval_benchmarks import DEFAULT_CELEB_DF_ROOT, run_full_eval_suite
from look_again.training import BATCH_SIZE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate a saved checkpoint on Celeb-DF (balanced), "
            "Kenjon (fake-only), and the DF40 robustness suite."
        ),
    )
    parser.add_argument(
        "--run-name",
        required=True,
        help=(
            "Training run name for checkpoints/{run_name}_best.pt "
            "(e.g. efficientnet_b0, inception_resnet_v1_140k)."
        ),
    )
    parser.add_argument(
        "--model-name",
        default=None,
        help="Override architecture name stored in the checkpoint.",
    )
    parser.add_argument(
        "--celeb-root",
        type=Path,
        default=None,
        help=(
            "Local Celeb-DF root with Celeb-synthesis/Celeb-real (or fake/real). "
            f"Defaults to {DEFAULT_CELEB_DF_ROOT} when present, otherwise HF mirror."
        ),
    )
    parser.add_argument(
        "--celeb-split",
        default="test",
        choices=("train", "validation", "test"),
        help="HF split for Celeb-DF when --celeb-root is not set (default: test).",
    )
    parser.add_argument(
        "--kenjon-split",
        default="test",
        choices=("train", "validation", "test"),
        help="Kenjon HF split (default: test).",
    )
    parser.add_argument(
        "--max-per-class",
        type=int,
        default=None,
        help="Optional cap when balancing Celeb-DF fake/real counts.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SEED,
        help=f"Random seed for balanced Celeb-DF subsampling (default: {SEED}).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Evaluation batch size (default: {BATCH_SIZE}).",
    )
    parser.add_argument("--skip-celebdf", action="store_true")
    parser.add_argument("--skip-kenjon", action="store_true")
    parser.add_argument("--skip-robustness", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_full_eval_suite(
        args.run_name,
        model_name=args.model_name,
        celeb_root=args.celeb_root,
        celeb_split=args.celeb_split,
        kenjon_split=args.kenjon_split,
        seed=args.seed,
        max_per_class=args.max_per_class,
        batch_size=args.batch_size,
        skip_celebdf=args.skip_celebdf,
        skip_kenjon=args.skip_kenjon,
        skip_robustness=args.skip_robustness,
    )


if __name__ == "__main__":
    main()
