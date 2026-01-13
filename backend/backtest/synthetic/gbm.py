from __future__ import annotations

import math
import random
from typing import List, Optional


def generate_gbm_prices(*, steps: int, start: float, mu: float, sigma: float, seed: Optional[int] = None) -> List[float]:
    """
    Very small GBM-ish synthetic generator for stress tests & dev.
    steps: number of points
    mu: drift per step
    sigma: vol per step
    """
    if seed is not None:
        random.seed(seed)

    prices = [float(start)]
    for _ in range(steps - 1):
        z = random.gauss(0.0, 1.0)
        # log-return
        r = (mu - 0.5 * sigma * sigma) + sigma * z
        nxt = prices[-1] * math.exp(r)
        prices.append(max(1e-9, nxt))
    return prices
