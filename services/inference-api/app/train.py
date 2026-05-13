from datetime import UTC, datetime
from os import getenv
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import psycopg
from psycopg.rows import dict_row
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, log_loss, roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from app.main import FEATURE_ORDER, FEATURE_VERSION

RANDOM_STATE = 42


def main() -> None:
    database_url = getenv("DATABASE_URL", "postgresql://hermes:hermes@localhost:5432/hermes_trader")
    model_dir = Path(getenv("MODEL_DIR", "models"))
    model_dir.mkdir(parents=True, exist_ok=True)

    rows = _load_training_rows(database_url)
    if len(rows) < 25:
        raise SystemExit("Need at least 25 labeled outcomes before training a baseline model")

    x = np.array([[float(row["features"].get(name, 0.0)) for name in FEATURE_ORDER] for row in rows])
    y = np.array([int(row["label"]) for row in rows])
    if len(set(y.tolist())) < 2:
        raise SystemExit("Need both positive and negative labels before training")

    split = _split_dataset(x, y)
    candidates = _candidate_grids(len(split["y_train"]))
    results = []
    fitted_models = {}

    for name, spec in candidates.items():
        result = _fit_candidate(name, spec, split)
        results.append(result["metrics"])
        fitted_models[name] = result["model"]

    results.sort(
        key=lambda item: (
            item["balanced_accuracy"],
            item["roc_auc"],
            item["f1"],
            -item["log_loss"],
        ),
        reverse=True,
    )
    best = results[0]
    best_model = fitted_models[best["name"]]
    tuned_thresholds = _tune_thresholds(best_model, split["x_valid"], split["y_valid"])
    final_model = clone(best_model)
    final_model.fit(x, y)

    version = f"baseline-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    artifact = {
        "model": final_model,
        "version": version,
        "feature_order": FEATURE_ORDER,
        "buy_threshold": tuned_thresholds["buy_threshold"],
        "sell_threshold": tuned_thresholds["sell_threshold"],
        "metadata": {
            "created_at": datetime.now(UTC).isoformat(),
            "feature_version": FEATURE_VERSION,
            "label_strategy": "trade_outcomes.label",
            "row_count": len(rows),
            "label_counts": {str(label): int(count) for label, count in zip(*np.unique(y, return_counts=True))},
            "train_rows": int(len(split["y_train"])),
            "validation_rows": int(len(split["y_valid"])),
            "best_model": best["name"],
            "best_params": best["best_params"],
            "validation": results,
            "threshold_tuning": tuned_thresholds,
        },
    }
    model_path = model_dir / "baseline.joblib"
    joblib.dump(artifact, model_path)

    print(f"Saved {version} with {len(rows)} rows")
    print(f"Best model: {best['name']}")
    print(
        "Validation: "
        f"balanced_accuracy={best['balanced_accuracy']:.3f} "
        f"roc_auc={best['roc_auc']:.3f} "
        f"f1={best['f1']:.3f} "
        f"log_loss={best['log_loss']:.3f}"
    )
    print(
        "Thresholds: "
        f"buy>{tuned_thresholds['buy_threshold']:.2f}, "
        f"sell<{tuned_thresholds['sell_threshold']:.2f}"
    )


def _load_training_rows(database_url: str) -> list[dict[str, Any]]:
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        rows = conn.execute(
            """
            select fs.features, co.label
            from feature_snapshots fs
            join inference_runs ir on ir.feature_snapshot_id = fs.id
            join agent_decisions ad on ad.inference_run_id = ir.id
            join trade_outcomes co on co.decision_id = ad.id
            where co.label is not null
            order by co.measured_at asc
            """
        ).fetchall()
    return list(rows)


def _split_dataset(x: np.ndarray, y: np.ndarray) -> dict[str, np.ndarray]:
    valid_size = 0.25 if len(y) >= 80 else 0.3
    try:
        x_train, x_valid, y_train, y_valid = train_test_split(
            x,
            y,
            test_size=valid_size,
            random_state=RANDOM_STATE,
            stratify=y,
        )
    except ValueError:
        x_train, x_valid, y_train, y_valid = train_test_split(
            x,
            y,
            test_size=valid_size,
            random_state=RANDOM_STATE,
        )
    return {
        "x_train": x_train,
        "x_valid": x_valid,
        "y_train": y_train,
        "y_valid": y_valid,
    }


def _candidate_grids(train_rows: int) -> dict[str, dict[str, Any]]:
    cv_splits = 5 if train_rows >= 100 else 3
    cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=RANDOM_STATE)
    return {
        "dummy_prior": {
            "estimator": DummyClassifier(strategy="prior"),
            "params": {},
            "cv": cv,
        },
        "logistic_regression": {
            "estimator": Pipeline(
                [
                    ("scale", StandardScaler()),
                    (
                        "model",
                        LogisticRegression(
                            max_iter=5000,
                            class_weight="balanced",
                            random_state=RANDOM_STATE,
                        ),
                    ),
                ]
            ),
            "params": {
                "model__C": [0.01, 0.1, 1.0, 10.0],
                "model__solver": ["lbfgs", "liblinear"],
            },
            "cv": cv,
        },
        "random_forest": {
            "estimator": RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE),
            "params": {
                "n_estimators": [100, 250],
                "max_depth": [2, 4, None],
                "min_samples_leaf": [1, 3, 8],
            },
            "cv": cv,
        },
        "extra_trees": {
            "estimator": ExtraTreesClassifier(class_weight="balanced", random_state=RANDOM_STATE),
            "params": {
                "n_estimators": [100, 250],
                "max_depth": [2, 4, None],
                "min_samples_leaf": [1, 3, 8],
            },
            "cv": cv,
        },
        "hist_gradient_boosting": {
            "estimator": HistGradientBoostingClassifier(random_state=RANDOM_STATE),
            "params": {
                "max_iter": [50, 100, 200],
                "learning_rate": [0.02, 0.05, 0.1],
                "max_leaf_nodes": [7, 15, 31],
                "l2_regularization": [0.0, 0.1],
            },
            "cv": cv,
        },
        "gradient_boosting": {
            "estimator": GradientBoostingClassifier(random_state=RANDOM_STATE),
            "params": {
                "n_estimators": [50, 100, 200],
                "learning_rate": [0.02, 0.05, 0.1],
                "max_depth": [1, 2, 3],
            },
            "cv": cv,
        },
        "svc_rbf": {
            "estimator": Pipeline(
                [
                    ("scale", StandardScaler()),
                    (
                        "model",
                        SVC(
                            probability=True,
                            class_weight="balanced",
                            random_state=RANDOM_STATE,
                        ),
                    ),
                ]
            ),
            "params": {
                "model__C": [0.1, 1.0, 10.0],
                "model__gamma": ["scale", 0.1, 1.0],
            },
            "cv": cv,
        },
        "knn": {
            "estimator": Pipeline(
                [
                    ("scale", StandardScaler()),
                    ("model", KNeighborsClassifier()),
                ]
            ),
            "params": {
                "model__n_neighbors": [3, 5, 9, 15],
                "model__weights": ["uniform", "distance"],
            },
            "cv": cv,
        },
        "gaussian_nb": {
            "estimator": GaussianNB(),
            "params": {
                "var_smoothing": [1e-9, 1e-8, 1e-7],
            },
            "cv": cv,
        },
    }


def _fit_candidate(name: str, spec: dict[str, Any], split: dict[str, np.ndarray]) -> dict[str, Any]:
    params = spec["params"]
    if params:
        search = GridSearchCV(
            estimator=spec["estimator"],
            param_grid=params,
            scoring="balanced_accuracy",
            cv=spec["cv"],
            n_jobs=-1,
            refit=True,
        )
        search.fit(split["x_train"], split["y_train"])
        model = search.best_estimator_
        best_params = search.best_params_
        cv_score = float(search.best_score_)
    else:
        model = spec["estimator"]
        model.fit(split["x_train"], split["y_train"])
        best_params = {}
        cv_score = None

    metrics = _evaluate_model(name, model, split["x_valid"], split["y_valid"])
    metrics["best_params"] = best_params
    metrics["cv_balanced_accuracy"] = cv_score
    return {"model": model, "metrics": metrics}


def _evaluate_model(name: str, model: Any, x_valid: np.ndarray, y_valid: np.ndarray) -> dict[str, Any]:
    probability_up = model.predict_proba(x_valid)[:, 1]
    pred = (probability_up >= 0.5).astype(int)
    return {
        "name": name,
        "accuracy": float(accuracy_score(y_valid, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_valid, pred)),
        "f1": float(f1_score(y_valid, pred, zero_division=0)),
        "roc_auc": _safe_roc_auc(y_valid, probability_up),
        "log_loss": float(log_loss(y_valid, probability_up, labels=[0, 1])),
    }


def _safe_roc_auc(y_true: np.ndarray, probability_up: np.ndarray) -> float:
    if len(set(y_true.tolist())) < 2:
        return 0.5
    return float(roc_auc_score(y_true, probability_up))


def _tune_thresholds(model: Any, x_valid: np.ndarray, y_valid: np.ndarray) -> dict[str, Any]:
    probability_up = model.predict_proba(x_valid)[:, 1]
    best = {
        "buy_threshold": 0.58,
        "sell_threshold": 0.42,
        "score": -1.0,
        "trade_rate": 0.0,
        "balanced_accuracy": 0.0,
    }
    for buy_threshold in np.arange(0.52, 0.76, 0.02):
        for sell_threshold in np.arange(0.24, 0.48, 0.02):
            if sell_threshold >= buy_threshold:
                continue
            trade_mask = (probability_up > buy_threshold) | (probability_up < sell_threshold)
            trade_rate = float(trade_mask.mean())
            if trade_mask.sum() < 3:
                continue
            pred = (probability_up > buy_threshold).astype(int)
            score = float(balanced_accuracy_score(y_valid[trade_mask], pred[trade_mask]))
            objective = score * min(trade_rate / 0.2, 1.0)
            if objective > best["score"]:
                best = {
                    "buy_threshold": float(round(buy_threshold, 2)),
                    "sell_threshold": float(round(sell_threshold, 2)),
                    "score": objective,
                    "trade_rate": trade_rate,
                    "balanced_accuracy": score,
                }
    return best


if __name__ == "__main__":
    main()
