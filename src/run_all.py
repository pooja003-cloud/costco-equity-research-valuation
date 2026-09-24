"""Rebuild the whole project in order: data, forecast, valuation, Excel model, charts, memo and slides.

Usage (from the repository root, with the virtual environment active):
    python -m src.run_all              # full rebuild, including the SEC download
    python -m src.run_all --offline    # skip all downloads and use the files already in data/raw/
    python -m src.run_all --refresh-market   # also re-download market data (Yahoo Finance often blocks this)

The SEC download needs a contact e-mail in the SEC_USER_AGENT environment variable.
Market data (prices, rates, equity risk premium) is committed in data/raw/market/, so it is not re-downloaded by default.
Each step is described in docs/reproducing.md. The run stops at the first step that fails.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    # (module, what it does, kind)   kind: "sec" / "market" = download steps
    ("src.sec_fetch", "Download filings and company data from SEC EDGAR", "sec"),
    ("src.market_fetch", "Download share prices, interest rates and the equity risk premium", "market"),
    ("src.extract_financials", "Financial statements from Costco's 10-K filings", None),
    ("src.operating_metrics", "Members, renewal rates and comparable sales, checked against the filing text", None),
    ("src.historical", "Historical ratios", None),
    ("src.extract_quarter", "Latest quarter before the valuation date (10-Q)", None),
    ("src.forecast", "Five-year forecast of the three financial statements", None),
    ("src.wacc", "Required return (weighted average cost of capital)", None),
    ("src.dcf", "Discounted cash flow valuation and reverse DCF", None),
    ("src.comps", "Comparable companies", None),
    ("src.sensitivity", "Sensitivity tables and scenarios", None),
    ("src.build_excel", "Excel model", None),
    ("src.charts", "Charts", None),
    ("src.build_memo", "Two-page investment memo (PDF)", None),
]


def run(cmd: list[str], label: str, n: int, total: int) -> None:
    print(f"\n[{n}/{total}] {label}\n      $ {' '.join(cmd)}", flush=True)
    t = time.time()
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        sys.exit(f"\nStopped: step {n} ({label}) failed. Fix the error above and run again.")
    print(f"      done in {time.time() - t:.1f}s", flush=True)


def main() -> None:
    offline = "--offline" in sys.argv
    refresh_market = "--refresh-market" in sys.argv
    steps = [s for s in STEPS
             if not (s[2] == "sec" and offline) and not (s[2] == "market" and (offline or not refresh_market))]
    node_check = "for (const m of ['pptxgenjs','react','react-dom','react-icons/fa','sharp']) require(m)"
    deck = bool(shutil.which("node")) and subprocess.run(["node", "-e", node_check], cwd=ROOT,
                                                         capture_output=True).returncode == 0
    total = len(steps) + (1 if deck else 0)
    for i, (mod, label, _) in enumerate(steps, 1):
        run([sys.executable, "-m", mod], label, i, total)
    if deck:
        run(["node", "scripts/build_deck.js"], "Slides (PowerPoint)", total, total)
    else:
        print("\nSkipped the slides: they need Node.js and `npm install pptxgenjs react react-dom react-icons sharp`.")
    print("\nAll steps finished. Open outputs/COST_Valuation_Model.xlsx in Excel to recalculate the formulas, "
          "then run `python -m pytest -q` for the automated checks.")


if __name__ == "__main__":
    main()
