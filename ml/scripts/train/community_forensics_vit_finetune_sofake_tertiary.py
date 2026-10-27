"""Stream So-Fake-Set with three classes: real / full_synthetic / tampered.

Default chunk caps: 500 real + 500 synthetic + 500 tampered per chunk (same
streaming pattern as ``community_forensics_vit_finetune_sofake``).

Checkpoints: ``checkpoints/community_forensics_sofake_tertiary/<run_name>/``
Feature accum: ``cache/community-forensics-vit/finetune_<run_name>_sofake_tertiary_accum.npz``

Does not mix binary universal caches (would collapse tampered into fake).

Usage (from ``ml/``):

  uv run python -m scripts.train.community_forensics_vit_finetune_sofake_tertiary
  uv run python -m scripts.train.community_forensics_vit_finetune_sofake_tertiary --chunks 30 --clear-accum
  uv run python -m scripts.train.community_forensics_vit_finetune_sofake_tertiary --features-only
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Iterator

import numpy as np
from tqdm import tqdm

from look_again.community_forensics_finetune import (
    extract_vit_features,
    load_feature_payload,
    merge_feature_payloads,
    pick_device,
    slice_feature_payload,
)
from look_again.community_forensics_finetune_multiclass import (
    TertiaryFinetuneConfig,
    label_counts_from_payload,
    load_tertiary_image_dataset,
    run_tertiary_probe_finetune_from_features,
    stratified_split_indices_tertiary,
)
from look_again.community_forensics_vit_probe import MODEL_CACHE, load_community_forensics_vit
from look_again.hf_binary_dataset import (
    SO_FAKE_HF_ID,
    materialize_hf_chunk_tertiary_from_iterator,
    open_hf_row_iterator,
    open_sofake_parquet_shard_iterator,
    skip_hf_stream_rows,
)
from look_again.paths import DATA_DIR, PROJECT_ROOT

DEFAULT_TMP = DATA_DIR / "finetune" / "so_fake_tertiary_chunk_tmp"
DEFAULT_RUN_NAME = "so_fake_tertiary_probe"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunked So-Fake 3-class ViT probe fine-tune (real / synthetic / tampered)",
    )
    parser.add_argument("--hf-split", default="train")
    parser.add_argument("--chunk-real", type=int, default=500)
    parser.add_argument("--chunk-synthetic", type=int, default=500)
    parser.add_argument("--chunk-tampered", type=int, default=500)
    parser.add_argument("--chunks", type=int, default=20)
    parser.add_argument("--tmp-dir", type=Path, default=DEFAULT_TMP)
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--logistic-c", type=float, default=0.01)
    parser.add_argument("--train-val-fraction", type=float, default=0.8)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--clear-accum", action="store_true")
    parser.add_argument("--no-streaming", action="store_true")
    parser.add_argument("--stream-skip", type=int, default=None)
    parser.add_argument("--features-only", action="store_true")
    parser.add_argument(
        "--parquet-shards",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    args = parser.parse_args()

    tmp_dir = args.tmp_dir if args.tmp_dir.is_absolute() else (PROJECT_ROOT / args.tmp_dir).resolve()
    accum_path = MODEL_CACHE / f"finetune_{args.run_name}_sofake_tertiary_accum.npz"
    stream_state_path = accum_path.with_suffix(".stream.json")

    if args.clear_accum:
        accum_path.unlink(missing_ok=True)
        stream_state_path.unlink(missing_ok=True)
        if accum_path.is_file() or stream_state_path.is_file():
            tqdm.write("cleared accum/stream state", file=sys.stderr)

    stream_stats: dict[str, int] = {"stream_rows_seen": 0, "skipped_bad_rows": 0}
    resume_skip_rows = 0
    start_parquet_shard = 0
    if stream_state_path.is_file() and not args.clear_accum:
        loaded = json.loads(stream_state_path.read_text())
        resume_skip_rows = int(loaded.get("stream_rows_seen", 0))
        stream_stats["skipped_bad_rows"] = int(loaded.get("skipped_bad_rows", 0))
        start_parquet_shard = int(loaded.get("parquet_shard_index", 0))

    device = pick_device()
    tqdm.write(f"device: {device}", file=sys.stderr)

    row_iter: Iterator | None = None
    if not args.features_only:
        if args.parquet_shards:
            tqdm.write(
                f"opening {SO_FAKE_HF_ID} split={args.hf_split!r} "
                f"(parquet shards, start={start_parquet_shard})",
                file=sys.stderr,
            )
            row_iter = open_sofake_parquet_shard_iterator(
                split=args.hf_split,
                stats=stream_stats,
                start_shard=start_parquet_shard,
            )
        else:
            row_iter = open_hf_row_iterator(
                dataset_id=SO_FAKE_HF_ID,
                split=args.hf_split,
                streaming=not args.no_streaming,
            )
            skip_rows = args.stream_skip if args.stream_skip is not None else resume_skip_rows
            if skip_rows > 0:
                tqdm.write(f"skipping {skip_rows} HF stream rows…", file=sys.stderr)
                skip_hf_stream_rows(row_iter, skip_rows, stats=stream_stats)

    accum: dict | None = load_feature_payload(accum_path)
    chunk_manifests: list[dict] = []

    if not args.features_only:
        tqdm.write("Loading CommunityForensics ViT…", file=sys.stderr)
        model, processor = load_community_forensics_vit(device)
        model.eval()

    for chunk_index in tqdm(range(args.chunks), desc="so-fake tertiary chunks", unit="chunk", file=sys.stderr):
        if args.features_only:
            break
        chunk_root = tmp_dir / f"chunk_{chunk_index:04d}"
        shutil.rmtree(chunk_root, ignore_errors=True)

        manifest, row_iter = materialize_hf_chunk_tertiary_from_iterator(
            row_iter,
            output_root=chunk_root,
            cap_real=args.chunk_real,
            cap_synthetic=args.chunk_synthetic,
            cap_tampered=args.chunk_tampered,
            filename_prefix=f"c{chunk_index:04d}_",
            desc=f"chunk {chunk_index + 1}/{args.chunks} export",
            stream_stats=stream_stats,
        )
        manifest["chunk_index"] = chunk_index
        chunk_manifests.append(manifest)
        if hasattr(row_iter, "shard_index"):
            stream_stats["parquet_shard_index"] = int(row_iter.shard_index)
        stream_state_path.write_text(json.dumps(stream_stats, indent=2) + "\n")

        if manifest["written"] == 0:
            tqdm.write("no more rows from HF stream; stopping", file=sys.stderr)
            break

        tqdm.write(
            f"chunk {chunk_index}: real={manifest['real']} synthetic={manifest['synthetic']} "
            f"tampered={manifest['tampered']}",
            file=sys.stderr,
        )
        samples = load_tertiary_image_dataset(chunk_root)
        chunk_cache = tmp_dir / f"_features_{chunk_index:04d}.npz"
        extract_vit_features(
            samples,
            model,
            processor,
            device,
            batch_size=args.batch_size,
            cache_path=chunk_cache,
            rebuild_cache=True,
            desc=f"chunk {chunk_index + 1} extract_vit",
        )
        chunk_payload = load_feature_payload(chunk_cache)
        if chunk_payload is None:
            raise RuntimeError(f"Missing feature cache for chunk {chunk_index}")
        accum = merge_feature_payloads(accum, chunk_payload)
        accum_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(accum_path, **accum)
        chunk_cache.unlink(missing_ok=True)
        shutil.rmtree(chunk_root, ignore_errors=True)

    if accum is None or len(accum.get("labels", [])) == 0:
        print("No features accumulated; nothing to train.", file=sys.stderr)
        sys.exit(1)

    labels = accum["labels"].astype(np.int64)
    train_idx, val_idx = stratified_split_indices_tertiary(
        labels,
        train_fraction=args.train_val_fraction,
        seed=42,
    )
    train_payload = slice_feature_payload(accum, train_idx)
    val_payload = slice_feature_payload(accum, val_idx)

    config = TertiaryFinetuneConfig(
        run_name=args.run_name,
        train_val_fraction=args.train_val_fraction,
        logistic_c=args.logistic_c,
    )
    probe_report = run_tertiary_probe_finetune_from_features(
        config,
        train_payload=train_payload,
        val_payload=val_payload,
    )

    report = {
        "dataset_id": SO_FAKE_HF_ID,
        "task": "tertiary_real_synthetic_tampered",
        "hf_split": args.hf_split,
        "chunk_real": args.chunk_real,
        "chunk_synthetic": args.chunk_synthetic,
        "chunk_tampered": args.chunk_tampered,
        "chunks_requested": args.chunks,
        "chunks_run": len(chunk_manifests),
        "chunk_manifests": chunk_manifests,
        "accumulated_features": int(len(labels)),
        "accum_cache": str(accum_path),
        "stream_state": str(stream_state_path),
        "stream_rows_seen": stream_stats.get("stream_rows_seen", 0),
        "skipped_bad_rows": stream_stats.get("skipped_bad_rows", 0),
        "parquet_shard_index": stream_stats.get("parquet_shard_index", 0),
        "parquet_shards": args.parquet_shards,
        "label_counts": label_counts_from_payload(labels),
        "checkpoint_root": str(config.resolved_output_dir()),
        **probe_report,
    }
    report_path = config.resolved_output_dir() / "finetune_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    report["report_path"] = str(report_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
