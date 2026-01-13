from __future__ import annotations

import random
from typing import Iterator, Dict


def orderbook_sim(
    *,
    steps: int,
    mid_start: float,
    spread_bps: float = 5.0,
    vol_bps: float = 10.0,
    seed: int | None = None,
) -> Iterator[Dict[str, float]]:
    """
    Microstructure-ish stream: mid random-walk + bid/ask from spread.
    """
    if seed is not None:
        random.seed(seed)

    mid = float(mid_start)

    for _ in range(steps):
        shock = random.gauss(0.0, vol_bps / 10_000.0)
        mid *= (1.0 + shock)

        spread = mid * (spread_bps / 10_000.0)
        bid = mid - spread / 2
        ask = mid + spread / 2

        yield {"mid": mid, "bid": bid, "ask": ask}
