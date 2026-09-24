"""Downloads the SEC data: companyfacts and filing history for Costco and the peers, plus Costco's
10-K and 10-Q documents. Every file is logged with its SHA-256 in data/raw/manifest.csv.

    export SEC_USER_AGENT="Your Name your.email@example.com"
    python -m src.sec_fetch              # everything
    python -m src.sec_fetch --only PSMT  # add one company

SEC fair-access rules: identify yourself and keep under 10 requests a second.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from src.config import (CIK, FISCAL_YEARS, PEERS, RAW, RAW_FILINGS, RAW_SEC, SETTINGS,
                        TICKER, VALUATION_DATE, cik10)

PAUSE = float(SETTINGS["sec"]["request_pause_seconds"])
MANIFEST = RAW / "manifest.csv"
FILING_INDEX = RAW / "filing_index.csv"


def _session() -> requests.Session:
    ua = os.environ.get(SETTINGS["sec"]["user_agent_env_var"], "").strip()
    if not ua or "@" not in ua:
        sys.exit(
            "Set a User-Agent with contact details before running, e.g.\n"
            '  export SEC_USER_AGENT="Your Name your.email@example.com"\n'
            "The SEC blocks automated requests that do not identify themselves."
        )
    s = requests.Session()
    s.headers.update({"User-Agent": ua, "Accept-Encoding": "gzip, deflate"})
    return s


def _get(session: requests.Session, url: str, retries: int = 4) -> bytes:
    for attempt in range(retries):
        time.sleep(PAUSE)
        r = session.get(url, timeout=60)
        if r.status_code == 200:
            return r.content
        if r.status_code in (429, 500, 502, 503, 504):
            wait = 2 ** attempt
            print(f"  HTTP {r.status_code}, retrying in {wait}s: {url}")
            time.sleep(wait)
            continue
        r.raise_for_status()
    raise RuntimeError(f"Failed after {retries} attempts: {url}")


class Downloader:
    def __init__(self) -> None:
        self.session = _session()
        self.log: list[dict] = []

    def fetch(self, url: str, dest: Path, description: str) -> bytes:
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = _get(self.session, url)
        dest.write_bytes(content)
        self.log.append({
            "file": dest.relative_to(RAW.parent.parent).as_posix(),
            "url": url,
            "description": description,
            "downloaded_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        })
        print(f"  saved {dest.name} ({len(content) / 1e6:.2f} MB)")
        return content

    def write_manifest(self) -> None:
        with open(MANIFEST, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(self.log[0].keys()))
            w.writeheader()
            w.writerows(self.log)


def verify_ciks(dl: Downloader) -> None:
    raw = dl.fetch("https://www.sec.gov/files/company_tickers.json",
                   RAW_SEC / "company_tickers.json", "SEC ticker-to-CIK map")
    by_ticker = {v["ticker"]: int(v["cik_str"]) for v in json.loads(raw).values()}
    expected = {TICKER: CIK, **{t: int(p["cik"]) for t, p in PEERS.items()}}
    for ticker, cik in expected.items():
        found = by_ticker.get(ticker)
        if found != cik:
            sys.exit(f"CIK mismatch for {ticker}: settings.json has {cik}, SEC map has {found}")
    print("  all CIKs in config/settings.json match the SEC ticker map")


def all_filings(dl: Downloader, ticker: str, cik: int) -> list[dict]:
    """Return the company's full filing history as a list of dicts, recent and older pages merged."""
    base = "https://data.sec.gov/submissions/"
    sub = json.loads(dl.fetch(f"{base}CIK{cik10(cik)}.json",
                              RAW_SEC / f"{ticker}_submissions.json", f"{ticker} EDGAR submissions"))
    pages = [sub["filings"]["recent"]]
    for extra in sub["filings"].get("files", []):
        page = json.loads(dl.fetch(base + extra["name"], RAW_SEC / f"{ticker}_{extra['name']}",
                                   f"{ticker} EDGAR submissions (older page)"))
        pages.append(page)
    rows = []
    for page in pages:
        keys = list(page.keys())
        for i in range(len(page["accessionNumber"])):
            rows.append({k: page[k][i] for k in keys})
    return rows


def select_costco_filings(filings: list[dict]) -> list[dict]:
    """Pick the FY2020-FY2024 10-Ks plus any 10-Q filed between FY2024 year-end and the valuation date."""
    first_fy, last_fy = min(FISCAL_YEARS), max(FISCAL_YEARS)
    val_date = date.fromisoformat(VALUATION_DATE)
    chosen = []
    for f in filings:
        if not f.get("reportDate"):
            continue
        period = date.fromisoformat(f["reportDate"])
        filed = date.fromisoformat(f["filingDate"])
        # Costco's fiscal year ends on the Sunday nearest 31 August, so FYxxxx ends in late Aug / early Sep of year xxxx.
        if f["form"] == "10-K" and first_fy <= period.year <= last_fy and period.month in (8, 9):
            f["fiscal_year"] = period.year
            chosen.append(f)
        elif f["form"] == "10-Q" and period > date(last_fy, 9, 1) and filed <= val_date:
            f["fiscal_year"] = last_fy + 1
            chosen.append(f)
    n_10k = sum(f["form"] == "10-K" for f in chosen)
    if n_10k != len(FISCAL_YEARS):
        sys.exit(f"Expected {len(FISCAL_YEARS)} annual reports, found {n_10k}. Check the filing history.")
    return sorted(chosen, key=lambda f: f["reportDate"])


def fetch_only(tickers: list[str]) -> None:
    """Adds companies (e.g. a new peer) to an existing download and appends them to the manifest."""
    dl = Downloader()
    raw = dl.fetch("https://www.sec.gov/files/company_tickers.json",
                   RAW_SEC / "company_tickers.json", "SEC ticker-to-CIK map")
    by_ticker = {v["ticker"]: int(v["cik_str"]) for v in json.loads(raw).values()}
    for t in tickers:
        cik = CIK if t == TICKER else int(PEERS[t]["cik"])
        if by_ticker.get(t) != cik:
            sys.exit(f"CIK mismatch for {t}: settings.json has {cik}, SEC map has {by_ticker.get(t)}")
        dl.fetch(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10(cik)}.json",
                 RAW_SEC / f"{t}_companyfacts.json", f"{t} XBRL company facts")
        all_filings(dl, t, cik)
    old = list(csv.DictReader(open(MANIFEST))) if MANIFEST.exists() else []
    new_files = {r["file"] for r in dl.log}
    rows = [r for r in old if r["file"] not in new_files] + dl.log
    with open(MANIFEST, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(dl.log[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Done. {len(dl.log)} files downloaded and added to {MANIFEST.name}.")


def main() -> None:
    if "--only" in sys.argv:
        return fetch_only(sys.argv[sys.argv.index("--only") + 1:])
    print("Downloading SEC data (this takes about a minute)...")
    dl = Downloader()

    print("\n[1/4] Checking CIKs")
    verify_ciks(dl)

    print("\n[2/4] Company facts (XBRL) for Costco and candidate peers")
    companies = {TICKER: CIK, **{t: int(p["cik"]) for t, p in PEERS.items()}}
    for ticker, cik in companies.items():
        dl.fetch(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10(cik)}.json",
                 RAW_SEC / f"{ticker}_companyfacts.json", f"{ticker} XBRL company facts")

    print("\n[3/4] Filing histories")
    histories = {t: all_filings(dl, t, c) for t, c in companies.items()}

    print("\n[4/4] Costco 10-K and 10-Q documents")
    selected = select_costco_filings(histories[TICKER])
    index_rows = []
    for f in selected:
        accn = f["accessionNumber"]
        url = (f"https://www.sec.gov/Archives/edgar/data/{CIK}/"
               f"{accn.replace('-', '')}/{f['primaryDocument']}")
        name = f"{TICKER}_{f['form']}_FY{f['fiscal_year']}_{f['reportDate']}_{accn}.htm"
        dl.fetch(url, RAW_FILINGS / name, f"{TICKER} {f['form']} for period ending {f['reportDate']}")
        index_rows.append({
            "ticker": TICKER, "form": f["form"], "fiscal_year": f["fiscal_year"],
            "period_end": f["reportDate"], "filing_date": f["filingDate"],
            "accession": accn, "local_file": f"data/raw/filings/{name}", "url": url,
        })

    with open(FILING_INDEX, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(index_rows[0].keys()))
        w.writeheader()
        w.writerows(index_rows)
    dl.write_manifest()

    print(f"\nDone. {len(dl.log)} files downloaded.")
    print(f"  manifest:     {MANIFEST.relative_to(RAW.parent.parent)}")
    print(f"  filing index: {FILING_INDEX.relative_to(RAW.parent.parent)}")
    for r in index_rows:
        print(f"    {r['form']:5s} FY{r['fiscal_year']}  period {r['period_end']}  filed {r['filing_date']}")


if __name__ == "__main__":
    main()
