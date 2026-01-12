import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { Metrics } from "../types";

export default function MetricsCard() {
  const [m, setM] = useState<Metrics | null>(null);
  const [mode, setMode] = useState<"ws" | "poll">("ws");
  const [err, setErr] = useState<string | null>(null);

  const wsUrl = useMemo(() => api.metricsWsUrl(), []);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let timer: any = null;
    let alive = true;

    async function poll() {
      try {
        setErr(null);
        setM(await api.getMetrics());
      } catch (e: any) {
        setErr(e.message ?? String(e));
      }
    }

    if (mode === "poll") {
      poll();
      timer = setInterval(poll, 1500);
    } else {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          setM(data);
          setErr(null);
        } catch {}
      };
      ws.onerror = () => setErr("WebSocket error (switch to Poll if needed).");
      ws.onclose = () => {
        if (alive) setErr("WebSocket closed (switch to Poll if needed).");
      };
    }

    return () => {
      alive = false;
      if (ws) ws.close();
      if (timer) clearInterval(timer);
    };
  }, [mode, wsUrl]);

  return (
    <div style={cardStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={h2}>Metrics</h2>
        <select value={mode} onChange={(e) => setMode(e.target.value as any)}>
          <option value="ws">Live (WS)</option>
          <option value="poll">Poll</option>
        </select>
      </div>

      {err && <div style={{ color: "crimson" }}>{err}</div>}
      {!m ? (
        <div>Loading…</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <Metric label="Sharpe" value={fmt(m.sharpe)} />
          <Metric label="Sortino" value={fmt(m.sortino)} />
          <Metric label="Max Drawdown %" value={fmt(m.max_drawdown_pct)} />
          <Metric label="Profit Factor" value={fmt(m.profit_factor)} />
          <Metric label="Win Rate" value={fmtPct(m.win_rate)} />
          <Metric label="Trades" value={String(m.trades)} />
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ border: "1px solid #eee", borderRadius: 10, padding: 10 }}>
      <div style={{ opacity: 0.65, fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

function fmt(x: number | null) {
  return x === null || Number.isNaN(x) ? "—" : x.toFixed(4);
}
function fmtPct(x: number | null) {
  return x === null || Number.isNaN(x) ? "—" : `${(x * 100).toFixed(1)}%`;
}

const cardStyle: React.CSSProperties = { border: "1px solid #ddd", borderRadius: 12, padding: 14 };
const h2: React.CSSProperties = { margin: "0 0 10px 0", fontSize: 18 };
