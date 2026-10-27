"""Materialize a capped So-Fake-Set binary folder (fake/ + real/) for backbone + probe fine-tune.

Usage (from ``ml/``):

  uv run python -m scripts.train.community_forensics_vit_materialize_sofake
  uv run python -m scripts.train.community_forensics_vit_materialize_sofake --max-fake 3000 --max-real 3000

Then train with ``config/so_fake_probe_v3.json``:

  uv run python -m scripts.train.community_forensics_vit_finetune --config config/so_fake_probe_v3.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from tqdm import tqdm

from look_again.hf_binary_dataset import (
    SO_FAKE_HF_ID,
    materialize_hf_chunk_from_iterator,
    open_hf_row_iterator,
    open_sofake_parquet_shard_iterator,
)
from look_again.paths import DATA_DIR, PROJECT_ROOT

DEFAULT_OUT = DATA_DIR / "finetune" / "so_fake_materialized"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export So-Fake-Set to fake/ and real/ folders")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-fake", type=int, default=2500)
    parser.add_argument("--max-real", type=int, default=2500)
    parser.add_argument("--chunk-fake", type=int, default=500)
    parser.add_argument("--chunk-real", type=int, default=500)
    parser.add_argument("--hf-split", default="train")
    parser.add_argument("--parquet-shards", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    out = args.output_root if args.output_root.is_absolute() else (PROJECT_ROOT / args.output_root).resolve()
    fake_dir = out / "fake"
    real_dir = out / "real"
    shutil.rmtree(out, ignore_errors=True)
    fake_dir.mkdir(parents=True, exist_ok=True)
    real_dir.mkdir(parents=True, exist_ok=True)

    totals = {"fake": 0, "real": 0}
    chunk_index = 0
    stream_stats: dict[str, int] = {}

    if args.parquet_shards:
        row_iter = open_sofake_parquet_shard_iterator(split=args.hf_split, stats=stream_stats)
    else:
        row_iter = open_hf_row_iterator(
            dataset_id=SO_FAKE_HF_ID,
            split=args.hf_split,
            streaming=True,
        )
    tmp = out / "_chunk_tmp"

    while totals["fake"] < args.max_fake or totals["real"] < args.max_real:
        cap_fake = min(args.chunk_fake, args.max_fake - totals["fake"])
        cap_real = min(args.chunk_real, args.max_real - totals["real"])
        if cap_fake <= 0 and cap_real <= 0:
            break
        shutil.rmtree(tmp, ignore_errors=True)
        manifest, row_iter = materialize_hf_chunk_from_iterator(
            row_iter,
            output_root=tmp,
            cap_fake=max(cap_fake, 0),
            cap_real=max(cap_real, 0),
            filename_prefix=f"c{chunk_index:04d}_",
            desc=f"materialize chunk {chunk_index + 1}",
            stream_stats=stream_stats,
        )
        chunk_index += 1
        if manifest["written"] == 0:
            tqdm.write("HF stream exhausted", file=sys.stderr)
            break
        for label_name, total_key in (("fake", "fake"), ("real", "real")):
            src = tmp / label_name
            if not src.is_dir():
                continue
            for path in sorted(src.iterdir()):
                if not path.is_file():
                    continue
                dest = out / label_name / path.name
                shutil.move(str(path), str(dest))
                totals[total_key] += 1
        shutil.rmtree(tmp, ignore_errors=True)

    report = {
        "dataset_id": SO_FAKE_HF_ID,
        "output_root": str(out),
        "counts": totals,
        "chunks": chunk_index,
        "stream_rows_seen": stream_stats.get("stream_rows_seen", 0),
    }
    (out / "materialize_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
