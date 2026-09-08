"""Host-native pyperf comparison of original and optimized Python/C++ adapters."""
import hashlib
import os
from pathlib import Path
import sys
import time
import pyperf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.backtest import native
from backend.backtest.data import quotes_from_mid_prices
from backend.backtest.synthetic.gbm import generate_gbm_prices
from scripts.baselines import native_before_buffers as baseline


def worker_args(cmd, args):
    cmd.extend(['--adapter', args.adapter, '--library', str(args.library)])


def measure(loops, run, quotes):
    start = time.perf_counter()
    for _ in range(loops):
        run(quotes, 'X', 10, 1, 1, 2)
    return time.perf_counter() - start


def main():
    runner = pyperf.Runner(add_cmdline_args=worker_args)
    runner.argparser.add_argument('--adapter', choices=['before', 'after'], required=True)
    runner.argparser.add_argument('--library', type=Path, default=ROOT/'build-benchmark/novaquant_backtest.dll')
    args = runner.parse_args()
    args.library = args.library.resolve(strict=True)
    os.environ['NOVAQUANT_BACKTEST_LIBRARY'] = str(args.library)
    baseline.library = native.library
    run = baseline.run_native if args.adapter == 'before' else native.run_native
    runner.metadata.update({
        'adapter': args.adapter,
        'native_library_sha256': hashlib.sha256(args.library.read_bytes()).hexdigest(),
        'baseline_sha256': hashlib.sha256((ROOT/'scripts/baselines/native_before_buffers.py').read_bytes()).hexdigest(),
        'optimized_sha256': hashlib.sha256((ROOT/'backend/backtest/native.py').read_bytes()).hexdigest(),
        'benchmark_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope': 'Input packing, native kernel, output construction and result disposal; excludes input generation, correctness checks, HTTP, database and DLL loading',
        'configuration': 'seed=42,lookback=10,qty=1,fee_bps=1,slippage_bps=2',
        'correctness': 'Exact baseline/new equality before timing in every worker',
    })
    for steps in [1000, 20000, 100000]:
        quotes = quotes_from_mid_prices(generate_gbm_prices(steps=steps, start=100, mu=0, sigma=.02, seed=42))
        if native.run_native(quotes, 'X', 10, 1, 1, 2) != baseline.run_native(quotes, 'X', 10, 1, 1, 2):
            raise RuntimeError('Before/after outputs differ')
        runner.bench_time_func(f'native_adapter_{steps}_quotes', measure, run, quotes)


if __name__ == '__main__':
    main()
