import HealthCard from "./components/HealthCard";
import PortfolioCard from "./components/PortfolioCard";
import MetricsCard from "./components/MetricsCard";
import OrderCard from "./components/OrderCard";

export default function App() {
  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 20, maxWidth: 1100, margin: "0 auto" }}>
      <h1 style={{ marginBottom: 6 }}>NovaQuant Dashboard</h1>
      <p style={{ marginTop: 0, opacity: 0.7 }}>FastAPI + C++ Engine (NDJSON bridge)</p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <HealthCard />
        <MetricsCard />
      </div>

      <div style={{ height: 16 }} />

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: 16 }}>
        <PortfolioCard />
        <OrderCard />
      </div>
    </div>
  );
}
