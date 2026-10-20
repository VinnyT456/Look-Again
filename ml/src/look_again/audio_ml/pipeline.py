"""End-to-end feature dataset construction with checkpointing."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from tqdm import tqdm

from look_again.paths import (
    DEFAULT_AUDIO_FEATURES_CSV,
    DEFAULT_AUDIO_FEATURES_PARQUET,
    DEFAULT_AUDIO_FEATURES_RUN_SUMMARY,
    DEFAULT_AUDIO_FEATURES_SKIPPED,
    MIX_AUDIO_DIR,
)

from .config import AudioPipelineConfig
from .data_loader import AudioSample, discover_audio_samples
from .feature_extraction import extract_features, feature_column_names
from .preprocessing import PreprocessFailure, load_audio, preprocess_audio


@dataclass(frozen=True)
class ProcessedRow:
    file_path: str
    label: str
    features: dict[str, float]


@dataclass(frozen=True)
class SkippedRow:
    file_path: str
    label: str
    reason: str


@dataclass(frozen=True)
class BuildFeatureDatasetResult:
    dataframe: pd.DataFrame
    skipped: list[SkippedRow]
    run_summary: dict[str, Any]
    parquet_path: Path
    csv_path: Path | None


def process_audio_file(
    sample: AudioSample,
    config: AudioPipelineConfig,
) -> tuple[ProcessedRow | None, SkippedRow | None]:
    """Load, preprocess, and featurize one clip; never raises."""
    loaded = load_audio(sample.absolute_path, config)
    if isinstance(loaded, PreprocessFailure):
        return None, SkippedRow(sample.file_path, sample.label, loaded.reason)
    preprocessed = preprocess_audio(loaded.waveform, config)
    if isinstance(preprocessed, PreprocessFailure):
        return None, SkippedRow(sample.file_path, sample.label, preprocessed.reason)
    try:
        features = extract_features(preprocessed.waveform, preprocessed.sample_rate, config)
    except Exception as error:  # noqa: BLE001
        return None, SkippedRow(sample.file_path, sample.label, f"feature_error: {error}")
    return ProcessedRow(sample.file_path, sample.label, features), None


def _process_sample_payload(payload: dict[str, Any], config: AudioPipelineConfig) -> tuple[
    dict[str, Any] | None, dict[str, str] | None
]:
    sample = AudioSample(
        absolute_path=Path(payload["absolute_path"]),
        file_path=payload["file_path"],
        label=payload["label"],
        class_index=int(payload["class_index"]),
    )
    processed, skipped = process_audio_file(sample, config)
    if processed is not None:
        row = {"file_path": processed.file_path, "label": processed.label}
        row.update(processed.features)
        return row, None
    assert skipped is not None
    return None, {
        "file_path": skipped.file_path,
        "label": skipped.label,
        "reason": skipped.reason,
    }


def _rows_to_dataframe(rows: list[dict[str, Any]], config: AudioPipelineConfig) -> pd.DataFrame:
    columns = ["file_path", *feature_column_names(config), "label"]
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=columns)
    return frame[columns]


def _validate_dataframe(frame: pd.DataFrame, config: AudioPipelineConfig) -> None:
    feature_names = feature_column_names(config)
    if frame.empty:
        return
    feature_block = frame.loc[:, feature_names].to_numpy(dtype=np.float64, copy=False)
    if not np.all(np.isfinite(feature_block)):
        raise ValueError("Feature matrix contains NaN or infinite values")
    if feature_block.shape[1] != len(feature_names):
        raise ValueError("Unexpected feature width in dataframe")


def save_feature_table(
    frame: pd.DataFrame,
    *,
    parquet_path: Path,
    csv_path: Path | None = None,
) -> None:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(parquet_path, index=False)
    if csv_path is not None:
        frame.to_csv(csv_path, index=False)


def load_feature_table(parquet_path: Path) -> pd.DataFrame:
    return pd.read_parquet(parquet_path)


def build_feature_dataset(
    config: AudioPipelineConfig | None = None,
    *,
    dataset_root: Path | None = None,
    output_parquet: Path = DEFAULT_AUDIO_FEATURES_PARQUET,
    output_csv: Path | None = DEFAULT_AUDIO_FEATURES_CSV,
    skipped_log: Path = DEFAULT_AUDIO_FEATURES_SKIPPED,
    run_summary_path: Path = DEFAULT_AUDIO_FEATURES_RUN_SUMMARY,
    resume: bool = True,
    write_csv: bool = False,
) -> BuildFeatureDatasetResult:
    """Extract features for all (or subsampled) Mix clips and persist a tabular dataset."""
    config = config or AudioPipelineConfig()
    start = time.perf_counter()
    samples = discover_audio_samples(
        dataset_root,
        max_samples=config.max_samples,
        random_seed=config.random_seed,
    )
    completed_paths: set[str] = set()
    existing_rows: list[dict[str, Any]] = []
    if resume and output_parquet.is_file():
        existing = pd.read_parquet(output_parquet)
        completed_paths = set(existing["file_path"].astype(str))
        existing_rows = existing.to_dict(orient="records")
        print(f"Resuming: {len(completed_paths)} clips already in {output_parquet}")

    pending = [sample for sample in samples if sample.file_path not in completed_paths]
    rows: list[dict[str, Any]] = list(existing_rows)
    skipped_rows: list[dict[str, str]] = []
    if skipped_log.is_file() and resume:
        prior_skipped = pd.read_csv(skipped_log)
        skipped_rows = prior_skipped.to_dict(orient="records")

    payloads = [
        {
            "absolute_path": str(sample.absolute_path),
            "file_path": sample.file_path,
            "label": sample.label,
            "class_index": sample.class_index,
        }
        for sample in pending
    ]

    if config.n_workers != 1 and payloads:
        batch_results = Parallel(n_jobs=config.n_workers, prefer="processes")(
            delayed(_process_sample_payload)(payload, config)
            for payload in tqdm(payloads, desc="Extracting audio features", unit="clip")
        )
        for row, skipped in batch_results:
            if row is not None:
                rows.append(row)
            if skipped is not None:
                skipped_rows.append(skipped)
    else:
        progress = tqdm(pending, desc="Extracting audio features", unit="clip")
        since_checkpoint = 0
        for sample in progress:
            processed, skipped = process_audio_file(sample, config)
            if processed is not None:
                row = {"file_path": processed.file_path, "label": processed.label}
                row.update(processed.features)
                rows.append(row)
            if skipped is not None:
                skipped_rows.append(
                    {
                        "file_path": skipped.file_path,
                        "label": skipped.label,
                        "reason": skipped.reason,
                    }
                )
            since_checkpoint += 1
            if (
                config.checkpoint_every > 0
                and since_checkpoint >= config.checkpoint_every
                and rows
            ):
                checkpoint_frame = _rows_to_dataframe(rows, config)
                _validate_dataframe(checkpoint_frame, config)
                save_feature_table(
                    checkpoint_frame,
                    parquet_path=output_parquet,
                    csv_path=output_csv if write_csv else None,
                )
                skipped_log.parent.mkdir(parents=True, exist_ok=True)
                pd.DataFrame(skipped_rows).to_csv(skipped_log, index=False)
                since_checkpoint = 0

    frame = _rows_to_dataframe(rows, config)
    _validate_dataframe(frame, config)
    save_feature_table(
        frame,
        parquet_path=output_parquet,
        csv_path=output_csv if write_csv else None,
    )
    skipped_log.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(skipped_rows).to_csv(skipped_log, index=False)

    label_counts = frame["label"].value_counts().to_dict() if not frame.empty else {}
    mix_root = (dataset_root or MIX_AUDIO_DIR).expanduser().resolve()
    run_summary = {
        "dataset_root": str(mix_root),
        "requested_samples": len(samples),
        "pending_samples": len(pending),
        "processed_successfully": int(len(frame)),
        "skipped_total": int(len(skipped_rows)),
        "label_counts_processed": label_counts,
        "sample_rate": config.sample_rate,
        "n_mfcc": config.n_mfcc,
        "normalize_audio": config.normalize_audio,
        "trim_silence": config.trim_silence,
        "feature_names": list(feature_column_names(config)),
        "feature_count": len(feature_column_names(config)),
        "runtime_seconds": time.perf_counter() - start,
        "output_parquet": str(output_parquet.resolve()),
        "output_csv": str(output_csv.resolve()) if write_csv and output_csv else None,
        "skipped_log": str(skipped_log.resolve()),
        "config": config.to_dict(),
    }
    run_summary_path.parent.mkdir(parents=True, exist_ok=True)
    run_summary_path.write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(run_summary, indent=2))
    return BuildFeatureDatasetResult(
        dataframe=frame,
        skipped=[SkippedRow(**row) for row in skipped_rows],
        run_summary=run_summary,
        parquet_path=output_parquet,
        csv_path=output_csv if write_csv else None,
    )
