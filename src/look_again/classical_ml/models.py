"""Classical classifier and ensemble factory."""

from __future__ import annotations

import importlib.util
from typing import Any

from sklearn.ensemble import RandomForestClassifier, StackingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import StratifiedKFold


BASE_MODEL_NAMES = ("logistic", "decision_tree", "random_forest", "svm", "xgboost")
ENSEMBLE_NAMES = ("hard_voting", "soft_voting", "weighted_soft_voting", "stacking")
MODEL_NAMES = BASE_MODEL_NAMES + ENSEMBLE_NAMES


def xgboost_available() -> bool:
    """Return whether optional XGBoost dependency is importable."""
    return importlib.util.find_spec("xgboost") is not None


def default_ensemble_members() -> tuple[str, ...]:
    """Use core estimators and add XGBoost only when installed."""
    members = ["logistic", "random_forest", "svm"]
    if xgboost_available():
        members.append("xgboost")
    return tuple(members)


def _make_base_model(
    name: str,
    config: dict[str, Any],
    *,
    random_state: int,
    num_classes: int,
):
    if name == "logistic":
        classifier = LogisticRegression(
            max_iter=config.get("max_iter", 2000),
            C=config.get("C", 1.0),
            class_weight=config.get("class_weight"),
            random_state=random_state,
        )
        return Pipeline([("scale", StandardScaler()), ("classifier", classifier)])
    if name == "decision_tree":
        return DecisionTreeClassifier(
            max_depth=config.get("max_depth"),
            min_samples_split=config.get("min_samples_split", 2),
            min_samples_leaf=config.get("min_samples_leaf", 1),
            criterion=config.get("criterion", "gini"),
            class_weight=config.get("class_weight"),
            random_state=random_state,
        )
    if name == "random_forest":
        return RandomForestClassifier(
            n_estimators=config.get("n_estimators", 300),
            max_depth=config.get("max_depth"),
            min_samples_split=config.get("min_samples_split", 2),
            min_samples_leaf=config.get("min_samples_leaf", 1),
            max_features=config.get("max_features", "sqrt"),
            class_weight=config.get("class_weight"),
            n_jobs=config.get("n_jobs", -1),
            random_state=random_state,
        )
    if name == "svm":
        classifier = SVC(
            C=config.get("C", 1.0),
            gamma=config.get("gamma", "scale"),
            kernel=config.get("kernel", "rbf"),
            probability=config.get("probability", True),
            class_weight=config.get("class_weight"),
            random_state=random_state,
        )
        return Pipeline([("scale", StandardScaler()), ("classifier", classifier)])
    if name == "xgboost":
        if not xgboost_available():
            raise ImportError(
                "XGBoost support requested, but package is missing. "
                "Install it with `uv sync --extra xgboost`."
            )
        from xgboost import XGBClassifier

        params: dict[str, Any] = {
            "n_estimators": config.get("n_estimators", 300),
            "max_depth": config.get("max_depth", 6),
            "learning_rate": config.get("learning_rate", 0.1),
            "subsample": config.get("subsample", 0.9),
            "colsample_bytree": config.get("colsample_bytree", 0.9),
            # The sklearn wrapper's default quantile-matrix path segfaults here.
            "tree_method": config.get("tree_method", "exact"),
            "objective": "binary:logistic" if num_classes == 2 else "multi:softprob",
            "eval_metric": "logloss" if num_classes == 2 else "mlogloss",
            # Avoid XGBoost's all-core OpenMP default, which can destabilize
            # native training on resource-constrained/macOS environments.
            "n_jobs": config.get("n_jobs", 1),
            "random_state": random_state,
        }
        if num_classes > 2:
            params["num_class"] = num_classes
        params.update({key: value for key, value in config.items() if key in {
            "min_child_weight", "reg_alpha", "reg_lambda", "gamma", "tree_method",
            "scale_pos_weight"
        }})
        return XGBClassifier(**params)
    raise ValueError(f"Unknown base model: {name}")


def get_model(
    name: str,
    config: dict[str, Any] | None = None,
    *,
    random_state: int = 42,
    num_classes: int = 2,
    cv_splits: list[tuple[Any, Any]] | None = None,
):
    """Build one supported estimator. Scalers stay inside their model pipelines."""
    config = dict(config or {})
    if name in BASE_MODEL_NAMES:
        return _make_base_model(
            name, config, random_state=random_state, num_classes=num_classes
        )
    if name not in ENSEMBLE_NAMES:
        raise ValueError(f"Unknown model {name!r}; choose from {', '.join(MODEL_NAMES)}")

    members = tuple(config.get("members", default_ensemble_members()))
    if not members:
        raise ValueError("An ensemble needs at least one base model")
    member_configs = config.get("member_configs", {})
    estimators = [
        (
            member,
            get_model(
                member,
                member_configs.get(member),
                random_state=random_state,
                num_classes=num_classes,
            ),
        )
        for member in members
    ]

    if name in {"hard_voting", "soft_voting", "weighted_soft_voting"}:
        voting = "hard" if name == "hard_voting" else "soft"
        weights = None
        if name == "weighted_soft_voting":
            provided = config.get("weights")
            if provided is not None:
                if set(provided) != set(members):
                    raise ValueError("Voting weights must name every ensemble member exactly once")
                weights = [float(provided[member]) for member in members]
                if any(weight < 0 for weight in weights) or sum(weights) <= 0:
                    raise ValueError("Voting weights must be non-negative with positive total")
        return VotingClassifier(estimators=estimators, voting=voting, weights=weights, n_jobs=1)

    if cv_splits is None:
        cv = StratifiedKFold(
            n_splits=int(config.get("cv", 5)), shuffle=True, random_state=random_state
        )
    else:
        cv = cv_splits
    return StackingClassifier(
        estimators=estimators,
        final_estimator=LogisticRegression(max_iter=2000, random_state=random_state),
        cv=cv,
        stack_method="predict_proba",
        passthrough=False,
        n_jobs=1,
    )


def parameter_grids() -> dict[str, dict[str, list[Any]]]:
    """Compact starting grids for grouped, macro-F1 hyperparameter search."""
    return {
        "logistic": {"classifier__C": [0.1, 1.0, 10.0]},
        "decision_tree": {"max_depth": [None, 12], "min_samples_leaf": [1, 3]},
        "random_forest": {
            "n_estimators": [100, 250],
            "max_depth": [None, 24],
            "min_samples_leaf": [1, 3],
        },
        "svm": {
            "classifier__C": [0.1, 1.0, 10.0],
            "classifier__gamma": ["scale", 0.01],
        },
        "xgboost": {
            "n_estimators": [100, 200],
            "max_depth": [3, 6],
        },
    }
