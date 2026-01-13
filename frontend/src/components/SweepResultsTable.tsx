import React from "react";
import type { SweepRow } from "../types";

export default function SweepResultsTable({ rows }: { rows: SweepRow[] }) {
  if (!rows || rows.length === 0) {
    return <div style={{ opacity: 0.7 }}>No sweep results yet.</div>;
  }

  return (
    <div>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>Sweep Results (Top)</div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid rgba(0,0,0,0.15)" }}>
              <th style={{ padding: 8 }}>Rank</th>
              <th style={{ padding: 8 }}>Score</th>
              <th style={{ padding: 8 }}>Params</th>
              <th style={{ padding: 8 }}>Trades</th>
              <th style={{ padding: 8 }}>Final Equity</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, idx) => (
              <tr key={idx} style={{ borderBottom: "1px solid rgba(0,0,0,0.08)" }}>
                <td style={{ padding: 8 }}>{idx + 1}</td>
                <td style={{ padding: 8 }}>{r.score == null ? "—" : r.score.toFixed(4)}</td>
                <td style={{ padding: 8 }}>
                  <code style={{ fontSize: 12 }}>{JSON.stringify(r.params)}</code>
                </td>
                <td style={{ padding: 8 }}>{r.trades}</td>
                <td style={{ padding: 8 }}>{r.final_equity == null ? "—" : r.final_equity.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
