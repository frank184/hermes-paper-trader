# Observability And Reporting Plan

## Summary

Build reporting around the questions that matter: what happened, why did Trader do it, did the result match the strategy's expectation, and should anything be paused or adjusted. This should avoid overly granular noise while still preserving full audit rows for drilldown.

References:

- Alpaca multi-strategy backtesting dashboard article: https://alpaca.markets/learn/from-value-investing-to-systematic-trading-building-a-multi-strategy-backtesting-dashboard-with-ai-and-alpaca
- Alpaca getting started docs: https://docs.alpaca.markets/us/docs/getting-started

This project remains educational paper-trading infrastructure, not investment advice or a recommendation to trade any security.

## Proposed Shape

Add an observability/reporting layer on top of existing persisted rows.

Primary outputs:

- Daily digest: portfolio state, open orders, fills, rejected decisions, strategy health, circuit breakers, and notable anomalies.
- Strategy report: recent runs, current positions, expected-vs-actual outcomes, drawdown, win/loss attribution, and validation drift.
- Trade review: entry thesis, regime, signal, intended holding period, exit plan, fill quality, outcome, and decision-quality notes.
- Weekly review: strategy changes, best/worst decisions, data quality issues, and recommended experiments.

Reports should summarize first and link to row-level details rather than dumping every event.

## Discord-Style Event Cards

Use the article's Discord bot screenshots as the model for compact event cards.

Cards should be generated for:

- Entry submitted.
- Entry filled.
- Exit submitted.
- Exit filled.
- Strategy paused.
- Strategy resumed.
- Circuit breaker triggered.
- Order rejected or canceled.
- Daily digest.

Each card should include:

- action and symbol
- strategy name/version
- regime
- qty or notional
- reason/thesis
- exit plan or close reason
- P/L when available
- related decision/order/run IDs.

Cards are reporting artifacts first. Delivery can later target dashboard, Hermes, Discord, Slack, email, or webhook.

## Required Orchestrator/API Work

- Add report endpoints for:
  - daily digest
  - strategy summary
  - trade review
  - validation drift
  - data quality summary.
- Add event-card generation endpoints or report payload fields.
- Add a way to persist generated reports as artifacts and structured JSON.
- Add lightweight notification delivery hooks for future Discord/Slack/email/webhook outputs.
- Add report filters for strategy, symbol, universe, date range, and severity.

## Data Model Work

Add or evolve tables for:

- Generated reports: report type, period, payload, artifact paths, created_at.
- Review notes: decision/order/trade reference, note type, human note, automated finding, created_at.
- Validation comparisons: expected return/risk/hold/fill assumptions vs observed results.
- Notification events: destination, severity, status, payload, related report/run/order.
- Event cards: card type, title, summary, payload, related IDs, created_at.

Existing audit rows remain canonical; reports and cards are derived views plus human-readable summaries.

## Report Content

Daily digest should include:

- account equity/cash/buying power
- open positions and P/L
- open orders and stale accepted orders
- decisions approved/rejected
- fills and cancellations
- circuit breakers
- strategy health.

Trade review should include:

- strategy name and version
- symbol and side
- entry thesis
- intended holding period
- exit plan and review time
- regime snapshot
- signal/features summary
- paper fill details
- actual outcome and P/L
- whether the result matched the backtest cohort.

Strategy report should include:

- allocation and exposure
- win rate, average win/loss, drawdown
- recent regime performance
- validation drift
- paused/unhealthy status
- next planned run.

## UI/Workflow

- Dashboard shows a high-level observability page first, with drilldowns to strategy, symbol, and trade reports.
- Hermes can ask for digest/report summaries through Trader MCP.
- Reports should be readable as Markdown artifacts for sharing and review.
- Human review notes should be attachable to a decision, order, trade, strategy run, or report.
- Event cards should render in the dashboard and be reusable for future notification channels.

## Test Plan

- Verify a daily digest can be generated from persisted account, position, order, decision, and strategy state.
- Verify a trade review links decision, order, features, strategy plan, fill, and outcome.
- Verify expected-vs-actual validation rows are included when available and omitted clearly when missing.
- Verify human notes persist and appear in later reports.
- Verify reports can be rendered in dashboard, returned via MCP, and saved as artifacts.
- Verify event cards can be generated for entry, exit, rejection, circuit breaker, and digest events.

## Assumptions

- Reports summarize persisted data; they do not become the source of truth.
- Notifications are planned as delivery outputs, but local report/card generation comes first.
- Discord-style cards are a useful inspiration, but the first implementation can use Markdown and JSON artifacts.
