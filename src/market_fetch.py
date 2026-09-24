"""Downloads the market data: Yahoo Finance prices, FRED rates and spreads, Damodaran's implied ERP.

Yahoo and FRED often block scripted requests, so the files in data/raw/market/ were saved from a browser
and checked against the source responses (see docs/valuation.md). manifest.csv has the URL and SHA-256 of each file.
"""
from __future__ import annotations

import csv
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.config import PEERS, RAW, TICKER

OUT = RAW / "market"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"}
TICKERS = [TICKER, *PEERS.keys(), "^GSPC"]
STOOQ = {"^GSPC": "^spx"}


def _unix(s: str) -> int:
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())


class Fetcher:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update(UA)
        self.log = []

    def get(self, url: str, dest: Path, desc: str) -> bool:
        for attempt in range(3):
            try:
                r = self.s.get(url, timeout=60)
                if r.status_code == 200 and r.content:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(r.content)
                    self.log.append({"file": dest.relative_to(RAW.parent.parent).as_posix(), "url": url, "description": desc,
                                     "downloaded_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                     "bytes": len(r.content), "sha256": hashlib.sha256(r.content).hexdigest()})
                    print(f"  ok   {dest.name}")
                    return True
                print(f"  HTTP {r.status_code} {url}")
            except requests.RequestException as e:
                print(f"  error {e.__class__.__name__}: {url}")
            time.sleep(2 * (attempt + 1))
        return False

    def prices(self, t: str, interval: str, start: str, end: str, tag: str) -> None:
        safe = t.replace("^", "")
        y = (f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1={_unix(start)}&period2={_unix(end)}"
             f"&interval={interval}&events=div%2Csplit&includeAdjustedClose=true")
        if self.get(y, OUT / f"yahoo_{safe}_{tag}.json", f"{t} {interval} prices {start}..{end} (Yahoo)"):
            return
        sym = STOOQ.get(t, f"{t.lower()}.us")
        i = {"1mo": "m", "1d": "d"}[interval]
        q = f"https://stooq.com/q/d/l/?s={sym}&d1={start.replace('-', '')}&d2={end.replace('-', '')}&i={i}"
        if not self.get(q, OUT / f"stooq_{safe}_{tag}.csv", f"{t} {interval} prices (Stooq fallback)"):
            print(f"  !! could not download {t} {tag} from Yahoo or Stooq")


def main() -> None:
    f = Fetcher()
    print("[1/3] Share prices")
    for t in TICKERS:
        f.prices(t, "1mo", "2019-12-01", "2025-02-01", "monthly")
        f.prices(t, "1d", "2025-01-20", "2025-02-05", "daily")
        time.sleep(0.5)
    print("[2/3] Treasury yields and credit spreads (FRED)")
    for sid, desc in [("DGS10", "10-year Treasury yield"), ("DGS30", "30-year Treasury yield"),
                      ("BAMLC0A2CAA", "ICE BofA AA US Corporate OAS"), ("BAMLC0A3CA", "ICE BofA A US Corporate OAS")]:
        f.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd=2024-12-01&coed=2025-02-28",
              OUT / f"fred_{sid}.csv", desc)
    print("[3/3] Damodaran implied equity risk premium")
    f.get("https://pages.stern.nyu.edu/~adamodar/pc/datasets/histimpl.xls", OUT / "damodaran_histimpl.xls",
          "Damodaran implied ERP history (annual, start of year)")
    with open(OUT / "manifest.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(f.log[0].keys()))
        w.writeheader()
        w.writerows(f.log)
    print(f"\nDone: {len(f.log)} files saved to data/raw/market/")


if __name__ == "__main__":
    main()
