"""Small inline-XBRL reader for SEC filings.

Needed because companyfacts doesn't include dimensional facts, and Costco reports membership fees and
segments that way (e.g. Revenues with ProductOrServiceAxis = MembershipMember).
"""
from __future__ import annotations

import re
import warnings
from functools import lru_cache
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

_ZERO_FORMATS = ("fixed-zero", "zerodash", "numdotdecimal-zero")


def _parse_number(tag) -> float | None:
    text = tag.get_text(strip=True)
    fmt = (tag.get("format") or "").lower()
    if any(z in fmt for z in _ZERO_FORMATS) or text in {"—", "–", "-"}:
        num = 0.0
    else:
        cleaned = re.sub(r"[^0-9.]", "", text.replace(",", ""))
        if cleaned in {"", "."}:
            return None
        num = float(cleaned)
    num *= 10 ** int(tag.get("scale") or 0)
    if tag.get("sign") == "-":
        num = -num
    return num


def _contexts(soup) -> dict[str, dict]:
    out = {}
    for c in soup.find_all("xbrli:context"):
        period = c.find("xbrli:period")
        start = period.find("xbrli:startdate")
        end = period.find("xbrli:enddate")
        instant = period.find("xbrli:instant")
        dims = {m["dimension"]: m.get_text(strip=True) for m in c.find_all("xbrldi:explicitmember")}
        out[c["id"]] = {
            "start": start.get_text(strip=True) if start else None,
            "end": (end or instant).get_text(strip=True),
            "period_type": "duration" if start else "instant",
            "dims": dims,
        }
    return out


@lru_cache(maxsize=16)
def read_facts(path: str | Path) -> pd.DataFrame:
    """Return every numeric fact in an iXBRL document as a DataFrame."""
    soup = BeautifulSoup(Path(path).read_bytes(), "lxml")
    ctx = _contexts(soup)
    rows = []
    for t in soup.find_all("ix:nonfraction"):
        c = ctx.get(t.get("contextref"))
        if c is None:
            continue
        rows.append({
            "concept": t.get("name"),
            "value": _parse_number(t),
            "unit": t.get("unitref"),
            "decimals": t.get("decimals"),
            "start": c["start"],
            "end": c["end"],
            "period_type": c["period_type"],
            "dims": "; ".join(f"{k}={v}" for k, v in sorted(c["dims"].items())),
            "n_dims": len(c["dims"]),
            "fact_id": t.get("id"),
            "context_id": t.get("contextref"),
        })
    df = pd.DataFrame(rows)
    return df.drop_duplicates(subset=["concept", "value", "start", "end", "dims"])


def document_text(path: str | Path) -> str:
    """Plain text of the filing with whitespace collapsed (used for operating metrics in MD&A)."""
    soup = BeautifulSoup(Path(path).read_bytes(), "lxml")
    for hidden in soup.find_all("ix:header"):
        hidden.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()
