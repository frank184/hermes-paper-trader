# Data Access Strategy Plan

## Summary

Define when Trader should use persisted local data, when it should pull fresh data from Alpaca, and when it should stream live data. The goal is to avoid stale decisions without turning every dashboard view, model query, or report into an unnecessary API call.

References:

- Alpaca multi-strategy backtesting dashboard article: https://alpaca.markets/learn/from-value-investing-to-systematic-trading-building-a-multi-strategy-backtesting-dashboard-with-ai-and-alpaca
- Alpaca getting started docs: https://docs.alpaca.markets/us/docs/getting-started

This project remains educational paper-trading infrastructure, not investment advice or a recommendation to trade any security.

## Proposed Shape

Use three data modes:

- Persisted data: Postgres-owned bars, features, decisions, orders, outcomes, backtests, and reports.
- Pull data: explicit Alpaca REST reads through `trading-orchestrator` for historical bars, account state, positions, orders, assets, and market clock.
- Stream data: later real-time market/order/account monitoring for open dashboards and autonomous strategy health.

No frontend, MCP, notebook, or runner should call Alpaca directly. All fresh pulls and streams go through orchestrator-owned clients.

## When To Use Persisted Data

- Backtest reproduction.
- Model training.
- Dataset inspection.
- Historical charts where the requested range is already complete.
- Strategy review and reporting.
- Joining decisions to outcomes.
- Comparing paper outcomes against backtest cohorts.

Persisted data is the source of truth for research and audit trails.

## When To Pull Fresh Data

- User explicitly asks for current account, positions, orders, or market clock.
- Dashboard opens a portfolio view and needs a fresh snapshot.
- Market bars are missing for the requested symbol/timeframe/date range.
- A backtest requests a range not yet present in `market_bars`.
- A strategy runner is about to make a scheduled decision and needs fresh enough bars/account state.
- Symbol validation needs Alpaca asset metadata.

Fresh pulls should persist reusable data before returning it when the data can support future research.

## When To Stream Data

Streaming is not required for the next MVP, but should be planned for:

- Open dashboard pages that need live order, fill, and position updates.
- Strategy-runner health monitoring during market hours.
- Intraday strategies where REST polling is too slow or wasteful.
- Alerts for order fills, rejected orders, circuit breakers, and regime changes.

Streaming output should still write meaningful snapshots or events to Postgres so later reports can explain what happened.

## Required Orchestrator/API Work

- Add cache metadata to market responses: source, persisted row count, fetched row count, and freshness timestamp.
- Add `force_refresh` and `persist` flags to market-data endpoints.
- Add freshness policy helpers per data class:
  - account, positions, orders: short freshness window.
  - daily bars: complete through latest market close unless forced.
  - intraday bars: short freshness window during market hours.
  - assets and symbol metadata: longer freshness window.
- Add read endpoints that can answer from Postgres only for dashboards and notebooks.
- Add future streaming endpoints or event tables without requiring dashboard changes to Alpaca credentials.

## Data Model Work

- Track data freshness per symbol/timeframe/range.
- Track ingestion source and fetch time for market bars.
- Track account, position, and order snapshots separately from current Alpaca state.
- Track stream events once streaming is added.
- Track whether a report was generated from persisted data, freshly pulled data, or mixed sources.

## Test Plan

- Verify a historical chart uses persisted bars when the range is complete.
- Verify missing bars trigger an Alpaca pull through orchestrator and persist results.
- Verify `force_refresh=true` bypasses stale local data.
- Verify dashboard portfolio views can request fresh snapshots without direct Alpaca access.
- Verify backtests are reproducible from persisted bars and record any fresh ingestion they required.

## Assumptions

- Postgres is the research/audit source of truth.
- Alpaca REST remains the first implementation for fresh data.
- Streaming is future work, but the data model should not block it.
- Data access rules should be enforced in `trading-orchestrator`, not in Hermes or frontend clients.
