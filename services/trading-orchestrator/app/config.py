from functools import lru_cache
from os import getenv

from pydantic import BaseModel


class Settings(BaseModel):
    database_url: str = getenv("DATABASE_URL", "postgresql://hermes:hermes@localhost:5432/hermes_trader")
    inference_api_url: str = getenv("INFERENCE_API_URL", "http://localhost:8002")
    alpaca_api_key: str | None = getenv("ALPACA_API_KEY")
    alpaca_secret_key: str | None = getenv("ALPACA_SECRET_KEY")
    alpaca_paper_trade: bool = getenv("ALPACA_PAPER_TRADE", "true").lower() == "true"
    symbol_allowlist: set[str] = {
        symbol.strip().upper()
        for symbol in getenv("SYMBOL_ALLOWLIST", "SPY,QQQ,AAPL,MSFT,NVDA").split(",")
        if symbol.strip()
    }
    max_notional_per_trade: float = float(getenv("MAX_NOTIONAL_PER_TRADE", "500"))
    max_daily_trades: int = int(getenv("MAX_DAILY_TRADES", "5"))
    min_confidence_to_trade: float = float(getenv("MIN_CONFIDENCE_TO_TRADE", "0.58"))
    cooldown_minutes: int = int(getenv("COOLDOWN_MINUTES", "30"))
    allow_inference_override: bool = getenv("ALLOW_INFERENCE_OVERRIDE", "true").lower() == "true"


@lru_cache
def get_settings() -> Settings:
    return Settings()
