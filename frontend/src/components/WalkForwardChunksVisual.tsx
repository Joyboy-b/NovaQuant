import React from "react";
import type { WalkForwardChunk } from "../types";

function pctChange(equity: number[]) {
  if (!equity || equity.length < 2) return 0;
  return ((equity[equity.length - 1] - equity[0]) / (equity[0] || 1)) * 100;
}

export default function WalkForwardChunksVisual({ chunks }: { chunks: WalkForwardChunk[] }) {
  if (!chunks || chunks.length === 0) {
    return <div style={{ opacity: 0.7 }}>No walk-forward results yet.</div>;
  }

  const changes = chunks.map((c) => pctChange(c.equity));
  const minC = Math.min(...changes);
  const maxC = Math.max(...changes);
  const span = Math.max(1e-9, maxC - minC);

  return (
    <div>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>Walk-Forward Chunks</div>

      <div style={{ display: "grid", gap: 10 }}>
        {chunks.map((c, idx) => {
          const ch = changes[idx];
          const norm = (ch - minC) / span; // 0..1

          // tiny sparkline
          const eq = c.equity;
          const w = 120;
          const h = 24;
          const pad = 2;
          const minV = Math.min(...eq);
          const maxV = Math.max(...eq);
          const r = Math.max(1e-9, maxV - minV);
          const path = eq
            .map((v, i) => {
              const x = pad + (i * (w - 2 * pad)) / (eq.length - 1);
              const y = pad + (h - 2 * pad) * (1 - (v - minV) / r);
              return `${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
            })
            .join(" ");

          return (
            <div
              key={idx}
              style={{
                display: "grid",
                gridTemplateColumns: "90px 1fr 140px",
                alignItems: "center",
                gap: 12,
                padding: 10,
                border: "1px solid rgba(0,0,0,0.12)",
                borderRadius: 12
              }}
            >
              <div style={{ fontWeight: 700 }}>#{idx + 1}</div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, opacity: 0.8 }}>
                  <span>
                    [{c.start} → {c.end}]
                  </span>
                  <span>{ch.toFixed(2)}%</span>
                </div>
                <div
                  style={{
                    height: 10,
                    borderRadius: 999,
                    border: "1px solid rgba(0,0,0,0.12)",
                    overflow: "hidden"
                  }}
                >
                  <div style={{ width: `${(norm * 100).toFixed(1)}%`, height: "100%", background: "currentColor" }} />
                </div>
              </div>

              <svg viewBox={`0 0 ${w} ${h}`} style={{ width: 140, height: 28, opacity: 0.9 }}>
                <path d={path} fill="none" stroke="currentColor" strokeWidth="2" />
              </svg>
            </div>
          );
        })}
      </div>
    </div>
  );
}
