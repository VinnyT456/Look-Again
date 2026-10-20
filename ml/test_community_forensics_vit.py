"""Local smoke test and evaluation for CommunityForensics DeepfakeDet-ViT.

Model: https://huggingface.co/buildborderless/CommunityForensics-DeepfakeDet-ViT
Requires transformers >= 5.4.0 for correct resize/center-crop preprocessing.

Example:
  uv run test_community_forensics_vit.py data/Deepfake/fake/fake_00003.jpg
  uv run test_community_forensics_vit.py --eval-deepfake
  uv run test_community_forensics_vit.py --eval-deepfake --no-tta --no-split
"""

import argparse
import csv
import json
import os
import random
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm
from transformers import ViTForImageClassification, ViTImageProcessor

MODEL_ID = "buildborderless/CommunityForensics-DeepfakeDet-ViT"
MODEL_CACHE = Path(__file__).resolve().parent / "cache" / "community-forensics-vit"
FEATURE_CACHE_PATH = MODEL_CACHE / "deepfake_vit_features.npz"
CNN_CACHE_PATH = MODEL_CACHE / "deepfake_cnn_logits.npz"
DEEPFAKE_ROOT = Path(__file__).resolve().parent / "data" / "Deepfake"
DEFAULT_IMAGE = str(DEEPFAKE_ROOT / "fake" / "fake_00003.jpg")
THRESHOLD = float(os.environ.get("FAKE_THRESHOLD", "0.5"))
EVAL_BATCH_SIZE = int(os.environ.get("EVAL_BATCH_SIZE", "32"))
SPLIT_SEED = int(os.environ.get("EVAL_SPLIT_SEED", "42"))
VAL_FRACTION = float(os.environ.get("EVAL_VAL_FRACTION", "0.8"))


def pick_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def load_model(device: torch.device) -> tuple[ViTForImageClassification, ViTImageProcessor]:
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


def _jsonable(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if hasattr(value, "items"):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return str(value)


def processor_summary(processor: ViTImageProcessor) -> dict:
    return {
        "size": _jsonable(processor.size),
        "crop_size": _jsonable(getattr(processor, "crop_size", None)),
        "do_center_crop": processor.do_center_crop,
        "do_resize": processor.do_resize,
        "resample": int(processor.resample),
    }


def score_image(
    image_path: Path,
    model: ViTForImageClassification,
    processor: ViTImageProcessor,
    device: torch.device,
    *,
    threshold: float,
    tta: bool,
) -> dict[str, float | str]:
    fake_prob = score_paths_batch(
        [image_path], model, processor, device, tta=tta, show_progress=False
    )[0]
    real_prob = 1.0 - fake_prob
    verdict = "fake" if fake_prob >= threshold else "real"
    return {
        "image": str(image_path.resolve()),
        "fake_prob": round(fake_prob, 6),
        "real_prob": round(real_prob, 6),
        "threshold": threshold,
        "verdict": verdict,
    }


def run_batch(
    image_paths: list[Path],
    model: ViTForImageClassification,
    processor: ViTImageProcessor,
    device: torch.device,
    *,
    threshold: float,
    tta: bool,
) -> None:
    probs = score_paths_batch(image_paths, model, processor, device, tta=tta, show_progress=False)
    for image_path, fake_prob in zip(image_paths, probs, strict=True):
        if not image_path.is_file():
            raise FileNotFoundError(image_path)
        real_prob = 1.0 - fake_prob
        verdict = "fake" if fake_prob >= threshold else "real"
        print(
            json.dumps(
                {
                    "image": str(image_path.resolve()),
                    "fake_prob": round(fake_prob, 6),
                    "real_prob": round(real_prob, 6),
                    "threshold": threshold,
                    "verdict": verdict,
                },
                separators=(",", ":"),
            )
        )


def list_images(folder: Path) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts)


def load_deepfake_samples(root: Path) -> list[tuple[Path, int]]:
    samples: list[tuple[Path, int]] = []
    for label_name, label in (("fake", 1), ("real", 0)):
        folder = root / label_name
        if not folder.is_dir():
            raise FileNotFoundError(folder)
        for path in list_images(folder):
            samples.append((path, label))
    return samples


def expand_images_for_tta(images: list[Image.Image], tta: bool) -> list[Image.Image]:
    if not tta:
        return images
    expanded: list[Image.Image] = []
    for image in images:
        expanded.append(image)
        expanded.append(image.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
    return expanded


def collapse_tta_probs(probs: list[float], tta: bool) -> list[float]:
    if not tta:
        return probs
    return [(probs[i] + probs[i + 1]) / 2.0 for i in range(0, len(probs), 2)]


def score_paths_batch(
    paths: list[Path],
    model: ViTForImageClassification,
    processor: ViTImageProcessor,
    device: torch.device,
    *,
    tta: bool,
    show_progress: bool,
) -> list[float]:
    all_probs: list[float] = []
    iterator = range(0, len(paths), EVAL_BATCH_SIZE)
    if show_progress:
        iterator = tqdm(iterator, desc="infer", unit="batch")
    for start in iterator:
        batch_paths = paths[start : start + EVAL_BATCH_SIZE]
        images = [Image.open(path).convert("RGB") for path in batch_paths]
        images = expand_images_for_tta(images, tta)
        inputs = processor(images=images, return_tensors="pt")
        inputs = {key: value.to(device=device, dtype=torch.float32) for key, value in inputs.items()}
        with torch.inference_mode():
            logits = model(**inputs).logits.float()
        batch_probs = torch.sigmoid(logits).squeeze(-1).cpu().tolist()
        if isinstance(batch_probs, float):
            batch_probs = [batch_probs]
        all_probs.extend(collapse_tta_probs(batch_probs, tta))
    return all_probs


def extract_or_load_vit_features(
    paths: list[Path],
    labels: list[int],
    model: ViTForImageClassification,
    processor: ViTImageProcessor,
    device: torch.device,
    *,
    cache_path: Path = FEATURE_CACHE_PATH,
    rebuild_cache: bool = False,
) -> dict[str, np.ndarray]:
    rel_paths = np.array([p.name for p in paths])
    if cache_path.is_file() and not rebuild_cache:
        data = np.load(cache_path, allow_pickle=False)
        if (
            "filenames" in data
            and len(data["filenames"]) == len(rel_paths)
            and np.array_equal(data["filenames"], rel_paths)
        ):
            print(f"Loaded cached ViT features from {cache_path}", file=sys.stderr)
            return {k: data[k] for k in data.files}

    n = len(paths)
    hidden_dim = model.config.hidden_size
    cls_orig = np.zeros((n, hidden_dim), dtype=np.float32)
    cls_flip = np.zeros((n, hidden_dim), dtype=np.float32)
    patch_mean = np.zeros((n, hidden_dim), dtype=np.float32)
    patch_std = np.zeros((n, hidden_dim), dtype=np.float32)
    logit_orig = np.zeros(n, dtype=np.float32)
    logit_flip = np.zeros(n, dtype=np.float32)

    iterator = tqdm(range(0, n, EVAL_BATCH_SIZE), desc="extract_vit", unit="batch")
    for start in iterator:
        end = min(start + EVAL_BATCH_SIZE, n)
        batch_paths = paths[start:end]
        images_orig = [Image.open(p).convert("RGB") for p in batch_paths]
        images_expanded = expand_images_for_tta(images_orig, tta=True)
        inputs = processor(images=images_expanded, return_tensors="pt")
        inputs = {k: v.to(device=device, dtype=torch.float32) for k, v in inputs.items()}
        with torch.inference_mode():
            vit_out = model.vit(**inputs)
            seq = vit_out.last_hidden_state.float()  # [2*B, 1+P, D]
            cls_tokens = seq[:, 0, :]  # [2*B, D]
            patches = seq[:, 1:, :]  # [2*B, P, D]
            logits = model.classifier(cls_tokens).squeeze(-1)  # [2*B]

            b = end - start
            cls_pair = cls_tokens.reshape(b, 2, hidden_dim)
            patches_pair = patches.reshape(b, 2 * patches.size(1), hidden_dim)
            logits_pair = logits.reshape(b, 2)

            cls_orig[start:end] = cls_pair[:, 0, :].cpu().numpy()
            cls_flip[start:end] = cls_pair[:, 1, :].cpu().numpy()
            patch_mean[start:end] = patches_pair.mean(dim=1).cpu().numpy()
            patch_std[start:end] = patches_pair.std(dim=1).cpu().numpy()
            logit_orig[start:end] = logits_pair[:, 0].cpu().numpy()
            logit_flip[start:end] = logits_pair[:, 1].cpu().numpy()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "filenames": rel_paths,
        "labels": np.array(labels, dtype=np.int64),
        "cls_orig": cls_orig,
        "cls_flip": cls_flip,
        "patch_mean": patch_mean,
        "patch_std": patch_std,
        "logit_orig": logit_orig,
        "logit_flip": logit_flip,
    }
    np.savez(cache_path, **payload)
    print(f"Saved ViT feature cache to {cache_path}", file=sys.stderr)
    return payload


class _SimpleImageDataset(Dataset):
    def __init__(self, paths: list[Path], transform) -> None:
        self.paths = paths
        self.transform = transform

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, idx: int):
        img = Image.open(self.paths[idx]).convert("RGB")
        return self.transform(img)


def extract_or_load_cnn_logits(
    paths: list[Path],
    device: torch.device,
    *,
    cache_path: Path = CNN_CACHE_PATH,
    rebuild_cache: bool = False,
) -> dict[str, np.ndarray]:
    """Extract real-minus-fake logits from available repo CNN checkpoints."""
    rel_paths = np.array([p.name for p in paths])
    run_names = (
        "inception_resnet_v1_140k",
        "inception_resnet_v1_unpaired_crops",
        "efficientnet_b0",
    )
    if cache_path.is_file() and not rebuild_cache:
        data = np.load(cache_path, allow_pickle=False)
        if (
            "filenames" in data
            and len(data["filenames"]) == len(rel_paths)
            and np.array_equal(data["filenames"], rel_paths)
            and all(name in data for name in run_names)
        ):
            print(f"Loaded cached CNN logits from {cache_path}", file=sys.stderr)
            return {name: data[name] for name in run_names}

    from look_again.robustness import build_baseline_test_transform
    from look_again.training import best_checkpoint_path, load_trained_model

    results: dict[str, np.ndarray] = {}
    for run_name in run_names:
        if not best_checkpoint_path(run_name).is_file():
            continue
        cnn_model, _ = load_trained_model(run_name, device=device)
        cnn_model.eval()
        transform = build_baseline_test_transform(cnn_model)
        ds = _SimpleImageDataset(paths, transform)
        loader = DataLoader(ds, batch_size=64, shuffle=False, num_workers=0)
        preds: list[np.ndarray] = []
        with torch.inference_mode():
            for batch in tqdm(loader, desc=f"cnn:{run_name}", unit="batch"):
                batch = batch.to(device)
                # Repo CNNs output logit for REAL (1) minus FAKE (0); negate for fake logit
                fake_logit = -cnn_model(batch).squeeze(-1).float().cpu().numpy()
                preds.append(fake_logit)
        results[run_name] = np.concatenate(preds, axis=0)

    if results:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(cache_path, filenames=rel_paths, **results)
        print(f"Saved CNN logits cache to {cache_path}", file=sys.stderr)
    return results


def confusion_at_threshold(probs: list[float] | np.ndarray, labels: list[int] | np.ndarray, threshold: float) -> dict:
    probs_arr = np.asarray(probs, dtype=np.float64)
    labels_arr = np.asarray(labels, dtype=np.int64)
    pred_fake = probs_arr >= threshold
    truth_fake = labels_arr == 1
    tp = int(np.sum(pred_fake & truth_fake))
    fp = int(np.sum(pred_fake & ~truth_fake))
    fn = int(np.sum(~pred_fake & truth_fake))
    tn = int(np.sum(~pred_fake & ~truth_fake))
    correct = tp + tn
    total = int(len(labels_arr))
    try:
        auc = round(float(roc_auc_score(labels_arr, probs_arr)), 6)
    except ValueError:
        auc = None
    return {
        "threshold": round(float(threshold), 4),
        "accuracy": round(correct / total, 6) if total else 0.0,
        "roc_auc": auc,
        "correct": correct,
        "n": total,
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "fake_precision": round(tp / (tp + fp), 6) if tp + fp else None,
        "fake_recall": round(tp / (tp + fn), 6) if tp + fn else None,
    }


def sweep_threshold(probs: list[float] | np.ndarray, labels: list[int] | np.ndarray) -> tuple[float, dict]:
    probs_arr = np.asarray(probs, dtype=np.float64)
    labels_arr = np.asarray(labels, dtype=np.int64)
    best_threshold = 0.5
    best_acc = -1.0
    for step in range(1, 100):
        threshold = step / 100.0
        acc = float(np.mean((probs_arr >= threshold) == (labels_arr == 1)))
        if acc > best_acc:
            best_acc = acc
            best_threshold = threshold
    best_metrics = confusion_at_threshold(probs_arr, labels_arr, best_threshold)
    return best_threshold, best_metrics


def stratified_split(
    samples: list[tuple[Path, int]],
    *,
    val_fraction: float,
    seed: int,
) -> tuple[list[int], list[int]]:
    by_label: dict[int, list[int]] = {0: [], 1: []}
    for index, (_, label) in enumerate(samples):
        by_label[label].append(index)
    rng = random.Random(seed)
    val_indices: list[int] = []
    test_indices: list[int] = []
    for label in (0, 1):
        indices = by_label[label][:]
        rng.shuffle(indices)
        val_count = int(len(indices) * val_fraction)
        val_indices.extend(indices[:val_count])
        test_indices.extend(indices[val_count:])
    val_indices.sort()
    test_indices.sort()
    return val_indices, test_indices


def identity_safe_split(
    samples: list[tuple[Path, int]],
    root: Path,
    *,
    val_fraction: float,
    seed: int,
) -> tuple[list[int], list[int]] | None:
    """Split by connected identity components from metadata.csv so no face leaks across splits."""
    metadata_path = root / "metadata.csv"
    if not metadata_path.is_file():
        return None

    rel_to_idx = {p.relative_to(root).as_posix(): idx for idx, (p, _) in enumerate(samples)}
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    rows: list[tuple[int, int, str]] = []
    with metadata_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            fk = Path(row["fake_file"]).as_posix()
            rl = Path(row["real_file"]).as_posix()
            if fk not in rel_to_idx or rl not in rel_to_idx:
                continue
            src_id = f"id:{row['source_identity']}"
            tgt_id = f"id:{row['target_face']}"
            union(src_id, tgt_id)
            rows.append((rel_to_idx[fk], rel_to_idx[rl], src_id))

    comp_to_indices: dict[str, list[int]] = {}
    for fk_idx, rl_idx, key in rows:
        comp = find(key)
        comp_to_indices.setdefault(comp, []).extend([fk_idx, rl_idx])

    groups = list(comp_to_indices.values())
    rng = random.Random(seed)
    rng.shuffle(groups)

    target_val = int(len(samples) * val_fraction)
    val_indices: list[int] = []
    test_indices: list[int] = []
    for g in groups:
        if len(val_indices) < target_val:
            val_indices.extend(g)
        else:
            test_indices.extend(g)
    val_indices.sort()
    test_indices.sort()
    return val_indices, test_indices


def evaluate_probes_on_split(
    feats: dict[str, np.ndarray],
    cnn_logits: dict[str, np.ndarray],
    labels: np.ndarray,
    train_idx: list[int],
    test_idx: list[int],
) -> dict:
    cls_orig = feats["cls_orig"]
    cls_flip = feats["cls_flip"]
    patch_mean = feats["patch_mean"]
    patch_std = feats["patch_std"]
    logit_orig = feats["logit_orig"]
    logit_flip = feats["logit_flip"]

    # 1. Zero-shot logit averaging vs prob averaging
    prob_avg = (1.0 / (1.0 + np.exp(-logit_orig)) + 1.0 / (1.0 + np.exp(-logit_flip))) / 2.0
    logit_avg_prob = 1.0 / (1.0 + np.exp(-0.5 * (logit_orig + logit_flip)))

    best_t_prob, _ = sweep_threshold(prob_avg[train_idx], labels[train_idx])
    best_t_logit, _ = sweep_threshold(logit_avg_prob[train_idx], labels[train_idx])

    # Build rich ViT representation: [CLS_mean, |CLS_diff|, patch_mean, patch_std, logit_orig, logit_flip]
    cls_mean = 0.5 * (cls_orig + cls_flip)
    cls_diff = np.abs(cls_orig - cls_flip)
    x_cls_only = cls_mean
    x_vit_rich = np.concatenate(
        [
            cls_mean,
            cls_diff,
            patch_mean,
            patch_std,
            logit_orig[:, None],
            logit_flip[:, None],
        ],
        axis=1,
    )

    y_train = labels[train_idx]
    y_test = labels[test_idx]

    results: dict = {
        "zero_shot_prob_tta_at_0.5": confusion_at_threshold(prob_avg[test_idx], y_test, 0.5),
        "zero_shot_prob_tta_swept": confusion_at_threshold(prob_avg[test_idx], y_test, best_t_prob),
        "zero_shot_logit_tta_swept": confusion_at_threshold(
            logit_avg_prob[test_idx], y_test, best_t_logit
        ),
    }

    # 2. Linear Probe on [CLS] (384-d)
    clf_cls = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=0.1, max_iter=1000, random_state=SPLIT_SEED),
    )
    clf_cls.fit(x_cls_only[train_idx], y_train)
    p_cls_train = clf_cls.predict_proba(x_cls_only[train_idx])[:, 1]
    p_cls_test = clf_cls.predict_proba(x_cls_only[test_idx])[:, 1]
    t_cls, _ = sweep_threshold(p_cls_train, y_train)
    results["vit_cls_linear_probe"] = confusion_at_threshold(p_cls_test, y_test, t_cls)

    # 3. Linear Probe on Rich ViT features ([CLS] + flip diff + patch mean/std + logits = 1538-d)
    clf_rich = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=0.05, max_iter=1000, random_state=SPLIT_SEED),
    )
    clf_rich.fit(x_vit_rich[train_idx], y_train)
    p_rich_train = clf_rich.predict_proba(x_vit_rich[train_idx])[:, 1]
    p_rich_test = clf_rich.predict_proba(x_vit_rich[test_idx])[:, 1]
    t_rich, _ = sweep_threshold(p_rich_train, y_train)
    results["vit_rich_linear_probe"] = confusion_at_threshold(p_rich_test, y_test, t_rich)

    # 4. MLP Probe (2-layer) on Rich ViT features
    mlp_rich = make_pipeline(
        StandardScaler(),
        MLPClassifier(
            hidden_layer_sizes=(256, 64),
            alpha=1.0,
            early_stopping=True,
            validation_fraction=0.1,
            max_iter=80,
            random_state=SPLIT_SEED,
        ),
    )
    mlp_rich.fit(x_vit_rich[train_idx], y_train)
    p_mlp_train = mlp_rich.predict_proba(x_vit_rich[train_idx])[:, 1]
    p_mlp_test = mlp_rich.predict_proba(x_vit_rich[test_idx])[:, 1]
    t_mlp, _ = sweep_threshold(p_mlp_train, y_train)
    results["vit_rich_mlp_probe"] = confusion_at_threshold(p_mlp_test, y_test, t_mlp)

    # 5. Blend ViT Linear + MLP Probe
    p_vit_blend_train = 0.5 * (p_rich_train + p_mlp_train)
    p_vit_blend_test = 0.5 * (p_rich_test + p_mlp_test)
    t_blend, _ = sweep_threshold(p_vit_blend_train, y_train)
    results["vit_linear_plus_mlp_blend"] = confusion_at_threshold(
        p_vit_blend_test, y_test, t_blend
    )

    # 6. If external CNN checkpoints exist, evaluate them + fusion with ViT
    if "inception_resnet_v1_140k" in cnn_logits:
        inc_140k = cnn_logits["inception_resnet_v1_140k"]
        inc_prob = 1.0 / (1.0 + np.exp(-inc_140k))
        results["inception_140k_zero_shot"] = confusion_at_threshold(
            inc_prob[test_idx], y_test, 0.5
        )
        # Out-of-domain ensemble: ViT rich features + Inception-140k (trained only on 140k faces)
        x_ood_ens = np.concatenate([x_vit_rich, inc_140k[:, None]], axis=1)
        mlp_ens = make_pipeline(
            StandardScaler(),
            MLPClassifier(
                hidden_layer_sizes=(256, 64),
                alpha=1.0,
                early_stopping=True,
                validation_fraction=0.1,
                max_iter=80,
                random_state=SPLIT_SEED,
            ),
        )
        mlp_ens.fit(x_ood_ens[train_idx], y_train)
        p_ens_train = 0.5 * (p_rich_train + mlp_ens.predict_proba(x_ood_ens[train_idx])[:, 1])
        p_ens_test = 0.5 * (p_rich_test + mlp_ens.predict_proba(x_ood_ens[test_idx])[:, 1])
        t_ens, _ = sweep_threshold(p_ens_train, y_train)
        results["vit_plus_inception140k_ensemble"] = confusion_at_threshold(
            p_ens_test, y_test, t_ens
        )

    return results


def eval_deepfake(
    model: ViTForImageClassification,
    processor: ViTImageProcessor,
    device: torch.device,
    *,
    root: Path,
    threshold: float,
    tta: bool,
    do_split: bool,
    rebuild_cache: bool = False,
    output_path: Path | None,
) -> dict:
    samples = load_deepfake_samples(root)
    paths = [path for path, _ in samples]
    labels = [label for _, label in samples]
    labels_arr = np.array(labels, dtype=np.int64)

    feats = extract_or_load_vit_features(
        paths,
        labels,
        model,
        processor,
        device,
        rebuild_cache=rebuild_cache,
    )
    logit_orig = feats["logit_orig"]
    logit_flip = feats["logit_flip"]
    prob_orig = 1.0 / (1.0 + np.exp(-logit_orig))
    prob_flip = 1.0 / (1.0 + np.exp(-logit_flip))
    fake_probs = (0.5 * (prob_orig + prob_flip)) if tta else prob_orig

    summary: dict = {
        "model_id": MODEL_ID,
        "dataset_root": str(root.resolve()),
        "weights_dtype": "float32",
        "preprocessing": processor_summary(processor),
        "tta_horizontal_flip": tta,
        "batch_size": EVAL_BATCH_SIZE,
        "n_images": len(samples),
        "n_fake": sum(labels),
        "n_real": len(labels) - sum(labels),
    }

    baseline_full = confusion_at_threshold(fake_probs, labels_arr, threshold)
    summary["baseline_threshold"] = baseline_full

    if do_split:
        val_idx, test_idx = stratified_split(samples, val_fraction=VAL_FRACTION, seed=SPLIT_SEED)
        val_probs = fake_probs[val_idx]
        val_labels = labels_arr[val_idx]
        test_probs = fake_probs[test_idx]
        test_labels = labels_arr[test_idx]

        best_t, val_metrics = sweep_threshold(val_probs, val_labels)
        test_metrics = confusion_at_threshold(test_probs, test_labels, best_t)
        full_tuned = confusion_at_threshold(fake_probs, labels_arr, best_t)

        summary["split"] = {
            "seed": SPLIT_SEED,
            "val_fraction": VAL_FRACTION,
            "n_val": len(val_idx),
            "n_test": len(test_idx),
        }
        summary["threshold_sweep_on_val"] = val_metrics
        summary["best_threshold"] = best_t
        summary["test_at_best_threshold"] = test_metrics
        summary["full_dataset_at_best_threshold"] = full_tuned

        cnn_logits = extract_or_load_cnn_logits(paths, device, rebuild_cache=rebuild_cache)

        summary["advanced_methods_stratified_test"] = evaluate_probes_on_split(
            feats, cnn_logits, labels_arr, val_idx, test_idx
        )

        id_split = identity_safe_split(samples, root, val_fraction=VAL_FRACTION, seed=SPLIT_SEED)
        if id_split is not None:
            id_train_idx, id_test_idx = id_split
            summary["identity_safe_split"] = {
                "seed": SPLIT_SEED,
                "n_train": len(id_train_idx),
                "n_test": len(id_test_idx),
                "methods_on_held_out_identities": evaluate_probes_on_split(
                    feats, cnn_logits, labels_arr, id_train_idx, id_test_idx
                ),
            }
    else:
        summary["threshold"] = threshold

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def _build_rich_matrix(feats: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cls_orig = feats["cls_orig"]
    cls_flip = feats["cls_flip"]
    patch_mean = feats["patch_mean"]
    patch_std = feats["patch_std"]
    logit_orig = feats["logit_orig"]
    logit_flip = feats["logit_flip"]

    prob_avg = (1.0 / (1.0 + np.exp(-logit_orig)) + 1.0 / (1.0 + np.exp(-logit_flip))) / 2.0
    cls_mean = 0.5 * (cls_orig + cls_flip)
    cls_diff = np.abs(cls_orig - cls_flip)
    x_rich = np.concatenate(
        [
            cls_mean,
            cls_diff,
            patch_mean,
            patch_std,
            logit_orig[:, None],
            logit_flip[:, None],
        ],
        axis=1,
    )
    return prob_avg, cls_mean, x_rich


def _subsample_balanced(
    samples: list[tuple[Path, int]],
    max_per_class: int | None,
    seed: int = SPLIT_SEED,
) -> list[tuple[Path, int]]:
    if max_per_class is None:
        return samples
    by_label: dict[int, list[tuple[Path, int]]] = {0: [], 1: []}
    for item in samples:
        by_label[item[1]].append(item)
    rng = random.Random(seed)
    out: list[tuple[Path, int]] = []
    for label in (1, 0):
        bucket = by_label[label][:]
        if len(bucket) > max_per_class:
            rng.shuffle(bucket)
            bucket = sorted(bucket[:max_per_class], key=lambda x: x[0])
        out.extend(bucket)
    return out


def eval_cross_dataset(
    model: ViTForImageClassification,
    processor: ViTImageProcessor,
    device: torch.device,
    *,
    rebuild_cache: bool = False,
    output_path: Path = Path("results/community_forensics_vit_cross_dataset_eval.json"),
) -> dict:
    """Train probes ONLY on data/Deepfake, then evaluate zero-shot on unseen datasets."""
    src_samples = load_deepfake_samples(DEEPFAKE_ROOT)
    src_paths = [p for p, _ in src_samples]
    src_labels = np.array([lbl for _, lbl in src_samples], dtype=np.int64)
    src_feats = extract_or_load_vit_features(
        src_paths,
        src_labels.tolist(),
        model,
        processor,
        device,
        cache_path=FEATURE_CACHE_PATH,
        rebuild_cache=rebuild_cache,
    )
    src_prob_avg, src_cls, src_rich = _build_rich_matrix(src_feats)

    # Fit probes on 100% of data/Deepfake
    clf_cls = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=0.05, max_iter=1000, random_state=SPLIT_SEED),
    )
    clf_cls.fit(src_cls, src_labels)

    clf_rich_c001 = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=0.01, max_iter=1000, random_state=SPLIT_SEED),
    )
    clf_rich_c001.fit(src_rich, src_labels)

    clf_rich_pca = make_pipeline(
        StandardScaler(),
        PCA(n_components=64, random_state=SPLIT_SEED),
        LogisticRegression(C=0.01, max_iter=1000, random_state=SPLIT_SEED),
    )
    clf_rich_pca.fit(src_rich, src_labels)

    mlp_rich = make_pipeline(
        StandardScaler(),
        MLPClassifier(
            hidden_layer_sizes=(256, 64),
            alpha=2.0,
            early_stopping=True,
            validation_fraction=0.1,
            max_iter=80,
            random_state=SPLIT_SEED,
        ),
    )
    mlp_rich.fit(src_rich, src_labels)

    data_root = DEEPFAKE_ROOT.parent
    benchmarks: list[tuple[str, Path, int | None]] = [
        ("sdfvd_face_frames_val", data_root / "sdfvd_face_frames" / "val", None),
        ("df40_face_crops_unpaired", data_root / "DF40_face_crops_unpaired", 1000),
        ("real_vs_fake_140k_test", data_root / "real-vs-fake" / "test", 1000),
    ]

    cross_results: dict[str, dict] = {}
    all_target_feats: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}

    for name, folder, max_per_class in benchmarks:
        if not folder.is_dir():
            continue
        raw_samples = load_deepfake_samples(folder)
        samples = _subsample_balanced(raw_samples, max_per_class=max_per_class, seed=SPLIT_SEED)
        paths = [p for p, _ in samples]
        labels = np.array([lbl for _, lbl in samples], dtype=np.int64)
        cache_file = MODEL_CACHE / f"cross_{name}_features.npz"
        feats = extract_or_load_vit_features(
            paths,
            labels.tolist(),
            model,
            processor,
            device,
            cache_path=cache_file,
            rebuild_cache=rebuild_cache,
        )
        prob_zs, x_cls, x_rich = _build_rich_matrix(feats)
        all_target_feats[name] = (prob_zs, x_cls, x_rich, labels)

        p_cls = clf_cls.predict_proba(x_cls)[:, 1]
        p_rich_c001 = clf_rich_c001.predict_proba(x_rich)[:, 1]
        p_rich_pca = clf_rich_pca.predict_proba(x_rich)[:, 1]
        p_mlp = mlp_rich.predict_proba(x_rich)[:, 1]

        # Guard 1: Anchor blend (0.5 * stock zero-shot ViT + 0.5 * probe)
        p_anchor_cls = 0.5 * prob_zs + 0.5 * p_cls
        p_anchor_c001 = 0.5 * prob_zs + 0.5 * p_rich_c001
        p_anchor_pca = 0.5 * prob_zs + 0.5 * p_rich_pca
        p_anchor_mlp = 0.5 * prob_zs + 0.5 * p_mlp

        cross_results[name] = {
            "dataset_path": str(folder.resolve()),
            "n_images": int(len(labels)),
            "n_fake": int(np.sum(labels == 1)),
            "n_real": int(np.sum(labels == 0)),
            "zero_shot_vit_tta": confusion_at_threshold(prob_zs, labels, 0.5),
            "deepfake_trained_cls_probe": confusion_at_threshold(p_cls, labels, 0.5),
            "deepfake_trained_rich_c001_probe": confusion_at_threshold(p_rich_c001, labels, 0.5),
            "deepfake_trained_pca64_c001_probe": confusion_at_threshold(p_rich_pca, labels, 0.5),
            "deepfake_trained_rich_mlp_probe": confusion_at_threshold(p_mlp, labels, 0.5),
            "anchor_blend_zs_plus_cls_probe": confusion_at_threshold(p_anchor_cls, labels, 0.5),
            "anchor_blend_zs_plus_rich_c001": confusion_at_threshold(p_anchor_c001, labels, 0.5),
            "anchor_blend_zs_plus_pca64_c001": confusion_at_threshold(p_anchor_pca, labels, 0.5),
            "anchor_blend_zs_plus_rich_mlp": confusion_at_threshold(p_anchor_mlp, labels, 0.5),
        }

    # Guard 3: Multi-Dataset Universal Probe (80% train / 20% test across all datasets combined)
    multi_x_train, multi_y_train = [], []
    multi_test_splits: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

    df_val_idx, df_test_idx = stratified_split(src_samples, val_fraction=0.8, seed=SPLIT_SEED)
    multi_x_train.append(src_rich[df_val_idx])
    multi_y_train.append(src_labels[df_val_idx])
    multi_test_splits["Deepfake"] = (
        src_prob_avg[df_test_idx],
        src_rich[df_test_idx],
        src_labels[df_test_idx],
    )

    for name, (prob_zs, _x_cls, x_rich, labels) in all_target_feats.items():
        dummy_samples = [(Path(str(i)), int(lbl)) for i, lbl in enumerate(labels)]
        tr_idx, te_idx = stratified_split(dummy_samples, val_fraction=0.8, seed=SPLIT_SEED)
        multi_x_train.append(x_rich[tr_idx])
        multi_y_train.append(labels[tr_idx])
        multi_test_splits[name] = (prob_zs[te_idx], x_rich[te_idx], labels[te_idx])

    x_univ_train = np.concatenate(multi_x_train, axis=0)
    y_univ_train = np.concatenate(multi_y_train, axis=0)

    univ_lin = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=0.01, max_iter=1000, random_state=SPLIT_SEED),
    )
    univ_lin.fit(x_univ_train, y_univ_train)

    univ_pca = make_pipeline(
        StandardScaler(),
        PCA(n_components=128, random_state=SPLIT_SEED),
        LogisticRegression(C=0.01, max_iter=1000, random_state=SPLIT_SEED),
    )
    univ_pca.fit(x_univ_train, y_univ_train)

    univ_mlp = make_pipeline(
        StandardScaler(),
        MLPClassifier(
            hidden_layer_sizes=(256, 64),
            alpha=1.0,
            early_stopping=True,
            validation_fraction=0.1,
            max_iter=80,
            random_state=SPLIT_SEED,
        ),
    )
    univ_mlp.fit(x_univ_train, y_univ_train)

    universal_results: dict[str, dict] = {}
    for ds_name, (prob_zs_te, x_te, y_te) in multi_test_splits.items():
        p_ulin = univ_lin.predict_proba(x_te)[:, 1]
        p_upca = univ_pca.predict_proba(x_te)[:, 1]
        p_umlp = univ_mlp.predict_proba(x_te)[:, 1]
        p_uanchor = 0.5 * prob_zs_te + 0.5 * p_umlp
        universal_results[ds_name] = {
            "n_test": int(len(y_te)),
            "zero_shot_vit_tta": confusion_at_threshold(prob_zs_te, y_te, 0.5),
            "universal_linear_c001": confusion_at_threshold(p_ulin, y_te, 0.5),
            "universal_pca128_c001": confusion_at_threshold(p_upca, y_te, 0.5),
            "universal_mlp_probe": confusion_at_threshold(p_umlp, y_te, 0.5),
            "universal_anchor_blend": confusion_at_threshold(p_uanchor, y_te, 0.5),
        }

    report = {
        "model_id": MODEL_ID,
        "source_training_dataset": str(DEEPFAKE_ROOT.resolve()),
        "cross_dataset_zero_shot_transfer": cross_results,
        "universal_multi_dataset_probe_test": universal_results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    return report


def run_interactive(
    model: ViTForImageClassification,
    processor: ViTImageProcessor,
    device: torch.device,
    *,
    threshold: float,
    tta: bool,
) -> None:
    print("Model loaded. Enter image paths (empty line or Ctrl-D to quit).", file=sys.stderr)
    while True:
        try:
            line = input("image> ").strip()
        except EOFError:
            print(file=sys.stderr)
            break
        if not line:
            break
        path = Path(line)
        try:
            print(
                json.dumps(
                    score_image(path, model, processor, device, threshold=threshold, tta=tta),
                    separators=(",", ":"),
                )
            )
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Score images with CommunityForensics DeepfakeDet-ViT")
    parser.add_argument("images", nargs="*", help="Image paths (default: FORENSIC_IMAGE or sample)")
    parser.add_argument("-i", "--interactive", action="store_true", help="REPL scoring loop")
    parser.add_argument(
        "--eval-deepfake",
        action="store_true",
        help="Eval data/Deepfake with FP32, TTA, feature caching, probes, and ensemble",
    )
    parser.add_argument(
        "--eval-output",
        type=Path,
        default=Path("results/community_forensics_vit_deepfake_eval.json"),
    )
    parser.add_argument(
        "--no-tta",
        action="store_true",
        help="Disable horizontal-flip test-time augmentation (average orig + flip)",
    )
    parser.add_argument(
        "--no-split",
        action="store_true",
        help="Skip 80/20 split and threshold sweep; only report baseline at FAKE_THRESHOLD",
    )
    parser.add_argument(
        "--rebuild-cache",
        action="store_true",
        help="Force recomputing cached ViT embeddings and CNN logits",
    )
    parser.add_argument(
        "--eval-cross-dataset",
        action="store_true",
        help="Test generalization of Deepfake-trained probes + universal probe on unseen datasets",
    )
    args = parser.parse_args()

    tta = not args.no_tta
    device = pick_device()
    model, processor = load_model(device)

    if args.eval_cross_dataset:
        report = eval_cross_dataset(
            model,
            processor,
            device,
            rebuild_cache=args.rebuild_cache,
        )
        print(json.dumps(report, indent=2))
        return

    if args.eval_deepfake:
        summary = eval_deepfake(
            model,
            processor,
            device,
            root=DEEPFAKE_ROOT,
            threshold=THRESHOLD,
            tta=tta,
            do_split=not args.no_split,
            rebuild_cache=args.rebuild_cache,
            output_path=args.eval_output,
        )
        print(json.dumps(summary, indent=2))
        return
    if args.interactive:
        run_interactive(model, processor, device, threshold=THRESHOLD, tta=tta)
        return

    image_paths = [Path(p) for p in args.images]
    if not image_paths:
        image_paths = [Path(os.environ.get("FORENSIC_IMAGE", DEFAULT_IMAGE))]
    run_batch(image_paths, model, processor, device, threshold=THRESHOLD, tta=tta)


if __name__ == "__main__":
    main()
