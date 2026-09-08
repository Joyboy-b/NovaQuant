# Native Windows benchmark with pyperf

Recorded September 8, 2026. This benchmark was executed directly by Windows CPython 3.12.10 with a native x64 MSVC 19.50 Release DLL (/O2 /fp:precise). Docker did not execute the benchmark or compile this DLL. Existing background services were not stopped; the host was not CPU-isolated or tuned.

pyperf 2.10.0 is a Python Software Foundation benchmarking toolkit with calibrated loops, fresh worker processes, distribution statistics and stability diagnostics. It is appropriate for this Python-to-C++ adapter optimization. Google Benchmark would be appropriate for isolating changes inside the C++ kernel, but the kernel itself did not change here.

Official documentation: https://pyperf.readthedocs.io/ and https://github.com/psf/pyperf

## Results

Numbers below are pyperf means +/- standard deviations, in milliseconds, not the medians from the previous custom harness.

| Workload | Before ms | After ms | Mean runtime reduction |
| --- | ---: | ---: | ---: |
| native_adapter_1000_quotes | 0.623 +/- 0.064 | 0.316 +/- 0.017 | 49.3% |
| native_adapter_20000_quotes | 13.084 +/- 1.485 | 6.640 +/- 0.436 | 49.3% |
| native_adapter_100000_quotes | 69.913 +/- 10.463 | 36.802 +/- 3.010 | 47.4% |

See [raw before](pyperf-native/before.json), [raw after](pyperf-native/after.json), [tool comparison](pyperf-native/comparison.txt), and [stability diagnostics](pyperf-native/stability.txt). pyperf compare_to reports all three changes as faster, approximately 1.90-1.97x. These are exploratory host-native results, not production latency guarantees.

## Method and scope

Each variant uses pyperf defaults: 20 measured worker processes per workload, three measured values per worker, one warmup value, automatically calibrated loops with a minimum time budget of 0.1 seconds. Calibration runs are additional. Each value is normalized time per call across multiple loop iterations; these are not individual HTTP-request tail latencies.

The before adapter is the preserved scripts/baselines/native_before_buffers.py; after is backend/backtest/native.py. Both use exactly the same MSVC-built DLL. Input sizes are 1,000, 20,000 and 100,000 quotes, seed 42, lookback 10, quantity 1, fee 1 bps and slippage 2 bps. Every worker checks exact before/after output equivalence before measurement. A separate native Windows check verified a hand-calculated fee/equity case and empty inputs. No Python API dependencies or database are needed for this benchmark.

Timing covers input packing, native calculation, output construction, and disposal of each output. It excludes generated inputs, correctness comparisons, DLL loading, HTTP, PostgreSQL and interpreter startup. This differs from the earlier custom harness, which excluded output disposal. Compiler, OS and measurement statistic also changed, so compare before and after within this experiment rather than subtracting Windows values from Docker values. Source/DLL hashes, Python version and machine metadata are saved in pyperf JSON.

Before ran first, followed by after; thus thermal state and system drift are limitations. pyperf flagged instability for all workloads: baseline standard deviations were about 10-15% of means, and optimized runs did not meet its stringent sample sufficiency check for 1% precision. Preserve those warnings. The measured difference is large, but exact timings and percentages need repeated sessions on an idle host. The wrapper supports -ReverseOrder for a second independent session; retain both sessions, not just the faster one. Do not claim stable p99 from these batch averages.

## Setup (already completed on this machine)

From the NovaQuant root in PowerShell:

```powershell
python -m venv .venv-bench
.\.venv-bench\Scripts\python.exe -m pip install -r requirements-benchmark.txt
cmd /c scripts\build_benchmark_windows.cmd
```

The build script finds an installed Visual Studio C++ toolchain and builds a separate benchmark DLL. It does not replace the app's normal build-engine files. No global Python packages or system performance settings are changed.

## Repeat the complete experiment

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pyperf.ps1
```

ExecutionPolicy Bypass applies only to this child PowerShell process. The wrapper builds the DLL, runs before and after, compares results, and records stability warnings in a new timestamped artifacts/pyperf-native-* directory. A second independent run can use -ReverseOrder. Keep the laptop plugged in and avoid other heavy work during measurement; do not run competing benchmarks simultaneously.

## Individual commands

```powershell
.\.venv-bench\Scripts\python.exe scripts/benchmark_pyperf.py --adapter before -o artifacts/before-native-rerun.json
.\.venv-bench\Scripts\python.exe scripts/benchmark_pyperf.py --adapter after -o artifacts/after-native-rerun.json
.\.venv-bench\Scripts\python.exe -m pyperf compare_to artifacts/before-native-rerun.json artifacts/after-native-rerun.json --table
.\.venv-bench\Scripts\python.exe -m pyperf check artifacts/before-native-rerun.json artifacts/after-native-rerun.json
```

Choose unused output filenames for later runs; pyperf refuses to overwrite existing results. --rigorous can collect more samples, but it does not remove systematic drift or host contention.
