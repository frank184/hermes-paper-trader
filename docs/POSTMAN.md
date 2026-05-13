# Postman Testing

Import:

```text
postman/hermes-paper-trader.postman_collection.json
```

The collection covers REST and MCP.

## REST Checks

Use these first:

- `REST - Trading Orchestrator / Health`
- `REST - Inference API / Health`
- `REST - Inference API / Predict`
- `REST - Trading Orchestrator / Discover Symbols`
- `REST - Trading Orchestrator / Current Positions`
- `REST - Trading Orchestrator / Current Orders`
- `REST - Trading Orchestrator / Propose Decision - Dry Run`

The inference requests do not touch Alpaca or Postgres. Orchestrator requests do touch Alpaca and persist rows.

## MCP Checks

MCP over streamable HTTP needs a session.

Run in order:

```text
1. MCP - Trader MCP / Initialize
2. MCP - Trader MCP / Initialized Notification
3. MCP - Trader MCP / Tools List
4. MCP - Trader MCP / Tools Call - ...
```

The initialize request stores the `mcp-session-id` response header in a collection variable. Later MCP requests use that value.

MCP responses are `text/event-stream`; the JSON-RPC response appears in `data:` lines.

Useful Trader MCP calls:

- `get_portfolio_state`: account cash/equity/buying power.
- `get_open_positions`: filled holdings only.
- `get_orders`: accepted/open/closed order records, including orders that have not filled yet.

## Safe Defaults

Keep:

```json
{
  "dry_run": true
}
```

Only use `dry_run=false` when you intentionally want to allow a paper order if policy approves it.

Use `auto_size=true` while testing. It lets the orchestrator reduce `qty` to fit `MAX_NOTIONAL_PER_TRADE` and returns the requested/effective quantities in the response.
