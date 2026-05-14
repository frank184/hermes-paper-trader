# Backtesting Infrastructure Plan

## Summary

Upgrade the current orchestrator backtesting path into a stronger, reproducible research stack. The article's key lesson is that a backtesting dashboard is useful when data ingestion, signals, simulation, and rendering are separated, parameters can be adjusted quickly, and results are evaluated for robustness instead of overfit headline returns.

References:

- Alpaca multi-strategy backtesting dashboard article: https://alpaca.markets/learn/from-value-investing-to-systematic-trading-building-a-multi-strategy-backtesting-dashboard-with-ai-and-alpaca
- Alpaca getting started docs: https://docs.alpaca.markets/us/docs/getting-started

This project remains educational paper-trading infrastructure, not investment advice or a recommendation to trade any security.

## Proposed Shape

Preserve strict separation of concerns:

- Alpaca/market data ingestion: fetch historical bars, persist reusable `market_bars`, never mix broker calls with strategy logic.
- Feature generation: one shared feature path for runtime decisions, notebooks, model training, scans, and backtests.
- Signal/strategy computation: strategy modules produce action, confidence, intended hold, and exit thesis from features.
- Simulation/execution modeling: backtest engine applies fills, slippage, spreads, sizing, capital limits, stops, cooldowns, and risk rules.
- Result persistence/rendering: persist inputs, config, trades, equity curve, metrics, labels, and chart artifacts.

The backtest engine should remain paper/research only. It should create training labels and decision audit rows, but it must not submit Alpaca orders.

## Required Orchestrator/API Work

- Expand `POST /backtests/run` to accept:
  - strategy config
  - start/end dates
  - benchmark symbol
  - slippage model
  - spread/fee assumptions
  - stop/trailing stop settings
  - cooldown settings
  - max exposure and allocation constraints.
- Expand `POST /backtests/sweep` to persist named parameter sweeps and compare robustness.
- Add read endpoints for:
  - backtest runs
  - backtest trades
  - equity curve points
  - run metrics
  - per-symbol metrics
  - sweep summaries.
- Keep chart endpoints reusable for both dashboard and Hermes MCP.

## Data Model Work

Add or evolve tables for:

- Strategy definitions/configs: name, version, asset class, enabled flag, default params, risk profile.
- Backtest parameters: complete JSON input, strategy version, feature version, data window, benchmark, friction settings.
- Equity curve points: backtest run, timestamp, equity, drawdown, exposure, cash, benchmark value.
- Run metrics: total return, annualized return, win rate, average win/loss, max drawdown, Sharpe-like ratio, trade count, exposure.
- Strategy allocation records: capital assigned per strategy/universe for combined portfolio simulations.

All backtest rows must be reproducible from persisted input config and persisted or re-fetchable market bars.

## Realism And Safeguards

- Add configurable slippage and spread assumptions even though Alpaca is commission-free for supported retail stock trades.
- Model capital allocation and max position notional; do not let every strategy assume it owns the full account.
- Enforce cooldowns after exits to reduce churn and repeated bad entries.
- Add trailing stops and daily loss limits to test operational safety before live paper automation.
- Preserve long/short controls; shorts remain disabled by default unless explicitly configured for research.
- Always compare against a benchmark and report per-symbol plus combined-portfolio metrics.

Anti-overfitting requirements:

- Support train/test date splits and out-of-sample windows.
- Run parameter perturbation checks around winning configs.
- Record when a result depends on narrow or fragile parameter values.
- Keep `random_baseline` available as a control, not a recommendation strategy.

Live-vs-backtest validation requirements:

- Compare expected return against paper outcome over the intended holding period.
- Compare expected hold period against actual hold period.
- Compare expected drawdown/risk against observed drawdown while the trade was open.
- Compare simulated fill assumptions against paper fill price, fill time, and order status.
- Track strategy drift when recent paper outcomes materially diverge from backtest assumptions.

## UI/Workflow

- Dashboard users choose universe, strategy, date range, initial cash, benchmark, and parameter values.
- Users can run a single backtest, then run a sweep around the same configuration.
- Results show equity curve, benchmark curve, drawdown, trade log, per-symbol metrics, and generated labels.
- Sweeps rank configs by robust metrics, not only final P/L.
- Parameter controls should support sliders/ranges, saved presets, before/after comparisons, and quick `-20%`/base/`+20%` robustness checks.
- Validation views should show whether paper trades behaved like the matching backtest cohort.

## Test Plan

- Verify two runs with the same data/config produce the same trades and metrics.
- Verify slippage/spread settings change P/L in the expected direction.
- Verify cooldowns reduce eligible entries after exits.
- Verify train/test splits produce separate metrics.
- Verify sweep results persist and can be reloaded by dashboard and MCP.
- Verify generated labels are linked to feature version, strategy version, and source backtest.
- Verify paper outcomes can be joined back to backtest expectations by strategy, symbol, regime, and intended holding period.
- Verify parameter perturbation checks identify fragile configs that only work at one narrow setting.

## Assumptions

- Alpaca remains the source for equities historical bars.
- Postgres remains the source of truth for persisted research data.
- The first implementation supports equities only; crypto/other asset classes remain future work.
- Backtesting is for research and dataset generation, not proof of future returns.
