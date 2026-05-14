# Trader Roadmap TODOs

This is the prioritized implementation map for the Trader roadmap. The detailed planning docs live in [`docs/todos/`](todos/).

The main sequencing rule: stabilize data, backtesting, and reporting before building a large dashboard. The dashboard is useful, but it should sit on stable APIs and persisted research objects instead of forcing UI rewrites while the backend shape is still changing.

This project remains educational paper-trading infrastructure, not investment advice or a recommendation to trade any security.

## Priority 1: Data Access Foundation

Detailed plan: [Data Access Strategy](todos/DATA_ACCESS_STRATEGY.md)

Why first:

- Every other feature needs a clear answer to "use Postgres, pull Alpaca, or stream live?"
- Backtests need reproducible data.
- Dashboard views need freshness metadata.
- Reports need to say whether they used persisted, fresh, or mixed data.

Initial implementation slice:

- Add freshness metadata to market-data responses.
- Add `force_refresh` and `persist` behavior where market data is fetched.
- Record whether rows were served from Postgres, fetched from Alpaca, or mixed.
- Define freshness windows for daily bars, intraday bars, account state, positions, orders, and assets.
- Keep all Alpaca data access inside `trading-orchestrator`.

Done when:

- A chart/backtest/report can explain what data source it used.
- Missing market bars are pulled and persisted through the orchestrator.
- Existing persisted bars are reused when fresh enough.

## Priority 2: Backtesting Infrastructure

Detailed plan: [Backtesting Infrastructure](todos/BACKTESTING_INFRASTRUCTURE.md)

Why second:

- The dashboard's highest-value page is backtesting, but it needs stable run records, metrics, trades, equity curves, and parameters.
- Strategy autonomy should not run until backtests can produce reproducible expectations.
- Model training needs better labeled rows than ad hoc paper decisions.

Initial implementation slice:

- Persist full backtest request/config payloads.
- Add equity curve point storage.
- Add run metric storage for return, drawdown, win rate, average win/loss, exposure, and trade count.
- Add `GET /backtests/runs`, `GET /backtests/runs/{id}`, and `GET /backtests/runs/{id}/trades`.
- Add basic saved sweep/preset records.
- Add expected-vs-actual placeholders linked to strategy, symbol, regime, and intended holding period.

Done when:

- A backtest can be reproduced from persisted config and market data.
- A run can be listed, opened, charted, and inspected without rerunning.
- Sweep results can be compared and ranked by robust metrics, not only final P/L.

## Priority 3: Observability And Reporting

Detailed plan: [Observability And Reporting](todos/OBSERVABILITY_REPORTING.md)

Why third:

- Reports are useful before a full dashboard exists.
- Hermes can consume reports immediately through Trader MCP.
- Strategy autonomy needs health, drift, circuit breaker, and trade-review outputs.

Initial implementation slice:

- Add a daily digest report endpoint.
- Add a backtest report endpoint.
- Add a trade review report shape that links decision, order, strategy plan, fill, and outcome.
- Generate Markdown and JSON artifacts.
- Add Discord-style event-card payloads for entry, exit, rejection, circuit breaker, and digest events.

Done when:

- Hermes can ask for a readable digest without stitching raw rows.
- A trade review explains why a decision happened and whether the result matched expectations.
- Reports are saved as artifacts and can later be rendered by the dashboard.

## Priority 4: Minimal Trader Dashboard

Detailed plan: [Trader Dashboard](todos/TRADER_DASHBOARD.md)

Why fourth:

- The dashboard should be a client of stable orchestrator APIs, not the thing that defines them by accident.
- Once data/backtests/reports exist, the dashboard can focus on workflow and visualization instead of backend churn.

Initial implementation slice:

- Add a `trader-dashboard` React + Vite + TypeScript service.
- Build a Backtesting page first:
  - left control rail
  - symbol chips
  - date range
  - initial capital
  - max positions
  - max position size
  - slippage
  - strategy sliders
  - run/reset/save/compare controls
  - equity curve and metric cards.
- Add a Symbols page for import, enable, disable, and universe membership.
- Add a Reports page for generated Markdown/JSON artifacts.
- Add a Portfolio page for account, positions, orders, and market clock.

Done when:

- A user can import symbols, run a backtest, view metrics/charts/trades, and open the generated report from the UI.
- The dashboard never owns Alpaca credentials.
- The dashboard talks only to `trading-orchestrator`.

## Priority 5: Strategy Autonomy

Detailed plan: [Strategy Autonomy](todos/STRATEGY_AUTONOMY.md)

Why last:

- Autonomy should automate a system with proven data freshness, backtesting, reporting, and policy boundaries.
- Running strategies before validation/reporting exists makes failures harder to explain.
- Human pause/resume/override audit should exist before scheduled execution becomes routine.

Initial implementation slice:

- Add a `strategy-runner` service in dry-run mode only.
- Store strategy configs, schedules, health snapshots, and runs in Postgres.
- Run scheduled scans/ticks through existing orchestrator endpoints.
- Persist strategy plan, intended holding period, exit plan, review time, and risk notes for each autonomous decision.
- Add manual pause/resume/override events with required reasons.
- Add circuit breaker states for max loss, max exposure, stale data, repeated rejection, and unhealthy strategy.

Done when:

- A dry-run strategy can run unattended and create auditable decisions.
- Paper-order mode remains opt-in and still goes only through orchestrator policy.
- Hermes can query status, but Hermes is not needed for scheduled execution.

## Cross-Cutting Constraints

- Paper trading only.
- Alpaca access remains inside `trading-orchestrator`.
- Postgres is the research and audit source of truth.
- Env vars define hard safety defaults; runtime entities like symbols and strategy configs live in Postgres.
- Random strategies are control baselines only, never autonomous order strategies.
- Dashboard and Hermes should render summaries, reports, and charts, but should not bypass policy or persistence.

## Suggested First Pull Request

Build Priority 1 plus a thin part of Priority 2:

- Add market-data freshness metadata.
- Add `force_refresh` behavior.
- Persist full backtest config payloads.
- Add equity curve point and run metric storage.
- Add read endpoints for backtest runs and trades.

That PR gives the project stable backend objects that the dashboard, reports, and autonomy work can use without immediate rewrites.
