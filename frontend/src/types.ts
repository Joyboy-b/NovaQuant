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

export type Position = {
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
  positions: Position[];
};

export type Side = "BUY" | "SELL";

export type Order = {
  order_id: string;
  symbol: string;
  side: Side;
  qty: number;
  px: number;
};

export type BacktestRequest = {
  symbol: string;

  data_source: "gbm" | "orderbook" | "yahoo";
  steps?: number;
  seed?: number | null;

  // synthetic
  start_price?: number;
  mu?: number;
  sigma?: number;
  spread_bps?: number;
  vol_bps?: number;

  // yahoo
  yahoo_symbol?: string;
  start?: string; // YYYY-MM-DD
  end?: string;   // YYYY-MM-DD
  interval?: string;

  // strategy
  strategy?: "momentum";
  lookback?: number;
  qty?: number;

  // costs
  fee_bps?: number;
  slippage_bps?: number;
};

export type Trade = {
  i: number;
  symbol: string;
  side: "BUY" | "SELL";
  qty: number;
  px: number;
  mid?: number;
  bid?: number;
  ask?: number;
  fee?: number;
};

export type BacktestResponse = {
  symbol: string;
  equity: number[];
  trades: Trade[];
  metrics: Record<string, any>;
  stats?: Record<string, any>;
};

export type SweepRequest = BacktestRequest & {
  lookbacks: number[];
  fee_bps_list: number[];
  slippage_bps_list: number[];
  top_k: number;
  score_key: "sharpe" | "sortino" | "max_drawdown_pct" | "profit_factor" | "win_rate";
};

export type SweepRow = {
  params: Record<string, any>;
  score: number | null;
  metrics: Record<string, any>;
  trades: number;
  final_equity: number | null;
};

export type SweepResponse = {
  top: SweepRow[];
};

export type WalkForwardRequest = BacktestRequest & {
  train_size: number;
  test_size: number;
};

export type WalkForwardChunk = {
  start: number;
  end: number;
  equity: number[];
  trades: any[];
};

export type WalkForwardResponse = {
  chunks: WalkForwardChunk[];
  chunk_metrics: { start: number; end: number; metrics: Record<string, any> }[];
};
