import { useEffect, useState } from "react";
import { api } from "../api";
import type { Health } from "../types";

export default function HealthCard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    try {
      setErr(null);
      setHealth(await api.getHealth());
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
      <h2 style={h2}>Health</h2>
      {err && <div style={{ color: "crimson" }}>{err}</div>}
      {!health ? (
        <div>Loading…</div>
      ) : (
        <div>
          <div>Status: <b>{health.status}</b></div>
          <div>Engine: <b style={{ color: health.engine_alive ? "green" : "crimson" }}>
            {health.engine_alive ? "Alive" : "Down"}
          </b></div>
          {health.engine_error && (
            <div style={{ marginTop: 8, opacity: 0.8, whiteSpace: "pre-wrap" }}>
              Error: {health.engine_error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  border: "1px solid #ddd",
  borderRadius: 12,
  padding: 14
};

const h2: React.CSSProperties = { margin: "0 0 10px 0", fontSize: 18 };
