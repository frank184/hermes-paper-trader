from decimal import Decimal
from datetime import UTC, datetime, timedelta
from typing import Any

from alpaca.common.enums import Sort
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import GetOrderByIdRequest, GetOrdersRequest, MarketOrderRequest

from app.config import Settings


class AlpacaPaperClient:
    def __init__(self, settings: Settings):
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            raise RuntimeError("ALPACA_API_KEY and ALPACA_SECRET_KEY are required")
        if not settings.alpaca_paper_trade:
            raise RuntimeError("This service refuses to run with ALPACA_PAPER_TRADE=false")

        self.trading = TradingClient(
            settings.alpaca_api_key,
            settings.alpaca_secret_key,
            paper=True,
        )
        self.data = StockHistoricalDataClient(settings.alpaca_api_key, settings.alpaca_secret_key)

    def get_account(self) -> dict[str, Any]:
        return self.trading.get_account().model_dump(mode="json")

    def get_positions(self) -> list[dict[str, Any]]:
        return [position.model_dump(mode="json") for position in self.trading.get_all_positions()]

    def get_orders(
        self,
        status: str = "open",
        limit: int = 50,
        symbols: list[str] | None = None,
        side: str | None = None,
    ) -> list[dict[str, Any]]:
        request = GetOrdersRequest(
            status=QueryOrderStatus(status),
            limit=limit,
            direction=Sort.DESC,
            symbols=symbols or None,
            side=OrderSide(side) if side else None,
        )
        return [order.model_dump(mode="json") for order in self.trading.get_orders(request)]

    def get_order(self, order_id: str) -> dict[str, Any]:
        order = self.trading.get_order_by_id(order_id, GetOrderByIdRequest(nested=False))
        return order.model_dump(mode="json") if hasattr(order, "model_dump") else order

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        self.trading.cancel_order_by_id(order_id)
        return {"order_id": order_id, "status": "cancel_requested"}

    def get_clock(self) -> dict[str, Any]:
        return self.trading.get_clock().model_dump(mode="json")

    def latest_bar(self, symbol: str) -> dict[str, Any]:
        end = datetime.now(UTC)
        start = end - timedelta(days=5)
        request = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Minute,
            start=start,
            end=end,
            limit=30,
            feed=DataFeed.IEX,
        )
        bars = self.data.get_stock_bars(request).data.get(symbol, [])
        if not bars:
            raise RuntimeError(f"No bars returned for {symbol}")
        bar = bars[-1]
        return {
            "symbol": symbol,
            "timeframe": "1Min",
            "open": float(bar.open),
            "high": float(bar.high),
            "low": float(bar.low),
            "close": float(bar.close),
            "volume": float(bar.volume),
            "raw": bar.model_dump(mode="json"),
            "history": [
                {
                    "close": float(item.close),
                    "volume": float(item.volume),
                    "timestamp": item.timestamp.isoformat(),
                }
                for item in bars
            ],
        }

    def historical_daily_bars(self, symbol: str, days: int) -> list[dict[str, Any]]:
        end = datetime.now(UTC)
        start = end - timedelta(days=days)
        request = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            limit=days + 10,
            feed=DataFeed.IEX,
        )
        bars = self.data.get_stock_bars(request).data.get(symbol, [])
        return [
            {
                "symbol": symbol,
                "timestamp": bar.timestamp.isoformat(),
                "timeframe": "1Day",
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": float(bar.volume),
                "raw": bar.model_dump(mode="json"),
            }
            for bar in sorted(bars, key=lambda item: item.timestamp)
        ]

    def submit_market_order(self, symbol: str, side: str, qty: Decimal) -> dict[str, Any]:
        order = self.trading.submit_order(
            MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )
        )
        return order.model_dump(mode="json")
