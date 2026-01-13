from __future__ import annotations

from typing import Any, Dict, List

from backend.services.portfolio import PortfolioState
from backend.backtest.data import Quote


class BacktestEngine:
    def __init__(self, symbol: str, strategy, cost_model):
        self.symbol = symbol
        self.strategy = strategy
        self.cost_model = cost_model
        self.portfolio = PortfolioState()
        self.portfolio.reset()
        self.trades: List[Dict[str, Any]] = []

    def run(self, quotes: List[Quote]) -> Dict[str, Any]:
        equity: List[float] = []

        for j, q in enumerate(quotes):
            # mark
            self.portfolio.marks[self.symbol] = q.mid

            # target position from strategy
            target_qty = self.strategy.target_position(j, quotes)

            cur_pos = self.portfolio.positions.get(self.symbol)
            cur_qty = cur_pos.qty if cur_pos else 0.0

            delta = target_qty - cur_qty
            if abs(delta) > 1e-9:
                side = "BUY" if delta > 0 else "SELL"
                qty = abs(delta)

                fill_px, fee = self.cost_model.fill_from_quote(
                    side=side, qty=qty, bid=q.bid, ask=q.ask
                )

                self.portfolio.on_fill(self.symbol, side, qty, fill_px)

                self.trades.append(
                    {
                        "i": q.i,
                        "symbol": self.symbol,
                        "side": side,
                        "qty": qty,
                        "px": fill_px,
                        "mid": q.mid,
                        "bid": q.bid,
                        "ask": q.ask,
                        "fee": fee,
                    }
                )

            equity.append(self.portfolio.mark_to_market())

        return {"equity": equity, "trades": self.trades}
