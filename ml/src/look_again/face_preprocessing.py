"""Shared face detection and crop logic for training and video evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image


FACE_CROP_SIZE = 256
FACE_CROP_MARGIN = 1.5
FACE_DETECTOR_VERSION = "opencv-haar-frontalface-v1"
DETECTOR_MAX_SIDE = 768


@dataclass(frozen=True)
class FaceCrop:
    image: Image.Image
    bbox: tuple[int, int, int, int]
    crop_bbox: tuple[int, int, int, int]


def crop_to_window(
    image: Image.Image,
    window: tuple[int, int, int, int],
) -> Image.Image:
    """Crop a source image to an explicit window and resize to the model size."""
    rgb_image = image.convert("RGB")
    left, top, right, bottom = window
    if not (0 <= left < right <= rgb_image.width and 0 <= top < bottom <= rgb_image.height):
        raise ValueError(f"Invalid face crop window {window} for image size {rgb_image.size}")
    return rgb_image.crop(window).resize(
        (FACE_CROP_SIZE, FACE_CROP_SIZE),
        Image.Resampling.LANCZOS,
    )


@lru_cache(maxsize=1)
def _face_cascade():
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    if cascade.empty():
        raise RuntimeError(f"Could not load OpenCV face cascade at {cascade_path}")
    return cascade


def crop_face(image: Image.Image) -> FaceCrop | None:
    """Detect the largest face and return its square crop plus source window.

    ``None`` means the detector found no face. Callers should exclude that image
    or break a video-frame sequence; they must not fall back to the full frame.
    """
    rgb_image = image.convert("RGB")
    rgb = np.asarray(rgb_image)
    height, width = rgb.shape[:2]

    scale = min(1.0, DETECTOR_MAX_SIDE / max(height, width))
    if scale < 1.0:
        detection_rgb = cv2.resize(
            rgb,
            (max(1, round(width * scale)), max(1, round(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
    else:
        detection_rgb = rgb

    gray = cv2.cvtColor(detection_rgb, cv2.COLOR_RGB2GRAY)
    boxes = _face_cascade().detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(24, 24),
    )
    if len(boxes) == 0:
        return None

    detection_x, detection_y, detection_w, detection_h = max(
        boxes,
        key=lambda box: int(box[2]) * int(box[3]),
    )
    x = max(0, round(float(detection_x) / scale))
    y = max(0, round(float(detection_y) / scale))
    face_w = max(1, round(float(detection_w) / scale))
    face_h = max(1, round(float(detection_h) / scale))
    face_cx = x + face_w / 2
    face_cy = y + face_h / 2

    # Keep the face plus surrounding context in a square. Shift the square at
    # image edges instead of padding, so both classes receive natural pixels.
    side = min(
        max(1, round(max(face_w, face_h) * FACE_CROP_MARGIN)),
        width,
        height,
    )
    left = min(max(0, round(face_cx - side / 2)), width - side)
    top = min(max(0, round(face_cy - side / 2)), height - side)
    right = left + side
    bottom = top + side

    crop_bbox = (left, top, right, bottom)
    return FaceCrop(
        image=crop_to_window(rgb_image, crop_bbox),
        bbox=(x, y, min(width, x + face_w), min(height, y + face_h)),
        crop_bbox=crop_bbox,
    )
