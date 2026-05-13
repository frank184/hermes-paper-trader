# Hermes Workspace

`hermes-workspace` is the all-in-one Hermes service used by this project.

## Compose Service

```text
hermes-workspace
```

Local ports:

```text
3000 Workspace UI
8642 Hermes gateway API / health
9119 Hermes built-in dashboard
```

## Runtime Mode

The container starts two local processes:

```text
hermes gateway run
node /opt/hermes-workspace/server-entry.js
```

`hermes gateway run` also starts the built-in dashboard side-process because:

```text
HERMES_DASHBOARD=1
```

Workspace then talks to Hermes inside the same container:

```text
HERMES_API_URL=http://127.0.0.1:8642
HERMES_DASHBOARD_URL=http://127.0.0.1:9119
```

This avoids the separate-container SSH bridge that Workspace otherwise needs for terminal and Hermes CLI access.

## Config And State

Hermes data is bind-mounted:

```text
./services/hermes-workspace -> /opt/data
```

The project-owned MCP config is:

```text
services/hermes-workspace/config.yaml
```

It registers only `hermes_trader`, the project MCP.

Workspace's MCP Marketplace fallback reads local presets from:

```text
services/hermes-workspace/mcp-presets.json
```

The same catalog is also stored as a seed asset at:

```text
services/hermes-workspace/assets/mcp-presets.seed.json
```

Compose exposes that seed with:

```text
MCP_PRESETS_SEED_PATH=/opt/data/assets/mcp-presets.seed.json
```

This prevents the Workspace Marketplace warning `local-file: seed asset missing` and gives the UI a local `Hermes Trader` preset.

The Marketplace also queries the upstream `mcp-get` source, currently backed by Smithery. The bundled Workspace image is patched at build time by:

```text
services/hermes-workspace/patch-mcp-marketplace.js
```

That patch adapts Smithery's current catalog shape into installable HTTP MCP templates and requests a larger first page from the registry. Without it, the remote catalog can return data but still show only the local fallback because the upstream parser silently drops entries that do not include an explicit `url` or `command`.

## Private Environment

Hermes-only and Workspace-only secrets live in:

```text
services/hermes-workspace/.env
```

Create it from:

```bash
cp services/hermes-workspace/.env.example services/hermes-workspace/.env
```

This file is loaded only by the `hermes-workspace` service. Put `OPEN_AI_TOKEN`, provider keys, Slack tokens, and `HERMES_PASSWORD` here.

For direct OpenAI API access, keep this shape in `services/hermes-workspace/config.yaml`:

```yaml
model:
  provider: custom:openai-direct
  default: gpt-5.4-mini
  base_url: https://api.openai.com/v1
custom_providers:
- name: OpenAI Direct
  base_url: https://api.openai.com/v1
  key_env: OPEN_AI_TOKEN
  model: gpt-5.4-mini
```

Then provide `OPEN_AI_TOKEN` in `services/hermes-workspace/.env`. `OPENAI_API_KEY` also works as a fallback for this Hermes runtime.

## Platform Warnings

This warning means Hermes will reject messages from external users unless you configure access:

```text
No user allowlists configured
```

For local-only experiments, add this to `services/hermes-workspace/.env`:

```text
GATEWAY_ALLOW_ALL_USERS=true
```

If Slack or another external platform is connected, prefer platform-specific allowlists instead of open access.

This Slack warning means the app can connect, but cannot list private channels:

```text
missing_scope ... needed: groups:read
```

Fix it by adding the `groups:read` bot OAuth scope in Slack app settings and reinstalling the Slack app to the workspace. If you do not need Slack for this project, remove `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` from `services/hermes-workspace/.env` and restart `hermes-workspace`.

## Boundary

Hermes sees:

```text
trader-mcp
```

Hermes does not see direct Alpaca tools.
