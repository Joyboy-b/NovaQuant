import React, { useState } from "react";
import HealthCard from "./components/HealthCard";
import PortfolioCard from "./components/PortfolioCard";
import MetricsCard from "./components/MetricsCard";
import OrderCard from "./components/OrderCard";
import BacktestRunnerCard from "./components/BackTestRunnerCard";
import EquityCurveChart from "./components/EquityCurveChart";
import SweepResultsTable from "./components/SweepResultsTable";
import WalkForwardChunksVisual from "./components/WalkForwardChunksVisual";

import type { BacktestResponse, SweepResponse, WalkForwardResponse } from "./types";

export default function App() {
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null);
  const [sweep, setSweep] = useState<SweepResponse | null>(null);
  const [walk, setWalk] = useState<WalkForwardResponse | null>(null);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 20, maxWidth: 1200, margin: "0 auto" }}>
      <h1 style={{ marginBottom: 6 }}>NovaQuant Dashboard</h1>
      <p style={{ marginTop: 0, opacity: 0.7 }}>FastAPI + C++ Engine + Backtesting Lab</p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <HealthCard />
        <MetricsCard />
      </div>

      <div style={{ height: 16 }} />

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: 16 }}>
        <PortfolioCard />
        <OrderCard />
      </div>

      <div style={{ height: 16 }} />

      <BacktestRunnerCard
        onBacktest={(r) => {
          setBacktest(r);
          setSweep(null);
        }}
        onSweep={(r) => setSweep(r)}
        onWalkForward={(r) => setWalk(r)}
      />

      <div style={{ height: 16 }} />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={{ border: "1px solid rgba(0,0,0,0.12)", borderRadius: 16, padding: 16 }}>
          {backtest ? <EquityCurveChart equity={backtest.equity} /> : <div style={{ opacity: 0.7 }}>Run a backtest to see equity curve.</div>}
        </div>

        <div style={{ border: "1px solid rgba(0,0,0,0.12)", borderRadius: 16, padding: 16 }}>
          {walk ? <WalkForwardChunksVisual chunks={walk.chunks} /> : <div style={{ opacity: 0.7 }}>Run walk-forward to see chunk performance.</div>}
        </div>
      </div>

      <div style={{ height: 16 }} />

      <div style={{ border: "1px solid rgba(0,0,0,0.12)", borderRadius: 16, padding: 16 }}>
        {sweep ? <SweepResultsTable rows={sweep.top} /> : <div style={{ opacity: 0.7 }}>Run a sweep to see top parameter sets.</div>}
      </div>
    </div>
  );
}
