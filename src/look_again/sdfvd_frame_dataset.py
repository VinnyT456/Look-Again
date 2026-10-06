"""Extract and cache SDFVD face crops for frame-level training (video-level splits)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from datasets import Video, load_dataset
from PIL import Image
from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset

from look_again.dataset import SEED
from look_again.paths import DATA_DIR
from look_again.eval_benchmarks import (
    FAKE_LABEL,
    REAL_LABEL,
    SDFVD_DATASET_ID,
    _iter_video_frames,
    _sdfvd_label_to_int,
    _sdfvd_video_name,
)
from look_again.face_preprocessing import crop_face

CACHE_ROOT = DATA_DIR / "sdfvd_face_frames"
MANIFEST_NAME = "manifest.json"
MANIFEST_VERSION = 1


@dataclass(frozen=True)
class SDFVDFrameSample:
    relative_path: str
    label: int
    split: str
    video_index: int
    frame_index: int


class SDFVDFrameFolderDataset(Dataset):
    """Cached cropped frames; labels fake=0, real=1."""

    def __init__(
        self,
        samples: Sequence[SDFVDFrameSample],
        *,
        cache_root: Path,
        transform: Callable | None = None,
    ) -> None:
        self.cache_root = cache_root.expanduser().resolve()
        self.samples = list(samples)
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        sample = self.samples[index]
        path = self.cache_root / sample.relative_path
        image = Image.open(path).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        return image, float(sample.label)


def _load_manifest(cache_root: Path) -> dict | None:
    manifest_path = cache_root / MANIFEST_NAME
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != MANIFEST_VERSION:
        return None
    return manifest


def _samples_from_manifest(manifest: dict, *, split: str) -> list[SDFVDFrameSample]:
    rows: list[SDFVDFrameSample] = []
    for row in manifest["samples"]:
        if row["split"] != split:
            continue
        rows.append(
            SDFVDFrameSample(
                relative_path=row["relative_path"],
                label=int(row["label"]),
                split=row["split"],
                video_index=int(row["video_index"]),
                frame_index=int(row["frame_index"]),
            )
        )
    return rows


def ensure_sdfvd_frame_cache(
    *,
    cache_root: Path = CACHE_ROOT,
    val_video_fraction: float = 0.2,
    train_frame_stride: int = 2,
    max_train_frames_per_video: int = 48,
    seed: int = SEED,
    force: bool = False,
) -> dict:
    """Build cached face crops if missing. Split is by video, not by frame."""
    cache_root = cache_root.expanduser().resolve()
    if not force:
        manifest = _load_manifest(cache_root)
        if manifest is not None and manifest.get("samples"):
            return manifest

    if val_video_fraction <= 0 or val_video_fraction >= 0.5:
        raise ValueError("val_video_fraction must be between 0 and 0.5 for held-out eval")
    if train_frame_stride < 1 or max_train_frames_per_video < 1:
        raise ValueError("train_frame_stride and max_train_frames_per_video must be positive")

    cache_root.mkdir(parents=True, exist_ok=True)
    for split_name in ("train", "val"):
        for class_name in ("fake", "real"):
            (cache_root / split_name / class_name).mkdir(parents=True, exist_ok=True)

    hf_dataset = load_dataset(SDFVD_DATASET_ID, split="train")
    hf_dataset = hf_dataset.cast_column("video", Video(decode=False))

    video_rows: list[dict] = []
    for video_index, row in enumerate(hf_dataset):
        label = _sdfvd_label_to_int(row["label"])
        video_rows.append(
            {
                "video_index": video_index,
                "label": label,
                "video_name": _sdfvd_video_name(row, video_index),
                "hf_row": row,
            }
        )

    labels = [row["label"] for row in video_rows]
    train_videos, val_videos = train_test_split(
        video_rows,
        test_size=val_video_fraction,
        stratify=labels,
        random_state=seed,
    )
    split_by_index = {
        row["video_index"]: "train"
        for row in train_videos
    }
    for row in val_videos:
        split_by_index[row["video_index"]] = "val"

    sample_rows: list[dict] = []
    stats = {"train_faces": 0, "val_faces": 0, "skipped_no_face": 0}

    for video_index, row in enumerate(hf_dataset):
        split = split_by_index[video_index]
        label = _sdfvd_label_to_int(row["label"])
        class_dir = "fake" if label == FAKE_LABEL else "real"
        video_name = _sdfvd_video_name(row, video_index)
        saved_train = 0

        for frame_index, frame in _iter_video_frames(row["video"]):
            if split == "train":
                if frame_index % train_frame_stride != 0:
                    continue
                if saved_train >= max_train_frames_per_video:
                    break
            face = crop_face(frame)
            if face is None:
                stats["skipped_no_face"] += 1
                continue

            file_name = f"{video_name}_f{frame_index:05d}.jpg"
            relative_path = f"{split}/{class_dir}/{file_name}"
            output_path = cache_root / relative_path
            face.image.save(output_path, format="JPEG", quality=92)
            sample_rows.append(
                {
                    "relative_path": relative_path,
                    "label": label,
                    "split": split,
                    "video_index": video_index,
                    "frame_index": frame_index,
                    "video_name": video_name,
                }
            )
            if split == "train":
                saved_train += 1
                stats["train_faces"] += 1
            else:
                stats["val_faces"] += 1

        if (video_index + 1) % 10 == 0 or video_index + 1 == len(hf_dataset):
            print(
                f"SDFVD cache: processed {video_index + 1}/{len(hf_dataset)} videos | "
                f"train_faces={stats['train_faces']} val_faces={stats['val_faces']} "
                f"skipped_no_face={stats['skipped_no_face']}",
                flush=True,
            )

    manifest = {
        "version": MANIFEST_VERSION,
        "dataset_id": SDFVD_DATASET_ID,
        "cache_root": str(cache_root),
        "seed": seed,
        "val_video_fraction": val_video_fraction,
        "train_frame_stride": train_frame_stride,
        "max_train_frames_per_video": max_train_frames_per_video,
        "train_videos": len(train_videos),
        "val_videos": len(val_videos),
        "samples": sample_rows,
        **stats,
    }
    (cache_root / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def build_sdfvd_frame_datasets(
    *,
    cache_root: Path = CACHE_ROOT,
    transform_train: Callable | None,
    transform_eval: Callable | None,
    val_video_fraction: float = 0.2,
    train_frame_stride: int = 2,
    max_train_frames_per_video: int = 48,
    seed: int = SEED,
    force_rebuild_cache: bool = False,
) -> tuple[SDFVDFrameFolderDataset, SDFVDFrameFolderDataset, dict]:
    manifest = ensure_sdfvd_frame_cache(
        cache_root=cache_root,
        val_video_fraction=val_video_fraction,
        train_frame_stride=train_frame_stride,
        max_train_frames_per_video=max_train_frames_per_video,
        seed=seed,
        force=force_rebuild_cache,
    )
    cache_root = cache_root.expanduser().resolve()
    train_samples = _samples_from_manifest(manifest, split="train")
    val_samples = _samples_from_manifest(manifest, split="val")
    if not train_samples or not val_samples:
        raise ValueError("SDFVD frame cache is empty after extraction")

    metadata = {
        "role": "sdfvd_video_frame_cache",
        "dataset_id": SDFVD_DATASET_ID,
        "cache_root": str(cache_root),
        "train_frames": len(train_samples),
        "val_frames": len(val_samples),
        "train_videos": manifest["train_videos"],
        "val_videos": manifest["val_videos"],
        "val_video_fraction": val_video_fraction,
    }
    return (
        SDFVDFrameFolderDataset(train_samples, cache_root=cache_root, transform=transform_train),
        SDFVDFrameFolderDataset(val_samples, cache_root=cache_root, transform=transform_eval),
        metadata,
    )
