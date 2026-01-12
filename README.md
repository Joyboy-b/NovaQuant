# NovaQuant Trading Platform

**NovaQuant** is a modular quantitative trading platform that separates **strategy & orchestration (Python)** from **execution & performance-critical logic (C++)**, inspired by real-world professional trading systems.

It is designed to be:

* clear
* debuggable
* extensible
* portfolio-ready

---

## High-Level Architecture

```
┌──────────────────────────┐
│        Frontend          │
│  (React / Dashboard)     │
│                          │
│  • Portfolio             │
│  • Metrics               │
│  • Live Updates          │
└─────────────┬────────────┘
              │ HTTP / WS
              ▼
┌──────────────────────────┐
│      FastAPI Backend     │
│                          │
│  • Risk Checks           │
│  • Portfolio State       │
│  • Metrics (Sharpe, DD)  │
│  • Session Control       │
│                          │
│  EngineBridge (stdin/out)│
└─────────────┬────────────┘
              │ NDJSON
              ▼
┌──────────────────────────┐
│       C++ Engine         │
│                          │
│  • Order ACK             │
│  • Order FILL            │
│  • Execution Stub        │
│                          │
│  (Replaceable later)     │
└──────────────────────────┘
```

### Design Principles

* **Python** → orchestration, safety, visibility
* **C++** → execution & low-latency logic
* **Explicit IPC** → no magic, easy debugging
* **Engine is swappable** → stub today, real matcher tomorrow

---

## Features

* FastAPI backend (REST + WebSocket)
* C++ execution engine (ACK / FILL stub)
* Portfolio accounting (cash, positions, PnL)
* Risk controls (notional caps, drawdown halts)
* Live mark prices via Binance WebSocket
* Performance metrics:

  * Sharpe
  * Sortino
  * Drawdown
  * Win rate
* Web dashboard

---

## Quick Start (Windows)

### Prerequisites

* Python **3.10+**
* Node.js **18+**
* **MSVC Build Tools 2022**
* CMake
* Ninja

---

### 1️⃣ Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

---

### 2️⃣ Backend dependencies

```powershell
pip install -r backend\requirements.txt
```

---

### 3️⃣ Frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

---

### 4️⃣ Build the C++ engine (Release)

Run in **x64 Native Tools Command Prompt for VS 2022**:

```bat
cmake -S engine-cpp -B build-engine -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build-engine --parallel
```

Produces:

```
build-engine\novaquant_engine.exe
```

---

### 5️⃣ Start backend

```powershell
python -m uvicorn backend.api.app:app --reload --port 8000
```

---

### 6️⃣ Start frontend

```powershell
cd frontend
npm run dev
```

---

## URLs

* **Dashboard:** [http://localhost:5173](http://localhost:5173)
* **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Health:** [http://localhost:8000/health](http://localhost:8000/health)

---

## One-Command Build (Optional)

Create `build.ps1` in repo root:

```powershell
Write-Host "Building C++ engine..."
cmake -S engine-cpp -B build-engine -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build-engine --parallel

Write-Host "Starting backend..."
python -m uvicorn backend.api.app:app --reload --port 8000
```

Run:

```powershell
.\build.ps1
```

---

## Troubleshooting

### ❌ `pip` not found

```powershell
python -m pip install --upgrade pip
```

---

### ❌ Cannot activate venv

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

---

### ❌ `cl` not found

You must install **Build Tools for Visual Studio 2022** and select:

* Desktop development with C++
* MSVC v143
* Windows SDK

Verify:

```powershell
cl
```

---

### ❌ CMake generator mismatch

Delete the build folder:

```powershell
rmdir /s /q build-engine
```

Then rebuild.

---

### ❌ Engine not found

Check:

```powershell
python -c "from backend.api.engine_bridge import default_engine_path; print(default_engine_path())"
```

---

## Recruiter Notes

This project demonstrates:

* **System design** (clear component separation)
* **Cross-language integration** (Python ↔ C++)
* **Trading fundamentals** (PnL, risk, metrics)
* **Production discipline** (health checks, build scripts)

It is intentionally designed to be **readable, inspectable, and extensible**, not a black-box trading bot.

---

## Roadmap

* Real order book & matching engine
* Backtesting framework
* Strategy plug-in system
* Persistent trade storage
* Latency & slippage models
* Multi-asset portfolios

---

## Git Hygiene

Ignored:

* `.venv/`
* `build-engine/`
* binaries

Committed:

* Python backend
* C++ source
* CMake config
* README

---

## License

MIT (or your choice)

---
