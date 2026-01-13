from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any

from backend.services.metrics import compute_metrics
from backend.backtest.engine import BacktestEngine
from backend.backtest.costs import BpsCostModel
from backend.backtest.data import Quote, quotes_from_mid_prices, quotes_from_yahoo_df
from backend.backtest.synthetic.gbm import generate_gbm_prices
from backend.backtest.synthetic.orderbook_sim import orderbook_sim
from backend.backtest.strategies.momentum import MomentumStrategy
from backend.backtest.walkforward import walk_forward
from backend.backtest.sweeps import grid_sweep
from backend.backtest.stats import bootstrap_mean_ci, permutation_test_mean_gt_zero
from backend.data.yahoo import load_yahoo

backtest_router = APIRouter(tags=["backtest"])


class BacktestRequest(BaseModel):
    symbol: str = Field(default="BTCUSDT", min_length=1)

    data_source: Literal["gbm", "orderbook", "yahoo"] = "gbm"

    # common length / seed
    steps: int = Field(default=500, ge=50, le=20000)
    seed: Optional[int] = None

    # synthetic params
    start_price: float = Field(default=30000.0, gt=0)
    mu: float = Field(default=0.0)
    sigma: float = Field(default=0.02)
    spread_bps: float = Field(default=5.0, ge=0)
    vol_bps: float = Field(default=10.0, ge=0)  # orderbook sim volatility

    # yahoo params
    yahoo_symbol: str = Field(default="SPY")
    start: str = Field(default="2024-01-01")  # YYYY-MM-DD
    end: str = Field(default="2025-01-01")    # YYYY-MM-DD
    interval: str = Field(default="1d")

    # strategy params
    strategy: Literal["momentum"] = "momentum"
    lookback: int = Field(default=10, ge=2, le=2000)
    qty: float = Field(default=1.0, gt=0)

    # costs
    fee_bps: float = Field(default=1.0, ge=0)
    slippage_bps: float = Field(default=2.0, ge=0)


class BacktestResponse(BaseModel):
    symbol: str
    equity: List[float]
    trades: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    stats: Dict[str, Any]


def _make_quotes(req: BacktestRequest) -> List[Quote]:
    if req.data_source == "gbm":
        prices = generate_gbm_prices(
            steps=req.steps,
            start=req.start_price,
            mu=req.mu,
            sigma=req.sigma,
            seed=req.seed,
        )
        return quotes_from_mid_prices(prices, spread_bps=req.spread_bps)

    if req.data_source == "orderbook":
        stream = list(
            orderbook_sim(
                steps=req.steps,
                mid_start=req.start_price,
                spread_bps=req.spread_bps,
                vol_bps=req.vol_bps,
                seed=req.seed,
            )
        )
        quotes: List[Quote] = []
        for i, q in enumerate(stream):
            quotes.append(Quote(i=i, mid=float(q["mid"]), bid=float(q["bid"]), ask=float(q["ask"])))
        return quotes

    if req.data_source == "yahoo":
        df = load_yahoo(req.yahoo_symbol, start=req.start, end=req.end, interval=req.interval)
        # treat close as mid and construct bid/ask from spread_bps
        return quotes_from_yahoo_df(df, price_col="close", spread_bps=req.spread_bps)

    raise ValueError("Unknown data_source")


def _run_once(req: BacktestRequest) -> Dict[str, Any]:
    quotes = _make_quotes(req)

    strat = MomentumStrategy(symbol=req.symbol, lookback=req.lookback, qty=req.qty)
    cost = BpsCostModel(fee_bps=req.fee_bps, slippage_bps=req.slippage_bps)

    engine = BacktestEngine(symbol=req.symbol, strategy=strat, cost_model=cost)
    out = engine.run(quotes)

    equity = out["equity"]
    trade_pnls = [equity[i] - equity[i - 1] for i in range(1, len(equity))]
    metrics = compute_metrics(equity, trade_pnls).model_dump()

    # stats on trade_pnls (simple but useful)
    stats = {
        "bootstrap_pnl_mean_ci": bootstrap_mean_ci(trade_pnls, seed=req.seed),
        "perm_test_mean_gt_zero": permutation_test_mean_gt_zero(trade_pnls, seed=req.seed),
    }

    return {"equity": equity, "trades": out["trades"], "metrics": metrics, "stats": stats}


@backtest_router.post("/run", response_model=BacktestResponse)
def run_backtest(req: BacktestRequest) -> BacktestResponse:
    out = _run_once(req)
    return BacktestResponse(symbol=req.symbol, **out)


class WalkForwardRequest(BacktestRequest):
    train_size: int = Field(default=300, ge=50, le=20000)
    test_size: int = Field(default=100, ge=10, le=20000)


@backtest_router.post("/walkforward")
def run_walkforward(req: WalkForwardRequest):
    quotes = _make_quotes(req)

    def factory(train_quotes: List[Quote]):
        # simple "fit": choose lookback that maximizes momentum win-rate on train (cheap heuristic)
        best_lb = req.lookback
        best_score = -1.0
        for lb in [5, 10, 20, 40, 80]:
            strat = MomentumStrategy(symbol=req.symbol, lookback=lb, qty=req.qty)
            cost = BpsCostModel(fee_bps=req.fee_bps, slippage_bps=req.slippage_bps)
            eng = BacktestEngine(symbol=req.symbol, strategy=strat, cost_model=cost)
            out = eng.run(train_quotes) or {}
            eq = out.get("equity") or []
            if len(eq) < 2:
                score = -1.0
            else:
                pnls = [eq[i] - eq[i-1] for i in range(1, len(eq))]
                wins = sum(1 for p in pnls if p > 0)
                score = wins / (len(pnls) or 1)

            if score > best_score:
                best_score = score
                best_lb = lb
        return MomentumStrategy(symbol=req.symbol, lookback=best_lb, qty=req.qty)

    def runner(strategy, test_quotes: List[Quote]):
        cost = BpsCostModel(fee_bps=req.fee_bps, slippage_bps=req.slippage_bps)
        eng = BacktestEngine(symbol=req.symbol, strategy=strategy, cost_model=cost)
        return eng.run(test_quotes)

    wf = walk_forward(
        data=quotes,
        train_size=req.train_size,
        test_size=req.test_size,
        strategy_factory=factory,
        backtest_runner=runner,
    )

    chunks = wf["chunks"]

    # compute metrics per chunk
    chunk_metrics = []
    for c in chunks:
        eq = c.get("equity") or []
        eq = [float(x) for x in eq]
        pnls = [eq[i] - eq[i - 1] for i in range(1, len(eq))] if len(eq) >= 2 else []
        m = compute_metrics(eq, pnls).model_dump()
        chunk_metrics.append({"start": c["start"], "end": c["end"], "metrics": m})

    return {"chunks": chunks, "chunk_metrics": chunk_metrics}



class SweepRequest(BacktestRequest):
    lookbacks: List[int] = Field(default_factory=lambda: [5, 10, 20, 40])
    fee_bps_list: List[float] = Field(default_factory=lambda: [0.0, 1.0, 2.0])
    slippage_bps_list: List[float] = Field(default_factory=lambda: [0.0, 2.0, 5.0])
    top_k: int = Field(default=10, ge=1, le=50)
    score_key: Literal["sharpe", "sortino", "max_drawdown_pct", "profit_factor", "win_rate"] = "sharpe"


@backtest_router.post("/sweep")
def run_sweep(req: SweepRequest):
    base = req.model_dump()

    grid = {
        "lookback": req.lookbacks,
        "fee_bps": req.fee_bps_list,
        "slippage_bps": req.slippage_bps_list,
    }

    def runner(p: Dict[str, Any]) -> Dict[str, Any]:
        r = BacktestRequest(**{**base, **p})
        out = _run_once(r)
        return out

    top = grid_sweep(param_grid=grid, runner=runner, score_key=req.score_key, top_k=req.top_k)
    # shrink payload a bit
    compact = [
        {
            "params": t["params"],
            "score": t["score"],
            "metrics": t["metrics"],
            "trades": len(t.get("trades", [])),
            "final_equity": (t.get("equity") or [None])[-1],
        }
        for t in top
    ]
    return {"top": compact}
