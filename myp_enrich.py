#!/usr/bin/env python3
"""Enriquece um XLSX de catálogo MYP com preço TCGplayer REAL (pokemontcg.io).

POR QUE existe (achado 2026-06-20): os runners do GitHub Actions **não
alcançam** `api.pokemontcg.io` (o Cloudflare da API bloqueia/challenge os IPs
de datacenter do GitHub/Azure → toda chamada falha → o scanner cai no fallback
`.estat-tcg`). Resultado: o `weekly-scan.yml` produz cobertura completa do
catálogo, mas com preço **fallback** (margens infladas/artefato), mesmo com o
secret `POKEMONTCG_API_KEY` setado. Confirmado: 0/1326 preços reais no workflow,
e 0 também forçando Python 3.11 — não é key nem versão de Python, é o IP do
runner. Uma máquina comum (PC do operador, container Claude Code) **alcança** a
API normalmente.

FLUXO HÍBRIDO (rápido + confiável p/ o catálogo completo):
  1. Rode o workflow `weekly-scan.yml` → XLSX consolidado (cobertura, ~2h, 20
     runners paralelos) — só falta o preço real.
  2. Baixe o artifact e rode ESTE script LOCAL (onde a pokemontcg.io responde):
       python myp_enrich.py myp_arbitrage_<stamp>.xlsx -o enriched.xlsx
  3. Entregue via myp_summary.py (use --real-only p/ um XLSX só com os cards de
     preço real — os de fallback têm margem não-confiável):
       python myp_summary.py enriched_real_only.xlsx --type weekly -o saida.md

NÃO reinventa cálculo: reusa `MYPScraper._real_tcg_brl` + `fetch_usd_brl` +
`generate_xlsx` do scanner, e replica o bloco de atribuição (v5.11, lê o scanner)
preço real → tcg_player_price/tcg_real_usd, limpa o flag `tcg_suspect`, e
recomputa a margem BRUTA pura.

Requer `POKEMONTCG_API_KEY` no ambiente (mesma key do scanner).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from myp_arbitrage_scanner import MYPScraper, fetch_usd_brl, generate_xlsx
from myp_aggregate import load_chunk_cards


def enrich(in_xlsx: str, out_xlsx: str, min_price: float,
           threshold_frac: float, real_only_out: str | None) -> int:
    cards = load_chunk_cards(Path(in_xlsx))
    if not cards:
        print(f"ERRO: 0 cards lidos de {in_xlsx}", file=sys.stderr)
        return 1
    print(f"Lidos {len(cards)} cards de {in_xlsx}")

    s = MYPScraper(min_price=min_price, threshold=threshold_frac)
    if not s.ptcg_api_key:
        print("AVISO: POKEMONTCG_API_KEY ausente — sem key a pokemontcg.io "
              "throttle 429; defina a key p/ enriquecer rápido.", file=sys.stderr)
    s.fx_usd_brl = fetch_usd_brl(s.session)
    if not s.fx_usd_brl:
        print("ERRO: sem câmbio USD→BRL — não dá p/ converter preço real.", file=sys.stderr)
        return 1
    print(f"Câmbio USD→BRL: {s.fx_usd_brl}")

    attempted = enriched = 0
    for i, card in enumerate(cards):
        # Mesmo gate do scanner: só busca real p/ candidatos (EN-NM ≥ min_price).
        if card.myp_lowest_en_nm and card.myp_lowest_en_nm >= min_price:
            attempted += 1
            real_brl = s._real_tcg_brl(card.name, card.edition)
            if real_brl is not None:
                card.tcg_player_price = real_brl
                card.tcg_real_usd = real_brl / s.fx_usd_brl
                card.tcg_source = "pokemontcg.io"
                if getattr(card, "tcg_suspect", False):
                    card.tcg_suspect = False  # preço agora é real → flag não se aplica
                enriched += 1
        # Margem BRUTA pura recomputada com o preço (real onde houve cobertura).
        if card.myp_lowest_en_nm and card.tcg_player_price and card.myp_lowest_en_nm > 0:
            card.margin_brl = card.tcg_player_price - card.myp_lowest_en_nm
            card.margin_pct = card.margin_brl / card.myp_lowest_en_nm
        if i and i % 200 == 0:
            print(f"  ...{i}/{len(cards)} (attempted={attempted} real={enriched})")

    print(f"Enriquecidos: {enriched} preço real / {attempted} tentados / {len(cards)} cards "
          f"({len(cards) - enriched} ficam em fallback .estat-tcg — sets sem cobertura)")
    generate_xlsx(cards, out_xlsx, threshold_frac)
    print(f"OK enriquecido: {out_xlsx}")

    if real_only_out:
        real = [c for c in cards if getattr(c, "tcg_real_usd", None) not in (None, "", "—")]
        generate_xlsx(real, real_only_out, threshold_frac)
        print(f"OK só-confiáveis ({len(real)} cards com preço real): {real_only_out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="XLSX do catálogo (consolidado do workflow ou chunk)")
    ap.add_argument("-o", "--output", required=True, help="XLSX enriquecido (todos os cards)")
    ap.add_argument("--real-only-out", default=None,
                    help="Opcional: XLSX só com cards de preço REAL (exclui fallback)")
    ap.add_argument("--min-price", type=float, default=80.0,
                    help="Piso EN-NM em R$ p/ buscar preço real (default 80)")
    ap.add_argument("--threshold", type=float, default=0.30,
                    help="Margem como FRAÇÃO p/ formatação do XLSX (default 0.30)")
    args = ap.parse_args()
    return enrich(args.input, args.output, args.min_price, args.threshold, args.real_only_out)


if __name__ == "__main__":
    sys.exit(main())
