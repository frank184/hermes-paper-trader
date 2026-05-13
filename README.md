# Hermes Paper Trader

Agentic paper-trading research scaffold using Hermes Workspace, Hermes Agent, a narrow project MCP, Alpaca paper trading, FastAPI services, Postgres, and simple inference.

The core rule: Hermes does not talk to Alpaca directly. Hermes calls `trader-mcp`; the orchestrator owns Alpaca access, policy checks, persistence, and paper order submission.

## Quick Start

```bash
cp .env.example .env
cp services/hermes-workspace/.env.example services/hermes-workspace/.env
# edit .env with Alpaca paper API credentials
# edit services/hermes-workspace/.env with Hermes/Workspace-only secrets
docker compose up --build
```

Useful local URLs:

- Hermes Workspace: `http://127.0.0.1:3000`
- Hermes native dashboard: `http://127.0.0.1:9119`
- Hermes gateway health: `http://127.0.0.1:8642/health`
- Trading orchestrator: `http://127.0.0.1:8001`
- Inference API: `http://127.0.0.1:8002`
- Trader MCP: `http://127.0.0.1:8004/mcp`

Optional notebooks:

```bash
docker compose --profile notebooks up jupyter
```

Then open `http://127.0.0.1:8888`.

## Service Entry Points

- [Trading Orchestrator](services/trading-orchestrator/README.md)
- [Inference API](services/inference-api/README.md)
- [Trader MCP](services/trader-mcp/README.md)
- [Hermes Workspace](services/hermes-workspace/README.md)
- [Jupyter](services/jupyter/README.md)

## Project Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Environment Variables](docs/ENVIRONMENT.md)
- [Runtime Flows](docs/FLOWS.md)
- [Postman Testing](docs/POSTMAN.md)
- [Notebooks](docs/NOTEBOOKS.md)
- [Service Docs](docs/services/)

## Manual Smoke Checks

```bash
./scripts/smoke.sh
```

Dry-run decision:

```bash
curl -X POST http://127.0.0.1:8001/decisions/propose \
  -H 'content-type: application/json' \
  -d '{"symbol":"SPY","qty":1,"dry_run":true,"auto_size":true}'
```

Import [postman/hermes-paper-trader.postman_collection.json](postman/hermes-paper-trader.postman_collection.json) for REST and MCP requests.
