"""Compare the preserved ctypes-copy adapter with the buffer adapter in paired runs."""
import cProfile
import hashlib
import json
import os
from pathlib import Path
import platform
import pstats
import statistics
import time
import tracemalloc
from datetime import datetime, timezone
from backend.backtest import native
from backend.backtest.data import quotes_from_mid_prices
from backend.backtest.synthetic.gbm import generate_gbm_prices
from scripts.baselines import native_before_buffers as baseline
from scripts.benchmark_backend import equivalent, summarize


def main():
    baseline.library = native.library  # Same compiled kernel for both adapters.
    destination = Path('artifacts')
    destination.mkdir(exist_ok=True)
    report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'platform': platform.platform(), 'python': platform.python_version(),
              'logical_cpus': os.cpu_count(), 'pairs_per_workload': 30,
              'scope': 'Complete native adapter including input packing, C++ kernel, and output reconstruction. Excludes quote generation, correctness comparisons, HTTP, database, profiling and memory measurements.',
              'method': 'One warmup each; alternate before/after order; identical immutable quotes; exact before/after output equality on every run.',
              'workloads': []}
    for steps in [1000, 20000, 100000]:
        quotes = quotes_from_mid_prices(generate_gbm_prices(steps=steps, start=100, mu=0, sigma=.02, seed=42))
        variants = {'before': baseline.run_native, 'after': native.run_native}
        reference = baseline.run_native(quotes, 'X', 10, 1, 1, 2)
        assert native.run_native(quotes, 'X', 10, 1, 1, 2) == reference
        samples = {name: [] for name in variants}
        for pair in range(30):
            for name in (['before', 'after'] if pair % 2 == 0 else ['after', 'before']):
                start = time.perf_counter()
                output = variants[name](quotes, 'X', 10, 1, 1, 2)
                elapsed = (time.perf_counter()-start)*1000
                samples[name].append(elapsed)
                assert output == reference
                del output  # Do not charge destruction of the previous result to the next variant.
        result = {'quotes': steps, 'seed': 42, 'lookback': 10, 'qty': 1, 'fee_bps': 1, 'slippage_bps': 2,
                  'measurements': {name: summarize(values) for name, values in samples.items()},
                  'trades': len(reference['trades']),
                  'output_sha256': hashlib.sha256(json.dumps(reference,sort_keys=True).encode()).hexdigest()}
        result['median_reduction_pct'] = 100*(1-statistics.median(samples['after'])/statistics.median(samples['before']))
        if steps == 20000:
            result['python_traced_peak_bytes'] = {}
            for name, run in variants.items():
                tracemalloc.start()
                output = run(quotes, 'X', 10, 1, 1, 2)
                result['python_traced_peak_bytes'][name] = tracemalloc.get_traced_memory()[1]
                tracemalloc.stop()
                del output
                profile = cProfile.Profile()
                profile.runcall(run, quotes, 'X', 10, 1, 1, 2)
                with (destination/f'profile-{name}.txt').open('w') as stream:
                    pstats.Stats(profile,stream=stream).sort_stats('cumulative').print_stats(20)
        report['workloads'].append(result)
        print(json.dumps({'quotes':steps,'median_ms':{name:statistics.median(values) for name,values in samples.items()},'reduction_pct':result['median_reduction_pct']}),flush=True)
    paths = ['backend/backtest/native.py','scripts/baselines/native_before_buffers.py','scripts/benchmark_native_buffers.py','engine-cpp/backtest.cpp','build-engine/libnovaquant_backtest.so']
    report['source_sha256'] = {path:hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths}
    (destination/'comparison.json').write_text(json.dumps(report,indent=2))
    print('All before/after outputs matched exactly. Saved artifacts/comparison.json')


if __name__ == '__main__':
    main()
