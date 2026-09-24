"""Render docs/investment_memo.md to outputs/COST_Investment_Memo.pdf (two pages, US Letter).

The markdown file is the single source of truth. This script is a small markdown-to-ReportLab renderer that
supports headings, paragraphs, bullet lists (one level of nesting), pipe tables, block quotes and **bold**.

Run:  python -m src.build_memo      (requires reportlab; fonts: Liberation Sans or DejaVu Sans if available, else Helvetica)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "investment_memo.md"
OUT = ROOT / "outputs" / "COST_Investment_Memo.pdf"

NAVY = colors.HexColor("#1F3864")
INK = colors.HexColor("#1A1A1A")
MUTED = colors.HexColor("#555555")
RULE = colors.HexColor("#BFBFBF")
TINT = colors.HexColor("#EEF2F8")


def register_fonts() -> tuple[str, str]:
    candidates = [
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
        ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ]
    for reg, bold in candidates:
        if Path(reg).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont("MemoSans", reg))
            pdfmetrics.registerFont(TTFont("MemoSans-Bold", bold))
            pdfmetrics.registerFontFamily("MemoSans", normal="MemoSans", bold="MemoSans-Bold", italic="MemoSans", boldItalic="MemoSans-Bold")
            return "MemoSans", "MemoSans-Bold"
    return "Helvetica", "Helvetica-Bold"


def inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


def build(src: Path = SRC, out: Path = OUT, base_size: float = 8.6) -> int:
    reg, bold = register_fonts()
    lead = base_size * 1.28
    st = {
        "title": ParagraphStyle("title", fontName=bold, fontSize=13.5, leading=16.5, textColor=NAVY, spaceAfter=2),
        "sub": ParagraphStyle("sub", fontName=reg, fontSize=base_size, leading=lead, textColor=MUTED, spaceAfter=4),
        "h2": ParagraphStyle("h2", fontName=bold, fontSize=base_size + 1.6, leading=lead + 2, textColor=NAVY, spaceBefore=5, spaceAfter=2),
        "body": ParagraphStyle("body", fontName=reg, fontSize=base_size, leading=lead, textColor=INK, alignment=TA_LEFT, spaceAfter=3),
        "cell": ParagraphStyle("cell", fontName=reg, fontSize=base_size - 0.4, leading=lead - 0.8, textColor=INK),
        "cellr": ParagraphStyle("cellr", fontName=reg, fontSize=base_size - 0.4, leading=lead - 0.8, textColor=INK, alignment=TA_RIGHT),
        "cellbr": ParagraphStyle("cellbr", fontName=bold, fontSize=base_size - 0.4, leading=lead - 0.8, textColor=INK, alignment=TA_RIGHT),
        "cellb": ParagraphStyle("cellb", fontName=bold, fontSize=base_size - 0.4, leading=lead - 0.8, textColor=INK),
        "quote": ParagraphStyle("quote", fontName=bold, fontSize=base_size, leading=lead, textColor=colors.HexColor("#C00000"), spaceAfter=4),
    }
    lines = src.read_text().splitlines()
    story, i = [], 0
    width = letter[0] - 1.2 * inch

    def flush_table(rows):
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows if not re.match(r"^\|\s*:?-", r.strip())]
        header_empty = all(c == "" for c in cells[0])
        body = cells[1:] if header_empty else cells
        ncol = len(cells[0])
        numeric = [all(re.match(r"^[\d$().,%x−\- ]+$", r[j]) for r in cells[1:] if r[j]) for j in range(ncol)]
        data = []
        for ri, r in enumerate(body):
            is_head = (not header_empty) and ri == 0
            row = []
            for j, c in enumerate(r):
                b = is_head or (header_empty and j == 0)
                right = (not header_empty) and numeric[j] and j > 0
                row.append(Paragraph(inline(c), st[("cellb" if b else "cell") + ("r" if right else "")] if not (b and right) else st["cellbr"]))
            data.append(row)
        if header_empty:
            colw = [1.45 * inch, width - 1.45 * inch]
        else:
            first = 2.1 * inch
            last = 2.2 * inch if ncol > 3 else (width - first) / (ncol - 1)
            mid = (width - first - last) / max(ncol - 2, 1) if ncol > 3 else last
            colw = [first] + [mid] * (ncol - 2) + [last] if ncol > 2 else [first, width - first]
        t = Table(data, colWidths=colw, hAlign="LEFT")
        style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
                 ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                 ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE)]
        if header_empty:
            style += [("BACKGROUND", (0, 0), (-1, -1), TINT)]
        else:
            style += [("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY)]
            for j in range(1, ncol):
                if numeric[j]:
                    style.append(("ALIGN", (j, 0), (j, -1), "RIGHT"))
        t.setStyle(TableStyle(style))
        story.append(t)
        story.append(Spacer(1, 4))

    def flush_list(items):
        flow = []
        for text, subs in items:
            p = Paragraph(inline(text), st["body"])
            if subs:
                sub = ListFlowable([ListItem(Paragraph(inline(s), st["body"]), leftIndent=10, value="–") for s in subs],
                                   bulletType="bullet", start="–", leftIndent=10, bulletFontSize=base_size)
                flow.append(ListItem([p, sub], leftIndent=10))
            else:
                flow.append(ListItem(p, leftIndent=10))
        story.append(ListFlowable(flow, bulletType="bullet", start="•", leftIndent=10, bulletFontSize=base_size))

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1
            continue
        if s.startswith("# "):
            story.append(Paragraph(inline(s[2:]), st["title"]))
        elif s.startswith("## "):
            story.append(Paragraph(inline(s[3:]), st["h2"]))
        elif s.startswith("!["):
            m = re.match(r"!\[(.*?)\]\((.*?)\)", s)
            path = (src.parent / m.group(2)).resolve()
            if path.exists():
                from reportlab.lib.utils import ImageReader
                iw, ih = ImageReader(str(path)).getSize()
                w = width * 0.72
                story.append(Image(str(path), width=w, height=w * ih / iw))
                story.append(Spacer(1, 3))
        elif s.startswith("> "):
            story.append(Paragraph(inline(s[2:]), st["quote"]))
        elif s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            flush_table(rows)
            continue
        elif s.startswith("- "):
            items = []
            while i < len(lines) and (lines[i].strip().startswith("- ") or lines[i].startswith("  - ")):
                if lines[i].startswith("  - "):
                    items[-1][1].append(lines[i].strip()[2:])
                else:
                    items.append((lines[i].strip()[2:], []))
                i += 1
            flush_list(items)
            continue
        else:
            style = st["sub"] if s.startswith("Equity research memo") or s.startswith("Full model") else st["body"]
            story.append(Paragraph(inline(s), style))
        i += 1

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(reg, 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(0.6 * inch, 0.4 * inch, "Independent academic research and valuation case study; not investment advice. "
                          "Sources: Costco 10-K/10-Q, Yahoo Finance, FRED, Damodaran.")
        canvas.setFont(reg, 7)
        canvas.drawRightString(letter[0] - 0.6 * inch, 0.4 * inch, f"Page {doc.page}")
        canvas.restoreState()

    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out), pagesize=letter, leftMargin=0.6 * inch, rightMargin=0.6 * inch, topMargin=0.5 * inch,
                            bottomMargin=0.6 * inch, title="Costco (COST) Investment Memo", author="Pooja Master",
                            subject="Independent academic research and valuation case study; not investment advice")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    from pypdf import PdfReader
    return len(PdfReader(str(out)).pages)


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT
    print("pages:", build(src, out))
