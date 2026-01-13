from typing import List, Dict, Any
from backend.config import SETTINGS


class SessionState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.equity: List[float] = [1_000_000.0]
        self.last_pnl: float = 0.0
        self.halt_trading: bool = False

        # engine fill reports for UI/debug
        self.fills: List[Dict[str, Any]] = []

    @property
    def start_equity(self) -> float:
        return self.equity[0]

    @property
    def current_equity(self) -> float:
        return self.equity[-1]

    @property
    def drawdown_pct(self) -> float:
        peak = max(self.equity)
        return ((peak - self.current_equity) / peak * 100) if peak > 0 else 0.0

    def apply_fill(self, est_fill_pnl: float):
        self.last_pnl = est_fill_pnl
        self.equity.append(self.current_equity + est_fill_pnl)
        if self.drawdown_pct >= SETTINGS.max_session_drawdown_pct:
            self.halt_trading = True


SESSION_STATE = SessionState()
