# backend/services/metrics.py
import math
import statistics
from typing import List
from backend.models.metrics import MetricsResponse


def _returns_from_equity(equity: List[float]) -> List[float]:
    if len(equity) < 2:
        return []
    out: List[float] = []
    for i in range(1, len(equity)):
        prev = equity[i - 1]
        if prev == 0:
            continue
        out.append((equity[i] - prev) / prev)
    return out


def compute_metrics(equity: List[float], trade_pnls: List[float]) -> MetricsResponse:
    rets = _returns_from_equity(equity)
    sharpe = sortino = None

    if rets:
        mean_r = statistics.fmean(rets)
        std_r = statistics.pstdev(rets) or 1e-12
        sharpe = mean_r * math.sqrt(len(rets)) / std_r

        downs = [r for r in rets if r < 0]
        if downs:
            std_down = statistics.pstdev(downs) if len(downs) > 1 else abs(downs[0])
        else:
            std_down = 0.0
        sortino = mean_r * math.sqrt(len(rets)) / (std_down or 1e-12)

    max_dd = None
    if equity:
        peak = equity[0]
        max_dd = 0.0
        for v in equity:
            peak = max(peak, v)
            dd = (peak - v) / peak * 100 if peak > 0 else 0.0
            max_dd = max(max_dd, dd)

    profit_factor = None
    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p < 0]
    if losses:
        profit_factor = sum(wins) / abs(sum(losses))

    win_rate = (len(wins) / len(trade_pnls)) if trade_pnls else None

    return MetricsResponse(
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown_pct=max_dd,
        profit_factor=profit_factor,
        win_rate=win_rate,
        trades=len(trade_pnls),
    )
