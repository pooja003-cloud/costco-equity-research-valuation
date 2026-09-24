# Review packet: Phase 4 WACC and DCF

For ClaudeFinanceLab's **DCF Model Builder** skill (or its Valuation MCP server). Enter the inputs below, compare its enterprise value,
WACC and terminal value with ours, and explain every difference in [`../model_review_log.md`](../model_review_log.md). Common causes:
- the mid-year convention;
- terminal cash-flow normalization;
- tax treatment;
- the net-debt definition (operating leases).

## Prompt

```
Act as an equity-research associate reviewing a DCF. Build a DCF from the inputs below, then compare your enterprise value,
WACC and terminal value with mine and explain any difference. Then list missing assumptions, internal inconsistencies,
and the questions an investment committee would ask. Do not invent company-specific facts.
```

## Inputs (Costco, valuation date 31 Jan 2025, $m)

- **Unlevered FCF, FY2025–FY2029:** 5,992 / 6,473 / 6,757 / 7,141 / 7,573. These are full-year figures. FY2025 is a stub: only 77% of the year is counted (the period after 24 Nov 2024), so 4,610 enters the valuation.
- **FCF build:** EBIT 10,187 → 13,165; tax 26%; D&A 2,439 → 3,379; capex 5,000 → 6,466; working capital releases ~0.9–1.0bn a year. Stock-based compensation is not added back.
- **WACC 8.38%:**
  - Rf 4.58% (10y UST);
  - Blume-adjusted beta 0.8946 (raw 0.8426, 60-month regression);
  - ERP 4.33% (Damodaran, Jan 2025);
  - pre-tax cost of debt 5.155% (tax 26%, so 3.815% after tax);
  - weights: equity 98.47%, debt 1.53%. Unrounded WACC 8.3825%.
- **Terminal value:** growth 3.0%. Value-driver terminal FCF = NOPAT(FY2030) × (1 − g/RONIC), with RONIC 25%, which gives $8,830m.
- **Timing:** mid-year convention. Discount times 0.20 / 1.08 / 2.08 / 3.08 / 4.09 years. The TV is discounted at 4.09 years, consistent with the mid-year flows.
- **Net debt:** cash + short-term investments 11,827; debt 5,842; finance leases 1,498. Operating leases (~2.6bn) are excluded because their cost is already in EBIT.
- **Shares:** 444.8m diluted.
- **Our result:**
  - EV $145.3bn; PV of TV $118.1bn (81% of EV);
  - equity $149.8bn, **$337/share** vs. $979.88 price;
  - implied exit multiple 10.3× FY2029 EBITDA at year-end (9.9× on the mid-year basis);
  - reverse DCF: the price implies 7.0% perpetual growth, or a 4.8% WACC.
