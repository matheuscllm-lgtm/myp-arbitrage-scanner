"""Gera markdown summary a partir de XLSX consolidado do MYP scanner.

Output otimizado pra leitura rápida em GitHub UI (renderiza markdown nativo)
e em Obsidian (frontmatter + tags + tabela). Foca em:
  - Top 10 deals limpos (sem flag SIR/HR/SAR)
  - Top deals com flag SIR (sinaliza pra validação manual)
  - Stats do scan (editions, EN cards, deals encontrados)

Uso:
    python myp_summary.py path/to/myp_arbitrage.xlsx \\
        --output results/daily-2026-05-15.md \\
        --type daily
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from openpyxl import load_workbook


def is_supranumerary(name: str | None) -> bool:
    """Detecta se card_num > set_total no nome '(N/M)'."""
    import re
    if not name:
        return False
    m = re.search(r"\((\d+)/(\d+)\)", name)
    if not m:
        return False
    try:
        return int(m.group(1)) > int(m.group(2))
    except (ValueError, TypeError):
        return False


def fmt_brl(v) -> str:
    """Formata valor BRL pra display."""
    if v is None:
        return "—"
    try:
        return f"R${float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "—"


def fmt_pct(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v) * 100:.1f}%"
    except (ValueError, TypeError):
        return "—"


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera markdown summary do scan MYP")
    parser.add_argument("xlsx", help="Caminho do XLSX consolidado")
    parser.add_argument("-o", "--output", required=True, help="Caminho do .md de saída")
    parser.add_argument("--type", choices=["daily", "weekly"], required=True,
                        help="Tipo do scan (afeta título + tags)")
    parser.add_argument("--run-id", default="",
                        help="GH Actions run ID (link no markdown)")
    parser.add_argument("--repo", default="matheuscllm-lgtm/myp-arbitrage-scanner",
                        help="Repo GH pra link do artifact")
    args = parser.parse_args()

    xlsx_path = Path(args.xlsx)
    if not xlsx_path.exists():
        print(f"ERROR: XLSX não encontrado: {xlsx_path}", file=sys.stderr)
        return 1

    wb = load_workbook(xlsx_path, read_only=True, data_only=True)

    # Stats do Summary sheet
    summary_data = {}
    if "Summary" in wb.sheetnames:
        for row in wb["Summary"].iter_rows(values_only=True):
            if row[0] and row[1] is not None:
                summary_data[str(row[0]).strip().rstrip(":")] = row[1]

    # All EN Cards (fonte mais rica que só Deals)
    all_cards = []
    if "All EN Cards" in wb.sheetnames:
        ws = wb["All EN Cards"]
        rows = list(ws.iter_rows(values_only=True))
        if rows:
            headers = list(rows[0])
            for r in rows[1:]:
                rec = dict(zip(headers, r))
                if rec.get("Card Name"):
                    all_cards.append(rec)

    deals = [c for c in all_cards if c.get("Margin %") and c["Margin %"] >= 0.25]
    deals_sorted = sorted(deals, key=lambda c: c.get("Margin %") or 0, reverse=True)

    # v5.8 (2026-05-16): Top 15 "limpos" exclui agora 3 buckets: supranumerários,
    # truncation-risk E tcg_suspect (Jirachi PR-SM_SM161 caso). Antes Jirachi
    # aparecia como #1 em latest-weekly.md mesmo com TCG inflado 75x.
    def _is_suspect(c) -> bool:
        return bool(c.get("⚠️ TCG Suspect"))

    deals_clean = [
        c for c in deals_sorted
        if not is_supranumerary(c.get("Card Name")) and not _is_suspect(c)
    ]
    deals_supranum = [c for c in deals_sorted if is_supranumerary(c.get("Card Name"))]
    deals_suspect = [c for c in deals_sorted if _is_suspect(c)]

    truncations = [c for c in all_cards if c.get("⚠️ EN Trunc")]

    today = datetime.utcnow().strftime("%Y-%m-%d")
    scan_type_label = "Daily Quick" if args.type == "daily" else "Weekly Full"

    # ── Build markdown ──
    lines = []
    lines.append(f"---")
    lines.append(f"tags: [tcg, scanner, myp, arbitrage, scan-{args.type}]")
    lines.append(f"date: {today}")
    lines.append(f"type: {args.type}")
    lines.append(f"source: GH Actions run {args.run_id}" if args.run_id else "source: local scan")
    lines.append(f"---")
    lines.append("")
    lines.append(f"# MYP Scan {scan_type_label} — {today}")
    lines.append("")

    # Stats line
    total = summary_data.get("Total EN Cards", len(all_cards))
    deals_n = summary_data.get("Deals Found (clean)", summary_data.get("Deals Found", len(deals)))
    threshold = summary_data.get("Margin Threshold", "25%")
    lines.append(f"**Cards EN escaneados:** {total} | **Deals (≥{threshold}):** {deals_n} | "
                 f"**Limpos:** {len(deals_clean)} | "
                 f"**🚨 TCG suspects:** {len(deals_suspect)} | "
                 f"**Truncation:** {len(truncations)}")
    lines.append("")

    if args.run_id:
        lines.append(f"**Artifact XLSX:** [`myp-{args.type}-consolidated-{args.run_id}`](https://github.com/{args.repo}/actions/runs/{args.run_id})")
        lines.append("")

    # ── Top 50 deals limpos ──
    lines.append("## 🟢 Top 50 deals limpos (sem flag SIR/HR/SAR)")
    lines.append("")
    if not deals_clean:
        lines.append("> Nenhum deal limpo nesta run.")
    else:
        lines.append("| # | Carta | Edição | MYP R$ | TCG R$ | Margem | Lucro R$ |")
        lines.append("|---|---|---|---:|---:|---:|---:|")
        for i, c in enumerate(deals_clean[:50], 1):
            name = (c.get("Card Name") or "")[:55]
            ed = (c.get("Edition") or "")[:30]
            myp = fmt_brl(c.get("MYP EN NM (R$)"))
            tcg = fmt_brl(c.get("TCG Player (R$)"))
            margin = fmt_pct(c.get("Margin %"))
            diff = fmt_brl(c.get("Diff (R$)"))
            lines.append(f"| {i} | {name} | {ed} | {myp} | {tcg} | **{margin}** | {diff} |")
    lines.append("")

    # ── Deals com flag SIR (alto risco) ──
    lines.append("## ⚠️ Deals com flag supranumerário (validar manualmente)")
    lines.append("")
    lines.append("> Cards com `card_num > set_total` aparecem como rarity='Comum' no MYP mas o "
                 "TCG pode estar refletindo a variant secret/illustration rare. Margens absurdas "
                 "(>200%) são quase certamente artefato. Não confiar sem validar.")
    lines.append("")
    if not deals_supranum:
        lines.append("> Nenhum deal com flag supranumerário nesta run.")
    else:
        lines.append("| # | Carta | Edição | MYP R$ | TCG R$ | Margem (suspeita) |")
        lines.append("|---|---|---|---:|---:|---:|")
        for i, c in enumerate(deals_supranum[:50], 1):
            name = (c.get("Card Name") or "")[:55]
            ed = (c.get("Edition") or "")[:30]
            myp = fmt_brl(c.get("MYP EN NM (R$)"))
            tcg = fmt_brl(c.get("TCG Player (R$)"))
            margin = fmt_pct(c.get("Margin %"))
            lines.append(f"| {i} | {name} | {ed} | {myp} | {tcg} | {margin} |")
    lines.append("")

    # ── TCG Suspect (v5.8 — MYP infla .estat-tcg) ──
    if deals_suspect:
        lines.append("## 🚨 TCG Suspect (campo .estat-tcg inflado pelo MYP)")
        lines.append("")
        lines.append("> Cards onde TCG declarado pelo MYP é >10x a última venda real "
                     "do próprio MYP. Provável bug do `.estat-tcg`. Caso Jirachi "
                     "PR-SM_SM161: MYP declarava R$1499 vs última venda R$19,99 (75x). "
                     "Margens absurdas aqui são quase certamente artefato. **Já excluídos "
                     "do Top 15 limpos**, listados aqui pra auditoria.")
        lines.append("")
        lines.append("| # | Carta | Edição | MYP R$ | TCG decl R$ | Última venda R$ | Margem (fake) |")
        lines.append("|---|---|---|---:|---:|---:|---:|")
        for i, c in enumerate(deals_suspect[:50], 1):
            name = (c.get("Card Name") or "")[:55]
            ed = (c.get("Edition") or "")[:30]
            myp = fmt_brl(c.get("MYP EN NM (R$)"))
            tcg = fmt_brl(c.get("TCG Player (R$)"))
            last = fmt_brl(c.get("MYP Last Sale (R$)"))
            margin = fmt_pct(c.get("Margin %"))
            lines.append(f"| {i} | {name} | {ed} | {myp} | {tcg} | {last} | {margin} |")
        lines.append("")

    # ── Truncation risks ──
    if truncations:
        lines.append("## 🚨 EN truncation risk (preço pode estar superestimado)")
        lines.append("")
        lines.append("> Seller table do MYP bateu cap com zero EN visível — listing real "
                     "pode ser mais barato. Validar via página direta.")
        lines.append("")
        lines.append("| Carta | Edição | MYP R$ reportado | TCG R$ |")
        lines.append("|---|---|---:|---:|")
        for c in truncations[:50]:
            name = (c.get("Card Name") or "")[:55]
            ed = (c.get("Edition") or "")[:30]
            myp = fmt_brl(c.get("MYP EN NM (R$)"))
            tcg = fmt_brl(c.get("TCG Player (R$)"))
            lines.append(f"| {name} | {ed} | {myp} | {tcg} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*Gerado em {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} via "
                 f"`myp_summary.py` (single source: XLSX consolidado).*")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"OK markdown summary: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
