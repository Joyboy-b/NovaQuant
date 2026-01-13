from __future__ import annotations

from typing import Dict, List
import numpy as np


def bootstrap_mean_ci(x: List[float], n: int = 2000, alpha: float = 0.05, seed: int | None = None) -> Dict[str, float]:
    rng = np.random.default_rng(seed)
    arr = np.array(x, dtype=float)
    if arr.size == 0:
        return {"mean": 0.0, "lo": 0.0, "hi": 0.0}

    samples = rng.choice(arr, size=(n, arr.size), replace=True)
    means = samples.mean(axis=1)
    lo = float(np.quantile(means, alpha / 2))
    hi = float(np.quantile(means, 1 - alpha / 2))
    return {"mean": float(arr.mean()), "lo": lo, "hi": hi}


def permutation_test_mean_gt_zero(x: List[float], n: int = 5000, seed: int | None = None) -> Dict[str, float]:
    """
    Sign-flip permutation test (null: mean == 0).
    Returns p-value for mean > 0.
    """
    rng = np.random.default_rng(seed)
    arr = np.array(x, dtype=float)
    if arr.size == 0:
        return {"mean": 0.0, "p_value": 1.0}

    observed = float(arr.mean())
    # sign flip
    signs = rng.choice([-1.0, 1.0], size=(n, arr.size), replace=True)
    perm_means = (arr * signs).mean(axis=1)
    p = float((perm_means >= observed).mean())
    return {"mean": observed, "p_value": p}
