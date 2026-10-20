"""The CommunityForensics ViT + rich probe with its heatmap, as the apps ship it."""

from __future__ import annotations

import io
import threading
from pathlib import Path

import numpy as np
import torch
from PIL import Image, UnidentifiedImageError

from look_again.community_forensics_vit_probe import (
    DEFAULT_COREML_DIR,
    CommunityForensicsViTProbeHeatmap,
    load_community_forensics_vit,
    load_probe_module_from_npz,
)
from look_again.serve.schemas import ClassifyResponse, HeatmapOut

WEIGHTS_PATH = DEFAULT_COREML_DIR / "community_forensics_vit_rich_probe_weights.npz"
"""Same cut-off as the iOS and Android apps."""
THRESHOLD = 0.5


class UnreadableImage(ValueError):
    pass


class Detector:
    def __init__(self, weights_path: Path = WEIGHTS_PATH, device: str = "cpu") -> None:
        self.device = torch.device(device)
        self.module = load_probe_module_from_npz(weights_path, self.device, CommunityForensicsViTProbeHeatmap)
        _, self.processor = load_community_forensics_vit(self.device)
        # One forward pass at a time keeps memory flat under concurrent requests.
        self._lock = threading.Lock()

    def warm_up(self) -> None:
        self.classify_image(Image.new("RGB", (64, 64)))

    def classify_bytes(self, data: bytes) -> ClassifyResponse:
        try:
            image = Image.open(io.BytesIO(data))
            image.load()
        except (UnidentifiedImageError, OSError) as error:
            raise UnreadableImage(str(error)) from error
        return self.classify_image(image.convert("RGB"))

    def classify_image(self, image: Image.Image) -> ClassifyResponse:
        pixels = self.processor(images=image, return_tensors="pt")["pixel_values"].float().to(self.device)
        with self._lock, torch.inference_mode():
            prob, patch_map = self.module(pixels)
        fake_prob = float(np.clip(float(prob.reshape(-1)[0]), 0.0, 1.0))
        is_fake = fake_prob >= THRESHOLD
        values = patch_map.reshape(-1).cpu().numpy().astype(float).tolist()
        return ClassifyResponse(
            verdict="ai" if is_fake else "real",
            confidence=fake_prob if is_fake else 1 - fake_prob,
            fake_prob=fake_prob,
            heatmap=HeatmapOut(values=values),
        )
