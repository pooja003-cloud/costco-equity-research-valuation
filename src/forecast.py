"""Driver-based, integrated three-statement forecast for Costco, FY2025-FY2029.

Every input comes from config/assumptions.json, where each assumption has its rationale. The FY2024 actuals
(Phase 1 data) are the starting point.

Build order for each year
-------------------------
1. Operating drivers: warehouses -> net sales (comps x new-warehouse contribution); paid members x fee per member -> fees
2. Income statement: gross margin, SG&A, operating income (EBIT), interest, tax, net income
3. Balance sheet, operating lines: working capital scales with revenue/fees; PP&E = beginning + capex - D&A
4. Cash flow statement: CFO (indirect method), CFI (capex), CFF (dividends, buybacks)
5. Cash = beginning cash + net cash flow. Cash is the only plug.
6. Check: total assets = total liabilities + equity. The model raises an error if it does not.

The balance sheet balances only if every movement passes through the cash flow statement. That is what makes
the three statements "linked"; tests/test_forecast.py checks it for every year.
"""
from __future__ import annotations

import json

import pandas as pd

from src.config import CONFIG_DIR, TABLES
from src.historical import load

WC_ASSETS = ["receivables", "inventories", "other_current_assets"]
WC_LIABS = ["accounts_payable", "accrued_salaries", "accrued_member_rewards", "other_current_liabilities"]


def load_assumptions() -> dict:
    with open(CONFIG_DIR / "assumptions.json") as fh:
        return json.load(fh)


def _yr(d: dict, fy: int):
    return d[str(fy)]


def build(a: dict | None = None) -> dict[str, pd.DataFrame]:
    a = a or load_assumptions()
    fin, ops = load()
    base = a["base_year"]
    years = a["forecast_years"]
    cols = [base] + years

    # ---- FY2024 opening values (actuals) ----
    act = lambda k: float(fin.loc[k, base])
    drv = {c: {} for c in cols}
    inc = {c: {} for c in cols}
    bs = {c: {} for c in cols}
    cf = {c: {} for c in cols}

    drv[base].update(warehouses=float(ops.loc["warehouses_end_of_year", base]), paid_members=float(ops.loc["paid_members", base]))
    fee_per_member_base = act("membership_fees") / ((ops.loc["paid_members", base] + ops.loc["paid_members", base - 1]) / 2)
    drv[base]["fee_per_avg_member"] = fee_per_member_base
    for k in ["net_sales", "membership_fees", "total_revenue", "merchandise_costs", "sga", "operating_income",
              "interest_expense", "interest_income_other", "pretax_income", "income_tax", "net_income", "d_and_a"]:
        inc[base][k] = act(k)
    inc[base]["ebitda"] = act("operating_income") + act("d_and_a")
    inc[base]["diluted_shares"] = act("shares_diluted")
    inc[base]["eps_diluted"] = act("eps_diluted")
    for k in ["cash", "short_term_investments", *WC_ASSETS, "ppe_net", "operating_lease_rou", "other_lt_assets",
              *WC_LIABS, "deferred_membership_fees", "current_debt", "long_term_debt", "lt_operating_lease_liab",
              "other_lt_liabilities", "total_equity"]:
        bs[base][k] = act(k)
    for k in ["cfo", "capex", "sbc", "dividends_paid", "buybacks", "d_and_a"]:
        cf[base][k] = act(k)
    cf[base]["net_income"] = act("net_income")
    cf[base]["free_cash_flow"] = act("cfo") - act("capex")

    # ---- forecast ----
    fee_inc = a["membership_fee_increase"]
    fee_uplift_full = fee_inc["full_uplift_on_affected_fees"] * fee_inc["share_of_fee_income_affected"]
    wc = a["working_capital_pct_revenue"]
    cs = a["capital_structure"]
    for fy in years:
        p = fy - 1
        d, i, b, c = drv[fy], inc[fy], bs[fy], cf[fy]

        # 1. drivers
        d["net_new_warehouses"] = _yr(a["warehouses"]["net_new"], fy)
        d["warehouses"] = drv[p]["warehouses"] + d["net_new_warehouses"]
        d["unit_growth"] = d["net_new_warehouses"] / drv[p]["warehouses"]
        d["comp_growth"] = _yr(a["comparable_sales_growth"]["values"], fy)
        d["new_unit_contribution"] = a["new_warehouse_productivity"]["value"] * d["unit_growth"]
        d["net_sales_growth"] = (1 + d["comp_growth"]) * (1 + d["new_unit_contribution"]) - 1
        d["member_growth"] = _yr(a["paid_member_growth"]["values"], fy)
        d["paid_members"] = drv[p]["paid_members"] * (1 + d["member_growth"])
        d["fee_increase_effect"] = fee_uplift_full * fee_inc["recognition_by_year"].get(str(fy), 0.0)
        d["fee_per_avg_member"] = drv[p]["fee_per_avg_member"] * (1 + d["fee_increase_effect"]) * (1 + a["fee_per_member_other_growth"]["value"])

        # 2. income statement
        i["net_sales"] = inc[p]["net_sales"] * (1 + d["net_sales_growth"])
        i["membership_fees"] = d["fee_per_avg_member"] * (d["paid_members"] + drv[p]["paid_members"]) / 2
        i["total_revenue"] = i["net_sales"] + i["membership_fees"]
        i["merchandise_costs"] = i["net_sales"] * (1 - _yr(a["gross_margin_on_net_sales"]["values"], fy))
        i["sga"] = i["net_sales"] * _yr(a["sga_pct_net_sales"]["values"], fy)
        i["operating_income"] = i["total_revenue"] - i["merchandise_costs"] - i["sga"]
        i["interest_expense"] = a["interest"]["expense_fixed"]
        i["interest_income_other"] = _yr(a["interest"]["income_yield_on_beginning_cash"], fy) * (bs[p]["cash"] + bs[p]["short_term_investments"])
        i["pretax_income"] = i["operating_income"] - i["interest_expense"] + i["interest_income_other"]
        i["income_tax"] = i["pretax_income"] * a["tax_rate"]["value"]
        i["net_income"] = i["pretax_income"] - i["income_tax"]
        i["d_and_a"] = a["d_and_a_pct_beginning_ppe"]["value"] * bs[p]["ppe_net"]
        i["ebitda"] = i["operating_income"] + i["d_and_a"]
        i["diluted_shares"] = cs["diluted_shares_m"]
        i["eps_diluted"] = i["net_income"] / cs["diluted_shares_m"]

        # 3. balance sheet, operating items
        rev = i["total_revenue"]
        for k in WC_ASSETS + WC_LIABS:
            b[k] = wc[k] * rev
        b["deferred_membership_fees"] = wc["deferred_membership_fees_pct_fee_income"] * i["membership_fees"]
        c["capex"] = a["capex"]["fy2025_dollars"] if fy == 2025 else a["capex"]["pct_revenue_after"] * rev
        b["ppe_net"] = bs[p]["ppe_net"] + c["capex"] - i["d_and_a"]
        for k in ["short_term_investments", "operating_lease_rou", "other_lt_assets", "current_debt", "long_term_debt",
                  "lt_operating_lease_liab", "other_lt_liabilities"]:
            b[k] = bs[p][k]

        # 4. cash flow statement
        nwc = lambda y: (sum(bs[y][k] for k in WC_ASSETS) - sum(bs[y][k] for k in WC_LIABS) - bs[y]["deferred_membership_fees"])
        c["net_income"] = i["net_income"]
        c["d_and_a"] = i["d_and_a"]
        c["sbc"] = cs["sbc_pct_revenue"] * rev
        c["change_in_nwc"] = -(nwc(fy) - nwc(p))            # cash inflow when working capital falls
        c["cfo"] = c["net_income"] + c["d_and_a"] + c["sbc"] + c["change_in_nwc"]
        c["cfi"] = -c["capex"]
        c["dividends_paid"] = cs["dividend_payout_of_net_income"] * i["net_income"]
        c["buybacks"] = cs["buybacks_per_year"]
        c["cff"] = -c["dividends_paid"] - c["buybacks"]
        c["net_change_cash"] = c["cfo"] + c["cfi"] + c["cff"]
        c["free_cash_flow"] = c["cfo"] - c["capex"]

        # 5. cash plug and equity roll-forward
        b["cash"] = bs[p]["cash"] + c["net_change_cash"]
        b["total_equity"] = bs[p]["total_equity"] + i["net_income"] + c["sbc"] - c["dividends_paid"] - c["buybacks"]

    # totals and the balance check
    for fy in cols:
        b = bs[fy]
        b["total_current_assets"] = b["cash"] + b["short_term_investments"] + sum(b[k] for k in WC_ASSETS)
        b["total_assets"] = b["total_current_assets"] + b["ppe_net"] + b["operating_lease_rou"] + b["other_lt_assets"]
        b["total_current_liabilities"] = sum(b[k] for k in WC_LIABS) + b["deferred_membership_fees"] + b["current_debt"]
        b["total_liabilities"] = b["total_current_liabilities"] + b["long_term_debt"] + b["lt_operating_lease_liab"] + b["other_lt_liabilities"]
        b["total_liabilities_equity"] = b["total_liabilities"] + b["total_equity"]
        b["balance_check"] = b["total_assets"] - b["total_liabilities_equity"]
        if abs(b["balance_check"]) > 0.5:
            raise AssertionError(f"FY{fy} balance sheet does not balance: {b['balance_check']:.2f}")
        inc[fy]["gross_margin_on_net_sales"] = 1 - inc[fy]["merchandise_costs"] / inc[fy]["net_sales"]
        inc[fy]["sga_pct_net_sales"] = inc[fy]["sga"] / inc[fy]["net_sales"]
        inc[fy]["operating_margin"] = inc[fy]["operating_income"] / inc[fy]["total_revenue"]
        inc[fy]["revenue_growth"] = (inc[fy]["total_revenue"] / inc[fy - 1]["total_revenue"] - 1) if fy in years else float(fin.loc["total_revenue", base] / fin.loc["total_revenue", base - 1] - 1)
        inc[fy]["membership_fee_growth"] = (inc[fy]["membership_fees"] / inc[fy - 1]["membership_fees"] - 1) if fy in years else float(fin.loc["membership_fees", base] / fin.loc["membership_fees", base - 1] - 1)

    to_df = lambda dct: pd.DataFrame(dct).rename(columns=lambda y: f"FY{y}{'A' if y == base else 'E'}")
    return {"drivers": to_df(drv), "income_statement": to_df(inc), "balance_sheet": to_df(bs), "cash_flow": to_df(cf)}


def main() -> None:
    out = build()
    TABLES.mkdir(parents=True, exist_ok=True)
    for name, df in out.items():
        df.to_csv(TABLES / f"forecast_{name}.csv", float_format="%.6g")
    pd.set_option("display.width", 200)
    show = out["income_statement"].loc[["total_revenue", "revenue_growth", "membership_fees", "membership_fee_growth",
                                        "operating_income", "operating_margin", "net_income", "eps_diluted", "ebitda"]]
    print(show.round(3).to_string())
    print(out["cash_flow"].loc[["cfo", "capex", "change_in_nwc", "free_cash_flow"]].round(0).to_string())
    print(out["balance_sheet"].loc[["cash", "total_assets", "total_equity", "balance_check"]].round(1).to_string())


if __name__ == "__main__":
    main()
