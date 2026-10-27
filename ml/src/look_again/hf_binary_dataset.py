"""Download Hugging Face image datasets into fake/ + real/ folders for ViT fine-tuning."""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

from PIL import Image
from tqdm import tqdm

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# Parquet view on HF has null labels; use imagefolder paths FAKE/ and REAL/.
CIFAKE_HF_ID = "batgre/CIFAKE"
CIFAKE_HF_IMAGE_ROOT = "hf://datasets/batgre/CIFAKE/CIFAKE"

SO_FAKE_HF_ID = "saberzl/So-Fake-Set"
SO_FAKE_FAKE_LABELS = frozenset({"fake", "full_synthetic", "tampered", 1, "1"})
SO_FAKE_REAL_LABELS = frozenset({"real", 0, "0"})

# Ternary So-Fake: 0=real, 1=full_synthetic (gen-AI), 2=tampered (edited real).
SO_FAKE_TERTIARY_REAL_LABELS = SO_FAKE_REAL_LABELS
SO_FAKE_TERTIARY_SYNTHETIC_LABELS = frozenset({"fake", "full_synthetic", 1, "1"})
SO_FAKE_TERTIARY_TAMPERED_LABELS = frozenset({"tampered", 2, "2"})

# HF ClassLabel names are usually ["fake", "real"] → index 0 = fake, 1 = real.
DEFAULT_FAKE_LABELS = frozenset({"fake", "0", 0})
DEFAULT_REAL_LABELS = frozenset({"real", "1", 1})


def _label_to_tertiary(
    value: Any,
    *,
    real_labels: frozenset[Any],
    synthetic_labels: frozenset[Any],
    tampered_labels: frozenset[Any],
) -> int:
    normalized = value.strip().lower() if isinstance(value, str) else value
    if normalized in real_labels or value in real_labels:
        return 0
    if normalized in synthetic_labels or value in synthetic_labels:
        return 1
    if normalized in tampered_labels or value in tampered_labels:
        return 2
    raise ValueError(f"Unrecognized label: {value!r}")


def _label_to_binary(value: Any, *, fake_labels: frozenset[Any], real_labels: frozenset[Any]) -> int:
    normalized = value
    if isinstance(value, str):
        normalized = value.strip().lower()
    if normalized in fake_labels or value in fake_labels:
        return 1
    if normalized in real_labels or value in real_labels:
        return 0
    raise ValueError(f"Unrecognized label: {value!r}")


def _load_hf_split(
    *,
    dataset_id: str,
    split: str,
    streaming: bool,
    config: str | None,
) -> Any:
    """Load a split; fall back to parquet shards when the repo has no loading script."""
    from datasets import load_dataset
    from datasets.exceptions import DataFilesNotFoundError

    load_kwargs: dict[str, Any] = {"path": dataset_id, "split": split, "streaming": streaming}
    if config is not None:
        load_kwargs["name"] = config
    try:
        return load_dataset(**load_kwargs)
    except DataFilesNotFoundError:
        parquet_glob = f"hf://datasets/{dataset_id}/data/{split}-*.parquet"
        return load_dataset(
            "parquet",
            data_files={split: parquet_glob},
            split=split,
            streaming=streaming,
        )


def _export_caps_met(
    counts: dict[int, int],
    cap_real: int | None,
    cap_fake: int | None,
    export_real: bool,
    export_fake: bool,
) -> bool:
    real_done = not export_real or (cap_real is not None and counts[0] >= cap_real)
    fake_done = not export_fake or (cap_fake is not None and counts[1] >= cap_fake)
    return real_done and fake_done


def _export_tertiary_caps_met(
    counts: dict[int, int],
    *,
    cap_real: int,
    cap_synthetic: int,
    cap_tampered: int,
    export_real: bool,
    export_synthetic: bool,
    export_tampered: bool,
) -> bool:
    real_done = not export_real or counts[0] >= cap_real
    synthetic_done = not export_synthetic or counts[1] >= cap_synthetic
    tampered_done = not export_tampered or counts[2] >= cap_tampered
    return real_done and synthetic_done and tampered_done


def is_readable_image(path: Path) -> bool:
    """Return False for missing, empty, or truncated image files."""
    if not path.is_file() or path.stat().st_size < 16:
        return False
    try:
        with Image.open(path) as im:
            im.load()
            return im.size[0] > 0 and im.size[1] > 0
    except OSError:
        return False


def _save_image(image: Any, path: Path) -> None:
    if isinstance(image, Image.Image):
        pil = image
        if pil.mode == "P":
            pil = pil.convert("RGBA")
        pil = pil.convert("RGB")
    else:
        pil = Image.open(image)
        if pil.mode == "P":
            pil = pil.convert("RGBA")
        pil = pil.convert("RGB")
    path.parent.mkdir(parents=True, exist_ok=True)
    pil.save(path, format="PNG")
    if not is_readable_image(path):
        path.unlink(missing_ok=True)
        raise OSError(f"Wrote corrupt image: {path}")


def _cifake_shards(split: str, export_fake: bool, export_real: bool) -> list[tuple[str, str, int]]:
    """batgre/CIFAKE on HF: train=REAL only; test=FAKE+REAL (parquet labels are null)."""
    shards: list[tuple[str, str, int]] = []
    use_train = split in ("train", "all")
    use_test = split in ("test", "all")
    if export_real:
        if use_train:
            shards.append(("train", "REAL", 0))
        if use_test:
            shards.append(("test", "REAL", 0))
    if export_fake and use_test:
        shards.append(("test", "FAKE", 1))
    return shards


def _materialize_cifake_split(
    *,
    split: str,
    output_root: Path,
    fake_dir: str,
    real_dir: str,
    cap_fake: int | None,
    cap_real: int | None,
    streaming: bool,
    filename_prefix: str,
    export_fake: bool,
    export_real: bool,
) -> tuple[dict[int, int], int]:
    from datasets import load_dataset

    counts = {0: 0, 1: 0}
    written = 0
    for hf_split, class_name, label in _cifake_shards(split, export_fake, export_real):
        cap = cap_fake if label == 1 else cap_real
        url = f"{CIFAKE_HF_IMAGE_ROOT}/{hf_split}/{class_name}/*"
        key = f"{hf_split}_{class_name.lower()}"
        dataset = load_dataset(
            "imagefolder",
            data_files={key: url},
            split=key,
            streaming=streaming,
        )
        iterator = dataset
        if not streaming:
            iterator = tqdm(dataset, desc=f"CIFAKE {hf_split}/{class_name}", unit="img")
        for index, row in enumerate(iterator):
            if cap is not None and counts[label] >= cap:
                break
            stem = f"{filename_prefix}cifake_{hf_split}_{class_name.lower()}_{index:06d}"
            folder = fake_dir if label == 1 else real_dir
            out_path = output_root / folder / f"{stem}.jpg"
            if out_path.exists():
                if is_readable_image(out_path):
                    counts[label] += 1
                    written += 1
                    continue
                out_path.unlink(missing_ok=True)
            try:
                _save_image(row["image"], out_path)
            except OSError:
                continue
            counts[label] += 1
            written += 1
        if _export_caps_met(counts, cap_real, cap_fake, export_real, export_fake):
            break
    return counts, written


def materialize_hf_split(
    *,
    dataset_id: str,
    split: str,
    output_root: Path,
    fake_dir: str = "fake",
    real_dir: str = "real",
    label_field: str = "label",
    image_field: str = "image",
    filename_field: str | None = None,
    fake_labels: Iterable[Any] = DEFAULT_FAKE_LABELS,
    real_labels: Iterable[Any] = DEFAULT_REAL_LABELS,
    max_per_class: int | None = None,
    max_fake_per_class: int | None = None,
    max_real_per_class: int | None = None,
    streaming: bool = False,
    config: str | None = None,
    filename_prefix: str = "",
    export_fake: bool = True,
    export_real: bool = True,
) -> dict[str, Any]:
    """Write one HF split to ``output_root/{fake,real}/`` and return a small manifest."""
    cap_fake = max_fake_per_class if max_fake_per_class is not None else max_per_class
    cap_real = max_real_per_class if max_real_per_class is not None else max_per_class

    if dataset_id == CIFAKE_HF_ID:
        counts, written = _materialize_cifake_split(
            split=split,
            output_root=output_root,
            fake_dir=fake_dir,
            real_dir=real_dir,
            cap_fake=cap_fake,
            cap_real=cap_real,
            streaming=streaming,
            filename_prefix=filename_prefix,
            export_fake=export_fake,
            export_real=export_real,
        )
        manifest = {
            "dataset_id": dataset_id,
            "split": split,
            "output_root": str(output_root.resolve()),
            "written": written,
            "real": counts[0],
            "fake": counts[1],
            "streaming": streaming,
            "loader": "imagefolder",
        }
        output_root.mkdir(parents=True, exist_ok=True)
        slug = dataset_id.replace("/", "__")
        (output_root / f"manifest_{slug}_{split}.json").write_text(json.dumps(manifest, indent=2) + "\n")
        return manifest

    fake_set = frozenset(fake_labels)
    real_set = frozenset(real_labels)
    dataset = _load_hf_split(
        dataset_id=dataset_id,
        split=split,
        streaming=streaming,
        config=config,
    )

    counts = {0: 0, 1: 0}
    written = 0
    iterator = dataset
    if not streaming:
        iterator = tqdm(dataset, desc=f"export {dataset_id}:{split}", unit="img")

    for index, row in enumerate(iterator):
        raw_label = row[label_field]
        if raw_label is None:
            continue
        label = _label_to_binary(raw_label, fake_labels=fake_set, real_labels=real_set)
        if label == 1 and not export_fake:
            continue
        if label == 0 and not export_real:
            continue
        cap = cap_fake if label == 1 else cap_real
        if cap is not None and counts[label] >= cap:
            continue
        if filename_field and row.get(filename_field):
            name = Path(str(row[filename_field])).name
        else:
            ext = ".png"
            name = f"{split}_{index:06d}{ext}"
        stem = Path(name).stem
        suffix = Path(name).suffix.lower() or ".png"
        if suffix not in IMAGE_EXTENSIONS:
            suffix = ".png"
        if filename_prefix:
            stem = f"{filename_prefix}{stem}"
        folder = fake_dir if label == 1 else real_dir
        out_path = output_root / folder / f"{stem}{suffix}"
        if out_path.exists():
            if is_readable_image(out_path):
                counts[label] += 1
                written += 1
                if _export_caps_met(counts, cap_real, cap_fake, export_real, export_fake):
                    break
                continue
            out_path.unlink(missing_ok=True)
        try:
            _save_image(row[image_field], out_path)
        except OSError:
            continue
        counts[label] += 1
        written += 1
        if _export_caps_met(counts, cap_real, cap_fake, export_real, export_fake):
            break

    manifest = {
        "dataset_id": dataset_id,
        "split": split,
        "output_root": str(output_root.resolve()),
        "written": written,
        "real": counts[0],
        "fake": counts[1],
        "streaming": streaming,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    slug = dataset_id.replace("/", "__")
    manifest_path = output_root / f"manifest_{slug}_{split}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def open_hf_row_iterator(
    *,
    dataset_id: str,
    split: str,
    streaming: bool = True,
    config: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Return a row iterator for chunked export (streaming recommended)."""
    dataset = _load_hf_split(
        dataset_id=dataset_id,
        split=split,
        streaming=streaming,
        config=config,
    )
    return iter(dataset)


_HF_ROW_DECODE_ERRORS = (OSError, struct.error, ValueError, TypeError, RuntimeError, KeyError)


def next_hf_row_safe(
    row_iterator: Iterator[dict[str, Any]],
    *,
    stats: dict[str, int],
) -> dict[str, Any] | None:
    """Read the next HF row, skipping truncated/corrupt image decode failures."""
    while True:
        try:
            row = next(row_iterator)
            stats["stream_rows_seen"] = stats.get("stream_rows_seen", 0) + 1
            return row
        except StopIteration:
            return None
        except _HF_ROW_DECODE_ERRORS as exc:
            stats["stream_rows_seen"] = stats.get("stream_rows_seen", 0) + 1
            skipped = stats.get("skipped_bad_rows", 0) + 1
            stats["skipped_bad_rows"] = skipped
            if skipped <= 5 or skipped % 50 == 0:
                tqdm.write(f"skip bad HF row ({skipped}): {exc}", file=sys.stderr)
            continue


def skip_hf_stream_rows(
    row_iterator: Iterator[dict[str, Any]],
    count: int,
    *,
    stats: dict[str, int],
    desc: str = "resume HF stream",
) -> Iterator[dict[str, Any]]:
    """Advance the HF iterator by ``count`` rows (including skipped corrupt rows)."""
    if count <= 0:
        return row_iterator
    for _ in tqdm(range(count), desc=desc, unit="row", file=sys.stderr):
        if next_hf_row_safe(row_iterator, stats=stats) is None:
            break
    return row_iterator


def list_hf_parquet_shards(dataset_id: str, split: str) -> list[str]:
    """Sorted repo-relative paths for ``data/{split}-*.parquet`` shards."""
    from huggingface_hub import HfApi

    prefix = f"data/{split}-"
    files = sorted(
        path
        for path in HfApi().list_repo_files(dataset_id, repo_type="dataset")
        if path.startswith(prefix) and path.endswith(".parquet")
    )
    if not files:
        raise FileNotFoundError(f"No parquet shards under {prefix} in {dataset_id}")
    return files


class ParquetShardRowIterator:
    """Walk one parquet shard at a time (avoids early EOF on multi-shard HF streams)."""

    def __init__(
        self,
        dataset_id: str,
        split: str,
        shards: list[str],
        *,
        start_shard: int,
        stats: dict[str, int],
    ) -> None:
        self.dataset_id = dataset_id
        self.split = split
        self.shards = shards
        self.stats = stats
        self.shard_index = max(0, min(start_shard, len(shards)))
        self.stats["parquet_shard_total"] = len(shards)
        self.stats["parquet_shard_index"] = self.shard_index
        self._inner: Iterator[dict[str, Any]] | None = None
        self._open_shard()

    def _open_shard(self) -> None:
        if self.shard_index >= len(self.shards):
            self._inner = None
            return
        shard_path = self.shards[self.shard_index]
        url = f"hf://datasets/{self.dataset_id}/{shard_path}"
        from datasets import load_dataset

        dataset = load_dataset(
            "parquet",
            data_files={self.split: url},
            split=self.split,
            streaming=True,
        )
        self._inner = iter(dataset)
        tqdm.write(
            f"parquet shard {self.shard_index + 1}/{len(self.shards)}: {shard_path}",
            file=sys.stderr,
        )

    def __iter__(self) -> ParquetShardRowIterator:
        return self

    def __next__(self) -> dict[str, Any]:
        while True:
            if self._inner is None:
                raise StopIteration
            row = next_hf_row_safe(self._inner, stats=self.stats)
            if row is not None:
                return row
            self.shard_index += 1
            self.stats["parquet_shard_index"] = self.shard_index
            self._open_shard()
            if self._inner is None:
                raise StopIteration


def open_sofake_parquet_shard_iterator(
    *,
    split: str,
    stats: dict[str, int],
    start_shard: int = 0,
    dataset_id: str = SO_FAKE_HF_ID,
) -> ParquetShardRowIterator:
    shards = list_hf_parquet_shards(dataset_id, split)
    return ParquetShardRowIterator(
        dataset_id,
        split,
        shards,
        start_shard=start_shard,
        stats=stats,
    )


def materialize_hf_chunk_from_iterator(
    row_iterator: Iterator[dict[str, Any]],
    *,
    output_root: Path,
    label_field: str = "label",
    image_field: str = "image",
    filename_field: str | None = "filename",
    fake_labels: Iterable[Any] = SO_FAKE_FAKE_LABELS,
    real_labels: Iterable[Any] = SO_FAKE_REAL_LABELS,
    cap_fake: int,
    cap_real: int,
    filename_prefix: str = "",
    fake_dir: str = "fake",
    real_dir: str = "real",
    export_fake: bool = True,
    export_real: bool = True,
    desc: str = "export chunk",
    stream_stats: dict[str, int] | None = None,
) -> tuple[dict[str, Any], Iterator[dict[str, Any]]]:
    """Write up to ``cap_fake`` / ``cap_real`` images from ``row_iterator``, then return it."""
    fake_set = frozenset(fake_labels)
    real_set = frozenset(real_labels)
    counts = {0: 0, 1: 0}
    written = 0
    skipped_labels = 0
    skipped_save = 0
    stats = stream_stats if stream_stats is not None else {}
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / fake_dir).mkdir(parents=True, exist_ok=True)
    (output_root / real_dir).mkdir(parents=True, exist_ok=True)

    target = 0
    if export_fake and cap_fake > 0:
        target += cap_fake
    if export_real and cap_real > 0:
        target += cap_real
    pbar = tqdm(total=target or None, desc=desc, unit="img", file=sys.stderr)

    while True:
        if _export_caps_met(counts, cap_real if export_real else 0, cap_fake if export_fake else 0, export_real, export_fake):
            break
        row = next_hf_row_safe(row_iterator, stats=stats)
        if row is None:
            break
        raw_label = row.get(label_field)
        if raw_label is None:
            continue
        try:
            label = _label_to_binary(raw_label, fake_labels=fake_set, real_labels=real_set)
        except ValueError:
            skipped_labels += 1
            continue
        if label == 1 and not export_fake:
            continue
        if label == 0 and not export_real:
            continue
        cap = cap_fake if label == 1 else cap_real
        if counts[label] >= cap:
            continue

        if filename_field and row.get(filename_field):
            name = Path(str(row[filename_field])).name
        else:
            name = f"row_{written:06d}.png"
        stem = Path(name).stem
        suffix = Path(name).suffix.lower() or ".png"
        if suffix not in IMAGE_EXTENSIONS:
            suffix = ".png"
        if filename_prefix:
            stem = f"{filename_prefix}{stem}"
        folder = fake_dir if label == 1 else real_dir
        out_path = output_root / folder / f"{stem}{suffix}"
        if out_path.exists():
            if is_readable_image(out_path):
                counts[label] += 1
                written += 1
                pbar.update(1)
                continue
            out_path.unlink(missing_ok=True)
        try:
            _save_image(row[image_field], out_path)
        except (OSError, KeyError, TypeError):
            skipped_save += 1
            continue
        counts[label] += 1
        written += 1
        pbar.update(1)

    pbar.close()
    manifest = {
        "output_root": str(output_root.resolve()),
        "written": written,
        "real": counts[0],
        "fake": counts[1],
        "skipped_labels": skipped_labels,
        "skipped_save": skipped_save,
        "stream_rows_seen": stats.get("stream_rows_seen", 0),
        "skipped_bad_rows": stats.get("skipped_bad_rows", 0),
        "cap_fake": cap_fake,
        "cap_real": cap_real,
    }
    return manifest, row_iterator


def materialize_hf_chunk_tertiary_from_iterator(
    row_iterator: Iterator[dict[str, Any]],
    *,
    output_root: Path,
    label_field: str = "label",
    image_field: str = "image",
    filename_field: str | None = "filename",
    real_labels: Iterable[Any] = SO_FAKE_TERTIARY_REAL_LABELS,
    synthetic_labels: Iterable[Any] = SO_FAKE_TERTIARY_SYNTHETIC_LABELS,
    tampered_labels: Iterable[Any] = SO_FAKE_TERTIARY_TAMPERED_LABELS,
    cap_real: int,
    cap_synthetic: int,
    cap_tampered: int,
    filename_prefix: str = "",
    real_dir: str = "real",
    synthetic_dir: str = "fake",
    tampered_dir: str = "tampered",
    export_real: bool = True,
    export_synthetic: bool = True,
    export_tampered: bool = True,
    desc: str = "export chunk",
    stream_stats: dict[str, int] | None = None,
) -> tuple[dict[str, Any], Iterator[dict[str, Any]]]:
    """Write up to ``cap_*`` images per class (0=real, 1=synthetic, 2=tampered)."""
    real_set = frozenset(real_labels)
    synthetic_set = frozenset(synthetic_labels)
    tampered_set = frozenset(tampered_labels)
    counts = {0: 0, 1: 0, 2: 0}
    dir_by_label = {0: real_dir, 1: synthetic_dir, 2: tampered_dir}
    cap_by_label = {0: cap_real, 1: cap_synthetic, 2: cap_tampered}
    export_by_label = {0: export_real, 1: export_synthetic, 2: export_tampered}
    written = 0
    skipped_labels = 0
    skipped_save = 0
    stats = stream_stats if stream_stats is not None else {}
    output_root.mkdir(parents=True, exist_ok=True)
    for folder in (real_dir, synthetic_dir, tampered_dir):
        (output_root / folder).mkdir(parents=True, exist_ok=True)

    target = sum(
        cap
        for label, cap in cap_by_label.items()
        if export_by_label[label] and cap > 0
    )
    pbar = tqdm(total=target or None, desc=desc, unit="img", file=sys.stderr)

    while True:
        if _export_tertiary_caps_met(
            counts,
            cap_real=cap_real,
            cap_synthetic=cap_synthetic,
            cap_tampered=cap_tampered,
            export_real=export_real,
            export_synthetic=export_synthetic,
            export_tampered=export_tampered,
        ):
            break
        row = next_hf_row_safe(row_iterator, stats=stats)
        if row is None:
            break
        raw_label = row.get(label_field)
        if raw_label is None:
            continue
        try:
            label = _label_to_tertiary(
                raw_label,
                real_labels=real_set,
                synthetic_labels=synthetic_set,
                tampered_labels=tampered_set,
            )
        except ValueError:
            skipped_labels += 1
            continue
        if not export_by_label[label]:
            continue
        if counts[label] >= cap_by_label[label]:
            continue

        if filename_field and row.get(filename_field):
            name = Path(str(row[filename_field])).name
        else:
            name = f"row_{written:06d}.png"
        stem = Path(name).stem
        suffix = Path(name).suffix.lower() or ".png"
        if suffix not in IMAGE_EXTENSIONS:
            suffix = ".png"
        if filename_prefix:
            stem = f"{filename_prefix}{stem}"
        folder = dir_by_label[label]
        out_path = output_root / folder / f"{stem}{suffix}"
        if out_path.exists():
            if is_readable_image(out_path):
                counts[label] += 1
                written += 1
                pbar.update(1)
                continue
            out_path.unlink(missing_ok=True)
        try:
            _save_image(row[image_field], out_path)
        except (OSError, KeyError, TypeError):
            skipped_save += 1
            continue
        counts[label] += 1
        written += 1
        pbar.update(1)

    pbar.close()
    manifest = {
        "output_root": str(output_root.resolve()),
        "written": written,
        "real": counts[0],
        "synthetic": counts[1],
        "tampered": counts[2],
        "skipped_labels": skipped_labels,
        "skipped_save": skipped_save,
        "stream_rows_seen": stats.get("stream_rows_seen", 0),
        "skipped_bad_rows": stats.get("skipped_bad_rows", 0),
        "cap_real": cap_real,
        "cap_synthetic": cap_synthetic,
        "cap_tampered": cap_tampered,
    }
    return manifest, row_iterator
