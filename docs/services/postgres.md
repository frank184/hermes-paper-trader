# Postgres

Postgres stores the audit trail and experiment data.

## Compose Service

```text
postgres
```

Local port:

```text
5432
```

Default database:

```text
hermes_trader
```

## Schema

Initialized from:

```text
db/init/001_schema.sql
```

Core tables:

- `market_snapshots`
- `feature_snapshots`
- `inference_runs`
- `agent_decisions`
- `paper_orders`
- `trade_outcomes`
- `portfolio_snapshots`

## Role In The System

The database turns each trading tick into training/evaluation data.

```text
market snapshot -> features -> prediction -> decision -> order/outcome
```

## Notes

The schema is intentionally simple. Add read-only debug endpoints before adding complex analysis tables.
