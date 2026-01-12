# backend/api/app.py
from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.config import SETTINGS
from backend.models.order import Order
from backend.models.metrics import MetricsResponse
from backend.services.portfolio import PORTFOLIO
from backend.services.session import SESSION_STATE
from backend.services.metrics import compute_metrics
from backend.api.engine_bridge import EngineBridge, default_engine_path
from backend.data.binance_ws import run_bookticker_loop

app = FastAPI(title=SETTINGS.name, version=SETTINGS.version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=SETTINGS.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# IMPORTANT: do NOT construct the engine at import time
bridge: EngineBridge | None = None
ENGINE_ERROR: str | None = None

BINANCE_TASK: Optional[asyncio.Task] = None


@app.on_event("startup")
async def startup():
    global bridge, ENGINE_ERROR, BINANCE_TASK

    PORTFOLIO.reset()
    SESSION_STATE.reset()

    # Start engine if present; otherwise keep API alive
    try:
        bridge = EngineBridge(default_engine_path())
        bridge.start()
        ENGINE_ERROR = None
    except Exception as e:
        bridge = None
        ENGINE_ERROR = f"{type(e).__name__}: {e}"

    # Start Binance streaming marks
    if BINANCE_TASK is None or BINANCE_TASK.done():
        BINANCE_TASK = asyncio.create_task(
            run_bookticker_loop(
                SETTINGS.binance_symbol,
                on_tick=lambda mid, bid, ask: _on_market_tick(mid=mid, bid=bid, ask=ask),
            )
        )


@app.on_event("shutdown")
async def shutdown():
    global BINANCE_TASK, bridge

    if BINANCE_TASK and not BINANCE_TASK.done():
        BINANCE_TASK.cancel()
        try:
            await BINANCE_TASK
        except asyncio.CancelledError:
            pass

    if bridge is not None:
        bridge.stop()
        bridge = None


def _on_market_tick(*, mid: float, bid: float, ask: float) -> None:
    PORTFOLIO.marks[SETTINGS.binance_symbol] = mid
    SESSION_STATE.equity.append(PORTFOLIO.mark_to_market())

    if SESSION_STATE.drawdown_pct >= SETTINGS.max_session_drawdown_pct:
        SESSION_STATE.halt_trading = True


def _check_risks(order: Order) -> None:
    notional = order.qty * order.px
    if notional > SETTINGS.per_trade_notional_cap:
        raise HTTPException(
            status_code=400,
            detail=f"Notional {notional:.2f} exceeds cap {SETTINGS.per_trade_notional_cap:.2f}",
        )
    if SESSION_STATE.halt_trading:
        raise HTTPException(
            status_code=403,
            detail=f"Trading halted: drawdown {SESSION_STATE.drawdown_pct:.2f}%",
        )


@app.post("/execute_order")
async def execute_order(order: Order):
    _check_risks(order)

    if bridge is None or not bridge.is_alive():
        raise HTTPException(
            status_code=503,
            detail=f"Engine unavailable. {ENGINE_ERROR or ''}".strip(),
        )

    bridge.send(order.model_dump())
    reports = bridge.recv_all(timeout=2.0)

    # Demo-fill until you parse real engine reports
    PORTFOLIO.on_fill(order.symbol, order.side.value, order.qty, order.px)
    SESSION_STATE.equity.append(PORTFOLIO.mark_to_market())

    return {"status": "submitted", "reports": reports}


@app.get("/metrics", response_model=MetricsResponse)
def get_metrics() -> MetricsResponse:
    equity = SESSION_STATE.equity
    trade_pnls = [equity[i] - equity[i - 1] for i in range(1, len(equity))]
    return compute_metrics(equity, trade_pnls)


@app.websocket("/ws/metrics")
async def ws_metrics(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            m = get_metrics()
            await ws.send_json(m.model_dump())
            await asyncio.sleep(SETTINGS.metrics_ws_interval_sec)
    except Exception:
        pass


@app.get("/health")
def health():
    return {
        "status": "ok",
        "engine_alive": bool(bridge and bridge.is_alive()),
        "engine_error": ENGINE_ERROR,
    }
@app.get("/")
def root():
    return {
        "name": SETTINGS.name,
        "version": SETTINGS.version,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
        "ws_metrics": "/ws/metrics",
    }
@app.get("/portfolio")
def portfolio():
    return PORTFOLIO.snapshot()
