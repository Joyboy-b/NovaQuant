# Backend and research persistence

NovaQuant now has a fee-aware Python reference backtester, a C++ momentum kernel, asynchronous order/report transport, and PostgreSQL research storage. The order executable is still an immediate-fill simulator, not a matching engine.

## Run

From the NovaQuant directory:

```powershell
docker compose up -d --build
```

API: http://localhost:8001/docs. PostgreSQL: loopback port 55433. The separate Backtest Relay application remains on port 8000 with its own database on port 55432.

Start the frontend with `npm run dev` from `frontend`. Its default API URL is now http://127.0.0.1:8001. Override `VITE_API_URL` to use another server.

For local Python development, install `requirements-runtime.txt`, start `docker compose up -d db`, and run `python -m uvicorn backend.api.app:app --port 8001`. The default database URL points to the local Compose database. For a native library outside Docker:

```powershell
cmake -S engine-cpp -B build-engine
cmake --build build-engine --config Release
```

The Docker build compiles the same sources with GCC `-O3`. C++ supports the long/flat momentum strategy only. ML and walk-forward run through Python.

## What is stored

- `research_datasets`: exact quote snapshots, deduplicated by SHA-256 of canonical quote JSON.
- `research_runs`: run kind, full configuration, dataset reference, implementation fingerprint, computation time, and complete returned results.
- Single backtests retain every trade and equity point. Walk-forward retains every returned chunk. Sweeps retain full details of the top K candidates and the compact ranking; discarded candidates are not retained.

`GET /backtest/runs` lists saved runs. `GET /backtest/runs/{id}` retrieves one. `GET /backtest/datasets/{id}` retrieves the actual input quotes. Submit a previously returned `dataset_id` to `/backtest/run` to reuse that exact input, including when comparing `engine: "python"` and `engine: "cpp"`. Retain the same strategy/cost configuration for a meaningful comparison.

Run data and its new snapshot are committed in one transaction. Successful responses are sent only after commit; database failures return 503. The named `research_data` volume survives normal container restarts and `docker compose down`.

The engine fingerprint includes research source, portfolio/metrics code, the research API, and the built native library on Linux. It identifies the local implementation; it is not a claim that uncommitted work has been published to GitHub.

Live portfolio/fill state still lives in memory and resets on startup. This persistence work is for research, not a durable live-trading ledger. PostgreSQL is a single local instance, without replication or backup automation.

## Correctness changes

- Fees are deducted from backtest cash when each trade executes.
- ML fits on the first 60% of quotes and evaluates only the held-out suffix; earlier quotes remain available as feature history.
- One-class training datasets safely produce a no-trade model rather than failing logistic regression.
- Seeded generators use local RNG objects, avoiding cross-request interference.
- Sweep candidates reuse one dataset. Zero scores are ranked correctly; smaller drawdown ranks ahead of larger drawdown.
- Bootstrap/permutation temporary allocations are bounded in batches rather than allocating thousands of full series at once.
- The streaming callback accepts the positional arguments supplied by the feed, and callback/stream exceptions are logged.
- The source `backend/data` folder is no longer accidentally excluded by the runtime-data gitignore rule.

## Order transport

The live API uses `async_engine_bridge.py`. One reader routes reports by order ID to pending futures; terminal reports complete requests immediately. There is no quiet-period wait. A write lock protects outgoing NDJSON writes without blocking the event loop.

Duplicate IDs are rejected within the session. Late fills after a client timeout are still applied once. Timeouts do not prove that an order did not execute. On restart, session IDs and live portfolio state are reset. The transport expects the current simulator's one terminal fill per order, not real-exchange partial fills or execution IDs. The old synchronous bridge remains as a benchmark baseline, not the application's order path.

## Verification and benchmark

```powershell
docker compose --profile test run --rm --build test
docker compose exec api python -m scripts.benchmark_backend
docker compose cp api:/app/artifacts/backend-benchmark.json ./artifacts/backend-benchmark.json
```

Tests use a temporary PostgreSQL schema and include accounting, nine C++ parity cases, concurrent RNG isolation, held-out evaluation, async out-of-order report routing, late-fill handling, atomic rollback, saved result retrieval, and dataset replay.

Current paired measurements, raw samples, timing scope and resume wording are in [PERFORMANCE.md](PERFORMANCE.md). That report supersedes the earlier sequential microbenchmark.

## Positioning and remaining gaps

This is a reproducible backtesting and execution-simulation project aimed at backend/quant-development engineering. It does not implement a real limit-order book, snapshot/delta reconciliation, durable live feed capture, or a validated alpha strategy.

The statistical routines are exploratory. Their IID resampling assumptions do not address serial dependence, and the metric fields currently derive win rate/profit factor from period PnL changes rather than a closed-trade ledger. They are not evidence of predictive profitability. A research extension should add dependence-aware resampling, explicit return horizons, baselines, and multiple-testing controls.

Live Binance streaming is disabled in Compose by default for an offline, deterministic demo. Set `MARKET_STREAM_ENABLED=true` to enable it. Synthetic data is explicitly labeled; no real historical dataset has been downloaded as part of this upgrade.
