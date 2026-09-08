"""ctypes releases the GIL while the C++ kernel runs; conversion stays in Python."""
import ctypes as c
from functools import lru_cache
from pathlib import Path
import os


@lru_cache(maxsize=1)
def library():
    root = Path(__file__).resolve().parents[2] / 'build-engine'
    paths = [Path(os.environ['NOVAQUANT_BACKTEST_LIBRARY'])] if os.getenv('NOVAQUANT_BACKTEST_LIBRARY') else [
        root/'libnovaquant_backtest.so', root/'libnovaquant_backtest.dylib',
        root/'Release/novaquant_backtest.dll', root/'novaquant_backtest.dll']
    path = next((p for p in paths if p.exists()), None)
    if path is None:
        raise RuntimeError('C++ backtest library missing; build with CMake or use engine=python')
    lib = c.CDLL(str(path))
    pointer = c.POINTER(c.c_double)
    lib.momentum_backtest.argtypes = [pointer,pointer,pointer,c.c_size_t,c.c_size_t,
        c.c_double,c.c_double,c.c_double,pointer,pointer,pointer,pointer]
    lib.momentum_backtest.restype = c.c_int
    return lib


def run_native(quotes, symbol, lookback, qty, fee_bps, slippage_bps):
    n = len(quotes)
    array = c.c_double * n
    mid, bid, ask = (array(*(getattr(q,k) for q in quotes)) for k in ('mid','bid','ask'))
    equity, deltas, prices, fees = (array() for _ in range(4))
    code = library().momentum_backtest(mid,bid,ask,n,lookback,qty,fee_bps,slippage_bps,
                                     equity,deltas,prices,fees)
    if code:
        raise ValueError(f'C++ kernel rejected input or non-finite result (code {code})')
    trades = [{'i':q.i,'symbol':symbol,'side':'BUY' if deltas[i]>0 else 'SELL',
               'qty':abs(deltas[i]),'px':prices[i],'mid':q.mid,'bid':q.bid,'ask':q.ask,'fee':fees[i]}
              for i,q in enumerate(quotes) if deltas[i]]
    return {'equity':list(equity),'trades':trades}
