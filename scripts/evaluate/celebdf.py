"""Evaluate a trained checkpoint on balanced Celeb-DF fake vs real."""

from __future__ import annotations

import argparse
from pathlib import Path

import torch.nn as nn

from look_again.dataset import SEED
from look_again.eval_benchmarks import DEFAULT_CELEB_DF_ROOT, default_celebdf_root, evaluate_celebdf_balanced
from look_again.training import BATCH_SIZE, load_trained_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate best saved checkpoint on balanced Celeb-DF.",
    )
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--model-name", default=None)
    parser.add_argument(
        "--celeb-root",
        type=str,
        default=None,
        help=f"Optional local Celeb-DF root (default: {DEFAULT_CELEB_DF_ROOT} if present).",
    )
    parser.add_argument(
        "--split",
        default="test",
        choices=("train", "validation", "test"),
        help="HF split when --celeb-root is not set (default: test).",
    )
    parser.add_argument("--max-per-class", type=int, default=None)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model, checkpoint = load_trained_model(args.run_name, model_name=args.model_name)
    device = next(model.parameters()).device
    loss_fn = nn.BCEWithLogitsLoss()
    print(
        f"Loaded checkpoint episode {checkpoint['best_epoch']} "
        f"(held-out DF40 test accuracy {checkpoint['best_test_accuracy']:.2%})",
        flush=True,
    )
    celeb_root = Path(args.celeb_root) if args.celeb_root else default_celebdf_root()
    evaluate_celebdf_balanced(
        model,
        device=device,
        loss_fn=loss_fn,
        celeb_root=celeb_root,
        split=args.split,
        seed=args.seed,
        max_per_class=args.max_per_class,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
