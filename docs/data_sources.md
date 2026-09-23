# Data sources and data-quality notes

Every historical number in this project comes from Costco's SEC filings. There are no third-party data vendors.

## Filings used

| Form | Fiscal year | Period end | Filed | Accession | Link |
|---|---|---|---|---|---|
| 10-K | FY2020 | 2020-08-30 | 2020-10-07 | 0000909832-20-000017 | [cost-20200830.htm](https://www.sec.gov/Archives/edgar/data/909832/000090983220000017/cost-20200830.htm) |
| 10-K | FY2021 | 2021-08-29 | 2021-10-06 | 0000909832-21-000014 | [cost-20210829.htm](https://www.sec.gov/Archives/edgar/data/909832/000090983221000014/cost-20210829.htm) |
| 10-K | FY2022 | 2022-08-28 | 2022-10-05 | 0000909832-22-000021 | [cost-20220828.htm](https://www.sec.gov/Archives/edgar/data/909832/000090983222000021/cost-20220828.htm) |
| 10-K | FY2023 | 2023-09-03 (53 weeks) | 2023-10-11 | 0000909832-23-000042 | [cost-20230903.htm](https://www.sec.gov/Archives/edgar/data/909832/000090983223000042/cost-20230903.htm) |
| 10-K | FY2024 | 2024-09-01 | 2024-10-09 | 0000909832-24-000049 | [cost-20240901.htm](https://www.sec.gov/Archives/edgar/data/909832/000090983224000049/cost-20240901.htm) |
| 10-Q | Q1 FY2025 | 2024-11-24 | 2024-12-19 | 0000909832-24-000079 | [cost-20241124.htm](https://www.sec.gov/Archives/edgar/data/909832/000090983224000079/cost-20241124.htm) |

The Q1 FY2025 10-Q is the most recent filing public on the valuation date (31 Jan 2025). It is used only for
the valuation-date balance sheet and share count (Phase 4).

## How each number is sourced

| Data | Method | Where to trace it |
|---|---|---|
| Income statement, balance sheet, cash flow | Tagged inline-XBRL facts read from the 10-K itself (`src/extract_financials.py`) | `data/processed/financials_long.csv` has `source_url`, a link to the exact tagged fact (`…htm#fact-id`) |
| Segment and merchandise-category data | Dimensional XBRL facts from the segment and revenue notes | same file, `statement = segments` |
| Lease liabilities | Lease note (XBRL); finance leases derived as total − operating where only the total is tagged | same file, `statement = lease_note` (the derivation is recorded in `note`) |
| Warehouses | XBRL `us-gaap:NumberOfStores` | `data/processed/operating_metrics_long.csv` |
| Members, renewal rates, comparable sales, floor space, fees | Hand-collected from the 10-K text, with the **verbatim quote** stored next to each number | `data/manual/operating_metrics.csv`; `src/operating_metrics.py` re-opens the filing and fails the build if a quote or number is not found word-for-word |

**Which filing is used.** Each statement for each year comes from the *most recent* 10-K that presents it,
so all years share the same line-item presentation. All items for one statement and year come from one filing.

## Verification

- `python -m pytest -q` runs 30 checks:
  - the income statement foots from revenue to net income;
  - EPS equals net income divided by diluted shares;
  - the balance sheet balances for every year (FY2019–FY2024);
  - the cash flow statement adds up to the change in cash and ties to the balance sheet;
  - segment and category data sum to the consolidated totals;
  - every number has a source;
  - the verifier rejects a made-up quote.
- **Independent cross-check.** 320 of the extracted values were compared with the SEC's own XBRL companyfacts API
  for the same accession and period, and all 320 match. The other 5 are Costco-specific (`cost:`) tags, which the API does not serve.
- Results: `data/processed/source_checks.csv`.

## Data-quality notes (things an analyst needs to know)

1. **Preopening expense was reclassified into SG&A.** Starting with the FY2022 10-K, Costco no longer
   shows preopening as its own line. FY2020 SG&A is $16,387m as restated, vs. $16,332m SG&A + $55m preopening
   as originally reported. FY2021 is $18,537m vs. $18,461m + $76m. Operating income is unchanged.
2. **Segment operating income was re-allocated.** Later 10-Ks restate FY2020–21 operating income between the U.S. and Canada
   segments (e.g., FY2020 U.S. $3,822m restated vs. $3,633m originally). The consolidated total is unchanged. We use the restated split.
3. **FY2023 had 53 weeks.** Growth rates for FY2023 are flattered, and FY2024 growth is understated, by about one week of sales
   (~2%). Costco's reported comparable sales adjust for this, and FY2024 comps use comparable retail weeks.
4. **Merchandise categories changed in FY2021.** Hardlines and Softlines were merged into Non-foods. FY2020 category data
   uses the restated four-category split from the FY2022 10-K.
5. **Leases (ASC 842) were adopted in FY2020.** FY2019 has no operating-lease assets or liabilities on the balance sheet.
6. **Special dividends:** $10/share in FY2021 (Dec 2020) and $15/share in FY2024 (Jan 2024). These explain the jumps
   in dividends paid ($5.7bn and $9.0bn). They are not recurring.
7. **Noncontrolling interest.** Costco bought out its Taiwan joint-venture partner in FY2022, so NCI goes to ~$0 from FY2023.
8. **Metric definitions shift over time:**
   - Renewal rates are rounded to whole percentages in FY2020–22 and shown to one decimal from FY2023.
   - The executive-member share is quoted on different bases (U.S. & Canada excluding affiliates in FY2021–22; all paid members from FY2023).
     We therefore use the executive-member **count**, which is consistent across years.
   - In FY2020 Costco standardized its global membership count, adding ~1.3m paid members with no change to fee income.
9. **Membership fee increase:** effective 1 Sep 2024 (first day of FY2025), the U.S./Canada fee rose from $60 to $65
   and the Executive fee from $120 to $130. This was disclosed in the FY2024 10-K, so it was known on the valuation date.
   Fee income is recognized ratably over the membership year, so the increase phases in over FY2025–26.

## Reproducing

```bash
export SEC_USER_AGENT="Your Name your.email@example.com"
python -m src.sec_fetch            # downloads raw files; data/raw/manifest.csv records the SHA-256 of each
python -m src.extract_financials   # statements, segments, lease note + source checks
python -m src.operating_metrics    # verifies hand-collected metrics against the filing text
python -m pytest -q
```
