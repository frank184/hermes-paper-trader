from os import getenv
from typing import Any
from urllib.parse import quote

import httpx
from fastmcp import FastMCP

mcp = FastMCP("hermes-paper-trader")


@mcp.tool
async def run_trading_tick(
    symbols: list[str] | None = None,
    qty: float = 1.0,
    dry_run: bool = True,
    auto_size: bool = True,
    discover_if_empty: bool = True,
    discovery_strategy: str = "trend_following",
    max_symbols: int = 3,
    strategy_name: str | None = None,
    intended_holding_period: str | None = None,
    strategy_plan: dict[str, Any] | None = None,
    override_action: str | None = None,
    override_confidence: float | None = None,
    override_predicted_return: float | None = None,
) -> dict[str, Any]:
    """Run a policy-gated decision tick.

    Omit symbols, pass an empty list, or pass ["all"] to discover candidates first.
    Do not invent ticker symbols for "all".
    """
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(
            f"{_orchestrator_url()}/ticks/run",
            json={
                "symbols": symbols or [],
                "qty": qty,
                "dry_run": dry_run,
                "auto_size": auto_size,
                "discover_if_empty": discover_if_empty,
                "discovery_strategy": discovery_strategy,
                "max_symbols": max_symbols,
                "strategy_name": strategy_name,
                "intended_holding_period": intended_holding_period,
                "strategy_plan": strategy_plan or {},
                "override_action": override_action,
                "override_confidence": override_confidence,
                "override_predicted_return": override_predicted_return,
            },
        )
        return _json_or_error(response)


@mcp.tool
async def discover_trade_candidates(
    max_symbols: int = 3,
    strategy: str = "trend_following",
    qty: float = 1.0,
    auto_size: bool = True,
    universe: str | None = None,
) -> dict[str, Any]:
    """Discover eligible symbols from the orchestrator symbol database before running a tick."""
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(
            f"{_orchestrator_url()}/symbols/discover",
            json={
                "max_symbols": max_symbols,
                "strategy": strategy,
                "qty": qty,
                "auto_size": auto_size,
                "universe": universe,
            },
        )
        return _json_or_error(response)


@mcp.tool
async def scan_trade_candidates(
    max_symbols: int = 5,
    strategy: str = "trend_following",
    qty: float = 1.0,
    auto_size: bool = True,
    universe: str | None = None,
) -> dict[str, Any]:
    """Scan the Postgres-backed symbol universe using a strategy-aware ranking."""
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(
            f"{_orchestrator_url()}/symbols/scan",
            json={
                "max_symbols": max_symbols,
                "strategy": strategy,
                "qty": qty,
                "auto_size": auto_size,
                "universe": universe,
            },
        )
        return _json_or_error(response)


@mcp.tool
async def list_symbols(enabled: bool | None = None, universe: str | None = None) -> dict[str, Any]:
    """List symbols controlled by the orchestrator's Postgres symbol database."""
    params: dict[str, Any] = {}
    if enabled is not None:
        params["enabled"] = enabled
    if universe:
        params["universe"] = universe
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{_orchestrator_url()}/symbols", params=params)
        return _json_or_error(response)


@mcp.tool
async def add_symbol(
    symbol: str,
    enabled: bool = True,
    universe: str = "core",
    notes: str | None = None,
    validate_with_alpaca: bool = True,
) -> dict[str, Any]:
    """Add or enable a tradable symbol after optional Alpaca asset validation."""
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(
            f"{_orchestrator_url()}/symbols",
            json={
                "symbol": symbol,
                "enabled": enabled,
                "notes": notes,
                "universes": [universe],
                "validate_with_alpaca": validate_with_alpaca,
            },
        )
        return _json_or_error(response)


@mcp.tool
async def disable_symbol(symbol: str, notes: str | None = None) -> dict[str, Any]:
    """Disable a symbol in the orchestrator's Postgres symbol database."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.patch(
            f"{_orchestrator_url()}/symbols/{symbol}",
            json={"enabled": False, "notes": notes},
        )
        return _json_or_error(response)


@mcp.tool
async def import_symbols(
    symbols: list[str],
    universe: str = "core",
    enabled: bool = True,
    validate_with_alpaca: bool = False,
) -> dict[str, Any]:
    """Bulk-import symbols into a named universe."""
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{_orchestrator_url()}/symbols/import",
            json={
                "symbols": symbols,
                "universe": universe,
                "enabled": enabled,
                "validate_with_alpaca": validate_with_alpaca,
            },
        )
        return _json_or_error(response)


@mcp.tool
async def propose_trade_decision(
    symbol: str,
    qty: float = 1.0,
    dry_run: bool = True,
    auto_size: bool = True,
    strategy_name: str | None = None,
    intended_holding_period: str | None = None,
    strategy_plan: dict[str, Any] | None = None,
    override_action: str | None = None,
    override_confidence: float | None = None,
    override_predicted_return: float | None = None,
) -> dict[str, Any]:
    """Propose a single trade and persist the decision audit trail."""
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(
            f"{_orchestrator_url()}/decisions/propose",
            json={
                "symbol": symbol,
                "qty": qty,
                "dry_run": dry_run,
                "auto_size": auto_size,
                "strategy_name": strategy_name,
                "intended_holding_period": intended_holding_period,
                "strategy_plan": strategy_plan or {},
                "override_action": override_action,
                "override_confidence": override_confidence,
                "override_predicted_return": override_predicted_return,
            },
        )
        return _json_or_error(response)


@mcp.tool
async def get_portfolio_state() -> dict[str, Any]:
    """Fetch and persist the current Alpaca paper portfolio/account state."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{_orchestrator_url()}/portfolio/state")
        return _json_or_error(response)


@mcp.tool
async def get_open_positions() -> dict[str, Any]:
    """Fetch and persist current open Alpaca paper positions."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{_orchestrator_url()}/portfolio/positions")
        return _json_or_error(response)


@mcp.tool
async def get_orders(
    status: str = "open",
    limit: int = 50,
    symbols: str | None = None,
    side: str | None = None,
) -> dict[str, Any]:
    """Fetch Alpaca paper orders, including accepted-but-not-filled orders."""
    params = {"status": status, "limit": limit}
    if symbols:
        params["symbols"] = symbols
    if side:
        params["side"] = side
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{_orchestrator_url()}/orders",
            params=params,
        )
        return _json_or_error(response)


@mcp.tool
async def get_order(order_id: str) -> dict[str, Any]:
    """Fetch one Alpaca paper order by id and sync the local order row."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{_orchestrator_url()}/orders/{order_id}")
        return _json_or_error(response)


@mcp.tool
async def cancel_order(order_id: str) -> dict[str, Any]:
    """Cancel a pending Alpaca paper order by id."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.delete(f"{_orchestrator_url()}/orders/{order_id}")
        return _json_or_error(response)


@mcp.tool
async def get_market_clock() -> dict[str, Any]:
    """Fetch the Alpaca market clock so queued orders can be explained."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{_orchestrator_url()}/market/clock")
        return _json_or_error(response)


@mcp.tool
async def get_market_bars(
    symbols: list[str],
    timeframe: str = "1Day",
    days: int = 120,
    limit: int | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Fetch Alpaca market bars through the orchestrator and persist them for research."""
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{_orchestrator_url()}/market/bars",
            json={
                "symbols": symbols,
                "timeframe": timeframe,
                "days": days,
                "limit": limit,
                "persist": persist,
            },
        )
        return _json_or_error(response)


@mcp.tool
async def chart_symbol(
    symbol: str,
    timeframe: str = "1Day",
    days: int = 120,
    persist: bool = True,
) -> dict[str, Any]:
    """Build a browser-viewable candle-chart artifact for one symbol."""
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{_orchestrator_url()}/charts/candles",
            json={"symbol": symbol, "timeframe": timeframe, "days": days, "persist": persist},
        )
        return _compact_chart_response(_json_or_error(response))


@mcp.tool
async def chart_backtest(backtest_run_id: int | None = None) -> dict[str, Any]:
    """Build a browser-viewable equity-curve artifact from persisted backtest trades."""
    params = {}
    if backtest_run_id is not None:
        params["backtest_run_id"] = backtest_run_id
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(f"{_orchestrator_url()}/charts/equity-curve", params=params)
        return _compact_chart_response(_json_or_error(response))


@mcp.tool
async def get_symbol_report(
    symbol: str,
    timeframe: str = "1Day",
    days: int = 120,
    persist: bool = True,
) -> dict[str, Any]:
    """Return recent bars, features, decisions, and a chart artifact for one symbol."""
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{_orchestrator_url()}/reports/symbol",
            json={"symbol": symbol, "timeframe": timeframe, "days": days, "persist": persist},
        )
        return _json_or_error(response)


@mcp.tool
async def get_portfolio_report() -> dict[str, Any]:
    """Return account, positions, open orders, and a persisted report artifact."""
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(f"{_orchestrator_url()}/reports/portfolio")
        return _json_or_error(response)


@mcp.tool
async def run_backtest_seed(
    symbols: list[str] | None = None,
    days: int = 120,
    horizon_days: int = 1,
    label_threshold: float = 0.0025,
    qty: float = 1.0,
    auto_size: bool = True,
    initial_cash: float = 10000,
    strategy: str = "moving_average",
    persist: bool = True,
    universe: str | None = None,
) -> dict[str, Any]:
    """Backtest historical bars and persist labeled rows for inference training."""
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{_orchestrator_url()}/backtests/run",
            json={
                "symbols": symbols or [],
                "universe": universe,
                "days": days,
                "horizon_days": horizon_days,
                "label_threshold": label_threshold,
                "qty": qty,
                "auto_size": auto_size,
                "initial_cash": initial_cash,
                "strategy": strategy,
                "persist": persist,
            },
        )
        return _json_or_error(response)


@mcp.tool
async def run_backtest_sweep(
    symbols: list[str] | None = None,
    universe: str | None = None,
    days: int = 120,
    strategies: list[str] | None = None,
    horizons: list[int] | None = None,
    label_thresholds: list[float] | None = None,
    initial_cash: float = 10000,
    persist: bool = False,
) -> dict[str, Any]:
    """Run a small strategy/parameter sweep without submitting paper orders."""
    async with httpx.AsyncClient(timeout=240) as client:
        response = await client.post(
            f"{_orchestrator_url()}/backtests/sweep",
            json={
                "symbols": symbols or [],
                "universe": universe,
                "days": days,
                "strategies": strategies or ["trend_following", "breakout"],
                "horizons": horizons or [1, 3, 5],
                "label_thresholds": label_thresholds or [0.0, 0.0025, 0.005],
                "initial_cash": initial_cash,
                "persist": persist,
            },
        )
        return _json_or_error(response)


def _orchestrator_url() -> str:
    return getenv("TRADING_ORCHESTRATOR_URL", "http://trading-orchestrator:8000").rstrip("/")


def _json_or_error(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        body = {"text": response.text}
    if response.is_error:
        return {
            "error": "orchestrator_request_failed",
            "status_code": response.status_code,
            "body": body,
        }
    return body


def _compact_chart_response(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("error"):
        return payload

    workspace_paths = payload.get("workspace_artifact_paths") or {}
    artifact_paths = payload.get("artifact_paths") or {}
    html_workspace_path = workspace_paths.get("html")
    svg_workspace_path = workspace_paths.get("svg")

    compact = {
        "type": payload.get("type"),
        "symbol": payload.get("symbol"),
        "timeframe": payload.get("timeframe"),
        "backtest_run_id": payload.get("backtest_run_id"),
        "summary": payload.get("summary"),
        "point_count": len(payload.get("points") or []),
        "bar_count": len(payload.get("bars") or []),
        "artifact_paths": artifact_paths,
        "workspace_artifact_paths": workspace_paths,
        "html_artifact_path": payload.get("html_artifact_path"),
        "svg_artifact_path": payload.get("svg_artifact_path"),
        "json_artifact_path": payload.get("artifact_path"),
    }
    if svg_workspace_path:
        image_url = f"/api/files?action=download&path={quote(svg_workspace_path, safe='')}"
        compact["chat_image_url"] = image_url
        compact["chat_markdown_image"] = f"![{payload.get('symbol') or payload.get('type') or 'Trader chart'} chart]({image_url})"
        compact["chat_render_hint"] = "Include chat_markdown_image verbatim in the assistant response to render the chart inline."
    if html_workspace_path:
        compact["open_hint"] = f"Open {html_workspace_path} in the Workspace Files panel to view the chart."
    return {key: value for key, value in compact.items() if value not in (None, {}, [])}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path="/mcp")
