import asyncio
import random
from concurrent.futures import ThreadPoolExecutor
import pytest
from backend.backtest.data import quotes_from_mid_prices
from backend.backtest.engine import BacktestEngine
from backend.backtest.costs import BpsCostModel
from backend.backtest.strategies.momentum import MomentumStrategy
from backend.backtest.synthetic.gbm import generate_gbm_prices
from backend.backtest.native import run_native
from backend.backtest.sweeps import grid_sweep


def test_fees_reduce_cash_and_equity():
    quotes = quotes_from_mid_prices([100,101,102,99],spread_bps=0)
    out = BacktestEngine('X',MomentumStrategy('X',2,1),BpsCostModel(100,0)).run(quotes)
    assert out['equity'][-1] == pytest.approx(1000000-3-1.02-.99)
    assert sum(t['fee'] for t in out['trades']) == pytest.approx(2.01)


@pytest.mark.parametrize('seed',[1,42,100])
@pytest.mark.parametrize('fee,slip,qty',[(0,0,1),(5,3,2.5),(20,10,.25)])
def test_cpp_matches_python_every_equity_point_and_trade(seed,fee,slip,qty):
    quotes=quotes_from_mid_prices(generate_gbm_prices(steps=1000,start=100,mu=0,sigma=.02,seed=seed))
    expected=BacktestEngine('X',MomentumStrategy('X',10,qty),BpsCostModel(fee,slip)).run(quotes)
    actual=run_native(quotes,'X',10,qty,fee,slip)
    assert actual['equity'] == pytest.approx(expected['equity'],rel=1e-12,abs=1e-8)
    assert len(actual['trades']) == len(expected['trades'])
    for a,b in zip(actual['trades'],expected['trades']):
        assert a['side']==b['side'] and a['i']==b['i'] and a['symbol']==b['symbol']
        for key in ('qty','px','fee','mid','bid','ask'):
            assert a[key]==pytest.approx(b[key],rel=1e-12)


def test_seed_does_not_modify_global_rng_and_is_concurrent_safe():
    random.seed(7)
    state=random.getstate()
    def generate(seed):
        return generate_gbm_prices(steps=100,start=100,mu=0,sigma=.02,seed=seed)
    expected=[generate(i) for i in range(8)]
    with ThreadPoolExecutor(8) as pool:
        assert list(pool.map(generate,range(8)))==expected
    assert random.getstate()==state


def test_ml_evaluates_only_holdout(monkeypatch):
    import backend.api.backtest_api as api
    trained=[]
    class FakeML:
        def fit(self,quotes): trained.extend(q.i for q in quotes)
        def target_position(self,i,quotes):
            assert i>max(trained)
            return 1
    monkeypatch.setattr(api,'_make_ml_momentum_strategy',lambda **kwargs:FakeML())
    out=api._run_once(api.BacktestRequest(steps=100,strategy='ml_momentum',seed=1))
    assert trained==list(range(60))
    assert len(out['equity'])==40
    assert all(t['i']>=60 for t in out['trades'])


def test_single_class_ml_training_is_safe():
    from backend.backtest.strategies.ml_momentum import MLMomentumStrategy
    strategy=MLMomentumStrategy('X')
    strategy.fit(quotes_from_mid_prices(range(100,200)))
    assert not strategy.is_fit


def test_sweep_zero_score_and_drawdown_direction():
    for key,expected in [('sharpe',[2,0,-1]),('max_drawdown_pct',[-1,0,2])]:
        results=grid_sweep(param_grid={'x':[0,-1,2]},runner=lambda p:{'metrics':{key:p['x']}},score_key=key)
        assert [r['score'] for r in results]==expected


def test_live_tick_callback_accepts_stream_contract():
    from backend.api.app import _on_market_tick, PORTFOLIO, SESSION_STATE
    from backend.config import SETTINGS
    PORTFOLIO.reset();SESSION_STATE.reset()
    _on_market_tick(100,99,101)
    assert PORTFOLIO.marks[SETTINGS.binance_symbol]==100
    assert len(SESSION_STATE.equity)==2
