"""Build Costco's FY2019-FY2024 financial dataset from the 10-K inline XBRL, with a source for every number.

Source rule
-----------
Each statement for each fiscal year comes from the **most recent 10-K that presents it**. A 10-K shows
three years of income statement and cash flow, and two years of balance sheet. Taking the latest one means
every year uses the company's current line-item presentation. Example: from FY2022 Costco stopped showing
preopening expense as its own line and folded it into SG&A, and restated FY2020-2021 to match.
All line items for a given statement and year come from the *same* filing, so reclassifications cannot be
double-counted. The originally reported values are kept, and any difference is listed in
``data/processed/source_checks.csv``.

Outputs (all in data/processed/)
--------------------------------
financials_long.csv   one row per number: value, XBRL concept, dimensions, period, accession, link to the tagged fact
income_statement.csv, balance_sheet.csv, cash_flow.csv, segments.csv   wide tables in $ millions
source_checks.csv     restatements across filings and a cross-check against the SEC companyfacts API
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd

from src.config import PROCESSED, RAW, RAW_SEC, TICKER
from src.ixbrl import read_facts

# ----------------------------------------------------------------------------------------------
# Line-item map: key -> (label, [XBRL concepts in order of preference], required dims, optional)
# A missing optional item means the filing does not show it as a separate line, so it is set to 0.
# ----------------------------------------------------------------------------------------------
P = "srt:ProductOrServiceAxis="
INCOME_STATEMENT = {
    "net_sales":            ("Net sales", ["RevenueFromContractWithCustomerExcludingAssessedTax"], P + "us-gaap:ProductMember", False),
    "membership_fees":      ("Membership fees", ["RevenueFromContractWithCustomerExcludingAssessedTax"], P + "us-gaap:MembershipMember", False),
    "total_revenue":        ("Total revenue", ["Revenues"], "", False),
    "merchandise_costs":    ("Merchandise costs", ["CostOfGoodsAndServicesSold", "CostOfRevenue"], "", False),
    "sga":                  ("Selling, general and administrative", ["SellingGeneralAndAdministrativeExpense"], "", False),
    "preopening":           ("Preopening expenses (in SG&A from FY2022 presentation)", ["PreOpeningCosts"], "", True),
    "operating_income":     ("Operating income", ["OperatingIncomeLoss"], "", False),
    "interest_expense":     ("Interest expense", ["InterestExpense"], "", False),
    "interest_income_other":("Interest income and other, net", ["InterestAndOtherIncome", "OtherNonoperatingIncomeExpense", "NonoperatingIncomeExpense"], "", False),
    "pretax_income":        ("Income before income taxes", ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"], "", False),
    "income_tax":           ("Provision for income taxes", ["IncomeTaxExpenseBenefit"], "", False),
    "net_income_incl_nci":  ("Net income including noncontrolling interests", ["ProfitLoss"], "", False),
    "nci_income":           ("Net income attributable to noncontrolling interests", ["NetIncomeLossAttributableToNoncontrollingInterest"], "", True),
    "net_income":           ("Net income attributable to Costco", ["NetIncomeLoss"], "", False),
    "eps_basic":            ("EPS - basic ($)", ["EarningsPerShareBasic"], "", False),
    "eps_diluted":          ("EPS - diluted ($)", ["EarningsPerShareDiluted"], "", False),
    "shares_basic":         ("Weighted avg. shares - basic (m)", ["WeightedAverageNumberOfSharesOutstandingBasic"], "", False),
    "shares_diluted":       ("Weighted avg. shares - diluted (m)", ["WeightedAverageNumberOfDilutedSharesOutstanding"], "", False),
}
BALANCE_SHEET = {
    "cash":                       ("Cash and cash equivalents", ["CashAndCashEquivalentsAtCarryingValue"], "", False),
    "short_term_investments":     ("Short-term investments", ["ShortTermInvestments"], "", False),
    "receivables":                ("Receivables, net", ["ReceivablesNetCurrent"], "", False),
    "inventories":                ("Merchandise inventories", ["InventoryNet"], "", False),
    "other_current_assets":       ("Other current assets", ["OtherAssetsCurrent"], "", False),
    "total_current_assets":       ("Total current assets", ["AssetsCurrent"], "", False),
    "ppe_net":                    ("Property and equipment, net", ["PropertyPlantAndEquipmentNet"], "", False),
    "operating_lease_rou":        ("Operating lease right-of-use assets", ["OperatingLeaseRightOfUseAsset"], "", False),
    "other_lt_assets":            ("Other long-term assets", ["OtherAssetsNoncurrent"], "", False),
    "total_assets":               ("Total assets", ["Assets"], "", False),
    "accounts_payable":           ("Accounts payable", ["AccountsPayableCurrent"], "", False),
    "accrued_salaries":           ("Accrued salaries and benefits", ["EmployeeRelatedLiabilitiesCurrent"], "", False),
    "accrued_member_rewards":     ("Accrued member rewards", ["AccruedLiabilitiesCurrent", "CustomerLoyaltyProgramLiabilityCurrent"], "", False),
    "deferred_membership_fees":   ("Deferred membership fees", ["DeferredRevenueCurrent"], "", False),
    "current_debt":               ("Current portion of long-term debt", ["LongTermDebtCurrent"], "", False),
    "other_current_liabilities":  ("Other current liabilities", ["OtherLiabilitiesCurrent"], "", False),
    "total_current_liabilities":  ("Total current liabilities", ["LiabilitiesCurrent"], "", False),
    "long_term_debt":             ("Long-term debt, excluding current portion", ["LongTermDebtNoncurrent"], "", False),
    "lt_operating_lease_liab":    ("Long-term operating lease liabilities", ["OperatingLeaseLiabilityNoncurrent"], "", False),
    "other_lt_liabilities":       ("Other long-term liabilities", ["OtherLiabilitiesNoncurrent"], "", False),
    "total_liabilities":          ("Total liabilities", ["Liabilities"], "", False),
    "costco_equity":              ("Total Costco stockholders' equity", ["StockholdersEquity"], "", False),
    "nci":                        ("Noncontrolling interests", ["MinorityInterest"], "", True),
    "total_equity":               ("Total equity", ["StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"], "", False),
    "total_liabilities_equity":   ("Total liabilities and equity", ["LiabilitiesAndStockholdersEquity"], "", False),
    "shares_outstanding":         ("Common shares outstanding (m)", ["CommonStockSharesOutstanding"], "", False),
}
CASH_FLOW = {
    "cfo":                  ("Net cash provided by operating activities", ["NetCashProvidedByUsedInOperatingActivities"], "", False),
    "d_and_a":              ("Depreciation and amortization", ["DepreciationDepletionAndAmortization"], "", False),
    "sbc":                  ("Stock-based compensation", ["ShareBasedCompensation"], "", False),
    "chg_inventories":      ("(Increase) decrease in merchandise inventories", ["IncreaseDecreaseInInventories"], "", False),
    "chg_accounts_payable": ("Increase in accounts payable", ["IncreaseDecreaseInAccountsPayable"], "", False),
    "chg_other_wc":         ("Other operating assets and liabilities, net", ["IncreaseDecreaseInOtherOperatingCapitalNet"], "", False),
    "capex":                ("Additions to property and equipment", ["PaymentsToAcquirePropertyPlantAndEquipment"], "", False),
    "cfi":                  ("Net cash used in investing activities", ["NetCashProvidedByUsedInInvestingActivities"], "", False),
    "dividends_paid":       ("Cash dividend payments", ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"], "", False),
    "buybacks":             ("Repurchases of common stock", ["PaymentsForRepurchaseOfCommonStock"], "", False),
    "debt_issued":          ("Proceeds from issuance of long-term debt", ["ProceedsFromIssuanceOfLongTermDebt"], "", True),
    "debt_repaid":          ("Repayments of long-term debt", ["RepaymentsOfLongTermDebt"], "", True),
    "cff":                  ("Net cash used in financing activities", ["NetCashProvidedByUsedInFinancingActivities"], "", False),
    "fx_effect":            ("Effect of exchange rates on cash", ["EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "EffectOfExchangeRateOnCashAndCashEquivalents"], "", False),
    "net_change_cash":      ("Net change in cash and cash equivalents", ["CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect", "CashAndCashEquivalentsPeriodIncreaseDecrease"], "", False),
    "income_taxes_paid":    ("Income taxes paid (supplemental)", ["IncomeTaxesPaid"], "", False),
    "interest_paid":        ("Interest paid (supplemental)", ["InterestPaidNet", "InterestPaid"], "", False),
}
# Lease-note disclosures, needed for the net-debt definition in the DCF. These are notes, not statement
# lines, so each value comes from the latest filing that discloses it. Newer 10-Ks show only the total
# of operating + finance lease liabilities, so finance leases are derived as total - operating when needed.
LEASE_NOTE = {
    "operating_lease_liab_total": ("Operating lease liabilities (current + long-term)", ["OperatingLeaseLiability"]),
    "total_lease_liab":           ("Total lease liabilities (operating + finance)", ["OperatingLeaseandFinanceLeaseLiabilities"]),
    "finance_lease_liab_total":   ("Finance lease liabilities (current + long-term)", ["FinanceLeaseLiability"]),
}
STATEMENTS = {"income_statement": INCOME_STATEMENT, "balance_sheet": BALANCE_SHEET, "cash_flow": CASH_FLOW}
ANCHOR = {"income_statement": "Revenues", "balance_sheet": "Assets", "cash_flow": "NetCashProvidedByUsedInOperatingActivities"}
# Years a 10-K presents on the face of each statement (the balance sheet shows 2 years, the others 3).
# Older years can appear elsewhere in a filing (notes, selected data), but those do not count here.
YEARS_PRESENTED = {"income_statement": 3, "balance_sheet": 2, "cash_flow": 3}

# Geographic segments. The member name for Other International changed in FY2022.
SEG = "srt:ConsolidationItemsAxis=us-gaap:OperatingSegmentsMember; srt:StatementGeographicalAxis="
SEGMENT_MEMBERS = {
    "United States": ["country:US"],
    "Canada": ["country:CA"],
    "Other International": ["cost:OtherInternationalMember", "cost:OtherInternationalOperationsMember"],
}
SEGMENT_CONCEPTS = {
    "revenue": ["Revenues"],
    "operating_income": ["OperatingIncomeLoss"],
    "d_and_a": ["DepreciationDepletionAndAmortization"],
    "capex": ["SegmentExpenditureAdditionToLongLivedAssets", "PaymentsToAcquirePropertyPlantAndEquipment"],
    "ppe_net": ["PropertyPlantAndEquipmentNet"],
    "total_assets": ["Assets"],
}
CATEGORY_MEMBERS = {
    "Foods and sundries": "cost:FoodandSundriesMember",
    "Non-foods": "cost:NonFoodsMember",
    "Fresh foods": "cost:FreshFoodMember",
    "Warehouse ancillary and other": "cost:OtherMember",
}


def fiscal_year_of(end: str) -> int:
    """Costco FYs end on the Sunday nearest 31 Aug. A period ending Aug-Sep of year Y is FY Y."""
    d = date.fromisoformat(end)
    if d.month not in (8, 9):
        raise ValueError(f"{end} is not a fiscal year-end")
    return d.year


def load_all_10k_facts() -> pd.DataFrame:
    idx = pd.read_csv(RAW / "filing_index.csv")
    frames = []
    for _, f in idx[idx.form == "10-K"].iterrows():
        df = read_facts(f.local_file).copy()
        df["concept"] = df.concept.str.split(":").str[-1]
        for col in ["accession", "filing_date", "url"]:
            df[col] = f[col]
        df["filing_fy"] = f.fiscal_year
        frames.append(df)
    facts = pd.concat(frames, ignore_index=True)
    ends = pd.to_datetime(facts.end)
    starts = pd.to_datetime(facts.start)
    days = (ends - starts).dt.days
    annual = (facts.period_type == "duration") & days.between(350, 380)
    fy_end = (facts.period_type == "instant") & ends.dt.month.isin([8, 9])
    facts = facts[annual | fy_end].copy()
    facts["fiscal_year"] = pd.to_datetime(facts.end).dt.year
    # An instant at FY-end is valid only if it matches a real FY-end, i.e. the end of some annual duration
    valid_ends = set(facts.loc[facts.period_type == "duration", "end"]) | set(idx.period_end)
    return facts[facts.end.isin(valid_ends) | (facts.period_type == "duration")]


def _scale(value: float, key: str, concept: str) -> float:
    if key.startswith("eps") or "PerShare" in concept:
        return value
    return value / 1e6  # USD -> $ millions; shares -> millions


def _row(key, label, statement, fy, fact, value_m, note=""):
    return {
        "statement": statement, "line_item": key, "label": label, "fiscal_year": fy,
        "value": value_m, "concept": None if fact is None else fact.concept,
        "dims": None if fact is None else fact.dims,
        "period_start": None if fact is None else fact.start,
        "period_end": None if fact is None else fact.end,
        "accession": None if fact is None else fact.accession,
        "filing_date": None if fact is None else fact.filing_date,
        "fact_id": None if fact is None else fact.fact_id,
        "source_url": None if fact is None else f"{fact.url}#{fact.fact_id}",
        "note": note,
    }


def extract_statements(facts: pd.DataFrame, years: dict[str, list[int]]) -> list[dict]:
    rows = []
    for statement, items in STATEMENTS.items():
        for fy in years[statement]:
            # choose the latest 10-K that presents this statement for this FY
            anchor = facts[(facts.concept == ANCHOR[statement]) & (facts.n_dims == 0) & (facts.fiscal_year == fy)
                           & (facts.filing_fy - fy < YEARS_PRESENTED[statement])]
            if anchor.empty:
                raise RuntimeError(f"No filing presents the {statement} for FY{fy}")
            accn = anchor.sort_values("filing_date").iloc[-1].accession
            pool = facts[(facts.accession == accn) & (facts.fiscal_year == fy)]
            for key, (label, concepts, dims, optional) in items.items():
                fact = None
                for c in concepts:
                    hit = pool[(pool.concept == c) & (pool.dims == dims)]
                    if not hit.empty:
                        fact = hit.iloc[0]
                        break
                if fact is None:
                    if not optional:
                        raise RuntimeError(f"FY{fy} {statement}: no value for {key} in {accn}")
                    rows.append(_row(key, label, statement, fy, None, 0.0,
                                     note=f"Not presented as a separate line in {accn}; set to 0"))
                    continue
                rows.append(_row(key, label, statement, fy, fact, _scale(fact.value, key, fact.concept)))
    return rows


def extract_lease_note(facts: pd.DataFrame, fys: list[int]) -> list[dict]:
    rows = []
    for fy in fys:
        got = {}
        for key, (label, concepts) in LEASE_NOTE.items():
            hit = facts[facts.concept.isin(concepts) & (facts.dims == "") & (facts.fiscal_year == fy)
                        & (facts.period_type == "instant")].sort_values("filing_date")
            if hit.empty:
                continue
            fact = hit.iloc[-1]
            got[key] = fact.value / 1e6
            rows.append(_row(key, label, "lease_note", fy, fact, got[key]))
        if "finance_lease_liab_total" not in got and {"total_lease_liab", "operating_lease_liab_total"} <= got.keys():
            v = got["total_lease_liab"] - got["operating_lease_liab_total"]
            rows.append(_row("finance_lease_liab_total", LEASE_NOTE["finance_lease_liab_total"][0], "lease_note", fy, None, v,
                             note="Derived: total lease liabilities - operating lease liabilities (both tagged in the lease note)"))
    return rows


def extract_segments(facts: pd.DataFrame, fys: list[int]) -> list[dict]:
    rows = []
    for fy in fys:
        seg_rev = facts[(facts.concept == "Revenues") & facts.dims.str.startswith(SEG, na=False) & (facts.fiscal_year == fy)]
        accn = seg_rev.sort_values("filing_date").iloc[-1].accession
        pool = facts[(facts.accession == accn) & (facts.fiscal_year == fy)]
        for metric, concepts in SEGMENT_CONCEPTS.items():
            for seg, members in SEGMENT_MEMBERS.items():
                fact = None
                for c in concepts:
                    hit = pool[(pool.concept == c) & pool.dims.isin([SEG + m for m in members])]
                    if not hit.empty:
                        fact = hit.iloc[0]
                        break
                if fact is None:
                    continue
                rows.append(_row(f"segment_{metric}", f"{seg}: {metric.replace('_', ' ')}", "segments", fy, fact, fact.value / 1e6))
        # merchandise categories (share of net sales). The FY2020 10-K used a different split
        # (hardlines/softlines), so we take the latest filing that uses the current four categories.
        cat = facts[(facts.concept == "RevenueFromContractWithCustomerExcludingAssessedTax")
                    & (facts.dims == P + CATEGORY_MEMBERS["Non-foods"]) & (facts.fiscal_year == fy)]
        if cat.empty:
            continue
        accn_c = cat.sort_values("filing_date").iloc[-1].accession
        pool_c = facts[(facts.accession == accn_c) & (facts.fiscal_year == fy)]
        for name, member in CATEGORY_MEMBERS.items():
            hit = pool_c[(pool_c.concept == "RevenueFromContractWithCustomerExcludingAssessedTax") & (pool_c.dims == P + member)]
            if not hit.empty:
                rows.append(_row("category_sales", f"Net sales: {name}", "segments", fy, hit.iloc[0], hit.iloc[0].value / 1e6))
    return rows


def _s(x) -> str:
    """Blank-safe string: None and NaN both become "". pandas 2 and 3 store missing text differently."""
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) or x is pd.NA else str(x)


def source_checks(facts: pd.DataFrame, long: pd.DataFrame) -> pd.DataFrame:
    """(a) Values that differ between filings (restatements/reclassifications).
       (b) Agreement with the SEC companyfacts API for the same accession and period."""
    out = []
    # (a) restatements
    for _, r in long[long.concept.notna()].iterrows():
        same = facts[(facts.concept == r.concept) & (facts.dims.fillna("") == _s(r.dims)) & (facts.end == r.period_end)
                     & (facts.start.fillna("") == _s(r.period_start))]
        for _, s in same.iterrows():
            v = _scale(s.value, r.line_item, s.concept)
            if abs(v - r.value) > 0.5 and not r.line_item.startswith("eps"):
                out.append({"check": "restated_in_other_filing", "line_item": r.line_item, "fiscal_year": r.fiscal_year,
                            "selected_value": r.value, "other_value": v, "other_accession": s.accession, "status": "INFO"})
    # line items that changed concept between filings (e.g. preopening folded into SG&A)
    for key in ["sga", "preopening"]:
        for fy in sorted(long.fiscal_year.unique()):
            sel = long[(long.line_item == key) & (long.fiscal_year == fy)]
            if sel.empty:
                continue
            orig = facts[(facts.concept == INCOME_STATEMENT[key][1][0]) & (facts.dims == "") & (facts.fiscal_year == fy)
                         & (facts.period_type == "duration")].sort_values("filing_date")
            if not orig.empty and abs(orig.iloc[0].value / 1e6 - sel.iloc[0].value) > 0.5:
                out.append({"check": "as_originally_reported", "line_item": key, "fiscal_year": fy,
                            "selected_value": sel.iloc[0].value, "other_value": orig.iloc[0].value / 1e6,
                            "other_accession": orig.iloc[0].accession, "status": "INFO"})
    # (b) companyfacts API
    cf = json.load(open(RAW_SEC / f"{TICKER}_companyfacts.json"))["facts"]["us-gaap"]
    for _, r in long[long.concept.notna() & (long.dims.fillna("") == "")].iterrows():
        if r.concept not in cf:
            out.append({"check": "companyfacts_api", "line_item": r.line_item, "fiscal_year": r.fiscal_year,
                        "selected_value": r.value, "other_value": None, "other_accession": r.accession,
                        "status": "COMPANY_EXTENSION_TAG"})  # company-specific tags are not served by the API
            continue
        units = cf[r.concept].get("units", {})
        match = [f for u in units.values() for f in u
                 if f.get("accn") == r.accession and f.get("end") == r.period_end and _s(f.get("start")) == _s(r.period_start)]
        if not match:
            out.append({"check": "companyfacts_api", "line_item": r.line_item, "fiscal_year": r.fiscal_year,
                        "selected_value": r.value, "other_value": None, "other_accession": r.accession, "status": "NOT_IN_API"})
            continue
        v = _scale(match[0]["val"], r.line_item, r.concept)
        out.append({"check": "companyfacts_api", "line_item": r.line_item, "fiscal_year": r.fiscal_year,
                    "selected_value": r.value, "other_value": v, "other_accession": r.accession,
                    "status": "MATCH" if abs(v - r.value) < 1e-6 else "MISMATCH"})
    return pd.DataFrame(out).drop_duplicates()


def wide(long: pd.DataFrame, statement: str) -> pd.DataFrame:
    d = long[long.statement == statement]
    order = list(dict.fromkeys(d.label))
    w = d.pivot_table(index="label", columns="fiscal_year", values="value", aggfunc="first").reindex(order)
    w.columns = [f"FY{c}" for c in w.columns]
    return w


def main() -> None:
    facts = load_all_10k_facts()
    years = {"income_statement": [2020, 2021, 2022, 2023, 2024],
             "cash_flow": [2020, 2021, 2022, 2023, 2024],
             "balance_sheet": [2019, 2020, 2021, 2022, 2023, 2024]}   # FY2019 BS = opening balance for FY2020
    fys = [2020, 2021, 2022, 2023, 2024]
    rows = extract_statements(facts, years) + extract_lease_note(facts, fys) + extract_segments(facts, fys)
    long = pd.DataFrame(rows)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    long.to_csv(PROCESSED / "financials_long.csv", index=False)
    for s in ["income_statement", "balance_sheet", "cash_flow", "lease_note", "segments"]:
        wide(long, s).round(2).to_csv(PROCESSED / f"{s}.csv")
    checks = source_checks(facts, long)
    checks.to_csv(PROCESSED / "source_checks.csv", index=False)
    print(f"{len(long)} numbers extracted, each with a source link -> data/processed/financials_long.csv")
    print(checks.groupby(["check", "status"]).size().to_string())


if __name__ == "__main__":
    main()
