# Costco Wholesale (COST): Equity Research and Valuation

> **Independent academic research and valuation case study; not investment advice.** See [DISCLAIMER.md](DISCLAIMER.md).

## In plain English

Costco runs membership warehouses: shoppers pay an annual fee, then buy in bulk at very low prices. On 31 January 2025,
one Costco share cost **$979.88**.

This project asks a simple question: **based on the cash Costco's business can be expected to generate, what is one share
worth?**

To answer it, I:

1. rebuilt five years of Costco's financial statements (fiscal years 2020–2024) from its official filings with the U.S.
   Securities and Exchange Commission;
2. forecast the next five years (fiscal years 2025–2029), step by step, from warehouse openings, sales per warehouse and
   membership fees;
3. valued the company in three ways: from its future cash flows, by comparison with similar retailers, and by working
   backwards from the share price to see what it assumes.

**The answer:** my central estimate is about **$337 per share**, roughly a third of the market price. Comparison with
similar retailers supports, at most, about **$690**. Costco is an excellent business, but at $980 investors are paying for
many decades of strong growth, or treating Costco's profits as almost risk-free.

Every number in the project is traced back to its source, and the full model can be rebuilt with one set of commands
(see [Reproducing the results](#reproducing-the-results)). Terms in bold below are explained in the [glossary](#glossary).

## Key results at a glance

| | |
|---|---:|
| Share price on 31 January 2025 | $979.88 |
| Value per share from **discounted cash flow** (central case) | **$337** |
| Pessimistic / optimistic cases | $263 / $400 |
| Range supported by the closest comparable companies (Walmart, BJ's, PriceSmart) | about $360–$690 |
| Long-term growth the share price assumes, every year forever after 2029 (my central case uses 3%) | 7.0% |
| Annual return investors would have to accept for the price to make sense (my estimate is 8.4%) | 4.8% |

## What is in this repository

| Deliverable | Files |
|---|---|
| Two-page investment memo | [PDF](outputs/COST_Investment_Memo.pdf) · [text source](docs/investment_memo.md) |
| Slides: investment thesis, valuation, and risks and what would change my view | [PowerPoint](outputs/COST_Equity_Research_Deck.pptx) · [PDF](outputs/COST_Equity_Research_Deck.pdf) |
| Fully linked Excel valuation model | [COST_Valuation_Model.xlsx](outputs/COST_Valuation_Model.xlsx) |
| Historical analysis notebook (Python) | [01_historical_analysis.ipynb](notebooks/01_historical_analysis.ipynb) |
| Comparable-company and sensitivity tables | [outputs/tables/](outputs/tables/) |
| Methods, assumptions and sources | [docs/](docs/) |
| External reviews and my responses | [docs/model_review_log.md](docs/model_review_log.md) |

**Valuation date:** 31 January 2025. All market data (share prices, interest rates, other companies' valuations) is taken
as of that date, and only filings that were public by then are used. Nothing that happened later is allowed into the model.

## 1. Costco's past performance (fiscal years 2020–2024)

- **Membership fees are small in sales but large in profit.** They were 1.9% of revenue but 52% of operating income in
  fiscal year 2024. In the U.S. and Canada, 92.9% of members renewed.
- **High returns on the money invested in the business.** **Return on invested capital** was 33% in fiscal year 2024
  (about 30% on average since 2020), while Costco spent about twice its annual depreciation on new warehouses.
- **Suppliers and members fund the growth.** Costco sells its inventory before it pays suppliers, and members pay their
  fees in advance. So its **working capital** is negative (about −5% of revenue): growth releases cash instead of
  using it.
- **Growth has settled down.** After the 2021–2022 surge, comparable-store sales (excluding gasoline prices and currency
  movements) grew 5–6% a year, plus about 2 percentage points a year from new warehouses.

![Profit engine](outputs/charts/03_profit_engine.png)

More detail: [docs/historical_analysis.md](docs/historical_analysis.md) and the [chart pack](outputs/charts/).

## 2. Forecast (fiscal years 2025–2029)

Revenue is built from its drivers rather than a single growth rate: the number of warehouses, sales growth in existing
warehouses, and membership fees (paid members × fee per member, including the September 2024 fee increase). Every
assumption is tied to the filings and explained in [docs/assumptions.md](docs/assumptions.md). The income statement,
balance sheet and cash flow statement are fully linked, and automated tests confirm the balance sheet balances every year.

| $ millions (except per share) | 2024 (actual) | 2025 (forecast) | 2029 (forecast) |
|---|---:|---:|---:|
| Revenue | 254,453 | 273,712 | 349,529 |
| Operating margin | 3.65% | 3.72% | 3.77% |
| Earnings per share ($, diluted) | 16.56 | 17.31 | 23.13 |
| **Free cash flow** | 6,629 | 7,032 | 9,240 |

## 3. Valuation from future cash flows (discounted cash flow, "DCF")

A **discounted cash flow** valuation adds up the cash the business is expected to produce, with future cash worth less
than cash today. The rate used to discount it is the **weighted average cost of capital (WACC)**, the return investors
require for the risk they take.

| | |
|---|---:|
| Required return (WACC), from a 4.58% 10-year U.S. Treasury yield, a **beta** of 0.89 and an **equity risk premium** of 4.33% | 8.38% |
| Long-term growth after 2029 / return on new investment after 2029 | 3.0% / 25% |
| **Enterprise value** (value of the business before cash and debt) | $145.3 billion |
| **Value per share** | **$337** |
| Share price, 31 January 2025 | $979.88 |

**What the share price implies.** A **reverse DCF** asks what you would have to believe to justify $980. The answer is
7.0% growth every year forever after 2029, or a required return of only 4.8%, barely above the 10-year Treasury yield
(4.58%), as if Costco's profits were almost risk-free. Even 7% growth for another 100 years only reaches about $780.
The next five years of cash flow account for just $61 of the $980 price.

Full workings, method choices and limitations: [docs/valuation.md](docs/valuation.md).

![Discounted cash flow bridge](outputs/charts/11_dcf_bridge.png)

## 4. Comparison with similar companies ("comparable companies")

This method values Costco the way the market values similar retailers, using ratios such as **enterprise value to
EBITDA** and the **price-to-earnings ratio**. Figures are for the **last twelve months** before 31 January 2025.

| | Enterprise value / EBITDA | Price / earnings | Implied value of one Costco share |
|---|---:|---:|---:|
| Costco | 36.5x | 57.4x | (market price $980) |
| Walmart (the most expensive comparable company) | 20.2x | 40.3x | $546–$688 |
| Median of the three membership-warehouse companies (Walmart, BJ's Wholesale, PriceSmart) | 13.2x | 23.9x | $359–$408 |
| Median of all seven comparable companies | 8.8x | 18.4x | $243–$313 |

The seven comparable companies are Walmart, BJ's Wholesale, PriceSmart, Target, Kroger, Dollar General and Dollar Tree.
Using the three membership-warehouse companies as the main reference, with Walmart as the upper limit, gives about
**$360–$690 per share**. The $980 price is 42–173% above that range. The premium is specific to Costco: the sector as a
whole is not priced this high. Company choices and method: [docs/comps.md](docs/comps.md).

![Valuation multiples](outputs/charts/12_comps_multiples.png)

## 5. Sensitivity analysis and scenarios

A **sensitivity analysis** shows how much the answer moves when the assumptions change.

| | Pessimistic ("bear") | Central ("base") | Optimistic ("bull") |
|---|---:|---:|---:|
| Value per share | $263 | $337 | $400 |
| Compared with the $979.88 price | −73% | −66% | −59% |

- **Weighted by probability** (25% pessimistic, 50% central, 25% optimistic): $334.
- **Most favourable combination tested** (7.4% required return with 4.0% long-term growth): $495.
- **Valuing 2029 at a multiple instead of a growth rate:** my central case equals 10.3 times 2029 EBITDA. Even
  20 times (roughly Walmart's level at the valuation date) gives about $585; the price needs about 35 times.
- **What matters most:** adding 2 percentage points of sales growth every year adds only about 4% to value. The required
  return and how long high growth lasts matter far more.

Grids, scenario definitions and "what would change my view": [docs/sensitivity.md](docs/sensitivity.md).

![Valuation summary](outputs/charts/14_football_field.png)

## 6. External review

The model was reviewed four times using finance review skills from ClaudeFinanceLab (claudefinancelab.com), each run in a
separate conversation with no access to how the model was built: forecast, discounted cash flow, comparable companies and the memo.
Every point raised, my response and whether the model changed are recorded in
[docs/model_review_log.md](docs/model_review_log.md). One outcome: PriceSmart was added as a comparable company.

## 7. Excel model

[`outputs/COST_Valuation_Model.xlsx`](outputs/COST_Valuation_Model.xlsx) is a fully linked workbook with 908 live formulas
and no formula errors. Its 11 sheets:

- **Cover:** headline results and a colour legend.
- **Historicals:** every typed-in number has a comment giving its source in the filing.
- **Assumptions:** includes a switch between the pessimistic, central and optimistic cases.
- **Forecast:** the three linked financial statements, with a balance check.
- **Beta:** Costco's beta calculated from 60 monthly returns.
- **WACC:** the required return.
- **DCF:** the discounted cash flow valuation.
- **Sensitivity:** live tables that recalculate with the assumptions.
- **Comps:** the comparable companies.
- **Summary:** all valuation methods side by side.
- **Checks:** reconciles every headline number to the Python model; all checks read *ALL OK*.

Colour convention: blue = input, black = formula, green = link to another sheet, yellow = key assumption.
Switching the scenario reproduces the Python pessimistic ($263) and optimistic ($400) values exactly.

## 8. Data sources

- **Costco's financial statements** (fiscal years 2020–2024, plus the 2019 opening balance sheet) come directly from its
  annual reports (**Form 10-K**) and quarterly report (**Form 10-Q**) on the U.S. Securities and Exchange Commission's
  EDGAR system, read from the machine-readable (**XBRL**) data in each filing. Every number carries a link to the exact
  item in the filing.
- **Operating figures** that are only in the report text (members, renewal rates, comparable-store sales) are stored with
  the exact sentence they come from and are re-checked against the filing every time the model is built.
- **Cross-check:** 320 values were compared with the Securities and Exchange Commission's own data service; all 320 match.
- **Market data:** share prices from Yahoo Finance; interest rates and credit spreads from the Federal Reserve Bank of
  St. Louis (FRED); the equity risk premium from Professor Aswath Damodaran (New York University). Each file is
  recorded with its address, download time and a checksum.

Details: [docs/data_sources.md](docs/data_sources.md).

| Dataset | File |
|---|---|
| Income statement, balance sheet, cash flow statement ($ millions) | `data/processed/income_statement.csv`, `balance_sheet.csv`, `cash_flow.csv` |
| Segments and merchandise categories | `data/processed/segments.csv` |
| Operating figures | `data/processed/operating_metrics.csv` |
| Every number with its source link | `data/processed/financials_long.csv`, `operating_metrics_long.csv` |

## Repository layout

```
config/          company, comparable companies, valuation date and forecast assumptions
src/             Python code for every step
data/raw/        downloaded source files (large SEC files are not stored; a manifest records them)
data/manual/     figures taken from filing text, each with its quotation
data/processed/  clean datasets with a source link for every number
notebooks/       analysis notebook
docs/            methods, assumptions, sources and review log
scripts/         slide generator (Node.js)
outputs/         Excel model, tables, charts, memo and slides
tests/           101 automated checks on the data and the model
```

## Reproducing the results

Every output can be rebuilt from the original filings (Python 3.10 or later):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export SEC_USER_AGENT="Your Name your.email@example.com"
python -m src.run_all        # rebuilds data, model, Excel, charts and memo
python -m pytest -q          # 101 automated checks
```

Each step, its options and its outputs are listed in [docs/reproducing.md](docs/reproducing.md).

## Glossary

| Term | Meaning |
|---|---|
| **Beta** | How much a share tends to move with the overall stock market. Below 1 means it moves less than the market. |
| **Comparable companies** ("comps") | Valuing a company by applying the valuation ratios of similar listed companies. |
| **Discounted cash flow (DCF)** | Valuing a business as the sum of its expected future cash flows, each reduced to today's value. |
| **EBITDA** | Earnings before interest, taxes, depreciation and amortisation: a rough measure of operating cash profit. |
| **Enterprise value** | The value of the whole business: shares plus debt, minus cash. |
| **Equity risk premium** | The extra return investors demand for owning shares instead of safe government bonds. |
| **Fiscal year** | Costco's financial year, which ends on the Sunday nearest 31 August. |
| **Form 10-K / Form 10-Q** | The annual and quarterly reports that U.S. listed companies file with the Securities and Exchange Commission. |
| **Free cash flow** | Cash from operations minus spending on new warehouses and equipment. |
| **Last twelve months** | The most recent twelve months of results, which may cross two fiscal years. |
| **Price-to-earnings ratio** | Share price divided by earnings per share: how many years of current profit the price pays for. |
| **Return on invested capital** | Profit after tax as a percentage of the money invested in the business. |
| **Reverse DCF** | Working backwards from the share price to find the growth or required return it implies. |
| **Sensitivity analysis** | Recalculating the value while changing one or two assumptions at a time. |
| **Terminal value** | The value of all cash flows after the forecast period (here, after 2029). It is 81% of Costco's value in this model. |
| **Weighted average cost of capital (WACC)** | The annual return that shareholders and lenders together require; used to discount future cash. |
| **Working capital** | Money tied up in inventory and unpaid customer bills, minus money owed to suppliers. Negative means suppliers and members fund the business. |
| **XBRL** | The machine-readable tagging inside SEC filings that lets each number be read and linked automatically. |
