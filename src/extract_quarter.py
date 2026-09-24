"""Q1 FY2025 (12 weeks to 24 Nov 2024) from the 10-Q: the latest quarter before the valuation date.

Used to sanity-check the FY2025 forecast and as the balance sheet for the DCF equity bridge.
"""
from __future__ import annotations

import pandas as pd

from src.config import PROCESSED, RAW
from src.extract_financials import BALANCE_SHEET, CASH_FLOW, INCOME_STATEMENT, LEASE_NOTE, _row, _scale
from src.ixbrl import read_facts


def main() -> pd.DataFrame:
    idx = pd.read_csv(RAW / "filing_index.csv")
    q = idx[idx.form == "10-Q"].sort_values("period_end").iloc[-1]
    facts = read_facts(q.local_file).copy()
    facts["concept"] = facts.concept.str.split(":").str[-1]
    facts["accession"], facts["filing_date"], facts["url"] = q.accession, q.filing_date, q.url
    days = (pd.to_datetime(facts.end) - pd.to_datetime(facts.start)).dt.days
    rows = []
    cur = facts[(facts.end == q.period_end) & days.between(80, 100)]
    prior = facts[(facts.end != q.period_end) & days.between(80, 100)]
    for label, pool in [("Q1 FY2025", cur), ("Q1 FY2024", prior)]:
        for statement, items in [("income_statement", INCOME_STATEMENT), ("cash_flow", CASH_FLOW)]:
            for key, (lab, concepts, dims, optional) in items.items():
                hit = pool[pool.concept.isin(concepts) & (pool.dims == dims)]
                if hit.empty:
                    continue
                f = hit.iloc[0]
                r = _row(key, lab, statement, label, f, _scale(f.value, key, f.concept))
                rows.append(r)
    bs = facts[(facts.end == q.period_end) & (facts.period_type == "instant") & (facts.dims == "")]
    for key, (lab, concepts, dims, optional) in {**BALANCE_SHEET, **{k: (v[0], v[1], "", True) for k, v in LEASE_NOTE.items()}}.items():
        hit = bs[bs.concept.isin(concepts)]
        if hit.empty:
            continue
        f = hit.iloc[0]
        rows.append(_row(key, lab, "balance_sheet", "Q1 FY2025", f, _scale(f.value, key, f.concept)))
    ws = facts[(facts.concept == "NumberOfStores") & (facts.dims == "") & (facts.end == q.period_end)]
    if not ws.empty:
        rows.append(_row("warehouses", "Warehouses in operation", "operating", "Q1 FY2025", ws.iloc[0], ws.iloc[0].value))
    out = pd.DataFrame(rows).rename(columns={"fiscal_year": "period"})
    out.to_csv(PROCESSED / "quarter_q1_fy2025.csv", index=False)
    return out


if __name__ == "__main__":
    out = main()
    w = out.pivot_table(index="line_item", columns="period", values="value", aggfunc="first")
    print(w.round(2).to_string())
