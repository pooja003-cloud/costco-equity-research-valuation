"""Last-twelve-months (LTM) income-statement figures from SEC companyfacts, as known on the valuation date.

    LTM = last fiscal year + current year-to-date - prior-year year-to-date

Only 10-K/10-Q facts filed on or before 31 Jan 2025 are used. Several peers had 53-week fiscal years (e.g. the year
ended 3 Feb 2024), so every LTM flow is scaled to a 364-day (52-week) basis. That keeps the multiples comparable.
"""
from __future__ import annotations

from datetime import date

from src.peers import _facts
from src.config import VALUATION_DATE

CONCEPTS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
    "operating_income": ["OperatingIncomeLoss"],
    "d_and_a": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "DepreciationAmortizationAndAccretionNet",
                "DepreciationAmortizationAndOther", "Depreciation"],
    "net_income": ["NetIncomeLoss"],
}


def _dur(f):
    return (date.fromisoformat(f["end"]) - date.fromisoformat(f["start"])).days + 1


def _durations(ticker: str, concept: str) -> list[dict]:
    node = _facts(ticker)["us-gaap"].get(concept)
    if not node:
        return []
    return [f for unit, fs in node["units"].items() if unit == "USD" for f in fs
            if "start" in f and f.get("filed", "9999") <= VALUATION_DATE and f.get("form") in ("10-K", "10-Q", "10-K/A", "10-Q/A")]


def _pick(facts, end, days, tol=8):
    hits = [f for f in facts if abs((date.fromisoformat(f["end"]) - date.fromisoformat(end)).days) <= 10 and abs(_dur(f) - days) <= tol]
    return max(hits, key=lambda f: f["filed"]) if hits else None


def ltm(ticker: str, item: str) -> dict:
    """Return the LTM value ($m, 52-week basis) plus the facts it was built from."""
    best = None
    for c in CONCEPTS[item]:
        fs = _durations(ticker, c)
        if not fs:
            continue
        latest_end = max(f["end"] for f in fs)
        if best is None or latest_end > best[1]:
            best = (c, latest_end, fs)
    concept, end, fs = best
    annuals = [f for f in fs if 350 <= _dur(f) <= 380]
    fy = max(annuals, key=lambda f: (f["end"], f["filed"]))
    if fy["end"] == end:
        value, days, parts = fy["val"], _dur(fy), {"fy": fy}
        ytd_cur = ytd_prior = None
    else:
        cands = [f for f in fs if f["end"] == end and f["start"] > fy["end"] and _dur(f) < 350]
        ytd_cur = max(cands, key=_dur)                   # longest year-to-date period ending at the latest quarter
        prior_end = date.fromisoformat(end).replace(year=date.fromisoformat(end).year - 1).isoformat()
        ytd_prior = _pick(fs, prior_end, _dur(ytd_cur))
        if ytd_prior is None:
            raise RuntimeError(f"{ticker} {item}: no prior-year YTD comparable to {ytd_cur['start']}..{end}")
        value = fy["val"] + ytd_cur["val"] - ytd_prior["val"]
        days = _dur(fy) + _dur(ytd_cur) - _dur(ytd_prior)
        parts = {"fy": fy, "ytd_cur": ytd_cur, "ytd_prior": ytd_prior}
    scaled = value * 364 / days / 1e6
    out = {"ticker": ticker, "item": item, "concept": concept, "ltm_end": end, "ltm_days": days, "value": scaled,
           "fy_end": parts["fy"]["end"], "fy_accn": parts["fy"]["accn"]}
    if ytd_cur:
        out.update(ytd_start=ytd_cur["start"], ytd_accn=ytd_cur["accn"],
                   ytd_growth=ytd_cur["val"] / ytd_prior["val"] - 1 if ytd_prior["val"] else None)
    return out


def annual_series(ticker: str, item: str) -> dict[str, float]:
    """Fiscal-year values ($m) keyed by fiscal-year end date, latest filing wins."""
    best = None
    for c in CONCEPTS[item]:
        fs = [f for f in _durations(ticker, c) if 350 <= _dur(f) <= 380]
        if fs and (best is None or max(f["end"] for f in fs) > best[0]):
            best = (max(f["end"] for f in fs), fs)
    out = {}
    for f in sorted(best[1], key=lambda f: f["filed"]):
        out[f["end"]] = f["val"] / 1e6 * 364 / _dur(f)
    return dict(sorted(out.items()))
