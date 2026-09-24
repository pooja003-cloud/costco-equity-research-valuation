"""Tests for the comparable-company analysis."""
import numpy as np
import pytest

from src.comps import build
from src.config import VALUATION_DATE


@pytest.fixture(scope="module")
def comps():
    return build()


def test_enterprise_value_identity(comps):
    df = comps[0]
    ev = df.market_cap + df.financial_debt + df.noncontrolling_interest - df.cash_and_sti
    assert np.allclose(ev, df.enterprise_value)


def test_multiples_are_consistent(comps):
    df = comps[0]
    assert np.allclose(df.ev_revenue, df.enterprise_value / df.ltm_revenue)
    ok = df.ltm_ebitda > 0
    assert np.allclose(df.ev_ebitda[ok], df.enterprise_value[ok] / df.ltm_ebitda[ok])


def test_no_look_ahead(comps):
    df = comps[0]
    assert (df.ltm_end <= VALUATION_DATE).all() and (df.bs_date <= VALUATION_DATE).all()
    assert (df.shares_date <= VALUATION_DATE).all()


def test_negative_earnings_are_not_meaningful(comps):
    df = comps[0]
    assert np.isnan(df.loc["DLTR", "ev_ebitda"]) and np.isnan(df.loc["DLTR", "pe"])


def test_costco_ltm_matches_extracted_quarter(comps):
    """Costco LTM revenue = FY2024 + Q1 FY2025 - Q1 FY2024."""
    import pandas as pd
    from src.config import PROCESSED
    q = pd.read_csv(PROCESSED / "quarter_q1_fy2025.csv")
    qv = lambda k, p: float(q[(q.line_item == k) & (q.period == p)].value.iloc[0])
    expected = 254453 + qv("total_revenue", "Q1 FY2025") - qv("total_revenue", "Q1 FY2024")
    assert comps[0].loc["COST", "ltm_revenue"] == pytest.approx(expected, rel=1e-3)


def test_implied_prices(comps):
    df, stats, implied = comps
    c = df.loc["COST"]
    row = implied[(implied.multiple == "ev_ebitda") & (implied.statistic == "peer_median")].iloc[0]
    net_cash = c.cash_and_sti - c.financial_debt - c.noncontrolling_interest
    assert row.implied_price == pytest.approx((stats.loc["ev_ebitda", "peer_median"] * c.ltm_ebitda + net_cash) / c.shares_m)
