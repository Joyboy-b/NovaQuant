from __future__ import annotations
from dataclasses import dataclass
from typing import List
import math

from backend.backtest.data import Quote


def _mean(xs: List[float]) -> float:
    return sum(xs) / (len(xs) or 1)


def _std(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(max(var, 0.0))


def _rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains = 0.0
    losses = 0.0
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        if diff >= 0:
            gains += diff
        else:
            losses += -diff
    if losses == 0:
        return 100.0
    rs = (gains / period) / (losses / period)
    return 100.0 - (100.0 / (1.0 + rs))


@dataclass
class FeatureConfig:
    lookbacks: List[int] = None

    def __post_init__(self):
        if self.lookbacks is None:
            self.lookbacks = [5, 10, 20, 40]


def build_features(quotes: List[Quote], idx: int, cfg: FeatureConfig) -> List[float]:
    """
    Build a feature vector at quotes[idx] using only past/current data.
    """
    closes = [q.mid for q in quotes[: idx + 1]]
    x: List[float] = []

    # Basic returns / momentum at multiple horizons
    for lb in cfg.lookbacks:
        if idx - lb < 0:
            x.extend([0.0, 0.0])
            continue
        ret = (closes[idx] / closes[idx - lb] - 1.0) if closes[idx - lb] != 0 else 0.0
        # realized vol estimate from last lb returns
        rets = []
        for k in range(max(1, idx - lb + 1), idx + 1):
            prev = closes[k - 1]
            rets.append((closes[k] / prev - 1.0) if prev != 0 else 0.0)
        vol = _std(rets)
        x.extend([ret, vol])

    # RSI-ish feature
    x.append(_rsi(closes, period=14) / 100.0)  # normalize 0..1

    # Spread proxy (if bid/ask available)
    q = quotes[idx]
    if q.bid and q.ask and q.mid:
        spread = (q.ask - q.bid) / q.mid if q.mid != 0 else 0.0
    else:
        spread = 0.0
    x.append(spread)

    return [float(v) for v in x]


def build_label_next_return(quotes: List[Quote], idx: int) -> int:
    """
    Classification label: 1 if next mid return > 0 else 0.
    """
    if idx + 1 >= len(quotes):
        return 0
    a = quotes[idx].mid
    b = quotes[idx + 1].mid
    if a == 0:
        return 0
    return 1 if (b / a - 1.0) > 0 else 0
