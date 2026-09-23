# Historical analysis: key findings (FY2020–FY2024)

*Independent academic research and valuation case study; not investment advice.*

Full workings: [`notebooks/01_historical_analysis.ipynb`](../notebooks/01_historical_analysis.ipynb).
Metric definitions: [`src/historical.py`](../src/historical.py).
All figures are computed from Costco's 10-K filings (see [data_sources.md](data_sources.md)).

## Summary table

| | FY2020 | FY2021 | FY2022 | FY2023 | FY2024 |
|---|---:|---:|---:|---:|---:|
| Net sales growth (52-week basis) | – | 17.7% | 16.0% | 4.7% | 7.0% |
| Comparable sales ex gas & FX | 9% | 13% | 11% | 5% | 6% |
| Gross margin (on net sales) | 11.20% | 11.13% | 10.48% | 10.57% | 10.92% |
| SG&A (% net sales) | 10.04% | 9.65% | 8.88% | 9.08% | 9.14% |
| Operating margin | 3.26% | 3.42% | 3.43% | 3.35% | 3.65% |
| Membership fees ÷ operating income | 65% | 58% | 54% | 56% | 52% |
| Tax rate excl. discrete items | 25.9% | 26.4% | 26.2% | 26.6% | 26.4% |
| Paid members (m) | 58.1 | 61.7 | 65.8 | 71.0 | 76.2 |
| Executive share of paid members | 39% | 41% | 44% | 45% | 46% |
| ROIC (after tax, incl. leases) | 25%* | 30% | 31% | 29% | 33% |
| Capex ÷ revenue | 1.7% | 1.8% | 1.7% | 1.8% | 1.9% |
| Operating working capital ÷ revenue | −6.0% | −5.8% | −4.5% | −4.9% | −4.8% |
| Free cash flow ($m) | 6,051 | 5,370 | 3,501 | 6,745 | 6,629 |
| Regular dividend payout | 30% | 26% | 26% | 27% | 26% |

\*FY2020 ROIC uses year-end capital because FY2019 predates lease accounting (ASC 842).

## Seven findings

1. **Growth has normalized.** Revenue compounded at 11% a year from FY2020 to FY2024, but FY2021–22 was inflated by pandemic demand, inflation and gasoline prices.
   The normalized FY2023–24 run-rate is 5–6% comparable sales (ex gas & FX), plus ~2 points from new warehouses.
2. **The fee is the profit engine.** Membership fees are 1.9% of revenue but 52% of operating income.
   Fee income is recurring, with a 92.9% U.S./Canada renewal rate. That makes Costco's earnings much steadier than a 3.6% margin suggests.
3. **Margins are thin and stable.** Gross margin stays in a 10.5–11.2% band. Operating-margin gains came from SG&A leverage, not pricing, and there is no margin-expansion story to underwrite.
4. **The FY2024 fee increase is a known tailwind.** Fee income per member was flat at about $65–66 through FY2024. The $60→$65 (Executive $120→$130)
   increase effective 1 Sep 2024 was disclosed in the FY2024 10-K. Fees are recognized over the membership year, so it phases in over FY2025–26.
5. **Returns on capital are exceptional.** ROIC is about 30%, and incremental ROIC FY2020→24 is about 49%.
   Capex runs at about 2x depreciation because the company keeps opening warehouses, and each new dollar earns more than the existing base.
6. **Growth releases cash.** Operating working capital is about −5% of revenue: suppliers are paid after goods sell, and members pay upfront.
   So growth needs no working-capital investment. FY2022's inventory build was the exception.
7. **Surplus cash goes out as special dividends.** $11.1bn in specials plus a steady 26–30% regular payout, while buybacks were small (5% of operating cash) and the share count stayed flat.
   The balance sheet ends FY2024 with $5.2bn net cash ($1.2bn after lease liabilities).

## What carries into the Phase 3 forecast

| Driver | Historical anchor |
|---|---|
| Warehouse growth | 20–29 net new/yr (2.5–3.4%) |
| Comparable sales | 5–6% ex gas & FX (FY2023–24) |
| Membership fees | ~7% member growth, rising Executive mix, 2024 fee increase |
| Gross margin | ~10.9% (FY2024), 10.5–11.2% range |
| SG&A | ~9.1% of net sales, with limited further leverage |
| Tax rate | ~26% (ex-discrete) |
| Capex | 1.7–1.9% of revenue |
| Working capital | about −5% of revenue |

## Caveats

- **53-week adjustment:** FY2023 is scaled by 52/53. Costco does not disclose the dollar value of the extra week, so this is an approximation.
- **Growth split:** "New warehouses & other" is a residual (52-week net sales growth minus reported comparable sales). Comps are reported in whole percentages, so the residual is approximate.
- **Membership metrics:** fee income per member is a blended figure. Paid members include business affiliates, and fee income includes Executive upgrade fees.
- **ROIC and leases:** ROIC adds lease liabilities to capital while NOPAT still includes lease expense, which slightly understates ROIC.
