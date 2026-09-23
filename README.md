# Costco Wholesale (COST): Equity Research and Valuation

> **Independent academic research and valuation case study; not investment advice.** See [DISCLAIMER.md](DISCLAIMER.md).

A fundamental equity research project on Costco Wholesale Corporation. It covers historical
financial-statement analysis from SEC filings (FY2020–FY2024), a driver-based forecast,
a DCF valuation, a WACC build, comparable-company analysis, sensitivity analysis and a two-page investment memo.

**Valuation date:** 31 January 2025. All market inputs (share prices, risk-free rate, peer multiples) are as of this date.
Only filings public by this date are used.

## Project status

| Phase | Scope | Status |
|---|---|---|
| 1. Data | SEC EDGAR / XBRL extraction, source tracking, 30 integrity tests | **Done**, see [docs/data_sources.md](docs/data_sources.md) |
| 2. Historical analysis | Three statements, ratios, trend notebook | Not started |
| 3. Forecast | FY2025–FY2029 operating drivers | Not started |
| 4. WACC & DCF | Cost of capital, UFCF, terminal value | Not started |
| 5. Comparable companies | Peer selection, multiples | Not started |
| 6. Sensitivity & scenarios | WACC × g, revenue × margin, bear/base/bull | Not started |
| 7. Excel model | Fully linked workbook | Not started |
| 8. Memo & slides | Two-page memo, thesis slide, risks slide | Not started |

## Repository layout

```
config/          settings.json (company, peers, valuation date)
src/             Python pipeline
data/raw/        SEC downloads (git-ignored; manifest.csv is committed)
data/manual/     figures hand-collected from filing text, each with a citation
data/processed/  clean, source-tracked datasets
notebooks/       analysis notebooks
docs/            methodology, data sources, assumptions
outputs/         model, tables, charts, memo, slides
tests/           data-integrity and model tests
```

## Data

FY2020–FY2024 historical data (and the FY2019 opening balance sheet) is extracted straight from the
inline XBRL in Costco's 10-K filings. Every number carries a link to the exact tagged fact in the filing.
Operating metrics (members, renewal rates, comparable sales) are stored with the verbatim sentence they
come from, and are re-verified against the filing text on every build.
320 values were cross-checked against the SEC companyfacts API, and all 320 match. See [docs/data_sources.md](docs/data_sources.md).

| Dataset | File |
|---|---|
| Income statement / balance sheet / cash flow ($m) | `data/processed/income_statement.csv`, `balance_sheet.csv`, `cash_flow.csv` |
| Segments and merchandise categories | `data/processed/segments.csv` |
| Operating metrics | `data/processed/operating_metrics.csv` |
| Every number with its source link | `data/processed/financials_long.csv`, `operating_metrics_long.csv` |

## Reproducing

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export SEC_USER_AGENT="Your Name your.email@example.com"   # the SEC requires contact details
python -m src.sec_fetch
python -m src.extract_financials
python -m src.operating_metrics
python -m pytest -q
```
