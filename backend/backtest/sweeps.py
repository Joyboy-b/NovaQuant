from __future__ import annotations

from typing import Dict, List, Any, Callable


def grid_sweep(
    *,
    param_grid: Dict[str, List[Any]],
    runner: Callable[[Dict[str, Any]], Dict[str, Any]],
    score_key: str = "sharpe",
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    runner(params) -> {"metrics": {...}, "equity": [...], "trades": [...]}
    score_key is looked up in metrics.
    """
    keys = list(param_grid.keys())
    results: List[Dict[str, Any]] = []

    def rec(i: int, cur: Dict[str, Any]):
        if i == len(keys):
            out = runner(cur)
            score = out.get("metrics", {}).get(score_key)
            results.append({"params": dict(cur), "score": score, **out})
            return
        k = keys[i]
        for v in param_grid[k]:
            cur[k] = v
            rec(i + 1, cur)
        cur.pop(k, None)

    rec(0, {})
    # sort None to bottom
    results.sort(key=lambda r: (r["score"] is None, -(r["score"] or -1e18)))
    return results[:top_k]
