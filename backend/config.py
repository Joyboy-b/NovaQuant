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


SETTINGS = Settings(
    # optionally override from environment
    allowed_origins=os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else ["http://localhost:3000", "http://localhost:5173"],
    binance_symbol=os.getenv("BINANCE_SYMBOL", "BTCUSDT"),
)
