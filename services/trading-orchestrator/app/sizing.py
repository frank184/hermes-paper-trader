from math import floor
from typing import Any

from app.config import Settings

MIN_ORDER_QTY = 0.0001
QTY_PRECISION = 4


def size_order(settings: Settings, requested_qty: float, latest_price: float, auto_size: bool) -> dict[str, Any]:
    max_notional = float(settings.max_notional_per_trade)
    requested_notional = requested_qty * latest_price
    max_qty = max_notional / latest_price if latest_price > 0 else 0.0
    effective_qty = requested_qty
    reasons: list[str] = []

    if auto_size and requested_notional > max_notional:
        effective_qty = _floor_qty(max_qty)
        reasons.append("requested qty reduced to stay under max notional per trade")

    if effective_qty < MIN_ORDER_QTY:
        effective_qty = 0.0
        reasons.append("sized qty is below minimum order quantity")

    effective_notional = effective_qty * latest_price
    return {
        "requested_qty": requested_qty,
        "effective_qty": effective_qty,
        "latest_price": latest_price,
        "requested_notional": requested_notional,
        "effective_notional": effective_notional,
        "max_notional": max_notional,
        "max_qty": _floor_qty(max_qty),
        "auto_size": auto_size,
        "adjusted": effective_qty != requested_qty,
        "reasons": reasons,
    }


def _floor_qty(qty: float) -> float:
    scale = 10**QTY_PRECISION
    return floor(qty * scale) / scale
