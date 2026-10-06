"""Build a local DF40-derived inswap subset for identity-safe training."""

from __future__ import annotations

import csv
import json
import os
import random
import re
import shutil
import tempfile
import zipfile
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import cv2
from huggingface_hub import hf_hub_download
from PIL import Image

from look_again.face_preprocessing import (
    FACE_CROP_MARGIN,
    FACE_CROP_SIZE,
    FACE_DETECTOR_VERSION,
    crop_face,
    crop_to_window,
)

from look_again.paths import CACHE_DIR, DATA_DIR, INTERMEDIATE_DIR, PROJECT_ROOT
DATASET_PATH = DATA_DIR / "DF40"
FACE_CROP_DATASET_PATH = DATA_DIR / "DF40_face_swap_crops"
LEGACY_FACE_CROP_DATASET_PATH = DATA_DIR / "DF40_face_crops"
UNPAIRED_FACE_CROP_DATASET_PATH = DATA_DIR / "DF40_face_crops_unpaired"
PREPARE_MARKER = DATASET_PATH / ".prepare_complete"
MANIFEST_PATH = DATASET_PATH / "prepare_manifest.json"
PREP_CACHE_DIR = CACHE_DIR / "df40_prep"

DF40_JSON_REPO = "sinister007/df40_dataset"
DF40_JSON_FILE = "dataset_json/inswap_ff.json"
DF40_FAKE_REPO = "ManhQuangAI/DF40_train"
DF40_FAKE_ARCHIVE = "inswap.zip"
FF_REPO = "bitmind/FaceForensicsC23"
FF_ARCHIVE = "FaceForensics++_C23.zip"

DF40_METHOD = "inswap"
DEFAULT_MAX_PAIRS = int(os.environ.get("DF40_MAX_PAIRS", "3000"))
JPEG_QUALITY = 95
MAX_OPEN_FF_VIDEO_DECODERS = 8
SEED = 42

_FAKE_FRAME_RE = re.compile(r"inswap/frames/(\d+)_(\d+)/(\d+)\.png$")


@dataclass(frozen=True)
class PairCandidate:
    source_identity: str
    target_face: str
    frame_index: int
    fake_zip_member: str


def _hub_dataset_path(repo_id: str, filename: str) -> Path:
    return Path(
        hf_hub_download(repo_id=repo_id, filename=filename, repo_type="dataset")
    )


def _iter_fake_candidates(inswap_json: dict) -> list[PairCandidate]:
    fake_root = inswap_json["inswap_ff"]["inswap_Fake"]
    candidates: list[PairCandidate] = []
    for split_name in ("train", "test", "val"):
        split = fake_root.get(split_name)
        if not split:
            continue
        for _video_key, entry in split.items():
            for relative_path in entry["frames"]:
                member = relative_path.split("DF40_train/", 1)[-1]
                match = _FAKE_FRAME_RE.search(member)
                if match is None:
                    continue
                source_identity, target_face, frame_text = match.groups()
                candidates.append(
                    PairCandidate(
                        source_identity=source_identity,
                        target_face=target_face,
                        frame_index=int(frame_text),
                        fake_zip_member=member,
                    )
                )
    return candidates


def _real_video_member(target_face: str) -> str:
    return f"FaceForensics++_C23/real/{target_face}.mp4"


class _FfVideoReader:
    def __init__(self, ff_zip: zipfile.ZipFile) -> None:
        self._ff_zip = ff_zip
        # OpenCV/FFmpeg keeps a decoder context per VideoCapture. Keeping a
        # capture for every video eventually exhausts H.264 decoder resources.
        self._captures: OrderedDict[str, cv2.VideoCapture] = OrderedDict()
        self._available_videos = {
            Path(name).name.replace(".mp4", "")
            for name in ff_zip.namelist()
            if name.endswith(".mp4") and "/real/" in name
        }

    def has_video(self, target_face: str) -> bool:
        return target_face in self._available_videos

    def read_frame(self, target_face: str, frame_index: int):
        if target_face not in self._captures:
            if len(self._captures) >= MAX_OPEN_FF_VIDEO_DECODERS:
                _, oldest_capture = self._captures.popitem(last=False)
                oldest_capture.release()
            member = _real_video_member(target_face)
            temp_path = PREP_CACHE_DIR / "ff_videos" / f"{target_face}.mp4"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            if not temp_path.is_file():
                with self._ff_zip.open(member) as src, temp_path.open("wb") as dst:
                    dst.write(src.read())
            capture = cv2.VideoCapture(str(temp_path))
            if not capture.isOpened():
                capture.release()
                return None
            self._captures[target_face] = capture
        else:
            self._captures.move_to_end(target_face)

        capture = self._captures[target_face]
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        success, frame = capture.read()
        if not success or frame is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    def close(self) -> None:
        for capture in self._captures.values():
            capture.release()
        self._captures.clear()


def ensure_df40_subset(
    *,
    max_pairs: int = DEFAULT_MAX_PAIRS,
    force: bool = False,
) -> Path:
    """Download DF40 inswap fakes + FF++ reals and materialize ``DF40/`` locally."""
    if (
        not force
        and PREPARE_MARKER.is_file()
        and (DATASET_PATH / "metadata.csv").is_file()
        and (DATASET_PATH / "fake").is_dir()
        and (DATASET_PATH / "real").is_dir()
    ):
        return DATASET_PATH

    DATASET_PATH.mkdir(parents=True, exist_ok=True)
    (DATASET_PATH / "fake").mkdir(exist_ok=True)
    (DATASET_PATH / "real").mkdir(exist_ok=True)

    json_path = _hub_dataset_path(DF40_JSON_REPO, DF40_JSON_FILE)
    fake_zip_path = _hub_dataset_path(DF40_FAKE_REPO, DF40_FAKE_ARCHIVE)
    ff_zip_path = _hub_dataset_path(FF_REPO, FF_ARCHIVE)

    with json_path.open(encoding="utf-8") as json_file:
        inswap_json = json.load(json_file)

    candidates = _iter_fake_candidates(inswap_json)
    random.Random(SEED).shuffle(candidates)

    metadata_rows: list[dict[str, str]] = []
    fake_members_in_zip: set[str] = set()

    with zipfile.ZipFile(fake_zip_path) as fake_zip, zipfile.ZipFile(ff_zip_path) as ff_zip:
        fake_members_in_zip = set(fake_zip.namelist())
        reader = _FfVideoReader(ff_zip)
        pair_id = 0
        for candidate in candidates:
            if len(metadata_rows) >= max_pairs:
                break
            if candidate.fake_zip_member not in fake_members_in_zip:
                continue
            if not reader.has_video(candidate.target_face):
                continue
            real_image = reader.read_frame(candidate.target_face, candidate.frame_index)
            if real_image is None:
                continue
            try:
                with fake_zip.open(candidate.fake_zip_member) as fake_file:
                    fake_image = Image.open(fake_file).convert("RGB")
            except KeyError:
                continue

            fake_name = f"fake/fake_{pair_id:05d}.jpg"
            real_name = f"real/real_{pair_id:05d}.jpg"
            fake_image.save(
                DATASET_PATH / fake_name,
                format="JPEG",
                quality=JPEG_QUALITY,
            )
            real_image.save(
                DATASET_PATH / real_name,
                format="JPEG",
                quality=JPEG_QUALITY,
            )
            metadata_rows.append(
                {
                    "id": str(pair_id),
                    "fake_file": fake_name,
                    "real_file": real_name,
                    "method": DF40_METHOD,
                        "source_identity": candidate.source_identity,
                        "target_face": candidate.target_face,
                        "source_video_id": candidate.target_face,
                        "frame_index": str(candidate.frame_index),
                        "label_fake": "1",
                    "label_real": "0",
                }
            )
            pair_id += 1
        reader.close()

    if not metadata_rows:
        raise RuntimeError("DF40 subset preparation produced zero valid pairs")

    metadata_path = DATASET_PATH / "metadata.csv"
    with metadata_path.open("w", newline="", encoding="utf-8") as metadata_file:
        writer = csv.DictWriter(
            metadata_file,
            fieldnames=[
                "id",
                "fake_file",
                "real_file",
                "method",
                "source_identity",
                "target_face",
                "source_video_id",
                "frame_index",
                "label_fake",
                "label_real",
            ],
        )
        writer.writeheader()
        writer.writerows(metadata_rows)

    manifest = {
        "dataset": "DF40-derived subset (inswap @ FF++)",
        "json_repo": DF40_JSON_REPO,
        "fake_repo": DF40_FAKE_REPO,
        "ff_repo": FF_REPO,
        "method": DF40_METHOD,
        "max_pairs": max_pairs,
        "pairs_written": len(metadata_rows),
        "seed": SEED,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    PREPARE_MARKER.write_text("ok\n", encoding="utf-8")
    print(
        f"DF40 subset ready at {DATASET_PATH} "
        f"({len(metadata_rows)} aligned inswap pairs)",
        flush=True,
    )
    return DATASET_PATH


def _safe_dataset_image_path(dataset_root: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe path in DF40 metadata: {relative_path}")
    root = dataset_root.resolve()
    image_path = (root / relative).resolve()
    try:
        image_path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"Image path escapes the DF40 folder: {relative_path}") from error
    return image_path


def _df40_pair_source_paths(row: dict[str, str]) -> tuple[Path, Path] | None:
    """Resolve original DF40 full-frame paths; return None if either file is missing."""
    fake_rel = row.get("original_fake_file") or row["fake_file"]
    real_rel = row.get("original_real_file") or row["real_file"]
    fake_source = _safe_dataset_image_path(DATASET_PATH, fake_rel)
    real_source = _safe_dataset_image_path(DATASET_PATH, real_rel)
    if not fake_source.is_file() or not real_source.is_file():
        return None
    return fake_source, real_source


def _face_crop_dataset_is_ready() -> bool:
    manifest_path = FACE_CROP_DATASET_PATH / "face_crop_manifest.json"
    if not (
        manifest_path.is_file()
        and (FACE_CROP_DATASET_PATH / "metadata.csv").is_file()
        and (FACE_CROP_DATASET_PATH / "fake").is_dir()
        and (FACE_CROP_DATASET_PATH / "real").is_dir()
    ):
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return manifest.get("crop_strategy") == "real_anchored_shared_window_v1"


def _scale_crop_window(
    window: tuple[int, int, int, int],
    reference_size: tuple[int, int],
    target_size: tuple[int, int],
) -> tuple[int, int, int, int] | None:
    """Transfer a crop window between same-aspect-ratio paired frames."""
    reference_width, reference_height = reference_size
    target_width, target_height = target_size
    reference_aspect = reference_width / reference_height
    target_aspect = target_width / target_height
    if abs(reference_aspect - target_aspect) > reference_aspect * 0.01:
        return None

    left, top, right, bottom = window
    target_window = (
        round(left * target_width / reference_width),
        round(top * target_height / reference_height),
        round(right * target_width / reference_width),
        round(bottom * target_height / reference_height),
    )
    left, top, right, bottom = target_window
    target_window = (
        max(0, min(target_width - 1, left)),
        max(0, min(target_height - 1, top)),
        max(1, min(target_width, right)),
        max(1, min(target_height, bottom)),
    )
    if target_window[2] <= target_window[0] or target_window[3] <= target_window[1]:
        return None
    return target_window


def _face_bbox_in_crop(
    face_bbox: tuple[int, int, int, int],
    crop_window: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    left, top, right, bottom = crop_window
    crop_width = right - left
    crop_height = bottom - top
    x1, y1, x2, y2 = face_bbox
    return (
        max(0, min(FACE_CROP_SIZE, round((x1 - left) * FACE_CROP_SIZE / crop_width))),
        max(0, min(FACE_CROP_SIZE, round((y1 - top) * FACE_CROP_SIZE / crop_height))),
        max(0, min(FACE_CROP_SIZE, round((x2 - left) * FACE_CROP_SIZE / crop_width))),
        max(0, min(FACE_CROP_SIZE, round((y2 - top) * FACE_CROP_SIZE / crop_height))),
    )


def ensure_face_crop_dataset(*, force: bool = False) -> Path:
    """Materialize a matched face-cropped copy while preserving the source data.

    The genuine image anchors face detection and the crop window. That same
    normalized window is applied to its paired swapped image; both crops then
    receive identical resizing and JPEG encoding. This removes detector and
    crop-placement differences as easy label cues.
    """
    if not force and _face_crop_dataset_is_ready():
        return FACE_CROP_DATASET_PATH

    if not (
        (DATASET_PATH / "metadata.csv").is_file()
        and (DATASET_PATH / "fake").is_dir()
        and (DATASET_PATH / "real").is_dir()
    ):
        ensure_df40_subset()

    metadata_path = DATASET_PATH / "metadata.csv"
    with metadata_path.open(newline="", encoding="utf-8") as metadata_file:
        reader = csv.DictReader(metadata_file)
        metadata_rows = list(reader)
        source_fields = list(reader.fieldnames or ())
    required_fields = {
        "id",
        "fake_file",
        "real_file",
        "method",
        "source_identity",
        "target_face",
    }
    missing_fields = required_fields - set(source_fields)
    if missing_fields:
        raise ValueError(
            f"DF40 metadata is missing required fields: {sorted(missing_fields)}"
        )
    if not metadata_rows:
        raise RuntimeError(f"DF40 metadata has no image pairs: {metadata_path}")

    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    stage_root = Path(
        tempfile.mkdtemp(prefix="DF40_face_swap_crops-", dir=INTERMEDIATE_DIR)
    )
    (stage_root / "fake").mkdir()
    (stage_root / "real").mkdir()
    output_fields = list(
        dict.fromkeys(
            source_fields
            + [
                "source_video_id",
                "frame_index",
                "original_fake_file",
                "original_real_file",
                "reference_face_bbox",
                "face_bbox_in_crop",
                "real_crop_window",
                "fake_crop_window",
                "real_image_size",
                "fake_image_size",
                "same_source_crop",
            ]
        )
    )
    output_rows: list[dict[str, str]] = []
    failures = {"real_no_face": 0, "fake_crop_invalid": 0, "pair_excluded": 0, "missing_source_file": 0}

    try:
        for row_number, row in enumerate(metadata_rows, start=1):
            sources = _df40_pair_source_paths(row)
            if sources is None:
                failures["missing_source_file"] += 1
                continue
            fake_source, real_source = sources
            with Image.open(fake_source) as source_image:
                fake_image = source_image.convert("RGB")
            with Image.open(real_source) as source_image:
                real_crop = crop_face(source_image)
                real_source_size = source_image.size

            if real_crop is None:
                failures["real_no_face"] += 1
            fake_crop_image = None
            fake_crop_window = None
            if real_crop is not None:
                fake_crop_window = _scale_crop_window(
                    real_crop.crop_bbox,
                    real_source_size,
                    fake_image.size,
                )
                if fake_crop_window is not None:
                    fake_crop_image = crop_to_window(fake_image, fake_crop_window)
                else:
                    failures["fake_crop_invalid"] += 1
            if fake_crop_image is None or real_crop is None:
                failures["pair_excluded"] += 1
            else:
                fake_name = f"fake/face_{len(output_rows):05d}.jpg"
                real_name = f"real/face_{len(output_rows):05d}.jpg"
                fake_crop_image.save(
                    stage_root / fake_name,
                    format="JPEG",
                    quality=JPEG_QUALITY,
                )
                real_crop.image.save(
                    stage_root / real_name,
                    format="JPEG",
                    quality=JPEG_QUALITY,
                )
                output_rows.append(
                    {
                        **row,
                        "fake_file": fake_name,
                        "real_file": real_name,
                        "original_fake_file": row["fake_file"],
                        "original_real_file": row["real_file"],
                        "source_video_id": row.get("source_video_id") or row["target_face"],
                        "frame_index": row.get("frame_index", ""),
                        "reference_face_bbox": ",".join(map(str, real_crop.bbox)),
                        "face_bbox_in_crop": ",".join(
                            map(
                                str,
                                _face_bbox_in_crop(real_crop.bbox, real_crop.crop_bbox),
                            )
                        ),
                        "real_crop_window": ",".join(map(str, real_crop.crop_bbox)),
                        "fake_crop_window": ",".join(map(str, fake_crop_window)),
                        "real_image_size": "x".join(map(str, real_source_size)),
                        "fake_image_size": "x".join(map(str, fake_image.size)),
                        "same_source_crop": "1",
                    }
                )

            if row_number % 500 == 0 or row_number == len(metadata_rows):
                print(
                    f"Face-crop preprocessing: {row_number}/{len(metadata_rows)} pairs; "
                    f"kept={len(output_rows)}, excluded={failures['pair_excluded']}",
                    flush=True,
                )

        if not output_rows:
            raise RuntimeError(
                "Face-crop preprocessing found no pairs with a detected reference face"
            )

        with (stage_root / "metadata.csv").open(
            "w", newline="", encoding="utf-8"
        ) as metadata_file:
            writer = csv.DictWriter(metadata_file, fieldnames=output_fields)
            writer.writeheader()
            writer.writerows(output_rows)

        manifest = {
            "dataset": "DF40-derived matched face-swap crops",
            "source_dataset": str(DATASET_PATH.relative_to(PROJECT_ROOT)),
            "detector": FACE_DETECTOR_VERSION,
            "crop_size": FACE_CROP_SIZE,
            "crop_margin": FACE_CROP_MARGIN,
            "crop_strategy": "real_anchored_shared_window_v1",
            "crop_anchor": "genuine_pair_image",
            "pairing": "same_target_video_and_frame_index",
            "source_pairs": len(metadata_rows),
            "pairs_written": len(output_rows),
            "pairs_excluded": failures["pair_excluded"],
            "crop_failures": {
                "fake_crop_invalid": failures["fake_crop_invalid"],
                "real_reference_no_face": failures["real_no_face"],
            },
        }
        (stage_root / "face_crop_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        (stage_root / ".prepare_complete").write_text("ok\n", encoding="utf-8")

        if FACE_CROP_DATASET_PATH.exists():
            if not _face_crop_dataset_is_ready():
                raise FileExistsError(
                    f"Refusing to replace unrecognized dataset directory: "
                    f"{FACE_CROP_DATASET_PATH}"
                )
            if not force:
                return FACE_CROP_DATASET_PATH
            backup_path = FACE_CROP_DATASET_PATH.with_name(
                f"{FACE_CROP_DATASET_PATH.name}.previous"
            )
            if backup_path.exists():
                raise FileExistsError(
                    f"Refusing to overwrite existing backup: {backup_path}"
                )
            os.replace(FACE_CROP_DATASET_PATH, backup_path)
            try:
                os.replace(stage_root, FACE_CROP_DATASET_PATH)
            except Exception:
                os.replace(backup_path, FACE_CROP_DATASET_PATH)
                raise
            shutil.rmtree(backup_path)
        else:
            os.replace(stage_root, FACE_CROP_DATASET_PATH)
    finally:
        if stage_root.exists():
            shutil.rmtree(stage_root)

    print(
        f"Matched face-swap crop dataset ready at {FACE_CROP_DATASET_PATH} "
        f"({len(output_rows)}/{len(metadata_rows)} pairs; "
        f"{failures['pair_excluded']} pairs excluded for missing reference faces "
        "or incompatible paired-frame geometry)",
        flush=True,
    )
    return FACE_CROP_DATASET_PATH


def _unpaired_face_crop_dataset_is_ready() -> bool:
    manifest_path = UNPAIRED_FACE_CROP_DATASET_PATH / "face_crop_manifest.json"
    if not (
        manifest_path.is_file()
        and (UNPAIRED_FACE_CROP_DATASET_PATH / "metadata.csv").is_file()
        and (UNPAIRED_FACE_CROP_DATASET_PATH / "fake").is_dir()
        and (UNPAIRED_FACE_CROP_DATASET_PATH / "real").is_dir()
    ):
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return manifest.get("crop_strategy") == "independent_per_image_v1"


def ensure_unpaired_face_crop_dataset(*, force: bool = False) -> Path:
    """Face-crop real and fake with separate detections (matches video inference)."""
    if not force and _unpaired_face_crop_dataset_is_ready():
        return UNPAIRED_FACE_CROP_DATASET_PATH

    if (
        (DATASET_PATH / "fake").is_dir()
        and (DATASET_PATH / "real").is_dir()
        and (DATASET_PATH / "metadata.csv").is_file()
    ):
        metadata_path = DATASET_PATH / "metadata.csv"
    elif (
        (DATASET_PATH / "fake").is_dir()
        and (DATASET_PATH / "real").is_dir()
        and (LEGACY_FACE_CROP_DATASET_PATH / "metadata.csv").is_file()
    ):
        metadata_path = LEGACY_FACE_CROP_DATASET_PATH / "metadata.csv"
    else:
        ensure_df40_subset()
        metadata_path = DATASET_PATH / "metadata.csv"

    with metadata_path.open(newline="", encoding="utf-8") as metadata_file:
        reader = csv.DictReader(metadata_file)
        metadata_rows = list(reader)
        source_fields = list(reader.fieldnames or ())
    if not metadata_rows:
        raise RuntimeError(f"DF40 metadata has no image pairs: {metadata_path}")

    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    stage_root = Path(
        tempfile.mkdtemp(prefix="DF40_face_crops_unpaired-", dir=INTERMEDIATE_DIR)
    )
    (stage_root / "fake").mkdir()
    (stage_root / "real").mkdir()
    output_fields = list(
        dict.fromkeys(
            source_fields
            + [
                "original_fake_file",
                "original_real_file",
                "real_crop_window",
                "fake_crop_window",
                "same_source_crop",
            ]
        )
    )
    output_rows: list[dict[str, str]] = []
    failures = {"real_no_face": 0, "fake_no_face": 0, "pair_excluded": 0, "missing_source_file": 0}

    try:
        for row_number, row in enumerate(metadata_rows, start=1):
            fake_rel = row.get("original_fake_file") or row["fake_file"]
            real_rel = row.get("original_real_file") or row["real_file"]
            sources = _df40_pair_source_paths(row)
            if sources is None:
                failures["missing_source_file"] += 1
                continue
            fake_source, real_source = sources
            with Image.open(fake_source) as source_image:
                fake_image = source_image.convert("RGB")
            with Image.open(real_source) as source_image:
                real_image = source_image.convert("RGB")

            real_crop = crop_face(real_image)
            fake_crop = crop_face(fake_image)
            if real_crop is None:
                failures["real_no_face"] += 1
            if fake_crop is None:
                failures["fake_no_face"] += 1
            if real_crop is None or fake_crop is None:
                failures["pair_excluded"] += 1
                continue

            fake_name = f"fake/face_{len(output_rows):05d}.jpg"
            real_name = f"real/face_{len(output_rows):05d}.jpg"
            fake_crop.image.save(stage_root / fake_name, format="JPEG", quality=JPEG_QUALITY)
            real_crop.image.save(stage_root / real_name, format="JPEG", quality=JPEG_QUALITY)
            output_rows.append(
                {
                    **row,
                    "fake_file": fake_name,
                    "real_file": real_name,
                    "original_fake_file": fake_rel,
                    "original_real_file": real_rel,
                    "real_crop_window": ",".join(map(str, real_crop.crop_bbox)),
                    "fake_crop_window": ",".join(map(str, fake_crop.crop_bbox)),
                    "same_source_crop": "0",
                }
            )

            if row_number % 500 == 0 or row_number == len(metadata_rows):
                print(
                    f"Unpaired face-crop preprocessing: {row_number}/{len(metadata_rows)} pairs; "
                    f"kept={len(output_rows)}, excluded={failures['pair_excluded']}",
                    flush=True,
                )

        if not output_rows:
            raise RuntimeError(
                "Unpaired face-crop preprocessing found no pairs with faces on both images"
            )

        with (stage_root / "metadata.csv").open(
            "w", newline="", encoding="utf-8"
        ) as metadata_file:
            writer = csv.DictWriter(metadata_file, fieldnames=output_fields)
            writer.writeheader()
            writer.writerows(output_rows)

        manifest = {
            "dataset": "DF40-derived independent face-swap crops",
            "source_dataset": str(DATASET_PATH.relative_to(PROJECT_ROOT)),
            "detector": FACE_DETECTOR_VERSION,
            "crop_size": FACE_CROP_SIZE,
            "crop_margin": FACE_CROP_MARGIN,
            "crop_strategy": "independent_per_image_v1",
            "crop_anchor": "per_image_detection",
            "pairing": "same_swap_pair_index_only",
            "source_pairs": len(metadata_rows),
            "pairs_written": len(output_rows),
            "pairs_excluded": failures["pair_excluded"],
            "crop_failures": failures,
        }
        (stage_root / "face_crop_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        (stage_root / ".prepare_complete").write_text("ok\n", encoding="utf-8")

        if UNPAIRED_FACE_CROP_DATASET_PATH.exists():
            if not _unpaired_face_crop_dataset_is_ready():
                raise FileExistsError(
                    f"Refusing to replace unrecognized dataset directory: "
                    f"{UNPAIRED_FACE_CROP_DATASET_PATH}"
                )
            if not force:
                return UNPAIRED_FACE_CROP_DATASET_PATH
            backup_path = UNPAIRED_FACE_CROP_DATASET_PATH.with_name(
                f"{UNPAIRED_FACE_CROP_DATASET_PATH.name}.previous"
            )
            if backup_path.exists():
                raise FileExistsError(
                    f"Refusing to overwrite existing backup: {backup_path}"
                )
            os.replace(UNPAIRED_FACE_CROP_DATASET_PATH, backup_path)
            try:
                os.replace(stage_root, UNPAIRED_FACE_CROP_DATASET_PATH)
            except Exception:
                os.replace(backup_path, UNPAIRED_FACE_CROP_DATASET_PATH)
                raise
            shutil.rmtree(backup_path)
        else:
            os.replace(stage_root, UNPAIRED_FACE_CROP_DATASET_PATH)
    finally:
        if stage_root.exists():
            shutil.rmtree(stage_root)

    print(
        f"Unpaired face-crop dataset ready at {UNPAIRED_FACE_CROP_DATASET_PATH} "
        f"({len(output_rows)}/{len(metadata_rows)} pairs; "
        f"{failures['pair_excluded']} pairs excluded)",
        flush=True,
    )
    return UNPAIRED_FACE_CROP_DATASET_PATH


def main() -> None:
    """Command-line entry point for preparing local DF40 image datasets."""
    import argparse

    parser = argparse.ArgumentParser(description="Materialize the local DF40 inswap subset.")
    parser.add_argument("--max-pairs", type=int, default=DEFAULT_MAX_PAIRS)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--build-face-crops",
        choices=("paired", "unpaired", "both"),
        help="After DF40 subset, build face-crop datasets.",
    )
    args = parser.parse_args()
    ensure_df40_subset(max_pairs=args.max_pairs, force=args.force)
    if args.build_face_crops in ("paired", "both"):
        ensure_face_crop_dataset(force=args.force)
    if args.build_face_crops in ("unpaired", "both"):
        ensure_unpaired_face_crop_dataset(force=args.force)


if __name__ == "__main__":
    main()
