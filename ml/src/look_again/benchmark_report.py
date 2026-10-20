"""Build standardized benchmark tables and markdown reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from look_again.audio_ml.data import load_parquet_feature_splits
from look_again.paths import (
    CHECKPOINT_DIR,
    DEFAULT_AUDIO_FEATURES_PARQUET,
    MIX_AUDIO_DIR,
    RESULTS_DIR,
    SPEECH_DEEPFAKE_CHECKPOINT_DIR,
)

STANDARD_AUDIO_SEED = 42
STANDARD_TRAIN_RATIO = 0.8
STANDARD_VAL_RATIO = 0.1
STANDARD_TEST_RATIO = 0.1

CLASSICAL_AUDIO_CHECKPOINTS: tuple[tuple[str, Path], ...] = (
    ("Random Forest", CHECKPOINT_DIR / "audio_random_forest_best.joblib"),
    ("SVM", CHECKPOINT_DIR / "audio_svm_best.joblib"),
    ("XGBoost", CHECKPOINT_DIR / "audio_xgboost_best.joblib"),
)

SPEECH_CHECKPOINTS: tuple[tuple[str, str, Path], ...] = (
    ("Wav2Vec2", "facebook/wav2vec2-base-960h", SPEECH_DEEPFAKE_CHECKPOINT_DIR / "wav2vec2" / "best_head.pt"),
    ("WavLM", "microsoft/wavlm-base-plus", SPEECH_DEEPFAKE_CHECKPOINT_DIR / "wavlm" / "best_head.pt"),
)


@dataclass(frozen=True)
class BenchmarkRow:
    family: str
    model: str
    dataset: str
    status: str
    n_samples: int
    accuracy: float | None
    precision: float | None
    recall: float | None
    f1: float | None
    roc_auc: float | None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "model": self.model,
            "dataset": self.dataset,
            "status": self.status,
            "n_samples": self.n_samples,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "roc_auc": self.roc_auc,
            "notes": self.notes,
        }


def _metrics_from_arrays(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    *,
    pos_label: int,
) -> dict[str, float | None]:
    metrics: dict[str, float | None] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, pos_label=pos_label, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, pos_label=pos_label, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, pos_label=pos_label, zero_division=0)),
    }
    if len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
    else:
        metrics["roc_auc"] = None
    return metrics


def _row_from_metrics(
    *,
    family: str,
    model: str,
    dataset: str,
    status: str,
    n_samples: int,
    metrics: dict[str, float | None],
    notes: str = "",
) -> BenchmarkRow:
    return BenchmarkRow(
        family=family,
        model=model,
        dataset=dataset,
        status=status,
        n_samples=n_samples,
        accuracy=metrics.get("accuracy"),
        precision=metrics.get("precision"),
        recall=metrics.get("recall"),
        f1=metrics.get("f1"),
        roc_auc=metrics.get("roc_auc"),
        notes=notes,
    )


def evaluate_classical_audio_models(
    *,
    features_parquet: Path = DEFAULT_AUDIO_FEATURES_PARQUET,
    seed: int = STANDARD_AUDIO_SEED,
) -> tuple[list[BenchmarkRow], dict[str, Any]]:
    dataset_name = "Mix test split (tabular features, seed=42, 10%)"
    context: dict[str, Any] = {"split_summary": None}
    if not features_parquet.is_file():
        note = f"Missing feature table: {features_parquet}"
        return [
            BenchmarkRow(
                family="Classical audio",
                model=name,
                dataset=dataset_name,
                status="skipped",
                n_samples=0,
                accuracy=None,
                precision=None,
                recall=None,
                f1=None,
                roc_auc=None,
                notes=note,
            )
            for name, _path in CLASSICAL_AUDIO_CHECKPOINTS
        ], context

    _train, _val, test = load_parquet_feature_splits(
        features_parquet,
        test_size=STANDARD_TEST_RATIO,
        validation_size=STANDARD_VAL_RATIO,
        seed=seed,
        max_samples=None,
        include_test=True,
    )
    context["split_summary"] = {
        "test": {
            "fake": int(np.sum(test.y == 0)),
            "real": int(np.sum(test.y == 1)),
        }
    }

    rows: list[BenchmarkRow] = []
    feature_names = list(test.feature_names)
    X_test = test.X
    y_true = test.y
    for display_name, checkpoint_path in CLASSICAL_AUDIO_CHECKPOINTS:
        if not checkpoint_path.is_file():
            rows.append(
                BenchmarkRow(
                    family="Classical audio",
                    model=display_name,
                    dataset=dataset_name,
                    status="missing_checkpoint",
                    n_samples=len(y_true),
                    accuracy=None,
                    precision=None,
                    recall=None,
                    f1=None,
                    roc_auc=None,
                    notes=str(checkpoint_path),
                )
            )
            continue
        bundle = joblib.load(checkpoint_path)
        model = bundle["model"]
        bundle_features = list(bundle.get("feature_names") or feature_names)
        if bundle_features != feature_names:
            rows.append(
                BenchmarkRow(
                    family="Classical audio",
                    model=display_name,
                    dataset=dataset_name,
                    status="feature_mismatch",
                    n_samples=len(y_true),
                    accuracy=None,
                    precision=None,
                    recall=None,
                    f1=None,
                    roc_auc=None,
                    notes="Checkpoint feature names differ from benchmark parquet",
                )
            )
            continue
        y_pred = np.asarray(model.predict(X_test), dtype=np.int64)
        if hasattr(model, "predict_proba"):
            proba = np.asarray(model.predict_proba(X_test))
            classes = [int(value) for value in model.classes_]
            fake_index = classes.index(0) if 0 in classes else 0
            y_prob = proba[:, fake_index]
        else:
            y_prob = y_pred.astype(np.float64)
        metrics = _metrics_from_arrays(y_true, y_pred, y_prob, pos_label=0)
        rows.append(
            _row_from_metrics(
                family="Classical audio",
                model=display_name,
                dataset=dataset_name,
                status="ok",
                n_samples=len(y_true),
                metrics=metrics,
            )
        )
    return rows, context


def evaluate_speech_deepfake_models(
    *,
    mix_root: Path = MIX_AUDIO_DIR,
    seed: int = STANDARD_AUDIO_SEED,
    batch_size: int = 8,
    max_audio_seconds: float = 5.0,
) -> tuple[list[BenchmarkRow], dict[str, Any]]:
    from functools import partial

    from torch.utils.data import DataLoader

    from look_again.speech_deepfake.checkpointing import load_model_from_checkpoint
    from look_again.speech_deepfake.dataset import SpeechWaveformDataset, collate_waveforms
    from look_again.speech_deepfake.metadata import build_speech_records
    from look_again.speech_deepfake.metrics import collect_predictions, compute_metrics, resolve_device
    from look_again.speech_deepfake.splits import format_split_summary, split_records

    dataset_name = "Mix test split (raw waveforms, seed=42, 10%)"
    records = build_speech_records(mix_root, max_samples=None, random_seed=seed)
    split = split_records(
        records,
        train_ratio=STANDARD_TRAIN_RATIO,
        val_ratio=STANDARD_VAL_RATIO,
        test_ratio=STANDARD_TEST_RATIO,
        random_seed=seed,
    )
    context = {"split_summary": format_split_summary(split)}
    device, _ = resolve_device(False)
    rows: list[BenchmarkRow] = []
    for display_name, _model_name, checkpoint_path in SPEECH_CHECKPOINTS:
        if not checkpoint_path.is_file():
            rows.append(
                BenchmarkRow(
                    family="Speech (frozen encoder)",
                    model=display_name,
                    dataset=dataset_name,
                    status="missing_checkpoint",
                    n_samples=len(split.test),
                    accuracy=None,
                    precision=None,
                    recall=None,
                    f1=None,
                    roc_auc=None,
                    notes=str(checkpoint_path),
                )
            )
            continue
        model = load_model_from_checkpoint(checkpoint_path, map_location=device)
        model.to(device)
        collate = partial(collate_waveforms, processor=model.feature_extractor)
        loader = DataLoader(
            SpeechWaveformDataset(
                split.test,
                max_audio_seconds=max_audio_seconds,
            ),
            batch_size=batch_size,
            shuffle=False,
            num_workers=0,
            collate_fn=collate,
        )
        y_true, y_pred, y_prob = collect_predictions(model, loader, device)
        metrics = compute_metrics(y_true, y_pred, y_prob, split_name="test")
        rows.append(
            _row_from_metrics(
                family="Speech (frozen encoder)",
                model=display_name,
                dataset=dataset_name,
                status="ok",
                n_samples=len(y_true),
                metrics=metrics,
                notes=f"pos_label=fake(1); checkpoint={checkpoint_path.name}",
            )
        )
    return rows, context


def evaluate_image_checkpoints(
    *,
    checkpoint_dir: Path = CHECKPOINT_DIR,
) -> list[BenchmarkRow]:
    from look_again.eval_benchmarks import run_full_eval_suite

    rows: list[BenchmarkRow] = []
    for checkpoint_path in sorted(checkpoint_dir.glob("*_best.pt")):
        run_name = checkpoint_path.name.removesuffix("_best.pt")
        summary_csv = run_full_eval_suite(run_name)
        import csv

        with summary_csv.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for record in reader:
                rows.append(
                    BenchmarkRow(
                        family="Image neural",
                        model=str(record.get("model_name") or run_name),
                        dataset=str(record.get("benchmark") or "unknown"),
                        status="ok",
                        n_samples=0,
                        accuracy=_float_or_none(record.get("accuracy")),
                        precision=_float_or_none(record.get("precision")),
                        recall=_float_or_none(record.get("recall")),
                        f1=_float_or_none(record.get("f1")),
                        roc_auc=_float_or_none(record.get("roc_auc")),
                        notes=f"run_name={run_name}",
                    )
                )
    return rows


def _float_or_none(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _format_metric(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}"


def render_markdown_report(
    rows: list[BenchmarkRow],
    *,
    context: dict[str, Any],
    output_path: Path,
) -> None:
    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Model benchmark report",
        "",
        f"Generated: {timestamp}",
        "",
        "## Standard evaluation sets",
        "",
        "- **Audio (classical + speech):** held-out **Mix** test split — 80/10/10 partition, "
        f"`random_seed={STANDARD_AUDIO_SEED}`, disjoint clip/speaker groups.",
        "- **Image (optional):** Celeb-DF (balanced), Kenjon (fake-only), DF40 robustness "
        "(via `look_again.eval_benchmarks.run_full_eval_suite`).",
        "",
    ]
    if context.get("audio_split_summary"):
        lines.extend(
            [
                "### Mix test split (speech pipeline counts)",
                "",
                "```json",
                json.dumps(context["audio_split_summary"], indent=2),
                "```",
                "",
            ]
        )
    if context.get("classical_split_summary"):
        lines.extend(
            [
                "### Mix test split (classical feature table counts)",
                "",
                "```json",
                json.dumps(context["classical_split_summary"], indent=2),
                "```",
                "",
            ]
        )

    families = []
    for row in rows:
        if row.family not in families:
            families.append(row.family)
    for family in families:
        family_rows = [row for row in rows if row.family == family]
        lines.extend([f"## {family}", ""])
        lines.append(
            "| Model | Dataset | Status | N | Accuracy | Precision | Recall | F1 | ROC-AUC | Notes |"
        )
        lines.append(
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"
        )
        for row in family_rows:
            lines.append(
                f"| {row.model} | {row.dataset} | {row.status} | {row.n_samples} | "
                f"{_format_metric(row.accuracy)} | {_format_metric(row.precision)} | "
                f"{_format_metric(row.recall)} | {_format_metric(row.f1)} | "
                f"{_format_metric(row.roc_auc)} | {row.notes.replace('|', '/')} |"
            )
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_benchmark_report(
    *,
    output_markdown: Path = RESULTS_DIR / "benchmark_report.md",
    output_json: Path = RESULTS_DIR / "benchmark_report.json",
    features_parquet: Path = DEFAULT_AUDIO_FEATURES_PARQUET,
    mix_root: Path = MIX_AUDIO_DIR,
    include_image: bool = False,
    include_speech: bool = True,
    batch_size: int = 8,
) -> Path:
    rows: list[BenchmarkRow] = []
    context: dict[str, Any] = {}

    classical_rows, classical_context = evaluate_classical_audio_models(
        features_parquet=features_parquet,
    )
    rows.extend(classical_rows)
    context["classical_split_summary"] = classical_context.get("split_summary")

    speech_rows, speech_context = [], {}
    if include_speech:
        speech_rows, speech_context = evaluate_speech_deepfake_models(
            mix_root=mix_root,
            batch_size=batch_size,
        )
    rows.extend(speech_rows)
    context["audio_split_summary"] = speech_context.get("split_summary")

    if include_image:
        rows.extend(evaluate_image_checkpoints())

    render_markdown_report(rows, context=context, output_path=output_markdown)
    output_json.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(tz=UTC).isoformat(),
                "context": context,
                "rows": [row.to_dict() for row in rows],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_markdown
