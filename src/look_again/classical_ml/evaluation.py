"""Common classification metrics, confusion matrices, and feature importance."""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_curve,
    roc_auc_score,
)

from .features import FeatureConfig, feature_family_slices


def evaluate_model(
    model,
    X_test: np.ndarray,
    y_test: np.ndarray,
    class_names: tuple[str, ...] | list[str],
    *,
    model_name: str,
    confusion_path: str | Path | None = None,
) -> dict[str, Any]:
    """Compute class-aware metrics, optional ROC-AUC, and inference latency."""
    labels = np.arange(len(class_names))
    start = time.perf_counter()
    predictions = np.asarray(model.predict(X_test), dtype=np.int64)
    inference_seconds = time.perf_counter() - start
    precision, recall, f1, support = precision_recall_fscore_support(
        y_test, predictions, labels=labels, zero_division=0
    )
    macro_precision, macro_recall, macro_f1, _ = precision_recall_fscore_support(
        y_test, predictions, labels=labels, average="macro", zero_division=0
    )
    weighted_precision, weighted_recall, weighted_f1, _ = precision_recall_fscore_support(
        y_test, predictions, labels=labels, average="weighted", zero_division=0
    )
    matrix = confusion_matrix(y_test, predictions, labels=labels)

    auc: float | None = None
    roc_curve_points: dict[str, list[float]] | None = None
    if hasattr(model, "predict_proba"):
        try:
            probabilities = np.asarray(model.predict_proba(X_test))
            model_classes = [int(value) for value in model.classes_]
            ordered = np.column_stack(
                [probabilities[:, model_classes.index(label)] for label in labels]
            )
            if len(class_names) == 2:
                auc = float(roc_auc_score(y_test, ordered[:, 1]))
                false_positive_rate, true_positive_rate, _ = roc_curve(
                    y_test, ordered[:, 1]
                )
                roc_curve_points = {
                    "false_positive_rate": false_positive_rate.tolist(),
                    "true_positive_rate": true_positive_rate.tolist(),
                }
            else:
                auc = float(
                    roc_auc_score(
                        y_test,
                        ordered,
                        labels=labels,
                        multi_class="ovr",
                        average="macro",
                    )
                )
        except (ValueError, IndexError, AttributeError):
            auc = None

    if confusion_path is not None:
        save_confusion_matrix(matrix, class_names, confusion_path, model_name)

    return {
        "model": model_name,
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision_macro": float(macro_precision),
        "recall_macro": float(macro_recall),
        "f1_macro": float(macro_f1),
        "precision_weighted": float(weighted_precision),
        "recall_weighted": float(weighted_recall),
        "f1_weighted": float(weighted_f1),
        "roc_auc_ovr_macro": auc,
        "inference_seconds": float(inference_seconds),
        "inference_ms_per_image": float(1000 * inference_seconds / max(1, len(X_test))),
        "per_class": {
            class_names[index]: {
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(f1[index]),
                "support": int(support[index]),
            }
            for index in range(len(class_names))
        },
        "confusion_matrix": matrix.tolist(),
        "_roc_curve": roc_curve_points,
        "classification_report": classification_report(
            y_test,
            predictions,
            labels=labels,
            target_names=list(class_names),
            output_dict=True,
            zero_division=0,
        ),
    }


def save_confusion_matrix(
    matrix: np.ndarray,
    class_names: tuple[str, ...] | list[str],
    path: str | Path,
    title: str,
) -> None:
    """Save labeled confusion matrix using dataset class order."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    import seaborn as sns

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure = Figure(figsize=(6, 5))
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    sns.heatmap(
        matrix,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=class_names,
        yticklabels=class_names,
        cbar=False,
        ax=axis,
    )
    axis.set(title=f"{title} confusion matrix", xlabel="Predicted", ylabel="Actual")
    figure.tight_layout()
    figure.savefig(output_path, dpi=150, bbox_inches="tight")


def write_results(results: list[dict[str, Any]], output_dir: str | Path, tag: str) -> None:
    """Write comparable scalar metrics as CSV and full per-class metrics as JSON."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / f"{tag}_metrics.json"
    csv_path = output / f"{tag}_metrics.csv"
    public_results = [
        {key: value for key, value in result.items() if not key.startswith("_")}
        for result in results
    ]
    json_path.write_text(
        json.dumps(public_results, indent=2, allow_nan=False), encoding="utf-8"
    )
    scalar_fields = (
        "model",
        "accuracy",
        "precision_macro",
        "recall_macro",
        "f1_macro",
        "precision_weighted",
        "recall_weighted",
        "f1_weighted",
        "roc_auc_ovr_macro",
        "inference_seconds",
        "inference_ms_per_image",
        "fit_seconds",
        "best_cv_f1_macro",
        "best_params",
    )
    with csv_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=scalar_fields)
        writer.writeheader()
        for row in results:
            writer.writerow(
                {
                    field: json.dumps(row[field], sort_keys=True)
                    if isinstance(row.get(field), dict)
                    else row.get(field)
                    for field in scalar_fields
                }
            )
    print(f"Metrics saved to {csv_path} and {json_path}")


def save_model_comparison_visualizations(
    results: list[dict[str, Any]], output_dir: str | Path, tag: str
) -> list[Path]:
    """Save comparative performance, ROC, and runtime figures for one run."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    import seaborn as sns

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    model_names = [str(result["model"]) for result in results]
    paths: list[Path] = []

    metric_specs = (
        ("Accuracy", "accuracy"),
        ("Macro F1", "f1_macro"),
        ("Weighted F1", "f1_weighted"),
        ("ROC-AUC", "roc_auc_ovr_macro"),
    )
    metric_rows = [
        {"model": result["model"], "metric": label, "score": result[key]}
        for result in results
        for label, key in metric_specs
        if result.get(key) is not None
    ]
    metrics_path = output / f"model_metrics_{tag}.png"
    figure = Figure(figsize=(max(10, len(model_names) * 1.2), 6))
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    sns.barplot(
        data=metric_rows,
        x="model",
        y="score",
        hue="metric",
        errorbar=None,
        ax=axis,
    )
    axis.set_ylim(0, 1.05)
    axis.set(title="Model performance comparison", xlabel="", ylabel="Score")
    axis.tick_params(axis="x", labelrotation=25)
    axis.legend(title="Metric", loc="lower left", bbox_to_anchor=(1.01, 0))
    figure.tight_layout()
    figure.savefig(metrics_path, dpi=180, bbox_inches="tight")
    paths.append(metrics_path)

    runtime_path = output / f"model_runtime_{tag}.png"
    figure = Figure(figsize=(max(10, len(model_names) * 1.1), 5.5))
    FigureCanvasAgg(figure)
    fit_axis, inference_axis = figure.subplots(1, 2)
    fit_axis.bar(model_names, [result.get("fit_seconds", 0.0) for result in results])
    fit_axis.set(title="Fit or search time", ylabel="Seconds", xlabel="")
    fit_axis.tick_params(axis="x", labelrotation=30)
    inference_axis.bar(
        model_names,
        [result["inference_ms_per_image"] for result in results],
        color="#55a868",
    )
    inference_axis.set(title="Inference latency", ylabel="Milliseconds / image", xlabel="")
    inference_axis.tick_params(axis="x", labelrotation=30)
    figure.tight_layout()
    figure.savefig(runtime_path, dpi=180, bbox_inches="tight")
    paths.append(runtime_path)

    roc_results = [result for result in results if result.get("_roc_curve")]
    if roc_results:
        roc_path = output / f"roc_curves_{tag}.png"
        figure = Figure(figsize=(7, 6))
        FigureCanvasAgg(figure)
        axis = figure.subplots()
        for result in roc_results:
            curve = result["_roc_curve"]
            auc = result.get("roc_auc_ovr_macro")
            axis.plot(
                curve["false_positive_rate"],
                curve["true_positive_rate"],
                label=f"{result['model']} (AUC {auc:.3f})",
            )
        axis.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Chance")
        axis.set(
            title="ROC curves",
            xlabel="False positive rate",
            ylabel="True positive rate",
            xlim=(0, 1),
            ylim=(0, 1.02),
        )
        axis.legend(loc="lower right", fontsize="small")
        figure.tight_layout()
        figure.savefig(roc_path, dpi=180, bbox_inches="tight")
        paths.append(roc_path)

    return paths


def save_grid_search_outputs(
    model_name: str,
    cv_results: list[dict[str, Any]],
    best_params: dict[str, Any],
    best_score: float,
    cv_folds: int,
    output_dir: str | Path,
    tag: str,
) -> list[Path]:
    """Persist GridSearchCV candidates and plot their grouped-CV scores."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    stem = f"grid_search_{model_name}_{tag}"
    json_path = output / f"{stem}.json"
    csv_path = output / f"{stem}.csv"
    plot_path = output / f"{stem}.png"
    summary = {
        "model": model_name,
        "scoring": "f1_macro",
        "cv_folds": cv_folds,
        "best_cv_f1_macro": best_score,
        "best_params": best_params,
        "candidates": cv_results,
    }
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=("rank", "mean_test_f1_macro", "std_test_f1_macro", "mean_fit_seconds", "params"),
        )
        writer.writeheader()
        for result in cv_results:
            writer.writerow(
                {
                    **result,
                    "params": json.dumps(result["params"], sort_keys=True),
                }
            )

    ordered = sorted(cv_results, key=lambda result: result["rank"], reverse=True)
    labels = [
        ", ".join(f"{key}={value}" for key, value in result["params"].items())
        for result in ordered
    ]
    scores = [result["mean_test_f1_macro"] for result in ordered]
    deviations = [result["std_test_f1_macro"] for result in ordered]
    figure = Figure(figsize=(9, max(4, len(ordered) * 0.48)))
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    axis.barh(labels, scores, xerr=deviations, color="#4c72b0", capsize=3)
    axis.set(
        title=f"{model_name}: grouped CV GridSearchCV (best F1={best_score:.3f})",
        xlabel="Mean macro F1",
        ylabel="Parameter candidate",
        xlim=(0, 1.02),
    )
    figure.tight_layout()
    figure.savefig(plot_path, dpi=180, bbox_inches="tight")
    return [json_path, csv_path, plot_path]


def save_feature_importance_plot(
    report: dict[str, Any], output_path: str | Path
) -> Path:
    """Plot the strongest random-forest features and their family totals."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    features = list(reversed(report["top_features"]))
    families = report["family_importance"]
    figure = Figure(figsize=(12, max(5, len(features) * 0.32)))
    FigureCanvasAgg(figure)
    feature_axis, family_axis = figure.subplots(1, 2, gridspec_kw={"width_ratios": [2, 1]})
    feature_axis.barh(
        [item["name"] for item in features],
        [item["importance"] for item in features],
        color="#4c72b0",
    )
    feature_axis.set(title="Top random-forest features", xlabel="Importance", ylabel="")
    family_axis.barh(list(families), list(families.values()), color="#55a868")
    family_axis.set(title="Feature-family importance", xlabel="Total importance", ylabel="")
    figure.tight_layout()
    figure.savefig(path, dpi=180, bbox_inches="tight")
    return path


def feature_importance_report(
    model,
    feature_names: tuple[str, ...],
    config: FeatureConfig | None = None,
    *,
    limit: int = 20,
) -> dict[str, Any]:
    """Report individual and family-level random-forest feature importance."""
    estimator = model
    if hasattr(model, "named_steps"):
        estimator = model.named_steps.get("classifier", model)
    if not hasattr(estimator, "feature_importances_"):
        raise TypeError("Selected fitted model does not expose feature_importances_")
    importances = np.asarray(estimator.feature_importances_, dtype=np.float64)
    if len(importances) != len(feature_names):
        raise ValueError("Feature importance count does not match feature names")
    order = np.argsort(importances)[::-1][:limit]
    families = {
        family: float(np.sum(importances[columns]))
        for family, columns in feature_family_slices(config).items()
    }
    return {
        "top_features": [
            {"name": feature_names[index], "importance": float(importances[index])}
            for index in order
        ],
        "family_importance": families,
    }


def print_comparison_table(results: list[dict[str, Any]]) -> None:
    """Print compact metrics for model comparison."""
    headers = ("Model", "Accuracy", "Macro F1", "Weighted F1", "ROC-AUC", "ms/image")
    rows = [headers]
    for result in results:
        auc = result["roc_auc_ovr_macro"]
        rows.append(
            (
                str(result["model"]),
                f"{result['accuracy']:.4f}",
                f"{result['f1_macro']:.4f}",
                f"{result['f1_weighted']:.4f}",
                "n/a" if auc is None else f"{auc:.4f}",
                f"{result['inference_ms_per_image']:.3f}",
            )
        )
    widths = [max(len(row[index]) for row in rows) for index in range(len(headers))]
    print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(rows[0])))
    print("-+-".join("-" * width for width in widths))
    for row in rows[1:]:
        print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
