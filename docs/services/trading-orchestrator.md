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
- Discover candidate symbols from the configured allowlist.
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
POST /backtests/run
POST /decisions/propose
POST /ticks/run
POST /symbols/discover
```

`/orders` reads live Alpaca paper orders and refreshes local `paper_orders` rows. This is the endpoint to use when an order is visible in Alpaca as `accepted`, `new`, `filled`, `canceled`, or similar. An accepted order with `filled_qty=0` is not a position yet.

`/market/clock` explains whether the market is currently open. A normal market order with `extended_hours=false` can sit as `new` or `accepted` until regular market hours.

`DELETE /orders/{order_id}` requests cancellation for a pending Alpaca paper order.

`/backtests/run` fetches historical daily bars, computes features at each historical point, looks forward by `horizon_days`, and writes labeled training rows. It is the preferred way to seed `trade_outcomes` before the paper agent has enough real fills.

Example:

```json
{
  "symbols": ["NVDA"],
  "days": 120,
  "horizon_days": 1,
  "label_threshold": 0.0025,
  "strategy": "moving_average",
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

Then run `./scripts/train.sh` to train the inference model from those labels.

`/symbols/discover` ranks symbols from `SYMBOL_ALLOWLIST` using one of:

- `random`: bounded random sample from eligible allowlist symbols.
- `liquidity`: latest minute volume.
- `momentum`: recent return plus moving-average distance, penalized by volatility.

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
- Symbol allowlist.
- Max notional per trade.
- Max daily trades.
- Minimum confidence.
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
- `backtest_runs`

Order reads can refresh `paper_orders` from Alpaca even when the order has not filled yet.

## Runtime Path

```text
trader-mcp -> trading-orchestrator -> inference-api
                                  -> Postgres
                                  -> Alpaca paper API
```
