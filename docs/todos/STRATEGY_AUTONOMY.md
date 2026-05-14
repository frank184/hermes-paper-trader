# Strategy Autonomy Plan

## Summary

Move from Hermes-driven manual prompts toward scheduled paper-trading strategies that can run without Hermes in the execution loop. Hermes remains useful for observability, ad hoc research, and explanations, but strategy execution should be owned by deterministic services reading configuration from Postgres and submitting only through Trader Orchestrator policy.

References:

- Alpaca multi-strategy backtesting dashboard article: https://alpaca.markets/learn/from-value-investing-to-systematic-trading-building-a-multi-strategy-backtesting-dashboard-with-ai-and-alpaca
- Alpaca getting started docs: https://docs.alpaca.markets/us/docs/getting-started

This project remains educational paper-trading infrastructure, not investment advice or a recommendation to trade any security.

## Proposed Shape

Add a new autonomous execution service, tentatively `strategy-runner`.

Responsibilities:

- Read enabled strategy configs, universes, schedules, risk settings, and allocation limits from Postgres.
- Run scans and decision ticks on schedule without Hermes.
- Submit paper orders only through `trading-orchestrator`, never directly to Alpaca.
- Persist strategy plan, intended holding period, entry thesis, exit plan, risk notes, and run metadata with every decision.
- Emit health status and notifications/digests for humans.
- Record every human override, manual pause, resume, and risk exception with a reason.

Process isolation should be staged:

- MVP: one `strategy-runner` service can execute many strategies, but each strategy must have independent persisted state, health status, cooldown state, and circuit breaker state.
- Later: split high-value strategies into independently restartable workers so one failing strategy does not stop other strategies.
- Dashboard and reports should treat each strategy as an independent actor even during the MVP single-process implementation.

Hermes role after autonomy:

- Ask questions about status, positions, outcomes, and strategy behavior.
- Trigger ad hoc scans, reports, charts, and dry runs.
- Never be required for a scheduled strategy to execute.

## Strategy Framework

Initial strategy families:

- Trend following: prefers aligned multi-window returns and moving averages.
- Breakout: prefers proximity to recent highs plus volume confirmation.
- Mean reversion watch: identifies pullbacks that may be candidates for later confirmation.
- Liquidity/risk-off: prioritizes liquidity, reduces exposure, and can pause risky strategies.
- Random baseline: control testing only; never used for autonomous order submission.

Each strategy config should define:

- universe
- schedule
- max symbols per run
- capital allocation
- intended holding period
- entry rules
- exit rules
- stop/trailing stop rules
- cooldown
- max daily loss
- whether shorts are allowed.

## Regime And Strategy Selection

Add regime detection as a first-class input before choosing actions:

- volatility regime
- trend/range classification
- drawdown from recent highs
- distance from recent lows
- volume anomalies
- current position exposure
- recent strategy performance.

Strategy selection should happen per symbol/universe, not as one global setting. The runner should prefer strategy diversification: multiple small, independently tracked strategies with separate capital allocation and risk limits.

## Required Orchestrator/API Work

- Add CRUD endpoints for strategy configs and schedules.
- Add runner-facing endpoints to:
  - list enabled strategy configs
  - record strategy run start/finish
  - request a policy-gated paper decision
  - record circuit breaker state
  - summarize current risk and exposure.
- Add lifecycle endpoints for active strategy state:
  - pause strategy
  - resume strategy
  - force cooldown
  - disable symbol for strategy.
- Add human intervention endpoints for:
  - manual pause with reason
  - manual resume with reason
  - risk override with reason
  - order cancel with reason
  - strategy config change with reason.

The runner should call existing `/symbols/scan`, `/ticks/run`, `/decisions/propose`, `/orders`, `/portfolio/state`, and `/portfolio/positions` paths where possible.

## Data Model Work

Add or evolve tables for:

- Strategy configs: name, version, enabled, universe, parameters, allocation, risk settings.
- Strategy schedules: cron/interval, market-hours-only flag, next run time, last run time.
- Strategy runs: status, started_at, finished_at, symbols scanned, decisions created, orders submitted.
- Regime snapshots: symbol/universe, detected regime, features, created_at.
- Circuit breakers: strategy, reason, triggered_at, cleared_at, status.
- Notifications: channel, severity, message, related decision/order/run.
- Human interventions: actor, action, reason, previous state, new state, related strategy/order/decision, created_at.
- Strategy health snapshots: strategy, status, heartbeat_at, last_success_at, last_failure_at, current blocker.

Existing `agent_decisions` fields for `strategy_name`, `intended_holding_period`, and `strategy_plan` remain required for every autonomous decision.
Every autonomous decision must also include an exit plan and review time derived from the strategy config.

## Safety And Operations

- Paper-only default; do not add live trading in this phase.
- Shorts disabled by default; sell-to-close remains allowed.
- Enforce max daily loss, max position notional, max strategy allocation, max account exposure, and max daily trades.
- Enforce cooldown after exits and after rejected/high-risk decisions.
- Add health checks so a strategy can be marked unhealthy without stopping the whole stack.
- Add notifications/digests for orders, fills, rejected decisions, regime changes, circuit breakers, and daily summaries.
- Keep all order placement behind orchestrator policy, even for autonomous services.
- Treat manual overrides as auditable events, not silent state changes.
- If a strategy is paused by circuit breaker or human intervention, it must stay paused until an explicit resume event clears the blocker.

## UI/Workflow

- Dashboard users create/edit strategy configs and schedules.
- Users can enable a strategy in dry-run mode before paper-order mode.
- Users can see active strategies, latest runs, circuit breakers, open positions, and orders.
- Users can pause a strategy or disable a symbol without editing env vars or restarting Compose.
- Users can review why a strategy entered, held, exited, paused, or rejected a trade.
- Users can compare recent autonomous outcomes against the strategy's backtest validation profile.

## Test Plan

- Verify a dry-run strategy can run on schedule and create auditable decisions without orders.
- Verify paper-order mode submits only through orchestrator policy.
- Verify circuit breakers pause a strategy after max daily loss or exposure breach.
- Verify cooldown prevents immediate re-entry after exit.
- Verify disabled symbols and paused strategies are skipped.
- Verify notifications/digests are emitted for strategy runs, orders, rejections, and circuit breakers.
- Verify Hermes can query status but is not required for scheduled execution.
- Verify one failing strategy does not corrupt or block another strategy's persisted state.
- Verify pause/resume/override actions require and persist a human-readable reason.
- Verify autonomous decisions include strategy plan, intended holding period, exit plan, and review time.

## Assumptions

- `strategy-runner` is a new service, not a Hermes plugin.
- Alpaca access remains exclusively inside `trading-orchestrator`.
- Paper trading remains the only execution mode.
- Multi-asset support is future work; first implementation focuses on Alpaca equities.
