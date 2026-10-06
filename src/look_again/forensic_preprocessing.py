"""CNN preprocessing that adds spatial versions of classical forensic cues."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps

from look_again.df40_subset import FACE_CROP_DATASET_PATH, LEGACY_FACE_CROP_DATASET_PATH
from look_again.classical_ml.features import (
    FeatureConfig,
    extract_ela_residual,
    extract_lbp_map,
    extract_noise_map,
)


from look_again.paths import CACHE_DIR
_CACHE_ROOT = CACHE_DIR / "forensic_features"
_CACHE_VERSION = 2
FORENSIC_CHANNEL_ORDER = (
    "rgb_r",
    "rgb_g",
    "rgb_b",
    "lbp",
    "ela_r",
    "ela_g",
    "ela_b",
    "noise_residual",
)
FORENSIC_INPUT_CHANNELS = len(FORENSIC_CHANNEL_ORDER)


class ForensicChannelsTransform:
    """Return RGB plus aligned LBP, RGB ELA, and blur-residual maps.

    The derived channels share their primitive feature implementations with
    the classical ML extractors. Cached maps are keyed by the source face-crop
    file and preprocessing configuration, so their extraction cost is paid
    once per image rather than once per training epoch.
    """

    requires_source_path = True

    def __init__(self, model, *, augment: bool = False) -> None:
        self.input_size = tuple(model.default_cfg.get("input_size", (3, 224, 224))[-2:])
        self.rgb_mean = tuple(float(value) for value in model.default_cfg["mean"])
        self.rgb_std = tuple(float(value) for value in model.default_cfg["std"])
        self.augment = augment
        self.config = FeatureConfig()
        self.cache_id = (
            f"v{_CACHE_VERSION}_q{self.config.ela_quality}_p{self.config.lbp_points}"
            f"_r{self.config.lbp_radius:g}_g{self.config.noise_kernel_size}"
        )

    def _cache_path(self, source_path: str | Path | None) -> tuple[Path, int, int] | None:
        if source_path is None:
            return None
        path = Path(source_path).expanduser().resolve()
        relative_path = None
        for dataset_root in (FACE_CROP_DATASET_PATH, LEGACY_FACE_CROP_DATASET_PATH):
            try:
                relative_path = path.relative_to(dataset_root.resolve())
                break
            except ValueError:
                continue
        if relative_path is None:
            return None
        try:
            stat = path.stat()
        except OSError:
            return None
        cache_path = (
            _CACHE_ROOT
            / self.cache_id
            / relative_path.parent
            / f"{relative_path.stem}.npz"
        )
        return cache_path, stat.st_size, stat.st_mtime_ns

    def _load_or_create_maps(
        self,
        image: Image.Image,
        source_path: str | Path | None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        cache = self._cache_path(source_path)
        if cache is not None:
            cache_path, source_size, source_mtime = cache
            if cache_path.is_file():
                try:
                    with np.load(cache_path, allow_pickle=False) as saved:
                        if (
                            int(saved["source_size"]) == source_size
                            and int(saved["source_mtime"]) == source_mtime
                            and tuple(saved["image_shape"].tolist())
                            == (image.height, image.width)
                        ):
                            return saved["lbp"], saved["ela"], saved["noise"]
                except (OSError, KeyError, ValueError):
                    pass

        lbp = extract_lbp_map(
            image,
            points=self.config.lbp_points,
            radius=self.config.lbp_radius,
        )
        ela = extract_ela_residual(image, quality=self.config.ela_quality)
        noise = extract_noise_map(
            image,
            kernel_size=self.config.noise_kernel_size,
        )

        if cache is not None:
            cache_path, source_size, source_mtime = cache
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = cache_path.with_suffix(".tmp")
            with temporary_path.open("wb") as cache_file:
                np.savez_compressed(
                    cache_file,
                    lbp=lbp,
                    ela=ela,
                    noise=noise,
                    source_size=np.int64(source_size),
                    source_mtime=np.int64(source_mtime),
                    image_shape=np.asarray((image.height, image.width), dtype=np.int32),
                )
            temporary_path.replace(cache_path)
        return lbp, ela, noise

    def __call__(
        self,
        image: Image.Image,
        *,
        source_path: str | Path | None = None,
    ) -> torch.Tensor:
        image = image.convert("RGB")
        lbp, ela, noise = self._load_or_create_maps(image, source_path)

        if self.augment and torch.rand(()).item() < 0.5:
            image = ImageOps.mirror(image)
            lbp = np.fliplr(lbp)
            ela = np.fliplr(ela)
            noise = np.fliplr(noise)

        target_height, target_width = self.input_size
        image = image.resize((target_width, target_height), Image.Resampling.BILINEAR)
        lbp_image = Image.fromarray(lbp).resize(
            (target_width, target_height), Image.Resampling.NEAREST
        )
        ela_image = Image.fromarray(ela, mode="RGB").resize(
            (target_width, target_height), Image.Resampling.BILINEAR
        )
        noise_image = Image.fromarray(noise).resize(
            (target_width, target_height), Image.Resampling.BILINEAR
        )

        rgb = np.asarray(image, dtype=np.float32) / 255.0
        rgb_tensor = torch.from_numpy(np.ascontiguousarray(rgb.transpose(2, 0, 1)))
        lbp_tensor = torch.from_numpy(np.asarray(lbp_image, dtype=np.float32).copy())
        ela_array = np.asarray(ela_image, dtype=np.float32) / 255.0
        ela_tensor = torch.from_numpy(np.ascontiguousarray(ela_array.transpose(2, 0, 1)))
        noise_tensor = torch.from_numpy(np.asarray(noise_image, dtype=np.float32).copy())

        auxiliary = torch.cat(
            (
                (lbp_tensor / float(self.config.lbp_points + 1)).unsqueeze(0),
                (ela_tensor * (255.0 / 32.0)).clamp_(0.0, 1.0),
                (noise_tensor / 16.0).clamp_(0.0, 1.0).unsqueeze(0),
            ),
            dim=0,
        )
        channels = torch.cat((rgb_tensor, auxiliary), dim=0)

        if channels.shape[0] != FORENSIC_INPUT_CHANNELS:
            raise RuntimeError(
                f"Expected {FORENSIC_INPUT_CHANNELS} input channels, got {channels.shape[0]}"
            )
        mean = torch.tensor(
            (*self.rgb_mean, *(0.5 for _ in range(channels.shape[0] - 3))),
            dtype=channels.dtype,
        ).view(channels.shape[0], 1, 1)
        std = torch.tensor(
            (*self.rgb_std, *(0.5 for _ in range(channels.shape[0] - 3))),
            dtype=channels.dtype,
        ).view(channels.shape[0], 1, 1)
        return (channels - mean) / std
