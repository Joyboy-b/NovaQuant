# backend/config.py
from __future__ import annotations
from pydantic import BaseModel
import os


class Settings(BaseModel):
    name: str = "NovaQuant"
    version: str = "0.1.0"

    allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Trading / risk
    per_trade_notional_cap: float = 50_000.0
    max_session_drawdown_pct: float = 10.0

    # Market data
    binance_symbol: str = "BTCUSDT"

    # WebSocket streaming interval
    metrics_ws_interval_sec: float = 1.0

    # Optional broker integration. Disabled unless credentials are present
    # and ALPACA_ENABLED is explicitly set to a truthy value.
    alpaca_enabled: bool = False
    alpaca_api_key: str | None = None
    alpaca_secret_key: str | None = None
    alpaca_base_url: str = "https://paper-api.alpaca.markets"


SETTINGS = Settings(
    # optionally override from environment
    allowed_origins=[
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    or ["http://localhost:3000", "http://localhost:5173"],
    binance_symbol=os.getenv("BINANCE_SYMBOL", "BTCUSDT"),
    alpaca_enabled=os.getenv("ALPACA_ENABLED", "").lower() in {"1", "true", "yes", "on"},
    alpaca_api_key=os.getenv("ALPACA_API_KEY"),
    alpaca_secret_key=os.getenv("ALPACA_SECRET_KEY"),
    alpaca_base_url=os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
)
