"""Comparable-company analysis as of 31 Jan 2025.

Every company is measured the same way:
* Price: close on 31 Jan 2025 (Yahoo Finance). Shares: cover-page count in the latest filing before that date.
* Enterprise value = market cap + financial debt (including finance leases) + noncontrolling interest - cash - short-term
  investments. Operating leases are excluded, consistent with EBITDA that is already after operating lease cost (ASC 842).
* Earnings: LTM to each company's latest quarter before the valuation date, on a 52-week basis (src/ltm.py). GAAP, unadjusted.
* Multiples: EV/Revenue, EV/EBITDA, P/E, P/S, and growth-adjusted EV/EBITDA (EV/EBITDA divided by the 3-year revenue CAGR in %).
"""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

from src.config import CONFIG_DIR, PEERS, PROCESSED, TABLES, TICKER
from src.ltm import annual_series, ltm
from src.market import price_on_valuation_date
from src.peers import debt_and_cash, shares_outstanding

MULTIPLES = ["ev_revenue", "ev_ebitda", "pe", "ps"]


def company_row(t: str) -> dict:
    price = price_on_valuation_date(t)
    sh, sh_date = shares_outstanding(t)
    d = debt_and_cash(t)
    fin = {k: ltm(t, k) for k in ["revenue", "operating_income", "d_and_a", "net_income"]}
    debt = d["financial_debt"]
    fl_note = d["concepts"]["finance_leases"]
    if t == TICKER and fl_note == "not tagged":
        # Costco stopped tagging finance leases separately; use our lease-note figure (FY2024 10-K)
        lease = pd.read_csv(PROCESSED / "financials_long.csv")
        fl = float(lease[(lease.line_item == "finance_lease_liab_total") & (lease.fiscal_year == 2024)].value.iloc[0])
        debt += fl
        fl_note = "finance_lease_liab_total from FY2024 10-K lease note (data/processed)"
    mcap = price * sh
    cash = d["cash"] + d["short_term_investments"]
    ev = mcap + debt + d["noncontrolling_interest"] - cash
    rev, ebit, da, ni = (fin[k]["value"] for k in ["revenue", "operating_income", "d_and_a", "net_income"])
    ebitda = ebit + da
    ann = annual_series(t, "revenue")
    ends = list(ann)
    cagr3 = (ann[ends[-1]] / ann[ends[-4]]) ** (1 / 3) - 1
    nm = lambda den, num: num / den if den and den > 0 else np.nan
    return {
        "ticker": t, "price": price, "shares_m": sh, "shares_date": sh_date, "market_cap": mcap,
        "financial_debt": debt, "noncontrolling_interest": d["noncontrolling_interest"], "cash_and_sti": cash,
        "enterprise_value": ev, "bs_date": d["bs_date"], "ltm_end": fin["revenue"]["ltm_end"],
        "ltm_revenue": rev, "ltm_ebit": ebit, "ltm_d_and_a": da, "ltm_ebitda": ebitda, "ltm_net_income": ni,
        "ebitda_margin": ebitda / rev, "ebit_margin": ebit / rev,
        "revenue_growth_ytd": fin["revenue"].get("ytd_growth"), "revenue_cagr_3y": cagr3,
        "ev_revenue": ev / rev, "ev_ebitda": nm(ebitda, ev), "pe": nm(ni, mcap), "ps": mcap / rev,
        "growth_adj_ev_ebitda": nm(cagr3 * 100, nm(ebitda, ev)),
        "d_and_a_ltm_end": fin["d_and_a"]["ltm_end"], "finance_lease_source": fl_note,
    }


def build() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tiers = json.load(open(CONFIG_DIR / "peers.json"))["tiers"]
    rows = [company_row(t) for t in [TICKER, *PEERS]]
    df = pd.DataFrame(rows).set_index("ticker")
    df["tier"] = [("Subject" if t == TICKER else tiers[t]) for t in df.index]
    peers = df.drop(TICKER)
    stats = pd.DataFrame({
        "peer_median": peers[MULTIPLES + ["growth_adj_ev_ebitda"]].median(),
        "peer_25th": peers[MULTIPLES + ["growth_adj_ev_ebitda"]].quantile(0.25),
        "peer_75th": peers[MULTIPLES + ["growth_adj_ev_ebitda"]].quantile(0.75),
        "tier1_median": peers[peers.tier.str.startswith("1")][MULTIPLES + ["growth_adj_ev_ebitda"]].median(),
        "costco": df.loc[TICKER, MULTIPLES + ["growth_adj_ev_ebitda"]],
    })
    stats["costco_premium_to_median"] = stats["costco"] / stats["peer_median"] - 1

    # implied Costco value per share from peer multiples
    c = df.loc[TICKER]
    net_cash = c["cash_and_sti"] - c["financial_debt"] - c["noncontrolling_interest"]
    base = {"ev_revenue": ("ltm_revenue", "ev"), "ev_ebitda": ("ltm_ebitda", "ev"), "pe": ("ltm_net_income", "equity"),
            "ps": ("ltm_revenue", "equity")}
    imp = []
    for mult, (metric, kind) in base.items():
        for col in ["peer_25th", "peer_median", "peer_75th", "tier1_median"]:
            m = stats.loc[mult, col]
            v = m * c[metric]
            eq = v + net_cash if kind == "ev" else v
            imp.append({"multiple": mult, "statistic": col, "multiple_value": m, "costco_metric": c[metric],
                        "implied_equity": eq, "implied_price": eq / c["shares_m"]})
    implied = pd.DataFrame(imp)
    return df, stats, implied


def main():
    df, stats, implied = build()
    TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLES / "comps.csv", float_format="%.6g")
    stats.to_csv(TABLES / "comps_statistics.csv", float_format="%.6g")
    implied.to_csv(TABLES / "comps_implied_value.csv", index=False, float_format="%.6g")
    pd.set_option("display.width", 220)
    show = df[["tier", "price", "market_cap", "enterprise_value", "ltm_revenue", "ltm_ebitda", "ltm_net_income", "ebitda_margin",
               "revenue_growth_ytd", "revenue_cagr_3y", "ev_revenue", "ev_ebitda", "pe", "ps", "growth_adj_ev_ebitda"]]
    print(show.round(3).to_string())
    print(stats.round(2).to_string())
    print(implied.pivot(index="multiple", columns="statistic", values="implied_price").round(0).to_string())
    return df, stats, implied


if __name__ == "__main__":
    main()
