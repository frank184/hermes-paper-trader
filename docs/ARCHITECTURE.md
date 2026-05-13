# Architecture

Hermes Paper Trader is a paper-trading research loop. It is designed to generate auditable decision data first; trading behavior is intentionally constrained.

## System Shape

```text
Hermes Workspace / Hermes Agent
  |
  | MCP tool calls
  v
trader-mcp
  |
  | HTTP
  v
trading-orchestrator
  |        |
  |        +--> inference-api
  |        |
  |        +--> Postgres
  |
  +--> alpaca-py SDK
       |
       v
    Alpaca paper API
```

## Main Boundary

Hermes only receives the project MCP:

```text
Hermes -> trader-mcp
```

Hermes does not receive direct Alpaca MCP access. That keeps the agent behind a project-specific tool surface:

- `run_trading_tick`
- `propose_trade_decision`
- `get_portfolio_state`

Those calls route through the orchestrator, which applies policy and writes an audit trail.

## Secret Boundary

Runtime secrets are split by audience:

```text
.env                  -> shared project settings and Alpaca credentials
services/hermes-workspace/.env -> Hermes-only secrets such as OPEN_AI_TOKEN
```

Only `hermes-workspace` loads `services/hermes-workspace/.env`. See [Environment Variables](ENVIRONMENT.md).

## Why Not Direct Alpaca MCP?

Direct Alpaca MCP access would let Hermes inspect or act through Alpaca’s broad tool surface. That is useful for exploration, but weaker for this project’s goal: controlled paper trading with reproducible data.

This project uses `alpaca-py` inside the orchestrator because execution is easier to type, test, log, and constrain in normal Python code.

## Data Product

The main artifact is not a clever trade. The main artifact is a durable row chain:

```text
market snapshot
  -> feature snapshot
  -> inference run
  -> agent decision
  -> optional paper order
  -> later outcome label
```

That chain becomes training and evaluation data.

## Runtime Services

- `postgres`: durable experiment and audit data.
- `trading-orchestrator`: market data, features, inference call, policy, persistence, paper orders.
- `inference-api`: heuristic baseline now; optional sklearn model artifact later.
- `trader-mcp`: MCP wrapper exposing only project tools.
- `hermes-workspace`: all-in-one Hermes gateway, Hermes native dashboard, and Hermes Workspace UI.
- `jupyter`: optional notebook server for research and inspection.

See [docs/services](services/) for service-level detail.
