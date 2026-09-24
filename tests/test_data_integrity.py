"""Accounting identities in the extracted statements (tolerance $1m, since filings round to millions)."""
import pandas as pd
import pytest

from src.config import MANUAL, PROCESSED

TOL = 1.0


@pytest.fixture(scope="module")
def fin():
    long = pd.read_csv(PROCESSED / "financials_long.csv")
    return {(r.line_item, r.fiscal_year): r.value for r in long.itertuples()}, long


def v(fin, key, fy):
    return fin[0][(key, fy)]


YEARS = [2020, 2021, 2022, 2023, 2024]
BS_YEARS = [2019] + YEARS


@pytest.mark.parametrize("fy", YEARS)
def test_income_statement_foots(fin, fy):
    assert abs(v(fin, "net_sales", fy) + v(fin, "membership_fees", fy) - v(fin, "total_revenue", fy)) <= TOL
    ebit = v(fin, "total_revenue", fy) - v(fin, "merchandise_costs", fy) - v(fin, "sga", fy) - v(fin, "preopening", fy)
    assert abs(ebit - v(fin, "operating_income", fy)) <= TOL
    pretax = v(fin, "operating_income", fy) - v(fin, "interest_expense", fy) + v(fin, "interest_income_other", fy)
    assert abs(pretax - v(fin, "pretax_income", fy)) <= TOL
    assert abs(v(fin, "pretax_income", fy) - v(fin, "income_tax", fy) - v(fin, "net_income_incl_nci", fy)) <= TOL
    assert abs(v(fin, "net_income_incl_nci", fy) - v(fin, "nci_income", fy) - v(fin, "net_income", fy)) <= TOL


@pytest.mark.parametrize("fy", YEARS)
def test_eps_consistent_with_net_income(fin, fy):
    implied = v(fin, "net_income", fy) / v(fin, "shares_diluted", fy)
    assert abs(implied - v(fin, "eps_diluted", fy)) < 0.02


@pytest.mark.parametrize("fy", BS_YEARS)
def test_balance_sheet_balances(fin, fy):
    ca = sum(v(fin, k, fy) for k in ["cash", "short_term_investments", "receivables", "inventories", "other_current_assets"])
    assert abs(ca - v(fin, "total_current_assets", fy)) <= TOL
    ta = v(fin, "total_current_assets", fy) + v(fin, "ppe_net", fy) + v(fin, "operating_lease_rou", fy) + v(fin, "other_lt_assets", fy)
    assert abs(ta - v(fin, "total_assets", fy)) <= TOL
    cl = sum(v(fin, k, fy) for k in ["accounts_payable", "accrued_salaries", "accrued_member_rewards",
                                     "deferred_membership_fees", "current_debt", "other_current_liabilities"])
    assert abs(cl - v(fin, "total_current_liabilities", fy)) <= TOL
    tl = v(fin, "total_current_liabilities", fy) + v(fin, "long_term_debt", fy) + v(fin, "lt_operating_lease_liab", fy) + v(fin, "other_lt_liabilities", fy)
    assert abs(tl - v(fin, "total_liabilities", fy)) <= TOL
    assert abs(v(fin, "costco_equity", fy) + v(fin, "nci", fy) - v(fin, "total_equity", fy)) <= TOL
    assert abs(v(fin, "total_liabilities", fy) + v(fin, "total_equity", fy) - v(fin, "total_assets", fy)) <= TOL
    assert abs(v(fin, "total_liabilities_equity", fy) - v(fin, "total_assets", fy)) <= TOL


@pytest.mark.parametrize("fy", YEARS)
def test_cash_flow_ties_to_balance_sheet(fin, fy):
    total = v(fin, "cfo", fy) + v(fin, "cfi", fy) + v(fin, "cff", fy) + v(fin, "fx_effect", fy)
    assert abs(total - v(fin, "net_change_cash", fy)) <= TOL
    assert abs(v(fin, "cash", fy) - v(fin, "cash", fy - 1) - v(fin, "net_change_cash", fy)) <= TOL


@pytest.mark.parametrize("fy", YEARS)
def test_segments_sum_to_consolidated(fin, fy):
    long = fin[1]
    seg = long[(long.statement == "segments") & (long.fiscal_year == fy)]
    s = lambda key: seg[seg.line_item == key].value.sum()
    assert abs(s("segment_revenue") - v(fin, "total_revenue", fy)) <= TOL
    assert abs(s("segment_operating_income") - v(fin, "operating_income", fy)) <= TOL
    assert abs(s("segment_d_and_a") - v(fin, "d_and_a", fy)) <= TOL
    assert abs(s("segment_capex") - v(fin, "capex", fy)) <= TOL
    assert abs(s("segment_ppe_net") - v(fin, "ppe_net", fy)) <= TOL
    assert abs(s("segment_total_assets") - v(fin, "total_assets", fy)) <= TOL
    assert abs(s("category_sales") - v(fin, "net_sales", fy)) <= TOL


def test_every_number_has_a_source(fin):
    long = fin[1]
    unsourced = long[long.source_url.isna() & long.note.isna()]
    assert unsourced.empty, unsourced[["line_item", "fiscal_year"]]


def test_values_agree_with_sec_companyfacts_api():
    checks = pd.read_csv(PROCESSED / "source_checks.csv")
    api = checks[checks.check == "companyfacts_api"]
    assert (api.status != "MISMATCH").all()
    assert (api.status == "MATCH").sum() > 300


def test_operating_metrics_are_verified():
    om = pd.read_csv(PROCESSED / "operating_metrics_long.csv")
    assert om.verified_in_filing.all()
    assert set(om.fiscal_year) >= set(YEARS)


@pytest.mark.skipif(not any((PROCESSED.parent / "raw" / "filings").glob("*.htm")),
                    reason="raw filings not downloaded (run python -m src.sec_fetch)")
def test_manual_verifier_rejects_a_bad_quote(tmp_path, monkeypatch):
    """A made-up quote must fail verification."""
    import src.operating_metrics as om
    bad = pd.read_csv(MANUAL / "operating_metrics.csv")
    bad.loc[0, "quote"] = "Total paid members 99,999"
    bad.loc[0, "value_as_written"] = "99,999"
    (tmp_path / "operating_metrics.csv").write_text(bad.to_csv(index=False))
    monkeypatch.setattr(om, "MANUAL", tmp_path)
    idx = pd.read_csv(om.RAW / "filing_index.csv")
    with pytest.raises(SystemExit):
        om.verify_manual(idx)
