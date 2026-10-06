"""Visualize paired vs unpaired DF40 face crops for one swap pair."""

from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw


from look_again.df40_subset import DATASET_PATH, LEGACY_FACE_CROP_DATASET_PATH, _safe_dataset_image_path, _scale_crop_window
from look_again.face_preprocessing import crop_face, crop_to_window

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
PREVIEW_SIZE = (320, 320)
CROP_PREVIEW = 160


def _draw_window(image: Image.Image, window: tuple[int, int, int, int], color: str) -> Image.Image:
    preview = image.copy()
    preview.thumbnail(PREVIEW_SIZE, Image.Resampling.LANCZOS)
    scale_x = preview.width / image.width
    scale_y = preview.height / image.height
    left, top, right, bottom = window
    box = (
        round(left * scale_x),
        round(top * scale_y),
        round(right * scale_x),
        round(bottom * scale_y),
    )
    draw = ImageDraw.Draw(preview)
    draw.rectangle(box, outline=color, width=3)
    return preview


def _parse_window(text: str) -> tuple[int, int, int, int]:
    parts = [int(part) for part in text.split(",")]
    if len(parts) != 4:
        raise ValueError(f"Expected four window values, got {text!r}")
    return parts[0], parts[1], parts[2], parts[3]


def _crop_preview(crop: Image.Image) -> Image.Image:
    preview = crop.copy()
    preview.thumbnail((CROP_PREVIEW, CROP_PREVIEW), Image.Resampling.LANCZOS)
    return preview


def _label(image: Image.Image, text: str) -> Image.Image:
    banner = 28
    canvas = Image.new("RGB", (image.width, image.height + banner), "white")
    canvas.paste(image, (0, banner))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 6), text, fill="black")
    return canvas


def _hstack(images: list[Image.Image], gap: int = 12) -> Image.Image:
    width = sum(image.width for image in images) + gap * (len(images) - 1)
    height = max(image.height for image in images)
    canvas = Image.new("RGB", (width, height), "white")
    x = 0
    for image in images:
        canvas.paste(image, (x, 0))
        x += image.width + gap
    return canvas


def main() -> None:
    metadata_path = LEGACY_FACE_CROP_DATASET_PATH / "metadata.csv"
    if not metadata_path.is_file():
        metadata_path = DATASET_PATH / "metadata.csv"
    if not metadata_path.is_file():
        raise FileNotFoundError("Need DF40_face_crops/metadata.csv or DF40/metadata.csv")

    metadata_rows: list[dict[str, str]] = []
    with metadata_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            metadata_rows.append(dict(row))

    row = None
    fake_image = real_image = None
    real_detect = fake_detect = None
    paired_fake_window = None
    for candidate in metadata_rows:
        fake_rel = candidate.get("original_fake_file") or candidate["fake_file"]
        real_rel = candidate.get("original_real_file") or candidate["real_file"]
        fake_path = _safe_dataset_image_path(DATASET_PATH, fake_rel)
        real_path = _safe_dataset_image_path(DATASET_PATH, real_rel)
        if not fake_path.is_file() or not real_path.is_file():
            continue
        fake_image = Image.open(fake_path).convert("RGB")
        real_image = Image.open(real_path).convert("RGB")
        real_detect = crop_face(real_image)
        fake_detect = crop_face(fake_image)
        if real_detect is None or fake_detect is None:
            continue
        paired_fake_window = _scale_crop_window(
            real_detect.crop_bbox,
            real_image.size,
            fake_image.size,
        )
        row = candidate
        break

    if row is None or fake_image is None or real_image is None or real_detect is None or fake_detect is None:
        raise RuntimeError("Could not find a DF40 pair with detectable faces on full frames")

    paired_real_crop_path = LEGACY_FACE_CROP_DATASET_PATH / row["real_file"]
    paired_fake_crop_path = LEGACY_FACE_CROP_DATASET_PATH / row["fake_file"]
    if paired_real_crop_path.is_file() and paired_fake_crop_path.is_file():
        paired_real_crop = Image.open(paired_real_crop_path).convert("RGB")
        paired_fake_crop = Image.open(paired_fake_crop_path).convert("RGB")
        if row.get("real_crop_window"):
            paired_real_window = _parse_window(row["real_crop_window"])
        else:
            paired_real_window = real_detect.crop_bbox
        if row.get("fake_crop_window"):
            paired_fake_window = _parse_window(row["fake_crop_window"])
        elif paired_fake_window is None:
            paired_fake_window = fake_detect.crop_bbox
    else:
        if paired_fake_window is None:
            raise RuntimeError(
                "Need DF40_face_crops/ paired images or matching aspect ratio to build paired example"
            )
        paired_real_crop = real_detect.image
        paired_fake_crop = crop_to_window(fake_image, paired_fake_window)
        paired_real_window = real_detect.crop_bbox

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paired_real_crop.save(OUTPUT_DIR / "paired_real_crop.jpg", quality=92)
    paired_fake_crop.save(OUTPUT_DIR / "paired_fake_crop.jpg", quality=92)
    fake_detect.image.save(OUTPUT_DIR / "unpaired_fake_crop.jpg", quality=92)
    real_detect.image.save(OUTPUT_DIR / "unpaired_real_crop.jpg", quality=92)

    paired_row = _hstack(
        [
            _label(_draw_window(real_image, paired_real_window, "#0077cc"), "Real + anchor window"),
            _label(_draw_window(fake_image, paired_fake_window, "#0077cc"), "Fake + shared window"),
            _label(_crop_preview(paired_real_crop), "Paired real crop"),
            _label(_crop_preview(paired_fake_crop), "Paired fake crop"),
        ]
    )
    unpaired_row = _hstack(
        [
            _label(_draw_window(real_image, real_detect.crop_bbox, "#cc4400"), "Real detect"),
            _label(_draw_window(fake_image, fake_detect.crop_bbox, "#cc4400"), "Fake detect"),
            _label(_crop_preview(real_detect.image), "Unpaired real crop"),
            _label(_crop_preview(fake_detect.image), "Unpaired fake crop"),
        ]
    )

    title = Image.new("RGB", (max(paired_row.width, unpaired_row.width), 36), "white")
    ImageDraw.Draw(title).text(
        (8, 8),
        f"DF40 pair id={row['id']} | Paired = real anchors window; "
        f"Unpaired = separate detect per image (video path)",
        fill="black",
    )
    comparison = Image.new(
        "RGB",
        (
            max(paired_row.width, unpaired_row.width),
            title.height + paired_row.height + unpaired_row.height + 16,
        ),
        "white",
    )
    comparison.paste(title, (0, 0))
    comparison.paste(paired_row, (0, title.height + 4))
    comparison.paste(unpaired_row, (0, title.height + paired_row.height + 12))
    comparison.save(OUTPUT_DIR / "comparison.png")
    print(f"Wrote examples to {OUTPUT_DIR}/")
    print("  comparison.png  — start here")
    print("  paired_*_crop.jpg, unpaired_*_crop.jpg")


if __name__ == "__main__":
    main()
