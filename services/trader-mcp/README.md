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

- `list_symbols`
- `add_symbol`
- `disable_symbol`
- `import_symbols`
- `scan_trade_candidates`
- `get_portfolio_state`
- `get_open_positions`
- `get_orders`
- `get_market_bars`
- `chart_symbol`
- `chart_backtest`
- `get_symbol_report`
- `get_portfolio_report`
- `run_backtest_seed`
- `run_backtest_sweep`
- `discover_trade_candidates`
- `propose_trade_decision`
- `run_trading_tick`

`run_trading_tick` can discover symbols from the Postgres-backed symbol universe when called without a symbol list, then runs a dry tick by default.

For dev-only paper plumbing tests, `run_trading_tick` and `propose_trade_decision` accept:

```text
override_action
override_confidence
override_predicted_return
```

These override inference only. The orchestrator still applies policy.

Use `run_backtest_seed` to create historical labeled rows for training without placing paper orders.
