"""Weighted average cost of capital for Costco as of 31 Jan 2025.

    WACC = E/(D+E) x Re + D/(D+E) x Rd x (1 - T)
    Re   = Rf + beta x ERP                                  (CAPM)

All market inputs come from data/raw/market/ (checksummed in manifest.csv); judgement calls from config/valuation.json.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.config import CONFIG_DIR, PEERS, PROCESSED, TABLES, TICKER
from src.market import damodaran_erp, fred, monthly_returns, price_on_valuation_date
from src.peers import debt_and_cash, shares_outstanding


def load_params() -> dict:
    with open(CONFIG_DIR / "valuation.json") as fh:
        return json.load(fh)


def regress_beta(ticker: str, months: int = 60) -> dict:
    y = monthly_returns(ticker, months)
    x = monthly_returns("^GSPC", months).loc[y.index]
    beta = np.cov(y, x)[0, 1] / np.var(x, ddof=1)
    r2 = np.corrcoef(y, x)[0, 1] ** 2
    se = np.sqrt((1 - r2) * np.var(y, ddof=1) / (np.var(x, ddof=1) * (len(y) - 2)))
    return {"ticker": ticker, "raw_beta": beta, "std_error": se, "r_squared": r2, "n_months": len(y),
            "window": f"{y.index[0]:%b %Y} - {y.index[-1]:%b %Y}"}


def costco_capital_structure() -> dict:
    """Valuation-date capital structure. Balance sheet: Q1 FY2025 10-Q (24 Nov 2024). Leases: FY2024 10-K lease note."""
    q = pd.read_csv(PROCESSED / "quarter_q1_fy2025.csv")
    qv = lambda k: float(q[(q.line_item == k) & (q.period == "Q1 FY2025")].value.iloc[0])
    lease = pd.read_csv(PROCESSED / "financials_long.csv")
    fl = float(lease[(lease.line_item == "finance_lease_liab_total") & (lease.fiscal_year == 2024)].value.iloc[0])
    shares_basic, shares_date = shares_outstanding(TICKER)
    # Diluted = cover-page basic shares + RSU dilution under the treasury-stock method (Q1 FY2025 diluted - basic weighted shares)
    rsu_dilution = qv("shares_diluted") - qv("shares_basic")
    price = price_on_valuation_date(TICKER)
    om = pd.read_csv(PROCESSED / "operating_metrics_long.csv").set_index("metric")["value"]
    return {
        "price": price,
        "shares_basic": shares_basic, "shares_basic_date": shares_date,
        "rsu_dilution": rsu_dilution, "shares_diluted": shares_basic + rsu_dilution,
        "market_cap": price * (shares_basic + rsu_dilution),
        "debt_carrying": qv("current_debt") + qv("long_term_debt"),
        "debt_fair_value": om.loc["q1_debt_fair_value"],   # Q1 FY2025 10-Q: fair value of long-term debt incl. current portion
        "finance_leases": fl,
        "cash": qv("cash"), "short_term_investments": qv("short_term_investments"),
        "noncontrolling_interest": 0.0,
        "balance_sheet_date": "2024-11-24",
    }


def peer_beta_crosscheck(tax: float, target_de: float, blume: float) -> pd.DataFrame:
    rows = []
    for t in PEERS:
        b = regress_beta(t)
        d = debt_and_cash(t)
        sh, _ = shares_outstanding(t)
        e = price_on_valuation_date(t) * sh
        de = d["financial_debt"] / e
        bu = b["raw_beta"] / (1 + (1 - tax) * de)          # Hamada unlevering
        rows.append({**b, "market_cap": e, "financial_debt": d["financial_debt"], "d_to_e": de, "unlevered_beta": bu})
    df = pd.DataFrame(rows).set_index("ticker")
    med = df["unlevered_beta"].median()
    relevered = med * (1 + (1 - tax) * target_de)
    df.attrs["median_unlevered"] = med
    df.attrs["relevered_raw"] = relevered
    df.attrs["relevered_blume"] = blume * relevered + (1 - blume)
    return df


def compute() -> dict:
    p = load_params()
    tax = p["tax_rate"]
    rf = fred("DGS10")
    erp = damodaran_erp(2024)["implied_erp_fcfe"]
    cs = costco_capital_structure()
    own = regress_beta(TICKER, p["beta"]["months"])
    w = p["beta"]["blume_weight"]
    beta_adj = w * own["raw_beta"] + (1 - w)
    spread = np.mean([fred(s) for s in p["cost_of_debt"]["spread_series"]])
    kd = rf + spread
    ke = rf + beta_adj * erp
    d_mv = cs["debt_fair_value"] + cs["finance_leases"]
    e_mv = cs["market_cap"]
    wd, we = d_mv / (d_mv + e_mv), e_mv / (d_mv + e_mv)
    wacc = we * ke + wd * kd * (1 - tax)
    peers = peer_beta_crosscheck(tax, d_mv / e_mv, w)
    return {"risk_free": rf, "erp": erp, "raw_beta": own["raw_beta"], "beta_std_error": own["std_error"],
            "beta_r_squared": own["r_squared"], "beta_window": own["window"], "adjusted_beta": beta_adj,
            "cost_of_equity": ke, "credit_spread": spread, "pre_tax_cost_of_debt": kd, "after_tax_cost_of_debt": kd * (1 - tax),
            "tax_rate": tax, "equity_value_mkt": e_mv, "debt_value_mkt": d_mv, "weight_equity": we, "weight_debt": wd,
            "wacc": wacc, "capital_structure": cs, "peer_betas": peers,
            "peer_relevered_beta_blume": peers.attrs["relevered_blume"],
            "wacc_with_peer_beta": we * (rf + peers.attrs["relevered_blume"] * erp) + wd * kd * (1 - tax)}


def main() -> dict:
    r = compute()
    TABLES.mkdir(parents=True, exist_ok=True)
    rows = [("Risk-free rate (10y UST, 31 Jan 2025)", r["risk_free"]), ("Equity risk premium (Damodaran, Jan 2025)", r["erp"]),
            (f"Raw beta ({r['beta_window']}, monthly)", r["raw_beta"]), ("Adjusted beta (Blume)", r["adjusted_beta"]),
            ("Cost of equity", r["cost_of_equity"]), ("Credit spread (avg AA/A OAS)", r["credit_spread"]),
            ("Pre-tax cost of debt", r["pre_tax_cost_of_debt"]), ("Tax rate", r["tax_rate"]),
            ("After-tax cost of debt", r["after_tax_cost_of_debt"]), ("Equity market value ($m)", r["equity_value_mkt"]),
            ("Debt incl. finance leases ($m)", r["debt_value_mkt"]), ("Weight of equity", r["weight_equity"]),
            ("Weight of debt", r["weight_debt"]), ("WACC", r["wacc"]),
            ("Cross-check: peer median beta relevered (Blume)", r["peer_relevered_beta_blume"]),
            ("Cross-check: WACC with peer beta", r["wacc_with_peer_beta"])]
    pd.DataFrame(rows, columns=["item", "value"]).to_csv(TABLES / "wacc.csv", index=False, float_format="%.6g")
    r["peer_betas"].to_csv(TABLES / "peer_betas.csv", float_format="%.6g")
    for k, v in rows:
        print(f"{k:55s} {v:,.4f}")
    print(r["peer_betas"][["raw_beta", "r_squared", "d_to_e", "unlevered_beta"]].round(3).to_string())
    return r


if __name__ == "__main__":
    main()
