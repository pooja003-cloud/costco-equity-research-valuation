"""Chart pack for the historical analysis (static PNGs for GitHub and the memo).

Style: one quiet system across every chart.
- Categorical colors come from a validated palette, in fixed order: blue, orange, aqua.
  Colorblind separation was checked with a validator.
- Marks are thin, gridlines are hairlines, and there is only ever one y-axis per panel.
- Text is ink colored, never series colored. Every chart with two or more series has a legend and selective direct labels.
"""
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


def _title(fig, title: str, subtitle: str) -> None:
    fig.text(0.02, 0.97, title, fontsize=13, fontweight="bold", color=INK, va="top", parse_math=False)
    fig.text(0.02, 0.905, subtitle, fontsize=9.5, color=INK2, va="top", parse_math=False)
    fig.text(0.02, 0.015, SOURCE, fontsize=7.5, color=MUTED)


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


def main() -> None:
    m = compute_metrics()
    revenue_and_growth(m); growth_decomposition(m); profit_engine(m); margins(m)
    membership(m); returns_and_capex(m); working_capital(m); cash_uses(); segments(m)
    print(f"{len(list(CHARTS.glob('*.png')))} charts written to outputs/charts/")


if __name__ == "__main__":
    main()
