"""Drift detection canary pra MYP scanner.

Roda ANTES do scan principal no daily workflow. Usa Firecrawl pra scrape
2 páginas canário e valida que selectors críticos ainda estão presentes.
Se MYP rebrandeu o site ou trocou markup, falha LOUD aqui em vez de
desperdiçar 30min de CI scrappando HTML quebrado.

Canaries:
  1. /pokemon/edicoes — catalog page (CRÍTICO: scanner não inicia sem isso)
     Validação: >= MIN_EDITIONS edition links extraíveis
  2. Stable product page (Mega Dragonite ex 271/217 — ME:AH)
     Validação: seller table + flag-icons + R$ prices

Exit codes:
  0 — ambos canaries OK, scan pode prosseguir
  1 — drift detectado, scan deve abortar
  2 — erro de infra (API key faltando, Firecrawl down, etc.)
"""
from __future__ import annotations

import os
import sys
import json
from typing import Optional

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import requests
from bs4 import BeautifulSoup

FIRECRAWL_API = "https://api.firecrawl.dev/v1/scrape"
TIMEOUT = 60   # firecrawl pode levar até ~30s pra páginas com CF
MIN_EDITIONS = 200   # mesmo floor do scanner v5.4 (catalog sanity)

CANARY_CATALOG = "https://mypcards.com/pokemon/edicoes"
CANARY_PRODUCT = "https://mypcards.com/pokemon/produto/310508/mega-dragonite-ex"


def firecrawl_scrape(url: str, api_key: str) -> Optional[str]:
    """Scrape URL via Firecrawl, retorna HTML ou None se falhar."""
    try:
        r = requests.post(
            FIRECRAWL_API,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"url": url, "formats": ["html"]},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        body = r.json()
        if not body.get("success"):
            print(f"  ❌ Firecrawl returned success=false: {body.get('error', '?')}")
            return None
        return body.get("data", {}).get("html")
    except requests.RequestException as e:
        print(f"  ❌ Firecrawl HTTP error: {e}")
        return None
    except (ValueError, KeyError) as e:
        print(f"  ❌ Firecrawl response parse error: {e}")
        return None


def check_catalog(html: str) -> tuple[bool, str]:
    """Valida catalog page: >= MIN_EDITIONS edition links extraíveis."""
    soup = BeautifulSoup(html, "lxml")

    # Mesmas estratégias do scanner get_all_editions (Strategy 1, 2, 3)
    import re

    links = soup.select("a.edicao-link")
    strategy = 1

    if not links:
        containers = soup.select('[class*="edicao"]')
        for c in containers:
            a = c.select_one('a[href*="/pokemon/"]')
            if a and a not in links:
                links.append(a)
        if links:
            strategy = 2

    if not links:
        exclude = ["produto", "edicoes", "outros", "selados",
                   "acessorios", "deck-lote", "cartas-graduadas",
                   "action-figure", "artigos-geek", "hq-livros",
                   "inscricao", "online", "pokemon?", "#"]
        for a in soup.select('a[href]'):
            href = a.get("href", "")
            if re.match(r'^/pokemon/[a-z0-9][\w-]+$', href):
                if not any(x in href for x in exclude):
                    links.append(a)
        if links:
            strategy = 3

    # Calibração 2026-05-14: page 1 retorna ~48 links consistentemente
    # (catálogo total ~348 dividido em ~7-8 pages). Threshold conservador
    # de 20 pega quebra real (selectors mudaram → 0 ou poucos links) sem
    # gerar falso positivo em scrape saudável.
    n = len(links)
    if n == 0:
        return False, f"Zero edition links extraíveis com strategies 1+2+3 (selectors quebraram completamente)"
    if n < 20:
        return False, f"Só {n} edition links na page 1 (esperado ~48). Strategy {strategy}. Selectors podem estar parcialmente quebrados."
    return True, f"{n} edition links na page 1 via strategy {strategy} (sanity OK)"


def check_product(html: str) -> tuple[bool, str]:
    """Valida product page: seller table + flag-icons + R$ prices."""
    soup = BeautifulSoup(html, "lxml")

    # 1. Seller tables (mesmo selector do scanner scrape_product)
    tables = soup.select("table.table-striped.table-bordered")
    if not tables:
        return False, "Nenhuma seller table com selector 'table.table-striped.table-bordered'. MYP mudou markup."

    # 2. Flag icons (selector usado no scanner pra detectar idioma)
    flags = soup.select("span.flag-icon[title]")
    if not flags:
        return False, f"{len(tables)} seller tables encontradas mas zero 'span.flag-icon[title]'. Idioma detection vai falhar."

    # 3. R$ prices na página
    text = soup.get_text()
    if "R$" not in text:
        return False, "Página produto sem nenhum 'R$' no texto. Pricing parser vai falhar."

    # 4. TCG Player reference (selector .estat-tcg)
    tcg_el = soup.select_one(".estat-tcg")
    if not tcg_el:
        return False, "Sem '.estat-tcg' element — referência TCGplayer ausente, scanner vai pular todos os produtos."

    return True, f"OK: {len(tables)} tables, {len(flags)} flag-icons, .estat-tcg presente"


def main() -> int:
    api_key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        print("ERROR: FIRECRAWL_API_KEY não está no env. Configurar via gh secret set.", file=sys.stderr)
        return 2

    print(f"=== MYP Drift Check ===")
    print(f"Canary 1: catalog page ({CANARY_CATALOG})")
    catalog_html = firecrawl_scrape(CANARY_CATALOG, api_key)
    if catalog_html is None:
        print("  ❌ Firecrawl falhou no catalog — não dá pra validar drift")
        return 2
    catalog_ok, catalog_msg = check_catalog(catalog_html)
    print(f"  {'✅' if catalog_ok else '❌'} {catalog_msg}")

    print(f"\nCanary 2: product page ({CANARY_PRODUCT})")
    product_html = firecrawl_scrape(CANARY_PRODUCT, api_key)
    if product_html is None:
        print("  ❌ Firecrawl falhou no product — não dá pra validar drift")
        return 2
    product_ok, product_msg = check_product(product_html)
    print(f"  {'✅' if product_ok else '❌'} {product_msg}")

    print()
    if catalog_ok and product_ok:
        print("✅ DRIFT CHECK PASSED — selectors do MYP intactos. Scan pode prosseguir.")
        return 0
    else:
        print("❌ DRIFT CHECK FAILED — MYP mudou markup. Scan ABORTADO pra não desperdiçar CI minutes.")
        print("   Próximo passo: rodar local com --max-editions 1 + inspecionar .debug/debug_1.html")
        print("   Atualizar selectors no scanner se necessário.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
