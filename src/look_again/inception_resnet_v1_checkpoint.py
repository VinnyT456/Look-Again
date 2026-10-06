"""Load Inception-ResNet-v1 (140K) checkpoints for shared neural eval."""

from __future__ import annotations

import sys
from pathlib import Path

import torch
import torch.nn as nn
from torchvision import transforms

from look_again.paths import CHECKPOINT_DIR
INCEPTION_RUN_NAME = "inception_resnet_v1_140k"
INCEPTION_MODEL_NAME = "inception_resnet_v1"
IMAGE_SIZE = 160

from look_again.models.inception_resnet_v1 import InceptionResnetV1  # noqa: E402


class FixedFaceNetStandardization:
    """Apply FaceNet's fixed (pixel - 127.5) / 128 RGB normalization."""

    def __call__(self, image: torch.Tensor) -> torch.Tensor:
        return (image * 255.0 - 127.5) / 128.0


class InceptionResnetV1BinaryWrapper(nn.Module):
    """Map two-class logits to one logit: real (1) minus fake (0)."""

    def __init__(self, backbone: InceptionResnetV1) -> None:
        super().__init__()
        self.backbone = backbone
        self.uses_facenet_standardization = True
        self.default_cfg = {
            "input_size": (3, IMAGE_SIZE, IMAGE_SIZE),
            "mean": (0.5, 0.5, 0.5),
            "std": (1.0, 1.0, 1.0),
        }

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        logits = self.backbone(x)
        return logits[:, 1:2] - logits[:, 0:1]


def build_facenet_test_transform(model) -> transforms.Compose:
    input_size = tuple(model.default_cfg.get("input_size", (3, IMAGE_SIZE, IMAGE_SIZE))[-2:])
    return transforms.Compose(
        [
            transforms.Resize(input_size, antialias=True),
            transforms.ToTensor(),
            FixedFaceNetStandardization(),
        ]
    )


def inception_checkpoint_path(run_name: str) -> Path:
    return CHECKPOINT_DIR / f"{run_name}_best.pt"


def load_inception_resnet_v1_checkpoint(
    run_name: str,
    *,
    device: torch.device | None = None,
) -> tuple[nn.Module, dict]:
    checkpoint_path = inception_checkpoint_path(run_name)
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"No best checkpoint found: {checkpoint_path}")

    if device is None:
        if torch.cuda.is_available():
            device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            device = torch.device("mps")
        else:
            device = torch.device("cpu")

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    pretrained = checkpoint.get("pretrained", "vggface2")
    if pretrained == "none":
        pretrained = None
    backbone = InceptionResnetV1(
        pretrained=pretrained,
        classify=True,
        num_classes=2,
    )
    model = InceptionResnetV1BinaryWrapper(backbone)
    model.backbone.load_state_dict(checkpoint["state_dict"])
    model = model.to(device)

    normalized = dict(checkpoint)
    normalized.setdefault("run_name", run_name)
    normalized.setdefault("model_name", INCEPTION_MODEL_NAME)
    if "best_test_accuracy" not in normalized:
        normalized["best_test_accuracy"] = float(
            normalized.get("best_validation_accuracy", 0.0)
        )
    return model, normalized
