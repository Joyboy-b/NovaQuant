import { useState } from "react";
import { api } from "../api";
import type { Side } from "../types";

export default function OrderCard() {
  const [orderId, setOrderId] = useState("ord-1");
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [side, setSide] = useState<Side>("BUY");
  const [qty, setQty] = useState(1);
  const [px, setPx] = useState(30000);
  const [out, setOut] = useState<string>("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    setOut("");
    try {
      const res = await api.executeOrder({
        order_id: orderId,
        symbol,
        side,
        qty,
        px
      });
      setOut(JSON.stringify(res, null, 2));
      setOrderId((prev) => (prev.startsWith("ord-") ? `ord-${Number(prev.slice(4) || "1") + 1}` : prev + "-next"));
    } catch (e: any) {
      setOut(`ERROR: ${e.message ?? String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={cardStyle}>
      <h2 style={h2}>Execute Order</h2>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Field label="Order ID">
          <input value={orderId} onChange={(e) => setOrderId(e.target.value)} />
        </Field>
        <Field label="Symbol">
          <input value={symbol} onChange={(e) => setSymbol(e.target.value)} />
        </Field>

        <Field label="Side">
          <select value={side} onChange={(e) => setSide(e.target.value as Side)}>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
        </Field>

        <Field label="Qty">
          <input type="number" value={qty} onChange={(e) => setQty(Number(e.target.value))} min={1} />
        </Field>

        <Field label="Price">
          <input type="number" value={px} onChange={(e) => setPx(Number(e.target.value))} min={0} />
        </Field>

        <div style={{ display: "flex", alignItems: "end" }}>
          <button onClick={submit} disabled={busy} style={btn}>
            {busy ? "Submitting…" : "Submit"}
          </button>
        </div>
      </div>

      <div style={{ marginTop: 12 }}>
        <div style={{ opacity: 0.65, fontSize: 12, marginBottom: 6 }}>Response</div>
        <pre style={pre}>{out || "—"}</pre>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "grid", gap: 6 }}>
      <span style={{ opacity: 0.7, fontSize: 12 }}>{label}</span>
      {children}
    </label>
  );
}

const cardStyle: React.CSSProperties = { border: "1px solid #ddd", borderRadius: 12, padding: 14 };
const h2: React.CSSProperties = { margin: "0 0 10px 0", fontSize: 18 };
const btn: React.CSSProperties = { padding: "10px 12px", borderRadius: 10, border: "1px solid #ddd" };
const pre: React.CSSProperties = {
  background: "#0b1020",
  color: "#e8e8e8",
  padding: 10,
  borderRadius: 10,
  overflow: "auto",
  maxHeight: 240
};
