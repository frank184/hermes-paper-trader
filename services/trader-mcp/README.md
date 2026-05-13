# Trader MCP

FastMCP service that exposes the project-safe trading tools to Hermes.

Local endpoint:

```text
http://127.0.0.1:8004/mcp
```

Primary docs:

- [Service doc](../../docs/services/trader-mcp.md)
- [Architecture](../../docs/ARCHITECTURE.md)
- [Postman testing](../../docs/POSTMAN.md)

The MCP tools call the trading orchestrator; this service does not talk to Alpaca directly.

It also does not receive Hermes-only secrets such as `OPEN_AI_TOKEN`.

Current tools:

- `get_portfolio_state`
- `get_open_positions`
- `get_orders`
- `run_backtest_seed`
- `discover_trade_candidates`
- `propose_trade_decision`
- `run_trading_tick`

`run_trading_tick` can discover symbols when called without a symbol list, then runs a dry tick by default.

For dev-only paper plumbing tests, `run_trading_tick` and `propose_trade_decision` accept:

```text
override_action
override_confidence
override_predicted_return
```

These override inference only. The orchestrator still applies policy.

Use `run_backtest_seed` to create historical labeled rows for training without placing paper orders.
