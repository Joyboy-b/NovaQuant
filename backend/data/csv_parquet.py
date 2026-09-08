from __future__ import annotations
from typing import Optional
import pandas as pd


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.lower() for c in df.columns]
    return df


def load_parquet(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df.columns = [c.lower() for c in df.columns]
    return df


def normalize_ohlc(df: pd.DataFrame, price_col: str = "close") -> pd.DataFrame:
    if price_col not in df.columns:
        raise ValueError(f"Expected column '{price_col}' in df. cols={list(df.columns)}")
    return df
