# Trading Orchestrator

The orchestrator owns the paper-trading control path.

## Service

```text
services/trading-orchestrator
```

Local port:

```text
8001
```

## Responsibilities

- Fetch Alpaca paper market/account data through `alpaca-py`.
- Seed and manage the Postgres-backed symbol universe.
- Discover candidate symbols from enabled DB symbols.
- Fetch and persist reusable market bars.
- Auto-size requested quantities under the max notional rule.
- Compute feature snapshots.
- Call `inference-api`.
- Apply deterministic policy.
- Persist every decision step.
- Submit Alpaca paper orders only when policy approves and `dry_run=false`.

## Endpoints

```text
GET  /health
GET  /portfolio/state
GET  /portfolio/positions
GET  /orders
GET  /orders/{order_id}
DELETE /orders/{order_id}
GET  /market/clock
GET  /symbols
POST /symbols
PATCH /symbols/{symbol}
POST /symbols/import
POST /market/bars
POST /charts/candles
POST /charts/equity-curve
POST /reports/symbol
POST /reports/portfolio
POST /backtests/run
POST /backtests/sweep
POST /decisions/propose
POST /ticks/run
POST /symbols/discover
POST /symbols/scan
GET  /data/market-bars
GET  /data/portfolio-snapshots
GET  /data/position-snapshots
GET  /data/paper-orders
```

`/orders` reads live Alpaca paper orders and refreshes local `paper_orders` rows. This is the endpoint to use when an order is visible in Alpaca as `accepted`, `new`, `filled`, `canceled`, or similar. An accepted order with `filled_qty=0` is not a position yet.

`/market/clock` explains whether the market is currently open. A normal market order with `extended_hours=false` can sit as `new` or `accepted` until regular market hours.

`DELETE /orders/{order_id}` requests cancellation for a pending Alpaca paper order.

`/symbols` is the runtime control surface for tradable symbols. `SYMBOL_ALLOWLIST_SEED` only seeds the DB; enabled rows in Postgres decide what Trader may scan or trade.

`/market/bars` reuses fresh persisted bars when possible and fetches from Alpaca when rows are missing, stale, or `force_refresh=true`. Responses include per-symbol `data_access` metadata showing whether rows came from Postgres, Alpaca, or a mixed path. Charts and backtests use the same path, so historical views and training-data generation can explain whether they reused local rows or refreshed from Alpaca.

`/data/*` endpoints are Postgres-only reads for dashboards and notebooks. They never call Alpaca and return `data_access` freshness metadata so consumers can decide whether to request a fresh orchestrator pull separately.

Chart and report endpoints include `data_access` metadata. Chart endpoints write JSON, self-contained HTML, SVG, and PNG image artifacts into `./artifacts` through the orchestrator container's `/artifacts` mount. The same host folder is mounted into Hermes Workspace at `artifacts/`, so `chart_symbol` and `chart_backtest` responses include `workspace_artifact_paths.html` for a browser-viewable chart and `workspace_artifact_paths.png` for inline chat rendering.

`/backtests/run` fetches historical daily bars, computes features at each historical point, looks forward by `horizon_days`, and writes labeled training rows plus `backtest_trades`. It is the preferred way to seed `trade_outcomes` before the paper agent has enough real fills.

Example:

```json
{
  "symbols": ["NVDA"],
  "days": 120,
  "horizon_days": 1,
  "label_threshold": 0.0025,
  "strategy": "trend_following",
  "persist": true
}
```

This writes:

- `market_snapshots`
- `feature_snapshots`
- `inference_runs`
- `agent_decisions`
- `trade_outcomes`
- `backtest_runs`
- `backtest_trades`

Then run `./scripts/train.sh` to train the inference model from those labels.

`/symbols/discover` and `/symbols/scan` rank enabled symbols using one of:

- `trend_following`: multi-week return and moving-average alignment.
- `breakout`: proximity to recent highs plus volume anomaly.
- `mean_reversion_watch`: pullback candidates inside stronger trend context.
- `liquidity`: latest minute volume.
- `random_baseline`: bounded random sample from eligible DB symbols.

`/ticks/run` can receive explicit symbols or discover candidates when `symbols` is empty and `discover_if_empty=true`.

Decision responses include a `sizing` block:

```json
{
  "requested_qty": 1,
  "effective_qty": 0.6791,
  "effective_notional": 499.99,
  "max_notional": 500,
  "adjusted": true
}
```

That lets the orchestrator reduce something like `SPY qty=1` under the configured trade cap instead of rejecting solely because one share is too expensive.

Decision responses also include a `strategy_plan` block, and the same data is persisted on `agent_decisions`:

```json
{
  "strategy_name": "trend_following",
  "intended_holding_period": "1-5 trading days",
  "monitoring": {
    "review_after": "1-5 trading days",
    "exit_on": [
      "policy breach",
      "opposite model signal",
      "risk limit breach",
      "holding period expires"
    ]
  }
}
```

The holding period is required decision context. A short-horizon signal and a three-month thesis should not be evaluated the same way, and future Alpaca automation should use this field when scheduling reviews or exits.

For dev-only paper testing, decision and tick requests can include an inference override:

```json
{
  "override_action": "buy",
  "override_confidence": 0.9,
  "dry_run": true
}
```

This replaces the inference action/confidence but does not bypass policy. Allowlist, paper-only mode, max notional, daily order cap, and cooldown still apply. Use `dry_run=false` only when intentionally submitting a paper order.

## Policy Checks

- Paper trading only.
- Symbol enabled in Postgres.
- Max notional per trade.
- Max position notional.
- Max daily trades.
- Minimum confidence.
- Short-selling disabled by default.
- Short confidence and trend-alignment checks when shorts are enabled.
- Per-symbol cooldown.
- `hold` is persisted but never submitted as an order.

Daily trade limits and cooldowns count actual `paper_orders`, not dry-run decisions.

## Data Writes

Decision requests can write to:

- `market_snapshots`
- `feature_snapshots`
- `inference_runs`
- `agent_decisions`
- `paper_orders`
- `portfolio_snapshots`
- `position_snapshots`
- `market_bars`
- `symbols`
- `backtest_runs`
- `backtest_trades`

Order reads can refresh `paper_orders` from Alpaca even when the order has not filled yet.

`agent_decisions.strategy_name`, `agent_decisions.intended_holding_period`, and `agent_decisions.strategy_plan` are the audit contract for future automated monitoring jobs.

## Runtime Path

```text
trader-mcp -> trading-orchestrator -> inference-api
                                  -> Postgres
                                  -> Alpaca paper API
```
