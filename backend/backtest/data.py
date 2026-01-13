from __future__ import annotations

from dataclasses import dataclass
from typing import List, Iterable, Dict, Any, Optional

import math


@dataclass(frozen=True)
class Quote:
    i: int
    mid: float
    bid: float
    ask: float

    @property
    def spread(self) -> float:
        return max(0.0, self.ask - self.bid)


def quotes_from_mid_prices(prices: List[float], spread_bps: float = 5.0) -> List[Quote]:
    out: List[Quote] = []
    for i, mid in enumerate(prices):
        spread = mid * (spread_bps / 10_000.0)
        bid = mid - spread / 2
        ask = mid + spread / 2
        out.append(Quote(i=i, mid=mid, bid=bid, ask=ask))
    return out


def quotes_from_yahoo_df(df, price_col: str = "close", spread_bps: float = 5.0) -> List[Quote]:
    # df expected to have a "close" column (lowercase from yahoo.py)
    out: List[Quote] = []
    pxs = df[price_col].tolist()
    return quotes_from_mid_prices(pxs, spread_bps=spread_bps)
