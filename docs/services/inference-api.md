# Inference API

The inference API scores feature snapshots and returns a suggested action.

## Service

```text
services/inference-api
```

Local port:

```text
8002
```

## Responsibilities

- Accept feature dictionaries.
- Return `buy`, `sell`, or `hold`.
- Return confidence and model metadata.
- Use `models/baseline.joblib` if present.
- Fall back to the heuristic baseline if no model exists.

## Endpoints

```text
GET  /health
POST /predict
```

## Predict Shape

Request:

```json
{
  "symbol": "SPY",
  "features": {
    "returns_5": 0.006,
    "moving_average_distance_20": 0.004,
    "volatility_20": 0.002
  }
}
```

Response:

```json
{
  "symbol": "SPY",
  "predicted_action": "hold",
  "confidence": 0.52,
  "model_name": "heuristic-baseline",
  "model_version": "baseline-heuristic-v0"
}
```

## Training

The training entry point is:

```bash
./scripts/train.sh
```

It currently expects at least 25 labeled `trade_outcomes` rows and both label classes.

To seed those labels without waiting for live paper fills, run a historical backtest through the orchestrator:

```bash
curl -X POST http://127.0.0.1:8001/backtests/run \
  -H 'content-type: application/json' \
  -d '{"symbols":["NVDA","AAPL"],"days":120,"horizon_days":1,"strategy":"moving_average","persist":true}'
```

The backtest writes historical `feature_snapshots` plus `trade_outcomes.label`, then `./scripts/train.sh` can build `models/baseline.joblib`.

The trainer is a supervised model-selection pipeline. It currently compares:

- dummy prior baseline
- logistic regression
- random forest
- extra trees
- histogram gradient boosting
- gradient boosting
- RBF SVC
- k-nearest neighbors
- Gaussian naive Bayes

Most candidates run a small hyperparameter grid search scored by balanced accuracy. The artifact stores the selected model, validation metrics, best parameters, label counts, and tuned buy/sell probability thresholds.

For exploratory work, use:

```text
notebooks/005_model_research_workbench.ipynb
```

That notebook can train against real audit rows, use a clearly marked proxy label while outcomes are missing, compare simple sklearn models, sweep thresholds, and save `models/baseline.joblib`.

Saved artifacts may include:

```text
model
version
feature_order
buy_threshold
sell_threshold
metadata
```

`inference-api` reads `feature_order`, `buy_threshold`, and `sell_threshold` from the artifact when present.
