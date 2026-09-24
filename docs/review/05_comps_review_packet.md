# Review packet: Phase 5 comparable companies

For ClaudeFinanceLab's **Comparable Company Analysis** skill. Log the results in [`../model_review_log.md`](../model_review_log.md).

## Prompt

```
Help me challenge a comparable-company analysis for Costco (valuation date 31 Jan 2025). Evaluate my peer set against
objective criteria (business model, geography, growth, margin profile, capital intensity, customer base), suggest peers
I should add or remove and why, and check whether my multiple choices (EV/Revenue, EV/EBITDA, P/E, P/S, growth-adjusted
EV/EBITDA) and EV definition are appropriate. Do not invent company-specific facts.
```

## What to paste

**Peers and tiers:**
- Tier 1 (membership warehouse / scale grocery): BJ's, Walmart.
- Tier 2 (mass merchant / supermarket): Target, Kroger.
- Tier 3 (value / discount): Dollar General, Dollar Tree.
- Excluded: Amazon, Albertsons, Sprouts.

**Method:**
- LTM GAAP to the latest quarter before 31 Jan 2025, 52-week basis.
- EV = market cap + debt incl. finance leases + NCI − cash; operating leases excluded.

**Multiples (EV/EBITDA, P/E):**
- Costco 36.5x, 57.4x
- Walmart 20.2x, 40.3x
- BJ's 13.2x, 23.9x
- Target 8.7x, 14.7x
- Kroger 7.5x, 16.4x
- Dollar General 7.3x, 11.7x
- Dollar Tree: not meaningful (negative LTM earnings)
- Peer median: 8.7x, 16.4x

**Implied Costco value per share (peer median):**
- EV/EBITDA $240; P/E $280; EV/Revenue $384
- Tier 1 median: EV/EBITDA $452, P/E $548 (EV/Revenue $570); Walmart alone: EV/EBITDA $546, P/E $688
- DCF: $337; price: $979.88
