# backend/backtest/strategies/ml_momentum.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from sklearn.linear_model import LogisticRegression

from backend.backtest.data import Quote


def _safe_log(x: float) -> float:
    return float(np.log(max(x, 1e-12)))


@dataclass
class MLMomentumStrategy:
    symbol: str
    qty: float = 1.0

    # training config
    lookbacks: List[int] = field(default_factory=lambda: [1, 2, 5, 10, 20])
    vol_window: int = 20

    # learned state
    model: Optional[LogisticRegression] = None
    is_fit: bool = False

    def fit(self, quotes: List[Quote]) -> None:
        if len(quotes) < max(self.lookbacks) + 5:
            # not enough data to train
            self.model = None
            self.is_fit = False
            return

        X, y = self._make_dataset(quotes)
        if len(y) < 10:
            self.model = None
            self.is_fit = False
            return

        m = LogisticRegression(max_iter=1000)
        m.fit(X, y)

        self.model = m
        self.is_fit = True

    def target_position(self, idx: int, quotes: List[Quote]) -> float:
        # If not trained, do nothing
        if not self.is_fit or self.model is None:
            return 0.0

        # Need enough history for features
        needed = max(self.lookbacks + [self.vol_window])
        if idx < needed:
            return 0.0

        x = self._features_at(idx, quotes).reshape(1, -1)
        p_up = float(self.model.predict_proba(x)[0, 1])

        # threshold can be tuned later / made a parameter
        return float(self.qty) if p_up >= 0.55 else 0.0

    # ---------- internals ----------

    def _features_at(self, idx: int, quotes: List[Quote]) -> np.ndarray:
        mids = np.array([q.mid for q in quotes], dtype=float)

        feats = []

        # multi-horizon returns
        for lb in self.lookbacks:
            r = _safe_log(mids[idx]) - _safe_log(mids[idx - lb])
            feats.append(r)

        # rolling mean return + volatility
        w = self.vol_window
        rets = np.diff(np.log(np.clip(mids[idx - w : idx + 1], 1e-12, None)))
        feats.append(float(np.mean(rets)))
        feats.append(float(np.std(rets) + 1e-12))

        # spread feature (microstructure-ish)
        feats.append(float(quotes[idx].spread / max(quotes[idx].mid, 1e-12)))

        return np.array(feats, dtype=float)

    def _make_dataset(self, quotes: List[Quote]):
        mids = np.array([q.mid for q in quotes], dtype=float)
        n = len(quotes)

        needed = max(self.lookbacks + [self.vol_window])
        X = []
        y = []

        # predict next-step direction
        for i in range(needed, n - 1):
            x = self._features_at(i, quotes)
            next_ret = _safe_log(mids[i + 1]) - _safe_log(mids[i])
            label = 1 if next_ret > 0 else 0

            X.append(x)
            y.append(label)

        return np.vstack(X), np.array(y, dtype=int)
