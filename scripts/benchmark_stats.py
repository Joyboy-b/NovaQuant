"""Alternating before/after statistics timings in Docker, with preserved source."""
import cProfile
from datetime import datetime, timezone
import json
import platform
from pathlib import Path
import pstats
import statistics
import time
import tracemalloc
import numpy as np
from backend.backtest import stats
from scripts.baselines import stats_before_resampling as baseline
from scripts.stats_workload import workload, run_stats, fingerprint

def main():
    values = workload()
    expected = run_stats(baseline,values)
    assert run_stats(stats,values)==expected
    samples = {'before':[],'after':[]}
    for pair in range(20):
        for name in (['before','after'] if pair%2==0 else ['after','before']):
            module = baseline if name=='before' else stats
            start = time.perf_counter()
            result = run_stats(module,values)
            samples[name].append((time.perf_counter()-start)*1000)
            assert result==expected
        print(f'Pair {pair+1}/20',flush=True)
    destination=Path('artifacts/stats-optimization')
    destination.mkdir(parents=True,exist_ok=True)
    peaks={}
    for name,module in [('before',baseline),('after',stats)]:
        tracemalloc.start();run_stats(module,values)
        peaks[name]=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
        profile=cProfile.Profile();profile.runcall(run_stats,module,values)
        with (destination/f'profile-{name}.txt').open('w') as stream:pstats.Stats(profile,stream=stream).sort_stats('cumulative').print_stats(20)
    medians={name:statistics.median(x) for name,x in samples.items()}
    report={'timestamp':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),'numpy':np.__version__,
            'input_count':len(values),'input_sha256':fingerprint(values),'pairs':20,'samples_ms':samples,'median_ms':medians,
            'runtime_reduction_pct':100*(1-medians['after']/medians['before']),'peak_traced_bytes':peaks,'output':expected,
            'scope':'Bootstrap(2000) plus permutation(5000), seed42. Input generation, tracing, profiling, memory measurement, HTTP and persistence excluded.'}
    (destination/'docker.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
