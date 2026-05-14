from typing import Any, Literal

from pydantic import BaseModel, Field


Action = Literal["buy", "sell", "hold"]
DiscoveryStrategy = Literal[
    "trend_following",
    "breakout",
    "mean_reversion_watch",
    "liquidity",
    "random_baseline",
    "random",
    "momentum",
]


class DecisionRequest(BaseModel):
    symbol: str = Field(min_length=1)
    qty: float = Field(default=1, gt=0)
    dry_run: bool = True
    auto_size: bool = True
    strategy_name: str | None = None
    intended_holding_period: str | None = None
    strategy_plan: dict[str, Any] = Field(default_factory=dict)
    override_action: Action | None = None
    override_confidence: float | None = Field(default=None, ge=0, le=1)
    override_predicted_return: float | None = None


class TickRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    qty: float = Field(default=1, gt=0)
    dry_run: bool = True
    auto_size: bool = True
    discover_if_empty: bool = True
    discovery_strategy: DiscoveryStrategy = "trend_following"
    max_symbols: int = Field(default=3, ge=1, le=20)
    strategy_name: str | None = None
    intended_holding_period: str | None = None
    strategy_plan: dict[str, Any] = Field(default_factory=dict)
    override_action: Action | None = None
    override_confidence: float | None = Field(default=None, ge=0, le=1)
    override_predicted_return: float | None = None


class DiscoveryRequest(BaseModel):
    max_symbols: int = Field(default=3, ge=1, le=20)
    strategy: DiscoveryStrategy = "trend_following"
    qty: float = Field(default=1, gt=0)
    auto_size: bool = True
    universe: str | None = None


class BacktestRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    universe: str | None = None
    days: int = Field(default=120, ge=30, le=1000)
    timeframes: list[str] = Field(default_factory=lambda: ["1Day"])
    horizon_days: int = Field(default=1, ge=1, le=20)
    label_threshold: float = 0.0025
    qty: float = Field(default=1, gt=0)
    auto_size: bool = True
    initial_cash: float = Field(default=10000, gt=0)
    strategy: Literal["inference", "moving_average", "trend_following", "breakout"] = "trend_following"
    persist: bool = True
    force_refresh: bool = False


class BacktestSweepRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    universe: str | None = None
    days: int = Field(default=120, ge=30, le=1000)
    strategies: list[str] = Field(default_factory=lambda: ["trend_following", "breakout"])
    horizons: list[int] = Field(default_factory=lambda: [1, 3, 5])
    label_thresholds: list[float] = Field(default_factory=lambda: [0.0, 0.0025, 0.005])
    initial_cash: float = Field(default=10000, gt=0)
    persist: bool = False
    force_refresh: bool = False


class SymbolRequest(BaseModel):
    symbol: str = Field(min_length=1)
    name: str | None = None
    asset_class: str | None = None
    exchange: str | None = None
    enabled: bool = True
    notes: str | None = None
    universes: list[str] = Field(default_factory=lambda: ["core"])
    validate_with_alpaca: bool = True


class SymbolPatchRequest(BaseModel):
    enabled: bool | None = None
    notes: str | None = None
    universes: list[str] | None = None


class SymbolImportRequest(BaseModel):
    symbols: list[str]
    universe: str = "core"
    enabled: bool = True
    validate_with_alpaca: bool = False


class MarketBarsRequest(BaseModel):
    symbols: list[str]
    timeframe: str = "1Day"
    days: int = Field(default=120, ge=1, le=1000)
    limit: int | None = Field(default=None, ge=1, le=10000)
    persist: bool = True
    force_refresh: bool = False


class ChartRequest(BaseModel):
    symbol: str
    timeframe: str = "1Day"
    days: int = Field(default=120, ge=1, le=1000)
    persist: bool = True


class Prediction(BaseModel):
    symbol: str
    predicted_action: Action
    predicted_return: float | None = None
    confidence: float
    model_name: str
    model_version: str
    raw_output: dict[str, Any] = Field(default_factory=dict)


class PolicyResult(BaseModel):
    status: Literal["approved", "rejected"]
    reasons: list[str] = Field(default_factory=list)
    final_action: Action
