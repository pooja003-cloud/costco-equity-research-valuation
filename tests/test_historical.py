"""Checks on the Phase 2 historical metrics: identities that must hold, plus sanity ranges."""
import pandas as pd
import pytest

from src.historical import cash_uses_5yr, compute_metrics, load

FY = ["FY2020", "FY2021", "FY2022", "FY2023", "FY2024"]


@pytest.fixture(scope="module")
def m():
    return compute_metrics()


@pytest.fixture(scope="module")
def fin():
    return load()[0]


@pytest.mark.parametrize("fy", FY)
def test_profit_split_adds_back_to_operating_income(m, fin, fy):
    y = int(fy[2:])
    assert abs(m.loc["merchandise_operating_income", fy] + fin.loc["membership_fees", y] - fin.loc["operating_income", y]) < 1e-6


@pytest.mark.parametrize("fy", FY)
def test_regular_plus_special_dividends_equal_cash_paid(m, fin, fy):
    y = int(fy[2:])
    assert abs(m.loc["regular_dividends", fy] + m.loc["special_dividends", fy] - fin.loc["dividends_paid", y]) < 1e-6


def test_53_week_adjustment_only_touches_fy2023_and_fy2024(m):
    for fy in ["FY2021", "FY2022"]:
        assert m.loc["net_sales_growth", fy] == pytest.approx(m.loc["net_sales_growth_52wk", fy])
    assert m.loc["net_sales_growth_52wk", "FY2023"] < m.loc["net_sales_growth", "FY2023"]
    assert m.loc["net_sales_growth_52wk", "FY2024"] > m.loc["net_sales_growth", "FY2024"]


def test_sanity_ranges(m):
    assert m.loc["roic", FY].between(0.15, 0.45).all()
    assert m.loc["effective_tax_rate_ex_discrete", FY].between(0.24, 0.28).all()
    assert (m.loc["operating_nwc", FY] < 0).all()            # Costco runs negative working capital
    assert m.loc["gross_margin_on_net_sales", FY].between(0.10, 0.12).all()
    assert m.loc["regular_payout_ratio", FY].between(0.2, 0.35).all()


def test_fy2024_tax_rate_ex_discrete_reconciles(m, fin):
    # (tax + $202m discrete benefits) / pretax, per the FY2024 10-K
    assert m.loc["effective_tax_rate_ex_discrete", "FY2024"] == pytest.approx((2373 + 94 + 63 + 45) / 9740)


def test_cash_uses_cover_cfo_totals(fin):
    cu = cash_uses_5yr().iloc[:, 0]
    assert cu["Cash from operations"] == pytest.approx(fin.loc["cfo", [2020, 2021, 2022, 2023, 2024]].sum())
    assert cu["Special dividends"] == pytest.approx(-(4430 + 6655))
