from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.db import connect
from app.models import PolicyResult, Prediction


def evaluate_policy(
    settings: Settings,
    prediction: Prediction,
    qty: float,
    latest_price: float,
    *,
    symbol_enabled: bool = True,
    features: dict | None = None,
    position_qty: float = 0.0,
) -> PolicyResult:
    reasons: list[str] = []
    symbol = prediction.symbol.upper()
    notional = qty * latest_price
    features = features or {}
    opens_short = prediction.predicted_action == "sell" and position_qty <= 0

    if not settings.alpaca_paper_trade:
        reasons.append("paper trading is required")
    if not symbol_enabled:
        reasons.append(f"{symbol} is not enabled in the symbol database")
    if prediction.predicted_action == "hold":
        reasons.append("model selected hold")
    if prediction.confidence < settings.min_confidence_to_trade:
        reasons.append("model confidence below minimum")
    if opens_short and not settings.allow_shorts:
        reasons.append("opening new short positions is disabled")
    if opens_short and prediction.confidence < settings.min_short_confidence:
        reasons.append("short confidence below minimum")
    if opens_short and settings.require_trend_alignment and float(features.get("trend_regime", 0.0)) > 0:
        reasons.append("short conflicts with bullish trend regime")
    if qty <= 0:
        reasons.append("order quantity is too small after sizing")
    if notional > settings.max_notional_per_trade:
        reasons.append("proposed order exceeds max notional per trade")
    if abs(float(features.get("position_notional", 0.0))) + notional > settings.max_position_notional:
        reasons.append("position exposure would exceed max position notional")
    if _daily_trade_count() >= settings.max_daily_trades:
        reasons.append("daily trade limit reached")
    if _has_recent_trade(symbol, settings.cooldown_minutes):
        reasons.append("symbol cooldown is active")

    if reasons:
        return PolicyResult(status="rejected", reasons=reasons, final_action="hold")
    return PolicyResult(status="approved", reasons=[], final_action=prediction.predicted_action)


def evaluate_symbol_precheck(
    settings: Settings,
    symbol: str,
    qty: float,
    latest_price: float,
    *,
    symbol_enabled: bool = True,
) -> list[str]:
    reasons: list[str] = []
    symbol = symbol.upper()
    notional = qty * latest_price

    if not settings.alpaca_paper_trade:
        reasons.append("paper trading is required")
    if not symbol_enabled:
        reasons.append(f"{symbol} is not enabled in the symbol database")
    if qty <= 0:
        reasons.append("order quantity is too small after sizing")
    if notional > settings.max_notional_per_trade:
        reasons.append("proposed order exceeds max notional per trade")
    if _daily_trade_count() >= settings.max_daily_trades:
        reasons.append("daily trade limit reached")
    if _has_recent_trade(symbol, settings.cooldown_minutes):
        reasons.append("symbol cooldown is active")

    return reasons


def _daily_trade_count() -> int:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    with connect() as conn:
        row = conn.execute(
            "select count(*) as count from paper_orders where created_at >= %s",
            (start,),
        ).fetchone()
    return int(row["count"])


def _has_recent_trade(symbol: str, cooldown_minutes: int) -> bool:
    since = datetime.now(UTC) - timedelta(minutes=cooldown_minutes)
    with connect() as conn:
        row = conn.execute(
            """
            select 1
            from paper_orders
            where symbol = %s and created_at >= %s
            limit 1
            """,
            (symbol, since),
        ).fetchone()
    return row is not None
