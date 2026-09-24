# Model review log

This log records every external review of the model: ClaudeFinanceLab skills, peers and mentors. For each point it records
what was raised, whether we changed the model, and why. Where a tool gets a different valuation from the same inputs,
the cause is identified: for example the mid-year convention, the tax rate, or how net debt is defined.

| # | Date | Phase | Reviewer / tool | Point raised | Our response | Model changed? |
|---|---|---|---|---|---|---|
| 1a | 23 Sep 2026 | 3 – Forecast | ClaudeFinanceLab: Three-Statement Model Checker | Instead of only checking, the reviewer rebuilt the FY25–29 forecast in its own workbook from the packet assumptions. | Used as an independent replication (reconciliation below). Revenue matches to within 0.03% and operating income to within 0.6% in every year. | No |
| 1b | 23 Sep 2026 | 3 – Forecast | same | FY25 fee growth of ~10.8% vs. +7.8% in Q1 needs a back-half acceleration. | Already flagged in docs/assumptions.md. The Sep 2024 increase is recognized ratably over the membership year, so the effect builds through Q2–Q4 by construction. Only the FY25/FY26 timing is at stake (the run-rate is the same by FY26). A ~$150m FY25 shortfall is worth about $0.25/share. | No |
| 1c | 23 Sep 2026 | 3 – Forecast | same | With no special dividends, cash builds to $25–31bn by FY29. | Already disclosed (docs/assumptions.md). The DCF values unlevered FCF plus net cash at 24 Nov 2024, so later cash build changes EPS (interest income), not value. The memo lists a special dividend as a catalyst. | No |
| 1d | 23 Sep 2026 | 3 – Forecast | same | SG&A of 9.20% is only 6bp worse than FY24, although Q1 SG&A rose 14bp. | Already flagged: Q1 is distorted by gasoline deflation (it shrinks net sales, the denominator). Sensitivity: gross margin ±30bp (the same as SG&A ∓30bp) moves value $310–$364. | No |
| 1e | 23 Sep 2026 | 3 – Forecast | same | ROIC of 36–39% is above Costco's ~30%. | This applies to the reviewer's condensed balance sheet (operating capital only). Our ROIC includes leases and all operating assets: 33% in FY2024. | No |
| 1f | 23 Sep 2026 | 3 – Forecast | same | Offered to compare the forecast with FY2025 actuals. | Out of scope for the valuation: it is point-in-time at 31 Jan 2025, and FY2025 results were filed later. Could be added as a clearly labelled back-test section. | No |
| 2 | | 4 – WACC & DCF | ClaudeFinanceLab: DCF Model Builder | | | |
| 3 | | 5 – Comparable companies | ClaudeFinanceLab: Comparable Company Analysis | | | |
| 4 | | 8 – Memo and slides | ClaudeFinanceLab: Investment Committee Memo Writer | | | |

## Reconciliation: review 1 (independent rebuild of the forecast)

| $m | FY25E ours | FY25E reviewer | FY29E ours | FY29E reviewer | Cause of difference |
|---|---:|---:|---:|---:|---|
| Total revenue | 273,712 | 273,704 | 349,529 | 349,448 | Rounding in unit-growth inputs |
| Membership fees | 5,357 | 5,349 | 7,000 | 6,918 | We apply fee per member to **average** paid members; the reviewer grows the prior-year fee total by year-end member growth |
| Operating income | 10,187 | 10,179 | 13,165 | 13,083 | The membership-fee difference (it flows through ~100%) |
| Net income | 7,702 | 7,737 | 10,290 | 10,236 | Reviewer earns 4.0%/3.5% on cash; we use 3.5% falling to 3.0% after the late-2024 rate cuts |
| Free cash flow | 7,032 | 6,100 | 9,240 | 8,072 | Reviewer deducts stock-based compensation (~$0.9–1.1bn) as if it were cash. Our DCF also treats SBC as a cost (no add-back), so the valuation is on the same basis |
| Net cash | 9,499 | 8,558 | 30,187 | 24,931 | Same SBC point: SBC is non-cash, so the reviewer's balance sheet understates cash by the cumulative SBC. Its own summary text says ~$31bn, in line with ours |

Conclusion: the independent rebuild confirms the forecast mechanics. No change to the model.
