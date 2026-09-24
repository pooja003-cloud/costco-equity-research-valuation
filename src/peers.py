"""Balance-sheet items and share counts from companyfacts, using only filings made by 31 Jan 2025.

Companies tag debt differently, so each item tries a list of concepts in order and records which one it used.
"""
from __future__ import annotations

import json
from functools import lru_cache

from src.config import RAW_SEC, VALUATION_DATE


@lru_cache(maxsize=16)
def _facts(ticker: str) -> dict:
    return json.load(open(RAW_SEC / f"{ticker}_companyfacts.json"))["facts"]


def _instants(ticker: str, concept: str, ns: str = "us-gaap") -> list[dict]:
    node = _facts(ticker).get(ns, {}).get(concept)
    if not node:
        return []
    return [f for u in node["units"].values() for f in u
            if "start" not in f and f.get("filed", "9999") <= VALUATION_DATE and f.get("form") in ("10-K", "10-Q", "10-K/A", "10-Q/A")]


def latest_bs_date(ticker: str) -> str:
    return max(f["end"] for f in _instants(ticker, "Assets"))


def value_at(ticker: str, concepts: list[str], end: str) -> tuple[float, str | None]:
    for c in concepts:
        hits = [f for f in _instants(ticker, c) if f["end"] == end]
        if hits:
            f = max(hits, key=lambda f: f["filed"])
            return f["val"] / 1e6, c
    return 0.0, None


def shares_outstanding(ticker: str) -> tuple[float, str]:
    """Cover-page share count from the latest filing before the valuation date (millions)."""
    fs = _instants(ticker, "EntityCommonStockSharesOutstanding", "dei")
    f = max(fs, key=lambda f: (f["filed"], f["end"]))
    return f["val"] / 1e6, f["end"]


def debt_and_cash(ticker: str) -> dict:
    """Financial debt (incl. finance leases), operating lease liabilities and cash at the latest balance-sheet date ($m)."""
    end = latest_bs_date(ticker)
    out = {"ticker": ticker, "bs_date": end}
    cur, c1 = value_at(ticker, ["LongTermDebtAndCapitalLeaseObligationsCurrent", "LongTermDebtCurrent", "DebtCurrent"], end)
    non, c2 = value_at(ticker, ["LongTermDebtAndCapitalLeaseObligations", "LongTermDebtNoncurrent"], end)
    stb, c3 = value_at(ticker, ["ShortTermBorrowings", "CommercialPaper"], end)
    fl = 0.0
    fl_note = "included in debt concepts" if (c1 or "").startswith("LongTermDebtAndCapital") or (c2 or "").startswith("LongTermDebtAndCapital") else None
    if fl_note is None:
        flc, a = value_at(ticker, ["FinanceLeaseLiabilityCurrent"], end)
        fln, b = value_at(ticker, ["FinanceLeaseLiabilityNoncurrent"], end)
        flt, c = value_at(ticker, ["FinanceLeaseLiability"], end)
        fl = flt if c else flc + fln
        fl_note = c or ("+".join(x for x in [a, b] if x) or None)
        if fl_note is None:  # finance leases are often disclosed only in the annual lease note
            from datetime import date
            annual = [f for con in ["FinanceLeaseLiability"] for f in _instants(ticker, con) if f["form"].startswith("10-K")
                      and (date.fromisoformat(end) - date.fromisoformat(f["end"])).days <= 400]   # ignore stale tags
            if annual:
                f = max(annual, key=lambda f: f["end"])
                fl, fl_note = f["val"] / 1e6, f"FinanceLeaseLiability from latest 10-K ({f['end']})"
            else:
                fl_note = "not tagged"
    cash, c4 = value_at(ticker, ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "Cash"], end)
    sti, c5 = value_at(ticker, ["ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"], end)
    oll, c6 = value_at(ticker, ["OperatingLeaseLiability"], end)
    if c6 is None:
        a, x = value_at(ticker, ["OperatingLeaseLiabilityCurrent"], end)
        b, y = value_at(ticker, ["OperatingLeaseLiabilityNoncurrent"], end)
        oll, c6 = a + b, "+".join(z for z in [x, y] if z) or None
    nci, c7 = value_at(ticker, ["MinorityInterest"], end)
    out.update(debt_current=cur, debt_noncurrent=non, short_term_borrowings=stb, finance_leases=fl,
               financial_debt=cur + non + stb + fl, cash=cash, short_term_investments=sti,
               operating_lease_liab=oll, noncontrolling_interest=nci,
               concepts={"debt_current": c1, "debt_noncurrent": c2, "stb": c3, "finance_leases": fl_note,
                         "cash": c4, "sti": c5, "op_leases": c6, "nci": c7})
    return out
