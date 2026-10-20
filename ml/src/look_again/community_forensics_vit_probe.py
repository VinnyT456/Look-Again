"""CommunityForensics ViT + rich-feature linear probe (exportable to Core ML)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from transformers import ViTForImageClassification, ViTImageProcessor

from look_again.paths import CACHE_DIR, CHECKPOINT_DIR, PROJECT_ROOT

MODEL_ID = "buildborderless/CommunityForensics-DeepfakeDet-ViT"
MODEL_CACHE = CACHE_DIR / "community-forensics-vit"
RICH_FEATURE_DIM = 1538  # 384*4 + 2
DEFAULT_COREML_DIR = CHECKPOINT_DIR / "coreml"
DEFAULT_TFLITE_DIR = CHECKPOINT_DIR / "tflite"
TFLITE_MODEL_FILENAME = "community_forensics_vit_rich_probe.tflite"
PROBE_SPLIT_SEED = 42


def load_community_forensics_vit(
    device: torch.device,
) -> tuple[ViTForImageClassification, ViTImageProcessor]:
    MODEL_CACHE.mkdir(parents=True, exist_ok=True)
    try:
        processor = ViTImageProcessor.from_pretrained(
            MODEL_ID, cache_dir=MODEL_CACHE, local_files_only=True
        )
        model = ViTForImageClassification.from_pretrained(
            MODEL_ID,
            cache_dir=MODEL_CACHE,
            torch_dtype=torch.float32,
            local_files_only=True,
        )
    except OSError:
        processor = ViTImageProcessor.from_pretrained(MODEL_ID, cache_dir=MODEL_CACHE)
        model = ViTForImageClassification.from_pretrained(
            MODEL_ID,
            cache_dir=MODEL_CACHE,
            torch_dtype=torch.float32,
        )
    model.to(device=device, dtype=torch.float32)
    model.eval()
    return model, processor


def rich_features_torch(
    vit: nn.Module,
    classifier: nn.Module,
    pixel_values: torch.Tensor,
) -> torch.Tensor:
    """Build 1538-D rich features with horizontal-flip TTA (matches eval pipeline)."""
    flipped = torch.flip(pixel_values, dims=[-1])

    vit_orig = vit(pixel_values=pixel_values)
    vit_flip = vit(pixel_values=flipped)
    seq_orig = vit_orig.last_hidden_state
    seq_flip = vit_flip.last_hidden_state

    cls_orig = seq_orig[:, 0, :]
    cls_flip = seq_flip[:, 0, :]
    patches_orig = seq_orig[:, 1:, :]
    patches_flip = seq_flip[:, 1:, :]
    logit_orig = classifier(cls_orig).squeeze(-1)
    logit_flip = classifier(cls_flip).squeeze(-1)

    patches_pair = torch.cat([patches_orig, patches_flip], dim=1)
    cls_mean = 0.5 * (cls_orig + cls_flip)
    cls_diff = torch.abs(cls_orig - cls_flip)
    patch_mean = patches_pair.mean(dim=1)
    patch_std = patches_pair.std(dim=1, unbiased=False)

    return torch.cat(
        [
            cls_mean,
            cls_diff,
            patch_mean,
            patch_std,
            logit_orig.unsqueeze(1),
            logit_flip.unsqueeze(1),
        ],
        dim=1,
    )


class CommunityForensicsViTProbe(nn.Module):
    """Frozen ViT + StandardScaler + logistic probe on rich features."""

    def __init__(
        self,
        backbone: ViTForImageClassification,
        *,
        feature_mean: torch.Tensor,
        feature_scale: torch.Tensor,
        probe_weight: torch.Tensor,
        probe_bias: torch.Tensor,
    ) -> None:
        super().__init__()
        self.vit = backbone.vit
        self.stock_classifier = backbone.classifier
        self.vit.eval()
        self.stock_classifier.eval()
        for param in self.vit.parameters():
            param.requires_grad = False
        for param in self.stock_classifier.parameters():
            param.requires_grad = False

        self.register_buffer("feature_mean", feature_mean.view(1, -1))
        self.register_buffer("feature_scale", feature_scale.view(1, -1))
        self.probe = nn.Linear(RICH_FEATURE_DIM, 1, bias=True)
        with torch.no_grad():
            self.probe.weight.copy_(probe_weight.view(1, -1))
            self.probe.bias.copy_(probe_bias.reshape(-1))

    def forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
        features = rich_features_torch(self.vit, self.stock_classifier, pixel_values)
        scaled = (features - self.feature_mean) / self.feature_scale
        logits = self.probe(scaled)
        return torch.sigmoid(logits).squeeze(-1)


@dataclass(frozen=True)
class SklearnLinearProbeWeights:
    mean: np.ndarray
    scale: np.ndarray
    coef: np.ndarray
    intercept: np.ndarray


def sklearn_linear_probe_weights(pipeline: Pipeline) -> SklearnLinearProbeWeights:
    scaler = pipeline.named_steps["standardscaler"]
    logistic = pipeline.named_steps["logisticregression"]
    return SklearnLinearProbeWeights(
        mean=np.asarray(scaler.mean_, dtype=np.float32),
        scale=np.asarray(scaler.scale_, dtype=np.float32),
        coef=np.asarray(logistic.coef_, dtype=np.float32),
        intercept=np.asarray(logistic.intercept_, dtype=np.float32),
    )


def fit_universal_rich_linear_probe(
    x_train: np.ndarray,
    y_train: np.ndarray,
    *,
    c: float = 0.01,
    seed: int = PROBE_SPLIT_SEED,
) -> Pipeline:
    pipeline = Pipeline(
        [
            ("standardscaler", StandardScaler()),
            (
                "logisticregression",
                LogisticRegression(C=c, max_iter=2000, random_state=seed),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)
    return pipeline


def build_rich_matrix_from_feature_dict(feats: dict[str, np.ndarray]) -> np.ndarray:
    cls_orig = feats["cls_orig"]
    cls_flip = feats["cls_flip"]
    patch_mean = feats["patch_mean"]
    patch_std = feats["patch_std"]
    logit_orig = feats["logit_orig"]
    logit_flip = feats["logit_flip"]
    cls_mean = 0.5 * (cls_orig + cls_flip)
    cls_diff = np.abs(cls_orig - cls_flip)
    return np.concatenate(
        [
            cls_mean,
            cls_diff,
            patch_mean,
            patch_std,
            logit_orig[:, None],
            logit_flip[:, None],
        ],
        axis=1,
    ).astype(np.float32)


def load_feature_npz(path: Path) -> tuple[np.ndarray, np.ndarray] | None:
    if not path.is_file():
        return None
    data = np.load(path, allow_pickle=False)
    feature_keys = (
        "cls_orig",
        "cls_flip",
        "patch_mean",
        "patch_std",
        "logit_orig",
        "logit_flip",
    )
    if "labels" not in data.files or not all(k in data.files for k in feature_keys):
        return None
    feats = {key: data[key] for key in feature_keys}
    x = build_rich_matrix_from_feature_dict(feats)
    y = data["labels"].astype(np.int64)
    return x, y


def collect_universal_probe_training_arrays(
    *,
    val_fraction: float = 0.8,
    seed: int = PROBE_SPLIT_SEED,
    max_per_class_subsample: int = 1000,
) -> tuple[np.ndarray, np.ndarray]:
    """80% stratified slices from cached rich features (multi-dataset mix)."""
    import random

    from look_again.paths import DATA_DIR

    cache_specs: list[Path] = [
        MODEL_CACHE / "deepfake_vit_features.npz",
        MODEL_CACHE / "cross_sdfvd_face_frames_val_features.npz",
        MODEL_CACHE / "cross_df40_face_crops_unpaired_features.npz",
        MODEL_CACHE / "cross_real_vs_fake_140k_test_features.npz",
    ]
    deepfake_root = DATA_DIR / "Deepfake"
    if deepfake_root.is_dir() and not cache_specs[0].is_file():
        raise FileNotFoundError(
            f"Missing {cache_specs[0]}. Run: cd ml && uv run test_community_forensics_vit.py --eval-deepfake"
        )

    x_parts: list[np.ndarray] = []
    y_parts: list[np.ndarray] = []

    for cache_path in cache_specs:
        loaded = load_feature_npz(cache_path)
        if loaded is None:
            continue
        x_all, y_all = loaded
        n = len(y_all)
        by_label: dict[int, list[int]] = {0: [], 1: []}
        for idx, label in enumerate(y_all):
            by_label[int(label)].append(idx)
        rng = random.Random(seed)
        indices: list[int] = []
        for label in (0, 1):
            bucket = by_label[label][:]
            rng.shuffle(bucket)
            if max_per_class_subsample and len(bucket) > max_per_class_subsample:
                bucket = bucket[:max_per_class_subsample]
            indices.extend(bucket)
        indices.sort()
        x_sub = x_all[indices]
        y_sub = y_all[indices]

        train_idx: list[int] = []
        test_idx: list[int] = []
        by_label = {0: [], 1: []}
        for idx, label in enumerate(y_sub):
            by_label[int(label)].append(idx)
        for label in (0, 1):
            bucket = by_label[label][:]
            rng.shuffle(bucket)
            val_count = int(len(bucket) * val_fraction)
            train_idx.extend(bucket[:val_count])
        train_idx.sort()
        x_parts.append(x_sub[train_idx])
        y_parts.append(y_sub[train_idx])

    if not x_parts:
        raise RuntimeError("No feature caches found for universal probe training.")
    return np.concatenate(x_parts, axis=0), np.concatenate(y_parts, axis=0)


def processor_export_metadata(processor: ViTImageProcessor) -> dict:
    return {
        "model_id": MODEL_ID,
        "input_name": "pixel_values",
        "input_shape": [1, 3, 384, 384],
        "input_dtype": "float32",
        "output_name": "fake_prob",
        "output_description": "Probability image is fake (class 1)",
        "preprocessing": {
            "note": (
                "Apply ViTImageProcessor from the same MODEL_ID before on-device inference "
                "(channel-first float32 NCHW)."
            ),
            "do_resize": processor.do_resize,
            "do_center_crop": processor.do_center_crop,
            "size": str(processor.size),
            "crop_size": str(getattr(processor, "crop_size", None)),
            "resample": int(processor.resample),
        },
        "probe": {
            "type": "rich_linear",
            "feature_dim": RICH_FEATURE_DIM,
            "logistic_C": 0.01,
            "tta_horizontal_flip": True,
        },
    }


def export_probe_coreml(
    module: CommunityForensicsViTProbe,
    output_path: Path,
    *,
    minimum_deployment_target: str = "iOS17",
) -> None:
    import coremltools as ct

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        if output_path.is_dir():
            import shutil

            shutil.rmtree(output_path)
        else:
            output_path.unlink()

    module.eval()
    target = getattr(ct.target, minimum_deployment_target)
    example = torch.randn(1, 3, 384, 384, dtype=torch.float32)
    with torch.inference_mode():
        traced = torch.jit.trace(module, example, strict=False)

    mlmodel = ct.convert(
        traced,
        inputs=[
            ct.TensorType(
                name="pixel_values",
                shape=(1, 3, 384, 384),
                dtype=np.float32,
            )
        ],
        outputs=[ct.TensorType(name="fake_prob", dtype=np.float32)],
        minimum_deployment_target=target,
        convert_to="mlprogram",
        source="pytorch",
    )
    mlmodel.save(str(output_path))


def verify_coreml_matches_torch(
    module: CommunityForensicsViTProbe,
    coreml_path: Path,
    pixel_values: torch.Tensor,
    *,
    atol: float = 1e-3,
) -> float:
    import coremltools as ct

    module.eval()
    with torch.inference_mode():
        torch_out = module(pixel_values).cpu().numpy()
    mlmodel = ct.models.MLModel(str(coreml_path))
    coreml_out = mlmodel.predict(
        {"pixel_values": pixel_values.cpu().numpy().astype(np.float32)}
    )["fake_prob"]
    max_diff = float(np.max(np.abs(torch_out - coreml_out)))
    if max_diff > atol:
        raise RuntimeError(f"Core ML verification failed: max diff {max_diff} > {atol}")
    return max_diff


def _export_probe_tflite_litert(
    module: CommunityForensicsViTProbe,
    output_path: Path,
) -> None:
    import litert_torch

    module.eval()
    example = torch.randn(1, 3, 384, 384, dtype=torch.float32)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    edge = litert_torch.convert(module, (example,))
    edge.export(str(output_path))


def _export_probe_tflite_subprocess(output_path: Path) -> None:
    import os
    import shutil
    import subprocess
    import sys

    worker = PROJECT_ROOT / "scripts" / "export" / "litert_tflite_worker.py"
    python312 = os.environ.get("LITERT_PYTHON")
    if python312:
        python312 = shutil.which(python312) or python312
    else:
        for candidate in ("python3.12", "python3.11"):
            found = shutil.which(candidate)
            if found:
                python312 = found
                break
    if not python312:
        raise RuntimeError(
            "LiteRT-Torch export requires Python 3.12 with litert-torch installed. "
            "Set LITERT_PYTHON to that interpreter, or install python3.12 and run:\n"
            "  uv pip install --python python3.12 litert-torch"
        )

    check = subprocess.run(
        [python312, "-c", "import litert_torch"],
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        raise RuntimeError(
            f"{python312} does not have litert-torch. Install with:\n"
            f"  uv pip install --python {python312} litert-torch"
        )

    env = os.environ.copy()
    src = str((PROJECT_ROOT / "src").resolve())
    export_dir = str((PROJECT_ROOT / "scripts" / "export").resolve())
    env["PYTHONPATH"] = os.pathsep.join([src, export_dir])
    subprocess.run(
        [python312, str(worker), "--output", str(output_path)],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
    )


def export_probe_tflite(
    module: CommunityForensicsViTProbe,
    output_path: Path,
) -> None:
    """Write a .tflite flatbuffer for LiteRT / TensorFlow Lite on Android."""
    try:
        import litert_torch  # noqa: F401
    except ImportError:
        _export_probe_tflite_subprocess(output_path)
        return
    _export_probe_tflite_litert(module, output_path)


def verify_tflite_matches_torch(
    module: CommunityForensicsViTProbe,
    tflite_path: Path,
    pixel_values: torch.Tensor,
    *,
    atol: float = 1e-2,
) -> float:
    from ai_edge_litert.interpreter import Interpreter

    module.eval()
    with torch.inference_mode():
        torch_out = module(pixel_values).cpu().numpy().reshape(-1)
    interpreter = Interpreter(model_path=str(tflite_path))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]
    x = pixel_values.cpu().numpy().astype(input_detail["dtype"])
    interpreter.set_tensor(input_detail["index"], x)
    interpreter.invoke()
    tflite_out = interpreter.get_tensor(output_detail["index"]).reshape(-1)
    max_diff = float(np.max(np.abs(torch_out - tflite_out)))
    if max_diff > atol:
        raise RuntimeError(f"TFLite verification failed: max diff {max_diff} > {atol}")
    return max_diff


def save_probe_bundle(
    output_dir: Path,
    pipeline: Pipeline,
    processor: ViTImageProcessor,
    *,
    model_filename: str = "community_forensics_vit_rich_probe.mlpackage",
    model_key: str = "coreml",
    runtime: dict[str, str] | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    weights = sklearn_linear_probe_weights(pipeline)
    meta = processor_export_metadata(processor)
    if runtime:
        meta["runtime"] = runtime
    meta["training"] = {
        "probe_pipeline": "StandardScaler + LogisticRegression(C=0.01)",
        "project_root": str(PROJECT_ROOT.resolve()),
    }

    meta_path = output_dir / "community_forensics_vit_rich_probe.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")

    np.savez(
        output_dir / "community_forensics_vit_rich_probe_weights.npz",
        mean=weights.mean,
        scale=weights.scale,
        coef=weights.coef,
        intercept=weights.intercept,
    )

    model_path = output_dir / model_filename
    return {
        "metadata": str(meta_path),
        "weights_npz": str(output_dir / "community_forensics_vit_rich_probe_weights.npz"),
        model_key: str(model_path),
    }


# ---------------------------------------------------------------------------
# Heatmap: per-patch attribution of the probe's decision
# ---------------------------------------------------------------------------

PATCH_GRID = 24  # 384 / 16 patch size
PATCH_COUNT = PATCH_GRID * PATCH_GRID
HIDDEN_DIM = (RICH_FEATURE_DIM - 2) // 4
PATCH_MAP_STD_EPS = 1e-6


def patch_contribution_map(
    patches_orig: torch.Tensor,
    patches_flip: torch.Tensor,
    effective_weight: torch.Tensor,
    hidden_dim: int,
) -> torch.Tensor:
    """Exact per-patch share of the probe logit that comes from patch features.

    The probe sees ``patch_mean`` and ``patch_std`` over the 2N tokens from the
    original and flipped passes. Both split exactly into per-token terms:

        patch_mean_d = μ_d                      (centered part sums to zero)
        patch_std_d  = Σ_t (x_td − μ_d)² / (2N · std_d)

    With ``a``/``c`` the effective weights (coef / scaler scale) on those blocks,
    token t contributes ``Σ_d [a_d (x_td − μ_d) + c_d (x_td − μ_d)² / std_d] / 2N``.
    Summed over tokens this equals ``Σ_d c_d · std_d``: the whole patch_std term,
    with the (spatially uniform) ``a·μ`` term left out. Flipped-pass tokens are
    mirrored back so both passes land on the same image location.

    Returns ``[B, 24, 24]`` in logit units; positive pushes toward "fake".
    """
    # Shapes are fixed (one image, 576 patches per pass); using constants keeps
    # the traced graph free of shape→int casts that Core ML can't convert.
    pairs = torch.cat([patches_orig, patches_flip], dim=1)
    tokens = float(2 * PATCH_COUNT)
    mean_weight = effective_weight[2 * hidden_dim : 3 * hidden_dim]
    std_weight = effective_weight[3 * hidden_dim : 4 * hidden_dim]

    mu = pairs.mean(dim=1, keepdim=True)
    std = pairs.std(dim=1, unbiased=False, keepdim=True).clamp_min(PATCH_MAP_STD_EPS)
    centered = pairs - mu
    per_token = ((centered * mean_weight) + (centered * centered * std_weight / std)).sum(-1) / tokens

    orig = per_token[:, :PATCH_COUNT].reshape(-1, PATCH_GRID, PATCH_GRID)
    flip = per_token[:, PATCH_COUNT:].reshape(-1, PATCH_GRID, PATCH_GRID).flip(-1)
    return orig + flip


class CommunityForensicsViTProbeHeatmap(CommunityForensicsViTProbe):
    """Same decision as ``CommunityForensicsViTProbe`` plus a 24×24 patch map."""

    def forward(self, pixel_values: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        flipped = torch.flip(pixel_values, dims=[-1])
        seq_orig = self.vit(pixel_values=pixel_values).last_hidden_state
        seq_flip = self.vit(pixel_values=flipped).last_hidden_state

        cls_orig = seq_orig[:, 0, :]
        cls_flip = seq_flip[:, 0, :]
        patches_orig = seq_orig[:, 1:, :]
        patches_flip = seq_flip[:, 1:, :]
        logit_orig = self.stock_classifier(cls_orig).squeeze(-1)
        logit_flip = self.stock_classifier(cls_flip).squeeze(-1)

        patches_pair = torch.cat([patches_orig, patches_flip], dim=1)
        features = torch.cat(
            [
                0.5 * (cls_orig + cls_flip),
                torch.abs(cls_orig - cls_flip),
                patches_pair.mean(dim=1),
                patches_pair.std(dim=1, unbiased=False),
                logit_orig.unsqueeze(1),
                logit_flip.unsqueeze(1),
            ],
            dim=1,
        )
        scaled = (features - self.feature_mean) / self.feature_scale
        fake_prob = torch.sigmoid(self.probe(scaled)).squeeze(-1)

        effective_weight = self.probe.weight.view(-1) / self.feature_scale.view(-1)
        patch_map = patch_contribution_map(patches_orig, patches_flip, effective_weight, HIDDEN_DIM)
        return fake_prob, patch_map


def load_probe_module_from_npz(
    weights_path: Path,
    device: torch.device,
    module_class: type[CommunityForensicsViTProbe] = CommunityForensicsViTProbe,
) -> CommunityForensicsViTProbe:
    """Rebuild the exported probe from its saved weights (no refitting)."""
    data = np.load(weights_path)
    backbone, _ = load_community_forensics_vit(device)
    module = module_class(
        backbone,
        feature_mean=torch.from_numpy(data["mean"].astype(np.float32)),
        feature_scale=torch.from_numpy(data["scale"].astype(np.float32)),
        probe_weight=torch.from_numpy(data["coef"].astype(np.float32)),
        probe_bias=torch.from_numpy(data["intercept"].astype(np.float32)),
    )
    return module.to(device).eval()


def export_heatmap_coreml(
    module: CommunityForensicsViTProbeHeatmap,
    output_path: Path,
    *,
    minimum_deployment_target: str = "iOS17",
) -> None:
    """Core ML export with two outputs: ``fake_prob`` [1] and ``patch_map`` [1, 24, 24]."""
    import shutil

    import coremltools as ct

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        shutil.rmtree(output_path) if output_path.is_dir() else output_path.unlink()

    module.eval()
    example = torch.randn(1, 3, 384, 384, dtype=torch.float32)
    with torch.inference_mode():
        traced = torch.jit.trace(module, example, strict=False)

    mlmodel = ct.convert(
        traced,
        inputs=[ct.TensorType(name="pixel_values", shape=(1, 3, 384, 384), dtype=np.float32)],
        outputs=[
            ct.TensorType(name="fake_prob", dtype=np.float32),
            ct.TensorType(name="patch_map", dtype=np.float32),
        ],
        minimum_deployment_target=getattr(ct.target, minimum_deployment_target),
        convert_to="mlprogram",
        source="pytorch",
    )
    mlmodel.short_description = (
        "CommunityForensics ViT + rich linear probe. fake_prob: probability the image is "
        "AI-generated. patch_map: 24x24 per-patch contribution to the decision (logit units, "
        "positive = toward fake) over the 384x384 center crop."
    )
    mlmodel.save(str(output_path))
