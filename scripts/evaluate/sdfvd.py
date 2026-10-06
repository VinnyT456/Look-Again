"""Evaluate a saved frame-classifier checkpoint on SDFVD frame by frame."""

from __future__ import annotations

import argparse
import csv

import torch.nn as nn

from look_again.eval_benchmarks import (
    SDFVD_DATASET_ID,
    SDFVD_MAX_CONSECUTIVE_FAKE_FRAMES,
    SDFVD_MIN_CONSECUTIVE_FAKE_FRAMES,
    evaluate_sdfvd_sequential_video_rule,
    sweep_sdfvd_consecutive_thresholds,
    sweep_sdfvd_real_logit_thresholds,
)
from look_again.training import BATCH_SIZE, NEURAL_RESULTS_DIR, load_trained_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Score every SDFVD frame and mark a video fake after a configured "
            "consecutive fake-frame run."
        ),
    )
    parser.add_argument(
        "--run-name",
        required=True,
        help="Training run name used to locate the best checkpoint.",
    )
    parser.add_argument(
        "--model-name",
        default=None,
        help="Override the architecture name stored in the checkpoint.",
    )
    parser.add_argument(
        "--consecutive-fake-frames",
        type=int,
        default=5,
        help=(
            f"Consecutive fake frame predictions required to mark a video fake "
            f"({SDFVD_MIN_CONSECUTIVE_FAKE_FRAMES}-"
            f"{SDFVD_MAX_CONSECUTIVE_FAKE_FRAMES}, default: 5). "
            "Lower = more sensitive (better fake recall, more real false alarms)."
        ),
    )
    parser.add_argument(
        "--real-logit-threshold",
        type=float,
        default=0.0,
        help=(
            "Classify a frame as fake when logit_real is below this value "
            "(default: 0). Video logits are often shifted positive; try ~9–11 "
            "for inception_resnet_v1_140k after --sweep-real-logit-threshold."
        ),
    )
    parser.add_argument(
        "--sweep-real-logit-threshold",
        action="store_true",
        help=(
            "After one inference pass, sweep frame logit thresholds using saved "
            "logits (uses --consecutive-fake-frames for video aggregation)."
        ),
    )
    parser.add_argument(
        "--sweep-consecutive-fake-frames",
        action="store_true",
        help=(
            "After one inference pass, print video-level fake recall/F1 for every "
            "threshold in range (no extra model runs)."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Frame inference batch size (default: {BATCH_SIZE}).",
    )
    return parser.parse_args()


def _print_real_logit_sweep(
    frame_predictions,
    video_stats,
    *,
    consecutive_fake_frames: int,
) -> None:
    print(
        f"\nSDFVD real-logit threshold sweep "
        f"(frame fake if logit_real < T; video fake if >= {consecutive_fake_frames} "
        f"consecutive fake frames)",
        flush=True,
    )
    print(
        f"{'T':>8} {'Frame F1':>10} {'Vid acc':>10} {'Fake prec':>10} "
        f"{'Fake rec':>10} {'Vid F1':>10}",
        flush=True,
    )
    for threshold, video_metrics, frame_metrics in sweep_sdfvd_real_logit_thresholds(
        frame_predictions,
        video_stats,
        consecutive_fake_frames=consecutive_fake_frames,
    ):
        print(
            f"{threshold:>8.2f} "
            f"{frame_metrics.f1:>10.2%} "
            f"{video_metrics.accuracy:>10.2%} "
            f"{video_metrics.precision:>10.2%} "
            f"{video_metrics.recall:>10.2%} "
            f"{video_metrics.f1:>10.2%}",
            flush=True,
        )


def _print_threshold_sweep(
    frame_predictions,
    video_stats,
    *,
    real_logit_threshold: float,
) -> None:
    print(
        f"\nSDFVD consecutive-fake threshold sweep "
        f"({SDFVD_MIN_CONSECUTIVE_FAKE_FRAMES}-"
        f"{SDFVD_MAX_CONSECUTIVE_FAKE_FRAMES})",
        flush=True,
    )
    print(
        f"{'K':>3} {'Video acc':>10} {'Fake prec':>10} {'Fake rec':>10} {'Fake F1':>10}",
        flush=True,
    )
    for threshold, metrics in sweep_sdfvd_consecutive_thresholds(
        frame_predictions,
        video_stats,
        real_logit_threshold=real_logit_threshold,
    ):
        print(
            f"{threshold:>3} "
            f"{metrics.accuracy:>10.2%} "
            f"{metrics.precision:>10.2%} "
            f"{metrics.recall:>10.2%} "
            f"{metrics.f1:>10.2%}",
            flush=True,
        )


def main() -> None:
    args = parse_args()
    if not SDFVD_MIN_CONSECUTIVE_FAKE_FRAMES <= args.consecutive_fake_frames <= SDFVD_MAX_CONSECUTIVE_FAKE_FRAMES:
        raise SystemExit(
            f"--consecutive-fake-frames must be between "
            f"{SDFVD_MIN_CONSECUTIVE_FAKE_FRAMES} and "
            f"{SDFVD_MAX_CONSECUTIVE_FAKE_FRAMES}"
        )

    model, checkpoint = load_trained_model(
        args.run_name,
        model_name=args.model_name,
    )
    device = next(model.parameters()).device
    loss_fn = nn.BCEWithLogitsLoss()

    print(
        f"SDFVD evaluation | run={args.run_name} | dataset={SDFVD_DATASET_ID} | "
        f"all frames | fake if logit_real < {args.real_logit_threshold} | "
        f"video fake after {args.consecutive_fake_frames} consecutive frames",
        flush=True,
    )
    selection_accuracy = checkpoint.get(
        "best_test_accuracy",
        checkpoint.get("best_validation_accuracy", 0.0),
    )
    print(
        f"Loaded checkpoint episode {checkpoint['best_epoch']} "
        f"(selection accuracy {selection_accuracy:.2%})",
        flush=True,
    )

    result = evaluate_sdfvd_sequential_video_rule(
        model,
        device=device,
        loss_fn=loss_fn,
        consecutive_fake_frames=args.consecutive_fake_frames,
        frame_batch_size=args.batch_size,
        real_logit_threshold=args.real_logit_threshold,
    )
    if args.sweep_real_logit_threshold:
        _print_real_logit_sweep(
            result.frame_predictions,
            result.video_stats,
            consecutive_fake_frames=args.consecutive_fake_frames,
        )
    if args.sweep_consecutive_fake_frames:
        _print_threshold_sweep(
            result.frame_predictions,
            result.video_stats,
            real_logit_threshold=args.real_logit_threshold,
        )

    frame_metrics = result.frame_metrics
    video_metrics = result.video_metrics
    details = result.details
    NEURAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_path = NEURAL_RESULTS_DIR / f"{args.run_name}_sdfvd_results.csv"
    with results_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "dataset",
                "split",
                "run_name",
                "model_name",
                "consecutive_fake_frames",
                "real_logit_threshold",
                "total_videos",
                "total_frames",
                "video_frames_seen",
                "frames_without_detected_face",
                "face_detection_rate",
                "fake_count",
                "real_count",
                "frame_accuracy",
                "frame_fake_precision",
                "frame_fake_recall",
                "frame_fake_f1",
                "frame_roc_auc",
                "frame_loss",
                "video_accuracy",
                "video_fake_precision",
                "video_fake_recall",
                "video_fake_f1",
                "video_roc_auc",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "dataset": details["dataset"],
                "split": details["split"],
                "run_name": args.run_name,
                "model_name": checkpoint["model_name"],
                "consecutive_fake_frames": details["consecutive_fake_frames"],
                "real_logit_threshold": details["real_logit_threshold"],
                "total_videos": details["total_videos"],
                "total_frames": details["total_frames"],
                "video_frames_seen": details["video_frames_seen"],
                "frames_without_detected_face": details[
                    "frames_without_detected_face"
                ],
                "face_detection_rate": details["face_detection_rate"],
                "fake_count": details["fake_count"],
                "real_count": details["real_count"],
                "frame_accuracy": frame_metrics.accuracy,
                "frame_fake_precision": frame_metrics.precision,
                "frame_fake_recall": frame_metrics.recall,
                "frame_fake_f1": frame_metrics.f1,
                "frame_roc_auc": frame_metrics.roc_auc,
                "frame_loss": frame_metrics.loss,
                "video_accuracy": video_metrics.accuracy,
                "video_fake_precision": video_metrics.precision,
                "video_fake_recall": video_metrics.recall,
                "video_fake_f1": video_metrics.f1,
                "video_roc_auc": video_metrics.roc_auc,
            }
        )
    print(f"SDFVD results saved to {results_path}", flush=True)

    frame_predictions_path = NEURAL_RESULTS_DIR / f"{args.run_name}_sdfvd_frame_predictions.csv"
    with frame_predictions_path.open("w", newline="", encoding="utf-8") as csv_file:
        fieldnames = list(result.frame_predictions[0])
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result.frame_predictions)
    print(f"SDFVD frame predictions saved to {frame_predictions_path}", flush=True)

    video_predictions_path = NEURAL_RESULTS_DIR / f"{args.run_name}_sdfvd_video_predictions.csv"
    with video_predictions_path.open("w", newline="", encoding="utf-8") as csv_file:
        fieldnames = list(result.video_predictions[0])
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result.video_predictions)
    print(f"SDFVD video predictions saved to {video_predictions_path}", flush=True)


if __name__ == "__main__":
    main()
