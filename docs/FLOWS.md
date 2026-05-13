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
  -> insert agent_decisions
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
  -> discover candidates from SYMBOL_ALLOWLIST
  -> fetch recent bars for each candidate
  -> size requested qty under max notional
  -> run normal dry-run decision flow for selected candidates
```

Discovery is bounded. It does not scan the whole market in v0.

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
