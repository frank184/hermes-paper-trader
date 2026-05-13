from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.db import connect
from app.models import PolicyResult, Prediction


def evaluate_policy(settings: Settings, prediction: Prediction, qty: float, latest_price: float) -> PolicyResult:
    reasons: list[str] = []
    symbol = prediction.symbol.upper()
    notional = qty * latest_price

    if not settings.alpaca_paper_trade:
        reasons.append("paper trading is required")
    if symbol not in settings.symbol_allowlist:
        reasons.append(f"{symbol} is not in the symbol allowlist")
    if prediction.predicted_action == "hold":
        reasons.append("model selected hold")
    if prediction.confidence < settings.min_confidence_to_trade:
        reasons.append("model confidence below minimum")
    if qty <= 0:
        reasons.append("order quantity is too small after sizing")
    if notional > settings.max_notional_per_trade:
        reasons.append("proposed order exceeds max notional per trade")
    if _daily_trade_count() >= settings.max_daily_trades:
        reasons.append("daily trade limit reached")
    if _has_recent_trade(symbol, settings.cooldown_minutes):
        reasons.append("symbol cooldown is active")

    if reasons:
        return PolicyResult(status="rejected", reasons=reasons, final_action="hold")
    return PolicyResult(status="approved", reasons=[], final_action=prediction.predicted_action)


def evaluate_symbol_precheck(settings: Settings, symbol: str, qty: float, latest_price: float) -> list[str]:
    reasons: list[str] = []
    symbol = symbol.upper()
    notional = qty * latest_price

    if not settings.alpaca_paper_trade:
        reasons.append("paper trading is required")
    if symbol not in settings.symbol_allowlist:
        reasons.append(f"{symbol} is not in the symbol allowlist")
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
