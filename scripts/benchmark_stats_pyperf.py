"""pyperf measures the same statistics workload as benchmark_stats.py, on the host."""
from pathlib import Path
import sys
import pyperf
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.backtest import stats
from scripts.baselines import stats_before_resampling as baseline
from scripts.stats_workload import workload,run_stats,fingerprint

def add_args(cmd,args):cmd.extend(['--variant',args.variant])

def main():
    runner=pyperf.Runner(add_cmdline_args=add_args)
    runner.argparser.add_argument('--variant',choices=['before','after'],required=True)
    args=runner.parse_args()
    values=workload()
    assert run_stats(baseline,values)==run_stats(stats,values)
    runner.metadata.update({'variant':args.variant,'numpy':np.__version__,'input_sha256':fingerprint(values),'input_count':len(values),
        'scope':'Bootstrap 2000 and permutation 5000; seed42; excludes workload creation, tracing, HTTP and persistence.'})
    runner.bench_func('research_statistics_20000_quotes',run_stats,baseline if args.variant=='before' else stats,values)

if __name__=='__main__':main()
