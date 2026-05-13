# Trading Orchestrator

FastAPI service for market data, features, inference calls, policy checks, persistence, and optional Alpaca paper orders.

Local port:

```text
8001
```

Primary docs:

- [Service doc](../../docs/services/trading-orchestrator.md)
- [Architecture](../../docs/ARCHITECTURE.md)
- [Runtime flows](../../docs/FLOWS.md)

Smoke check:

```bash
curl http://127.0.0.1:8001/health
```

Discover candidates:

```bash
curl -X POST http://127.0.0.1:8001/symbols/discover \
  -H 'content-type: application/json' \
  -d '{"max_symbols":3,"strategy":"trend_following","qty":1,"auto_size":true}'
```

List or add DB-controlled symbols:

```bash
curl http://127.0.0.1:8001/symbols

curl -X POST http://127.0.0.1:8001/symbols \
  -H 'content-type: application/json' \
  -d '{"symbol":"GOOGL","enabled":true,"universes":["core"],"validate_with_alpaca":true}'
```

Current positions:

```bash
curl http://127.0.0.1:8001/portfolio/positions
```

Current open orders:

```bash
curl 'http://127.0.0.1:8001/orders?status=open&limit=20'
```

Run a discovery-backed dry tick:

```bash
curl -X POST http://127.0.0.1:8001/ticks/run \
  -H 'content-type: application/json' \
  -d '{"symbols":[],"dry_run":true,"discover_if_empty":true,"max_symbols":2}'
```

Dev-only inference override dry run:

```bash
curl -X POST http://127.0.0.1:8001/decisions/propose \
  -H 'content-type: application/json' \
  -d '{"symbol":"NVDA","qty":1,"dry_run":true,"auto_size":true,"strategy_name":"trend_following","intended_holding_period":"1-5 trading days","override_action":"buy","override_confidence":0.9}'
```

Every persisted decision includes strategy name, intended holding period, and a structured strategy plan. These fields are the handoff point for future scheduled Alpaca automation.

Seed labeled backtest data for inference training:

```bash
curl -X POST http://127.0.0.1:8001/backtests/run \
  -H 'content-type: application/json' \
  -d '{"symbols":["NVDA"],"days":120,"horizon_days":1,"strategy":"trend_following","persist":true}'
```

Environment note: this service receives shared Alpaca settings from root `.env`, not Hermes-only secrets from `services/hermes-workspace/.env`.
