import React from "react";

export default function EquityCurveChart({
  equity,
  height = 160
}: {
  equity: number[];
  height?: number;
}) {
  if (!equity || equity.length < 2) {
    return <div style={{ opacity: 0.7 }}>No equity data yet.</div>;
  }

  const w = 640;
  const h = height;
  const pad = 10;

  const minV = Math.min(...equity);
  const maxV = Math.max(...equity);
  const range = Math.max(1e-9, maxV - minV);

  const x = (i: number) => pad + (i * (w - 2 * pad)) / (equity.length - 1);
  const y = (v: number) => pad + (h - 2 * pad) * (1 - (v - minV) / range);

  const d = equity
    .map((v, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(2)} ${y(v).toFixed(2)}`)
    .join(" ");

  const last = equity[equity.length - 1];
  const first = equity[0];
  const pct = ((last - first) / (first || 1)) * 100;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <div style={{ fontWeight: 700 }}>Equity Curve</div>
        <div style={{ opacity: 0.75 }}>
          Final: {last.toFixed(2)} ({pct.toFixed(2)}%)
        </div>
      </div>

      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height }}>
        <path d={d} fill="none" stroke="currentColor" strokeWidth="2" />
      </svg>

      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, opacity: 0.7 }}>
        <span>Min: {minV.toFixed(2)}</span>
        <span>Max: {maxV.toFixed(2)}</span>
      </div>
    </div>
  );
}
