import React, { useMemo, useState } from "react";
import { api } from "../api";
import type { BacktestRequest, BacktestResponse, SweepRequest, SweepResponse, WalkForwardRequest, WalkForwardResponse } from "../types";

type Props = {
  onBacktest: (r: BacktestResponse) => void;
  onSweep: (r: SweepResponse) => void;
  onWalkForward: (r: WalkForwardResponse) => void;
};

export default function BacktestRunnerCard({ onBacktest, onSweep, onWalkForward }: Props) {
  const [dataSource, setDataSource] = useState<BacktestRequest["data_source"]>("gbm");
  const [symbol, setSymbol] = useState("BTCUSDT");

  // gbm/orderbook
  const [steps, setSteps] = useState(800);
  const [startPrice, setStartPrice] = useState(30000);
  const [mu, setMu] = useState(0.0001);
  const [sigma, setSigma] = useState(0.02);
  const [spreadBps, setSpreadBps] = useState(5);
  const [volBps, setVolBps] = useState(10);

  // yahoo
  const [yahooSymbol, setYahooSymbol] = useState("SPY");
  const [start, setStart] = useState("2024-01-01");
  const [end, setEnd] = useState("2025-01-01");
  const [interval, setInterval] = useState("1d");

  // strategy/costs
  const [lookback, setLookback] = useState(10);
  const [qty, setQty] = useState(1);
  const [feeBps, setFeeBps] = useState(1);
  const [slipBps, setSlipBps] = useState(2);
  const [seed, setSeed] = useState<number>(7);

  // walk-forward
  const [trainSize, setTrainSize] = useState(300);
  const [testSize, setTestSize] = useState(100);

  // sweep
  const [lookbacks, setLookbacks] = useState("5,10,20,40");
  const [feeList, setFeeList] = useState("0,1,2");
  const [slipList, setSlipList] = useState("0,2,5");
  const [scoreKey, setScoreKey] = useState<SweepRequest["score_key"]>("sharpe");
  const [topK, setTopK] = useState(10);

  const [busy, setBusy] = useState<null | "backtest" | "walkforward" | "sweep">(null);
  const [err, setErr] = useState<string | null>(null);

  const baseReq: BacktestRequest = useMemo(() => {
    const common: BacktestRequest = {
      symbol,
      data_source: dataSource,
      lookback,
      qty,
      fee_bps: feeBps,
      slippage_bps: slipBps,
      seed
    };

    if (dataSource === "yahoo") {
      return {
        ...common,
        yahoo_symbol: yahooSymbol,
        start,
        end,
        interval,
        spread_bps: spreadBps
      };
    }

    if (dataSource === "orderbook") {
      return {
        ...common,
        steps,
        start_price: startPrice,
        spread_bps: spreadBps,
        vol_bps: volBps
      };
    }

    // gbm
    return {
      ...common,
      steps,
      start_price: startPrice,
      mu,
      sigma,
      spread_bps: spreadBps
    };
  }, [symbol, dataSource, steps, startPrice, mu, sigma, spreadBps, volBps, yahooSymbol, start, end, interval, lookback, qty, feeBps, slipBps, seed]);

  function parseNums(s: string) {
    return s
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean)
      .map((x) => Number(x))
      .filter((n) => Number.isFinite(n));
  }

  async function runBacktest() {
    setErr(null);
    setBusy("backtest");
    try {
      const r = await api.runBacktest(baseReq);
      onBacktest(r);
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    } finally {
      setBusy(null);
    }
  }

  async function runWalkForward() {
    setErr(null);
    setBusy("walkforward");
    try {
      const req: WalkForwardRequest = { ...baseReq, train_size: trainSize, test_size: testSize } as any;
      const r = await api.runWalkForward(req);
      onWalkForward(r);
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    } finally {
      setBusy(null);
    }
  }

  async function runSweep() {
    setErr(null);
    setBusy("sweep");
    try {
      const req: SweepRequest = {
        ...(baseReq as any),
        lookbacks: parseNums(lookbacks) as any,
        fee_bps_list: parseNums(feeList) as any,
        slippage_bps_list: parseNums(slipList) as any,
        top_k: topK,
        score_key: scoreKey
      };
      const r = await api.runSweep(req);
      onSweep(r);
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div style={{ border: "1px solid rgba(0,0,0,0.12)", borderRadius: 16, padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "baseline" }}>
        <div>
          <div style={{ fontWeight: 800, fontSize: 16 }}>Backtest Runner</div>
          <div style={{ opacity: 0.7, fontSize: 13 }}>Run synthetic/Yahoo backtests, sweeps, and walk-forward.</div>
        </div>
      </div>

      <div style={{ height: 12 }} />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <label>
          <div style={{ fontSize: 12, opacity: 0.75 }}>Data source</div>
          <select value={dataSource} onChange={(e) => setDataSource(e.target.value as any)} style={{ width: "100%", padding: 8 }}>
            <option value="gbm">GBM (synthetic)</option>
            <option value="orderbook">Orderbook sim</option>
            <option value="yahoo">Yahoo Finance</option>
          </select>
        </label>

        <label>
          <div style={{ fontSize: 12, opacity: 0.75 }}>Symbol</div>
          <input value={symbol} onChange={(e) => setSymbol(e.target.value)} style={{ width: "100%", padding: 8 }} />
        </label>

        {dataSource === "yahoo" ? (
          <>
            <label>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Yahoo symbol</div>
              <input value={yahooSymbol} onChange={(e) => setYahooSymbol(e.target.value)} style={{ width: "100%", padding: 8 }} />
            </label>

            <label>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Interval</div>
              <input value={interval} onChange={(e) => setInterval(e.target.value)} style={{ width: "100%", padding: 8 }} />
            </label>

            <label>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Start (YYYY-MM-DD)</div>
              <input value={start} onChange={(e) => setStart(e.target.value)} style={{ width: "100%", padding: 8 }} />
            </label>

            <label>
              <div style={{ fontSize: 12, opacity: 0.75 }}>End (YYYY-MM-DD)</div>
              <input value={end} onChange={(e) => setEnd(e.target.value)} style={{ width: "100%", padding: 8 }} />
            </label>
          </>
        ) : (
          <>
            <label>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Steps</div>
              <input type="number" value={steps} onChange={(e) => setSteps(Number(e.target.value))} style={{ width: "100%", padding: 8 }} />
            </label>

            <label>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Start price</div>
              <input type="number" value={startPrice} onChange={(e) => setStartPrice(Number(e.target.value))} style={{ width: "100%", padding: 8 }} />
            </label>

            {dataSource === "gbm" ? (
              <>
                <label>
                  <div style={{ fontSize: 12, opacity: 0.75 }}>mu</div>
                  <input value={mu} onChange={(e) => setMu(Number(e.target.value))} style={{ width: "100%", padding: 8 }} />
                </label>
                <label>
                  <div style={{ fontSize: 12, opacity: 0.75 }}>sigma</div>
                  <input value={sigma} onChange={(e) => setSigma(Number(e.target.value))} style={{ width: "100%", padding: 8 }} />
                </label>
              </>
            ) : (
              <>
                <label>
                  <div style={{ fontSize: 12, opacity: 0.75 }}>vol (bps)</div>
                  <input type="number" value={volBps} onChange={(e) => setVolBps(Number(e.target.value))} style={{ width: "100%", padding: 8 }} />
                </label>
                <div />
              </>
            )}
          </>
        )}

        <label>
          <div style={{ fontSize: 12, opacity: 0.75 }}>Lookback</div>
          <input type="number" value={lookback} onChange={(e) => setLookback(Number(e.target.value))} style={{ width: "100%", padding: 8 }} />
        </label>

        <label>
          <div style={{ fontSize: 12, opacity: 0.75 }}>Qty</div>
          <input type="number" value={qty} onChange={(e) => setQty(Number(e.target.value))} style={{ width: "100%", padding: 8 }} />
        </label>

        <label>
          <div style={{ fontSize: 12, opacity: 0.75 }}>Spread (bps)</div>
          <input type="number" value={spreadBps} onChange={(e) => setSpreadBps(Number(e.target.value))} style={{ width: "100%", padding: 8 }} />
        </label>

        <label>
          <div style={{ fontSize: 12, opacity: 0.75 }}>Seed</div>
          <input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value))} style={{ width: "100%", padding: 8 }} />
        </label>

        <label>
          <div style={{ fontSize: 12, opacity: 0.75 }}>Fee (bps)</div>
          <input type="number" value={feeBps} onChange={(e) => setFeeBps(Number(e.target.value))} style={{ width: "100%", padding: 8 }} />
        </label>

        <label>
          <div style={{ fontSize: 12, opacity: 0.75 }}>Slippage (bps)</div>
          <input type="number" value={slipBps} onChange={(e) => setSlipBps(Number(e.target.value))} style={{ width: "100%", padding: 8 }} />
        </label>
      </div>

      <div style={{ height: 12 }} />

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <button onClick={runBacktest} disabled={busy !== null} style={{ padding: "8px 12px" }}>
          {busy === "backtest" ? "Running..." : "Run Backtest"}
        </button>

        <button onClick={runWalkForward} disabled={busy !== null} style={{ padding: "8px 12px" }}>
          {busy === "walkforward" ? "Running..." : "Run Walk-Forward"}
        </button>

        <button onClick={runSweep} disabled={busy !== null} style={{ padding: "8px 12px" }}>
          {busy === "sweep" ? "Running..." : "Run Sweep"}
        </button>
      </div>

      <div style={{ height: 12 }} />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div style={{ border: "1px solid rgba(0,0,0,0.08)", borderRadius: 12, padding: 12 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Walk-forward settings</div>
          <label style={{ display: "block", marginBottom: 8 }}>
            <div style={{ fontSize: 12, opacity: 0.75 }}>Train size</div>
            <input type="number" value={trainSize} onChange={(e) => setTrainSize(Number(e.target.value))} style={{ width: "100%", padding: 8 }} />
          </label>
          <label style={{ display: "block" }}>
            <div style={{ fontSize: 12, opacity: 0.75 }}>Test size</div>
            <input type="number" value={testSize} onChange={(e) => setTestSize(Number(e.target.value))} style={{ width: "100%", padding: 8 }} />
          </label>
        </div>

        <div style={{ border: "1px solid rgba(0,0,0,0.08)", borderRadius: 12, padding: 12 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Sweep settings</div>

          <label style={{ display: "block", marginBottom: 8 }}>
            <div style={{ fontSize: 12, opacity: 0.75 }}>Lookbacks</div>
            <input value={lookbacks} onChange={(e) => setLookbacks(e.target.value)} style={{ width: "100%", padding: 8 }} />
          </label>

          <label style={{ display: "block", marginBottom: 8 }}>
            <div style={{ fontSize: 12, opacity: 0.75 }}>Fee bps list</div>
            <input value={feeList} onChange={(e) => setFeeList(e.target.value)} style={{ width: "100%", padding: 8 }} />
          </label>

          <label style={{ display: "block", marginBottom: 8 }}>
            <div style={{ fontSize: 12, opacity: 0.75 }}>Slippage bps list</div>
            <input value={slipList} onChange={(e) => setSlipList(e.target.value)} style={{ width: "100%", padding: 8 }} />
          </label>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <label>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Score key</div>
              <select value={scoreKey} onChange={(e) => setScoreKey(e.target.value as any)} style={{ width: "100%", padding: 8 }}>
                <option value="sharpe">sharpe</option>
                <option value="sortino">sortino</option>
                <option value="win_rate">win_rate</option>
                <option value="profit_factor">profit_factor</option>
                <option value="max_drawdown_pct">max_drawdown_pct</option>
              </select>
            </label>

            <label>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Top K</div>
              <input type="number" value={topK} onChange={(e) => setTopK(Number(e.target.value))} style={{ width: "100%", padding: 8 }} />
            </label>
          </div>
        </div>
      </div>

      {err && (
        <div style={{ marginTop: 12, color: "crimson", whiteSpace: "pre-wrap" }}>
          {err}
        </div>
      )}
    </div>
  );
}
