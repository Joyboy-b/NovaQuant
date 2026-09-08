from __future__ import annotations

from typing import Dict, List
import numpy as np


def bootstrap_mean_ci(x: List[float], n: int = 2000, alpha: float = 0.05, seed: int | None = None) -> Dict[str, float]:
    rng = np.random.default_rng(seed)
    arr = np.array(x, dtype=float)
    if arr.size == 0:
        return {"mean": 0.0, "lo": 0.0, "hi": 0.0}

    if n <= 0:
        raise ValueError('n must be positive')

    # Reuse a small gather buffer; indices use the same RNG algorithm as choice.
    # Eight rows keep the working set smaller than the original 32-row batches.
    means = np.empty(n, dtype=float)
    samples = np.empty((min(8, n), arr.size), dtype=float)
    for i in range(0, n, 8):
        count = min(8, n-i)
        indices = rng.integers(0, arr.size, size=(count, arr.size))
        np.take(arr, indices, out=samples[:count], mode='clip')
        means[i:i+count] = samples[:count].mean(axis=1)
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

    if n <= 0:
        raise ValueError('n must be positive')
    observed = float(arr.mean())
    signs = np.array([-1.0, 1.0])
    samples = np.empty((min(8, n), arr.size), dtype=float)
    exceedances = 0
    for i in range(0, n, 8):
        count = min(8, n-i)
        indices = rng.integers(0, 2, size=(count, arr.size))
        np.take(signs, indices, out=samples[:count], mode='clip')
        np.multiply(samples[:count], arr, out=samples[:count])
        exceedances += np.count_nonzero(samples[:count].mean(axis=1) >= observed)
    p = float(exceedances / n)
    return {"mean": observed, "p_value": p}
