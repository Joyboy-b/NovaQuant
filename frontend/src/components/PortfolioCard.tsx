import { useEffect, useState } from "react";
import { api } from "../api";
import type { Portfolio } from "../types";

export default function PortfolioCard() {
  const [p, setP] = useState<Portfolio | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    try {
      setErr(null);
      setP(await api.getPortfolio());
    } catch (e: any) {
      setErr(e.message ?? String(e));
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, []);

  return (
    <div style={cardStyle}>
      <h2 style={h2}>Portfolio</h2>
      {err && <div style={{ color: "crimson" }}>{err}</div>}
      {!p ? (
        <div>Loading…</div>
      ) : (
        <>
          <div style={{ display: "flex", gap: 18, marginBottom: 10 }}>
            <Stat label="Cash" value={money(p.cash)} />
            <Stat label="Equity" value={money(p.equity)} />
            <Stat label="Positions" value={String(p.positions.length)} />
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>
                <th>Symbol</th><th>Qty</th><th>Avg</th><th>Mark</th><th>Unreal</th><th>Real</th>
              </tr>
            </thead>
            <tbody>
              {p.positions.length === 0 ? (
                <tr><td colSpan={6} style={{ paddingTop: 10, opacity: 0.7 }}>No positions.</td></tr>
              ) : (
                p.positions.map((x) => (
                  <tr key={x.symbol} style={{ borderBottom: "1px solid #f3f3f3" }}>
                    <td>{x.symbol}</td>
                    <td>{x.qty}</td>
                    <td>{money(x.avg_px)}</td>
                    <td>{money(x.mark)}</td>
                    <td style={{ color: x.unrealized_pnl >= 0 ? "green" : "crimson" }}>
                      {money(x.unrealized_pnl)}
                    </td>
                    <td style={{ color: x.realized_pnl >= 0 ? "green" : "crimson" }}>
                      {money(x.realized_pnl)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ opacity: 0.65, fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 800 }}>{value}</div>
    </div>
  );
}

function money(x: number) {
  return `$${x.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

const cardStyle: React.CSSProperties = { border: "1px solid #ddd", borderRadius: 12, padding: 14 };
const h2: React.CSSProperties = { margin: "0 0 10px 0", fontSize: 18 };
