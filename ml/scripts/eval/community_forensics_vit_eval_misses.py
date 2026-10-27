"""Score binary vs tertiary probes on a fixed manual eval set (miss tracking).

See ``ml/eval/misses/README.md``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from look_again.community_forensics_finetune_multiclass import (
    CLASS_NAMES,
    TertiaryProbeWeights,
    default_tertiary_weights_path,
    predict_probs_from_features,
)
from look_again.community_forensics_vit_probe import (
    DEFAULT_COREML_DIR,
    CommunityForensicsViTProbe,
    load_community_forensics_vit,
    load_probe_module_from_npz,
    rich_features_torch,
)
from look_again.hf_binary_dataset import IMAGE_EXTENSIONS
from look_again.paths import CHECKPOINT_DIR, PROJECT_ROOT, RESULTS_DIR

BINARY_THRESHOLD = 0.5
DEFAULT_BINARY_RUN = "so_fake_probe"
DEFAULT_TERTIARY_RUN = "so_fake_tertiary_probe"

EXPECTED_ALIASES: dict[str, str] = {
    "real": "real",
    "synthetic": "synthetic",
    "fake": "synthetic",
    "ai": "synthetic",
    "genai": "synthetic",
    "full_synthetic": "synthetic",
    "tampered": "tampered",
    "edited": "tampered",
    "manipulated": "tampered",
}

FOLDER_TO_CLASS: dict[str, str] = {
    "real": "real",
    "fake": "synthetic",
    "synthetic": "synthetic",
    "ai": "synthetic",
    "tampered": "tampered",
    "edited": "tampered",
}


@dataclass(frozen=True)
class EvalRow:
    path: Path
    expected: str
    note: str = ""


def normalize_expected(value: str) -> str:
    key = value.strip().lower()
    if key not in EXPECTED_ALIASES:
        raise ValueError(f"Unknown expected label {value!r}; use real | synthetic | tampered")
    return EXPECTED_ALIASES[key]


def load_manifest(path: Path) -> list[EvalRow]:
    raw = json.loads(path.read_text())
    if not isinstance(raw, list):
        raise ValueError("Manifest must be a JSON array of {path, expected, note?}")
    rows: list[EvalRow] = []
    for item in raw:
        rel = Path(item["path"])
        image_path = rel if rel.is_absolute() else (PROJECT_ROOT / rel).resolve()
        rows.append(
            EvalRow(
                path=image_path,
                expected=normalize_expected(str(item["expected"])),
                note=str(item.get("note", "")),
            )
        )
    return rows


def load_from_folders(root: Path) -> list[EvalRow]:
    root = root if root.is_absolute() else (PROJECT_ROOT / root).resolve()
    rows: list[EvalRow] = []
    for folder_name, class_name in FOLDER_TO_CLASS.items():
        folder = root / folder_name
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                rows.append(EvalRow(path=path.resolve(), expected=class_name))
    if not rows:
        raise FileNotFoundError(f"No images under {root} (expected real/ synthetic|fake/ tampered|edited/)")
    return rows


def resolve_binary_weights(run_name: str | None, weights: Path | None) -> Path:
    if weights is not None:
        p = weights if weights.is_absolute() else (PROJECT_ROOT / weights).resolve()
        if not p.is_file():
            raise FileNotFoundError(p)
        return p
    if run_name:
        p = CHECKPOINT_DIR / "community_forensics_finetune" / run_name / "community_forensics_vit_rich_probe_weights.npz"
    else:
        p = DEFAULT_COREML_DIR / "community_forensics_vit_rich_probe_weights.npz"
    if not p.is_file():
        raise FileNotFoundError(f"Binary weights not found: {p}")
    return p


def resolve_tertiary_weights(run_name: str | None, weights: Path | None) -> Path:
    if weights is not None:
        p = weights if weights.is_absolute() else (PROJECT_ROOT / weights).resolve()
        if not p.is_file():
            raise FileNotFoundError(p)
        return p
    name = run_name or DEFAULT_TERTIARY_RUN
    p = default_tertiary_weights_path(name)
    if not p.is_file():
        raise FileNotFoundError(f"Tertiary weights not found: {p}")
    return p


def pick_device(requested: str | None) -> torch.device:
    if requested:
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def binary_predicted_class(fake_prob: float) -> str:
    if fake_prob >= BINARY_THRESHOLD:
        return "synthetic"
    return "real"


def tertiary_predicted_class(probs: np.ndarray) -> str:
    index = int(np.argmax(probs))
    return CLASS_NAMES[index] if index < len(CLASS_NAMES) else str(index)


def predict_one(
    image_path: Path,
    *,
    backbone: torch.nn.Module,
    processor,
    binary_module: CommunityForensicsViTProbe,
    tertiary_weights: TertiaryProbeWeights,
    device: torch.device,
) -> dict:
    image = Image.open(image_path).convert("RGB")
    pixels = processor(images=image, return_tensors="pt")["pixel_values"].float().to(device)
    with torch.inference_mode():
        features = rich_features_torch(backbone.vit, backbone.classifier, pixels)
        fake_prob = float(binary_module(pixels).reshape(-1).cpu())
    fake_prob = float(np.clip(fake_prob, 0.0, 1.0))
    t_probs = predict_probs_from_features(features.cpu().numpy(), tertiary_weights)[0]
    return {
        "binary_fake_prob": fake_prob,
        "binary_pred": binary_predicted_class(fake_prob),
        "tertiary_pred": tertiary_predicted_class(t_probs),
        "prob_real": float(t_probs[0]),
        "prob_synthetic": float(t_probs[1]),
        "prob_tampered": float(t_probs[2]) if t_probs.size > 2 else None,
    }


def score_row(expected: str, binary_pred: str, tertiary_pred: str) -> dict[str, bool]:
    binary_ok = binary_pred == expected or (
        expected == "tampered" and binary_pred == "synthetic"
    )
    tertiary_ok = tertiary_pred == expected
    binary_miss = not binary_ok
    tertiary_miss = not tertiary_ok
    tertiary_fixed = binary_miss and tertiary_ok
    return {
        "binary_ok": binary_ok,
        "tertiary_ok": tertiary_ok,
        "binary_miss": binary_miss,
        "tertiary_miss": tertiary_miss,
        "tertiary_fixed": tertiary_fixed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Track binary vs tertiary misses on a manual set")
    parser.add_argument("--manifest", type=Path, help="JSON list of {path, expected, note?}")
    parser.add_argument(
        "--dataset-root",
        type=Path,
        help="Folder with real/ synthetic|fake/ tampered|edited/ subdirs",
    )
    parser.add_argument("--binary-run-name", default=DEFAULT_BINARY_RUN)
    parser.add_argument("--binary-weights", type=Path, default=None)
    parser.add_argument("--tertiary-run-name", default=DEFAULT_TERTIARY_RUN)
    parser.add_argument("--tertiary-weights", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None, help="JSON report path")
    parser.add_argument("--device", default=None)
    args = parser.parse_args()

    if args.manifest and args.dataset_root:
        print("Use only one of --manifest or --dataset-root", file=sys.stderr)
        sys.exit(1)
    if args.manifest:
        rows = load_manifest(args.manifest if args.manifest.is_absolute() else PROJECT_ROOT / args.manifest)
    elif args.dataset_root:
        rows = load_from_folders(args.dataset_root)
    else:
        default_manifest = PROJECT_ROOT / "data" / "eval_misses" / "manifest.json"
        if default_manifest.is_file():
            rows = load_manifest(default_manifest)
        else:
            print(
                "Provide --manifest or --dataset-root (see ml/eval/misses/README.md)",
                file=sys.stderr,
            )
            sys.exit(1)

    device = pick_device(args.device)
    binary_path = resolve_binary_weights(args.binary_run_name, args.binary_weights)
    tertiary_path = resolve_tertiary_weights(args.tertiary_run_name, args.tertiary_weights)

    backbone, processor = load_community_forensics_vit(device)
    binary_module = load_probe_module_from_npz(binary_path, device, CommunityForensicsViTProbe)
    tertiary_weights = TertiaryProbeWeights.from_npz(tertiary_path)

    results: list[dict] = []
    for row in rows:
        if not row.path.is_file():
            print(f"skip missing: {row.path}", file=sys.stderr)
            continue
        preds = predict_one(
            row.path,
            backbone=backbone,
            processor=processor,
            binary_module=binary_module,
            tertiary_weights=tertiary_weights,
            device=device,
        )
        flags = score_row(row.expected, preds["binary_pred"], preds["tertiary_pred"])
        entry = {
            "path": str(row.path),
            "note": row.note,
            "expected": row.expected,
            **preds,
            **flags,
        }
        results.append(entry)

    n = len(results)
    summary = {
        "n_images": n,
        "binary_correct": sum(1 for r in results if r["binary_ok"]),
        "tertiary_correct": sum(1 for r in results if r["tertiary_ok"]),
        "binary_misses": sum(1 for r in results if r["binary_miss"]),
        "tertiary_misses": sum(1 for r in results if r["tertiary_miss"]),
        "tertiary_fixed_binary_miss": sum(1 for r in results if r["tertiary_fixed"]),
        "binary_weights": str(binary_path),
        "tertiary_weights": str(tertiary_path),
    }

    out_path = args.output
    if out_path is None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = RESULTS_DIR / f"misses_{stamp}.json"
    else:
        out_path = out_path if out_path.is_absolute() else (PROJECT_ROOT / out_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

    report = {"summary": summary, "rows": results}
    out_path.write_text(json.dumps(report, indent=2) + "\n")

    print(f"report: {out_path}")
    print(
        f"summary: binary {summary['binary_correct']}/{n} ok | "
        f"tertiary {summary['tertiary_correct']}/{n} ok | "
        f"tertiary fixed {summary['tertiary_fixed_binary_miss']} binary misses"
    )
    print()
    print(f"{'expected':10} {'binary':10} {'tertiary':10}  {'fake_p':>6}  {'tamp':>6}  note")
    print("-" * 72)
    for r in results:
        mark = " *" if r["tertiary_fixed"] else (" !" if r["binary_miss"] and r["tertiary_miss"] else "")
        note = (r["note"] or Path(r["path"]).name)[:40]
        print(
            f"{r['expected']:10} {r['binary_pred']:10} {r['tertiary_pred']:10}  "
            f"{r['binary_fake_prob']:6.3f}  {r['prob_tampered'] or 0:6.3f}  {note}{mark}"
        )
    print("  * = tertiary fixed a binary miss")


if __name__ == "__main__":
    main()
