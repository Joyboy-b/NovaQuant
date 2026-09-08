from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict, model_validator
from uuid import UUID
from time import perf_counter
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
from backend.services.research_store import get_research_store
from backend.backtest.native import run_native
from backend.services.telemetry import span, traced

backtest_router = APIRouter(tags=["backtest"])


def _make_ml_momentum_strategy(symbol: str, qty: float):
    try:
        from backend.backtest.strategies.ml_momentum import MLMomentumStrategy
    except ModuleNotFoundError as exc:
        if exc.name == "sklearn":
            raise HTTPException(
                status_code=503,
                detail="ML momentum requires scikit-learn. Install backend requirements to enable it.",
            ) from exc
        raise

    return MLMomentumStrategy(symbol=symbol, qty=qty)


class BacktestRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    engine: Literal['python','cpp'] = 'python'
    dataset_id: Optional[str] = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    symbol: str = Field(default="BTCUSDT", min_length=1)

    data_source: Literal["gbm", "orderbook", "yahoo"] = "gbm"

    # common length / seed
    steps: int = Field(default=500, ge=50, le=20000)
    seed: Optional[int] = None

    # synthetic params
    start_price: float = Field(default=30000.0, gt=0)
    mu: float = Field(default=0.0)
    sigma: float = Field(default=0.02, ge=0, le=0.1)
    spread_bps: float = Field(default=5.0, ge=0)
    vol_bps: float = Field(default=10.0, ge=0)  # orderbook sim volatility

    # yahoo params
    yahoo_symbol: str = Field(default="SPY")
    start: str = Field(default="2024-01-01")  # YYYY-MM-DD
    end: str = Field(default="2025-01-01")    # YYYY-MM-DD
    interval: str = Field(default="1d")

    # strategy params
    strategy: Literal["momentum", "ml_momentum"] = "momentum"
    lookback: int = Field(default=10, ge=2, le=2000)
    qty: float = Field(default=1.0, gt=0)

    # costs
    fee_bps: float = Field(default=1.0, ge=0)
    slippage_bps: float = Field(default=2.0, ge=0, lt=10000)

    @model_validator(mode='after')
    def supported_engine(self):
        if self.engine == 'cpp' and self.strategy != 'momentum':
            raise ValueError('C++ currently supports momentum only')
        return self


class BacktestResponse(BaseModel):
    run_id: str
    dataset_id: str
    engine_version: str
    elapsed_ms: float
    evaluation: Dict[str, Any]
    symbol: str
    equity: List[float]
    trades: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    stats: Dict[str, Any]


@traced('backtest.data')
def _make_quotes(req: BacktestRequest) -> List[Quote]:
    if req.dataset_id:
        stored = get_research_store().dataset(req.dataset_id)
        if stored is None:
            raise HTTPException(404, 'Dataset not found')
        return [Quote(**q) for q in stored['quotes']]
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


def _run_once(req: BacktestRequest, quotes=None) -> Dict[str, Any]:
    quotes = _make_quotes(req) if quotes is None else quotes
    split = 0
    if req.strategy == "ml_momentum":
        strat = _make_ml_momentum_strategy(symbol=req.symbol, qty=req.qty)
        # Fit on the first part of quotes (simple split for single backtest run)
        if len(quotes) < 60:
            raise HTTPException(422, 'ML evaluation requires at least 60 quotes')
        split = min(len(quotes)-1, max(30, int(len(quotes) * 0.6)))
        strat.fit(quotes[:split])
    else:
        strat = MomentumStrategy(symbol=req.symbol, lookback=req.lookback, qty=req.qty)
    cost = BpsCostModel(fee_bps=req.fee_bps, slippage_bps=req.slippage_bps)

    engine = BacktestEngine(symbol=req.symbol, strategy=strat, cost_model=cost)
    with span('backtest.engine', engine=req.engine, quotes=len(quotes)):
        if req.engine == 'cpp':
            out = run_native(quotes,req.symbol,req.lookback,req.qty,req.fee_bps,req.slippage_bps)
        else:
            out = engine.run(quotes, start_index=split)

    with span('backtest.metrics'):
        equity = out["equity"]
        trade_pnls = [equity[i] - equity[i - 1] for i in range(1, len(equity))]
        metrics = compute_metrics(equity, trade_pnls).model_dump()

    # stats on trade_pnls (simple but useful)
    with span('backtest.bootstrap'):
        bootstrap = bootstrap_mean_ci(trade_pnls, seed=req.seed)
    with span('backtest.permutation'):
        permutation = permutation_test_mean_gt_zero(trade_pnls, seed=req.seed)
    stats = {"bootstrap_pnl_mean_ci": bootstrap, "perm_test_mean_gt_zero": permutation}

    return {"equity": equity, "trades": out["trades"], "metrics": metrics, "stats": stats,
            'evaluation':{'training_quotes':split,'evaluation_quotes':len(quotes)-split,
                          'start_index':split,'engine':req.engine}}


@backtest_router.post("/run", response_model=BacktestResponse)
def run_backtest(req: BacktestRequest) -> BacktestResponse:
    start = perf_counter()
    quotes = _make_quotes(req)
    out = _run_once(req, quotes)
    saved = get_research_store().save('backtest',req.model_dump(),quotes,
        {'symbol':req.symbol,**out},(perf_counter()-start)*1000)
    return BacktestResponse(**saved)


@backtest_router.get('/runs')
def list_runs(limit: int=Query(50,ge=1,le=200), offset: int=Query(0,ge=0)):
    return get_research_store().list(limit,offset)


@backtest_router.get('/runs/{run_id}')
def get_run(run_id: UUID):
    result = get_research_store().get(run_id)
    if result is None:
        raise HTTPException(404,'Research run not found')
    return result


@backtest_router.get('/datasets/{dataset_id}')
def get_dataset(dataset_id: str):
    result = get_research_store().dataset(dataset_id)
    if result is None:
        raise HTTPException(404,'Dataset not found')
    return result


class WalkForwardRequest(BacktestRequest):
    train_size: int = Field(default=300, ge=50, le=20000)
    test_size: int = Field(default=100, ge=10, le=20000)


@backtest_router.post("/walkforward")
def run_walkforward(req: WalkForwardRequest):
    if req.engine == 'cpp':
        raise HTTPException(422, 'C++ walk-forward is not supported yet; use engine=python')
    start = perf_counter()
    quotes = _make_quotes(req)

    def factory(train_quotes: List[Quote]):
        if req.strategy == "ml_momentum":
            s = _make_ml_momentum_strategy(symbol=req.symbol, qty=req.qty)
            s.fit(train_quotes)
            return s
        else:
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

    return get_research_store().save('walkforward',req.model_dump(),quotes,
        {"chunks": chunks, "chunk_metrics": chunk_metrics},(perf_counter()-start)*1000)



class SweepRequest(BacktestRequest):
    lookbacks: List[int] = Field(default_factory=lambda: [5, 10, 20, 40])
    fee_bps_list: List[float] = Field(default_factory=lambda: [0.0, 1.0, 2.0])
    slippage_bps_list: List[float] = Field(default_factory=lambda: [0.0, 2.0, 5.0])
    top_k: int = Field(default=10, ge=1, le=50)
    score_key: Literal["sharpe", "sortino", "max_drawdown_pct", "profit_factor", "win_rate"] = "sharpe"


@backtest_router.post("/sweep")
def run_sweep(req: SweepRequest):
    start = perf_counter()
    if not req.lookbacks or not req.fee_bps_list or not req.slippage_bps_list or len(req.lookbacks)*len(req.fee_bps_list)*len(req.slippage_bps_list)>200:
        raise HTTPException(422,'Sweep must contain between 1 and 200 combinations')
    quotes = _make_quotes(req)
    base = req.model_dump()

    grid = {
        "lookback": req.lookbacks,
        "fee_bps": req.fee_bps_list,
        "slippage_bps": req.slippage_bps_list,
    }

    def runner(p: Dict[str, Any]) -> Dict[str, Any]:
        r = BacktestRequest(**{**base, **p})
        out = _run_once(r, quotes)
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
    return get_research_store().save('sweep',req.model_dump(),quotes,
        {"top": compact, 'top_details':top},(perf_counter()-start)*1000)
