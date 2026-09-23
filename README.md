# Costco Wholesale (COST): Equity Research and Valuation

> **Independent academic research and valuation case study; not investment advice.** See [DISCLAIMER.md](DISCLAIMER.md).

A fundamental equity research project on Costco Wholesale Corporation. It covers historical
financial-statement analysis from SEC filings (FY2020–FY2024), a driver-based forecast,
a DCF valuation, a WACC build, comparable-company analysis, sensitivity analysis and a two-page investment memo.

**Valuation date:** 31 January 2025. All market inputs (share prices, risk-free rate, peer multiples) are as of this date.
Only filings public by this date are used.

## Repository layout

```
config/          settings.json (company, peers, valuation date), assumptions.json (forecast)
src/             Python pipeline
data/raw/        SEC downloads (git-ignored; manifest.csv is committed)
data/manual/     figures hand-collected from filing text, each with a citation
data/processed/  clean, source-tracked datasets
notebooks/       analysis notebooks
docs/            methodology, data sources, assumptions
outputs/         model, tables, charts, memo, slides
tests/           data-integrity and model tests
```

## Historical analysis: highlights

- **Membership fees are 1.9% of revenue but 52% of operating income** (FY2024), with a 92.9% U.S./Canada renewal rate.
- **~30% return on invested capital**, while capex runs at about 2x depreciation to fund new warehouses.
- **Negative working capital (about −5% of revenue):** suppliers and members finance growth.
- **Growth normalized** after the FY2021–22 surge to 5–6% comparable sales (ex gas & FX) plus ~2 points from new warehouses.

![Profit engine](outputs/charts/03_profit_engine.png)

More in [docs/historical_analysis.md](docs/historical_analysis.md) and the [chart pack](outputs/charts/).

## Base-case forecast (FY2025–FY2029)

Revenue is built from warehouse openings, comparable sales and membership fees (members × fee per member, including the
Sep 2024 fee increase). Every assumption is tied to the filings and explained in [docs/assumptions.md](docs/assumptions.md).
The three statements are fully linked, and tests confirm the balance sheet balances every year.

| $m | FY24A | FY25E | FY29E |
|---|---:|---:|---:|
| Revenue | 254,453 | 273,712 | 349,529 |
| Operating margin | 3.65% | 3.72% | 3.77% |
| Diluted EPS ($) | 16.56 | 17.31 | 23.13 |
| Free cash flow | 6,629 | 7,032 | 9,240 |

## Valuation (as of 31 Jan 2025)

| | |
|---|---:|
| WACC (CAPM: Rf 4.58%, beta 0.89, ERP 4.33%) | 8.38% |
| Terminal growth / RONIC | 3.0% / 25% |
| Enterprise value | $145.3bn |
| **DCF value per share** | **$337** |
| Share price (31 Jan 2025) | $979.88 |
| Terminal growth the price implies | 7.0% |

The DCF says the market is paying for decades of above-economy growth. The next five years of cash flow account for
only $61 of the $980 share price. Full workings, method choices and limitations: [docs/valuation.md](docs/valuation.md).

![DCF bridge](outputs/charts/11_dcf_bridge.png)

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
python -m src.historical           # metrics -> outputs/tables/
python -m src.extract_quarter      # Q1 FY2025 10-Q (latest quarter before the valuation date)
python -m src.forecast             # three-statement forecast -> outputs/tables/forecast_*.csv
python -m src.market_fetch         # market data (see note in docs/valuation.md if blocked)
python -m src.wacc                 # cost of capital -> outputs/tables/wacc.csv
python -m src.dcf                  # DCF -> outputs/tables/dcf_*.csv
python -m src.charts               # chart pack -> outputs/charts/
python -m pytest -q
jupyter notebook notebooks/01_historical_analysis.ipynb
```
