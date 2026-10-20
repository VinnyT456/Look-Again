"""Inception-ResNet-v1 architecture and FaceNet pretrained-weight loader.

Copyright (c) 2019 Timothy Esler. MIT License; see licenses/facenet-pytorch-MIT.txt.
Architecture adapted from:
https://github.com/timesler/facenet-pytorch/blob/master/models/inception_resnet_v1.py
"""

from __future__ import annotations

from typing import Literal

import torch
from torch import nn
from torch.nn import functional as F


PRETRAINED_URLS = {
    "vggface2": "https://github.com/timesler/facenet-pytorch/releases/download/v2.2.9/20180402-114759-vggface2.pt",
    "casia-webface": "https://github.com/timesler/facenet-pytorch/releases/download/v2.2.9/20180408-102900-casia-webface.pt",
}
PRETRAINED_CLASS_COUNTS = {"vggface2": 8631, "casia-webface": 10575}


class BasicConv2d(nn.Module):
    def __init__(self, in_planes, out_planes, kernel_size, stride, padding=0):
        super().__init__()
        self.conv = nn.Conv2d(
            in_planes, out_planes, kernel_size=kernel_size, stride=stride,
            padding=padding, bias=False,
        )
        self.bn = nn.BatchNorm2d(out_planes, eps=0.001, momentum=0.1, affine=True)
        self.relu = nn.ReLU(inplace=False)

    def forward(self, x):
        return self.relu(self.bn(self.conv(x)))


class Block35(nn.Module):
    def __init__(self, scale=1.0):
        super().__init__()
        self.scale = scale
        self.branch0 = BasicConv2d(256, 32, kernel_size=1, stride=1)
        self.branch1 = nn.Sequential(
            BasicConv2d(256, 32, kernel_size=1, stride=1),
            BasicConv2d(32, 32, kernel_size=3, stride=1, padding=1),
        )
        self.branch2 = nn.Sequential(
            BasicConv2d(256, 32, kernel_size=1, stride=1),
            BasicConv2d(32, 32, kernel_size=3, stride=1, padding=1),
            BasicConv2d(32, 32, kernel_size=3, stride=1, padding=1),
        )
        self.conv2d = nn.Conv2d(96, 256, kernel_size=1, stride=1)
        self.relu = nn.ReLU(inplace=False)

    def forward(self, x):
        out = torch.cat((self.branch0(x), self.branch1(x), self.branch2(x)), dim=1)
        return self.relu(self.conv2d(out) * self.scale + x)


class Block17(nn.Module):
    def __init__(self, scale=1.0):
        super().__init__()
        self.scale = scale
        self.branch0 = BasicConv2d(896, 128, kernel_size=1, stride=1)
        self.branch1 = nn.Sequential(
            BasicConv2d(896, 128, kernel_size=1, stride=1),
            BasicConv2d(128, 128, kernel_size=(1, 7), stride=1, padding=(0, 3)),
            BasicConv2d(128, 128, kernel_size=(7, 1), stride=1, padding=(3, 0)),
        )
        self.conv2d = nn.Conv2d(256, 896, kernel_size=1, stride=1)
        self.relu = nn.ReLU(inplace=False)

    def forward(self, x):
        out = torch.cat((self.branch0(x), self.branch1(x)), dim=1)
        return self.relu(self.conv2d(out) * self.scale + x)


class Block8(nn.Module):
    def __init__(self, scale=1.0, noReLU=False):
        super().__init__()
        self.scale = scale
        self.noReLU = noReLU
        self.branch0 = BasicConv2d(1792, 192, kernel_size=1, stride=1)
        self.branch1 = nn.Sequential(
            BasicConv2d(1792, 192, kernel_size=1, stride=1),
            BasicConv2d(192, 192, kernel_size=(1, 3), stride=1, padding=(0, 1)),
            BasicConv2d(192, 192, kernel_size=(3, 1), stride=1, padding=(1, 0)),
        )
        self.conv2d = nn.Conv2d(384, 1792, kernel_size=1, stride=1)
        if not self.noReLU:
            self.relu = nn.ReLU(inplace=False)

    def forward(self, x):
        out = torch.cat((self.branch0(x), self.branch1(x)), dim=1)
        out = self.conv2d(out) * self.scale + x
        return out if self.noReLU else self.relu(out)


class Mixed6a(nn.Module):
    def __init__(self):
        super().__init__()
        self.branch0 = BasicConv2d(256, 384, kernel_size=3, stride=2)
        self.branch1 = nn.Sequential(
            BasicConv2d(256, 192, kernel_size=1, stride=1),
            BasicConv2d(192, 192, kernel_size=3, stride=1, padding=1),
            BasicConv2d(192, 256, kernel_size=3, stride=2),
        )
        self.branch2 = nn.MaxPool2d(3, stride=2)

    def forward(self, x):
        return torch.cat((self.branch0(x), self.branch1(x), self.branch2(x)), dim=1)


class Mixed7a(nn.Module):
    def __init__(self):
        super().__init__()
        self.branch0 = nn.Sequential(
            BasicConv2d(896, 256, kernel_size=1, stride=1),
            BasicConv2d(256, 384, kernel_size=3, stride=2),
        )
        self.branch1 = nn.Sequential(
            BasicConv2d(896, 256, kernel_size=1, stride=1),
            BasicConv2d(256, 256, kernel_size=3, stride=2),
        )
        self.branch2 = nn.Sequential(
            BasicConv2d(896, 256, kernel_size=1, stride=1),
            BasicConv2d(256, 256, kernel_size=3, stride=1, padding=1),
            BasicConv2d(256, 256, kernel_size=3, stride=2),
        )
        self.branch3 = nn.MaxPool2d(3, stride=2)

    def forward(self, x):
        return torch.cat(
            (self.branch0(x), self.branch1(x), self.branch2(x), self.branch3(x)), dim=1
        )


class InceptionResnetV1(nn.Module):
    """FaceNet Inception-ResNet-v1 with an optional classification head."""

    def __init__(
        self,
        pretrained: Literal["vggface2", "casia-webface"] | None = None,
        classify: bool = False,
        num_classes: int | None = None,
        dropout_prob: float = 0.6,
    ):
        super().__init__()
        if pretrained is not None and pretrained not in PRETRAINED_URLS:
            raise ValueError(f"Unknown pretrained weights: {pretrained}")
        if classify and num_classes is None and pretrained is None:
            raise ValueError("num_classes is required for an untrained classifier")
        self.pretrained = pretrained
        self.classify = classify
        self.num_classes = num_classes

        self.conv2d_1a = BasicConv2d(3, 32, kernel_size=3, stride=2)
        self.conv2d_2a = BasicConv2d(32, 32, kernel_size=3, stride=1)
        self.conv2d_2b = BasicConv2d(32, 64, kernel_size=3, stride=1, padding=1)
        self.maxpool_3a = nn.MaxPool2d(3, stride=2)
        self.conv2d_3b = BasicConv2d(64, 80, kernel_size=1, stride=1)
        self.conv2d_4a = BasicConv2d(80, 192, kernel_size=3, stride=1)
        self.conv2d_4b = BasicConv2d(192, 256, kernel_size=3, stride=2)
        self.repeat_1 = nn.Sequential(*(Block35(scale=0.17) for _ in range(5)))
        self.mixed_6a = Mixed6a()
        self.repeat_2 = nn.Sequential(*(Block17(scale=0.10) for _ in range(10)))
        self.mixed_7a = Mixed7a()
        self.repeat_3 = nn.Sequential(*(Block8(scale=0.20) for _ in range(5)))
        self.block8 = Block8(noReLU=True)
        self.avgpool_1a = nn.AdaptiveAvgPool2d(1)
        self.dropout = nn.Dropout(dropout_prob)
        self.last_linear = nn.Linear(1792, 512, bias=False)
        self.last_bn = nn.BatchNorm1d(512, eps=0.001, momentum=0.1, affine=True)

        if pretrained is not None:
            self.logits = nn.Linear(512, PRETRAINED_CLASS_COUNTS[pretrained])
            state_dict = torch.hub.load_state_dict_from_url(
                PRETRAINED_URLS[pretrained], map_location="cpu", progress=True
            )
            self.load_state_dict(state_dict)
        if self.classify and self.num_classes is not None:
            # Replace the identity-classification layer after loading the FaceNet weights.
            self.logits = nn.Linear(512, self.num_classes)

    def forward(self, x):
        x = self.conv2d_1a(x)
        x = self.conv2d_2a(x)
        x = self.conv2d_2b(x)
        x = self.maxpool_3a(x)
        x = self.conv2d_3b(x)
        x = self.conv2d_4a(x)
        x = self.conv2d_4b(x)
        x = self.repeat_1(x)
        x = self.mixed_6a(x)
        x = self.repeat_2(x)
        x = self.mixed_7a(x)
        x = self.repeat_3(x)
        x = self.block8(x)
        x = self.avgpool_1a(x)
        x = self.dropout(x)
        x = self.last_linear(x.flatten(1))
        x = self.last_bn(x)
        if self.classify:
            return self.logits(x)
        return F.normalize(x, p=2, dim=1)
