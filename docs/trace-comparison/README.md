# Before/after comparison with OpenTelemetry

This compares the preserved C++ adapter with the optimized C++ adapter inside real API requests. It does not compare Python with C++ and does not replay old measurements as traces.

## Run it yourself

Open Docker Desktop. In PowerShell:

```powershell
cd C:\Users\hideo\OneDrive\Desktop\NovaQuant
docker compose -f compose.yaml -f compose.telemetry.yaml -f compose.compare.yaml up -d --build before-api after-api
python scripts/compare_traces.py
```

The script waits for startup, warms up both variants twice, sends 20 alternating request pairs, verifies complete research output equality and implementation fingerprints, and retrieves all traces from Jaeger. Each request uses 20,000 synthetic quotes with seed 42 and engine=cpp. The requests save results to PostgreSQL. Each session saves raw traces and comparison.json in a new artifacts/telemetry/comparison-TIMESTAMP folder. For a quick smoke check, use `python scripts/compare_traces.py --pairs 3 --steps 1000`; it is not equivalent to the recorded workload.

Open http://localhost:16686 . Select service `novaquant-before`, operation `POST /backtest/run`, and click Find Traces. Repeat in another browser tab with `novaquant-after`. The script also prints direct example trace links. Inspect `backtest.engine` for the adapter change and the server span for the full request. The original API remains on port 8001; comparison services use 8002 and 8003. No request-controlled production switch is added: the original adapter is selected only in the dedicated comparison process entry point.

## Recorded result

September 8, 2026: two warmups each, 20 alternating pairs, 40 measured requests; one outstanding request at a time. Tracing is enabled identically for both processes. Querying Jaeger happens after all requests finish. All complete research output hashes matched, all traces contained the required stages, and saved implementation fingerprints distinguish the two adapters. Both service images had identical filesystem layers; SHA-256 checks independently confirmed the same C++ DLL, statistics module and comparison entry point. Image configuration IDs differed, but runtime files/dependencies matched.

Median durations in milliseconds:

| Measurement | Before | After |
| --- | ---: | ---: |
| client_ms | 1192.53 | 1454.57 |
| POST /backtest/run | 1174.90 | 1432.60 |
| backtest.data | 25.23 | 26.34 |
| backtest.engine | 11.88 | 6.26 |
| backtest.metrics | 17.90 | 18.44 |
| backtest.bootstrap | 269.10 | 346.14 |
| backtest.permutation | 656.68 | 861.01 |
| research.persist | 168.94 | 163.28 |
| research.transaction | 85.86 | 81.79 |

The engine span improved by 47.3% (11.88 to 6.26 ms). The full server request was 21.9% slower in this session (1,174.90 to 1,432.60 ms). Do not claim an end-to-end API speedup from this run. Bootstrap and permutation phases took longer in the after service despite unchanged source, dependencies and identical results. The experiment does not identify why: process placement, allocation/cache state and host contention remain possible explanations, not established causes.

The engine saved about 5.6 ms, less than 0.5% of the baseline whole-request median. Statistical work and persistence dominate this workload. A microbenchmark win need not produce a measurable whole-request win. These phase medians are calculated independently, so their sum need not equal median request duration. `research.transaction` is nested inside `research.persist` and must not be added to it.

The raw summary includes each request's durations and ranges. The baseline server span ranged from 671 to 1,685 ms; the optimized server span ranged from 1,120 to 1,871 ms. This is a small, single-client local diagnostic experiment with tracing overhead, shared PostgreSQL and two separate service processes. It is not a load/capacity test, stable p99 estimate or a causal explanation of the total-latency difference. A follow-up should repeat sessions and swap process assignments to distinguish adapter effects from process/environment effects; retain all sessions rather than selecting the best.

## Evidence

- [All 40 measurements, source fingerprints and trace IDs](comparison.json)
- [Before example trace](before-example-trace.json)
- [After example trace](after-example-trace.json)

All raw Jaeger traces also remain in the timestamped artifacts folder. Jaeger stores this local demo in memory, so the live UI links stop working after its restart; saved JSON remains available. Existing application tests were not rerun because this addition changes only dedicated comparison entry points, Compose services and the harness. The real API experiment itself checked exact returned data, trace service identity, required stages and distinct provenance.

## Stop just the comparison services

```powershell
docker compose -f compose.yaml -f compose.telemetry.yaml -f compose.compare.yaml stop before-api after-api
```

## Observe your normal application

```powershell
docker compose -f compose.yaml -f compose.telemetry.yaml up -d --build api
python scripts/trace_demo.py
```

Choose `novaquant-api` in Jaeger for the normal application. OpenTelemetry records the timeline; the scripts generate requests and calculate comparisons. For the separate Windows-native pyperf benchmark, use the instructions in ../PYPERF_NATIVE.md; do not compare its timings directly with these traced Docker API requests.
