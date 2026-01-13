from __future__ import annotations

from dataclasses import dataclass
from typing import List
from backend.backtest.data import Quote

@dataclass
class MomentumStrategy:
    symbol: str
    lookback: int = 10
    qty: float = 1.0

    def target_position(self, idx: int, quotes: List[Quote]) -> float:
        # idx is LOCAL index within the quotes list passed to the engine
        if idx < self.lookback:
            return 0.0

        if quotes[idx].mid > quotes[idx - self.lookback].mid:
            return float(self.qty)
        else:
            return 0.0
