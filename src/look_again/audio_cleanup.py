"""Remove or quarantine audio clips outside a target duration range."""

from __future__ import annotations

import csv
import hashlib
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

from look_again.paths import MIX_AUDIO_DIR

AUDIO_SUFFIXES = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac", ".opus", ".webm"}
MIX_CLASS_DIR_NAMES = ("fake", "real")
MIX_IGNORED_ROOT_FILES = frozenset({"info.txt"})
MIX_QUARANTINE_DIR_NAMES = ("_duration_rejected", "_duplicate_rejected")


def validate_mix_layout(root: Path) -> None:
    root = root.expanduser().resolve()
    missing = [name for name in MIX_CLASS_DIR_NAMES if not (root / name).is_dir()]
    if missing:
        raise FileNotFoundError(
            f"Mix folder must contain {', '.join(MIX_CLASS_DIR_NAMES)}/ "
            f"(missing {missing} under {root}). info.txt at the root is ignored."
        )


def iter_audio_files(root: Path) -> list[Path]:
    """List audio clips under Mix/fake and Mix/real only."""
    root = root.expanduser().resolve()
    validate_mix_layout(root)
    files: list[Path] = []
    for class_name in MIX_CLASS_DIR_NAMES:
        class_dir = root / class_name
        for path in sorted(class_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.casefold() not in AUDIO_SUFFIXES:
                continue
            if any(marker in path.parts for marker in MIX_QUARANTINE_DIR_NAMES):
                continue
            files.append(path)
    return files


@dataclass(frozen=True)
class AudioCleanupResult:
    scanned: int
    kept: int
    removed_short: int
    removed_long: int
    removed_unreadable: int
    rejected_dir: Path | None


@dataclass(frozen=True)
class DuplicateCleanupResult:
    scanned: int
    unique: int
    duplicate_groups: int
    removed_duplicates: int
    rejected_dir: Path | None


def file_sha256(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicate_groups(paths: list[Path]) -> list[tuple[str, list[Path]]]:
    """Group paths by identical file content (SHA-256)."""
    by_hash: dict[str, list[Path]] = {}
    for path in sorted(paths):
        by_hash.setdefault(file_sha256(path), []).append(path)
    return [(digest, group) for digest, group in sorted(by_hash.items()) if len(group) > 1]


def _quarantine_file(
    path: Path,
    *,
    root: Path,
    rejected_root: Path,
    delete: bool,
    dry_run: bool,
) -> None:
    if dry_run:
        return
    if delete:
        path.unlink(missing_ok=True)
        return
    destination = rejected_root / path.relative_to(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    shutil.move(str(path), str(destination))


def cleanup_mix_duplicates(
    mix_root: Path | None = None,
    *,
    dry_run: bool = False,
    delete: bool = False,
    rejected_subdir: str = "_duplicate_rejected",
    write_log: bool = True,
) -> DuplicateCleanupResult:
    """Within each of Mix/fake and Mix/real, keep one copy per identical file."""
    root = (mix_root or MIX_AUDIO_DIR).expanduser().resolve()
    rejected_root = root / rejected_subdir
    log_path = root / "duplicate_cleanup_log.csv"

    scanned = duplicate_groups = removed_duplicates = 0
    log_rows: list[dict[str, str]] = []

    by_class: dict[str, list[Path]] = {name: [] for name in MIX_CLASS_DIR_NAMES}
    for path in iter_audio_files(root):
        class_name = path.relative_to(root).parts[0]
        by_class[class_name].append(path)

    for class_name in MIX_CLASS_DIR_NAMES:
        paths = by_class[class_name]
        scanned += len(paths)
        for file_hash, group in find_duplicate_groups(paths):
            duplicate_groups += 1
            keeper = group[0]
            for duplicate in group[1:]:
                removed_duplicates += 1
                log_rows.append(
                    {
                        "class": class_name,
                        "path": str(duplicate.relative_to(root)),
                        "kept_path": str(keeper.relative_to(root)),
                        "sha256": file_hash,
                        "reason": "duplicate",
                        "action": "delete" if delete else "move",
                    }
                )
                _quarantine_file(
                    duplicate,
                    root=root,
                    rejected_root=rejected_root,
                    delete=delete,
                    dry_run=dry_run,
                )

    unique = scanned - removed_duplicates

    if write_log and log_rows and not dry_run:
        with log_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["class", "path", "kept_path", "sha256", "reason", "action"],
            )
            writer.writeheader()
            writer.writerows(log_rows)

    rejected_dir = rejected_root if not delete and removed_duplicates else None
    return DuplicateCleanupResult(
        scanned=scanned,
        unique=unique,
        duplicate_groups=duplicate_groups,
        removed_duplicates=removed_duplicates,
        rejected_dir=rejected_dir,
    )


def _duration_wav_seconds(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as handle:
            frame_rate = handle.getframerate()
            if frame_rate <= 0:
                return None
            return handle.getnframes() / float(frame_rate)
    except (OSError, wave.Error):
        return None


def _duration_ffprobe_seconds(path: Path) -> float | None:
    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if completed.returncode != 0:
        return None
    text = completed.stdout.strip()
    if not text:
        return None
    try:
        duration = float(text)
    except ValueError:
        return None
    if duration < 0:
        return None
    return duration


def probe_audio_duration_seconds(path: Path) -> float | None:
    """Return clip length in seconds, or None if duration cannot be read."""
    if path.suffix.casefold() == ".wav":
        duration = _duration_wav_seconds(path)
        if duration is not None:
            return duration
    return _duration_ffprobe_seconds(path)


def cleanup_mix_audio(
    mix_root: Path | None = None,
    *,
    min_seconds: float = 0.5,
    max_seconds: float = 30.0,
    dry_run: bool = False,
    delete: bool = False,
    remove_unreadable: bool = True,
    rejected_subdir: str = "_duration_rejected",
    write_log: bool = True,
) -> AudioCleanupResult:
    """Drop or quarantine clips shorter than min_seconds or longer than max_seconds."""
    if min_seconds <= 0:
        raise ValueError(f"min_seconds must be positive, got {min_seconds}")
    if max_seconds <= min_seconds:
        raise ValueError(
            f"max_seconds must be greater than min_seconds; got {max_seconds} <= {min_seconds}"
        )

    root = (mix_root or MIX_AUDIO_DIR).expanduser().resolve()
    rejected_root = root / rejected_subdir
    log_path = root / "duration_cleanup_log.csv"

    scanned = kept = removed_short = removed_long = removed_unreadable = 0
    log_rows: list[dict[str, str | float]] = []

    for path in iter_audio_files(root):
        if rejected_root in path.parents:
            continue
        if path.name.casefold() in MIX_IGNORED_ROOT_FILES:
            continue
        scanned += 1
        duration = probe_audio_duration_seconds(path)
        reason = "keep"
        if duration is None:
            if not remove_unreadable:
                kept += 1
                continue
            reason = "unreadable"
            removed_unreadable += 1
        elif duration < min_seconds:
            reason = "too_short"
            removed_short += 1
        elif duration > max_seconds:
            reason = "too_long"
            removed_long += 1
        else:
            kept += 1
            continue

        log_rows.append(
            {
                "path": str(path.relative_to(root)),
                "duration_seconds": duration if duration is not None else "",
                "reason": reason,
                "action": "delete" if delete else "move",
            }
        )
        if dry_run:
            continue

        _quarantine_file(
            path,
            root=root,
            rejected_root=rejected_root,
            delete=delete,
            dry_run=False,
        )

    if write_log and log_rows and not dry_run:
        rejected_root.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["path", "duration_seconds", "reason", "action"],
            )
            writer.writeheader()
            writer.writerows(log_rows)

    rejected_dir = rejected_root if not delete and (removed_short + removed_long + removed_unreadable) else None
    return AudioCleanupResult(
        scanned=scanned,
        kept=kept,
        removed_short=removed_short,
        removed_long=removed_long,
        removed_unreadable=removed_unreadable,
        rejected_dir=rejected_dir,
    )
