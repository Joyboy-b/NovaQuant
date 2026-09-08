# Running pyperf and OpenTelemetry yourself

## 1. Controlled adapter benchmarks with pyperf

From PowerShell:

```powershell
cd C:\Users\hideo\OneDrive\Desktop\NovaQuant
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pyperf.ps1
```

The environment and native build tooling are already set up on this machine. The child PowerShell policy override applies only to that process. Docker is not required for this benchmark. The script builds a Windows C++ DLL, tests the preserved and optimized adapters with pyperf, prints comparison/stability output, and creates a new artifacts/pyperf-native-TIMESTAMP directory. Both variants must use the same DLL, inputs and machine settings. Avoid simultaneous load tests or heavy background work. A later session can use -ReverseOrder; retain both sessions and all warnings.

Read the before/after means, standard deviations and speed ratio. pyperf batch averages are not individual HTTP p95/p99 measurements. Instability warnings indicate that exact timings need more controlled repeat sessions. See [native benchmark setup and recorded evidence](PYPERF_NATIVE.md).

## 2. API tracing with OpenTelemetry and Jaeger

OpenTelemetry observes the real request path. Jaeger displays the traces. This setup exports traces only, not a metrics dashboard or load generator. It uses Docker for the API, PostgreSQL and Jaeger; it does not change the host-native pyperf benchmark.

Open Docker Desktop, then run:

```powershell
cd C:\Users\hideo\OneDrive\Desktop\NovaQuant
docker compose -f compose.yaml -f compose.telemetry.yaml up -d --build
python scripts/trace_demo.py
```

Open http://localhost:16686 . Select service novaquant-api, choose operation POST /backtest/run, and click Find Traces. Alternatively, the demo prints a direct link to each trace. New browser backtests also produce traces. SDK batching may delay display by a few seconds.

The demo sends one Python and one C++ request with 1,000 synthetic quotes and seed 42. Both runs are saved in the research database. It supplies trace IDs, checks that Jaeger received every required phase, checks equivalent equity/trades, and saves a diagnostic summary in artifacts/telemetry/demo.json. This is a smoke test with two requests, not a performance comparison suitable for a resume percentage. To inspect a larger request, use python scripts/trace_demo.py --steps 20000 (the API limit).

## 3. Reading the timeline

| Span | What it includes |
| --- | --- |
| POST /backtest/run | Server handling through response transmission; excludes the client's network path |
| backtest.data | Generate synthetic quotes or retrieve a saved dataset |
| backtest.engine | Python engine or C++ adapter including input/output conversion |
| backtest.metrics | Equity differences and financial metrics |
| backtest.bootstrap | Bootstrap calculation |
| backtest.permutation | Permutation calculation |
| research.persist | Prepare/hash the snapshot, fingerprint source, and persist the result |
| research.transaction | Acquire a pooled connection, execute inserts and commit |

research.transaction is a child of research.persist. Do not add their times together: the parent's duration already includes the child. Client response time is measured separately and includes the network and full response read. The existing API elapsed_ms field stops before persistence, so it is not full request latency. Uninstrumented work such as strategy setup, validation and serialization appears in the server span rather than a dedicated phase.

The demo trace on September 8, 2026 showed the C++ engine phase at about 0.71 ms, permutation work at 21.15 ms and persistence at 12.17 ms. This suggests where to investigate next for this workload; these single-request observations are not statistical benchmarks. See [recorded demo](telemetry-demo.json). Jaeger's current local trace storage is in memory and is lost on restart; research results remain in PostgreSQL.

## 4. Trace configuration and correctness

Tracing is disabled unless NOVAQUANT_TELEMETRY_ENABLED=true. compose.telemetry.yaml enables it and points OTLP/HTTP at the local Jaeger service. The SDK sends bounded batches in the background, with a two-second export timeout, and flushes on graceful application shutdown. Each API has one configured provider. The default local demo records all traces; instrumenting production traffic would require appropriate sampling and storage policies. We record engine/count attributes, not full input/output payloads or credentials.

The engine and standalone adapter have no OpenTelemetry imports, so pyperf's code path is unchanged. API instrumentation adds some overhead; keep its settings consistent when comparing full-request measurements. OpenTelemetry spans show elapsed time, not necessarily CPU time; profile a slow phase to explain why it is slow.

30 tests passed, including new tests for disabled mode, exported span hierarchy through API worker threads and database commit, and exception recording. Existing accounting, C++ parity, concurrency and persistence tests continue to pass. Both real demo traces were received by Jaeger with all eight expected span names and matching results. Existing dependency deprecation warnings remain.

To run all tests with the tracing dependencies installed in the image:

```powershell
docker compose -f compose.yaml -f compose.telemetry.yaml run --rm -e TEST_DATABASE_URL=postgresql://novaquant:novaquant@db:5432/novaquant api python -m pytest -q -p no:cacheprovider
```

To return the API to tracing-disabled configuration:

```powershell
docker compose -f compose.yaml up -d api
```

To stop this local stack while retaining PostgreSQL's named data volume:

```powershell
docker compose -f compose.yaml -f compose.telemetry.yaml down
```

## References

- [pyperf documentation](https://pyperf.readthedocs.io/)
- [OpenTelemetry Python exporters](https://opentelemetry.io/docs/languages/python/exporters/)
- [FastAPI instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html)
- [Jaeger getting started](https://www.jaegertracing.io/docs/2.20/getting-started/)


For an actual original-versus-optimized traced API comparison, see [the comparison guide](trace-comparison/README.md).
