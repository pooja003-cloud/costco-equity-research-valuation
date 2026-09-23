"""Integrity tests for the three-statement forecast: the statements must link, and the drivers must behave sensibly."""
import copy

import pytest

from src.forecast import build, load_assumptions

YEARS = ["FY2025E", "FY2026E", "FY2027E", "FY2028E", "FY2029E"]


@pytest.fixture(scope="module")
def out():
    return build()


def prev(col):
    y = int(col[2:6]) - 1
    return f"FY{y}{'A' if y == 2024 else 'E'}"


@pytest.mark.parametrize("fy", ["FY2024A"] + YEARS)
def test_balance_sheet_balances(out, fy):
    assert abs(out["balance_sheet"].loc["balance_check", fy]) < 0.01


@pytest.mark.parametrize("fy", YEARS)
def test_cash_change_equals_cash_flow_statement(out, fy):
    bs, cf = out["balance_sheet"], out["cash_flow"]
    assert bs.loc["cash", fy] - bs.loc["cash", prev(fy)] == pytest.approx(cf.loc["net_change_cash", fy])


@pytest.mark.parametrize("fy", YEARS)
def test_equity_roll_forward(out, fy):
    bs, i, cf = out["balance_sheet"], out["income_statement"], out["cash_flow"]
    expected = bs.loc["total_equity", prev(fy)] + i.loc["net_income", fy] + cf.loc["sbc", fy] - cf.loc["dividends_paid", fy] - cf.loc["buybacks", fy]
    assert bs.loc["total_equity", fy] == pytest.approx(expected)


@pytest.mark.parametrize("fy", YEARS)
def test_ppe_roll_forward(out, fy):
    bs, i, cf = out["balance_sheet"], out["income_statement"], out["cash_flow"]
    assert bs.loc["ppe_net", fy] == pytest.approx(bs.loc["ppe_net", prev(fy)] + cf.loc["capex", fy] - i.loc["d_and_a", fy])


@pytest.mark.parametrize("fy", YEARS)
def test_income_statement_foots(out, fy):
    i = out["income_statement"]
    assert i.loc["total_revenue", fy] == pytest.approx(i.loc["net_sales", fy] + i.loc["membership_fees", fy])
    assert i.loc["operating_income", fy] == pytest.approx(i.loc["total_revenue", fy] - i.loc["merchandise_costs", fy] - i.loc["sga", fy])
    assert i.loc["net_income", fy] == pytest.approx(i.loc["pretax_income", fy] * (1 - 0.26))


def test_fy2025_matches_management_plans(out):
    d, cf = out["drivers"], out["cash_flow"]
    assert d.loc["warehouses", "FY2025E"] == 916           # 890 + 29 openings - 3 relocations
    assert cf.loc["capex", "FY2025E"] == 5000               # stated plan in Q1 FY2025 10-Q


def test_fee_increase_fully_recognized_by_fy2026(out):
    d = out["drivers"]
    uplift = d.loc["fee_per_avg_member", "FY2026E"] / d.loc["fee_per_avg_member", "FY2024A"] - 1
    assert uplift == pytest.approx((1 + 0.0833 * 0.85 * 0.5) ** 2 - 1)
    assert d.loc["fee_per_avg_member", "FY2027E"] == pytest.approx(d.loc["fee_per_avg_member", "FY2026E"])


def test_working_capital_stays_negative(out):
    cf = out["cash_flow"]
    assert (cf.loc["change_in_nwc", YEARS] > 0).all()        # growth releases cash


def test_higher_comps_raise_revenue_and_cash():
    a = load_assumptions()
    hi = copy.deepcopy(a)
    hi["comparable_sales_growth"]["values"] = {k: v + 0.01 for k, v in a["comparable_sales_growth"]["values"].items()}
    base, up = build(a), build(hi)
    assert (up["income_statement"].loc["total_revenue", YEARS] > base["income_statement"].loc["total_revenue", YEARS]).all()
    assert up["balance_sheet"].loc["cash", "FY2029E"] > base["balance_sheet"].loc["cash", "FY2029E"]
    assert abs(up["balance_sheet"].loc["balance_check", "FY2029E"]) < 0.01
