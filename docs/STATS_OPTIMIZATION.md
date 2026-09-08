# Statistics performance comparison ? September 8, 2026

The new resampling implementation reduced median traced API latency by 53.1% on the measured local workload, with matching research outputs. This baseline already includes the earlier Python/C++ buffer optimization. Only the statistics implementation changes in this comparison; the C++ engine and database persistence remain the same.

| Measurement | Before | After | Time reduction |
|---|---:|---:|---:|
| Docker: statistics functions, median | 951.18 ms | 414.68 ms | 56.4% |
| Native Windows pyperf: statistics functions, mean | 1245.68 ms | 926.57 ms | 25.6% |
| OpenTelemetry: full server request, median | 1479.89 ms | 693.88 ms | 53.1% |
| HTTP client with tracing enabled, median | 1495.05 ms | 709.84 ms | 52.5% |

## Bottleneck, change, and tradeoff

Profiling identified bootstrap and permutation resampling as the dominant costs. Both repeatedly allocated sample matrices. The new implementation reuses eight-row sample buffers, gathers values with NumPy take, multiplies signs in place, preallocates bootstrap means, and counts permutation exceedances incrementally. It retains all 2,000 bootstrap and 5,000 permutation trials. RNG draws and tested outputs match the preserved original implementation exactly.

Peak allocations observed by tracemalloc decreased from 10,460,440 to 4,018,376 bytes (61.6%). This is traced allocation memory, not process RSS. Smaller batches introduce more Python iterations and more explicit buffer management; the measured net benefit depends on input size and environment. These changes do not strengthen the statistical assumptions or establish predictive trading value.

## Method and correctness

Workload: 20,000 synthetic GBM quotes, seed 42, C++ momentum engine, 19,999 adjacent equity differences, bootstrap 2,000 trials and permutation 5,000 trials. Input generation is outside the statistics microbenchmark timing.

Docker: Python 3.12.14, NumPy 2.4.1, Linux under WSL2. One warmup per variant, 20 alternating pairs in one process; output equality checked outside timing. Profiling and memory measurement run separately.

Native pyperf: Windows Python 3.12.10, NumPy 2.4.1, MSVC optimized DLL. Ten worker processes per variant, 30 measured timing values per variant, plus calibration and warmups. Standard deviations were 181 ms before (15%) and 122 ms after (13%); pyperf explicitly warned both results may be unstable. Retain those warnings; these are local measurements, not precise production guarantees.

OpenTelemetry: two Docker API services using current C++ adapter and old/new statistics, shared local PostgreSQL, tracing enabled in both. Two warmups per variant, 20 alternating pairs, one outstanding request. Compared complete equity, trades, metrics, statistics, evaluation and dataset identity for every response. All matched. Verified eight expected spans in every measured trace and different variant provenance. Jaeger queries occur after timing. The first collection attempt encountered incomplete asynchronous trace export; the collector now waits for all expected phases, and the complete run was repeated. Exported JSON preserves evidence beyond Jaeger's in-memory lifetime.

69 tests passed, including seeded old/new statistics equality, edge cases, C++ parity, accounting and database replay. The existing unrelated backend/requirements.txt trailing blank line remains reported by git diff --check.

## What the spans show

| Phase median | Before | After |
|---|---:|---:|
| Bootstrap | 360.71 ms | 119.79 ms |
| Permutation | 863.46 ms | 311.98 ms |
| Engine | 6.45 ms | 6.78 ms |
| Persistence, including serialization | 147.98 ms | 154.58 ms |
| Database transaction (inside persistence) | 82.93 ms | 83.14 ms |

Parent and child spans overlap: do not sum them. The unchanged engine and database did not improve in this run. Persistence is now a larger fraction of total latency and is a candidate for a separate profile-driven change.

Docker is an execution environment, pyperf a benchmark harness, and OpenTelemetry instrumentation. Their absolute times are not interchangeable: the OTel row includes HTTP processing and persistence, while the first two time only statistics. Windows and Linux input fingerprints differ despite the same generation recipe; each before/after pair uses identical inputs within its environment. OS, compiler, process scheduling and instrumentation also differ. No benchmark suites ran concurrently. These sequential requests do not measure concurrent throughput or reliable tail latency. Older adapter-only measurements in docs/trace-comparison belong to a different experiment and should not be combined into a cumulative speedup.

## Reproduce from the NovaQuant directory

Preserve existing result files before rerunning; pyperf refuses to overwrite its JSON output.

```powershell
# Docker statistics benchmark (writes artifacts/stats-optimization/docker.json)
docker compose -f compose.yaml -f compose.telemetry.yaml run --rm --no-deps -v "${PWD}/artifacts:/app/artifacts" api python -m scripts.benchmark_stats

# Native setup, if needed
py -3.12 -m venv .venv-bench
.\.venv-bench\Scripts\python.exe -m pip install -r requirements-benchmark.txt
cmd /c scripts\build_benchmark_windows.cmd

# Use fresh output names for each experiment
.\.venv-bench\Scripts\python.exe scripts/benchmark_stats_pyperf.py --variant before --processes 10 -o artifacts/stats-before-new.json
.\.venv-bench\Scripts\python.exe scripts/benchmark_stats_pyperf.py --variant after --processes 10 -o artifacts/stats-after-new.json
.\.venv-bench\Scripts\python.exe -m pyperf compare_to artifacts/stats-before-new.json artifacts/stats-after-new.json --table
.\.venv-bench\Scripts\python.exe -m pyperf check artifacts/stats-before-new.json artifacts/stats-after-new.json

# Full API with exported traces
 docker compose -f compose.yaml -f compose.telemetry.yaml -f compose.compare.yaml -f compose.stats.yaml up -d --build before-api after-api
python scripts/compare_traces.py --comparison stats --service-prefix novaquant-stats

# Correctness suite
docker compose --profile test run --rm test
```

Open http://localhost:16686 and select novaquant-stats-before or novaquant-stats-after. Each comparison prints direct trace links and writes a timestamped artifact directory.

Raw samples, pyperf stability warnings, profiles, source hashes and all verified trace JSON are preserved in [stats-optimization](stats-optimization/). Full phase ranges and request identifiers are in [the trace report](stats-optimization/traces/comparison.json).
