"""Shared, untimed workload construction for Docker and native pyperf."""
import hashlib
import json
import os
from pathlib import Path
from backend.backtest import native
from backend.backtest.data import quotes_from_mid_prices
from backend.backtest.synthetic.gbm import generate_gbm_prices

def workload():
    if os.name == 'nt':
        os.environ['NOVAQUANT_BACKTEST_LIBRARY'] = str(Path(__file__).resolve().parents[1]/'build-benchmark/novaquant_backtest.dll')
    quotes = quotes_from_mid_prices(generate_gbm_prices(steps=20000,start=30000,mu=0,sigma=.02,seed=42))
    equity = native.run_native(quotes,'BTCUSDT',10,1,1,2)['equity']
    return [equity[i]-equity[i-1] for i in range(1,len(equity))]

def run_stats(module, values):
    return {'bootstrap':module.bootstrap_mean_ci(values,seed=42),
            'permutation':module.permutation_test_mean_gt_zero(values,seed=42)}

def fingerprint(values):
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()
