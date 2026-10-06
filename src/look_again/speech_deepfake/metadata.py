"""Metadata extraction for Mix audio clips."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from look_again.audio_cleanup import MIX_CLASS_DIR_NAMES
from look_again.audio_ml.data_loader import discover_audio_samples

from .config import CLASS_NAMES, LABEL_FAKE, LABEL_REAL

_LJ_SPEAKER = re.compile(r"^(LJ\d{3})", re.IGNORECASE)
_GENERATED_SUFFIX = re.compile(r"(_generated|_gen)$", re.IGNORECASE)


@dataclass(frozen=True)
class SpeechRecord:
    absolute_path: Path
    file_path: str
    label: int
    label_name: str
    speaker_id: str | None
    group_id: str
    source_bucket: str
    generation_hint: str | None


def _label_to_int(label_name: str) -> int:
    if label_name == "real":
        return LABEL_REAL
    if label_name == "fake":
        return LABEL_FAKE
    raise ValueError(f"Unexpected label {label_name!r}")


def infer_speaker_id(file_path: str) -> str | None:
    stem = Path(file_path).stem
    match = _LJ_SPEAKER.match(stem)
    if match:
        return match.group(1).upper()
    return None


def infer_generation_hint(file_path: str, label_name: str) -> str | None:
    if label_name != "fake":
        return None
    stem = Path(file_path).stem
    if _GENERATED_SUFFIX.search(stem):
        return "synthetic_suffix"
    if stem.startswith("LJ"):
        return "lj_speech_derived"
    if "deep" in stem.casefold() or "fake" in stem.casefold():
        return "filename_hint"
    return "unknown_fake"


def build_speech_records(
    dataset_root: Path | None = None,
    *,
    max_samples: int | None = None,
    random_seed: int = 42,
) -> list[SpeechRecord]:
    """Discover Mix clips and attach speaker/group metadata for disjoint splits."""
    samples = discover_audio_samples(
        dataset_root,
        max_samples=max_samples,
        random_seed=random_seed,
    )
    records: list[SpeechRecord] = []
    for sample in samples:
        if sample.label not in CLASS_NAMES:
            raise ValueError(f"Unexpected label {sample.label!r} for {sample.file_path}")
        speaker_id = infer_speaker_id(sample.file_path)
        group_id = f"speaker:{speaker_id}" if speaker_id else f"clip:{sample.file_path}"
        records.append(
            SpeechRecord(
                absolute_path=sample.absolute_path,
                file_path=sample.file_path,
                label=_label_to_int(sample.label),
                label_name=sample.label,
                speaker_id=speaker_id,
                group_id=group_id,
                source_bucket=Path(sample.file_path).parts[0],
                generation_hint=infer_generation_hint(sample.file_path, sample.label),
            )
        )
    return records
