from os import getenv
from typing import Any

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
    discovery_strategy: str = "random",
    max_symbols: int = 3,
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
                "override_action": override_action,
                "override_confidence": override_confidence,
                "override_predicted_return": override_predicted_return,
            },
        )
        return _json_or_error(response)


@mcp.tool
async def discover_trade_candidates(
    max_symbols: int = 3,
    strategy: str = "random",
    qty: float = 1.0,
    auto_size: bool = True,
) -> dict[str, Any]:
    """Discover eligible symbols from the orchestrator allowlist before running a tick."""
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(
            f"{_orchestrator_url()}/symbols/discover",
            json={
                "max_symbols": max_symbols,
                "strategy": strategy,
                "qty": qty,
                "auto_size": auto_size,
            },
        )
        return _json_or_error(response)


@mcp.tool
async def propose_trade_decision(
    symbol: str,
    qty: float = 1.0,
    dry_run: bool = True,
    auto_size: bool = True,
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
) -> dict[str, Any]:
    """Backtest historical bars and persist labeled rows for inference training."""
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{_orchestrator_url()}/backtests/run",
            json={
                "symbols": symbols or [],
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


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path="/mcp")
