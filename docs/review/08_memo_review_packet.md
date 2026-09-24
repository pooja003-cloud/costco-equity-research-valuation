# Review packet: Phase 8 investment memo and slides

For ClaudeFinanceLab's **Investment Committee Memo Writer** skill. Log the results in [`../model_review_log.md`](../model_review_log.md).

## Prompt

```
Act as an investment committee reviewer. Critique the attached two-page equity research memo on Costco (valuation date
31 Jan 2025) and its one-slide thesis and one-slide risks. Check that: the conclusion follows from the evidence; every
number is consistent across sections; the forecast assumptions and valuation method are stated clearly enough for a
reader to challenge them; the risks and "what would change my view" triggers are specific and measurable; and the
limitations are honest. Point out anything that reads as advocacy rather than analysis. Do not invent company-specific facts.
This is an independent academic case study, not investment advice.
```

## What to paste

1. The full text of [`../investment_memo.md`](../investment_memo.md).
2. Slide text, from `outputs/COST_Equity_Research_Deck.pptx` (slides 2 and 4):
   - **Thesis:** fee engine (fees 52% of FY2024 operating income, 92.9% renewal); cost structure (working capital −4.8%
     of revenue, ROIC ~33%); steady growth (revenue +6.6% a year to $349.5bn by FY2029, EPS $23.13). Price $980 vs.
     base-case DCF $337; the price implies 7.0% perpetual growth or a 4.8% WACC; 57x LTM earnings vs. a 16x peer median.
   - **What would change my view:** price toward $452–$548 (Walmart/BJ's multiples); evidence of ~8% growth for decades
     (76 years needed after FY2029); a lasting fall in the cost of capital (each 0.5pp off WACC adds ~$33; the price
     needs 4.8%). A strong quarter alone would not: operating upside tops out at $380.

## Questions to ask specifically

- Is "overvalued on fundamentals" supported, given that the reverse DCF shows the market may use a much lower discount rate?
- Is terminal value at 81% of EV disclosed prominently enough?
- Are any numbers in the memo inconsistent with the tables in `outputs/tables/`?
