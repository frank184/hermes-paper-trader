from typing import Any

from psycopg.types.json import Jsonb

from app.config import Settings
from app.schema import ensure_runtime_schema


DEFAULT_UNIVERSE = "core"


def seed_symbols(conn: Any, settings: Settings) -> None:
    ensure_runtime_schema(conn)
    for symbol in sorted(settings.symbol_allowlist_seed):
        conn.execute(
            """
            insert into symbols (symbol, source, metadata)
            values (%s, 'env-seed', %s)
            on conflict (symbol) do update set
              metadata = symbols.metadata || excluded.metadata,
              updated_at = now()
            """,
            (symbol, Jsonb({"seeded_from_env": True})),
        )
        conn.execute(
            """
            insert into symbol_universe_members (symbol, universe)
            values (%s, %s)
            on conflict do nothing
            """,
            (symbol, DEFAULT_UNIVERSE),
        )


def enabled_symbols(conn: Any, settings: Settings, universe: str | None = None) -> list[str]:
    seed_symbols(conn, settings)
    if not settings.symbol_db_control_enabled:
        return sorted(settings.symbol_allowlist_seed)

    if universe:
        rows = conn.execute(
            """
            select s.symbol
            from symbols s
            join symbol_universe_members m on m.symbol = s.symbol
            where s.enabled is true and s.tradable is true and m.universe = %s
            order by s.symbol
            """,
            (universe,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            select symbol
            from symbols
            where enabled is true and tradable is true
            order by symbol
            """
        ).fetchall()
    symbols = [row["symbol"] for row in rows]
    if not symbols and not settings.symbol_require_enabled:
        return sorted(settings.symbol_allowlist_seed)
    return symbols


def symbol_is_enabled(conn: Any, settings: Settings, symbol: str) -> bool:
    if not settings.symbol_require_enabled:
        return True
    return symbol.upper() in set(enabled_symbols(conn, settings))


def upsert_symbol(
    conn: Any,
    symbol: str,
    *,
    name: str | None = None,
    asset_class: str | None = None,
    exchange: str | None = None,
    tradable: bool = True,
    enabled: bool = True,
    source: str = "manual",
    notes: str | None = None,
    metadata: dict[str, Any] | None = None,
    universes: list[str] | None = None,
) -> dict[str, Any]:
    ensure_runtime_schema(conn)
    symbol = symbol.upper()
    row = conn.execute(
        """
        insert into symbols
          (symbol, name, asset_class, exchange, tradable, enabled, source, notes, metadata)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (symbol) do update set
          name = coalesce(excluded.name, symbols.name),
          asset_class = coalesce(excluded.asset_class, symbols.asset_class),
          exchange = coalesce(excluded.exchange, symbols.exchange),
          tradable = excluded.tradable,
          enabled = excluded.enabled,
          source = excluded.source,
          notes = coalesce(excluded.notes, symbols.notes),
          metadata = symbols.metadata || excluded.metadata,
          updated_at = now()
        returning *
        """,
        (
            symbol,
            name,
            asset_class,
            exchange,
            tradable,
            enabled,
            source,
            notes,
            Jsonb(metadata or {}),
        ),
    ).fetchone()
    for universe in universes or [DEFAULT_UNIVERSE]:
        conn.execute(
            """
            insert into symbol_universe_members (symbol, universe)
            values (%s, %s)
            on conflict do nothing
            """,
            (symbol, universe),
        )
    return dict(row)

