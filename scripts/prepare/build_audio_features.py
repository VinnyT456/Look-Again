"""Build tabular audio features from the Mix dataset (no model training)."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from look_again.audio_ml.config import AudioPipelineConfig
from look_again.audio_ml.feature_extraction import feature_column_names
from look_again.audio_ml.pipeline import build_feature_dataset, load_feature_table
from look_again.paths import (
    DEFAULT_AUDIO_FEATURES_CSV,
    DEFAULT_AUDIO_FEATURES_PARQUET,
    DEFAULT_AUDIO_FEATURES_RUN_SUMMARY,
    DEFAULT_AUDIO_FEATURES_SKIPPED,
    MIX_AUDIO_DIR,
    PROCESSED_DIR,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mix-root", type=Path, default=MIX_AUDIO_DIR)
    parser.add_argument("--output-parquet", type=Path, default=DEFAULT_AUDIO_FEATURES_PARQUET)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_AUDIO_FEATURES_CSV)
    parser.add_argument("--skipped-log", type=Path, default=DEFAULT_AUDIO_FEATURES_SKIPPED)
    parser.add_argument("--run-summary", type=Path, default=DEFAULT_AUDIO_FEATURES_RUN_SUMMARY)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--sample-rate", type=int, default=16_000)
    parser.add_argument("--n-mfcc", type=int, default=20)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--checkpoint-every", type=int, default=5_000)
    parser.add_argument("--no-normalize", action="store_true")
    parser.add_argument("--trim-silence", action="store_true")
    parser.add_argument("--top-db", type=float, default=30.0)
    parser.add_argument("--write-csv", action="store_true", help="Also emit CSV (Parquet is default).")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument(
        "--validate-only",
        type=Path,
        default=None,
        help="Load an existing Parquet file and print validation stats.",
    )
    return parser.parse_args()


def validate_dataframe(frame: pd.DataFrame, config: AudioPipelineConfig) -> None:
    names = feature_column_names(config)
    print(f"Rows: {len(frame)}")
    print(f"Columns: {len(frame.columns)} (features={len(names)})")
    if frame.empty:
        print("Empty dataframe.")
        return
    print("Label counts:")
    print(frame["label"].value_counts())
    feature_block = frame.loc[:, names]
    values = feature_block.to_numpy(dtype=np.float64, copy=False)
    print(f"Feature matrix shape: {feature_block.shape}")
    print(f"NaN count: {int(np.isnan(values).sum())}")
    print(f"Infinite count: {int(np.isinf(values).sum())}")
    print("Sample rows:")
    print(frame.head(3).to_string(index=False))
    print("Feature names (first 10):", list(names[:10]))
    print("Total feature count:", len(names))


def main() -> None:
    args = parse_args()
    config = AudioPipelineConfig(
        sample_rate=args.sample_rate,
        n_mfcc=args.n_mfcc,
        normalize_audio=not args.no_normalize,
        trim_silence=args.trim_silence,
        top_db=args.top_db,
        random_seed=args.random_seed,
        max_samples=args.max_samples,
        n_workers=args.workers,
        checkpoint_every=args.checkpoint_every,
    )
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if args.validate_only is not None:
        loaded = load_feature_table(args.validate_only)
        validate_dataframe(loaded, config)
        return

    result = build_feature_dataset(
        config,
        dataset_root=args.mix_root,
        output_parquet=args.output_parquet,
        output_csv=args.output_csv,
        skipped_log=args.skipped_log,
        run_summary_path=args.run_summary,
        resume=not args.no_resume,
        write_csv=args.write_csv,
    )
    validate_dataframe(result.dataframe, config)
    reloaded = load_feature_table(result.parquet_path)
    if len(reloaded) != len(result.dataframe):
        raise RuntimeError("Reloaded parquet row count mismatch")
    print(f"Saved features to {result.parquet_path}")
    if args.write_csv:
        print(f"Saved CSV to {args.output_csv}")
    print(f"Run summary: {args.run_summary}")


if __name__ == "__main__":
    main()
