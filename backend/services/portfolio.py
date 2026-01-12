# backend/services/portfolio.py
from collections import defaultdict
from pydantic import BaseModel
from typing import List, Dict, Any


class Position(BaseModel):
    symbol: str
    qty: float = 0.0
    avg_px: float = 0.0
    realized_pnl: float = 0.0


class PortfolioState:
    def __init__(self):
        self.cash: float = 1_000_000.0
        self.positions: Dict[str, Position] = {}
        self.marks: Dict[str, float] = defaultdict(lambda: 100.0)
        self.equity_curve: List[float] = [self.cash]

    def reset(self):
        self.__init__()

    def mark_to_market(self) -> float:
        pos_val = sum(p.qty * self.marks[sym] for sym, p in self.positions.items())
        return self.cash + pos_val

    def _get_pos(self, symbol: str) -> Position:
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)
        return self.positions[symbol]

    def on_fill(self, symbol: str, side: str, qty: float, px: float):
        sign = 1.0 if side == "BUY" else -1.0

        # BUY reduces cash, SELL increases cash
        self.cash -= sign * qty * px

        pos = self._get_pos(symbol)
        new_qty = pos.qty + sign * qty

        if sign > 0:  # BUY
            if pos.qty < 0:  # covering a short
                covered = min(qty, -pos.qty)
                pos.realized_pnl += covered * (pos.avg_px - px)
                remaining = qty - covered
                if remaining > 0:
                    # flipped to long
                    pos.avg_px = px
            elif pos.qty == 0:
                pos.avg_px = px
            else:
                # add to long
                pos.avg_px = (pos.avg_px * pos.qty + px * qty) / new_qty

        else:  # SELL
            if pos.qty > 0:  # selling long
                sold = min(qty, pos.qty)
                pos.realized_pnl += sold * (px - pos.avg_px)
                remaining = qty - sold
                if remaining > 0:
                    # flipped to short
                    pos.avg_px = px
            elif pos.qty == 0:
                # opening short
                pos.avg_px = px
            else:
                # add to short (keep avg)
                pos.avg_px = (pos.avg_px * abs(pos.qty) + px * qty) / abs(new_qty)

        pos.qty = new_qty
        if pos.qty == 0:
            pos.avg_px = 0.0

        self.equity_curve.append(self.mark_to_market())

    def snapshot(self) -> Dict[str, Any]:
        positions = []
        for sym, p in self.positions.items():
            mark = self.marks[sym]
            positions.append(
                {
                    "symbol": sym,
                    "qty": p.qty,
                    "avg_px": p.avg_px,
                    "mark": mark,
                    "unrealized_pnl": (mark - p.avg_px) * p.qty,
                    "realized_pnl": p.realized_pnl,
                }
            )
        return {"cash": self.cash, "equity": self.mark_to_market(), "positions": positions}


PORTFOLIO = PortfolioState()
