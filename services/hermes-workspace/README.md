# Hermes Workspace

All-in-one Hermes runtime for this stack.

This image combines:

- Hermes gateway API on `8642`
- Hermes built-in dashboard on `9119`
- Hermes Workspace UI on `3000`

Hermes state, config, runtime files, and private service env all live here:

```text
services/hermes-workspace -> /opt/data
```

Workspace talks to Hermes locally inside the same container:

```text
HERMES_API_URL=http://127.0.0.1:8642
HERMES_DASHBOARD_URL=http://127.0.0.1:9119
```

MCP Marketplace local fallback files:

```text
mcp-presets.json
assets/mcp-presets.seed.json
```

These provide the local `Hermes Trader` preset and avoid the Workspace `local-file: seed asset missing` warning.

`patch-mcp-marketplace.js` is applied during image build so the Marketplace can also show the remote Smithery catalog in fallback mode.

Primary docs:

- [Service doc](../../docs/services/hermes-workspace.md)
- [Environment variables](../../docs/ENVIRONMENT.md)
- [Architecture](../../docs/ARCHITECTURE.md)
