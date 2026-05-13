from statistics import mean, pstdev


def compute_features(bar: dict) -> dict[str, float | str]:
    history = bar.get("history", [])
    closes = [float(item["close"]) for item in history if item.get("close") is not None]
    volumes = [float(item["volume"]) for item in history if item.get("volume") is not None]
    close = float(bar["close"])

    def ret(period: int) -> float:
        if len(closes) <= period or closes[-period - 1] == 0:
            return 0.0
        return (close / closes[-period - 1]) - 1.0

    ma_window = closes[-20:] or [close]
    vol_window = volumes[-20:] or [float(bar.get("volume") or 0)]
    avg_close = mean(ma_window)
    avg_volume = mean(vol_window)
    volume_std = pstdev(vol_window) if len(vol_window) > 1 else 0.0

    return {
        "symbol": str(bar["symbol"]),
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
    }
