"""Revalidate deals em XLSX existente fazendo re-scrape leve.

Pra cada deal no sheet '🔥 Deals' do XLSX input:
  1. Scrape URL do produto MYP
  2. Extrai `.estat-tcg` (TCG declarado) E `.estatistica-ultimo` (última venda real)
  3. Calcula ratio. Se > 10x = tcg_suspect.
  4. Gera novo XLSX com 3 sheets:
     - 🔥 Deals Limpos (sobreviventes)
     - 🚨 TCG Suspect (filtrados por sanity check)
     - All EN Cards (cópia inalterada)

Uso:
    python scripts/revalidate_deals.py <input.xlsx> [--output <output.xlsx>]
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from pathlib import Path

if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from bs4 import BeautifulSoup

from myp_arbitrage_scanner import MYPScraper, TCG_SUSPECT_RATIO_THRESHOLD

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)

# v5.8 (2026-05-16): single source of truth, importa do scanner
SUSPECT_RATIO = TCG_SUSPECT_RATIO_THRESHOLD


def parse_brl(text) -> float | None:
    """v5.8.4: DRY — delegate to MYPScraper._parse_brl (single source of
    truth). Previously this script duplicated the parser; reviewer flagged
    drift risk (v5.8.2 BR/US leak fix had to be reapplied here separately).
    """
    return MYPScraper._parse_brl(text)


def revalidate_url(scraper: MYPScraper, url: str) -> dict:
    """Re-scrape URL e retorna {tcg_declared, last_sale, ratio, suspect}."""
    try:
        r = scraper.session.get(url, timeout=30)
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}"}
        soup = BeautifulSoup(r.text, "lxml")

        tcg_decl = None
        tcg_el = soup.select_one(".estat-tcg")
        if tcg_el:
            matches = re.findall(r'R\$\s*[\d.,]+', tcg_el.get_text())
            if matches:
                tcg_decl = parse_brl(matches[-1])

        last_sale = None
        ls_el = soup.select_one(".estatistica-ultimo")
        if ls_el:
            matches = re.findall(r'R\$\s*[\d.,]+', ls_el.get_text())
            if matches:
                last_sale = parse_brl(matches[-1])

        ratio = None
        suspect = False
        if tcg_decl and last_sale and last_sale > 0:
            ratio = tcg_decl / last_sale
            suspect = ratio > SUSPECT_RATIO

        return {
            "tcg_declared": tcg_decl,
            "last_sale": last_sale,
            "ratio": ratio,
            "suspect": suspect,
        }
    except Exception as e:
        return {"error": str(e)}


def revalidate(input_xlsx: Path, output_xlsx: Path, delay: float = 1.5):
    log.info(f"Loading: {input_xlsx}")
    wb_in = load_workbook(input_xlsx, data_only=True)

    deals_ws = wb_in["🔥 Deals"]
    headers = [c.value for c in next(deals_ws.iter_rows(min_row=1, max_row=1))]
    url_idx = headers.index("URL")
    name_idx = headers.index("Card Name")

    rows = list(deals_ws.iter_rows(min_row=2, values_only=True))
    log.info(f"Total deals to revalidate: {len(rows)}")

    scraper = MYPScraper()

    clean = []
    suspect = []

    for i, row in enumerate(rows, 1):
        if not row or not row[name_idx]:
            continue
        url = row[url_idx]
        name = row[name_idx]
        if not url:
            clean.append(row)
            continue

        result = revalidate_url(scraper, url)
        if "error" in result:
            log.warning(f"  [{i}/{len(rows)}] {name[:50]}: error={result['error']} — keeping in clean")
            clean.append(row)
            continue

        if result["suspect"]:
            log.warning(
                f"  [{i}/{len(rows)}] 🚨 SUSPECT {name[:40]} | "
                f"TCG decl={result['tcg_declared']} vs last sale={result['last_sale']} "
                f"(ratio={result['ratio']:.1f}x)"
            )
            suspect.append((row, result))
        else:
            ratio_str = f"{result['ratio']:.1f}x" if result['ratio'] else "n/a"
            log.info(f"  [{i}/{len(rows)}] OK {name[:50]} (ratio={ratio_str})")
            clean.append(row)

        time.sleep(delay)

    log.info(f"\n=== Resultado: {len(clean)} limpos | {len(suspect)} suspeitos ===\n")

    # Write output XLSX
    wb_out = Workbook()
    wb_out.remove(wb_out.active)

    # Clean Deals
    ws_clean = wb_out.create_sheet("🔥 Deals Limpos")
    ws_clean.append(headers)
    for r in clean:
        ws_clean.append(r)
    _style_header(ws_clean, headers, fill="C6EFCE")

    # Suspect Deals
    ws_susp = wb_out.create_sheet("🚨 TCG Suspect")
    ws_susp.append(headers + ["TCG Decl Re-check", "Last Sale", "Ratio"])
    for r, result in suspect:
        ws_susp.append(list(r) + [result["tcg_declared"], result["last_sale"], result["ratio"]])
    _style_header(ws_susp, headers + ["TCG Decl Re-check", "Last Sale", "Ratio"], fill="FFC7CE")

    # Copy All EN Cards
    if "All EN Cards" in wb_in.sheetnames:
        src = wb_in["All EN Cards"]
        ws_all = wb_out.create_sheet("All EN Cards")
        for row in src.iter_rows(values_only=True):
            ws_all.append(row)
        _style_header(ws_all, headers, fill="DCE6F1")

    # Summary
    ws_sum = wb_out.create_sheet("Summary")
    ws_sum.append(["Metric", "Value"])
    ws_sum.append(["Revalidation timestamp", time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())])
    ws_sum.append(["Input file", str(input_xlsx.name)])
    ws_sum.append(["Total deals revalidated", len(rows)])
    ws_sum.append(["Deals limpos", len(clean)])
    ws_sum.append(["Deals suspeitos (filtrados)", len(suspect)])
    ws_sum.append(["Suspect ratio threshold", f">{SUSPECT_RATIO}x"])

    wb_out.save(output_xlsx)
    log.info(f"OK output saved: {output_xlsx}")


def _style_header(ws, headers, fill="4472C4"):
    for col_idx, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col_idx, value=h)
        c.font = Font(bold=True)
        c.fill = PatternFill(start_color=fill, end_color=fill, fill_type="solid")
        c.alignment = Alignment(horizontal="center")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--delay", type=float, default=1.5)
    args = p.parse_args()

    if args.output is None:
        stem = args.input.stem
        args.output = args.input.parent / f"{stem}_REVALIDATED.xlsx"

    revalidate(args.input, args.output, args.delay)


if __name__ == "__main__":
    main()
