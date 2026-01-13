from __future__ import annotations

from typing import Tuple


class BpsCostModel:
    def __init__(self, fee_bps: float = 0.0, slippage_bps: float = 0.0):
        self.fee_bps = float(fee_bps)
        self.slippage_bps = float(slippage_bps)

    def fill_from_quote(self, *, side: str, qty: float, bid: float, ask: float) -> Tuple[float, float]:
        """
        Quote-based fill:
          - BUY fills at ask
          - SELL fills at bid
          - plus extra slippage in bps against you
          - fee on notional
        """
        base = ask if side == "BUY" else bid
        slip = base * (self.slippage_bps / 10_000.0)
        fill_px = base + slip if side == "BUY" else base - slip

        fee = (qty * fill_px) * (self.fee_bps / 10_000.0)
        return fill_px, fee
