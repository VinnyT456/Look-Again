"""Audit face-swap pair controls and simple non-spatial label shortcuts."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from look_again.paths import RESULTS_DIR

from look_again.dataset import build_image_splits, hold_out_validation_split
from look_again.df40_subset import FACE_CROP_DATASET_PATH as PAIR_CONTROLLED_DATASET_PATH
from look_again.df40_subset import ensure_face_crop_dataset


def _rows_for_split(grouped_split):
    subset = grouped_split.dataset
    folder = subset.dataset
    rows = []
    for image_index, group_id in zip(subset.indices, grouped_split.group_ids):
        path, label = folder.samples[image_index]
        rows.append((Path(path), int(label), group_id))
    return rows


def _color_statistics(pixels: np.ndarray) -> list[float]:
    gray = pixels.mean(axis=1)
    return [
        *pixels.mean(axis=0).tolist(),
        *pixels.std(axis=0).tolist(),
        float(gray.mean()),
        float(gray.std()),
        *np.percentile(gray, (10, 50, 90)).tolist(),
    ]


def _image_audit_features(
    image_path: Path,
    face_box: tuple[int, int, int, int],
) -> tuple[list[float], list[float], list[float], str]:
    with Image.open(image_path) as image:
        image_format = image.format or "unknown"
        rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0

    metadata = [
        float(rgb.shape[1]),
        float(rgb.shape[0]),
        float(np.log1p(image_path.stat().st_size)),
        float(image_format == "JPEG"),
    ]
    global_pixels = _color_statistics(rgb.reshape(-1, 3))
    x1, y1, x2, y2 = face_box
    margin_x = max(1, round((x2 - x1) * 0.12))
    margin_y = max(1, round((y2 - y1) * 0.12))
    x1, y1 = max(0, x1 - margin_x), max(0, y1 - margin_y)
    x2, y2 = min(rgb.shape[1], x2 + margin_x), min(rgb.shape[0], y2 + margin_y)
    context_mask = np.ones(rgb.shape[:2], dtype=bool)
    context_mask[y1:y2, x1:x2] = False
    context_pixels = rgb[context_mask]
    context_statistics = (
        _color_statistics(context_pixels)
        if len(context_pixels)
        else [0.0] * len(global_pixels)
    )
    return metadata, global_pixels, context_statistics, image_format


def _baseline_report(name: str, train_rows, validation_rows, feature_index: int) -> dict:
    train_features = np.asarray([row[feature_index] for row in train_rows], dtype=np.float32)
    validation_features = np.asarray(
        [row[feature_index] for row in validation_rows], dtype=np.float32
    )
    train_labels = np.asarray([row[1] for row in train_rows], dtype=np.int64)
    validation_labels = np.asarray([row[1] for row in validation_rows], dtype=np.int64)

    classifier = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced"),
    )
    classifier.fit(train_features, train_labels)
    predictions = classifier.predict(validation_features)
    probabilities = classifier.predict_proba(validation_features)[:, 1]
    result = {
        "accuracy": float(accuracy_score(validation_labels, predictions)),
        "roc_auc": float(roc_auc_score(validation_labels, probabilities)),
        "train_examples": len(train_rows),
        "validation_examples": len(validation_rows),
    }
    print(
        f"{name}: accuracy={result['accuracy']:.2%}, "
        f"ROC-AUC={result['roc_auc']:.4f} "
        f"(group-held-out validation; test split untouched)",
        flush=True,
    )
    return result


def _pair_context_differences(
    metadata_rows: list[dict[str, str]], dataset_path: Path
) -> dict[str, float]:
    outside_errors: list[float] = []
    inside_errors: list[float] = []
    for row in metadata_rows:
        fake_path = dataset_path / row["fake_file"]
        real_path = dataset_path / row["real_file"]
        with Image.open(fake_path) as fake_image, Image.open(real_path) as real_image:
            fake = np.asarray(fake_image.convert("RGB"), dtype=np.int16)
            real = np.asarray(real_image.convert("RGB"), dtype=np.int16)
            if fake.shape != real.shape:
                raise ValueError(f"Mismatched saved pair dimensions for pair {row['id']}")

        face_box = tuple(int(value) for value in row["face_bbox_in_crop"].split(","))
        x1, y1, x2, y2 = face_box
        height, width = fake.shape[:2]
        margin_x = max(1, round((x2 - x1) * 0.12))
        margin_y = max(1, round((y2 - y1) * 0.12))
        x1, y1 = max(0, x1 - margin_x), max(0, y1 - margin_y)
        x2, y2 = min(width, x2 + margin_x), min(height, y2 + margin_y)
        face_mask = np.zeros((height, width), dtype=bool)
        face_mask[y1:y2, x1:x2] = True
        difference = np.abs(fake.astype(np.float32) - real.astype(np.float32)).mean(axis=2)
        if face_mask.any() and (~face_mask).any():
            inside_errors.append(float(difference[face_mask].mean()))
            outside_errors.append(float(difference[~face_mask].mean()))

    if not outside_errors:
        return {"outside_face_mae": float("nan"), "inside_face_mae": float("nan")}
    return {
        "outside_face_mae": float(np.mean(outside_errors)),
        "inside_face_mae": float(np.mean(inside_errors)),
    }


def main() -> None:
    ensure_face_crop_dataset()
    dataset_path = PAIR_CONTROLLED_DATASET_PATH
    metadata_path = dataset_path / "metadata.csv"
    with metadata_path.open(newline="", encoding="utf-8") as metadata_file:
        metadata_rows = list(csv.DictReader(metadata_file))
    if not metadata_rows:
        raise RuntimeError(f"No face-swap pairs found in {metadata_path}")

    invalid_pairs = [row["id"] for row in metadata_rows if row.get("same_source_crop") != "1"]
    if invalid_pairs:
        raise RuntimeError(
            f"{len(invalid_pairs)} pairs do not have shared crop windows; "
            f"examples: {invalid_pairs[:5]}"
        )

    method_counts = Counter(row.get("method") or "unknown" for row in metadata_rows)
    video_count = len(
        {row.get("source_video_id") or row["target_face"] for row in metadata_rows}
    )
    print(
        f"Pair controls: {len(metadata_rows)} matched pairs, "
        f"{video_count} source videos, methods={dict(method_counts)}",
        flush=True,
    )

    face_boxes_by_path = {}
    for row in metadata_rows:
        face_box = tuple(int(value) for value in row["face_bbox_in_crop"].split(","))
        face_boxes_by_path[dataset_path / row["fake_file"]] = face_box
        face_boxes_by_path[dataset_path / row["real_file"]] = face_box

    for row in metadata_rows:
        fake_path = dataset_path / row["fake_file"]
        real_path = dataset_path / row["real_file"]
        fake_meta, _, _, fake_format = _image_audit_features(
            fake_path, face_boxes_by_path[fake_path]
        )
        real_meta, _, _, real_format = _image_audit_features(
            real_path, face_boxes_by_path[real_path]
        )
        if fake_meta[:2] != real_meta[:2] or fake_format != real_format:
            raise ValueError(f"Pair {row['id']} differs in saved dimensions or format")

    original_train, _held_out_test = build_image_splits(dataset_path=dataset_path)
    train_split, validation_split = hold_out_validation_split(original_train)
    train_samples = _rows_for_split(train_split)
    validation_samples = _rows_for_split(validation_split)

    def enrich(rows):
        result = []
        for path, label, group_id in rows:
            metadata, global_pixels, context_statistics, _ = _image_audit_features(
                path, face_boxes_by_path[path]
            )
            result.append((metadata, label, group_id, global_pixels, context_statistics))
        return result

    train_rows = enrich(train_samples)
    validation_rows = enrich(validation_samples)
    metadata_baseline = _baseline_report(
        "File metadata baseline", train_rows, validation_rows, 0
    )
    global_baseline = _baseline_report(
        "Global color/statistics baseline", train_rows, validation_rows, 3
    )
    context_baseline = _baseline_report(
        "Outside-face context baseline", train_rows, validation_rows, 4
    )

    pair_context = _pair_context_differences(metadata_rows, dataset_path)
    print(
        "Matched-pair mean absolute pixel error: "
        f"inside face={pair_context['inside_face_mae']:.2f}/255, "
        f"outside face={pair_context['outside_face_mae']:.2f}/255",
        flush=True,
    )

    report = {
        "pairs": len(metadata_rows),
        "source_videos": video_count,
        "methods": dict(method_counts),
        "file_metadata_baseline": metadata_baseline,
        "global_color_statistics_baseline": global_baseline,
        "outside_face_context_baseline": context_baseline,
        "paired_frame_difference": pair_context,
        "test_split_used_for_audit": False,
    }
    report_dir = RESULTS_DIR / "audits"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "face_swap_dataset_audit.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Shortcut audit report saved to {report_path}", flush=True)


if __name__ == "__main__":
    main()
