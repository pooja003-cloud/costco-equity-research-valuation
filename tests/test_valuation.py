"""Tests for the WACC and DCF: formulas, identities and sensible behaviour."""
import pytest

from src.dcf import main as dcf_main, value
from src.wacc import compute


@pytest.fixture(scope="module")
def w():
    return compute()


@pytest.fixture(scope="module")
def r():
    return dcf_main()


def test_wacc_formula(w):
    ke = w["risk_free"] + w["adjusted_beta"] * w["erp"]
    assert w["cost_of_equity"] == pytest.approx(ke)
    assert w["weight_equity"] + w["weight_debt"] == pytest.approx(1.0)
    expected = w["weight_equity"] * ke + w["weight_debt"] * w["pre_tax_cost_of_debt"] * (1 - w["tax_rate"])
    assert w["wacc"] == pytest.approx(expected)


def test_market_inputs_as_of_valuation_date(w):
    assert w["risk_free"] == pytest.approx(0.0458)            # FRED DGS10, 31 Jan 2025
    assert w["erp"] == pytest.approx(0.0433)                  # Damodaran, start of 2025
    assert w["capital_structure"]["price"] == pytest.approx(979.88, abs=0.01)


def test_blume_adjustment(w):
    assert w["adjusted_beta"] == pytest.approx(0.67 * w["raw_beta"] + 0.33)


def test_ufcf_formula(r):
    t = r["table"]
    rebuilt = t["ebit"] * (1 - r["tax"]) + t["d_and_a"] - t["capex"] + t["change_in_nwc_inflow"]
    assert (abs(rebuilt - t["ufcf"]) < 1e-6).all()


def test_terminal_value_formula(r):
    fcf_next = r["table"]["ebit"].iloc[-1] * (1 + r["g"]) * (1 - r["tax"]) * (1 - r["g"] / r["ronic"])
    assert r["terminal_value"] == pytest.approx(fcf_next / (r["wacc"] - r["g"]))


def test_enterprise_to_equity_bridge(r):
    assert r["enterprise_value"] == pytest.approx(r["sum_pv_ufcf"] + r["pv_terminal_value"])
    assert r["equity_value"] == pytest.approx(r["enterprise_value"] + r["cash_and_sti"] - r["debt"] - r["finance_leases"])
    assert r["value_per_share"] == pytest.approx(r["equity_value"] / r["shares_diluted"])


def test_value_moves_the_right_way(r):
    base = r["value_per_share"]
    assert value(r["wacc"] + 0.005, r["g"], r["ronic"]) < base
    assert value(r["wacc"], r["g"] + 0.005, r["ronic"]) > base
    assert value(r["wacc"], r["g"], r["ronic"] + 0.05) > base   # higher returns -> less reinvestment needed


def test_reverse_dcf_reproduces_price(r):
    price = r["price"]
    assert value(r["wacc"], r["implied_g"], r["ronic"]) == pytest.approx(price, rel=1e-4)
    assert value(r["implied_wacc"], r["g"], r["ronic"]) == pytest.approx(price, rel=1e-4)


def test_stub_period(r):
    t = r["table"]
    assert t["period_fraction"].iloc[0] == pytest.approx(280 / 364, abs=0.01)   # 24 Nov 2024 - 31 Aug 2025
    assert (t["period_fraction"].iloc[1:] == 1).all()
    assert t["discount_time_yrs"].is_monotonic_increasing
