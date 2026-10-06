"""Train classical classifiers on precomputed Mix audio features."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from look_again.audio_ml.data import load_parquet_feature_splits
from look_again.classical_ml.evaluation import evaluate_model, print_comparison_table, write_results
from look_again.classical_ml.models import parameter_grids, xgboost_available
from look_again.classical_ml.training import train_model
from look_again.paths import CHECKPOINT_DIR, DEFAULT_AUDIO_FEATURES_PARQUET, RESULTS_DIR

AUDIO_MODELS = ("random_forest", "svm", "xgboost")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        choices=("all", *AUDIO_MODELS),
        default="random_forest",
        help="Fit one model or compare random_forest, svm, and xgboost on validation.",
    )
    parser.add_argument(
        "--features-parquet",
        type=Path,
        default=DEFAULT_AUDIO_FEATURES_PARQUET,
        help="Parquet table from scripts.prepare.build_audio_features.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--validation-size", type=float, default=0.15)
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Stratified cap on rows loaded from the feature table (debug/smoke runs).",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=RESULTS_DIR / "classical_ml" / "audio",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=CHECKPOINT_DIR,
    )
    parser.add_argument(
        "--tune",
        action="store_true",
        help="Run grouped GridSearchCV on the training split before validation scoring.",
    )
    parser.add_argument("--cv-folds", type=int, default=3)
    parser.add_argument(
        "--eval-test",
        action="store_true",
        help="Fit on train+validation and evaluate the held-out test split.",
    )
    parser.add_argument("--config", type=Path, help="JSON map of model name to hyperparameters.")
    return parser.parse_args()


def _feature_importance_json(model, names: tuple[str, ...], *, limit: int = 25) -> dict[str, Any] | None:
    estimator = model
    if hasattr(model, "named_steps"):
        estimator = model.named_steps.get("classifier", model)
    if not hasattr(estimator, "feature_importances_"):
        return None
    importances = np.asarray(estimator.feature_importances_, dtype=np.float64)
    order = np.argsort(importances)[::-1][:limit]
    return {
        "top_features": [
            {"name": names[index], "importance": float(importances[index])} for index in order
        ]
    }


def _resolve_models(requested: str) -> list[str]:
    if requested == "all":
        models = list(AUDIO_MODELS)
    else:
        models = [requested]
    if not xgboost_available() and "xgboost" in models:
        if requested == "xgboost":
            raise ImportError("XGBoost missing. Install with `uv sync --extra xgboost`.")
        models.remove("xgboost")
        print("Skipping xgboost: optional dependency missing (`uv sync --extra xgboost`).")
    return models


def _fit_and_evaluate(
    model_name: str,
    *,
    features_parquet: Path,
    train,
    validation,
    test,
    eval_test: bool,
    tune: bool,
    cv_folds: int,
    seed: int,
    model_config: dict[str, Any],
    checkpoint_dir: Path,
    results_dir: Path,
) -> dict[str, Any]:
    if eval_test:
        assert test is not None
        X_fit = np.concatenate((train.X, validation.X), axis=0)
        y_fit = np.concatenate((train.y, validation.y), axis=0)
        groups_fit = np.concatenate((train.group_ids, validation.group_ids), axis=0)
        X_eval, y_eval = test.X, test.y
        eval_name = "test"
    else:
        X_fit, y_fit, groups_fit = train.X, train.y, train.group_ids
        X_eval, y_eval = validation.X, validation.y
        eval_name = "validation"

    param_grid = parameter_grids().get(model_name) if tune else None
    artifact_path = checkpoint_dir / f"audio_{model_name}_best.joblib"
    result = train_model(
        model_name,
        X_fit,
        y_fit,
        X_eval,
        y_eval,
        model_config,
        groups=groups_fit if tune else None,
        class_names=train.class_names,
        feature_config={"source": "audio_features_parquet"},
        feature_name_list=train.feature_names,
        random_state=seed,
        artifact_path=artifact_path,
        param_grid=param_grid,
        cv_folds=cv_folds,
    )
    metrics = result.validation_metrics
    if metrics is None:
        metrics = evaluate_model(
            result.model,
            X_eval,
            y_eval,
            train.class_names,
            model_name=f"audio_{model_name}_{eval_name}",
        )

    model_results_dir = results_dir / model_name
    model_results_dir.mkdir(parents=True, exist_ok=True)
    write_results([metrics], model_results_dir, f"{model_name}_{eval_name}")
    importance = _feature_importance_json(result.model, train.feature_names)
    if importance is not None:
        (model_results_dir / "feature_importance.json").write_text(
            json.dumps(importance, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    summary = {
        "model": model_name,
        "features_parquet": str(features_parquet.resolve()),
        "eval_split": eval_name,
        "artifact": str(artifact_path.resolve()),
        "metrics": metrics,
        "best_params": result.best_params,
        "best_cv_f1_macro": result.best_cv_score,
        "fit_seconds": result.fit_seconds,
    }
    (model_results_dir / "training_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    args = parse_args()
    if args.cv_folds < 2:
        raise ValueError("--cv-folds must be at least 2")
    model_configs: dict[str, Any] = {}
    if args.config:
        model_configs = json.loads(args.config.read_text(encoding="utf-8"))
        if not isinstance(model_configs, dict):
            raise ValueError("Model configuration file must contain a JSON object")

    models = _resolve_models(args.model)
    print(f"Feature table: {args.features_parquet.resolve()}")
    train, validation, test = load_parquet_feature_splits(
        args.features_parquet,
        test_size=args.test_size,
        validation_size=args.validation_size,
        seed=args.seed,
        max_samples=args.max_samples,
        include_test=args.eval_test or args.model != "all",
    )
    print(
        f"Train rows: {len(train.y)}; validation rows: {len(validation.y)}; "
        f"test rows: {len(test.y) if test is not None else 'not loaded'}; "
        f"features: {train.X.shape[1]}"
    )
    for split_name, split in ("train", train), ("validation", validation):
        counts = Counter(split.y.tolist())
        print(
            f"  {split_name}: "
            + ", ".join(
                f"{split.class_names[index]}={counts[index]}"
                for index in range(len(split.class_names))
            )
        )

    summaries: list[dict[str, Any]] = []
    comparison_metrics: list[dict[str, Any]] = []
    for model_name in models:
        print(f"\n=== Training {model_name} ===")
        summary = _fit_and_evaluate(
            model_name,
            features_parquet=args.features_parquet,
            train=train,
            validation=validation,
            test=test,
            eval_test=args.eval_test,
            tune=args.tune,
            cv_folds=args.cv_folds,
            seed=args.seed,
            model_config=model_configs.get(model_name, {}),
            checkpoint_dir=args.checkpoint_dir,
            results_dir=args.results_dir,
        )
        summaries.append(summary)
        comparison_metrics.append(summary["metrics"])

    args.results_dir.mkdir(parents=True, exist_ok=True)
    (args.results_dir / "run_summaries.json").write_text(
        json.dumps(summaries, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if len(comparison_metrics) > 1:
        print_comparison_table(comparison_metrics)
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
