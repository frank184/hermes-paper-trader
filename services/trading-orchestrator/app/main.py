from datetime import UTC, datetime
from decimal import Decimal
import json
from os import getenv
from pathlib import Path
from random import random
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from psycopg.types.json import Jsonb

from app.alpaca_client import AlpacaPaperClient
from app.config import get_settings
from app.db import connect
from app.features import compute_features
from app.inference_client import predict
from app.models import (
    BacktestRequest,
    BacktestSweepRequest,
    ChartRequest,
    DecisionRequest,
    DiscoveryRequest,
    MarketBarsRequest,
    Prediction,
    SymbolImportRequest,
    SymbolPatchRequest,
    SymbolRequest,
    TickRequest,
)
from app.policy import evaluate_policy, evaluate_symbol_precheck
from app.schema import ensure_runtime_schema
from app.sizing import size_order
from app.universe import enabled_symbols, seed_symbols, symbol_is_enabled, upsert_symbol

app = FastAPI(title="Hermes Trading Orchestrator", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    settings = get_settings()
    with connect() as conn:
        ensure_runtime_schema(conn)
        seed_symbols(conn, settings)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/portfolio/state")
def portfolio_state() -> dict[str, Any]:
    client = AlpacaPaperClient(get_settings())
    account = client.get_account()
    with connect() as conn:
        conn.execute(
            """
            insert into portfolio_snapshots (cash, equity, buying_power, raw)
            values (%s, %s, %s, %s)
            """,
            (
                account.get("cash"),
                account.get("equity"),
                account.get("buying_power"),
                Jsonb(account),
            ),
        )
    return account


@app.get("/portfolio/positions")
def portfolio_positions() -> dict[str, Any]:
    client = AlpacaPaperClient(get_settings())
    positions = client.get_positions()
    with connect() as conn:
        _ensure_position_snapshots_table(conn)
        for position in positions:
            conn.execute(
                """
                insert into position_snapshots
                  (symbol, qty, market_value, cost_basis, unrealized_pl, unrealized_plpc, current_price, raw)
                values (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    position.get("symbol"),
                    position.get("qty"),
                    position.get("market_value"),
                    position.get("cost_basis"),
                    position.get("unrealized_pl"),
                    position.get("unrealized_plpc"),
                    position.get("current_price"),
                    Jsonb(position),
                ),
            )
    return {
        "count": len(positions),
        "symbols": [position.get("symbol") for position in positions],
        "positions": positions,
    }


@app.get("/orders")
def orders(
    status: str = Query(default="open", pattern="^(open|closed|all)$"),
    limit: int = Query(default=50, ge=1, le=500),
    symbols: str | None = Query(default=None),
    side: str | None = Query(default=None, pattern="^(buy|sell)$"),
) -> dict[str, Any]:
    client = AlpacaPaperClient(get_settings())
    symbol_list = _parse_symbol_filter(symbols)
    orders = client.get_orders(status=status, limit=limit, symbols=symbol_list, side=side)
    with connect() as conn:
        _ensure_paper_orders_runtime_schema(conn)
        _sync_orders(conn, orders)
    return {
        "count": len(orders),
        "status": status,
        "symbols": symbol_list or [],
        "orders": orders,
    }


@app.get("/orders/{order_id}")
def order(order_id: str) -> dict[str, Any]:
    client = AlpacaPaperClient(get_settings())
    order = client.get_order(order_id)
    with connect() as conn:
        _ensure_paper_orders_runtime_schema(conn)
        _sync_orders(conn, [order])
    return order


@app.delete("/orders/{order_id}")
def cancel_order(order_id: str) -> dict[str, Any]:
    client = AlpacaPaperClient(get_settings())
    result = client.cancel_order(order_id)
    refreshed = None
    try:
        refreshed = client.get_order(order_id)
    except Exception:
        refreshed = None
    if refreshed:
        with connect() as conn:
            _ensure_paper_orders_runtime_schema(conn)
            _sync_orders(conn, [refreshed])
    return {"cancel": result, "order": refreshed}


@app.get("/market/clock")
def market_clock() -> dict[str, Any]:
    client = AlpacaPaperClient(get_settings())
    return client.get_clock()


@app.get("/symbols")
def list_symbols(
    enabled: bool | None = Query(default=None),
    universe: str | None = Query(default=None),
) -> dict[str, Any]:
    settings = get_settings()
    with connect() as conn:
        seed_symbols(conn, settings)
        params: list[Any] = []
        where = []
        joins = ""
        if universe:
            joins = "join symbol_universe_members m on m.symbol = s.symbol"
            where.append("m.universe = %s")
            params.append(universe)
        if enabled is not None:
            where.append("s.enabled is %s" % ("true" if enabled else "false"))
        where_sql = f"where {' and '.join(where)}" if where else ""
        rows = conn.execute(
            f"""
            select s.*
            from symbols s
            {joins}
            {where_sql}
            order by s.symbol
            """,
            params,
        ).fetchall()
    return {"count": len(rows), "symbols": [dict(row) for row in rows]}


@app.post("/symbols")
def add_symbol(request: SymbolRequest) -> dict[str, Any]:
    settings = get_settings()
    asset = None
    if request.validate_with_alpaca:
        try:
            asset = AlpacaPaperClient(settings).get_asset(request.symbol)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Alpaca asset validation failed: {exc}") from exc
    metadata = {"alpaca_asset": asset} if asset else {}
    with connect() as conn:
        row = upsert_symbol(
            conn,
            request.symbol,
            name=request.name or (asset or {}).get("name"),
            asset_class=request.asset_class or (asset or {}).get("asset_class"),
            exchange=request.exchange or (asset or {}).get("exchange"),
            tradable=bool((asset or {}).get("tradable", True)),
            enabled=request.enabled,
            source="manual",
            notes=request.notes,
            metadata=metadata,
            universes=request.universes,
        )
    return {"symbol": row}


@app.patch("/symbols/{symbol}")
def patch_symbol(symbol: str, request: SymbolPatchRequest) -> dict[str, Any]:
    settings = get_settings()
    with connect() as conn:
        seed_symbols(conn, settings)
        values = {
            "enabled": request.enabled,
            "notes": request.notes,
        }
        row = conn.execute(
            """
            update symbols
            set
              enabled = coalesce(%s, enabled),
              notes = coalesce(%s, notes),
              updated_at = now()
            where symbol = %s
            returning *
            """,
            (values["enabled"], values["notes"], symbol.upper()),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"{symbol.upper()} is not in symbols")
        if request.universes is not None:
            conn.execute("delete from symbol_universe_members where symbol = %s", (symbol.upper(),))
            for universe in request.universes:
                conn.execute(
                    """
                    insert into symbol_universe_members (symbol, universe)
                    values (%s, %s)
                    on conflict do nothing
                    """,
                    (symbol.upper(), universe),
                )
    return {"symbol": dict(row)}


@app.post("/symbols/import")
def import_symbols(request: SymbolImportRequest) -> dict[str, Any]:
    imported = []
    rejected = []
    settings = get_settings()
    client = AlpacaPaperClient(settings) if request.validate_with_alpaca else None
    with connect() as conn:
        seed_symbols(conn, settings)
        for raw_symbol in request.symbols:
            symbol = raw_symbol.strip().upper()
            if not symbol:
                continue
            asset = None
            try:
                if client:
                    asset = client.get_asset(symbol)
                imported.append(
                    upsert_symbol(
                        conn,
                        symbol,
                        name=(asset or {}).get("name"),
                        asset_class=(asset or {}).get("asset_class"),
                        exchange=(asset or {}).get("exchange"),
                        tradable=bool((asset or {}).get("tradable", True)),
                        enabled=request.enabled,
                        source="import",
                        metadata={"alpaca_asset": asset} if asset else {},
                        universes=[request.universe],
                    )
                )
            except Exception as exc:
                rejected.append({"symbol": symbol, "reason": str(exc)})
    return {"imported_count": len(imported), "rejected_count": len(rejected), "symbols": imported, "rejected": rejected}


@app.post("/market/bars")
def market_bars(request: MarketBarsRequest) -> dict[str, Any]:
    settings = get_settings()
    client = AlpacaPaperClient(settings)
    result = {"timeframe": request.timeframe, "persist": request.persist, "symbols": {}, "rows": 0}
    for symbol in _normalize_symbols(request.symbols):
        bars = client.historical_bars(
            symbol,
            timeframe=request.timeframe,
            days=request.days,
            limit=request.limit,
        )
        if request.persist:
            with connect() as conn:
                _persist_market_bars(conn, bars)
        result["symbols"][symbol] = {"count": len(bars), "bars": bars}
        result["rows"] += len(bars)
    return result


@app.post("/ticks/run")
async def run_tick(request: TickRequest) -> dict[str, Any]:
    discovery = None
    symbols = _normalize_symbols(request.symbols)
    if not symbols and request.discover_if_empty:
        discovery = await _discover_candidates(
            DiscoveryRequest(
                max_symbols=request.max_symbols,
                strategy=request.discovery_strategy,
                qty=request.qty,
                auto_size=request.auto_size,
            )
        )
        symbols = [candidate["symbol"] for candidate in discovery["candidates"]]

    results = []
    for symbol in symbols:
        try:
            results.append(
                await propose_decision(
                    DecisionRequest(
                        symbol=symbol,
                        qty=request.qty,
                        dry_run=request.dry_run,
                        auto_size=request.auto_size,
                        override_action=request.override_action,
                        override_confidence=request.override_confidence,
                        override_predicted_return=request.override_predicted_return,
                    )
                )
            )
        except HTTPException as exc:
            results.append(_rejected_symbol_result(symbol, request.dry_run, [str(exc.detail)]))
        except Exception as exc:
            results.append(_rejected_symbol_result(symbol, request.dry_run, [str(exc)]))
    return {"discovery": discovery, "results": results}


@app.post("/symbols/discover")
async def discover_symbols(request: DiscoveryRequest) -> dict[str, Any]:
    return await _discover_candidates(request)


@app.post("/symbols/scan")
async def scan_symbols(request: DiscoveryRequest) -> dict[str, Any]:
    return await _discover_candidates(request)


@app.post("/backtests/run")
async def run_backtest(request: BacktestRequest) -> dict[str, Any]:
    settings = get_settings()
    with connect() as conn:
        symbols = _normalize_symbols(request.symbols) or enabled_symbols(conn, settings, request.universe)
    client = AlpacaPaperClient(settings)
    summary = {
        "strategy": request.strategy,
        "symbols": symbols,
        "days": request.days,
        "horizon_days": request.horizon_days,
        "label_threshold": request.label_threshold,
        "persist": request.persist,
        "rows_created": 0,
        "symbols_processed": [],
        "rejected": [],
    }
    total_pnl = 0.0
    total_trade_count = 0
    run_id = None

    if request.persist:
        with connect() as conn:
            _ensure_backtest_runs_table(conn)
            _ensure_backtest_trades_table(conn)
            run_id = conn.execute(
                """
                insert into backtest_runs
                  (strategy, symbols, days, initial_cash, raw)
                values (%s, %s, %s, %s, %s)
                returning id
                """,
                (
                    request.strategy,
                    Jsonb(symbols),
                    request.days,
                    request.initial_cash,
                    Jsonb({"status": "running", **summary}),
                ),
            ).fetchone()["id"]

    for symbol in symbols:
        bars = client.historical_daily_bars(symbol, request.days)
        if request.persist:
            with connect() as conn:
                _persist_market_bars(conn, bars)
        if len(bars) < 25 + request.horizon_days:
            summary["rejected"].append(
                {"symbol": symbol, "reason": "not enough historical bars", "bars": len(bars)}
            )
            continue

        symbol_result = await _backtest_symbol(settings, request, symbol, bars, run_id)
        summary["rows_created"] += symbol_result["rows_created"]
        total_pnl += float(symbol_result["pnl"])
        total_trade_count += int(symbol_result["trade_count"])
        summary["symbols_processed"].append(symbol_result)

    final_value = request.initial_cash + total_pnl
    pnl = final_value - request.initial_cash
    summary["trade_count"] = total_trade_count
    summary["final_value"] = final_value
    summary["pnl"] = pnl
    summary["return_pct"] = pnl / request.initial_cash if request.initial_cash else 0.0

    if request.persist and run_id is not None:
        with connect() as conn:
            conn.execute(
                """
                update backtest_runs
                set final_value = %s,
                    pnl = %s,
                    return_pct = %s,
                    trade_count = %s,
                    raw = %s
                where id = %s
                """,
                (
                    final_value,
                    pnl,
                    summary["return_pct"],
                    summary["trade_count"],
                    Jsonb(summary),
                    run_id,
                ),
            )
        summary["backtest_run_id"] = run_id

    return summary


@app.post("/backtests/sweep")
async def run_backtest_sweep(request: BacktestSweepRequest) -> dict[str, Any]:
    runs = []
    for strategy in request.strategies:
        for horizon in request.horizons:
            for threshold in request.label_thresholds:
                runs.append(
                    await run_backtest(
                        BacktestRequest(
                            symbols=request.symbols,
                            universe=request.universe,
                            days=request.days,
                            horizon_days=horizon,
                            label_threshold=threshold,
                            initial_cash=request.initial_cash,
                            strategy=strategy if strategy in {"inference", "moving_average", "trend_following", "breakout"} else "trend_following",
                            persist=request.persist,
                        )
                    )
                )
    runs.sort(key=lambda item: float(item.get("return_pct", 0.0)), reverse=True)
    return {"count": len(runs), "runs": runs}


@app.post("/charts/candles")
def chart_candles(request: ChartRequest) -> dict[str, Any]:
    bars_response = market_bars(
        MarketBarsRequest(
            symbols=[request.symbol],
            timeframe=request.timeframe,
            days=request.days,
            persist=request.persist,
        )
    )
    bars = bars_response["symbols"].get(request.symbol.upper(), {}).get("bars", [])
    chart = {
        "type": "candles",
        "symbol": request.symbol.upper(),
        "timeframe": request.timeframe,
        "bars": bars,
        "summary": _bar_summary(bars),
    }
    artifact_path = _write_artifact("candles", request.symbol.upper(), chart)
    return {**chart, "artifact_path": artifact_path}


@app.post("/charts/equity-curve")
def chart_equity_curve(backtest_run_id: int | None = None) -> dict[str, Any]:
    with connect() as conn:
        if backtest_run_id:
            rows = conn.execute(
                """
                select *
                from backtest_trades
                where backtest_run_id = %s
                order by entry_at asc
                """,
                (backtest_run_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                select *
                from backtest_trades
                order by entry_at asc
                limit 1000
                """
            ).fetchall()
    points = []
    equity = 0.0
    for row in rows:
        equity += float(row.get("pnl") or 0.0)
        points.append({"timestamp": row.get("exit_at"), "equity": equity, "symbol": row.get("symbol")})
    chart = {"type": "equity_curve", "backtest_run_id": backtest_run_id, "points": points}
    artifact_path = _write_artifact("equity-curve", str(backtest_run_id or "latest"), chart)
    return {**chart, "artifact_path": artifact_path}


@app.post("/reports/symbol")
def symbol_report(request: ChartRequest) -> dict[str, Any]:
    bars = chart_candles(request)
    features = compute_features(
        {
            **bars["bars"][-1],
            "history": bars["bars"][-30:],
            "daily_history": bars["bars"],
        }
    ) if bars["bars"] else {}
    with connect() as conn:
        decisions = conn.execute(
            """
            select *
            from agent_decisions
            where symbol = %s
            order by created_at desc
            limit 20
            """,
            (request.symbol.upper(),),
        ).fetchall()
    report = {
        "symbol": request.symbol.upper(),
        "bar_summary": bars["summary"],
        "features": features,
        "recent_decisions": [dict(row) for row in decisions],
        "chart_artifact_path": bars["artifact_path"],
    }
    artifact_path = _write_artifact("symbol-report", request.symbol.upper(), report)
    return {**report, "artifact_path": artifact_path}


@app.post("/reports/portfolio")
def portfolio_report() -> dict[str, Any]:
    account = portfolio_state()
    positions = portfolio_positions()
    orders_snapshot = orders(status="open", limit=50, symbols=None, side=None)
    report = {
        "account": account,
        "positions": positions,
        "open_orders": orders_snapshot,
    }
    artifact_path = _write_artifact("portfolio-report", "latest", report)
    return {**report, "artifact_path": artifact_path}


@app.post("/decisions/propose")
async def propose_decision(request: DecisionRequest) -> dict[str, Any]:
    settings = get_settings()
    symbol = request.symbol.upper()

    with connect() as conn:
        enabled = symbol_is_enabled(conn, settings, symbol)
    if not enabled:
        return _rejected_symbol_result(symbol, request.dry_run, [f"{symbol} is not enabled"])

    try:
        client = AlpacaPaperClient(settings)
        bar = client.latest_bar(symbol)
        position = _position_for_symbol(client, symbol)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    features = compute_features(bar, position)
    prediction = await predict(settings.inference_api_url, symbol, features)
    prediction = _apply_prediction_override(settings, prediction, request)
    sizing = size_order(settings, request.qty, float(bar["close"]), request.auto_size)
    effective_qty = float(sizing["effective_qty"])
    policy = evaluate_policy(
        settings,
        prediction,
        effective_qty,
        float(bar["close"]),
        symbol_enabled=enabled,
        features=features,
        position_qty=float(features.get("position_qty", 0.0)),
    )

    with connect() as conn:
        _persist_market_bars(conn, [*_history_to_bars(symbol, "1Min", bar.get("history", [])), *bar.get("daily_history", [])])
        market_id = conn.execute(
            """
            insert into market_snapshots (symbol, timeframe, open, high, low, close, volume, raw)
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            returning id
            """,
            (
                symbol,
                bar["timeframe"],
                bar["open"],
                bar["high"],
                bar["low"],
                bar["close"],
                bar["volume"],
                Jsonb(bar["raw"]),
            ),
        ).fetchone()["id"]
        feature_id = conn.execute(
            """
            insert into feature_snapshots (symbol, market_snapshot_id, features)
            values (%s, %s, %s)
            returning id
            """,
            (symbol, market_id, Jsonb(features)),
        ).fetchone()["id"]
        inference_id = conn.execute(
            """
            insert into inference_runs
              (feature_snapshot_id, model_name, model_version, predicted_action, predicted_return, confidence, raw_output)
            values (%s, %s, %s, %s, %s, %s, %s)
            returning id
            """,
            (
                feature_id,
                prediction.model_name,
                prediction.model_version,
                prediction.predicted_action,
                prediction.predicted_return,
                prediction.confidence,
                Jsonb(prediction.raw_output),
            ),
        ).fetchone()["id"]
        decision_id = conn.execute(
            """
            insert into agent_decisions
              (inference_run_id, symbol, proposed_action, proposed_qty, rationale, policy_status, policy_reasons, final_action)
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            returning id
            """,
            (
                inference_id,
                symbol,
                prediction.predicted_action,
                effective_qty,
                _decision_rationale(request.qty, sizing),
                policy.status,
                Jsonb(policy.reasons),
                policy.final_action,
            ),
        ).fetchone()["id"]

    order = None
    if policy.status == "approved" and not request.dry_run:
        order = client.submit_market_order(symbol, policy.final_action, Decimal(str(effective_qty)))
        with connect() as conn:
            _ensure_paper_orders_runtime_schema(conn)
            conn.execute(
                """
                insert into paper_orders
                  (decision_id, alpaca_order_id, symbol, side, order_type, qty, notional, status, submitted_at,
                   filled_at, filled_avg_price, filled_qty, expires_at, expired_at, canceled_at, raw)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (alpaca_order_id) do update set
                  decision_id = coalesce(paper_orders.decision_id, excluded.decision_id),
                  symbol = excluded.symbol,
                  side = excluded.side,
                  order_type = excluded.order_type,
                  qty = excluded.qty,
                  notional = excluded.notional,
                  status = excluded.status,
                  submitted_at = excluded.submitted_at,
                  filled_at = excluded.filled_at,
                  filled_avg_price = excluded.filled_avg_price,
                  filled_qty = excluded.filled_qty,
                  expires_at = excluded.expires_at,
                  expired_at = excluded.expired_at,
                  canceled_at = excluded.canceled_at,
                  raw = excluded.raw
                """,
                (
                    decision_id,
                    order.get("id"),
                    symbol,
                    policy.final_action,
                    order.get("type", "market"),
                    effective_qty,
                    sizing["effective_notional"],
                    order.get("status"),
                    order.get("submitted_at"),
                    order.get("filled_at"),
                    order.get("filled_avg_price"),
                    order.get("filled_qty"),
                    order.get("expires_at"),
                    order.get("expired_at"),
                    order.get("canceled_at"),
                    Jsonb(order),
                ),
            )

    return {
        "decision_id": decision_id,
        "symbol": symbol,
        "dry_run": request.dry_run,
        "features": features,
        "prediction": prediction.model_dump(),
        "sizing": sizing,
        "policy": policy.model_dump(),
        "order": order,
    }


async def _discover_candidates(request: DiscoveryRequest) -> dict[str, Any]:
    settings = get_settings()
    client = AlpacaPaperClient(settings)
    candidates = []
    rejected = []

    with connect() as conn:
        symbols = enabled_symbols(conn, settings, request.universe)

    for symbol in symbols:
        try:
            bar = client.latest_bar(symbol)
            position = _position_for_symbol(client, symbol)
        except Exception as exc:
            rejected.append({"symbol": symbol, "eligible": False, "reasons": [str(exc)]})
            continue

        features = compute_features(bar, position)
        latest_price = float(bar["close"])
        sizing = size_order(settings, request.qty, latest_price, request.auto_size)
        with connect() as conn:
            _persist_market_bars(conn, [*bar.get("daily_history", []), *_history_to_bars(symbol, "1Min", bar.get("history", []))])
            enabled = symbol_is_enabled(conn, settings, symbol)
        reasons = evaluate_symbol_precheck(
            settings,
            symbol,
            float(sizing["effective_qty"]),
            latest_price,
            symbol_enabled=enabled,
        )
        hard_reasons = [
            reason
            for reason in reasons
            if reason not in {"daily trade limit reached", "symbol cooldown is active"}
        ]
        score = _candidate_score(request.strategy, features)
        candidate = {
            "symbol": symbol,
            "eligible": not hard_reasons,
            "score": score,
            "strategy": request.strategy,
            "reason": _candidate_reason(request.strategy, features, sizing),
            "features": features,
            "sizing": sizing,
            "reasons": hard_reasons,
            "policy_limit_reasons": [reason for reason in reasons if reason not in hard_reasons],
        }
        if hard_reasons:
            rejected.append(candidate)
        else:
            candidates.append(candidate)

    candidates.sort(key=lambda item: item["score"], reverse=True)
    rejected.sort(key=lambda item: item.get("symbol", ""))
    return {
        "strategy": request.strategy,
        "max_symbols": request.max_symbols,
        "candidates": candidates[: request.max_symbols],
        "rejected": rejected,
    }


async def _backtest_symbol(
    settings: Any,
    request: BacktestRequest,
    symbol: str,
    bars: list[dict[str, Any]],
    backtest_run_id: int | None,
) -> dict[str, Any]:
    rows_created = 0
    trades = []
    start_index = 20
    end_index = len(bars) - request.horizon_days

    with connect() as conn:
        if request.persist:
            _ensure_backtest_runs_table(conn)

        for index in range(start_index, end_index):
            bar = dict(bars[index])
            bar["daily_history"] = bars[max(0, index - 260) : index + 1]
            bar["history"] = [
                {
                    "close": item["close"],
                    "volume": item["volume"],
                    "timestamp": item["timestamp"],
                }
                for item in bars[max(0, index - 30) : index + 1]
            ]
            future_bar = bars[index + request.horizon_days]
            features = compute_features(bar)
            prediction = await _backtest_prediction(settings, request, symbol, features)
            sizing = size_order(settings, request.qty, float(bar["close"]), request.auto_size)
            effective_qty = float(sizing["effective_qty"])
            future_return = (float(future_bar["close"]) / float(bar["close"])) - 1.0
            label = 1 if future_return > request.label_threshold else 0
            pnl = _backtest_pnl(
                prediction.predicted_action,
                effective_qty,
                float(bar["close"]),
                float(future_bar["close"]),
            )
            trade = {
                "symbol": symbol,
                "timestamp": bar["timestamp"],
                "future_timestamp": future_bar["timestamp"],
                "action": prediction.predicted_action,
                "entry_price": bar["close"],
                "exit_price": future_bar["close"],
                "future_return": future_return,
                "label": label,
                "qty": effective_qty,
                "pnl": pnl,
            }

            if request.persist:
                market_id = conn.execute(
                    """
                    insert into market_snapshots (symbol, captured_at, timeframe, open, high, low, close, volume, raw)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    returning id
                    """,
                    (
                        symbol,
                        bar["timestamp"],
                        bar["timeframe"],
                        bar["open"],
                        bar["high"],
                        bar["low"],
                        bar["close"],
                        bar["volume"],
                        Jsonb(bar["raw"]),
                    ),
                ).fetchone()["id"]
                feature_id = conn.execute(
                    """
                    insert into feature_snapshots (symbol, market_snapshot_id, computed_at, features)
                    values (%s, %s, %s, %s)
                    returning id
                    """,
                    (symbol, market_id, bar["timestamp"], Jsonb(features)),
                ).fetchone()["id"]
                inference_id = conn.execute(
                    """
                    insert into inference_runs
                      (feature_snapshot_id, model_name, model_version, predicted_action, predicted_return,
                       confidence, raw_output, created_at)
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    returning id
                    """,
                    (
                        feature_id,
                        prediction.model_name,
                        prediction.model_version,
                        prediction.predicted_action,
                        prediction.predicted_return,
                        prediction.confidence,
                        Jsonb(prediction.raw_output),
                        bar["timestamp"],
                    ),
                ).fetchone()["id"]
                decision_id = conn.execute(
                    """
                    insert into agent_decisions
                      (inference_run_id, symbol, proposed_action, proposed_qty, rationale,
                       policy_status, policy_reasons, final_action, created_at)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    returning id
                    """,
                    (
                        inference_id,
                        symbol,
                        prediction.predicted_action,
                        effective_qty,
                        f"historical backtest seed using {request.strategy}",
                        "backtest",
                        Jsonb([]),
                        prediction.predicted_action,
                        bar["timestamp"],
                    ),
                ).fetchone()["id"]
                conn.execute(
                    """
                    insert into trade_outcomes
                      (decision_id, horizon, measured_at, entry_price, exit_price, return_pct, pnl, label, raw)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        decision_id,
                        f"{request.horizon_days}d",
                        future_bar["timestamp"],
                        bar["close"],
                        future_bar["close"],
                        future_return,
                        pnl,
                        label,
                        Jsonb(trade),
                    ),
                )
                conn.execute(
                    """
                    insert into backtest_trades
                      (backtest_run_id, decision_id, symbol, strategy, side, entry_at, exit_at,
                       entry_price, exit_price, qty, pnl, return_pct, label, raw)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        backtest_run_id,
                        decision_id,
                        symbol,
                        request.strategy,
                        prediction.predicted_action,
                        bar["timestamp"],
                        future_bar["timestamp"],
                        bar["close"],
                        future_bar["close"],
                        effective_qty,
                        pnl,
                        future_return,
                        label,
                        Jsonb(trade),
                    ),
                )
                rows_created += 1
            trades.append(trade)

    wins = [trade for trade in trades if float(trade["pnl"]) > 0]
    losses = [trade for trade in trades if float(trade["pnl"]) < 0]
    equity = _equity_curve(trades)
    return {
        "symbol": symbol,
        "bars": len(bars),
        "rows_created": rows_created,
        "trade_count": len(trades),
        "positive_labels": sum(1 for trade in trades if trade["label"] == 1),
        "negative_labels": sum(1 for trade in trades if trade["label"] == 0),
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "average_win": sum(float(trade["pnl"]) for trade in wins) / len(wins) if wins else 0.0,
        "average_loss": sum(float(trade["pnl"]) for trade in losses) / len(losses) if losses else 0.0,
        "max_drawdown": _max_drawdown(equity),
        "pnl": sum(float(trade["pnl"]) for trade in trades),
        "trades": trades[-5:],
    }


async def _backtest_prediction(
    settings: Any,
    request: BacktestRequest,
    symbol: str,
    features: dict[str, Any],
) -> Prediction:
    if request.strategy == "inference":
        return await predict(settings.inference_api_url, symbol, features)

    probability_up = _strategy_probability(request.strategy, features)
    if probability_up > 0.55:
        action = "buy"
    elif probability_up < 0.45:
        action = "sell"
    else:
        action = "hold"
    return Prediction(
        symbol=symbol,
        predicted_action=action,
        predicted_return=float(features.get("returns_5", 0.0)),
        confidence=max(probability_up, 1.0 - probability_up),
        model_name="backtest-seed",
        model_version=f"{request.strategy}-v1",
        raw_output={
            "probability_up": probability_up,
            "strategy": request.strategy,
            "source": "historical backtest seed",
        },
    )


def _strategy_probability(strategy: str, features: dict[str, Any]) -> float:
    if strategy in {"trend_following", "breakout"}:
        return _trend_probability(features)
    return _moving_average_probability(features)


def _moving_average_probability(features: dict[str, Any]) -> float:
    score = (
        float(features.get("returns_5", 0.0)) * 4.0
        + float(features.get("moving_average_distance_20", 0.0)) * 3.0
        - abs(float(features.get("volatility_20", 0.0)))
    )
    return max(0.05, min(0.95, 0.5 + score))


def _trend_probability(features: dict[str, Any]) -> float:
    score = (
        float(features.get("daily_returns_20", 0.0)) * 1.5
        + float(features.get("daily_returns_60", 0.0)) * 1.2
        + float(features.get("sma_distance_20", 0.0)) * 1.5
        + float(features.get("sma_distance_50", 0.0))
        + float(features.get("trend_regime", 0.0)) * 0.06
        - abs(float(features.get("volatility_20", 0.0))) * 0.5
        - min(abs(float(features.get("drawdown_from_52w_high", 0.0))), 0.25) * 0.2
    )
    return max(0.05, min(0.95, 0.5 + score))


def _backtest_pnl(action: str, qty: float, entry_price: float, exit_price: float) -> float:
    if action == "buy":
        return (exit_price - entry_price) * qty
    if action == "sell":
        return (entry_price - exit_price) * qty
    return 0.0


def _equity_curve(trades: list[dict[str, Any]]) -> list[float]:
    equity = 0.0
    curve = []
    for trade in trades:
        equity += float(trade.get("pnl") or 0.0)
        curve.append(equity)
    return curve


def _max_drawdown(curve: list[float]) -> float:
    peak = 0.0
    max_drawdown = 0.0
    for value in curve:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value - peak)
    return max_drawdown


def _candidate_score(strategy: str, features: dict[str, Any]) -> float:
    if strategy == "liquidity":
        return float(features.get("volume", 0.0))
    if strategy in {"momentum", "trend_following"}:
        return (
            float(features.get("daily_returns_20", 0.0)) * 2.0
            + float(features.get("daily_returns_60", 0.0)) * 1.5
            + float(features.get("sma_distance_20", 0.0)) * 1.5
            + float(features.get("trend_regime", 0.0)) * 0.2
            - abs(float(features.get("volatility_20", 0.0)))
        )
    if strategy == "breakout":
        return (
            float(features.get("daily_returns_20", 0.0)) * 2.0
            + (1.0 + float(features.get("drawdown_from_52w_high", 0.0)))
            + max(float(features.get("volume_zscore_20", 0.0)), 0.0) * 0.1
        )
    if strategy == "mean_reversion_watch":
        return (
            abs(float(features.get("drawdown_from_52w_high", 0.0)))
            - abs(float(features.get("sma_distance_50", 0.0)))
            + max(float(features.get("trend_regime", 0.0)), 0.0) * 0.1
        )
    return random()


def _candidate_reason(strategy: str, features: dict[str, Any], sizing: dict[str, Any]) -> str:
    qty = sizing["effective_qty"]
    notional = sizing["effective_notional"]
    if strategy == "liquidity":
        return f"ranked by latest minute volume; sized qty {qty} uses about ${notional:.2f}"
    if strategy in {"momentum", "trend_following"}:
        return f"ranked by multi-week trend and moving-average alignment; sized qty {qty} uses about ${notional:.2f}"
    if strategy == "breakout":
        return f"ranked by proximity to recent highs plus volume; sized qty {qty} uses about ${notional:.2f}"
    if strategy == "mean_reversion_watch":
        return f"ranked as a pullback watch candidate; sized qty {qty} uses about ${notional:.2f}"
    return f"random baseline from eligible symbol database; sized qty {qty} uses about ${notional:.2f}"


def _decision_rationale(requested_qty: float, sizing: dict[str, Any]) -> str:
    if sizing["adjusted"]:
        return (
            "v0 uses inference output directly; "
            f"requested qty {requested_qty} was auto-sized to {sizing['effective_qty']} "
            "to stay under max notional per trade."
        )
    return "v0 uses inference output directly; Hermes narration can be added above this API."


def _apply_prediction_override(settings: Any, prediction: Any, request: DecisionRequest) -> Any:
    if not request.override_action:
        return prediction
    if not settings.allow_inference_override:
        return prediction

    confidence = (
        request.override_confidence
        if request.override_confidence is not None
        else max(settings.min_confidence_to_trade, prediction.confidence)
    )
    predicted_return = (
        request.override_predicted_return
        if request.override_predicted_return is not None
        else prediction.predicted_return
    )
    raw_output = dict(prediction.raw_output)
    raw_output["override"] = {
        "enabled": True,
        "original_action": prediction.predicted_action,
        "original_confidence": prediction.confidence,
        "requested_action": request.override_action,
        "requested_confidence": confidence,
    }
    return prediction.model_copy(
        update={
            "predicted_action": request.override_action,
            "confidence": confidence,
            "predicted_return": predicted_return,
            "model_name": "manual-override",
            "model_version": "dev-paper-override-v0",
            "raw_output": raw_output,
        }
    )


def _normalize_symbols(symbols: list[str]) -> list[str]:
    normalized = [symbol.strip().upper() for symbol in symbols if symbol and symbol.strip()]
    discovery_aliases = {"ALL", "ALLOWLIST", "CANDIDATES", "DISCOVER", "DISCOVERED"}
    if any(symbol in discovery_aliases for symbol in normalized):
        return []
    return normalized


def _parse_symbol_filter(symbols: str | None) -> list[str] | None:
    if not symbols:
        return None
    parsed = [symbol.strip().upper() for symbol in symbols.split(",") if symbol.strip()]
    return parsed or None


def _rejected_symbol_result(symbol: str, dry_run: bool, reasons: list[str]) -> dict[str, Any]:
    return {
        "decision_id": None,
        "symbol": symbol.upper(),
        "dry_run": dry_run,
        "features": {},
        "prediction": None,
        "sizing": None,
        "policy": {
            "status": "rejected",
            "reasons": reasons,
            "final_action": "hold",
        },
        "order": None,
    }


def _position_for_symbol(client: AlpacaPaperClient, symbol: str) -> dict[str, Any] | None:
    for position in client.get_positions():
        if position.get("symbol") == symbol.upper():
            return position
    return None


def _history_to_bars(symbol: str, timeframe: str, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bars = []
    for item in history:
        if not item.get("timestamp"):
            continue
        close = float(item.get("close") or 0.0)
        bars.append(
            {
                "symbol": symbol.upper(),
                "timeframe": timeframe,
                "timestamp": item["timestamp"],
                "open": item.get("open", close),
                "high": item.get("high", close),
                "low": item.get("low", close),
                "close": close,
                "volume": item.get("volume", 0.0),
                "raw": item,
            }
        )
    return bars


def _persist_market_bars(conn: Any, bars: list[dict[str, Any]]) -> None:
    ensure_runtime_schema(conn)
    for bar in bars:
        timestamp = bar.get("timestamp") or bar.get("raw", {}).get("timestamp")
        if not timestamp:
            continue
        conn.execute(
            """
            insert into market_bars
              (symbol, timeframe, timestamp, open, high, low, close, volume, raw)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (symbol, timeframe, timestamp) do update set
              open = excluded.open,
              high = excluded.high,
              low = excluded.low,
              close = excluded.close,
              volume = excluded.volume,
              raw = excluded.raw
            """,
            (
                str(bar["symbol"]).upper(),
                bar.get("timeframe", "1Day"),
                timestamp,
                bar.get("open"),
                bar.get("high"),
                bar.get("low"),
                bar.get("close"),
                bar.get("volume"),
                Jsonb(bar.get("raw", bar)),
            ),
        )


def _bar_summary(bars: list[dict[str, Any]]) -> dict[str, Any]:
    if not bars:
        return {"count": 0}
    first = float(bars[0].get("close") or 0.0)
    last = float(bars[-1].get("close") or 0.0)
    closes = [float(bar.get("close") or 0.0) for bar in bars]
    return {
        "count": len(bars),
        "first_close": first,
        "last_close": last,
        "return_pct": (last / first) - 1.0 if first else 0.0,
        "high": max(closes),
        "low": min(closes),
    }


def _write_artifact(kind: str, name: str, payload: dict[str, Any]) -> str:
    artifact_dir = Path(getenv("ARTIFACT_DIR", "/artifacts"))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in name)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    path = artifact_dir / f"{kind}-{safe_name}-{timestamp}.json"
    path.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")
    return str(path)


def _ensure_paper_orders_runtime_schema(conn: Any) -> None:
    conn.execute("alter table paper_orders add column if not exists filled_qty numeric")
    conn.execute("alter table paper_orders add column if not exists expires_at timestamptz")
    conn.execute("alter table paper_orders add column if not exists expired_at timestamptz")
    conn.execute("alter table paper_orders add column if not exists canceled_at timestamptz")
    conn.execute(
        """
        do $$
        begin
          if not exists (
            select 1 from pg_constraint where conname = 'paper_orders_alpaca_order_id_key'
          ) then
            alter table paper_orders add constraint paper_orders_alpaca_order_id_key unique (alpaca_order_id);
          end if;
        end
        $$;
        """
    )


def _ensure_backtest_runs_table(conn: Any) -> None:
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


def _ensure_backtest_trades_table(conn: Any) -> None:
    ensure_runtime_schema(conn)


def _sync_orders(conn: Any, orders: list[dict[str, Any]]) -> None:
    for order in orders:
        if not order.get("id"):
            continue
        conn.execute(
            """
            insert into paper_orders
              (alpaca_order_id, symbol, side, order_type, qty, status, submitted_at, filled_at,
               filled_avg_price, filled_qty, expires_at, expired_at, canceled_at, raw)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (alpaca_order_id) do update set
              symbol = excluded.symbol,
              side = excluded.side,
              order_type = excluded.order_type,
              qty = excluded.qty,
              status = excluded.status,
              submitted_at = excluded.submitted_at,
              filled_at = excluded.filled_at,
              filled_avg_price = excluded.filled_avg_price,
              filled_qty = excluded.filled_qty,
              expires_at = excluded.expires_at,
              expired_at = excluded.expired_at,
              canceled_at = excluded.canceled_at,
              raw = excluded.raw
            """,
            (
                order.get("id"),
                order.get("symbol"),
                order.get("side"),
                order.get("type", "market"),
                order.get("qty"),
                order.get("status"),
                order.get("submitted_at"),
                order.get("filled_at"),
                order.get("filled_avg_price"),
                order.get("filled_qty"),
                order.get("expires_at"),
                order.get("expired_at"),
                order.get("canceled_at"),
                Jsonb(order),
            ),
        )


def _ensure_position_snapshots_table(conn: Any) -> None:
    conn.execute(
        """
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
        )
        """
    )
    conn.execute(
        "create index if not exists position_snapshots_symbol_time_idx on position_snapshots(symbol, captured_at desc)"
    )
