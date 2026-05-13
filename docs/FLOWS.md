# Runtime Flows

## Dry-Run Decision

Used for normal development and data collection without order submission.

```text
POST /decisions/propose
  -> fetch latest Alpaca bar data
  -> insert market_snapshots
  -> compute features
  -> insert feature_snapshots
  -> POST inference-api /predict
  -> insert inference_runs
  -> evaluate policy
  -> insert agent_decisions with strategy_name, intended_holding_period, strategy_plan
  -> return decision
```

With `dry_run=true`, no order is submitted even if policy approves.

## Inference Override Flow

Used to test paper order plumbing before the model is trained.

```text
POST /decisions/propose {
  symbol: "NVDA",
  dry_run: true,
  override_action: "buy",
  override_confidence: 0.9
}
  -> fetch latest Alpaca bar data
  -> call inference-api
  -> replace inference action/confidence with explicit override
  -> apply normal policy
  -> persist the decision
```

The override does not bypass policy. It only prevents the untrained inference model from forcing every decision to `hold`.

## Discovery Tick

Used when Hermes asks to run a tick without specifying symbols.

```text
POST /ticks/run { symbols: [], discover_if_empty: true }
  -> seed/read enabled symbols from Postgres
  -> fetch recent + daily bars for each candidate
  -> upsert bars into market_bars
  -> size requested qty under max notional
  -> run normal dry-run decision flow for selected candidates
```

Discovery is bounded by the enabled Postgres symbol universe. Env only seeds the universe.

## Symbol Control Flow

Used to change what Trader is allowed to scan without editing Compose.

```text
Trader MCP add_symbol / import_symbols
  -> orchestrator validates symbol with Alpaca when requested
  -> upsert symbols
  -> attach symbol to a universe
  -> future scans and policy checks read DB state
```

Disabling a symbol prevents new scans/trades for it without deleting historical data.

## Paper Order Decision

Same as dry-run, but with order submission enabled.

```text
POST /decisions/propose { dry_run: false }
  -> all dry-run steps
  -> if policy approved:
       submit Alpaca paper market order
       insert paper_orders
```

Policy can still reject the decision. Rejections are persisted.

## Strategy Plan Flow

Every decision should carry a thesis and expected hold length:

```text
Hermes / MCP request
  -> strategy_name
  -> intended_holding_period
  -> strategy_plan
  -> orchestrator persists these on agent_decisions
  -> future monitoring/algo jobs can schedule reviews and exits
```

If Hermes does not provide a holding period, the orchestrator defaults to `1-5 trading days`. Model artifacts can later provide their own horizon in `raw_output`.

## Hermes Tool Flow

Hermes does not call the orchestrator REST API directly. It calls MCP tools.

```text
Hermes
  -> trader-mcp tools/call
  -> trading-orchestrator REST
  -> inference/Postgres/Alpaca
```

This is the flow that should resemble production agent behavior.

## Inference-Only Flow

Used for model behavior checks without Alpaca or Postgres.

```text
POST inference-api /predict
  -> load models/baseline.joblib if present
  -> otherwise use heuristic baseline
  -> return action/confidence/metadata
```

Useful for Postman and notebook tests.

## Notebook Flow

Jupyter is optional and starts with:

```bash
docker compose up jupyter
```

It mounts:

```text
./notebooks -> /home/jovyan/work
./models    -> /home/jovyan/work/models
```

Use notebooks for research, not runtime control.
