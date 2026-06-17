#!/usr/bin/env python3
"""
bench.py — micro-benchmark reprodutível do MYP scanner (loop de otimização).

Faz parte do "loop iterativo de dev" (ver docs/optimization-loop.md): roda o
scanner sobre uma fatia pequena e fixa e imprime um relatório de UMA TELA, fácil
de comparar antes/depois de uma mudança.

    # baseline (mockado, SEM rede — roda em CI/local sem segredos)
    python bench.py > before.txt
    # ... aplica uma otimização ...
    python bench.py > after.txt
    diff before.txt after.txt

Dois modos:
  • DEFAULT (mockado): substitui só a REDE (`session.get` + câmbio) por fixtures
    determinísticas. Todo o resto roda de verdade — `scrape_product`, `_get`,
    `_real_tcg_brl`, `_fetch_ptcg_usd`, o cache `_ptcg_cache`. Logo `ptcg_calls`
    é REAL: conta os round-trips à pokemontcg.io. Essa é a métrica que a
    otimização "batch por set" deve derrubar (de ~O(cards) p/ ~O(sets)). Os
    timings (t_http/t_ptcg) ficam perto de 0 porque a I/O fake é instantânea.
  • --live: roda o scan de verdade contra o site + pokemontcg.io (precisa de
    rede e idealmente POKEMONTCG_API_KEY). Aí os timings viram tempo real.

    python bench.py --live --editions "Surging Sparks" --limit-products 5

Saída vai pro stdout (o summary do próprio scanner é log/stderr e não polui).
"""
import argparse
import logging
import re
import statistics
import time

import myp_arbitrage_scanner as M
from myp_arbitrage_scanner import MYPScraper

# ── Fixtures determinísticas (modo mockado) ─────────────────────────────
# Edições que MAPEIAM pra um setcode pokemontcg.io (senão o preço real nem é
# consultado e ptcg_calls fica 0). Surging Sparks→sv8, Stellar Crown→sv7.
_FIXTURE_EDITIONS = [
    {"title": "Surging Sparks", "url": "https://bench.local/surging-sparks"},
    {"title": "Stellar Crown", "url": "https://bench.local/stellar-crown"},
]
_CARD_NUM_RE = re.compile(r"card-(\d+)")
# JSON pokemontcg.io mínimo que `_fetch_ptcg_usd` sabe parsear (market US$40).
_PTCG_JSON = {"data": {"tcgplayer": {"prices": {"holofoil": {"market": 40.0}}}}}


def _product_html(num: int) -> str:
    """Página de produto sintética: 1 EN-NM ≥ min_price (dispara o preço real),
    número de colecionador único por produto (cids distintos → cache miss →
    1 round-trip pokemontcg.io por card, que é o que o batch vai otimizar)."""
    return (
        f"<html><body><h1>Bench Card ({num:03d}/999)</h1>"
        f'<span class="estat-tcg">TCG Player: R$ 300,00</span>'
        f'<table class="table-striped table-bordered"><tbody>'
        f'<tr><td><span class="flag-icon" title="Inglês"></span></td>'
        f'<td class="estoque-lista-qualidadenome">NM - Quase nova</td>'
        f'<td class="estoque-lista-nomeenfoil">Normal</td>'
        f"<td>R$ 100,00</td></tr>"
        f"</tbody></table></body></html>"
    )


class _FakeResp:
    def __init__(self, *, text="", json_data=None, status=200):
        self.text = text
        self._json = json_data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise M.requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


class _FakeSession:
    """Substitui scraper.session: serve fixtures por URL, zero rede."""

    def __init__(self):
        self.headers = {}

    def get(self, url, **kwargs):
        if "api.pokemontcg.io" in url:
            return _FakeResp(json_data=_PTCG_JSON)
        m = _CARD_NUM_RE.search(url)
        num = int(m.group(1)) if m else 1
        return _FakeResp(text=_product_html(num))


def _make_mocked(limit_products: int) -> MYPScraper:
    sc = MYPScraper(delay=0.0, min_price=50.0, threshold=0.30)
    sc.session = _FakeSession()
    sc.get_all_editions = lambda: list(_FIXTURE_EDITIONS)
    sc.get_edition_products = lambda url: [f"{url}/card-{n}" for n in range(1, limit_products + 1)]
    return sc


def run_once(args) -> tuple[float, dict]:
    if args.live:
        sc = MYPScraper(delay=args.delay, min_price=args.min_price, threshold=0.30)
    else:
        sc = _make_mocked(args.limit_products)
        M.fetch_usd_brl = lambda session: 5.0  # câmbio fixo, sem rede

    t0 = time.perf_counter()
    sc.scan(
        edition_filter=args.editions if args.live else None,
        max_products=args.limit_products,
        checkpoint_path=None,  # sem I/O de disco no bench
    )
    wall = time.perf_counter() - t0
    return wall, dict(sc._stats)


def main():
    p = argparse.ArgumentParser(description="Micro-benchmark do MYP scanner (loop de otimização).")
    p.add_argument("--live", action="store_true",
                   help="Scan real (rede + idealmente POKEMONTCG_API_KEY). Default: mockado, sem rede.")
    p.add_argument("--limit-products", type=int, default=8,
                   help="Produtos por edição (default 8). Mapeia pra --max-products do scanner.")
    p.add_argument("--editions", nargs="+", default=None,
                   help="(só --live) edições a escanear, substring match.")
    p.add_argument("--repeat", type=int, default=1,
                   help="Repetições; reporta a MEDIANA do wall-time (útil pra amortecer jitter no --live).")
    p.add_argument("--delay", type=float, default=1.5, help="(só --live) delay entre requests.")
    p.add_argument("--min-price", type=float, default=50.0, help="(só --live) piso de preço EN.")
    args = p.parse_args()

    # silencia o log verboso do scanner; o relatório do bench é só o stdout abaixo
    logging.disable(logging.WARNING)

    walls, stats = [], {}
    for _ in range(max(1, args.repeat)):
        w, stats = run_once(args)
        walls.append(w)
    wall = statistics.median(walls)

    mode = "LIVE (rede real)" if args.live else "mockado (sem rede; timings ~0, foco em ptcg_calls)"
    rows = [
        ("wall_total_s", f"{wall:8.2f}"),
        ("products_scanned", f"{stats.get('products_scanned', 0):8d}"),
        ("pages_fetched", f"{stats.get('pages_fetched', 0):8d}"),
        ("ptcg_calls", f"{stats.get('ptcg_calls', 0):8d}"),
        ("t_http_total_s", f"{stats.get('t_http_total', 0.0):8.2f}"),
        ("t_ptcg_total_s", f"{stats.get('t_ptcg_total', 0.0):8.2f}"),
        ("t_editions_total_s", f"{stats.get('t_editions_total', 0.0):8.2f}"),
        ("en_found", f"{stats.get('en_found', 0):8d}"),
        ("tcg_from_real", f"{stats.get('tcg_from_real', 0):8d}"),
        ("tcg_from_myp_fallback", f"{stats.get('tcg_from_myp_fallback', 0):8d}"),
    ]
    print("══ MYP bench ══")
    print(f"modo: {mode}")
    print(f"limit_products/edição: {args.limit_products} | repeat: {args.repeat}")
    print("─" * 34)
    for label, val in rows:
        print(f"{label:<22}{val}")


if __name__ == "__main__":
    main()
