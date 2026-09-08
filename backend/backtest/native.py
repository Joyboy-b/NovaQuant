"""ctypes releases the GIL while the C++ kernel runs; conversion stays in Python."""
import ctypes as c
from array import array
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
    # Own buffers locally for the entire native call. from_buffer shares their
    # storage instead of converting each element through a ctypes constructor.
    inputs = [array('d', (q.mid for q in quotes)),
              array('d', (q.bid for q in quotes)),
              array('d', (q.ask for q in quotes))]
    outputs = [array('d', [0.0]) * n for _ in range(4)]
    view = c.c_double * n
    mid, bid, ask = (view.from_buffer(values) for values in inputs)
    equity, deltas, prices, fees = (view.from_buffer(values) for values in outputs)
    code = library().momentum_backtest(mid,bid,ask,n,lookback,qty,fee_bps,slippage_bps,
                                     equity,deltas,prices,fees)
    if code:
        raise ValueError(f'C++ kernel rejected input or non-finite result (code {code})')
    equity_values, deltas, prices, fees = outputs
    trades = [{'i':q.i,'symbol':symbol,'side':'BUY' if deltas[i]>0 else 'SELL',
               'qty':abs(deltas[i]),'px':prices[i],'mid':q.mid,'bid':q.bid,'ask':q.ask,'fee':fees[i]}
              for i,q in enumerate(quotes) if deltas[i]]
    return {'equity':equity_values.tolist(),'trades':trades}
