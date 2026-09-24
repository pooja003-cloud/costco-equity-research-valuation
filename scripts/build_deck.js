// Build outputs/COST_Equity_Research_Deck.pptx: title, investment thesis, valuation summary,
// and "Risks and What Would Change My View".
//
// Every number on the slides is read from the model outputs in outputs/tables/ (and the monthly price file),
// so the deck cannot drift from the Python model. Re-run after `python -m src.sensitivity` etc.
//
// Requires Node 18+ and: npm install pptxgenjs react react-dom react-icons sharp
// Run from the repo root:  node scripts/build_deck.js
// PDF copy (LibreOffice):  soffice --headless --convert-to pdf --outdir outputs outputs/COST_Equity_Research_Deck.pptx

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const { FaIdCard, FaWarehouse, FaChartLine, FaExclamationTriangle, FaUndoAlt, FaSearchDollar } = require("react-icons/fa");

const ROOT = path.resolve(__dirname, "..");
const T = (f) => path.join(ROOT, "outputs", "tables", f);
const OUT = path.join(ROOT, "outputs", "COST_Equity_Research_Deck.pptx");

// ---------- data -------------------------------------------------------------------------------------------------
function readCsv(file) {
  const [head, ...rows] = fs.readFileSync(file, "utf8").trim().split(/\r?\n/).map(splitCsv);
  return { head, rows };
}
function splitCsv(line) {
  const out = []; let cur = ""; let q = false;
  for (const ch of line) {
    if (ch === '"') q = !q;
    else if (ch === "," && !q) { out.push(cur); cur = ""; }
    else cur += ch;
  }
  out.push(cur);
  return out;
}
// two-column item,value table -> {item: number}
function kv(file) {
  const o = {};
  for (const r of readCsv(file).rows) o[r[0]] = Number(r[1]);
  return o;
}
// matrix table with row labels in col 0 -> {row: {col: number}}
function grid(file) {
  const { head, rows } = readCsv(file);
  const o = {};
  for (const r of rows) { o[r[0]] = {}; head.slice(1).forEach((h, j) => { o[r[0]][h] = Number(r[j + 1]); }); }
  return o;
}

const dcf = kv(T("dcf_summary.csv"));
const wacc = kv(T("wacc.csv"));
const hist = grid(T("historical_metrics.csv"));
const fis = grid(T("forecast_income_statement.csv"));
const comps = grid(T("comps_statistics.csv"));
const scen = grid(T("sens_scenarios.csv"));
const wg = grid(T("sens_wacc_g.csv"));
const rm = grid(T("sens_revenue_margin.csv"));
const implied = {};
for (const r of readCsv(T("comps_implied_value.csv")).rows) implied[`${r[0]}|${r[1]}`] = Number(r[5]);
const dur = readCsv(T("reverse_dcf_growth_duration.csv")).rows.map((r) => r.map(Number));
const dur7 = dur.find((r) => r[0] === 0.25 && r[1] === 0.07);
const dur8 = dur.find((r) => r[0] === 0.25 && r[1] === 0.08);
const monthly = readCsv(path.join(ROOT, "data", "raw", "market", "yahoo_COST_monthly.csv")).rows
  .filter((r) => r[0] > "2024-01-31" && r[0] <= "2025-01-31").map((r) => Number(r[1]));

const price = dcf["Share price 31 Jan 2025 ($)"];
const base = dcf["Value per share ($)"];
const bear = scen.bear.value_per_share, bull = scen.bull.value_per_share;
const pw = ["bear", "base", "bull"].reduce((s, k) => s + scen[k].probability * scen[k].value_per_share, 0);
const wgRows = Object.keys(wg).slice(1, 4), wgCols = Object.keys(wg[wgRows[0]]).slice(1, 4);
const wgVals = wgRows.flatMap((r) => wgCols.map((c) => wg[r][c]));
const rmVals = Object.values(rm).flatMap((r) => Object.values(r));
// value at WACC one grid step (50bp) lower than base, same g
const wgKeys = Object.keys(wg);
const baseRow = wgKeys.find((k) => Math.abs(wg[k]["3.0%"] - base) < 0.01);
const lowerRow = wgKeys[wgKeys.indexOf(baseRow) - 1];

const $ = (v) => "$" + Math.round(v).toLocaleString("en-US");
const pct = (v, d = 1) => (v * 100).toFixed(d) + "%";
const x = (v, d = 0) => v.toFixed(d) + "x";

const N = {
  price: $(price), base: $(base), bear: $(bear), bull: $(bull), pw: $(pw),
  down: pct(dcf["Upside / (downside)"], 0).replace("-", "−"),
  gImp: pct(dcf["Reverse DCF: terminal growth implied by price"]),
  wImp: pct(dcf["Reverse DCF: WACC implied by price"]),
  wacc: pct(dcf.WACC, 2), g: pct(dcf["Terminal growth"]), ronic: pct(dcf["Terminal RONIC"], 0),
  tvShare: pct(dcf["Terminal value as % of EV"], 0), tvMult: x(dcf["Implied terminal EV/EBITDA (FY2029 year-end basis, comparable to trading multiples)"], 1),
  rf: pct(wacc["Risk-free rate (10y UST, 31 Jan 2025)"], 2), erp: pct(wacc["Equity risk premium (Damodaran, Jan 2025)"], 2),
  beta: wacc["Adjusted beta (Blume)"].toFixed(2),
  feeShare: pct(hist.membership_fees_pct_operating_income.FY2024, 0),
  renewal: pct(hist.renewal_rate_us_canada.FY2024),
  nwc: pct(hist.operating_nwc_pct_revenue.FY2024).replace("-", "−"),
  roic: pct(hist.roic.FY2024, 0),
  revCagr: pct(Math.pow(fis.total_revenue.FY2029E / fis.total_revenue.FY2024A, 1 / 5) - 1),
  rev29: "$" + (fis.total_revenue.FY2029E / 1000).toFixed(1) + "bn",
  eps29: "$" + fis.eps_diluted.FY2029E.toFixed(2),
  om24: pct(fis.operating_margin.FY2024A, 2), om29: pct(fis.operating_margin.FY2029E, 2),
  feeG25: pct(fis.membership_fees.FY2025E / fis.membership_fees.FY2024A - 1, 0),
  pe: x(comps.pe.costco), peMed: x(comps.pe.peer_median), evE: x(comps.ev_ebitda.costco, 1), evEMed: x(comps.ev_ebitda.peer_median, 1),
  opLo: $(Math.min(...rmVals)), opHi: $(Math.max(...rmVals)),
  lowerW: lowerRow, lowerV: $(wg[lowerRow]["3.0%"]),
  dur8: dur8[2], dur7_100: $(dur7[5]),
  t1Lo: $(implied["ev_ebitda|tier1_median"]), t1Hi: $(implied["pe|walmart"]),
};

// ---------- design -----------------------------------------------------------------------------------------------
const C = {
  navy: "14213D", navy2: "22335A", ink: "1A1A1A", muted: "5C5C5C", tint: "EEF2F8", line: "D5DAE3",
  blue: "2A78D6", orange: "E8702A", white: "FFFFFF", ice: "CADCFC",
};
const HEAD = "Cambria", BODY = "Calibri";
const DISCLAIMER = "Independent academic research and valuation case study; not investment advice.";

async function icon(Comp, color, px = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: px }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

function footer(s, source, dark = false) {
  s.addText(`${DISCLAIMER}  Sources: ${source}`, {
    x: 0.5, y: 5.22, w: 8.3, h: 0.25, fontFace: BODY, fontSize: 7.5, color: dark ? "AEB8CC" : C.muted, margin: 0, isTextBox: true,
  });
}
function pageNo(s, n, dark = false) {
  s.addText(String(n), { x: 9.0, y: 5.22, w: 0.5, h: 0.25, fontFace: BODY, fontSize: 7.5, color: dark ? "AEB8CC" : C.muted, align: "right", margin: 0, isTextBox: true });
}
function title(s, text) {
  s.addText(text, { x: 0.5, y: 0.32, w: 9.0, h: 0.62, fontFace: HEAD, fontSize: 26, bold: true, color: C.navy, margin: 0, valign: "middle", isTextBox: true });
}

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
  pres.author = "Pooja Master";
  pres.title = "Costco (COST) equity research: investment thesis, valuation and risks";
  pres.subject = DISCLAIMER;

  const ic = {
    fee: await icon(FaIdCard, C.white), cost: await icon(FaWarehouse, C.white), growth: await icon(FaChartLine, C.white),
    risk: await icon(FaExclamationTriangle, C.white), wrong: await icon(FaUndoAlt, C.white), change: await icon(FaSearchDollar, C.navy),
  };
  const circle = (s, img, xx, yy, d = 0.46, fill = C.navy) => {
    s.addShape(pres.shapes.OVAL, { x: xx, y: yy, w: d, h: d, fill: { color: fill }, line: { color: fill } });
    s.addImage({ data: img, x: xx + d * 0.25, y: yy + d * 0.25, w: d * 0.5, h: d * 0.5 });
  };

  // ---------------- 1. Title ------------------------------------------------------------------------------------
  {
    const s = pres.addSlide();
    s.background = { color: C.navy };
    s.addText("EQUITY RESEARCH  |  VALUATION CASE STUDY", { x: 0.6, y: 0.55, w: 8.8, h: 0.3, fontFace: BODY, fontSize: 11, bold: true, color: C.ice, charSpacing: 2, margin: 0, isTextBox: true });
    s.addText("Costco Wholesale (NASDAQ: COST)", { x: 0.6, y: 1.0, w: 8.8, h: 0.75, fontFace: HEAD, fontSize: 38, bold: true, color: C.white, margin: 0, isTextBox: true });
    s.addText("A great business at a price the cash flows cannot reach", { x: 0.6, y: 1.8, w: 8.8, h: 0.45, fontFace: HEAD, fontSize: 18, italic: true, color: C.ice, margin: 0, isTextBox: true });

    const stats = [
      [N.price, "Share price, 31 Jan 2025"],
      [N.base, "Base-case DCF value per share"],
      [N.down, "Value vs. price"],
    ];
    stats.forEach(([big, small], k) => {
      const xx = 0.6 + k * 2.95;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: xx, y: 2.75, w: 2.7, h: 1.35, fill: { color: C.navy2 }, line: { color: C.navy2 }, rectRadius: 0.08 });
      s.addText(big, { x: xx + 0.2, y: 2.9, w: 2.3, h: 0.7, fontFace: HEAD, fontSize: 34, bold: true, color: k === 2 ? C.orange : C.white, margin: 0, isTextBox: true });
      s.addText(small, { x: xx + 0.2, y: 3.6, w: 2.3, h: 0.35, fontFace: BODY, fontSize: 11.5, color: C.ice, margin: 0, isTextBox: true });
    });
    s.addText("Pooja Master  |  Valuation date: 31 January 2025  |  github.com/pooja003-cloud/costco-equity-research-valuation", {
      x: 0.6, y: 4.45, w: 8.8, h: 0.3, fontFace: BODY, fontSize: 11, color: C.white, margin: 0, isTextBox: true,
    });
    s.addText(DISCLAIMER, { x: 0.6, y: 4.8, w: 8.8, h: 0.3, fontFace: BODY, fontSize: 11, bold: true, color: C.orange, margin: 0, isTextBox: true });
    s.addNotes("Costco equity research case study, valued at 31 January 2025 using only filings available on that date. " +
      `The share price was ${N.price}; the base-case DCF gives ${N.base}. The rest of the deck explains the gap. ${DISCLAIMER}`);
  }

  // ---------------- 2. Investment thesis ------------------------------------------------------------------------
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    title(s, "Investment thesis: admire the business, not the price");

    const rows = [
      [ic.fee, "A fee engine that makes earnings durable",
        `Membership fees were ${N.feeShare} of FY2024 operating income, with ${N.renewal} renewal in the U.S. and Canada. The Sep 2024 fee rise lifts fee growth to ~${N.feeG25} in FY2025.`],
      [ic.cost, "A cost structure rivals struggle to copy",
        `Fewer than 4,000 SKUs, suppliers paid after goods sell and fees collected upfront: working capital is ${N.nwc} of revenue and ROIC ${N.roic} in FY2024.`],
      [ic.growth, "Growth is steady, not explosive",
        `Base case: revenue +${N.revCagr} a year to ${N.rev29} by FY2029, operating margin ${N.om24} to ${N.om29}, EPS ${N.eps29}.`],
    ];
    rows.forEach(([img, head, body], k) => {
      const yy = 1.2 + k * 1.2;
      circle(s, img, 0.5, yy + 0.02);
      s.addText(head, { x: 1.12, y: yy, w: 4.4, h: 0.3, fontFace: BODY, fontSize: 14, bold: true, color: C.navy, margin: 0, isTextBox: true });
      s.addText(body, { x: 1.12, y: yy + 0.32, w: 4.4, h: 0.78, fontFace: BODY, fontSize: 11.5, color: C.ink, margin: 0, valign: "top", isTextBox: true });
    });

    // right: valuation card
    const cx = 5.85, cy = 1.15, cw = 3.65, ch = 3.75;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx, y: cy, w: cw, h: ch, fill: { color: C.navy }, line: { color: C.navy }, rectRadius: 0.08 });
    s.addText("But the price assumes far more", { x: cx + 0.25, y: cy + 0.2, w: cw - 0.5, h: 0.32, fontFace: BODY, fontSize: 14, bold: true, color: C.white, margin: 0, isTextBox: true });
    s.addText([
      { text: N.base, options: { fontSize: 30, bold: true, color: C.white, fontFace: HEAD } },
      { text: "  base-case DCF", options: { fontSize: 11.5, color: C.ice } },
    ], { x: cx + 0.25, y: cy + 0.6, w: cw - 0.5, h: 0.55, margin: 0, valign: "middle", fontFace: BODY, isTextBox: true });
    s.addText([
      { text: N.price, options: { fontSize: 30, bold: true, color: C.orange, fontFace: HEAD } },
      { text: "  share price", options: { fontSize: 11.5, color: C.ice } },
    ], { x: cx + 0.25, y: cy + 1.15, w: cw - 0.5, h: 0.55, margin: 0, valign: "middle", fontFace: BODY, isTextBox: true });
    s.addText([
      { text: `To justify the price, cash flows must grow ${N.gImp} a year forever after FY2029 (base case ${N.g}),`, options: { bullet: true, breakLine: true } },
      { text: `or the cost of capital must be ${N.wImp} (base case ${pct(dcf.WACC, 1)}).`, options: { bullet: true, breakLine: true } },
      { text: `Costco trades at ${N.pe} LTM earnings; the peer median is ${N.peMed}.`, options: { bullet: true } },
    ], { x: cx + 0.25, y: cy + 1.85, w: cw - 0.45, h: 1.75, fontFace: BODY, fontSize: 11.5, color: C.white, paraSpaceAfter: 5, margin: 0, valign: "top", isTextBox: true });

    s.addText([
      { text: "View: ", options: { bold: true, color: C.navy } },
      { text: `overvalued on fundamentals. Bear / base / bull ${N.bear} / ${N.base} / ${N.bull}; probability-weighted ${N.pw}.`, options: { color: C.ink } },
    ], { x: 0.5, y: 4.62, w: 5.1, h: 0.45, fontFace: BODY, fontSize: 11.5, margin: 0, valign: "middle", isTextBox: true });
    footer(s, "Costco 10-K FY2024 and 10-Q Q1 FY2025 (SEC EDGAR); Yahoo Finance; model outputs.");
    pageNo(s, 2);
    s.addNotes("Three reasons Costco is an exceptional business: the membership fee stream, the negative-working-capital cost model, and steady mid-single-digit growth. " +
      `The problem is price. The base-case DCF is ${N.base} against ${N.price}; the reverse DCF says the market is pricing ${N.gImp} perpetual growth or a ${N.wImp} cost of capital.`);
  }

  // ---------------- 3. Valuation --------------------------------------------------------------------------------
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    title(s, `Valuation: all methods land far below ${N.price}`);

    const rows = [
      ["52-week range (monthly closes)", Math.min(...monthly), Math.max(...monthly), true],
      ["DCF: bear / base / bull", bear, bull],
      ["DCF: WACC and growth ±0.5pp", Math.min(...wgVals), Math.max(...wgVals)],
      ["Comps: EV/EBITDA, peer 25th–75th", implied["ev_ebitda|peer_25th"], implied["ev_ebitda|peer_75th"]],
      ["Comps: P/E, peer 25th–75th", implied["pe|peer_25th"], implied["pe|peer_75th"]],
      ["Comps: EV/Revenue, peer 25th–75th", implied["ev_revenue|peer_25th"], implied["ev_revenue|peer_75th"]],
      ["Comps: Walmart & BJ's, selected", implied["ev_ebitda|tier1_median"], implied["pe|walmart"]],
      ["7% growth for 10 to 100 more years", dur7[3], dur7[5]],
    ];
    const labels = rows.map(([l, lo, hi]) => `${l}   ${$(lo)}–${$(hi).slice(1)}`);
    const data = [
      { name: "Offset", labels, values: rows.map((r) => r[1]) },
      { name: "Fundamental value range", labels, values: rows.map((r) => (r[3] ? 0 : r[2] - r[1])) },
      { name: "Market price range", labels, values: rows.map((r) => (r[3] ? r[2] - r[1] : 0)) },
    ];
    const ch = { x: 0.35, y: 1.1, w: 6.25, h: 3.75 };
    const pl = { x: 0.47, y: 0.03, w: 0.5, h: 0.85 }; // inner plot area, fractions of chart frame
    const axMax = 1100;
    s.addChart(pres.charts.BAR, data, {
      ...ch, barDir: "bar", barGrouping: "stacked", barGapWidthPct: 55,
      chartColors: [C.white, C.blue, C.orange], showLegend: false,
      layout: { ...pl },
      catAxisOrientation: "maxMin", catAxisLabelFontFace: BODY, catAxisLabelFontSize: 9, catAxisLabelColor: C.ink,
      catAxisLineShow: false, catGridLine: { style: "none" },
      valAxisMinVal: 0, valAxisMaxVal: axMax, valAxisMajorUnit: 250, valAxisLabelFormatCode: "$#,##0",
      valAxisLabelFontFace: BODY, valAxisLabelFontSize: 9, valAxisLabelColor: C.muted, valAxisLineShow: false,
      valGridLine: { style: "none" },
    });
    // share-price marker, positioned from the fixed inner plot layout
    const px = ch.x + ch.w * (pl.x + pl.w * (price / axMax));
    s.addShape(pres.shapes.LINE, { x: px, y: ch.y + ch.h * pl.y - 0.05, w: 0, h: ch.h * pl.h + 0.05, line: { color: C.orange, width: 2, dashType: "dash" } });
    s.addText(`Price ${N.price}`, { x: px - 0.6, y: ch.y + ch.h * (pl.y + pl.h) + 0.04, w: 1.2, h: 0.22, fontFace: BODY, fontSize: 9.5, bold: true, color: C.orange, align: "center", margin: 0, isTextBox: true });

    // right: three stat cards
    const cards = [
      [N.wacc, "WACC", `Risk-free ${N.rf}, Blume beta ${N.beta}, Damodaran ERP ${N.erp}; debt is 1.5% of capital.`],
      [N.tvShare, "of EV is terminal value", `Growth ${N.g}, reinvestment set by a ${N.ronic} return on new capital; ${N.tvMult} FY2029 EBITDA at year-end.`],
      [`${N.opLo}–${N.opHi.slice(1)}`, "operating range", "Comparable sales ±2pp a year and gross margin ±30bp. The gap is about duration and discount rate, not next year's numbers."],
    ];
    cards.forEach(([big, lab, body], k) => {
      const yy = 1.12 + k * 1.28;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.8, y: yy, w: 2.7, h: 1.15, fill: { color: C.tint }, line: { color: C.tint }, rectRadius: 0.06 });
      s.addText([
        { text: big, options: { fontFace: HEAD, fontSize: 20, bold: true, color: C.navy } },
        { text: "  " + lab, options: { fontSize: 10.5, bold: true, color: C.navy } },
      ], { x: 6.95, y: yy + 0.08, w: 2.45, h: 0.38, fontFace: BODY, margin: 0, valign: "middle", isTextBox: true });
      s.addText(body, { x: 6.95, y: yy + 0.47, w: 2.45, h: 0.62, fontFace: BODY, fontSize: 9.5, color: C.ink, margin: 0, valign: "top", isTextBox: true });
    });
    footer(s, "model outputs (outputs/tables); peers WMT, BJ, TGT, KR, DG, DLTR from SEC filings; FRED; Damodaran.");
    pageNo(s, 3);
    s.addNotes(`Football field of every valuation method. Base-case DCF ${N.base} (WACC ${N.wacc}, terminal growth ${N.g}). ` +
      `Peer-median multiples imply $240 (EV/EBITDA) and $280 (P/E); Walmart and BJ's multiples ${N.t1Hi.length ? N.t1Lo + "–" + N.t1Hi.slice(1) : ""}. ` +
      `Even 7% growth for 100 years after FY2029 gives only ${N.dur7_100}. Operating sensitivities move value only ${N.opLo}–${N.opHi.slice(1)}.`);
  }

  // ---------------- 4. Risks and what would change my view ------------------------------------------------------
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    title(s, "Risks and what would change my view");

    const blocks = [
      [ic.wrong, "Why I could be wrong (upside risk)", [
        // $596 / $713: src.dcf.value() at WACC 6.0% / 5.5%, base g and RONIC (docs/sensitivity.md)
        `Investors keep pricing Costco like a bond: a 6.0% WACC gives ~$596, 5.5% ~$713.`,
        "International expansion sustains 8–10% growth for decades.",
        "New high-margin income: retail media, financial services, faster fee increases.",
      ]],
      [ic.risk, "Risks to the business (downside)", [
        "Consumer slowdown; price competition from Walmart/Sam's Club and Amazon.",
        "Wage and tariff cost inflation.",
        "New warehouses cannibalize old ones and slow member growth.",
        `Multiple compression from ${N.pe} earnings toward the peer range.`,
      ]],
    ];
    let yy = 1.15;
    blocks.forEach(([img, head, items]) => {
      circle(s, img, 0.5, yy);
      s.addText(head, { x: 1.08, y: yy + 0.06, w: 4.2, h: 0.34, fontFace: BODY, fontSize: 14, bold: true, color: C.navy, margin: 0, isTextBox: true });
      s.addText(items.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < items.length - 1 } })), {
        x: 1.08, y: yy + 0.45, w: 4.3, h: items.length * 0.36, fontFace: BODY, fontSize: 11, color: C.ink, paraSpaceAfter: 3, margin: 0, valign: "top", isTextBox: true,
      });
      yy += 0.45 + items.length * 0.36 + 0.3;
    });

    // right card: measurable triggers
    const cx = 5.7, cy = 1.1, cw = 3.8, chh = 3.85;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx, y: cy, w: cw, h: chh, fill: { color: C.tint }, line: { color: C.tint }, rectRadius: 0.08 });
    circle(s, ic.change, cx + 0.22, cy + 0.2, 0.46, C.white);
    s.addText("What would change my view", { x: cx + 0.8, y: cy + 0.26, w: cw - 1.0, h: 0.34, fontFace: BODY, fontSize: 14, bold: true, color: C.navy, margin: 0, isTextBox: true });
    const triggers = [
      ["Price. ", `A fall toward ${N.t1Lo}–${N.t1Hi.slice(1)}, the comps range anchored on Walmart and BJ's.`],
      ["Growth runway. ", `Evidence Costco can compound ~8% for decades: at 8% it needs ${N.dur8} years after FY2029 to justify ${N.price}.`],
      ["Discount rate. ", `A lasting fall in rates or risk premia. Near the base, 0.5pp off WACC adds ~$${Math.round(wg[lowerRow]["3.0%"] - base)}/share (more as WACC falls: 6.0% gives ~$596); the price needs ${N.wImp}.`],
      ["Not enough on its own: ", `a strong quarter. Operating upside moves value to ${N.opHi} at most.`],
    ];
    s.addText(triggers.flatMap(([b, t], j) => [
      { text: b, options: { bold: true, color: C.navy } },
      { text: t, options: { color: C.ink, breakLine: j < triggers.length - 1 } },
    ]), { x: cx + 0.25, y: cy + 0.82, w: cw - 0.5, h: chh - 1.0, fontFace: BODY, fontSize: 12, paraSpaceAfter: 9, margin: 0, valign: "top", isTextBox: true });

    footer(s, "model sensitivity and reverse-DCF tables; Costco 10-K FY2024.");
    pageNo(s, 4);
    s.addNotes("The main risk to this view is that the market is right to use a very low discount rate or to expect decades of high growth. " +
      `The triggers are measurable: price, evidence of a long growth runway, or a lasting fall in the cost of capital. A single strong quarter would not change the conclusion, because operating sensitivities only reach ${N.opHi}.`);
  }

  await pres.writeFile({ fileName: OUT });
  console.log("wrote", path.relative(ROOT, OUT));
}

main().catch((e) => { console.error(e); process.exit(1); });
