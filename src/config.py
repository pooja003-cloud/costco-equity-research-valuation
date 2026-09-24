"""Paths and settings used by the rest of the code."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA = ROOT / "data"
RAW = DATA / "raw"
RAW_SEC = RAW / "sec"
RAW_FILINGS = RAW / "filings"
MANUAL = DATA / "manual"
PROCESSED = DATA / "processed"
OUTPUTS = ROOT / "outputs"
TABLES = OUTPUTS / "tables"
CHARTS = OUTPUTS / "charts"

with open(CONFIG_DIR / "settings.json") as fh:
    SETTINGS = json.load(fh)

TICKER = SETTINGS["company"]["ticker"]
CIK = int(SETTINGS["company"]["cik"])
VALUATION_DATE = SETTINGS["valuation_date"]
FISCAL_YEARS = SETTINGS["historical_fiscal_years"]
PEERS = SETTINGS["peers"]


def cik10(cik: int) -> str:
    """SEC URLs use the CIK zero-padded to 10 digits."""
    return f"{int(cik):010d}"
