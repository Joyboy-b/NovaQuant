import type { Health, Metrics, Portfolio, Order } from "./types";

const API = import.meta.env.VITE_API_URL as string;

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getHealth: () => http<Health>("/health"),
  getMetrics: () => http<Metrics>("/metrics"),
  getPortfolio: () => http<Portfolio>("/portfolio"),
  executeOrder: (order: Order) =>
    http<{ status: string; reports: any[] }>("/execute_order", {
      method: "POST",
      body: JSON.stringify(order)
    }),
  metricsWsUrl: () => {
    const url = new URL(API);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = "/ws/metrics";
    return url.toString();
  }
};
