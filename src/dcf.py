"""Discounted cash flow valuation of Costco as of 31 Jan 2025.

    UFCF  = EBIT x (1 - T) + D&A - Capex - increase in operating working capital
    TV    = FCF(n+1) / (WACC - g),  with FCF(n+1) = NOPAT(n+1) x (1 - g / RONIC)     (value-driver form)
    EV    = PV(stub FY2025 UFCF) + PV(FY2026-29 UFCF) + PV(TV)
    Equity = EV + cash & short-term investments - debt - finance leases - noncontrolling interest

Timing: net debt is from the 24 Nov 2024 balance sheet, so the first cash-flow period is the remaining 40/52 of
FY2025 (24 Nov 2024 - 31 Aug 2025). Every flow is discounted from the 31 Jan 2025 valuation date to the midpoint
of its period (mid-year convention). Stock-based compensation is treated as a real cost: it is already in EBIT
and is not added back.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from src.config import TABLES, VALUATION_DATE
from src.forecast import build
from src.wacc import compute as compute_wacc, load_params

FY_END = {2025: date(2025, 8, 31), 2026: date(2026, 8, 30), 2027: date(2027, 8, 29), 2028: date(2028, 9, 3), 2029: date(2029, 9, 2)}
BS_DATE = date(2024, 11, 24)
FY2025_START = date(2024, 9, 2)


def _years(a: date, b: date) -> float:
    return (b - a).days / 365.25


def ufcf_table(fc: dict, tax: float) -> pd.DataFrame:
    i, c = fc["income_statement"], fc["cash_flow"]
    cols = [x for x in i.columns if x.endswith("E")]
    t = pd.DataFrame(index=cols)
    t["revenue"] = i.loc["total_revenue", cols]
    t["ebit"] = i.loc["operating_income", cols]
    t["taxes_on_ebit"] = t["ebit"] * tax
    t["nopat"] = t["ebit"] - t["taxes_on_ebit"]
    t["d_and_a"] = i.loc["d_and_a", cols]
    t["capex"] = c.loc["capex", cols]
    t["change_in_nwc_inflow"] = c.loc["change_in_nwc", cols]
    t["ufcf"] = t["nopat"] + t["d_and_a"] - t["capex"] + t["change_in_nwc_inflow"]
    t["ebitda"] = t["ebit"] + t["d_and_a"]
    return t


def value(wacc: float, g: float, ronic: float, fc: dict | None = None, tax: float | None = None,
          cs: dict | None = None, detail: bool = False):
    params = load_params()
    tax = params["tax_rate"] if tax is None else tax
    fc = fc or build()
    if cs is None:
        from src.wacc import costco_capital_structure
        cs = costco_capital_structure()
    vd = date.fromisoformat(VALUATION_DATE)
    t = ufcf_table(fc, tax)
    years = [int(c[2:6]) for c in t.index]

    # period fractions and discount timing
    fy25_len = (FY_END[2025] - FY2025_START).days + 1
    stub_frac = (FY_END[2025] - BS_DATE).days / fy25_len
    frac, tmid = [], []
    for y in years:
        if y == 2025:
            start = BS_DATE
            frac.append(stub_frac)
        else:
            start = FY_END[y - 1]
            frac.append(1.0)
        mid = start + (FY_END[y] - start) / 2
        tmid.append(max(_years(vd, mid), 0.0))
    t["period_fraction"] = frac
    t["discount_time_yrs"] = tmid
    t["ufcf_in_period"] = t["ufcf"] * t["period_fraction"]
    t["discount_factor"] = 1 / (1 + wacc) ** t["discount_time_yrs"]
    t["pv_ufcf"] = t["ufcf_in_period"] * t["discount_factor"]

    last = t.iloc[-1]
    nopat_next = last["ebit"] * (1 + g) * (1 - tax)
    reinvestment_rate = g / ronic
    fcf_next = nopat_next * (1 - reinvestment_rate)
    tv = fcf_next / (wacc - g)                              # value one year before the first perpetuity flow's midpoint
    tv_time = t["discount_time_yrs"].iloc[-1]               # first perpetuity flow arrives mid-FY2030 = t_last + 1
    pv_tv = tv / (1 + wacc) ** tv_time
    ev = t["pv_ufcf"].sum() + pv_tv
    net_cash = cs["cash"] + cs["short_term_investments"] - cs["debt_carrying"] - cs["finance_leases"] - cs["noncontrolling_interest"]
    equity = ev + net_cash
    per_share = equity / cs["shares_diluted"]
    if not detail:
        return per_share
    ebitda_29 = last["ebitda"]
    out = {
        "table": t, "wacc": wacc, "g": g, "ronic": ronic, "tax": tax,
        "sum_pv_ufcf": t["pv_ufcf"].sum(), "nopat_next": nopat_next, "reinvestment_rate": reinvestment_rate,
        "fcf_next": fcf_next, "terminal_value": tv, "pv_terminal_value": pv_tv, "tv_discount_time": tv_time,
        "enterprise_value": ev, "tv_share_of_ev": pv_tv / ev,
        "cash_and_sti": cs["cash"] + cs["short_term_investments"], "debt": cs["debt_carrying"],
        "finance_leases": cs["finance_leases"], "net_cash": net_cash, "equity_value": equity,
        "shares_diluted": cs["shares_diluted"], "value_per_share": per_share, "price": cs["price"],
        "upside": per_share / cs["price"] - 1,
        "implied_tv_ev_ebitda_fy29": tv / ebitda_29, "implied_tv_ev_ebitda_fy30": tv / (ebitda_29 * (1 + g)),
        # TV restated to FY2029 year-end (t_last + 0.5), the date a trading multiple would be measured at.
        # Same PV: pv_tv = tv_yearend / (1 + wacc) ** (tv_time + 0.5).
        "terminal_value_yearend": tv * (1 + wacc) ** 0.5,
        "implied_tv_ev_ebitda_fy29_yearend": tv * (1 + wacc) ** 0.5 / ebitda_29,
        "ebitda_fy29": ebitda_29, "fcf_fy29": last["ufcf"],
        "market_ev_ebitda_fy29": (cs["market_cap"] - net_cash) / ebitda_29,
        "ev_ebitda_fy25_at_value": ev / t["ebitda"].iloc[0],
        "market_ev": cs["market_cap"] - net_cash,
        "market_ev_ebitda_fy25": (cs["market_cap"] - net_cash) / t["ebitda"].iloc[0],
        "pv_tv_end_of_year_convention": tv / (1 + wacc) ** (tv_time + 0.5),
        "simple_tv": last["ufcf"] * (1 + g) / (wacc - g),
    }
    return out


def value_with_extended_growth(wacc: float, g_high: float, years_high: int, g: float, ronic: float,
                               fc: dict | None = None, cs: dict | None = None, tax: float | None = None) -> float:
    """Value per share if, after FY2029, NOPAT keeps growing at `g_high` for `years_high` more years
    before settling to terminal growth `g`. Reinvestment always matches growth: FCF = NOPAT x (1 - growth / RONIC).
    With years_high = 0 this equals the base-case DCF."""
    base = value(wacc, g, ronic, fc=fc, cs=cs, tax=tax, detail=True)
    t = base["table"]
    tax = base["tax"]
    n = base["shares_diluted"]
    t_last = t["discount_time_yrs"].iloc[-1]
    nopat = t["ebit"].iloc[-1] * (1 - tax)
    pv_extra = 0.0
    for k in range(1, years_high + 1):
        nopat *= 1 + g_high
        pv_extra += nopat * (1 - g_high / ronic) / (1 + wacc) ** (t_last + k)
    nopat_next = nopat * (1 + g)
    tv = nopat_next * (1 - g / ronic) / (wacc - g)
    pv_tv = tv / (1 + wacc) ** (t_last + years_high)
    ev = base["sum_pv_ufcf"] + pv_extra + pv_tv
    return (ev + base["net_cash"]) / n


def growth_duration_table(wacc: float, g: float, ronic_list=(0.25, 0.30), g_high_list=(0.06, 0.07, 0.08, 0.10),
                          price: float | None = None, fc=None, cs=None, max_years: int = 100) -> pd.DataFrame:
    """Reverse DCF in years: how long must high growth last (at high returns) for the DCF to reach the share price?"""
    rows = []
    for ronic in ronic_list:
        for gh in g_high_list:
            years = None
            for y in range(0, max_years + 1):
                if value_with_extended_growth(wacc, gh, y, g, ronic, fc=fc, cs=cs) >= price:
                    years = y
                    break
            limit = value_with_extended_growth(wacc, gh, max_years, g, ronic, fc=fc, cs=cs)
            rows.append({"ronic": ronic, "high_growth_rate": gh, "years_after_fy2029_needed": years,
                         "value_if_it_lasts_10y": value_with_extended_growth(wacc, gh, 10, g, ronic, fc=fc, cs=cs),
                         "value_if_it_lasts_20y": value_with_extended_growth(wacc, gh, 20, g, ronic, fc=fc, cs=cs),
                         f"value_if_it_lasts_{max_years}y": limit})
    return pd.DataFrame(rows)


def value_exit_multiple(wacc: float, multiple: float, fc: dict | None = None, cs: dict | None = None,
                        tax: float | None = None) -> float:
    """Value per share with the terminal value set as `multiple` x FY2029 EBITDA at FY2029 year-end
    (discounted at t_last + 0.5 years). Explicit cash flows as in value()."""
    d = value(wacc, 0.03, 0.25, fc=fc, cs=cs, tax=tax, detail=True)   # g/RONIC do not affect the explicit flows
    pv_tv = multiple * d["ebitda_fy29"] / (1 + wacc) ** (d["tv_discount_time"] + 0.5)
    return (d["sum_pv_ufcf"] + pv_tv + d["net_cash"]) / d["shares_diluted"]


def solve(f, lo: float, hi: float, target: float, tol: float = 1e-7) -> float:
    """Bisection: find x in [lo, hi] with f(x) = target (f monotonic)."""
    flo = f(lo) - target
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = f(mid) - target
        if abs(fm) < tol:
            return mid
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return mid


def main() -> dict:
    p = load_params()
    w = compute_wacc()
    fc = build()
    cs = w["capital_structure"]
    g, ronic = p["terminal"]["growth"], p["terminal"]["ronic"]
    r = value(w["wacc"], g, ronic, fc=fc, cs=cs, detail=True)
    # reverse DCF: what does the share price imply?
    price = cs["price"]
    r["implied_g"] = solve(lambda x: value(w["wacc"], x, ronic, fc=fc, cs=cs), 0.0, w["wacc"] - 0.001, price)
    r["implied_wacc"] = solve(lambda x: value(x, g, ronic, fc=fc, cs=cs), g + 0.002, 0.15, price)
    r["implied_erp"] = (r["implied_wacc"] - w["weight_debt"] * w["after_tax_cost_of_debt"]) / w["weight_equity"]
    r["implied_erp"] = (r["implied_erp"] - w["risk_free"]) / w["adjusted_beta"]
    r["value_with_peer_beta_wacc"] = value(w["wacc_with_peer_beta"], g, ronic, fc=fc, cs=cs)
    r["value_cash_excluded"] = r["value_per_share"] - r["cash_and_sti"] / r["shares_diluted"]
    ke_raw = w["risk_free"] + w["raw_beta"] * w["erp"]
    r["wacc_raw_beta"] = w["weight_equity"] * ke_raw + w["weight_debt"] * w["after_tax_cost_of_debt"]
    r["value_with_raw_beta"] = value(r["wacc_raw_beta"], g, ronic, fc=fc, cs=cs)
    r["implied_exit_multiple"] = solve(lambda m: value_exit_multiple(w["wacc"], m, fc=fc, cs=cs), 1.0, 80.0, price)

    r["growth_duration"] = growth_duration_table(w["wacc"], g, price=price, fc=fc, cs=cs)

    TABLES.mkdir(parents=True, exist_ok=True)
    r["table"].T.to_csv(TABLES / "dcf_ufcf.csv", float_format="%.6g")
    r["growth_duration"].to_csv(TABLES / "reverse_dcf_growth_duration.csv", index=False, float_format="%.6g")
    summary = [
        ("WACC", r["wacc"]), ("Terminal growth", g), ("Terminal RONIC", ronic),
        ("Sum of PV of UFCF (stub FY25 - FY29)", r["sum_pv_ufcf"]), ("Terminal value (undiscounted)", r["terminal_value"]),
        ("PV of terminal value", r["pv_terminal_value"]), ("Enterprise value", r["enterprise_value"]),
        ("Terminal value as % of EV", r["tv_share_of_ev"]), ("+ Cash and short-term investments", r["cash_and_sti"]),
        ("- Debt (carrying value)", r["debt"]), ("- Finance lease liabilities", r["finance_leases"]),
        ("Equity value", r["equity_value"]), ("Diluted shares (m)", r["shares_diluted"]),
        ("Value per share ($)", r["value_per_share"]), ("Share price 31 Jan 2025 ($)", price), ("Upside / (downside)", r["upside"]),
        ("Terminal FCF (FY2030) vs. FY2029 UFCF", r["fcf_next"] / r["fcf_fy29"] - 1),
        ("Implied terminal EV/EBITDA (FY2029, mid-year basis)", r["implied_tv_ev_ebitda_fy29"]),
        ("Implied terminal EV/EBITDA (FY2029 year-end basis, comparable to trading multiples)", r["implied_tv_ev_ebitda_fy29_yearend"]),
        ("Market EV / FY2029E EBITDA", r["market_ev_ebitda_fy29"]),
        ("Reverse DCF: FY2029 year-end exit multiple implied by price", r["implied_exit_multiple"]),
        ("Market EV / FY2025E EBITDA", r["market_ev_ebitda_fy25"]), ("DCF EV / FY2025E EBITDA", r["ev_ebitda_fy25_at_value"]),
        ("Reverse DCF: terminal growth implied by price", r["implied_g"]),
        ("Reverse DCF: WACC implied by price", r["implied_wacc"]),
        ("Reverse DCF: ERP implied by price (beta held)", r["implied_erp"]),
        ("Cross-check: value per share at peer-beta WACC", r["value_with_peer_beta_wacc"]),
        ("Cross-check: value per share treating all cash as operating", r["value_cash_excluded"]),
        ("Cross-check: WACC with raw (unadjusted) beta", r["wacc_raw_beta"]),
        ("Cross-check: value per share with raw beta", r["value_with_raw_beta"]),
    ]
    pd.DataFrame(summary, columns=["item", "value"]).to_csv(TABLES / "dcf_summary.csv", index=False, float_format="%.6g")
    pd.set_option("display.width", 200)
    print(r["table"][["ebit", "nopat", "d_and_a", "capex", "change_in_nwc_inflow", "ufcf", "period_fraction",
                      "discount_time_yrs", "pv_ufcf"]].round(2).T.to_string())
    for k, v in summary:
        print(f"{k:58s} {v:,.4f}")
    print(r["growth_duration"].round(3).to_string())
    return r


if __name__ == "__main__":
    main()
