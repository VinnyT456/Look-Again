"""Load a saved classical pipeline and classify one image."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from PIL import Image

from .features import FeatureConfig, extract_features


def load_model_bundle(path: str | Path) -> dict[str, Any]:
    """Load a trusted joblib bundle created by ``train_model``."""
    bundle = joblib.load(path)
    required = {"model", "class_names", "feature_config", "feature_names"}
    missing = required - set(bundle)
    if missing:
        raise ValueError(f"Model bundle is missing fields: {sorted(missing)}")
    return bundle


def predict_image(
    bundle_or_path: dict[str, Any] | str | Path,
    image: Image.Image | np.ndarray,
) -> dict[str, Any]:
    """Predict dataset class name and probabilities using saved feature settings."""
    bundle = (
        bundle_or_path
        if isinstance(bundle_or_path, dict)
        else load_model_bundle(bundle_or_path)
    )
    config_values = dict(bundle["feature_config"] or {})
    config_values["features"] = tuple(config_values.get("features", FeatureConfig().features))
    feature_config = FeatureConfig(**config_values)
    vector = extract_features(image, feature_config).reshape(1, -1)
    expected_count = len(bundle["feature_names"])
    if vector.shape[1] != expected_count:
        raise ValueError(
            f"Image produced {vector.shape[1]} features; model expects {expected_count}"
        )

    model = bundle["model"]
    predicted_id = int(model.predict(vector)[0])
    class_names = tuple(bundle["class_names"])
    if predicted_id < 0 or predicted_id >= len(class_names):
        raise ValueError(f"Model returned unknown class id {predicted_id}")
    result: dict[str, Any] = {
        "class_id": predicted_id,
        "predicted_label": class_names[predicted_id],
    }
    if hasattr(model, "predict_proba"):
        probabilities = np.asarray(model.predict_proba(vector))[0]
        model_classes = [int(value) for value in model.classes_]
        result["probabilities"] = {
            class_names[label]: float(probabilities[model_classes.index(label)])
            for label in model_classes
            if 0 <= label < len(class_names)
        }
    return result
