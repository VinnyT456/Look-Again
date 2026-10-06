"""Reusable model fitting, leakage-aware stacking CV, and persistence."""

from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold

from .evaluation import evaluate_model
from .features import FeatureConfig, feature_names
from .models import get_model


@dataclass(frozen=True)
class TrainingResult:
    model: Any
    validation_metrics: dict[str, Any] | None
    fit_seconds: float
    artifact_path: Path | None
    best_params: dict[str, Any] | None = None
    best_cv_score: float | None = None
    cv_results: list[dict[str, Any]] | None = None
    cv_folds: int | None = None


def _grouped_cv_splits(
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    *,
    folds: int,
    random_state: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    unique_groups = np.unique(groups)
    split_count = min(folds, len(unique_groups))
    if split_count < 2:
        raise ValueError("Grouped cross-validation needs at least two distinct identity groups")
    splitter = StratifiedGroupKFold(
        n_splits=split_count, shuffle=True, random_state=random_state
    )
    splits = list(splitter.split(X, y, groups))
    expected_classes = set(np.unique(y))
    for train_indices, held_out_indices in splits:
        if set(groups[train_indices]) & set(groups[held_out_indices]):
            raise RuntimeError("Identity group leaked across stacking cross-validation folds")
        if set(y[train_indices]) != expected_classes or set(y[held_out_indices]) != expected_classes:
            raise ValueError(
                "Every grouped fold must contain each class in train and held-out rows; "
                "use fewer folds or add more identity groups"
            )
    return splits


def train_model(
    model_name: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray | None = None,
    y_val: np.ndarray | None = None,
    config: dict[str, Any] | None = None,
    *,
    groups: np.ndarray | None = None,
    class_names: tuple[str, ...] | list[str] | None = None,
    feature_config: FeatureConfig | dict[str, Any] | None = None,
    feature_name_list: tuple[str, ...] | None = None,
    random_state: int = 42,
    artifact_path: str | Path | None = None,
    param_grid: dict[str, list[Any]] | None = None,
    cv_folds: int = 3,
) -> TrainingResult:
    """Fit one estimator, optionally score validation rows, and persist a bundle."""
    if (X_val is None) != (y_val is None):
        raise ValueError("Pass both X_val and y_val, or neither")
    X_train = np.asarray(X_train, dtype=np.float32)
    y_train = np.asarray(y_train, dtype=np.int64)
    if X_train.ndim != 2 or y_train.ndim != 1 or len(X_train) != len(y_train):
        raise ValueError("Expected X_train shape (N, features) and y_train shape (N,)")
    if len(X_train) == 0 or not np.all(np.isfinite(X_train)):
        raise ValueError("Training features must be non-empty and finite")
    if np.unique(y_train).size < 2:
        raise ValueError("Training data must contain at least two classes")
    if X_val is not None and y_val is not None:
        X_val = np.asarray(X_val, dtype=np.float32)
        y_val = np.asarray(y_val, dtype=np.int64)
        if X_val.ndim != 2 or X_val.shape[1] != X_train.shape[1]:
            raise ValueError("Validation feature shape must match training feature count")
        if y_val.ndim != 1 or len(y_val) != len(X_val):
            raise ValueError("Validation labels must match validation row count")
        if not len(X_val) or not np.all(np.isfinite(X_val)):
            raise ValueError("Validation features must be non-empty and finite")
    if groups is not None and len(groups) != len(y_train):
        raise ValueError("Training group count must match training row count")
    if feature_name_list is not None and len(feature_name_list) != X_train.shape[1]:
        raise ValueError("Feature name count must match training feature count")

    np.random.seed(random_state)
    model_config = dict(config or {})
    cv_splits = None
    if model_name == "stacking" and groups is not None:
        cv_splits = _grouped_cv_splits(
            X_train,
            y_train,
            np.asarray(groups, dtype=str),
            folds=int(model_config.get("cv", 5)),
            random_state=random_state,
        )
    model = get_model(
        model_name,
        model_config,
        random_state=random_state,
        num_classes=len(np.unique(y_train)),
        cv_splits=cv_splits,
    )
    start = time.perf_counter()
    best_params = None
    best_cv_score = None
    cv_results = None
    resolved_cv_folds = None
    if param_grid is not None:
        if not param_grid:
            raise ValueError("GridSearchCV needs at least one hyperparameter candidate")
        if groups is None:
            raise ValueError("Group IDs are required for leakage-safe GridSearchCV")
        search_splits = _grouped_cv_splits(
            X_train,
            y_train,
            np.asarray(groups, dtype=str),
            folds=cv_folds,
            random_state=random_state,
        )
        search = GridSearchCV(
            estimator=model,
            param_grid=param_grid,
            scoring="f1_macro",
            cv=search_splits,
            refit=True,
            n_jobs=1,
            return_train_score=False,
            error_score="raise",
        )
        search.fit(X_train, y_train)
        model = search.best_estimator_
        best_params = dict(search.best_params_)
        best_cv_score = float(search.best_score_)
        resolved_cv_folds = len(search_splits)
        cv_results = [
            {
                "rank": int(search.cv_results_["rank_test_score"][index]),
                "mean_test_f1_macro": float(search.cv_results_["mean_test_score"][index]),
                "std_test_f1_macro": float(search.cv_results_["std_test_score"][index]),
                "mean_fit_seconds": float(search.cv_results_["mean_fit_time"][index]),
                "params": dict(search.cv_results_["params"][index]),
            }
            for index in range(len(search.cv_results_["params"]))
        ]
    else:
        model.fit(X_train, y_train)
    fit_seconds = time.perf_counter() - start

    validation_metrics = None
    if X_val is not None and y_val is not None:
        resolved_names = tuple(class_names or (str(v) for v in sorted(np.unique(y_train))))
        validation_metrics = evaluate_model(
            model,
            np.asarray(X_val, dtype=np.float32),
            np.asarray(y_val, dtype=np.int64),
            resolved_names,
            model_name=f"{model_name}_validation",
        )

    saved_path = Path(artifact_path) if artifact_path is not None else None
    if saved_path is not None:
        if isinstance(feature_config, FeatureConfig):
            saved_feature_config: dict[str, Any] | None = feature_config.to_dict()
        else:
            saved_feature_config = feature_config
        resolved_class_names = tuple(class_names or (str(v) for v in sorted(np.unique(y_train))))
        bundle = {
            "model": model,
            "model_name": model_name,
            "model_config": model_config,
            "class_names": resolved_class_names,
            "label_mapping": {name: index for index, name in enumerate(resolved_class_names)},
            "feature_config": saved_feature_config,
            "feature_names": feature_name_list or tuple(
                f"feature_{index}" for index in range(X_train.shape[1])
            ),
            "random_state": random_state,
            "metadata": {
                "training_rows": len(y_train),
                "feature_count": X_train.shape[1],
                "fit_seconds": fit_seconds,
                "hyperparameter_search": (
                    {
                        "scoring": "f1_macro",
                        "cv_folds": resolved_cv_folds,
                        "best_params": best_params,
                        "best_cv_f1_macro": best_cv_score,
                    }
                    if best_params is not None
                    else None
                ),
            },
        }
        saved_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=saved_path.parent, prefix=f".{saved_path.name}.", delete=False
            ) as temporary_file:
                temp_path = Path(temporary_file.name)
            joblib.dump(bundle, temp_path)
            os.replace(temp_path, saved_path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()

    return TrainingResult(
        model,
        validation_metrics,
        fit_seconds,
        saved_path,
        best_params,
        best_cv_score,
        cv_results,
        resolved_cv_folds,
    )
