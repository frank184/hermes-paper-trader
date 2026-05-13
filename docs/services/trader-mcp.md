# Trader MCP

Trader MCP exposes the safe project tool surface to Hermes.

## Service

```text
services/trader-mcp
```

Local endpoint:

```text
http://127.0.0.1:8004/mcp
```

## Why It Exists

Hermes should not receive direct Alpaca access. Instead, Hermes receives project tools that call the orchestrator.

```text
Hermes -> trader-mcp -> trading-orchestrator
```

## Tools

```text
run_trading_tick
discover_trade_candidates
propose_trade_decision
get_portfolio_state
get_open_positions
get_orders
get_order
cancel_order
get_market_clock
run_backtest_seed
```

`run_trading_tick` accepts explicit symbols, but it can also discover candidates when `symbols` is omitted:

```json
{
  "symbols": [],
  "discover_if_empty": true,
  "discovery_strategy": "random",
  "max_symbols": 3,
  "qty": 1,
  "auto_size": true,
  "dry_run": true
}
```

`discover_trade_candidates` exposes discovery without running decisions, which is useful when you want Hermes to inspect candidates first.

`get_open_positions` returns current Alpaca paper positions and persists a position snapshot.

`get_orders` returns live Alpaca paper orders and syncs local order rows. Use it to inspect accepted/open orders that have not filled and therefore do not appear under positions.

`get_market_clock` returns the Alpaca market clock, which is useful when explaining queued orders.

`cancel_order` requests cancellation for a pending paper order by Alpaca order id.

`run_backtest_seed` calls `/backtests/run` and persists labeled historical rows for model training. It does not submit paper orders.

## MCP Notes

The service uses streamable HTTP. MCP clients must:

1. call `initialize`
2. send `notifications/initialized`
3. call `tools/list` or `tools/call`

Postman examples live in:

```text
postman/hermes-paper-trader.postman_collection.json
```

## Safety Boundary

Trader MCP does not place orders itself. It delegates to the orchestrator, which applies policy and persistence.
