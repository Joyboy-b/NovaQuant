from __future__ import annotations

from typing import Callable, List, Dict, Any


def walk_forward(
    *,
    data: List[Any],
    train_size: int,
    test_size: int,
    strategy_factory: Callable[[List[Any]], Any],
    backtest_runner: Callable[[Any, List[Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    if train_size <= 0 or test_size <= 0:
        raise ValueError("train_size and test_size must be > 0")

    n = len(data)
    if n < (train_size + test_size):
        return {"chunks": [], "chunk_metrics": []}

    chunks: List[Dict[str, Any]] = []
    i = 0

    while i + train_size + test_size <= n:
        train = data[i : i + train_size]
        test = data[i + train_size : i + train_size + test_size]

        strategy = strategy_factory(train)

        out = backtest_runner(strategy, test) or {}
        equity = out.get("equity")

        # Defensive checks to avoid 500s
        if equity is None:
            raise ValueError(
                f"backtest_runner must return dict with key 'equity'. Got keys={list(out.keys())}"
            )

        # Make sure equity is JSON-serializable floats
        equity = [float(x) for x in equity]

        chunks.append(
            {
                "start": i + train_size,             # start of test segment
                "end": i + train_size + test_size,   # end of test segment
                "equity": equity,
                "trades": out.get("trades", []),
            }
        )

        i += test_size

    # Optional: compute per-chunk metrics later; return empty list for now
    return {"chunks": chunks, "chunk_metrics": []}
