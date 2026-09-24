# Reproducing the results

Everything in `outputs/` can be rebuilt from the original filings. This page lists each step, what it does and what it
produces. For most people, the short version in the [README](../README.md#reproducing-the-results) is enough.

## Requirements

- Python 3.10 or later, with the packages in `requirements.txt`.
- An e-mail address for the SEC download: the U.S. Securities and Exchange Commission asks every automated request to
  identify itself (`export SEC_USER_AGENT="Your Name your.email@example.com"`).
- Optional, for the slides: Node.js and `npm install pptxgenjs react react-dom react-icons sharp`.
- Optional, to see calculated values in the Excel file: open it in Excel (or LibreOffice), which recalculates the formulas.

## One command

```bash
python -m src.run_all              # full rebuild, including the SEC download
python -m src.run_all --offline    # no downloads: use the files already in data/raw/
python -m pytest -q                # 101 automated checks
```

Market data (share prices, interest rates, equity risk premium) is already stored in `data/raw/market/`, so `run_all`
does not download it again. Add `--refresh-market` to re-download it; Yahoo Finance and FRED often block automated
requests, which is why the stored files were collected through a browser (see [valuation.md](valuation.md), section 8).

## Step by step

Each step can also be run on its own with `python -m <module>`, in this order.

| # | Module | What it does | Main output |
|---:|---|---|---|
| 1 | `src.sec_fetch` | Downloads Costco's 10-K and 10-Q filings and the XBRL company data for Costco and the seven comparable companies from SEC EDGAR. `--only TICKER` adds one company. | `data/raw/` and `data/raw/manifest.csv` |
| 2 | `src.market_fetch` | Downloads share prices, Treasury yields, credit spreads and the equity risk premium (optional; see above). | `data/raw/market/` |
| 3 | `src.extract_financials` | Reads the income statement, balance sheet and cash flow statement for fiscal years 2020–2024 from the 10-K filings, with a source link for every number, and cross-checks 320 values against the SEC data service. | `data/processed/*.csv` |
| 4 | `src.operating_metrics` | Checks each hand-collected figure (members, renewal rates, comparable sales) against the exact sentence in the filing. | `data/processed/operating_metrics.csv` |
| 5 | `src.historical` | Historical ratios: growth, margins, returns, working capital, cash use. | `outputs/tables/historical_metrics.csv` |
| 6 | `src.extract_quarter` | The latest quarter before the valuation date (first quarter of fiscal 2025, to 24 November 2024). | `data/processed/quarter_q1_fy2025.csv` |
| 7 | `src.forecast` | Five-year forecast of the three linked financial statements from the assumptions in `config/assumptions.json`. | `outputs/tables/forecast_*.csv` |
| 8 | `src.wacc` | Required return: regression beta, risk-free rate, equity risk premium, cost of debt, weights. | `outputs/tables/wacc.csv`, `peer_betas.csv` |
| 9 | `src.dcf` | Discounted cash flow valuation, reverse DCF and cross-checks. | `outputs/tables/dcf_*.csv`, `reverse_dcf_growth_duration.csv` |
| 10 | `src.comps` | Comparable-company multiples and implied values. | `outputs/tables/comps*.csv` |
| 11 | `src.sensitivity` | Sensitivity tables and bear / base / bull scenarios. | `outputs/tables/sens_*.csv` |
| 12 | `src.build_excel` | The fully linked Excel model, including a Checks sheet that reconciles it to the Python results. | `outputs/COST_Valuation_Model.xlsx` |
| 13 | `src.charts` | The 14 charts. | `outputs/charts/` |
| 14 | `src.build_memo` | The two-page investment memo from `docs/investment_memo.md`. | `outputs/COST_Investment_Memo.pdf` |
| 15 | `node scripts/build_deck.js` | The four-slide deck. | `outputs/COST_Equity_Research_Deck.pptx` |

The historical analysis notebook can be opened with `jupyter notebook notebooks/01_historical_analysis.ipynb`.
