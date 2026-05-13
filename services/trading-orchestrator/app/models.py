from typing import Any, Literal

from pydantic import BaseModel, Field


Action = Literal["buy", "sell", "hold"]


class DecisionRequest(BaseModel):
    symbol: str = Field(min_length=1)
    qty: float = Field(default=1, gt=0)
    dry_run: bool = True
    auto_size: bool = True
    override_action: Action | None = None
    override_confidence: float | None = Field(default=None, ge=0, le=1)
    override_predicted_return: float | None = None


class TickRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    qty: float = Field(default=1, gt=0)
    dry_run: bool = True
    auto_size: bool = True
    discover_if_empty: bool = True
    discovery_strategy: Literal["random", "liquidity", "momentum"] = "random"
    max_symbols: int = Field(default=3, ge=1, le=20)
    override_action: Action | None = None
    override_confidence: float | None = Field(default=None, ge=0, le=1)
    override_predicted_return: float | None = None


class DiscoveryRequest(BaseModel):
    max_symbols: int = Field(default=3, ge=1, le=20)
    strategy: Literal["random", "liquidity", "momentum"] = "random"
    qty: float = Field(default=1, gt=0)
    auto_size: bool = True


class BacktestRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    days: int = Field(default=120, ge=30, le=1000)
    horizon_days: int = Field(default=1, ge=1, le=20)
    label_threshold: float = 0.0025
    qty: float = Field(default=1, gt=0)
    auto_size: bool = True
    initial_cash: float = Field(default=10000, gt=0)
    strategy: Literal["inference", "moving_average"] = "moving_average"
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
