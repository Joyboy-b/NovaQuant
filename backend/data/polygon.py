from __future__ import annotations
import os
import requests
import pandas as pd


def load_polygon_agg(
    ticker: str,
    start: str,
    end: str,
    *,
    timespan: str = "day",
    multiplier: int = 1,
) -> pd.DataFrame:
    key = os.environ.get("POLYGON_API_KEY")
    if not key:
        raise RuntimeError("Missing POLYGON_API_KEY env var")

    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{start}/{end}"
    r = requests.get(url, params={"adjusted": "true", "sort": "asc", "apiKey": key}, timeout=30)
    r.raise_for_status()
    j = r.json()
    rows = j.get("results", []) or []
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # polygon uses: o/h/l/c/v and t (ms epoch)
    df["t"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    df.columns = [c.lower() for c in df.columns]
    return df
