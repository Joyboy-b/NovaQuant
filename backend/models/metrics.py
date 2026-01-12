# backend/models/metrics.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class MetricsResponse(BaseModel):
    sharpe: Optional[float] = None
    sortino: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    profit_factor: Optional[float] = None
    win_rate: Optional[float] = None
    trades: int = 0
