"""Train and compare classical image-forensics models on shared features."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from look_again.paths import CACHE_DIR, RESULTS_DIR
from look_again.classical_ml.data import load_and_extract_dataset
from look_again.classical_ml.evaluation import (
    evaluate_model,
    feature_importance_report,
    print_comparison_table,
    save_feature_importance_plot,
    save_grid_search_outputs,
    save_model_comparison_visualizations,
    write_results,
)
from look_again.classical_ml.features import FEATURE_ORDER, FeatureConfig, feature_names
from look_again.classical_ml.models import (
    BASE_MODEL_NAMES,
    ENSEMBLE_NAMES,
    MODEL_NAMES,
    parameter_grids,
    xgboost_available,
)
from look_again.classical_ml.training import train_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        choices=("all", *MODEL_NAMES),
        default="logistic",
        help="Compare all models on validation, or fit one model and evaluate the final test split.",
    )
    parser.add_argument(
        "--features",
        nargs="+",
        choices=FEATURE_ORDER,
        default=list(FEATURE_ORDER),
        help="Feature families to use. Omit for all four families.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.3)
    parser.add_argument("--validation-size", type=float, default=0.15)
    parser.add_argument("--cache-dir", type=Path, default=CACHE_DIR / "classical_ml")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR / "classical_ml")
    parser.add_argument("--config", type=Path, help="JSON map of model name to model parameters.")
    parser.add_argument(
        "--tune",
        action="store_true",
        help="Run grouped GridSearchCV for base models before validation/test evaluation.",
    )
    parser.add_argument(
        "--cv-folds",
        type=int,
        default=3,
        help="Number of identity-grouped folds for GridSearchCV (default: 3).",
    )
    parser.add_argument("--no-cache", action="store_true", help="Recompute all image features.")
    parser.add_argument("--progress-interval", type=int, default=250)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.cv_folds < 2:
        raise ValueError("--cv-folds must be at least 2")
    if args.tune and args.model in ENSEMBLE_NAMES:
        raise ValueError(
            "GridSearchCV is defined for base models. Use --model all --tune to tune "
            "the base models and compare the ensemble approaches alongside them."
        )
    config = FeatureConfig(features=tuple(args.features))
    tag = "-".join(config.features)
    run_dir = args.results_dir / tag
    cache_dir = args.cache_dir
    model_configs = {}
    if args.config:
        model_configs = json.loads(args.config.read_text(encoding="utf-8"))
        if not isinstance(model_configs, dict):
            raise ValueError("Model configuration file must contain a JSON object")

    if args.model == "all":
        selected_models = list(BASE_MODEL_NAMES + ENSEMBLE_NAMES)
    else:
        selected_models = [args.model]
    if not xgboost_available() and "xgboost" in selected_models:
        if args.model == "xgboost":
            raise ImportError("XGBoost missing. Install with `uv sync --extra xgboost`.")
        selected_models.remove("xgboost")
        print("Skipping XGBoost: optional dependency missing (`uv sync --extra xgboost`).")
    grids = parameter_grids()
    if args.tune:
        print(
            f"GridSearchCV: grouped macro-F1 scoring with {args.cv_folds} folds; "
            "ensemble estimators keep their configured members."
        )

    print(f"Feature families: {', '.join(config.features)}")
    print(f"Feature dimensions: {len(feature_names(config))}")
    print(f"Random seed: {args.seed}")
    evaluation_name = "validation" if args.model == "all" else "test"
    train, validation, test = load_and_extract_dataset(
        config,
        cache_dir=cache_dir,
        use_cache=not args.no_cache,
        test_size=args.test_size,
        validation_size=args.validation_size,
        seed=args.seed,
        progress_interval=args.progress_interval,
        include_test=evaluation_name == "test",
    )
    print(
        f"Train rows: {len(train.y)}; validation rows: {len(validation.y)}; "
        f"test rows: {len(test.y) if test is not None else 'not loaded'}; "
        f"feature count: {train.X.shape[1]}"
    )
    print("Class counts by split:")
    train_counts = Counter(train.y.tolist())
    validation_counts = Counter(validation.y.tolist())
    test_counts = Counter(test.y.tolist()) if test is not None else Counter()
    for index, class_name in enumerate(train.class_names):
        test_count = test_counts[index] if test is not None else "not loaded"
        print(
            f"  {class_name}: train={train_counts[index]}, "
            f"validation={validation_counts[index]}, test={test_count}"
        )

    results = []
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir = run_dir / "models"
    if args.model == "all":
        X_fit, y_fit, groups_fit = train.X, train.y, train.group_ids
        X_evaluate, y_evaluate = validation.X, validation.y
    else:
        assert test is not None
        X_fit = np.concatenate((train.X, validation.X), axis=0)
        y_fit = np.concatenate((train.y, validation.y), axis=0)
        groups_fit = np.concatenate((train.group_ids, validation.group_ids), axis=0)
        X_evaluate, y_evaluate = test.X, test.y

    for model_name in selected_models:
        model_config = model_configs.get(model_name, {})
        print(f"\nTraining {model_name}: config={model_config}")
        result = train_model(
            model_name,
            X_fit,
            y_fit,
            config=model_config,
            groups=groups_fit,
            class_names=train.class_names,
            feature_config=config,
            feature_name_list=train.feature_names,
            random_state=args.seed,
            artifact_path=artifact_dir / f"{model_name}.joblib",
            param_grid=(grids.get(model_name) if args.tune else None),
            cv_folds=args.cv_folds,
        )
        print(f"Fit time: {result.fit_seconds:.2f}s")
        if result.best_params is not None:
            print(
                f"GridSearchCV best grouped macro F1={result.best_cv_score:.4f}; "
                f"params={result.best_params}"
            )
            assert result.cv_results is not None and result.cv_folds is not None
            search_paths = save_grid_search_outputs(
                model_name,
                result.cv_results,
                result.best_params,
                result.best_cv_score,
                result.cv_folds,
                run_dir,
                evaluation_name,
            )
            print("Grid-search results saved to " + ", ".join(str(path) for path in search_paths))
        confusion_path = run_dir / f"{model_name}_{evaluation_name}_confusion_matrix.png"
        metrics = evaluate_model(
            result.model,
            X_evaluate,
            y_evaluate,
            train.class_names,
            model_name=model_name,
            confusion_path=confusion_path,
        )
        metrics["fit_seconds"] = result.fit_seconds
        metrics["best_cv_f1_macro"] = result.best_cv_score
        metrics["best_params"] = result.best_params
        results.append(metrics)
        print(
            f"{model_name}: accuracy={metrics['accuracy']:.4f}, "
            f"macro F1={metrics['f1_macro']:.4f}, "
            f"weighted F1={metrics['f1_weighted']:.4f}, "
            f"ROC-AUC={metrics['roc_auc_ovr_macro']}"
        )
        if model_name == "random_forest":
            importance = feature_importance_report(result.model, train.feature_names, config)
            (run_dir / "random_forest_feature_importance.json").write_text(
                json.dumps(importance, indent=2), encoding="utf-8"
            )
            importance_plot = save_feature_importance_plot(
                importance, run_dir / "random_forest_feature_importance.png"
            )
            print(f"Top random-forest feature: {importance['top_features'][0]}")
            print(f"Feature-family importance: {importance['family_importance']}")
            print(f"Feature-importance plot saved to {importance_plot}")

    print_comparison_table(results)
    result_tag = "comparison_validation" if args.model == "all" else f"{args.model}_test"
    plot_paths = save_model_comparison_visualizations(results, run_dir, result_tag)
    print("Comparison plots saved to " + ", ".join(str(path) for path in plot_paths))
    write_results(results, run_dir, result_tag)


if __name__ == "__main__":
    main()
