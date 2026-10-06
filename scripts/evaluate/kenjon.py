"""Evaluate a trained checkpoint on the external kenjon/deep-fake-face-swap dataset."""

from __future__ import annotations

import argparse
import csv

import torch.nn as nn

from look_again.eval_benchmarks import KENJON_DATASET_ID, evaluate_kenjon_fake_only
from look_again.training import BATCH_SIZE, NEURAL_RESULTS_DIR, load_trained_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate best saved checkpoint on kenjon/deep-fake-face-swap.",
    )
    parser.add_argument(
        "--run-name",
        required=True,
        help="Training run name used for the best checkpoint file.",
    )
    parser.add_argument(
        "--model-name",
        default=None,
        help="Override architecture name stored in the checkpoint.",
    )
    parser.add_argument(
        "--split",
        default="test",
        choices=("train", "validation", "test"),
        help="HF split to evaluate (default: test).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Evaluation batch size (default: {BATCH_SIZE}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model, checkpoint = load_trained_model(
        args.run_name,
        model_name=args.model_name,
    )
    device = next(model.parameters()).device
    loss_fn = nn.BCEWithLogitsLoss()

    print(
        f"Kenjon evaluation | run={args.run_name} | split={args.split} | all labels=fake (0)",
        flush=True,
    )
    print(
        f"Loaded checkpoint from episode {checkpoint['best_epoch']} "
        f"(held-out test accuracy {checkpoint['best_test_accuracy']:.2%})",
        flush=True,
    )

    result = evaluate_kenjon_fake_only(
        model,
        device=device,
        loss_fn=loss_fn,
        split=args.split,
        batch_size=args.batch_size,
    )
    metrics = result.metrics

    NEURAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_path = NEURAL_RESULTS_DIR / f"{args.run_name}_kenjon_{args.split}_results.csv"
    with results_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "dataset",
                "split",
                "run_name",
                "model_name",
                "label_assumption",
                "accuracy",
                "fake_precision",
                "fake_recall",
                "fake_f1",
                "roc_auc",
                "loss",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "dataset": KENJON_DATASET_ID,
                "split": args.split,
                "run_name": args.run_name,
                "model_name": checkpoint["model_name"],
                "label_assumption": "all_fake",
                "accuracy": metrics.accuracy,
                "fake_precision": metrics.precision,
                "fake_recall": metrics.recall,
                "fake_f1": metrics.f1,
                "roc_auc": metrics.roc_auc,
                "loss": metrics.loss,
            }
        )
    print(f"Results saved to {results_path}")


if __name__ == "__main__":
    main()
