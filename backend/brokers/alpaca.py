from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.models.order import Side


@dataclass(frozen=True)
class AlpacaConfig:
    api_key: str | None
    secret_key: str | None
    base_url: str = "https://paper-api.alpaca.markets"

    @property
    def paper(self) -> bool:
        return "paper" in self.base_url.lower()


class AlpacaBroker:
    def __init__(self, config: AlpacaConfig):
        if not config.api_key or not config.secret_key:
            raise ValueError("Alpaca API key and secret are required.")
        self.config = config
        self._client: Any | None = None

    @property
    def client(self) -> Any:
        if self._client is None:
            try:
                from alpaca.trading.client import TradingClient
            except ImportError as exc:
                raise RuntimeError("Install alpaca-py to enable Alpaca paper trading.") from exc

            self._client = TradingClient(
                api_key=self.config.api_key,
                secret_key=self.config.secret_key,
                paper=self.config.paper,
            )
        return self._client

    def submit_limit_order(
        self,
        *,
        order_id: str,
        symbol: str,
        side: Side,
        qty: int,
        limit_price: float,
    ) -> dict[str, Any]:
        try:
            from alpaca.trading.enums import OrderSide, TimeInForce
            from alpaca.trading.requests import LimitOrderRequest
        except ImportError as exc:
            raise RuntimeError("Install alpaca-py to enable Alpaca paper trading.") from exc

        request = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY if side == Side.BUY else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
            limit_price=limit_price,
            client_order_id=order_id,
        )
        submitted = self.client.submit_order(order_data=request)
        return {
            "status": "submitted",
            "broker": "alpaca_paper",
            "order_id": str(submitted.id),
            "client_order_id": submitted.client_order_id,
            "symbol": submitted.symbol,
            "side": str(submitted.side),
            "qty": str(submitted.qty),
            "limit_price": str(submitted.limit_price),
            "submitted_at": submitted.submitted_at.isoformat() if submitted.submitted_at else None,
        }
