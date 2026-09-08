# Verified backend measurements

Latest optimization: [native buffer comparison](buffer-optimization/README.md). The measurements below describe the earlier adapter and are retained as historical evidence.


Measured September 7, 2026. This rerun improves the existing harness with alternating paired runs, nearest-rank percentiles, raw samples, source fingerprints, full equity/trade comparisons and matching-fill validation. It measures the existing C++ kernel and async bridge changes; it is not a new claimed speedup over yesterday's optimized version.

## Backtest: bottleneck, change, measurement, tradeoff

The Python engine performs event-by-event strategy/accounting work with Python objects. The C++ momentum kernel moves this loop into compiled code; the ctypes adapter converts inputs and reconstructs Python results. Both implementations use the corrected fee accounting.

Docker/WSL2 Linux, Python 3.12.14, GCC -O3, 32 visible logical CPUs on Ryzen 9 8940HX. Thirty alternating pairs after warmup, one process/thread, 20,000 synthetic quote events, seed 42, lookback 10, quantity 1, 1 bps fees, 2 bps slippage. Timer includes conversion and output reconstruction; excludes quote generation, HTTP, statistical analysis and database writes.

| Metric | Python | C++ adapter |
| --- | ---: | ---: |
| Median runtime | 22.914 ms | 12.672 ms |
| p95 runtime | 27.402 ms | 14.520 ms |

Median runtime fell 44.7%. Every run matched all equity points and trade fields with rel_tol=1e-12 / abs_tol=1e-8. Both produced 2,789 trades and final equity 999,978.1945909028. Raw samples and SHA-256 source hashes are in [backend-benchmark.json](backend-benchmark.json).

Tradeoff: native build/platform maintenance, an additional implementation to keep equivalent, and remaining Python conversion cost. The C++ kernel supports the long/flat momentum strategy only. This does not establish profitable signals, sweep acceleration, multithreaded routing or a million-order throughput result.

## Bridge: bottleneck, change, measurement, tradeoff

The legacy bridge waited for a 100 ms quiet period after receiving reports. The async bridge routes reports by order ID and resolves a future immediately on its terminal fill. Fifty alternating paired round trips after warmup, one outstanding order per bridge, against the same immediate-fill C++ subprocess stub.

Median 100.390 -> 0.242 ms; p95 100.450 -> 0.349 ms. All calls returned exactly one matching fill. The large reduction removes an artificial polling wait; it is not market/network latency or order-book matching throughput. Small sample counts do not support rare-tail guarantees.

Tradeoff: futures, correlation, cancellation, process failure and late-fill handling add lifecycle complexity. Duplicate-ID tracking is session-scoped and bounded; this stub assumes one terminal fill, not real exchange partial fills.

## Database and correctness

20 tests passed, including nine cross-language parity cases, fees, RNG isolation, held-out ML evaluation, sweep ordering, out-of-order/late fills, PostgreSQL atomic rollback, committed result retrieval and replay from saved quote snapshots. Research inputs/configuration/results persist in PostgreSQL; live order state is still in memory. Database time is intentionally excluded from these microbenchmarks, so do not present them as API or persistence latency. Existing dependency deprecation warnings remain.

## Reproduce

```powershell
docker compose build api
docker compose run --rm --no-deps -v ./artifacts:/app/artifacts api python -m scripts.benchmark_backend
docker compose run --rm -e TEST_DATABASE_URL=postgresql://novaquant:novaquant@db:5432/novaquant api python -m pytest -q -p no:cacheprovider
```

## Resume wording

"Implemented a C++ momentum backtest kernel with a Python adapter, reducing median runtime by 45% on 20,000 quote events (22.91 to 12.67 ms); verified every equity point and trade against the Python baseline."

Optional: "Replaced quiet-period polling with asynchronous per-order completion, reducing median local simulator round-trip time from 100 ms to 0.24 ms."

Remove the unverified 1-million-orders/2.1-seconds/350% and 10,000-sweeps/14.2-to-4.5-minutes/68% claims. The engine stub is single threaded and has no real limit-order book. No employer metrics were validated in this work.
