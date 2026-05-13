from typing import Any


def ensure_runtime_schema(conn: Any) -> None:
    conn.execute("alter table agent_decisions add column if not exists strategy_name text")
    conn.execute("alter table agent_decisions add column if not exists intended_holding_period text")
    conn.execute(
        "alter table agent_decisions add column if not exists strategy_plan jsonb not null default '{}'"
    )
    conn.execute(
        """
        create table if not exists symbols (
          symbol text primary key,
          name text,
          asset_class text,
          exchange text,
          tradable boolean not null default true,
          enabled boolean not null default true,
          source text not null default 'manual',
          notes text,
          metadata jsonb not null default '{}',
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    conn.execute(
        """
        create table if not exists symbol_universe_members (
          symbol text not null references symbols(symbol) on delete cascade,
          universe text not null,
          created_at timestamptz not null default now(),
          primary key (symbol, universe)
        )
        """
    )
    conn.execute(
        """
        create table if not exists market_bars (
          id bigserial primary key,
          symbol text not null,
          timeframe text not null,
          timestamp timestamptz not null,
          open numeric,
          high numeric,
          low numeric,
          close numeric,
          volume numeric,
          raw jsonb not null default '{}',
          source text not null default 'alpaca',
          created_at timestamptz not null default now(),
          unique (symbol, timeframe, timestamp)
        )
        """
    )
    conn.execute(
        """
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
        )
        """
    )
    conn.execute(
        """
        create table if not exists backtest_trades (
          id bigserial primary key,
          backtest_run_id bigint references backtest_runs(id),
          decision_id bigint references agent_decisions(id),
          symbol text not null,
          strategy text not null,
          side text not null,
          entry_at timestamptz,
          exit_at timestamptz,
          entry_price numeric,
          exit_price numeric,
          qty numeric,
          pnl numeric,
          return_pct numeric,
          label integer,
          raw jsonb not null default '{}',
          created_at timestamptz not null default now()
        )
        """
    )
    conn.execute(
        "create index if not exists market_bars_symbol_time_idx on market_bars(symbol, timeframe, timestamp desc)"
    )
    conn.execute("create index if not exists symbols_enabled_idx on symbols(enabled, tradable)")
    conn.execute("create index if not exists backtest_trades_symbol_idx on backtest_trades(symbol, entry_at desc)")
