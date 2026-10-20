"""Validation-only tools for explicit weighted-soft-voting candidates."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import f1_score


def select_voting_weights(
    fitted_models: dict[str, Any],
    X_val: np.ndarray,
    y_val: np.ndarray,
    candidates: list[dict[str, float]],
    *,
    class_order: tuple[int, ...] | None = None,
) -> dict[str, float]:
    """Choose caller-supplied weights by macro F1 on validation data only."""
    if not fitted_models or not candidates:
        raise ValueError("Provide fitted models and at least one candidate weight map")
    member_names = tuple(fitted_models)
    classes = tuple(class_order or sorted(np.unique(y_val).tolist()))
    probabilities: dict[str, np.ndarray] = {}
    for name, model in fitted_models.items():
        if not hasattr(model, "predict_proba"):
            raise TypeError(f"Model {name!r} does not support predict_proba")
        model_classes = [int(value) for value in model.classes_]
        raw = np.asarray(model.predict_proba(X_val))
        probabilities[name] = np.column_stack(
            [raw[:, model_classes.index(label)] for label in classes]
        )

    best_weights = None
    best_score = -1.0
    for candidate in candidates:
        if set(candidate) != set(member_names):
            raise ValueError("Each candidate must set one weight for every fitted model")
        weights = np.asarray([candidate[name] for name in member_names], dtype=np.float64)
        if np.any(weights < 0) or float(weights.sum()) <= 0:
            raise ValueError("Candidate weights must be non-negative with positive total")
        average = sum(
            probabilities[name] * candidate[name] for name in member_names
        ) / float(weights.sum())
        predictions = np.asarray(classes)[np.argmax(average, axis=1)]
        score = float(f1_score(y_val, predictions, labels=classes, average="macro", zero_division=0))
        if score > best_score:
            best_score = score
            best_weights = {name: float(candidate[name]) for name in member_names}
    assert best_weights is not None
    return best_weights
