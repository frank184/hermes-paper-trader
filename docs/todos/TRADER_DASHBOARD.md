# Trader Dashboard Plan

## Summary

Build a dedicated `trader-dashboard` service for operating and inspecting Trader Orchestrator without Postman or Hermes prompts. The dashboard should make the current paper-trading research system visible: portfolio state, symbol universe controls, historical market data, backtests, generated datasets, charts, settings, and artifacts.

References:

- Alpaca multi-strategy backtesting dashboard article: https://alpaca.markets/learn/from-value-investing-to-systematic-trading-building-a-multi-strategy-backtesting-dashboard-with-ai-and-alpaca
- Alpaca getting started docs: https://docs.alpaca.markets/us/docs/getting-started

This project remains educational paper-trading infrastructure, not investment advice or a recommendation to trade any security.

## Proposed Shape

- Add a new Docker Compose service named `trader-dashboard`.
- Use React + Vite + TypeScript for a fast local app with interactive controls and charts.
- Dashboard talks only to `trading-orchestrator`; it must never call Alpaca directly or own Alpaca credentials.
- Keep Hermes Workspace as the agent UI. Trader Dashboard is the operational research UI.
- Use the same chart artifacts and persisted Postgres data that Trader MCP already exposes.

Core pages:

- Portfolio: account, positions, open orders, market clock, latest paper order states, recent decisions.
- Symbols: DB-backed symbol allowlist/universe management, import, enable, disable, validation status, notes.
- Market Data: persisted `market_bars`, symbol/timeframe/date controls, candle charts, reusable holdings charts.
- Backtesting: run single backtests, run sweeps, compare metrics, show equity curves, inspect trade logs.
- Datasets: inspect `market_bars`, feature snapshots, decisions, inference runs, orders, outcomes, and backtest labels.
- Settings: show hard env safety caps as read-only; expose runtime DB settings as editable once they exist.

## Required Orchestrator/API Work

- Add dashboard-friendly read endpoints for:
  - backtest runs
  - backtest trades
  - generated artifacts
  - recent decisions
  - feature/inference dataset rows
  - symbol universes and symbol membership
  - strategy configs once strategy persistence exists.
- Add pagination, filtering, and sorting to dataset-heavy endpoints.
- Add summary endpoints for portfolio, datasets, backtests, and symbols so the UI does not need to stitch many large responses.
- Return chart artifact paths consistently for JSON, HTML, SVG, and PNG, with PNG as the default inline preview format.

## Data Model Work

- Keep Postgres as the runtime source of truth for symbols, market bars, decisions, orders, outcomes, and backtest rows.
- Add dashboard metadata only when needed, such as saved views, saved filter presets, user notes, and dashboard-visible strategy configs.
- Avoid duplicating Alpaca data in dashboard-local state; the dashboard should render orchestrator responses.

## UI/Workflow

- First workflow: import symbols into `core`, run a backtest, view equity curve, inspect trades, and inspect generated labels.
- Second workflow: view current portfolio, open positions, open orders, and market clock, then open a symbol chart.
- Third workflow: scan candidates, compare strategy scores, and decide whether to run a dry tick or paper order through orchestrator policy.
- Fourth workflow: inspect model/data health by comparing market rows, feature rows, inference runs, decisions, and outcomes.

## Test Plan

- Verify the dashboard can load with only Docker Compose and no direct Alpaca credentials.
- Verify symbol import/enable/disable flows update Postgres through orchestrator endpoints.
- Verify a backtest run can be started, completed, listed, opened, and charted.
- Verify dataset pages can paginate without loading the whole database into the browser.
- Verify chart previews use PNG artifacts and still link to HTML artifacts for full inspection.
- Verify hard safety settings are displayed read-only and cannot be edited from the dashboard.

## Assumptions

- `trader-dashboard` is a new service, separate from Hermes Workspace.
- Alpaca access remains exclusively inside `trading-orchestrator`.
- Paper trading remains the only execution mode.
- Crypto and other asset classes are future expansion ideas from the article, not part of this first dashboard build.
