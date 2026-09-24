"""Loaders for the market data in data/raw/market/."""
from __future__ import annotations

import pandas as pd

from src.config import RAW, VALUATION_DATE

MKT = RAW / "market"


def prices(ticker: str, freq: str = "monthly") -> pd.DataFrame:
    """Yahoo Finance closes. `close` is the traded price; `adjclose` also reflects dividends and splits."""
    t = ticker.replace("^", "")
    df = pd.read_csv(MKT / f"yahoo_{t}_{freq}.csv", parse_dates=["date"]).set_index("date")
    return df


def price_on_valuation_date(ticker: str) -> float:
    d = prices(ticker, "daily")
    return float(d.loc[pd.Timestamp(VALUATION_DATE), "close"])


def monthly_returns(ticker: str, months: int = 60) -> pd.Series:
    """Total-return (dividend-adjusted) monthly returns for the `months` months ending with the valuation month."""
    p = prices(ticker, "monthly")["adjclose"]
    p = p[p.index <= pd.Timestamp(VALUATION_DATE)]
    return p.pct_change().dropna().iloc[-months:]


def fred(series: str) -> float:
    """Value of a FRED series on the valuation date, in decimal (FRED quotes percent)."""
    df = pd.read_csv(MKT / f"fred_{series}.csv", parse_dates=["observation_date"]).set_index("observation_date")
    s = pd.to_numeric(df[series], errors="coerce").dropna()
    s = s[s.index <= pd.Timestamp(VALUATION_DATE)]
    return float(s.iloc[-1]) / 100


def damodaran_erp(year_end: int) -> dict:
    df = pd.read_csv(MKT / "damodaran_implied_erp.csv").set_index("year_end")
    return df.loc[year_end].to_dict()
