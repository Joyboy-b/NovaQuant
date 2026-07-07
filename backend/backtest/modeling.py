from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional

import numpy as np
from sklearn.linear_model import LogisticRegression

from backend.backtest.data import Quote
from backend.backtest.features import FeatureConfig, build_features, build_label_next_return


@dataclass
class TrainedModel:
    model: LogisticRegression
    cfg: FeatureConfig
    feature_dim: int


def train_classifier(
    quotes: List[Quote],
    *,
    cfg: Optional[FeatureConfig] = None,
    min_points: int = 200,
) -> TrainedModel:
    cfg = cfg or FeatureConfig()

    # Need enough points for features + next-step labels
    if len(quotes) < max(min_points, (max(cfg.lookbacks) + 5)):
        raise ValueError(f"Not enough data to train: n={len(quotes)}")

    X: List[List[float]] = []
    y: List[int] = []

    start_idx = max(cfg.lookbacks)  # ensure lookbacks exist
    for i in range(start_idx, len(quotes) - 1):
        X.append(build_features(quotes, i, cfg))
        y.append(build_label_next_return(quotes, i))

    Xn = np.asarray(X, dtype=np.float64)
    yn = np.asarray(y, dtype=np.int32)

    model = LogisticRegression(max_iter=200)
    model.fit(Xn, yn)

    return TrainedModel(model=model, cfg=cfg, feature_dim=Xn.shape[1])


def predict_proba_up(tm: TrainedModel, quotes: List[Quote], idx: int) -> float:
    x = np.asarray([build_features(quotes, idx, tm.cfg)], dtype=np.float64)
    # proba for class 1
    p = float(tm.model.predict_proba(x)[0, 1])
    return p
