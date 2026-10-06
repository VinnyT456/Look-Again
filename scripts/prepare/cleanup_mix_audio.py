"""Remove or quarantine out-of-range and duplicate audio clips under Mix/."""

from __future__ import annotations

import argparse
from pathlib import Path

from look_again.audio_cleanup import cleanup_mix_audio, cleanup_mix_duplicates
from look_again.paths import MIX_AUDIO_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Clean Mix/fake and Mix/real: optional duration filter and duplicate "
            "removal (SHA-256, per class). Mix/info.txt is ignored."
        ),
    )
    parser.add_argument(
        "--mix-root",
        type=Path,
        default=MIX_AUDIO_DIR,
        help=f"Root folder to scan (default: {MIX_AUDIO_DIR}).",
    )
    parser.add_argument(
        "--min-seconds",
        type=float,
        default=0.5,
        help="Minimum allowed duration in seconds (default: 0.5).",
    )
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=30.0,
        help="Maximum allowed duration in seconds (default: 30).",
    )
    parser.add_argument(
        "--skip-duration",
        action="store_true",
        help="Skip too-short/too-long filtering.",
    )
    parser.add_argument(
        "--skip-duplicates",
        action="store_true",
        help="Skip duplicate detection within fake/ and within real/.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts only; do not move or delete files.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Permanently delete rejected clips instead of moving them.",
    )
    parser.add_argument(
        "--keep-unreadable",
        action="store_true",
        help="Leave files alone when duration cannot be determined.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mode = "dry-run" if args.dry_run else ("delete" if args.delete else "move")
    mix_root = args.mix_root.resolve()

    if not args.skip_duration:
        duration_result = cleanup_mix_audio(
            args.mix_root,
            min_seconds=args.min_seconds,
            max_seconds=args.max_seconds,
            dry_run=args.dry_run,
            delete=args.delete,
            remove_unreadable=not args.keep_unreadable,
        )
        print(
            f"Duration cleanup ({mode}) | root={mix_root} | "
            f"window=[{args.min_seconds:g}, {args.max_seconds:g}]s",
            flush=True,
        )
        print(
            f"scanned={duration_result.scanned} kept={duration_result.kept} "
            f"too_short={duration_result.removed_short} too_long={duration_result.removed_long} "
            f"unreadable={duration_result.removed_unreadable}",
            flush=True,
        )
        if duration_result.rejected_dir is not None:
            print(f"Duration rejects: {duration_result.rejected_dir}", flush=True)
        if not args.dry_run and duration_result.scanned:
            print(f"Duration log: {mix_root / 'duration_cleanup_log.csv'}", flush=True)

    if not args.skip_duplicates:
        duplicate_result = cleanup_mix_duplicates(
            args.mix_root,
            dry_run=args.dry_run,
            delete=args.delete,
        )
        print(f"Duplicate cleanup ({mode}) | root={mix_root}", flush=True)
        print(
            f"scanned={duplicate_result.scanned} unique={duplicate_result.unique} "
            f"groups={duplicate_result.duplicate_groups} "
            f"removed={duplicate_result.removed_duplicates}",
            flush=True,
        )
        if duplicate_result.rejected_dir is not None:
            print(f"Duplicate rejects: {duplicate_result.rejected_dir}", flush=True)
        if not args.dry_run and duplicate_result.removed_duplicates:
            print(f"Duplicate log: {mix_root / 'duplicate_cleanup_log.csv'}", flush=True)


if __name__ == "__main__":
    main()
