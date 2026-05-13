from statistics import mean, pstdev


FEATURE_VERSION = "features-v1"
FEATURE_ORDER = [
    "returns_1",
    "returns_5",
    "returns_20",
    "moving_average_distance_20",
    "volatility_20",
    "volume_zscore_20",
    "daily_returns_20",
    "daily_returns_60",
    "daily_returns_120",
    "sma_distance_20",
    "sma_distance_50",
    "sma_distance_200",
    "trend_regime",
    "drawdown_from_52w_high",
    "distance_from_52w_low",
    "position_qty",
    "position_notional",
    "unrealized_plpc",
]


def compute_features(bar: dict, position: dict | None = None) -> dict[str, float | str]:
    history = bar.get("history", [])
    closes = [float(item["close"]) for item in history if item.get("close") is not None]
    volumes = [float(item["volume"]) for item in history if item.get("volume") is not None]
    daily_history = bar.get("daily_history", [])
    daily_closes = [
        float(item["close"]) for item in daily_history if item.get("close") is not None
    ] or closes
    close = float(bar["close"])

    def ret(period: int) -> float:
        if len(closes) <= period or closes[-period - 1] == 0:
            return 0.0
        return (close / closes[-period - 1]) - 1.0

    def daily_ret(period: int) -> float:
        if len(daily_closes) <= period or daily_closes[-period - 1] == 0:
            return 0.0
        return (close / daily_closes[-period - 1]) - 1.0

    def sma_distance(window: int) -> float:
        values = daily_closes[-window:]
        if not values:
            return 0.0
        avg = mean(values)
        return (close / avg) - 1.0 if avg else 0.0

    ma_window = closes[-20:] or [close]
    vol_window = volumes[-20:] or [float(bar.get("volume") or 0)]
    avg_close = mean(ma_window)
    avg_volume = mean(vol_window)
    volume_std = pstdev(vol_window) if len(vol_window) > 1 else 0.0
    high_52w = max(daily_closes[-252:] or [close])
    low_52w = min(daily_closes[-252:] or [close])
    position_qty = _safe_float((position or {}).get("qty"))
    position_notional = _safe_float((position or {}).get("market_value"))
    unrealized_plpc = _safe_float((position or {}).get("unrealized_plpc"))
    sma20 = sma_distance(20)
    sma50 = sma_distance(50)
    sma200 = sma_distance(200)
    trend_regime = 1.0 if sma20 > 0 and sma50 > 0 and sma200 >= -0.02 else -1.0 if sma20 < 0 and sma50 < 0 else 0.0

    return {
        "symbol": str(bar["symbol"]),
        "feature_version": FEATURE_VERSION,
        "close": close,
        "volume": float(bar.get("volume") or 0),
        "returns_1": ret(1),
        "returns_5": ret(5),
        "returns_20": ret(20),
        "moving_average_distance_20": (close / avg_close) - 1.0 if avg_close else 0.0,
        "volatility_20": pstdev(closes[-20:]) / avg_close if len(closes[-20:]) > 1 and avg_close else 0.0,
        "volume_zscore_20": ((float(bar.get("volume") or 0) - avg_volume) / volume_std)
        if volume_std
        else 0.0,
        "daily_returns_20": daily_ret(20),
        "daily_returns_60": daily_ret(60),
        "daily_returns_120": daily_ret(120),
        "sma_distance_20": sma20,
        "sma_distance_50": sma50,
        "sma_distance_200": sma200,
        "trend_regime": trend_regime,
        "drawdown_from_52w_high": (close / high_52w) - 1.0 if high_52w else 0.0,
        "distance_from_52w_low": (close / low_52w) - 1.0 if low_52w else 0.0,
        "position_qty": position_qty,
        "position_notional": position_notional,
        "unrealized_plpc": unrealized_plpc,
    }


def _safe_float(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
