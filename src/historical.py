"""Historical analysis metrics for Costco, FY2020-FY2024.

Every metric is computed from the source-tracked datasets built in Phase 1 (data/processed/). Nothing
here is typed in by hand. Definitions are in the docstrings and in docs/historical_analysis.md.

Conventions
-----------
* $ millions unless stated otherwise. Fiscal years end on the Sunday nearest 31 August.
* Averages of balance-sheet items use (opening + closing) / 2. FY2019 is the opening balance for FY2020.
* FY2023 had 53 weeks. "52-week adjusted" figures scale FY2023 flow items by 52/53. Costco does not
  disclose the dollar value of the extra week, so this is a stated approximation.
"""
from __future__ import annotations

import pandas as pd

from src.config import PROCESSED, TABLES

YEARS = [2020, 2021, 2022, 2023, 2024]
WEEKS = {2019: 52, 2020: 52, 2021: 52, 2022: 52, 2023: 53, 2024: 52}


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (financials, operating metrics) as DataFrames indexed by line item, one column per FY (int)."""
    long = pd.read_csv(PROCESSED / "financials_long.csv")
    fin = long.pivot_table(index="line_item", columns="fiscal_year", values="value", aggfunc="first")
    om = pd.read_csv(PROCESSED / "operating_metrics_long.csv")
    ops = om.pivot_table(index="metric", columns="fiscal_year", values="value", aggfunc="first")
    return fin, ops


def _avg(s: pd.Series, fy: int) -> float:
    return (s[fy] + s[fy - 1]) / 2


def compute_metrics() -> pd.DataFrame:
    f, o = load()
    m: dict[str, dict[int, float]] = {}

    def put(name, fn, years=YEARS):
        m[name] = {fy: fn(fy) for fy in years}

    rev, ns, fees = f.loc["total_revenue"], f.loc["net_sales"], f.loc["membership_fees"]
    cogs, sga, ebit = f.loc["merchandise_costs"], f.loc["sga"], f.loc["operating_income"]
    wh, sqft = o.loc["warehouses_end_of_year"], o.loc["operating_floor_space"]

    # ---------------- Growth ----------------
    adj = lambda s, fy: s[fy] * 52 / WEEKS[fy]                     # 52-week equivalent
    put("revenue_growth", lambda fy: rev[fy] / rev[fy - 1] - 1, YEARS[1:])
    put("net_sales_growth", lambda fy: ns[fy] / ns[fy - 1] - 1, YEARS[1:])
    put("net_sales_growth_52wk", lambda fy: adj(ns, fy) / adj(ns, fy - 1) - 1, YEARS[1:])
    put("membership_fee_growth", lambda fy: fees[fy] / fees[fy - 1] - 1, YEARS[1:])
    put("membership_fee_growth_52wk", lambda fy: adj(fees, fy) / adj(fees, fy - 1) - 1, YEARS[1:])
    put("comparable_sales_growth", lambda fy: o.loc["comparable_sales_growth", fy] / 100)
    put("comparable_sales_growth_ex_gas_fx", lambda fy: o.loc["comparable_sales_growth_ex_gas_fx", fy] / 100)
    # Net sales growth not explained by comps = mainly new warehouses (plus rounding in reported comps).
    put("non_comp_growth_52wk", lambda fy: m["net_sales_growth_52wk"][fy] - m["comparable_sales_growth"][fy], YEARS[1:])
    put("warehouses", lambda fy: wh[fy])
    put("net_new_warehouses", lambda fy: wh[fy] - wh[fy - 1], YEARS[1:])
    put("warehouse_growth", lambda fy: wh[fy] / wh[fy - 1] - 1, YEARS[1:])
    put("floor_space_growth", lambda fy: sqft[fy] / sqft[fy - 1] - 1, YEARS[1:])
    put("net_sales_per_avg_warehouse", lambda fy: adj(ns, fy) / _avg(wh, fy), YEARS[1:])   # $m, 52-wk
    put("net_sales_per_avg_sqft", lambda fy: adj(ns, fy) * 1e6 / (_avg(sqft, fy) * 1e6), YEARS[1:])  # $ per sq ft

    # ---------------- Margins ----------------
    put("gross_margin_on_net_sales", lambda fy: (ns[fy] - cogs[fy]) / ns[fy])
    put("sga_pct_net_sales", lambda fy: sga[fy] / ns[fy])
    put("operating_margin", lambda fy: ebit[fy] / rev[fy])
    put("membership_fees_pct_revenue", lambda fy: fees[fy] / rev[fy])
    put("membership_fees_pct_operating_income", lambda fy: fees[fy] / ebit[fy])
    # Merchandising profit: operating income earned *before* counting fee income. Costco prices goods near cost.
    put("merchandise_operating_income", lambda fy: ebit[fy] - fees[fy])
    put("merchandise_operating_margin", lambda fy: (ebit[fy] - fees[fy]) / ns[fy])
    put("net_margin", lambda fy: f.loc["net_income", fy] / rev[fy])
    put("effective_tax_rate", lambda fy: f.loc["income_tax", fy] / f.loc["pretax_income", fy])
    ex_disc = o.loc["effective_tax_rate_ex_discrete"] if "effective_tax_rate_ex_discrete" in o.index else pd.Series(dtype=float)
    disc24 = sum(o.loc[k, 2024] for k in o.index if k.startswith("discrete_tax_benefit_"))

    def etr_ex(fy):
        if fy == 2024:  # FY2024 10-K lists the discrete items but not the resulting rate, so compute it
            return (f.loc["income_tax", fy] + disc24) / f.loc["pretax_income", fy]
        return ex_disc[fy] / 100
    put("effective_tax_rate_ex_discrete", etr_ex)

    # Segment operating margins
    seg = pd.read_csv(PROCESSED / "financials_long.csv")
    seg = seg[seg.statement == "segments"]
    for name, key in [("United States", "us"), ("Canada", "canada"), ("Other International", "other_intl")]:
        r = seg[seg.label == f"{name}: revenue"].set_index("fiscal_year").value
        oi = seg[seg.label == f"{name}: operating income"].set_index("fiscal_year").value
        put(f"segment_margin_{key}", lambda fy, r=r, oi=oi: oi[fy] / r[fy])
        put(f"segment_revenue_share_{key}", lambda fy, r=r: r[fy] / rev[fy])

    # ---------------- Membership economics ----------------
    pm, ex = o.loc["paid_members"], o.loc["executive_members"]
    put("paid_members_m", lambda fy: pm[fy])
    put("paid_member_growth", lambda fy: pm[fy] / pm[fy - 1] - 1, YEARS[1:])
    put("executive_members_m", lambda fy: ex[fy])
    put("executive_share_of_paid", lambda fy: ex[fy] / pm[fy])
    # Fee income per average paid member ($/yr, 52-week basis). Paid members include affiliates, and Executive
    # upgrade fees are in fee income, so this is a blended figure, not a list price.
    put("fee_per_avg_paid_member", lambda fy: adj(fees, fy) * 1e6 / (_avg(pm, fy) * 1e6), YEARS[1:])
    put("renewal_rate_us_canada", lambda fy: o.loc["renewal_rate_us_canada", fy] / 100)
    put("renewal_rate_worldwide", lambda fy: o.loc["renewal_rate_worldwide", fy] / 100)
    put("net_sales_per_avg_paid_member", lambda fy: adj(ns, fy) * 1e6 / (_avg(pm, fy) * 1e6), YEARS[1:])

    # ---------------- Working capital ----------------
    op_ca = lambda fy: f.loc["receivables", fy] + f.loc["inventories", fy] + f.loc["other_current_assets", fy]
    op_cl = lambda fy: (f.loc["accounts_payable", fy] + f.loc["accrued_salaries", fy] + f.loc["accrued_member_rewards", fy]
                        + f.loc["deferred_membership_fees", fy] + f.loc["other_current_liabilities", fy])
    nwc = {fy: op_ca(fy) - op_cl(fy) for fy in [2019] + YEARS}
    put("operating_nwc", lambda fy: nwc[fy])
    put("operating_nwc_pct_revenue", lambda fy: nwc[fy] / rev[fy])
    put("change_in_operating_nwc", lambda fy: nwc[fy] - nwc[fy - 1])
    days = lambda fy: 7 * WEEKS[fy] - (0 if WEEKS[fy] == 52 else 0)   # 364 or 371 days
    put("inventory_days", lambda fy: _avg(f.loc["inventories"], fy) / cogs[fy] * days(fy))
    put("payable_days", lambda fy: _avg(f.loc["accounts_payable"], fy) / cogs[fy] * days(fy))
    put("payables_to_inventory", lambda fy: f.loc["accounts_payable", fy] / f.loc["inventories", fy])
    put("deferred_fees_pct_fee_income", lambda fy: f.loc["deferred_membership_fees", fy] / fees[fy])

    # ---------------- Capital intensity, cash flow ----------------
    capex, da, cfo = f.loc["capex"], f.loc["d_and_a"], f.loc["cfo"]
    put("capex", lambda fy: capex[fy])
    put("capex_pct_revenue", lambda fy: capex[fy] / rev[fy])
    put("d_and_a_pct_revenue", lambda fy: da[fy] / rev[fy])
    put("capex_to_d_and_a", lambda fy: capex[fy] / da[fy])
    put("sbc_pct_revenue", lambda fy: f.loc["sbc", fy] / rev[fy])
    put("free_cash_flow", lambda fy: cfo[fy] - capex[fy])
    put("fcf_margin", lambda fy: (cfo[fy] - capex[fy]) / rev[fy])
    put("fcf_conversion", lambda fy: (cfo[fy] - capex[fy]) / f.loc["net_income", fy])
    put("cfo_to_net_income", lambda fy: cfo[fy] / f.loc["net_income", fy])

    # ---------------- Returns on capital ----------------
    # Invested capital (financing view) = debt + lease liabilities + total equity - cash - short-term investments.
    # FY2019 predates ASC 842 (no operating leases on balance sheet), so FY2020 ROIC uses year-end IC only.
    lease = {fy: f.loc["total_lease_liab", fy] for fy in YEARS}
    ic = {fy: (f.loc["current_debt", fy] + f.loc["long_term_debt", fy] + lease[fy] + f.loc["total_equity", fy]
               - f.loc["cash", fy] - f.loc["short_term_investments", fy]) for fy in YEARS}
    nopat = {fy: ebit[fy] * (1 - m["effective_tax_rate"][fy]) for fy in YEARS}
    put("invested_capital", lambda fy: ic[fy])
    put("nopat", lambda fy: nopat[fy])
    put("roic", lambda fy: nopat[fy] / (ic[fy] if fy == 2020 else (ic[fy] + ic[fy - 1]) / 2))
    put("roe", lambda fy: f.loc["net_income", fy] / _avg(f.loc["costco_equity"], fy))
    put("net_cash", lambda fy: f.loc["cash", fy] + f.loc["short_term_investments", fy]
        - f.loc["current_debt", fy] - f.loc["long_term_debt", fy])
    put("net_cash_after_leases", lambda fy: m["net_cash"][fy] - lease[fy])
    put("revenue_to_avg_ppe", lambda fy: rev[fy] / _avg(f.loc["ppe_net"], fy))

    # ---------------- Capital allocation ----------------
    special = o.loc["special_dividend_paid"] if "special_dividend_paid" in o.index else pd.Series(dtype=float)
    sp = lambda fy: special.get(fy, 0.0) if pd.notna(special.get(fy, float("nan"))) else 0.0
    put("dividends_paid_total", lambda fy: f.loc["dividends_paid", fy])
    put("special_dividends", lambda fy: sp(fy))
    put("regular_dividends", lambda fy: f.loc["dividends_paid", fy] - sp(fy))
    # Cash paid shifts between years with the timing of the last quarterly payment, so the payout ratio uses
    # dividends *declared* per share (excluding specials) divided by diluted EPS.
    dps = o.loc["dividends_declared_per_share"]
    sdps = o.loc["special_dividend_per_share"]
    put("regular_dps_declared", lambda fy: dps[fy] - (sdps[fy] if pd.notna(sdps.get(fy)) else 0.0))
    put("regular_payout_ratio", lambda fy: m["regular_dps_declared"][fy] / f.loc["eps_diluted", fy])
    put("buybacks", lambda fy: f.loc["buybacks", fy])
    put("diluted_shares_m", lambda fy: f.loc["shares_diluted", fy])

    out = pd.DataFrame(m).T[YEARS]
    out.columns = [f"FY{c}" for c in out.columns]
    return out


# Incremental return: extra NOPAT earned per extra dollar of capital, FY2020 -> FY2024
def incremental_roic(metrics: pd.DataFrame) -> float:
    d_nopat = metrics.loc["nopat", "FY2024"] - metrics.loc["nopat", "FY2020"]
    d_ic = metrics.loc["invested_capital", "FY2024"] - metrics.loc["invested_capital", "FY2020"]
    return d_nopat / d_ic


def cagr(series: pd.Series, start: str = "FY2020", end: str = "FY2024") -> float:
    n = int(end[2:]) - int(start[2:])
    return (series[end] / series[start]) ** (1 / n) - 1


def cash_uses_5yr() -> pd.DataFrame:
    """Where the FY2020-FY2024 operating cash went."""
    f, o = load()
    tot = lambda k: f.loc[k, YEARS].sum()
    special = o.loc["special_dividend_paid"].dropna().sum()
    rows = {
        "Cash from operations": tot("cfo"),
        "Capital expenditure": -tot("capex"),
        "Regular dividends": -(tot("dividends_paid") - special),
        "Special dividends": -special,
        "Share repurchases": -tot("buybacks"),
    }
    df = pd.Series(rows, name="FY2020-24 cumulative ($m)").to_frame()
    df["% of CFO"] = df.iloc[:, 0] / tot("cfo")
    return df


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    mt = compute_metrics()
    mt.to_csv(TABLES / "historical_metrics.csv", float_format="%.6g")
    cash_uses_5yr().to_csv(TABLES / "cash_uses_fy2020_24.csv", float_format="%.6g")
    print(mt.round(4).to_string())
    print("\nIncremental ROIC FY2020->24:", round(incremental_roic(mt), 4))
    print(cash_uses_5yr().round(3))


if __name__ == "__main__":
    main()
