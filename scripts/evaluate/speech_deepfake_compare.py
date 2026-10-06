"""Compare Wav2Vec2 and WavLM speech deepfake results."""

from __future__ import annotations

import json
from pathlib import Path

from look_again.paths import SPEECH_DEEPFAKE_RESULTS_DIR
from look_again.speech_deepfake.config import MODEL_SHORT_NAMES, WAV2VEC2_BASE, WAVLM_BASE_PLUS


def load_test_metrics(results_dir: Path) -> dict:
    metrics_path = results_dir / "metrics.json"
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    return payload["test"]


def main() -> None:
    rows = []
    for model_name in (WAV2VEC2_BASE, WAVLM_BASE_PLUS):
        short_name = MODEL_SHORT_NAMES[model_name]
        metrics = load_test_metrics(SPEECH_DEEPFAKE_RESULTS_DIR / short_name)
        rows.append(
            {
                "model": short_name,
                "accuracy": metrics["accuracy"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "roc_auc": metrics.get("roc_auc"),
            }
        )
    header = f"{'Model':<10} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>10} {'ROC-AUC':>10}"
    print(header)
    print("-" * len(header))
    for row in rows:
        roc = "n/a" if row["roc_auc"] is None else f"{row['roc_auc']:.4f}"
        print(
            f"{row['model']:<10} {row['accuracy']:10.4f} {row['precision']:10.4f} "
            f"{row['recall']:10.4f} {row['f1']:10.4f} {roc:>10}"
        )
    output = SPEECH_DEEPFAKE_RESULTS_DIR / "comparison_summary.json"
    output.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
