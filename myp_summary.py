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

# v5.11.1 (2026-06-09): reaproveita os helpers de URL do scanner pra montar o
# link DIRETO do TCGplayer (via redirect pokemontcg.io) na tabela de ENTREGA.
# Mesma lógica do XLSX (generate_xlsx) — direct link quando a edição é mapeada
# e o collector# está in-range; senão cai pra busca-por-nome. Import tolerante:
# se o módulo do scanner não estiver importável (ex.: teste isolado), o link
# TCG some mas o resto da tabela segue.
try:
    from myp_arbitrage_scanner import tcg_direct_url, tcg_search_url
except Exception:  # pragma: no cover - fallback defensivo
    def tcg_direct_url(name, edition, oversized_collector_risk=False):
        return None

    def tcg_search_url(name):
        return None


def fmt_usd(v) -> str:
    """Formata valor USD pra display (US$1,234.56). '—' se ausente."""
    if v is None:
        return "—"
    try:
        return f"US${float(v):,.2f}"
    except (ValueError, TypeError):
        return "—"


def split_card_name(name: str | None) -> tuple[str, str]:
    """Separa 'Pikachu (173/165)' → ('Pikachu', '173/165').

    Retorna (nome_base, numero). Numero vazio se o nome não embute (NNN/MMM).
    A coluna `Carta` da entrega junta como 'Pikachu 173/165' (sem duplicar o
    número quando já está no nome)."""
    if not name:
        return ("", "")
    import re
    m = re.search(r"\((\d+/\d+)\)\s*$", name)
    if not m:
        return (name.strip(), "")
    base = name[: m.start()].strip()
    return (base, m.group(1))


def carta_label(name: str | None) -> str:
    """Coluna `Carta` = nome + número numa string só ('Pikachu 173/165').

    Se o nome não embute número, retorna só o nome (sem duplicar)."""
    base, num = split_card_name(name)
    if num and num not in base:
        return f"{base} {num}"
    return base or (name or "").strip()


def delivery_links(myp_url: str | None, name: str | None, edition: str | None,
                   oversized: bool = False) -> str:
    """Coluna `Links`: '[oferta](myp_url) · [TCG](tcg_url)'.

    - oferta → página do produto no MYP (validação do preço/seller).
    - TCG → produto/busca TCGplayer (workflow manual de conferir preço NM).
    Emite só os links que existirem; '—' se nenhum."""
    parts = []
    if myp_url:
        parts.append(f"[oferta]({myp_url})")
    tcg = (
        tcg_direct_url(name or "", edition or "", oversized_collector_risk=oversized)
        or tcg_search_url(name or "")
    )
    if tcg:
        parts.append(f"[TCG]({tcg})")
    return " · ".join(parts) if parts else "—"


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


def build_markdown(xlsx: str, output: str, scan_type: str,
                   run_id: str = "",
                   repo: str = "matheuscllm-lgtm/myp-arbitrage-scanner") -> int:
    """Gera o markdown de ENTREGA a partir do XLSX consolidado.

    Extraído do antigo main() (v5.11.1) pra ser testável sem argv/subprocess.
    `scan_type` ∈ {"daily","weekly"}."""
    # nomes legados usados no corpo (mantidos pra diff mínimo)
    class _A:  # namespace leve, evita reescrever args.* abaixo
        pass
    args = _A()
    args.xlsx = xlsx
    args.output = output
    args.type = scan_type
    args.run_id = run_id
    args.repo = repo

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

    # v5.11.1: solta o handle do XLSX assim que a extração termina (Windows
    # segura o arquivo em read_only até fechar — relevante p/ testes/uso in-process).
    wb.close()

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

    # ── Top 50 deals limpos — FORMATO DE ENTREGA (links clicáveis) ──
    # v5.11.1 (2026-06-09): formato aprovado pelo operador (espelha a entrega do
    # scanner COMC). Colunas:
    #   # | Margem % | MYP R$ | TCG US$ | Dif | Carta | Set | Raridade | Cond | Qtd | Links
    # - Carta = nome + número numa coluna só ('Pikachu 173/165'), sem duplicar.
    # - TCG US$ = preço REAL do TCGplayer em USD (pokemontcg.io). '—' onde só
    #   houve fallback .estat-tcg (sem USD real).
    # - Dif = lucro bruto em R$ (Diff (R$) = TCG R$ − MYP R$); margem segue BRUTA.
    # - Cond = NM (invariante NM-only).
    # - Qtd = nº de ofertas EN-NM (NM Sellers) — quantos lotes o operador pode
    #   comprar; o scanner não captura estoque por seller, então é a contagem.
    # - Links = [oferta](MYP) · [TCG](TCGplayer) — clicáveis; TCG p/ validação NM.
    lines.append("## 🟢 Top 50 deals limpos (sem flag SIR/HR/SAR)")
    lines.append("")
    if not deals_clean:
        lines.append("> Nenhum deal limpo nesta run.")
    else:
        lines.append("| # | Margem % | MYP R$ | TCG US$ | Dif | Carta | Set | Raridade | Cond | Qtd | Links |")
        lines.append("|---|---:|---:|---:|---:|---|---|---|---|---:|---|")
        for i, c in enumerate(deals_clean[:50], 1):
            name = c.get("Card Name")
            carta = carta_label(name)
            ed = (c.get("Edition") or "").strip()
            rarity = (c.get("Rarity") or "").strip() or "—"
            myp = fmt_brl(c.get("MYP EN NM (R$)"))
            tcg_usd = fmt_usd(c.get("TCG US$"))
            margin = fmt_pct(c.get("Margin %"))
            diff = fmt_brl(c.get("Diff (R$)"))
            qty = c.get("NM Sellers") or 0
            links = delivery_links(
                c.get("URL"), name, ed,
                oversized=bool(c.get("⚠️ COLLECTOR#")),
            )
            lines.append(
                f"| {i} | **{margin}** | {myp} | {tcg_usd} | {diff} | "
                f"{carta} | {ed} | {rarity} | NM | {qty} | {links} |"
            )
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
    return build_markdown(
        xlsx=args.xlsx, output=args.output, scan_type=args.type,
        run_id=args.run_id, repo=args.repo,
    )


if __name__ == "__main__":
    sys.exit(main())
