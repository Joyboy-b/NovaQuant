export type Side = "BUY" | "SELL";

export type Order = {
  order_id: string;
  symbol: string;
  side: Side;
  qty: number;
  px: number;
};

export type Health = {
  status: string;
  engine_alive: boolean;
  engine_error: string | null;
};

export type Metrics = {
  sharpe: number | null;
  sortino: number | null;
  max_drawdown_pct: number | null;
  profit_factor: number | null;
  win_rate: number | null;
  trades: number;
};

export type PortfolioPosition = {
  symbol: string;
  qty: number;
  avg_px: number;
  mark: number;
  unrealized_pnl: number;
  realized_pnl: number;
};

export type Portfolio = {
  cash: number;
  equity: number;
  positions: PortfolioPosition[];
};
