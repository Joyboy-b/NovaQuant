# Native adapter buffer optimization

Recorded at 2026-09-08T01:55:19.361001+00:00. This compares the previous C++ adapter with the optimized C++ adapter, not Python versus C++. The C++ kernel and accounting formulas are unchanged.

## Bottleneck and implementation

Profiling the original adapter identified repeated dynamic attribute lookup and per-element ctypes construction during input packing. At 20,000 quotes, the original performs 60,000 getattr calls per run. It also converts the equity ctypes array to a list using Python iteration.

The new implementation fills standard-library array('d') buffers with direct quote attributes, exposes their storage to C++ through ctypes.from_buffer, and uses array.tolist() for equity conversion. Native outputs use the same contiguous buffer approach. Inputs are still copied out of Quote objects once; this is not a zero-copy pipeline from ingestion. Buffer storage is owned locally until the synchronous native call returns, including while ctypes releases the GIL. No global mutable buffer cache or additional dependency was introduced.

## Recorded before and after

| Quotes | Before median ms | After median ms | Runtime reduction | Before p95 ms | After p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.697 | 0.386 | 44.6% | 0.828 | 0.448 |
| 20,000 | 11.747 | 6.025 | 48.7% | 13.971 | 8.797 |
| 100,000 | 59.498 | 31.433 | 47.2% | 66.112 | 34.162 |

Before changing code, the original implementation was saved as scripts/baselines/native_before_buffers.py and a fresh full benchmark was recorded in initial-baseline.json. The main comparison above then alternated that preserved adapter with the new one in the same process, using exactly the same compiled library and inputs. This paired comparison is more controlled than comparing separate historical sessions.

Method: 30 pairs per input size, one warmup per adapter, alternating A/B and B/A order, seed 42, lookback 10, quantity 1, fees 1 bps, slippage 2 bps. Wall-clock timer includes input allocation/packing, the C++ kernel and Python result reconstruction. It excludes data generation, correctness checks, profiling, memory measurements, HTTP and PostgreSQL. Result destruction occurs outside timing for both variants. Full raw samples and source/library SHA-256 fingerprints are in comparison.json. Platform: Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.41, Python 3.12.14, 32 visible logical CPUs; Docker on the same local Ryzen 9 8940HX host as earlier measurements.

All 180 measured outputs across the three workloads matched their original-adapter reference exactly. The full test suite passed 27 tests, including nine Python/C++ parity cases and seven new buffer tests covering empty/small/constant/changing inputs, concurrent calls and invalid quotes. PostgreSQL persistence/replay tests passed. Five existing dependency deprecation warnings remain.

## Tradeoffs and limits

Buffer ownership and pointer views add implementation complexity. Numeric buffers must remain alive and must not be resized during the native call. The 20,000-quote tracemalloc check recorded peak Python-traced allocation of 2,736,638 bytes before and 2,763,480 bytes after (about 1% more). This single allocation check excludes input quotes and is not process RSS or a leak/soak test. Profiling and memory instrumentation were run separately from performance timing.

All runs use one synthetic seed and one strategy configuration; the size matrix does not establish all-workload performance. Thirty samples provide preliminary tail estimates, not p99 guarantees. Python result construction and input packing remain costs. These numbers do not establish API capacity, database throughput or market execution speed.

## Reproduce

From the NovaQuant root in PowerShell, with Docker Desktop running:

```powershell
docker compose --profile test run --rm --build --no-deps -v ./artifacts/buffer-optimization:/app/artifacts test python -m scripts.benchmark_native_buffers
docker compose --profile test run --rm test
```

The benchmark prints before/after medians and refuses to finish if any complete result differs. Its raw report is artifacts/buffer-optimization/comparison.json. The initial preserved baseline file resolves its native library through the current adapter inside the comparison harness, ensuring a shared kernel.

Resume wording supported by this experiment: "Optimized Python-to-C++ buffer conversion, reducing median runtime for a 20,000-quote backtest by 49% (11.75 to 6.02 ms); verified exact results across 180 paired-workload executions."
