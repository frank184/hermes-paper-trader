# Environment Variables

The project uses two environment files with different scopes.

## Root `.env`

Use root `.env` for shared project settings and services that need Alpaca access.

Example source:

```text
.env.example
```

Used by:

- `trading-orchestrator`
- `jupyter`
- Docker Compose variable interpolation

Typical values:

```text
ALPACA_API_KEY
ALPACA_SECRET_KEY
ALPACA_PAPER_TRADE
HERMES_UID
HERMES_GID
JUPYTER_TOKEN
SYMBOL_ALLOWLIST
SYMBOL_ALLOWLIST_SEED
SYMBOL_DB_CONTROL_ENABLED
SYMBOL_REQUIRE_ENABLED
MAX_NOTIONAL_PER_TRADE
MAX_POSITION_NOTIONAL
MAX_DAILY_TRADES
MIN_CONFIDENCE_TO_TRADE
MIN_SHORT_CONFIDENCE
COOLDOWN_MINUTES
ALLOW_SHORTS
REQUIRE_TREND_ALIGNMENT
```

`SYMBOL_ALLOWLIST` is deprecated. Use `SYMBOL_ALLOWLIST_SEED` to seed Postgres on startup, then manage symbols through Trader MCP or the orchestrator `/symbols` endpoints. The database is the runtime source of truth when `SYMBOL_DB_CONTROL_ENABLED=true`.

Short selling is disabled by default with `ALLOW_SHORTS=false`. If enabled, `MIN_SHORT_CONFIDENCE` and `REQUIRE_TREND_ALIGNMENT` still guard new short positions.

## Hermes `.env`

Use `services/hermes-workspace/.env` for Hermes-only secrets.

Example source:

```text
services/hermes-workspace/.env.example
```

Used only by:

```text
hermes-workspace
```

Typical values:

```text
API_SERVER_KEY
HERMES_PASSWORD
GATEWAY_ALLOW_ALL_USERS
OPEN_AI_TOKEN
OPENAI_API_KEY
SLACK_BOT_TOKEN
SLACK_APP_TOKEN
```

This is where `OPEN_AI_TOKEN` belongs if Hermes needs it. It will not be passed to the orchestrator, inference API, Jupyter, or trader MCP.

For direct OpenAI API access, `services/hermes-workspace/config.yaml` defines a named custom provider, `custom:openai-direct`, with `base_url: https://api.openai.com/v1` and `key_env: OPEN_AI_TOKEN`. Hermes also falls back to `OPENAI_API_KEY` for custom providers, so either variable works in `services/hermes-workspace/.env`. Do not set `model.provider: openai`; this Hermes runtime does not recognize that provider id.

`HERMES_PASSWORD` protects the Workspace UI. The container defaults to `dev-hermes-workspace` if unset so local development starts cleanly, but use a real value for anything beyond local loopback testing.

Use dotenv syntax:

```text
API_SERVER_KEY=your-private-value
```

Do not use shell syntax:

```text
export API_SERVER_KEY=your-private-value
```

Docker Compose `env_file` does not pass `export ...` lines into the container.

## Hermes Platform Access

Hermes logs this warning when no platform allowlist is configured:

```text
No user allowlists configured
```

For local-only experiments, `GATEWAY_ALLOW_ALL_USERS=true` is convenient. If Slack or another external platform is connected, configure platform-specific allowlists instead.

Slack channel discovery may log:

```text
missing_scope ... needed: groups:read
```

That means Slack is connected, but the Slack app cannot list private channels. Add the `groups:read` bot OAuth scope and reinstall the app, or remove the Slack token variables if this project does not need Slack.

## Why Split Them?

The orchestrator needs Alpaca credentials to fetch market data and submit paper orders. Hermes and Workspace may need separate model/provider credentials and UI auth. Keeping those scopes separate prevents accidental secret exposure between containers.

```text
.env                  -> shared project/service settings
services/hermes-workspace/.env -> Hermes-only private secrets
```
