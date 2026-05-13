create table if not exists market_snapshots (
  id bigserial primary key,
  symbol text not null,
  captured_at timestamptz not null default now(),
  timeframe text not null,
  open numeric,
  high numeric,
  low numeric,
  close numeric,
  volume numeric,
  raw jsonb not null default '{}'
);

create table if not exists feature_snapshots (
  id bigserial primary key,
  symbol text not null,
  market_snapshot_id bigint references market_snapshots(id),
  computed_at timestamptz not null default now(),
  features jsonb not null
);

create table if not exists inference_runs (
  id bigserial primary key,
  feature_snapshot_id bigint references feature_snapshots(id),
  model_name text not null,
  model_version text not null,
  predicted_action text not null,
  predicted_return numeric,
  confidence numeric,
  raw_output jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists agent_decisions (
  id bigserial primary key,
  inference_run_id bigint references inference_runs(id),
  symbol text not null,
  proposed_action text not null,
  proposed_qty numeric,
  rationale text,
  policy_status text not null,
  policy_reasons jsonb not null default '[]',
  final_action text not null,
  created_at timestamptz not null default now()
);

create table if not exists paper_orders (
  id bigserial primary key,
  decision_id bigint references agent_decisions(id),
  alpaca_order_id text unique,
  symbol text not null,
  side text not null,
  order_type text not null,
  qty numeric,
  notional numeric,
  status text,
  submitted_at timestamptz,
  filled_qty numeric,
  filled_at timestamptz,
  filled_avg_price numeric,
  expires_at timestamptz,
  expired_at timestamptz,
  canceled_at timestamptz,
  raw jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists trade_outcomes (
  id bigserial primary key,
  decision_id bigint references agent_decisions(id),
  horizon text not null,
  measured_at timestamptz not null default now(),
  entry_price numeric,
  exit_price numeric,
  return_pct numeric,
  pnl numeric,
  label integer,
  raw jsonb not null default '{}'
);

create table if not exists backtest_runs (
  id bigserial primary key,
  created_at timestamptz not null default now(),
  strategy text not null,
  symbols jsonb not null default '[]',
  days integer not null,
  initial_cash numeric not null,
  final_value numeric,
  pnl numeric,
  return_pct numeric,
  trade_count integer,
  raw jsonb not null default '{}'
);

create table if not exists portfolio_snapshots (
  id bigserial primary key,
  captured_at timestamptz not null default now(),
  cash numeric,
  equity numeric,
  buying_power numeric,
  raw jsonb not null default '{}'
);

create table if not exists position_snapshots (
  id bigserial primary key,
  captured_at timestamptz not null default now(),
  symbol text not null,
  qty numeric,
  market_value numeric,
  cost_basis numeric,
  unrealized_pl numeric,
  unrealized_plpc numeric,
  current_price numeric,
  raw jsonb not null default '{}'
);

create index if not exists market_snapshots_symbol_time_idx on market_snapshots(symbol, captured_at desc);
create index if not exists agent_decisions_symbol_time_idx on agent_decisions(symbol, created_at desc);
create index if not exists position_snapshots_symbol_time_idx on position_snapshots(symbol, captured_at desc);
