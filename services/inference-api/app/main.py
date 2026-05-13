from os import getenv
from pathlib import Path
from typing import Any, Literal

import joblib
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel, Field

Action = Literal["buy", "sell", "hold"]
FEATURE_VERSION = "features-v1"
FEATURE_ORDER = [
    "returns_1",
    "returns_5",
    "returns_20",
    "moving_average_distance_20",
    "volatility_20",
    "volume_zscore_20",
    "daily_returns_20",
    "daily_returns_60",
    "daily_returns_120",
    "sma_distance_20",
    "sma_distance_50",
    "sma_distance_200",
    "trend_regime",
    "drawdown_from_52w_high",
    "distance_from_52w_low",
    "position_qty",
    "position_notional",
    "unrealized_plpc",
]


class PredictRequest(BaseModel):
    symbol: str
    features: dict[str, Any] = Field(default_factory=dict)


class PredictResponse(BaseModel):
    symbol: str
    predicted_action: Action
    predicted_return: float | None = None
    confidence: float
    model_name: str
    model_version: str
    raw_output: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(title="Hermes Inference API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predict")
def predict(request: PredictRequest) -> PredictResponse:
    model_path = Path(getenv("MODEL_DIR", "/models")) / "baseline.joblib"
    if model_path.exists():
        return _model_prediction(request, model_path)
    return _heuristic_prediction(request)


def _model_prediction(request: PredictRequest, model_path: Path) -> PredictResponse:
    artifact = joblib.load(model_path)
    model = artifact["model"] if isinstance(artifact, dict) and "model" in artifact else artifact
    version = artifact.get("version", getenv("MODEL_VERSION", "baseline-joblib")) if isinstance(artifact, dict) else "baseline-joblib"
    feature_order = artifact.get("feature_order", FEATURE_ORDER) if isinstance(artifact, dict) else FEATURE_ORDER
    buy_threshold = float(artifact.get("buy_threshold", 0.58)) if isinstance(artifact, dict) else 0.58
    sell_threshold = float(artifact.get("sell_threshold", 0.42)) if isinstance(artifact, dict) else 0.42
    x = np.array([[float(request.features.get(name, 0.0)) for name in feature_order]])
    probability_up = float(model.predict_proba(x)[0][1])
    action = _action_from_probability(probability_up, buy_threshold, sell_threshold)
    return PredictResponse(
        symbol=request.symbol.upper(),
        predicted_action=action,
        predicted_return=float(request.features.get("returns_5", 0.0)),
        confidence=max(probability_up, 1.0 - probability_up),
        model_name="sklearn-baseline",
        model_version=version,
        raw_output={
            "probability_up": probability_up,
            "feature_order": feature_order,
            "buy_threshold": buy_threshold,
            "sell_threshold": sell_threshold,
        },
    )


def _heuristic_prediction(request: PredictRequest) -> PredictResponse:
    returns_5 = float(request.features.get("returns_5", 0.0))
    ma_distance = float(request.features.get("moving_average_distance_20", 0.0))
    daily_returns_60 = float(request.features.get("daily_returns_60", 0.0))
    trend_regime = float(request.features.get("trend_regime", 0.0))
    drawdown = abs(float(request.features.get("drawdown_from_52w_high", 0.0)))
    volatility = abs(float(request.features.get("volatility_20", 0.0)))
    score = (
        (returns_5 * 2.0)
        + (ma_distance * 1.5)
        + (daily_returns_60 * 1.5)
        + (trend_regime * 0.04)
        - min(volatility, 0.05)
        - min(drawdown, 0.2) * 0.15
    )
    probability_up = max(0.05, min(0.95, 0.5 + score))
    return PredictResponse(
        symbol=request.symbol.upper(),
        predicted_action=_action_from_probability(probability_up),
        predicted_return=score,
        confidence=max(probability_up, 1.0 - probability_up),
        model_name="heuristic-baseline",
        model_version=getenv("MODEL_VERSION", "baseline-heuristic-v0"),
        raw_output={
            "probability_up": probability_up,
            "score": score,
            "source": "heuristic",
            "feature_version": request.features.get("feature_version", FEATURE_VERSION),
        },
    )


def _action_from_probability(
    probability_up: float,
    buy_threshold: float = 0.58,
    sell_threshold: float = 0.42,
) -> Action:
    if probability_up > buy_threshold:
        return "buy"
    if probability_up < sell_threshold:
        return "sell"
    return "hold"
