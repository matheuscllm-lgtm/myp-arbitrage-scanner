#!/usr/bin/env python3
"""
bench.py — micro-benchmark reprodutível do MYP scanner (loop de otimização).

Faz parte do "loop iterativo de dev" (medir→mudar→verificar→repetir; ver a seção
"Otimizar o scanner" no CLAUDE.md): roda o scanner sobre uma fatia pequena e fixa
e imprime um relatório de UMA TELA, fácil
de comparar antes/depois de uma mudança.

    # baseline (mockado, SEM rede — roda em CI/local sem segredos)
    python bench.py > before.txt
    # ... aplica uma otimização ...
    python bench.py > after.txt
    diff before.txt after.txt

Dois modos:
  • DEFAULT (mockado): substitui só a REDE (`session.get` + câmbio) por fixtures
    determinísticas. Todo o resto roda de verdade — `scrape_product`, `_get`,
    `_real_tcg_brl`, prefill (tcgcsv E pokemontcg), o cache `_ptcg_cache`. O
    fixture agora serve tcgcsv.com TAMBÉM (v5.19.1), então o default
    `--tcg-source auto` exercita a rota REAL do CI/prod (tcgcsv-first): nele
    `tcgcsv_prefill_sets`/`tcg_from_tcgcsv` sobem e `ptcg_calls` fica 0
    (esperado — a pokemontcg.io não é tocada quando o tcgcsv cobre o set).
    Pra medir a rota legada pokemontcg (a métrica `ptcg_calls`/o batch por set),
    passe `--tcg-source pokemontcg`. Os timings (t_http/t_ptcg) ficam perto de 0
    porque a I/O fake é instantânea.

    python bench.py                          # default = rota tcgcsv (CI/prod)
    python bench.py --tcg-source pokemontcg  # rota legada (mede ptcg_calls)
  • --live: roda o scan de verdade contra o site + a fonte escolhida (precisa de
    rede; pokemontcg idealmente com POKEMONTCG_API_KEY). Aí os timings viram
    tempo real.

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


def _ptcg_set_json():
    """Resposta do endpoint de BUSCA por set (v5.12 batch): lista de cards com
    `number` + tcgplayer.prices. Cobre números 1..50 (≥ limit típico do bench),
    então no modo mockado o prefill cobre todos os cards → ptcg_calls cai pra 0."""
    return {
        "data": [
            {"id": f"set-{n}", "number": str(n),
             "tcgplayer": {"prices": {"holofoil": {"market": 40.0}}}}
            for n in range(1, 51)
        ],
        "page": 1, "pageSize": 250, "count": 50, "totalCount": 50,
    }


# ── Fixtures tcgcsv.com (v5.19.1) ───────────────────────────────────────────
# O default do scanner é `--tcg-source auto` = tcgcsv PRIMEIRO (a fonte que o CI
# usa). Sem estes fixtures o mock só servia api.pokemontcg.io, então no modo
# default o prefill tcgcsv falhava (json None) e o bench caía no caminho
# pokemontcg — medindo a rota ERRADA. As edições-fixture mapeiam: Surging
# Sparks→sv8→SSP, Stellar Crown→sv7→SCR (abbreviation casada por
# resolve_tcgcsv_group_id contra estes groups).
_TCGCSV_GROUPS = [
    {"groupId": 1, "name": "SV08: Surging Sparks", "abbreviation": "SSP"},
    {"groupId": 2, "name": "SV07: Stellar Crown", "abbreviation": "SCR"},
]


def _tcgcsv_products_json():
    """/{groupId}/products: productId → extendedData Number ('NNN/MMM'). Cobre
    1..50 (≥ limit do bench) → o prefill tcgcsv cobre todos os cards."""
    return {"results": [
        {"productId": n, "extendedData": [{"name": "Number", "value": f"{n}/191"}]}
        for n in range(1, 51)
    ]}


def _tcgcsv_prices_json():
    """/{groupId}/prices: productId → preço por subtype. market US$40 = MESMO
    valor do fixture pokemontcg, então deals_clean fica idêntico nas 2 rotas."""
    return {"results": [
        {"productId": n, "subTypeName": "Holofoil",
         "marketPrice": 40.0, "midPrice": 40.0}
        for n in range(1, 51)
    ]}


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
        # tcgcsv.com (v5.19.1): a fonte default (auto/tcgcsv). Roteada ANTES do
        # fallthrough de produto pra que o prefill tcgcsv seja exercido no bench.
        if "tcgcsv.com" in url:
            if url.endswith("/groups"):
                return _FakeResp(json_data={"results": list(_TCGCSV_GROUPS)})
            if url.endswith("/products"):
                return _FakeResp(json_data=_tcgcsv_products_json())
            if url.endswith("/prices"):
                return _FakeResp(json_data=_tcgcsv_prices_json())
            return _FakeResp(json_data={"results": []})
        if "api.pokemontcg.io" in url:
            if "q=set.id" in url:           # v5.12: prefill batch por set
                return _FakeResp(json_data=_ptcg_set_json())
            return _FakeResp(json_data=_PTCG_JSON)
        m = _CARD_NUM_RE.search(url)
        num = int(m.group(1)) if m else 1
        return _FakeResp(text=_product_html(num))


def _make_mocked(limit_products: int, tcg_source: str) -> MYPScraper:
    sc = MYPScraper(delay=0.0, min_price=50.0, threshold=0.30, tcg_source=tcg_source)
    sc.session = _FakeSession()
    sc.get_all_editions = lambda: list(_FIXTURE_EDITIONS)
    sc.get_edition_products = lambda url: [f"{url}/card-{n}" for n in range(1, limit_products + 1)]
    return sc


def run_once(args) -> tuple[float, dict]:
    if args.live:
        sc = MYPScraper(delay=args.delay, min_price=args.min_price,
                        threshold=0.30, tcg_source=args.tcg_source)
    else:
        sc = _make_mocked(args.limit_products, args.tcg_source)
        M.fetch_usd_brl = lambda session: 5.0  # câmbio fixo, sem rede

    t0 = time.perf_counter()
    sc.scan(
        edition_filter=args.editions if args.live else None,
        max_products=args.limit_products,
        checkpoint_path=None,  # sem I/O de disco no bench
    )
    wall = time.perf_counter() - t0
    # v5.13: o bench precisa demonstrar a SAÍDA (deals), não só velocidade/calls
    # — senão uma otimização que zerasse os deals passaria no gate. Deal = card
    # com margem ≥ threshold (mesma definição do summary do scanner, L1615).
    # `deals_clean` exclui tcg_suspect (o que de fato entra na sheet 🔥 Deals).
    stats = dict(sc._stats)
    thr = sc.margin_threshold
    stats["deals"] = sum(1 for c in sc.cards if c.margin_pct and c.margin_pct >= thr)
    stats["deals_clean"] = sum(1 for c in sc.cards
                               if c.margin_pct and c.margin_pct >= thr and not c.tcg_suspect)
    return wall, stats


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
    p.add_argument("--tcg-source", choices=("auto", "tcgcsv", "pokemontcg"), default="auto",
                   help="Fonte de preço a medir. 'auto'(default)/'tcgcsv' = rota "
                        "tcgcsv-first (a do CI/prod; veja tcgcsv_prefill_sets). "
                        "'pokemontcg' = rota legada api.pokemontcg.io (veja "
                        "ptcg_calls/ptcg_prefill_calls).")
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
        # SAÍDA (o que importa): uma otimização só vale se os deals sobrevivem.
        ("deals (margem≥thr)", f"{stats.get('deals', 0):8d}"),
        ("deals_clean", f"{stats.get('deals_clean', 0):8d}"),
        ("pages_fetched", f"{stats.get('pages_fetched', 0):8d}"),
        ("ptcg_calls", f"{stats.get('ptcg_calls', 0):8d}"),
        ("ptcg_prefill_calls", f"{stats.get('ptcg_prefill_calls', 0):8d}"),
        # v5.19.1: rota tcgcsv (default auto/tcgcsv = a do CI). tcgcsv_prefill_sets
        # = sets pré-carregados via tcgcsv; tcg_from_tcgcsv = cards precificados
        # por ela. No default agora estes sobem e ptcg_calls fica 0 (esperado).
        ("tcgcsv_prefill_sets", f"{stats.get('tcgcsv_prefill_sets', 0):8d}"),
        ("tcg_from_tcgcsv", f"{stats.get('tcg_from_tcgcsv', 0):8d}"),
        ("t_http_total_s", f"{stats.get('t_http_total', 0.0):8.2f}"),
        ("t_ptcg_total_s", f"{stats.get('t_ptcg_total', 0.0):8.2f}"),
        ("t_editions_total_s", f"{stats.get('t_editions_total', 0.0):8.2f}"),
        ("en_found", f"{stats.get('en_found', 0):8d}"),
        ("tcg_from_real", f"{stats.get('tcg_from_real', 0):8d}"),
        ("tcg_from_myp_fallback", f"{stats.get('tcg_from_myp_fallback', 0):8d}"),
        # v5.13 (Iteração #2): atribuição de cobertura do fallback (raiz dos FP).
        # Some os 4 = tcg_from_myp_fallback. No mockado fica ~0 (mock cobre tudo);
        # é em --live que o balde fixável aparece.
        ("  fb_no_fx", f"{stats.get('fallback_no_fx', 0):8d}"),
        ("  fb_unmapped_set", f"{stats.get('fallback_unmapped_set', 0):8d}"),
        ("  fb_no_collector_num", f"{stats.get('fallback_no_collector_num', 0):8d}"),
        ("  fb_no_coverage", f"{stats.get('fallback_no_coverage', 0):8d}"),
    ]
    print("══ MYP bench ══")
    print(f"modo: {mode}")
    print(f"limit_products/edição: {args.limit_products} | repeat: {args.repeat}")
    print("─" * 34)
    for label, val in rows:
        print(f"{label:<22}{val}")


if __name__ == "__main__":
    main()
