"""Charts for the historical analysis, memo and README (PNG files in outputs/charts/)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
import pandas as pd

from src.config import CHARTS, PROCESSED
from src.historical import YEARS, cash_uses_5yr, compute_metrics, load

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
S1, S2, S3, NEUTRAL = "#2a78d6", "#eb6834", "#1baf7a", "#c3c2bc"
SOURCE = "Source: Costco 10-K filings FY2020–FY2024 (SEC EDGAR); author analysis."

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
    "axes.edgecolor": GRID, "axes.linewidth": 1, "axes.labelcolor": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 1,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.major.size": 0, "ytick.major.size": 0,
    "legend.frameon": False, "axes.axisbelow": True, "legend.fontsize": 9, "lines.linewidth": 2,
    "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
})

FY = [f"FY{y}" for y in YEARS]
X = list(range(len(FY)))


def _title(fig, title: str, subtitle: str, source: str = SOURCE) -> None:
    fig.text(0.02, 0.97, title, fontsize=13, fontweight="bold", color=INK, va="top", parse_math=False)
    fig.text(0.02, 0.905, subtitle, fontsize=9.5, color=INK2, va="top", parse_math=False)
    fig.text(0.02, 0.015, source, fontsize=7.5, color=MUTED)


def _save(fig, name: str) -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHARTS / name, dpi=200)
    plt.close(fig)


def _pct(ax, decimals=0, step=None):
    if step:
        ax.yaxis.set_major_locator(mt.MultipleLocator(step))
    ax.yaxis.set_major_formatter(mt.PercentFormatter(1.0, decimals=decimals))


def _dot(ax, x, y, color):
    ax.scatter([x], [y], s=42, color=color, edgecolor=SURFACE, linewidth=2, zorder=5)


def revenue_and_growth(m: pd.DataFrame) -> None:
    f, _ = load()
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"wspace": 0.28})
    fig.subplots_adjust(top=0.78, bottom=0.15, left=0.06, right=0.98)
    rev = f.loc["total_revenue", YEARS] / 1000
    a.bar(X, rev, width=0.5, color=S1)
    for x, v in zip(X, rev):
        a.text(x, v + 4, f"${v:,.0f}bn", ha="center", fontsize=9, color=INK)
    a.set_xticks(X, FY); a.set_ylim(0, 290); a.set_title("Total revenue ($bn)", loc="left", fontsize=10, color=INK2)
    a.yaxis.set_major_formatter(mt.StrMethodFormatter("{x:,.0f}"))
    xs = X[1:]
    series = [("net_sales_growth_52wk", "Net sales growth (52-week basis)", S1),
              ("comparable_sales_growth", "Comparable sales growth", S2),
              ("comparable_sales_growth_ex_gas_fx", "Comparable sales ex gas & FX", S3)]
    for key, label, c in series:
        ys = [m.loc[key, fy] for fy in FY[1:]]
        b.plot(xs, ys, color=c, label=label)
        _dot(b, xs[-1], ys[-1], c)
        b.text(xs[-1] + 0.12, ys[-1], f"{ys[-1]:.0%}", va="center", fontsize=9, color=INK)
    b.set_xticks(xs, FY[1:]); b.set_xlim(0.7, 4.5); b.set_ylim(0, 0.2); _pct(b, step=0.05)
    b.set_title("Growth rates", loc="left", fontsize=10, color=INK2)
    b.legend(loc="upper right")
    _title(fig, "Growth normalized from the 2021–22 inflation surge to a mid-single-digit base",
           "FY2023 had 53 weeks; net sales growth is shown on a 52-week basis (FY2023 scaled by 52/53).")
    _save(fig, "01_revenue_and_growth.png")


def growth_decomposition(m: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    fig.subplots_adjust(top=0.78, bottom=0.14, left=0.08, right=0.97)
    xs = X[1:]
    comp = [m.loc["comparable_sales_growth", fy] for fy in FY[1:]]
    new = [m.loc["non_comp_growth_52wk", fy] for fy in FY[1:]]
    ax.bar(xs, comp, width=0.45, color=S1, label="Comparable (existing-warehouse) sales")
    ax.bar(xs, new, width=0.45, bottom=[c + 0.0015 for c in comp], color=S2, label="New warehouses & other (residual)")
    for x, c, n in zip(xs, comp, new):
        ax.text(x, c + n + 0.004, f"{c + n:.1%}", ha="center", fontsize=9, color=INK)
    ax.set_xticks(xs, FY[1:]); _pct(ax, step=0.05); ax.set_ylim(0, 0.2)
    ax.legend(loc="upper right")
    _title(fig, "New warehouses add a steady ~2 points of growth a year",
           "Net sales growth (52-week basis) = reported comparable sales + residual. Comps are reported in whole %, so the residual is approximate.")
    _save(fig, "02_growth_decomposition.png")


def profit_engine(m: pd.DataFrame) -> None:
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"wspace": 0.28})
    fig.subplots_adjust(top=0.78, bottom=0.15, left=0.06, right=0.98)
    f, _ = load()
    fee = f.loc["membership_fees", YEARS] / 1000
    merch = [m.loc["merchandise_operating_income", fy] / 1000 for fy in FY]
    a.bar(X, fee, width=0.5, color=S1, label="Membership fees")
    a.bar(X, merch, width=0.5, bottom=[v + 0.06 for v in fee], color=S2, label="Merchandising profit")
    for x, fv, mv in zip(X, fee, merch):
        a.text(x, fv + mv + 0.2, f"${fv + mv:,.1f}bn", ha="center", fontsize=9, color=INK)
    a.set_xticks(X, FY); a.set_ylim(0, 11); a.legend(loc="upper left")
    a.set_title("Operating income by source ($bn)", loc="left", fontsize=10, color=INK2)
    share = [m.loc["membership_fees_pct_operating_income", fy] for fy in FY]
    b.plot(X, share, color=S1)
    for x, v in zip(X, share):
        _dot(b, x, v, S1)
    b.text(X[0], share[0] + 0.03, f"{share[0]:.0%}", ha="center", fontsize=9)
    b.text(X[-1], share[-1] + 0.03, f"{share[-1]:.0%}", ha="center", fontsize=9)
    b.set_xticks(X, FY); b.set_ylim(0, 0.8); _pct(b)
    b.set_title("Membership fees as % of operating income", loc="left", fontsize=10, color=INK2)
    _title(fig, "Membership fees earn about half of operating income on ~2% of revenue",
           "Merchandising profit = operating income − membership fees (goods are priced close to cost).")
    _save(fig, "03_profit_engine.png")


def margins(m: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    fig.subplots_adjust(top=0.78, bottom=0.14, left=0.08, right=0.86)
    series = [("gross_margin_on_net_sales", "Gross margin (on net sales)", S1),
              ("sga_pct_net_sales", "SG&A (% net sales)", S2),
              ("operating_margin", "Operating margin (% revenue)", S3)]
    for key, label, c in series:
        ys = [m.loc[key, fy] for fy in FY]
        ax.plot(X, ys, color=c, label=label)
        _dot(ax, X[-1], ys[-1], c)
        ax.text(X[-1] + 0.12, ys[-1], f"{ys[-1]:.2%}", va="center", fontsize=9)
    ax.set_xticks(X, FY); ax.set_ylim(0, 0.13); _pct(ax, 0); ax.set_xlim(-0.3, 4.6)
    ax.legend(loc="center left", bbox_to_anchor=(0, 0.55))
    _title(fig, "Thin, stable margins: SG&A leverage offset lower gross margin",
           "Gross margin dipped in FY2022 (LIFO charge, gasoline mix) and recovered by FY2024.")
    _save(fig, "04_margins.png")


def membership(m: pd.DataFrame) -> None:
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"wspace": 0.28})
    fig.subplots_adjust(top=0.78, bottom=0.15, left=0.06, right=0.96)
    for key, label, c in [("paid_members_m", "Paid members", S1), ("executive_members_m", "Executive members", S2)]:
        ys = [m.loc[key, fy] for fy in FY]
        a.plot(X, ys, color=c, label=label)
        _dot(a, X[-1], ys[-1], c)
        a.text(X[-1] + 0.12, ys[-1], f"{ys[-1]:.1f}m", va="center", fontsize=9)
    a.set_xticks(X, FY); a.set_ylim(0, 85); a.set_xlim(-0.3, 4.6); a.legend(loc="lower right")
    a.set_title("Members (millions)", loc="left", fontsize=10, color=INK2)
    for key, label, c in [("renewal_rate_us_canada", "Renewal rate, U.S. & Canada", S1),
                          ("renewal_rate_worldwide", "Renewal rate, worldwide", S2)]:
        ys = [m.loc[key, fy] for fy in FY]
        b.plot(X, ys, color=c, label=label)
        _dot(b, X[-1], ys[-1], c)
        b.text(X[-1] + 0.12, ys[-1], f"{ys[-1]:.1%}", va="center", fontsize=9)
    b.set_xticks(X, FY); b.set_ylim(0.85, 0.95); _pct(b); b.set_xlim(-0.3, 4.6); b.legend(loc="lower right")
    b.set_title("Renewal rates (y-axis starts at 85%)", loc="left", fontsize=10, color=INK2)
    _title(fig, "Membership base compounding ~7% a year with ~93% renewal in the core markets",
           "Executive members (2x fee, 2% reward) rose from 39% to 46% of paid members. FY2020–22 rates are rounded in the filings.")
    _save(fig, "05_membership.png")


def returns_and_capex(m: pd.DataFrame) -> None:
    f, _ = load()
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"wspace": 0.28})
    fig.subplots_adjust(top=0.78, bottom=0.15, left=0.06, right=0.97)
    ys = [m.loc["roic", fy] for fy in FY]
    a.plot(X, ys, color=S1)
    for x, v in zip(X, ys):
        _dot(a, x, v, S1)
        a.text(x, v + 0.015, f"{v:.0%}", ha="center", fontsize=9)
    a.set_xticks(X, FY); a.set_ylim(0, 0.4); _pct(a)
    a.set_title("Return on invested capital (after tax, incl. leases)", loc="left", fontsize=10, color=INK2)
    w = 0.32
    cap = f.loc["capex", YEARS] / 1000
    da = f.loc["d_and_a", YEARS] / 1000
    b.bar([x - w / 2 - 0.01 for x in X], cap, width=w, color=S1, label="Capex")
    b.bar([x + w / 2 + 0.01 for x in X], da, width=w, color=S2, label="Depreciation & amortization")
    b.text(X[-1] - w / 2, cap.iloc[-1] + 0.1, f"${cap.iloc[-1]:.1f}bn", ha="center", fontsize=9)
    b.text(X[-1] + w / 2, da.iloc[-1] + 0.1, f"${da.iloc[-1]:.1f}bn", ha="center", fontsize=9)
    b.set_xticks(X, FY); b.set_ylim(0, 5.5); b.legend(loc="upper left")
    b.set_title("Capex vs. D&A ($bn)", loc="left", fontsize=10, color=INK2)
    _title(fig, "~30% returns on capital while reinvesting 2x depreciation",
           "ROIC = operating income × (1 − tax rate) ÷ average (debt + leases + equity − cash & investments). FY2020 uses year-end capital.")
    _save(fig, "06_returns_and_capex.png")


def working_capital(m: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    fig.subplots_adjust(top=0.78, bottom=0.14, left=0.08, right=0.86)
    # end values go in the legend: the two lines converge, so end-labels would collide
    for key, label, c in [("payable_days", "Payable days", S1), ("inventory_days", "Inventory days", S2)]:
        ys = [m.loc[key, fy] for fy in FY]
        ax.plot(X, ys, color=c, label=f"{label} (FY2024: {ys[-1]:.1f})")
        _dot(ax, X[-1], ys[-1], c)
    ax.set_xticks(X, FY); ax.set_ylim(0, 40); ax.set_xlim(-0.3, 4.6); ax.legend(loc="lower left")
    _title(fig, "Suppliers finance the inventory: goods sell before they are paid for",
           "Days on average balances vs. merchandise costs. Operating working capital was −$12.3bn (−4.8% of revenue) in FY2024.")
    _save(fig, "07_working_capital.png")


def cash_uses() -> None:
    d = cash_uses_5yr().iloc[:, 0] / 1000
    labels = list(d.index)[::-1]
    vals = list(d.values)[::-1]
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    fig.subplots_adjust(top=0.78, bottom=0.14, left=0.25, right=0.95)
    colors = [S2 if v < 0 else S1 for v in vals]
    ax.barh(range(len(vals)), [abs(v) for v in vals], height=0.5, color=colors)
    for i, v in enumerate(vals):
        ax.text(abs(v) + 0.5, i, f"${abs(v):,.1f}bn", va="center", fontsize=9)
    ax.set_yticks(range(len(vals)), labels); ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
    ax.set_xlim(0, 55)
    ax.xaxis.set_major_formatter(mt.StrMethodFormatter("${x:,.0f}bn"))
    _title(fig, "FY2020–24: $47.6bn of operating cash; 41% reinvested, 40% paid as dividends",
           "Cumulative. Blue = source, orange = use. Specials: $10/share (Dec 2020) and $15/share (Jan 2024).")
    _save(fig, "08_cash_uses.png")


def segments(m: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    fig.subplots_adjust(top=0.78, bottom=0.14, left=0.08, right=0.83)
    for key, label, c in [("segment_margin_us", "United States", S1), ("segment_margin_canada", "Canada", S2),
                          ("segment_margin_other_intl", "Other International", S3)]:
        ys = [m.loc[key, fy] for fy in FY]
        ax.plot(X, ys, color=c, label=label)
        _dot(ax, X[-1], ys[-1], c)
        ax.text(X[-1] + 0.12, ys[-1], f"{label}  {ys[-1]:.1%}", va="center", fontsize=9)
    ax.set_xticks(X, FY); ax.set_ylim(0, 0.06); _pct(ax, 0); ax.set_xlim(-0.3, 4.4); ax.legend(loc="lower left")
    _title(fig, "Canada and International run higher margins than the U.S.",
           "Segment operating income ÷ segment revenue. The U.S. is 72% of revenue.")
    _save(fig, "09_segment_margins.png")


S1_LIGHT = "#86b6ef"   # blue ramp step 250: forecast years


def forecast_overview() -> None:
    """History (FY2020-24) vs. base-case forecast (FY2025-29)."""
    from src.forecast import build
    fc = build()
    f, _ = load()
    hist_years = YEARS
    fc_cols = [c for c in fc["income_statement"].columns if c.endswith("E")]
    labels = [f"FY{y}" for y in hist_years] + [c[:-1] for c in fc_cols]
    rev = list(f.loc["total_revenue", hist_years] / 1000) + list(fc["income_statement"].loc["total_revenue", fc_cols] / 1000)
    opm = list(f.loc["operating_income", hist_years] / f.loc["total_revenue", hist_years]) + list(fc["income_statement"].loc["operating_margin", fc_cols])
    fcf = list((f.loc["cfo", hist_years] - f.loc["capex", hist_years]) / 1000) + list(fc["cash_flow"].loc["free_cash_flow", fc_cols] / 1000)
    xs = list(range(len(labels)))
    colors = [S1] * len(hist_years) + [S1_LIGHT] * len(fc_cols)
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"wspace": 0.22})
    fig.subplots_adjust(top=0.78, bottom=0.16, left=0.05, right=0.98)
    a.bar(xs, rev, width=0.55, color=colors)
    for x in (0, 4, 9):
        a.text(x, rev[x] + 5, f"${rev[x]:,.0f}bn", ha="center", fontsize=8.5)
    a.set_xticks(xs, [l.replace("FY20", "FY") for l in labels]); a.set_ylim(0, 390)
    a.set_title("Total revenue ($bn)", loc="left", fontsize=10, color=INK2)
    from matplotlib.patches import Patch
    a.legend(handles=[Patch(color=S1, label="Actual"), Patch(color=S1_LIGHT, label="Base-case forecast")], loc="upper left")
    b.bar(xs, fcf, width=0.55, color=colors)
    for x in (0, 4, 9):
        b.text(x, fcf[x] + 0.15, f"${fcf[x]:,.1f}bn", ha="center", fontsize=8.5)
    b.set_xticks(xs, [l.replace("FY20", "FY") for l in labels]); b.set_ylim(0, 11)
    b.set_title("Free cash flow, CFO − capex ($bn)", loc="left", fontsize=10, color=INK2)
    _title(fig, f"Base case: revenue +{(rev[-1] / rev[4]) ** (1 / 5) - 1:.1%} a year to FY2029; operating margin {opm[4]:.2%} → {opm[-1]:.2%}",
           "Margin gain comes from the Sep 2024 membership fee increase; merchandise margins are held flat. Assumptions: config/assumptions.json.",
           SOURCE.replace("author analysis", "FY2025-29 are the author's base-case forecast, not company guidance"))
    _save(fig, "10_forecast_overview.png")


def dcf_bridge() -> None:
    """Per-share build of the DCF value vs. the 31 Jan 2025 share price."""
    from matplotlib.patches import Patch
    from src.dcf import main as dcf_main
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        r = dcf_main()
    n = r["shares_diluted"]
    parts = [("PV of FY2025-29 free cash flow", r["sum_pv_ufcf"] / n), ("PV of terminal value", r["pv_terminal_value"] / n),
             ("Net cash (cash - debt - finance leases)", r["net_cash"] / n)]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    fig.subplots_adjust(top=0.78, bottom=0.14, left=0.30, right=0.95)
    labels, y = [], 0
    rows = len(parts) + 2
    base = 0.0
    for idx, (lab, v) in enumerate(parts):
        yy = rows - 1 - idx
        ax.barh(yy, v, left=base, height=0.5, color=S1_LIGHT)
        ax.text(base + v + 8, yy, f"${v:,.0f}", va="center", fontsize=9)
        base += v
        labels.append((yy, lab))
    yy = 1
    ax.barh(yy, r["value_per_share"], height=0.5, color=S1)
    ax.text(r["value_per_share"] + 8, yy, f"${r['value_per_share']:,.0f}", va="center", fontsize=9, fontweight="bold")
    labels.append((yy, "DCF value per share"))
    ax.barh(0, r["price"], height=0.5, color=S2)
    ax.text(r["price"] + 8, 0, f"${r['price']:,.0f}", va="center", fontsize=9, fontweight="bold")
    labels.append((0, "Share price, 31 Jan 2025"))
    ax.set_yticks([l[0] for l in labels], [l[1] for l in labels])
    ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
    ax.set_xlim(0, 1100); ax.xaxis.set_major_formatter(mt.StrMethodFormatter("${x:,.0f}"))
    # every bar is named on the y-axis, so no legend box is needed
    _title(fig, f"Base-case DCF: ${r['value_per_share']:,.0f} per share vs. ${r['price']:,.0f} market price",
           f"WACC {r['wacc']:.2%}, terminal growth {r['g']:.1%}. The price implies {r['implied_g']:.1%} perpetual growth, or a {r['implied_wacc']:.1%} WACC.",
           SOURCE.replace("author analysis", "Yahoo Finance, FRED, Damodaran; author analysis"))
    _save(fig, "11_dcf_bridge.png")


def comps_chart() -> None:
    """EV/EBITDA and P/E: Costco vs. peers (LTM, 31 Jan 2025)."""
    import contextlib, io
    from src.comps import build as comps_build
    with contextlib.redirect_stdout(io.StringIO()):
        df, stats, implied = comps_build()
    names = {"COST": "Costco", "WMT": "Walmart", "BJ": "BJ's", "TGT": "Target", "KR": "Kroger", "DG": "Dollar General",
             "DLTR": "Dollar Tree", "PSMT": "PriceSmart"}
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"wspace": 0.45})
    fig.subplots_adjust(top=0.78, bottom=0.13, left=0.11, right=0.97)
    for ax, col, title in [(axes[0], "ev_ebitda", "EV / LTM EBITDA"), (axes[1], "pe", "Price / LTM earnings")]:
        d = df[col].dropna().sort_values()
        ys = list(range(len(d)))
        ax.barh(ys, d.values, height=0.55, color=[S2 if t == "COST" else S1 for t in d.index])
        for y, (t, v) in zip(ys, d.items()):
            ax.text(v + d.max() * 0.015, y, f"{v:.1f}x", va="center", fontsize=9, fontweight="bold" if t == "COST" else None,
                    bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1.0), zorder=4)
        med = stats.loc[col, "peer_median"]
        ax.axvline(med, color=INK2, linewidth=1, zorder=1)
        ax.set_yticks(ys, [names[t] for t in d.index]); ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
        ax.set_xlim(0, d.max() * 1.18)
        ax.set_title(f"{title}  (vertical line = peer median, {med:.1f}x)", loc="left", fontsize=10, color=INK2)
    prem = stats.loc["ev_ebitda", "costco"] / stats.loc["ev_ebitda", "peer_median"]
    _title(fig, f"Costco trades at {prem:.1f}x the peer median EV/EBITDA and above Walmart",
           "LTM to each company's latest quarter before 31 Jan 2025, 52-week basis, GAAP. Dollar Tree is not shown: LTM EBITDA and earnings are negative (impairments).",
           SOURCE.replace("Costco 10-K filings FY2020–FY2024 (SEC EDGAR)", "SEC XBRL company facts; Yahoo Finance"))
    _save(fig, "12_comps_multiples.png")


BLUE_RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab"]


def _heatmap(ax, df, fmt="${:,.0f}", base=None):
    from matplotlib.colors import LinearSegmentedColormap
    import matplotlib.patches as mpatches
    cmap = LinearSegmentedColormap.from_list("blue", BLUE_RAMP)
    v = df.values.astype(float)
    ax.imshow(v, cmap=cmap, aspect="auto", vmin=v.min(), vmax=v.max())
    ax.set_xticks(range(df.shape[1]), df.columns); ax.set_yticks(range(df.shape[0]), df.index)
    ax.grid(False)
    for s_ in ax.spines.values():
        s_.set_visible(False)
    for i in range(v.shape[0]):
        for j in range(v.shape[1]):
            lum = (v[i, j] - v.min()) / (v.max() - v.min() + 1e-9)
            ax.text(j, i, fmt.format(v[i, j]), ha="center", va="center", fontsize=9,
                    color="#ffffff" if lum > 0.55 else INK, fontweight="bold" if base == (i, j) else None)
    if base:
        ax.add_patch(mpatches.Rectangle((base[1] - 0.5, base[0] - 0.5), 1, 1, fill=False, edgecolor=INK, linewidth=2))


def sensitivity_charts() -> None:
    import contextlib, io
    from src.sensitivity import run
    with contextlib.redirect_stdout(io.StringIO()):
        out = run()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.0), gridspec_kw={"wspace": 0.35})
    fig.subplots_adjust(top=0.76, bottom=0.14, left=0.08, right=0.98)
    _heatmap(axes[0], out["wacc_g"], base=(2, 2))
    axes[0].set_title("WACC (rows) x terminal growth (columns)", loc="left", fontsize=10, color=INK2)
    rm = out["revenue_margin"].copy()
    rm.index = [i.split(" (")[0].replace("comps", "Comps") for i in rm.index]
    rm.columns = [c.replace("gross margin ", "GM ") for c in rm.columns]
    _heatmap(axes[1], rm, base=(2, 2))
    axes[1].set_title("Comparable-sales growth x gross margin, every year", loc="left", fontsize=10, color=INK2)
    hi = max(out["wacc_g"].values.max(), rm.values.max())
    _title(fig, f"No reasonable input combination gets near the ${out['price']:,.0f} share price (highest cell ${hi:,.0f})",
           "DCF value per share. Outlined = base case ($337). Discount rate and terminal growth matter far more than five-year operating assumptions.",
           SOURCE.replace("author analysis", "Yahoo Finance, FRED, Damodaran; author analysis"))
    _save(fig, "13_sensitivity.png")


def football_field() -> None:
    import contextlib, io
    from src.sensitivity import run
    from src.comps import build as comps_build
    from src.market import prices
    with contextlib.redirect_stdout(io.StringIO()):
        out = run()
        _, stats, implied = comps_build()
    ip = implied.pivot(index="multiple", columns="statistic", values="implied_price")
    sc = out["scenarios"]["value_per_share"]
    wg = out["wacc_g"].iloc[1:4, 1:4].values
    mc = prices("COST", "monthly")["close"]
    last12 = mc[(mc.index > "2024-01-31") & (mc.index <= "2025-01-31")]
    rows = [
        ("52-week range (monthly closes)", last12.min(), last12.max(), None),
        ("DCF: bear / base / bull scenarios", sc["bear"], sc["bull"], sc["base"]),
        ("DCF: WACC +/-0.5pp, growth +/-0.5pp", wg.min(), wg.max(), out["base_value"]),
        ("Comps: EV/EBITDA, peer 25th-75th", ip.loc["ev_ebitda", "peer_25th"], ip.loc["ev_ebitda", "peer_75th"], ip.loc["ev_ebitda", "peer_median"]),
        ("Comps: P/E, peer 25th-75th", ip.loc["pe", "peer_25th"], ip.loc["pe", "peer_75th"], ip.loc["pe", "peer_median"]),
        ("Comps: EV/Revenue, peer 25th-75th", ip.loc["ev_revenue", "peer_25th"], ip.loc["ev_revenue", "peer_75th"], ip.loc["ev_revenue", "peer_median"]),
        ("Comps selected range: Tier 1 median to Walmart", ip.loc["ev_ebitda", "tier1_median"], ip.loc["pe", "walmart"], None),
    ]
    fig, ax = plt.subplots(figsize=(11, 5.2))
    fig.subplots_adjust(top=0.80, bottom=0.12, left=0.33, right=0.95)
    n = len(rows)
    for k, (lab, lo, hi, mid) in enumerate(rows):
        y = n - 1 - k
        ax.barh(y, hi - lo, left=lo, height=0.5, color=S1_LIGHT if k else NEUTRAL)
        ax.text(lo - 8, y, f"${lo:,.0f}", ha="right", va="center", fontsize=8.5)
        ax.text(hi + 8, y, f"${hi:,.0f}", ha="left", va="center", fontsize=8.5)
        if mid is not None:
            _dot(ax, mid, y, S1)
    price = out["price"]
    ax.axvline(price, color=S2, linewidth=2)
    ax.text(price - 12, n - 0.35, f"Share price ${price:,.0f} (31 Jan 2025)", ha="right", va="center", fontsize=9, color=INK)
    ax.set_yticks(range(n), [r[0] for r in rows][::-1])
    ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
    ax.set_xlim(0, 1100); ax.set_ylim(-0.6, n + 0.4)
    ax.xaxis.set_major_formatter(mt.StrMethodFormatter("${x:,.0f}"))
    fund = [r for r in rows[1:]]
    lo_all, hi_all = min(r[1] for r in fund), max(r[2] for r in fund)
    _title(fig, f"Valuation summary: every fundamental method lands between ${lo_all:,.0f} and ${hi_all:,.0f} per share",
           f"Dots = base case / peer median. Probability-weighted DCF (25/50/25) = ${out['scenarios'].attrs['probability_weighted']:,.0f}. The 12-month trading range was ${last12.min():,.0f}-${last12.max():,.0f}.",
           SOURCE.replace("author analysis", "SEC XBRL company facts, Yahoo Finance, FRED, Damodaran; author analysis"))
    _save(fig, "14_football_field.png")


def main() -> None:
    m = compute_metrics()
    revenue_and_growth(m); growth_decomposition(m); profit_engine(m); margins(m)
    membership(m); returns_and_capex(m); working_capital(m); cash_uses(); segments(m); forecast_overview(); dcf_bridge(); comps_chart(); sensitivity_charts(); football_field()
    print(f"{len(list(CHARTS.glob('*.png')))} charts written to outputs/charts/")


if __name__ == "__main__":
    main()
