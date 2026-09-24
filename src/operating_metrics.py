"""Operating metrics (members, renewal rates, comparable sales, floor space) from data/manual/.

These are in the 10-K text rather than XBRL, so each row stores the sentence it came from. The build stops if a
quote isn't found word-for-word in the filing or the number isn't in the quote.
"""
from __future__ import annotations

import re
import sys

import pandas as pd

from src.config import MANUAL, PROCESSED, RAW
from src.ixbrl import document_text, read_facts


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("“", '"').replace("”", '"')).strip()


def verify_manual(idx: pd.DataFrame) -> pd.DataFrame:
    m = pd.read_csv(MANUAL / "operating_metrics.csv")
    texts = {a: _norm(document_text(f)) for a, f in zip(idx.accession, idx.local_file)}
    urls = dict(zip(idx.accession, idx.url))
    failures = []
    for i, r in m.iterrows():
        text = texts.get(r.source_accession)
        if text is None:
            failures.append(f"row {i}: unknown accession {r.source_accession}")
            continue
        if _norm(r.quote) not in text:
            failures.append(f"row {i} ({r.metric} FY{r.fiscal_year}): quote not found in {r.source_accession}")
        if str(r.value_as_written) not in r.quote:
            failures.append(f"row {i} ({r.metric} FY{r.fiscal_year}): '{r.value_as_written}' not in quote")
    if failures:
        sys.exit("Manual data verification FAILED:\n  " + "\n  ".join(failures))
    m["source_url"] = m.source_accession.map(urls)
    m["verified_in_filing"] = True
    return m


def warehouses_from_xbrl(idx: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, f in idx[idx.form == "10-K"].iterrows():
        df = read_facts(f.local_file)
        hit = df[(df.concept == "us-gaap:NumberOfStores") & (df.n_dims == 0) & (df.end == f.period_end)]
        fact = hit.iloc[0]
        rows.append({"fiscal_year": f.fiscal_year, "metric": "warehouses_end_of_year", "value": fact.value,
                     "unit": "count", "value_as_written": str(int(fact.value)), "source_accession": f.accession,
                     "section": "XBRL us-gaap:NumberOfStores", "quote": "",
                     "source_url": f"{f.url}#{fact.fact_id}", "verified_in_filing": True})
    return pd.DataFrame(rows)


def main() -> None:
    idx = pd.read_csv(RAW / "filing_index.csv")
    long = pd.concat([warehouses_from_xbrl(idx), verify_manual(idx)], ignore_index=True)
    long.to_csv(PROCESSED / "operating_metrics_long.csv", index=False)
    wide = long.pivot_table(index="metric", columns="fiscal_year", values="value", aggfunc="first")
    wide.columns = [f"FY{c}" for c in wide.columns]
    wide.to_csv(PROCESSED / "operating_metrics.csv")
    print(f"{len(long)} operating metrics verified against the filing text -> data/processed/operating_metrics.csv")
    print(wide.to_string())


if __name__ == "__main__":
    main()
