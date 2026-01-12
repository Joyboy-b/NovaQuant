# backend/data/binance_ws.py
"""
Minimal Binance bookTicker streaming.

Requires:
  pip install websockets

Binance stream docs: wss://stream.binance.com:9443/ws/{symbol_lower}@bookTicker
Message includes best bid/ask.
"""
from __future__ import annotations

import asyncio
import json
from typing import Callable, Optional

import websockets


async def run_bookticker_loop(
    symbol: str,
    on_tick: Callable[[float, float, float], None],
    *,
    reconnect_delay_sec: float = 2.0,
):
    stream = f"{symbol.lower()}@bookTicker"
    url = f"wss://stream.binance.com:9443/ws/{stream}"

    while True:
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                async for raw in ws:
                    msg = json.loads(raw)
                    bid = float(msg["b"])
                    ask = float(msg["a"])
                    mid = (bid + ask) / 2.0
                    on_tick(mid, bid, ask)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(reconnect_delay_sec)
