"""Grids and scenarios are centred on the base case and move the right way."""
import numpy as np
import pytest

from src.sensitivity import run


@pytest.fixture(scope="module")
def out():
    return run()


def test_grids_centre_on_base_case(out):
    base = out["base_value"]
    for k in ["wacc_g", "revenue_margin", "ronic_g", "terminal_cf"]:
        assert out[k].iloc[2, 2] == pytest.approx(base, rel=1e-9), k


def test_wacc_g_monotonic(out):
    v = out["wacc_g"].values
    assert (np.diff(v, axis=0) < 0).all()      # higher WACC -> lower value
    assert (np.diff(v, axis=1) > 0).all()      # higher growth -> higher value


def test_revenue_margin_monotonic(out):
    v = out["revenue_margin"].values
    assert (np.diff(v, axis=0) > 0).all() and (np.diff(v, axis=1) > 0).all()


def test_ronic_monotonic(out):
    assert (np.diff(out["ronic_g"].values, axis=0) > 0).all()


def test_scenarios(out):
    sc = out["scenarios"]
    assert sc.loc["bear", "value_per_share"] < sc.loc["base", "value_per_share"] < sc.loc["bull", "value_per_share"]
    assert sc.loc["base", "value_per_share"] == pytest.approx(out["base_value"])
    assert sc.probability.sum() == pytest.approx(1.0)
    assert sc.attrs["probability_weighted"] == pytest.approx((sc.value_per_share * sc.probability).sum())
