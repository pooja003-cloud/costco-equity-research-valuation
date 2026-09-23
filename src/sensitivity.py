"""Sensitivity analysis and bear/base/bull scenarios for the DCF.

Grids (value per share, $):
  1. WACC x terminal growth
  2. Revenue growth x operating margin: comparable-sales growth shifted every year, and gross margin shifted in bps
     every year (which moves operating margin one-for-one), re-running the full three-statement forecast each time
  3. Terminal RONIC x terminal growth (how much growth must be reinvested, i.e. the terminal-year cash flow)
  4. Terminal-year cash flow +/- x% at each WACC
Scenarios: config/scenarios.json.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json

import numpy as np
import pandas as pd

from src.config import CONFIG_DIR, TABLES
from src.dcf import value
from src.forecast import build, load_assumptions
from src.wacc import compute as compute_wacc, load_params

WACC_STEPS = [-0.010, -0.005, 0.0, 0.005, 0.010]
G_GRID = [0.020, 0.025, 0.030, 0.035, 0.040]
COMP_SHIFT = [-0.02, -0.01, 0.0, 0.01, 0.02]
GM_SHIFT_BPS = [-30, -15, 0, 15, 30]
RONIC_GRID = [0.15, 0.20, 0.25, 0.30, 0.35]
TCF_SHIFT = [-0.20, -0.10, 0.0, 0.10, 0.20]


def _context():
    with contextlib.redirect_stdout(io.StringIO()):
        w = compute_wacc()
    return w, w["capital_structure"], load_params(), load_assumptions()


def wacc_g_grid(w, cs, p, fc) -> pd.DataFrame:
    base_w = w["wacc"]
    rows = {}
    for dw in WACC_STEPS:
        ww = base_w + dw
        rows[f"{ww:.2%}"] = {f"{g:.1%}": value(ww, g, p["terminal"]["ronic"], fc=fc, cs=cs) for g in G_GRID}
    return pd.DataFrame(rows).T.rename_axis("WACC \\ g")


def revenue_margin_grid(w, cs, p, a) -> tuple[pd.DataFrame, dict]:
    rows, meta = {}, {}
    for dg in COMP_SHIFT:
        row = {}
        for bps in GM_SHIFT_BPS:
            aa = copy.deepcopy(a)
            aa["comparable_sales_growth"]["values"] = {k: v + dg for k, v in a["comparable_sales_growth"]["values"].items()}
            aa["gross_margin_on_net_sales"]["values"] = {k: v + bps / 10000 for k, v in a["gross_margin_on_net_sales"]["values"].items()}
            fc = build(aa)
            i = fc["income_statement"]
            cagr = (i.loc["total_revenue", "FY2029E"] / i.loc["total_revenue", "FY2024A"]) ** 0.2 - 1
            opm = i.loc["operating_margin", "FY2029E"]
            meta[(dg, bps)] = (cagr, opm)
            row[f"gross margin {bps:+d}bp"] = value(w["wacc"], p["terminal"]["growth"], p["terminal"]["ronic"], fc=fc, cs=cs)
        cagr0 = meta[(dg, 0)][0]
        rows[f"comps {dg * 100:+.0f}pp (FY24-29 revenue CAGR {cagr0:.1%})"] = row
    df = pd.DataFrame(rows).T
    # FY2029 operating margin behind each column (base comps row), for the chart/doc labels
    df.attrs["fy29_operating_margin_by_bps"] = {bps: meta[(0.0, bps)][1] for bps in GM_SHIFT_BPS}
    return df, meta


def ronic_g_grid(w, cs, p, fc) -> pd.DataFrame:
    rows = {}
    for r in RONIC_GRID:
        rows[f"{r:.0%}"] = {f"{g:.1%}": value(w["wacc"], g, r, fc=fc, cs=cs) for g in G_GRID}
    return pd.DataFrame(rows).T.rename_axis("RONIC \\ g")


def terminal_cf_grid(w, cs, p, fc) -> pd.DataFrame:
    """Scale the terminal-year free cash flow by +/-x% (equivalent to scaling the terminal value)."""
    rows = {}
    for dw in WACC_STEPS:
        ww = w["wacc"] + dw
        d = value(ww, p["terminal"]["growth"], p["terminal"]["ronic"], fc=fc, cs=cs, detail=True)
        rows[f"{ww:.2%}"] = {f"{s:+.0%}": (d["equity_value"] + s * d["pv_terminal_value"]) / d["shares_diluted"] for s in TCF_SHIFT}
    return pd.DataFrame(rows).T.rename_axis("WACC \\ terminal FCF")


def scenario_assumptions(a: dict, sc: dict) -> dict:
    aa = copy.deepcopy(a)
    if "comparable_sales_growth" in sc:
        aa["comparable_sales_growth"]["values"] = sc["comparable_sales_growth"]
    if "paid_member_growth" in sc:
        aa["paid_member_growth"]["values"] = sc["paid_member_growth"]
    if "net_new_warehouses" in sc:
        aa["warehouses"]["net_new"] = sc["net_new_warehouses"]
    if "gross_margin_on_net_sales" in sc:
        aa["gross_margin_on_net_sales"]["values"] = {k: sc["gross_margin_on_net_sales"] for k in aa["gross_margin_on_net_sales"]["values"]}
    if "sga_pct_net_sales" in sc:
        aa["sga_pct_net_sales"]["values"] = {k: sc["sga_pct_net_sales"] for k in aa["sga_pct_net_sales"]["values"]}
    return aa


def scenarios(w, cs, p, a) -> pd.DataFrame:
    spec = json.load(open(CONFIG_DIR / "scenarios.json"))
    rows = []
    for name in ["bear", "base", "bull"]:
        sc = spec[name]
        fc = build(scenario_assumptions(a, sc))
        g = sc.get("terminal_growth", p["terminal"]["growth"])
        r = sc.get("terminal_ronic", p["terminal"]["ronic"])
        d = value(w["wacc"], g, r, fc=fc, cs=cs, detail=True)
        i = fc["income_statement"]
        rows.append({
            "scenario": name, "probability": spec["probabilities"][name],
            "revenue_fy2029": i.loc["total_revenue", "FY2029E"],
            "revenue_cagr_fy24_29": (i.loc["total_revenue", "FY2029E"] / i.loc["total_revenue", "FY2024A"]) ** 0.2 - 1,
            "operating_margin_fy2029": i.loc["operating_margin", "FY2029E"],
            "eps_fy2029": i.loc["eps_diluted", "FY2029E"],
            "terminal_growth": g, "terminal_ronic": r, "wacc": w["wacc"],
            "enterprise_value": d["enterprise_value"], "tv_share_of_ev": d["tv_share_of_ev"],
            "value_per_share": d["value_per_share"], "vs_price": d["value_per_share"] / cs["price"] - 1,
        })
    df = pd.DataFrame(rows).set_index("scenario")
    df.attrs["probability_weighted"] = float((df.value_per_share * df.probability).sum())
    return df


def run() -> dict:
    w, cs, p, a = _context()
    fc = build(a)
    out = {
        "wacc_g": wacc_g_grid(w, cs, p, fc),
        "revenue_margin": revenue_margin_grid(w, cs, p, a)[0],
        "ronic_g": ronic_g_grid(w, cs, p, fc),
        "terminal_cf": terminal_cf_grid(w, cs, p, fc),
        "scenarios": scenarios(w, cs, p, a),
        "base_value": value(w["wacc"], p["terminal"]["growth"], p["terminal"]["ronic"], fc=fc, cs=cs),
        "price": cs["price"], "wacc": w["wacc"],
    }
    return out


def main() -> dict:
    out = run()
    TABLES.mkdir(parents=True, exist_ok=True)
    for k in ["wacc_g", "revenue_margin", "ronic_g", "terminal_cf", "scenarios"]:
        out[k].to_csv(TABLES / f"sens_{k}.csv", float_format="%.6g")
    pd.set_option("display.width", 250)
    for k in ["wacc_g", "revenue_margin", "ronic_g", "terminal_cf"]:
        print(f"\n== {k} ($/share)\n", out[k].round(0).to_string())
    print("\n== scenarios\n", out["scenarios"].round(3).to_string())
    print("probability-weighted value:", round(out["scenarios"].attrs["probability_weighted"], 1), " price:", out["price"])
    return out


if __name__ == "__main__":
    main()
