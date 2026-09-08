"""Paired runtime measurements, raw samples and correctness gates; no market downloads."""
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import time

from backend.api.engine_bridge import EngineBridge as LegacyBridge, default_engine_path
from backend.api.async_engine_bridge import EngineBridge
from backend.backtest.data import quotes_from_mid_prices
from backend.backtest.synthetic.gbm import generate_gbm_prices
from backend.backtest.engine import BacktestEngine
from backend.backtest.strategies.momentum import MomentumStrategy
from backend.backtest.costs import BpsCostModel
from backend.backtest.native import run_native


def summarize(samples):
    ordered=sorted(samples)
    return {'samples':len(samples),'raw_ms':samples,'p50_ms':statistics.median(samples),
            'p95_ms':ordered[math.ceil(len(ordered)*.95)-1],
            'p99_ms':ordered[math.ceil(len(ordered)*.99)-1]}


def equivalent(a,b):
    if isinstance(a,dict):
        assert a.keys()==b.keys()
        for key in a:equivalent(a[key],b[key])
    elif isinstance(a,list):
        assert len(a)==len(b)
        for x,y in zip(a,b):equivalent(x,y)
    elif isinstance(a,(float,int)):
        assert math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-8),(a,b)
    else:assert a==b,(a,b)


def benchmark_backtest():
    quotes=quotes_from_mid_prices(generate_gbm_prices(steps=20000,start=100,mu=0,sigma=.02,seed=42))
    engines={
        'python':lambda:BacktestEngine('X',MomentumStrategy('X',10,1),BpsCostModel(1,2)).run(quotes),
        'cpp_adapter':lambda:run_native(quotes,'X',10,1,1,2)}
    samples={name:[] for name in engines}
    reference=engines['python']();equivalent(reference,engines['cpp_adapter']())
    for pair in range(30):
        for name in (['python','cpp_adapter'] if pair%2==0 else ['cpp_adapter','python']):
            start=time.perf_counter();out=engines[name]();samples[name].append((time.perf_counter()-start)*1000)
            equivalent(reference,out)  # correctness comparison is outside timing
    return {name:{**summarize(values),'final_equity':reference['equity'][-1],
                  'trades':len(reference['trades'])} for name,values in samples.items()}


def order(i):
    return {'order_id':f'bench-{i}','symbol':'X','side':'BUY','qty':1,'px':100}


def verify_fill(reports,message):
    fills=[r for r in reports if r.get('type')=='fill']
    assert len(fills)==1
    for key,value in message.items():assert fills[0][key]==value


async def bridge_latency():
    legacy=LegacyBridge(default_engine_path());legacy.start()
    bridge=EngineBridge(default_engine_path());await bridge.start()
    samples={'legacy':[],'async':[]}
    try:
        legacy.send(order('warmup'));verify_fill(legacy.recv_all(),order('warmup'))
        verify_fill(await bridge.execute(order('warmup')),order('warmup'))
        for i in range(50):
            for variant in (['legacy','async'] if i%2==0 else ['async','legacy']):
                message=order(i);start=time.perf_counter()
                if variant=='legacy':
                    legacy.send(message);reports=legacy.recv_all()
                else:reports=await bridge.execute(message)
                samples[variant].append((time.perf_counter()-start)*1000)
                verify_fill(reports,message)
    finally:
        legacy.stop();await bridge.stop()
    return {name:summarize(values) for name,values in samples.items()}


def main():
    report={'platform':platform.platform(),'python':platform.python_version(),'logical_cpus':os.cpu_count(),
            'workload':{'price_steps':20000,'seed':42,'lookback':10,'qty':1,'fee_bps':1,'slippage_bps':2},
            'method':'Alternating paired runs after warmup; nearest-rank percentiles; raw samples retained',
            'scope':'Backtest includes Python/C++ conversion and result reconstruction, excludes downloads, persistence and statistical analysis. Bridge is local subprocess round-trip to an immediate-fill stub, not exchange latency.',
            'checks':'All equity points and trade fields agree (rel_tol=1e-12, abs_tol=1e-8); every bridge call returns its matching fill.'}
    report['backtest']=benchmark_backtest()
    report['order_bridge']=asyncio.run(bridge_latency())
    root=Path(__file__).resolve().parents[1]
    paths=['engine-cpp/backtest.cpp','engine-cpp/main.cpp','backend/backtest/native.py',
           'backend/backtest/engine.py','backend/api/engine_bridge.py','backend/api/async_engine_bridge.py','scripts/benchmark_backend.py']
    report['source_sha256']={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/backend-benchmark.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
