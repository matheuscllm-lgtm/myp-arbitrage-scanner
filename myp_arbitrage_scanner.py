#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║         MYP Cards Arbitrage Scanner — Pokémon TCG Singles          ║
║                                                                      ║
║  Compara preços de singles (EN) no mypcards.com vs TCG Player.     ║
║  Gera planilha .xlsx com alertas de arbitragem (margem >= 25%).    ║
╚══════════════════════════════════════════════════════════════════════╝

Uso:
    python myp_arbitrage_scanner.py                          # Scan completo
    python myp_arbitrage_scanner.py --max-editions 5         # Apenas 5 edições
    python myp_arbitrage_scanner.py --threshold 40           # Margem mínima 40%
    python myp_arbitrage_scanner.py --delay 2.0              # 2s entre requests

Requisitos:
    pip install cloudscraper beautifulsoup4 openpyxl lxml

Autor: Matheus Chillemi / Claude
Data: 2026-04-15 (v5) | 2026-05-12 (v5.1 → v5.3)
Versão: v5.3

Changelog v5.1 (2026-05-12 — auditoria C/H/M, mesma metodologia do CT scanner):
  - C1: --threshold < 1.0 auto-converte com warning (UX guard contra trap
    inverso ao CT scanner — MYP usa percent integer, CT usa fração)
  - H3: detecção heurística SIR/HR/SAR — warning quando rarity="Comum" mas
    TCG price alto (>R$200). Reduz falso positivo documentado em memória.
  - M1: HTTP retry com backoff (3 tentativas, 2s→4s) em transient errors
  - M4: debug_*.html agora salvo em subpasta .debug/ do script,
    não polui CWD
  - M5: novos stat counters (skipped_no_tcg, skipped_no_en_sellers,
    skipped_low_price) pra auditoria do funnel

Changelog v5.2 (2026-05-12):
  - Default --threshold de 35 → 25 (mais discovery, menos filtragem)
  - Nova sheet "🏆 Top 50 Margin" no xlsx: cards ordenados por margem
    decrescente sem filtro, pra inspeção visual chase-card

Changelog v5.3 (2026-05-12 — após caso Psyduck/bartsimpson):
  - T1: novo campo CardData.en_truncation_risk; parser itera por seller table
    individualmente (Tabela 0=lojistas/15-cap, Tabela 1=marketplace/20-cap).
    Heurística refinada: dispara só quando uma tabela está no cap (≥15 rows),
    com zero EN visível, E max_price visível < lowest_en reportado (= hidden
    listings podem ser EN mais baratos que o reportado). Evita false alarm
    quando max visível já está acima do lowest_en (hidden não pode quebrar).
  - H3 refinada: agora também exige card_num > set_total quando o sufixo
    (X/Y) é extraível do nome — evita falso alarm em commons in-set caros.
  - Nova sheet "🚨 Validate Manually" no xlsx: lista os cards com
    en_truncation_risk pra punch-list de validação manual.
  - Nova coluna "⚠️ EN Trunc" nas sheets de cards.
  - Novo stat counter en_truncation_risks no summary final.
  - Bug fix: pricing promocional. Rows com "R$ X (riscado) R$ Y" usavam X
    (preço antigo, mais caro) via re.search; agora re.findall + [-1] pega
    Y (preço ativo). Caso: MatchampTCG Psyduck "R$ 275,00 R$ 220,00" lido
    como R$275 quando deveria ser R$220.
"""

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False
    import requests

from bs4 import BeautifulSoup
import re
import time
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════
BASE_URL = "https://mypcards.com"
MARGIN_THRESHOLD = 0.25          # 25% margem mínima para alerta
MIN_PRICE_BRL = 80.0             # preço mínimo EN em R$ (ignora cartas baratas)
REQUEST_DELAY = 1.5              # segundos entre requests
MAX_PAGES_PER_EDITION = 30       # max páginas por edição
TIMEOUT = 20                     # timeout HTTP em segundos
HTTP_MAX_RETRIES = 3             # M1 fix: retries em transient errors
DEBUG_DIR = Path(__file__).resolve().parent / ".debug"   # M4 fix: subpasta dedicada
SUPRANUMERARY_PRICE_THRESHOLD = 200.0  # H3 fix: TCG R$ acima disso + rarity="Comum" = SIR/HR suspeito

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
}

# Mapeamento de códigos de idioma no produto
LANG_MAP = {
    "eng": "EN", "por": "PT", "jpn": "JP", "ita": "IT",
    "esp": "ES", "fra": "FR", "deu": "DE", "kor": "KR",
    "chi": "CN", "tha": "TH",
}


@dataclass
class CardData:
    name: str = ""
    edition: str = ""
    edition_url: str = ""
    product_url: str = ""
    product_code: str = ""
    language: str = ""
    condition: str = "NM"
    rarity: str = ""
    myp_lowest_en_nm: Optional[float] = None   # menor preço EN NM no MYP
    tcg_player_price: Optional[float] = None    # preço referência TCG Player (EN)
    margin_pct: Optional[float] = None
    margin_brl: Optional[float] = None
    en_nm_sellers: int = 0                      # qtd vendedores EN NM
    en_truncation_risk: bool = False            # 2026-05-12: alguma seller table está no cap (15/20) sem EN visível → EN possivelmente escondido
    last_updated: str = ""


# ══════════════════════════════════════════════════════════════════════
# SCRAPER
# ══════════════════════════════════════════════════════════════════════
class MYPScraper:
    def __init__(self, delay: float = REQUEST_DELAY):
        if HAS_CLOUDSCRAPER:
            self.session = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "desktop": True},
            )
            log.info("Using cloudscraper (CloudFlare bypass enabled)")
        else:
            self.session = requests.Session()
            log.warning("cloudscraper not installed — may get 403 errors!")
            log.warning("Fix: pip install cloudscraper")
        self.session.headers.update(HEADERS)
        self.delay = delay
        self.cards: list[CardData] = []
        self._stats = {
            "pages_fetched": 0, "products_scanned": 0, "en_found": 0,
            # M5 fix: counters por motivo de skip (auditoria do funnel)
            "skipped_no_tcg_price": 0,
            "skipped_no_en_sellers": 0,
            "skipped_low_price": 0,
            "supranumerary_warnings": 0,
            "http_retries": 0,
            # 2026-05-12: contador de risco de truncamento de EN-NM
            # (alguma seller table cheia sem EN visível — caso bartsimpson Psyduck)
            "en_truncation_risks": 0,
        }

    def _get(self, url: str, save_debug: bool = False) -> Optional[BeautifulSoup]:
        """Fetch a page and return parsed soup. M1 fix: retry com backoff."""
        last_err = None
        last_status = ""
        for attempt in range(HTTP_MAX_RETRIES):
            try:
                time.sleep(self.delay)
                resp = self.session.get(url, timeout=TIMEOUT)
                resp.raise_for_status()
                self._stats["pages_fetched"] += 1

                if save_debug:
                    # M4 fix: salva em subpasta .debug/ ao invés do CWD
                    DEBUG_DIR.mkdir(exist_ok=True)
                    debug_file = DEBUG_DIR / f"debug_{self._stats['pages_fetched']}.html"
                    debug_file.write_text(resp.text[:50000], encoding="utf-8")
                    log.info(f"  DEBUG: saved HTML to {debug_file}")

                return BeautifulSoup(resp.text, "lxml")
            except Exception as e:
                last_err = e
                if hasattr(e, 'response') and e.response is not None:
                    last_status = f" (HTTP {e.response.status_code})"
                if attempt < HTTP_MAX_RETRIES - 1:
                    wait = (attempt + 1) * 2  # backoff 2s, 4s
                    self._stats["http_retries"] += 1
                    log.warning(f"Retry {attempt+1}/{HTTP_MAX_RETRIES} for {url}{last_status}: {e}, waiting {wait}s")
                    time.sleep(wait)
                    continue
        log.warning(f"Failed to fetch {url}{last_status} after {HTTP_MAX_RETRIES} attempts: {last_err}")
        return None

    @staticmethod
    def _parse_brl(text: str) -> Optional[float]:
        """Parse Brazilian Real price format: 'R$ 1.900,00' → 1900.0"""
        if not text:
            return None
        text = re.sub(r'[R$\s\xa0]', '', text.strip())
        if not text:
            return None
        # R$ 1.900,00 → remove thousands dot, convert decimal comma
        text = text.replace('.', '').replace(',', '.')
        try:
            val = float(text)
            return val if val > 0 else None
        except (ValueError, TypeError):
            return None

    # ── Step 1: Get all editions ─────────────────────────────────────
    def get_all_editions(self) -> list[dict]:
        """Scrape /pokemon/edicoes for all available editions."""
        editions = []
        page = 1
        while True:
            url = f"{BASE_URL}/pokemon/edicoes?page={page}"
            log.info(f"Fetching editions page {page}...")
            soup = self._get(url, save_debug=(page == 1))
            if not soup:
                break

            # Strategy 1: specific class selectors
            links = soup.select("a.edicao-link")

            # Strategy 2: any link inside an edicao container
            if not links:
                containers = soup.select('[class*="edicao"]')
                for c in containers:
                    a = c.select_one('a[href*="/pokemon/"]')
                    if a and a not in links:
                        links.append(a)

            # Strategy 3: broader pattern matching on all links
            if not links:
                exclude = ["produto", "edicoes", "outros", "selados",
                           "acessorios", "deck-lote", "cartas-graduadas",
                           "action-figure", "artigos-geek", "hq-livros",
                           "inscricao", "online", "pokemon?", "#"]
                for a in soup.select('a[href]'):
                    href = a.get("href", "")
                    # Match pattern: /pokemon/{slug} where slug is a valid edition
                    if re.match(r'^/pokemon/[a-z0-9][\w-]+$', href):
                        if not any(x in href for x in exclude):
                            links.append(a)

            if not links:
                if page == 1:
                    log.warning("No editions found! Check debug_1.html for page structure")
                break

            found_on_page = 0
            seen_urls = {e["url"] for e in editions}
            for link in links:
                href = link.get("href", "")
                if not href:
                    continue

                full_url = f"{BASE_URL}{href}" if href.startswith("/") else href
                if full_url in seen_urls:
                    continue

                # Get title: try parent container, then link text
                title = ""
                for parent_class in ["edicao-card", "edicao-item", "edicao"]:
                    parent = link.find_parent(class_=re.compile(parent_class))
                    if parent:
                        for title_class in ["edicao-titulo", "edicao-header", "titulo", "title"]:
                            t = parent.select_one(f'[class*="{title_class}"]')
                            if t:
                                title = t.get_text(strip=True)
                                break
                        break

                if not title:
                    title = link.get_text(strip=True)[:80]

                if not title or len(title) < 2:
                    continue

                editions.append({
                    "title": title,
                    "url": full_url,
                    "href": href,
                })
                seen_urls.add(full_url)
                found_on_page += 1

            if found_on_page == 0:
                break
            page += 1

        log.info(f"Found {len(editions)} editions")
        return editions

    # ── Step 2: Get product URLs from edition listing ────────────────
    def get_edition_products(self, edition_url: str) -> list[str]:
        """Get all product URLs from an edition listing page."""
        product_urls = []
        seen = set()
        page = 1

        while page <= MAX_PAGES_PER_EDITION:
            url = f"{edition_url}?page={page}"
            soup = self._get(url)
            if not soup:
                break

            links = soup.select('a[href*="/pokemon/produto/"]')
            new_count = 0
            for link in links:
                href = link.get("href", "")
                full_url = f"{BASE_URL}{href}" if href.startswith("/") else href
                if full_url not in seen:
                    seen.add(full_url)
                    product_urls.append(full_url)
                    new_count += 1

            if new_count == 0:
                break
            page += 1

        return product_urls

    # ── Step 3: Scrape product detail page (v2 — per-seller language) ─
    def scrape_product(self, url: str, edition_name: str) -> Optional[CardData]:
        """Extract card data from product page, filtering sellers by language.

        v2 logic: The language is determined per SELLER ROW, not per product.
        Each <tr> in the seller table has an element with title="Português",
        title="Inglês", etc. We extract only EN seller prices and compare
        against the TCG Player reference price (which is always EN).
        """
        soup = self._get(url)
        if not soup:
            return None

        card = CardData()
        card.product_url = url
        card.edition = edition_name
        card.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Name
        h1 = soup.select_one("h1")
        card.name = h1.get_text(strip=True) if h1 else ""

        # Product code
        page_text = soup.get_text()
        code_match = re.search(r'pokemon_[a-z]{2,3}_[\w/]+', page_text)
        card.product_code = code_match.group(0) if code_match else ""

        # ── TCG Player price (always EN reference) ──
        tcg_el = soup.select_one(".estat-tcg")
        if tcg_el:
            card.tcg_player_price = self._parse_brl(tcg_el.get_text())

        # If no TCG Player price, skip this product entirely
        if not card.tcg_player_price:
            self._stats["skipped_no_tcg_price"] += 1
            return None

        # ── Parse seller tables: extract EN sellers only ──
        # 2026-05-12: itera por tabela individualmente (não plano em tr)
        # pra detectar truncamento de EN. Padrão MYP: Tabela 0 (lojistas, cap ~15)
        # + Tabela 1 (marketplace, cap ~20). Quando uma tabela bate o cap E não
        # tem EN visível, há risco de listing EN-NM real mais barato escondido
        # (caso bartsimpson Psyduck R$300 EN sendo truncado por 20 listings PT/JP).
        en_prices = []
        en_sellers = 0
        TABLE_CAP_THRESHOLD = 15   # tabela com >= 15 rows sem EN visível → candidato a truncamento

        seller_tables = soup.select("table.table-striped.table-bordered")
        if not seller_tables:
            # fallback: trata o documento inteiro como uma "tabela"
            seller_tables = [soup]

        # Coleta estatísticas por tabela primeiro; decisão de truncation_risk
        # acontece depois quando temos lowest_en pra comparar.
        per_table_stats = []
        for table in seller_tables:
            rows_in_table = 0
            en_in_table = 0
            max_price_in_table = 0.0  # maior preço VISÍVEL nesta tabela
            for row in table.find_all("tr"):
                row_text = row.get_text()
                if "R$" not in row_text:
                    continue
                rows_in_table += 1

                # Extrai preço (qualquer idioma) pra rastrear max visível.
                # 2026-05-12 v5.3: usa LAST match pra pegar preço atual em rows
                # com promo strikethrough (ex.: "R$ 275,00 R$ 220,00" — R$275
                # é o preço antigo riscado, R$220 é o ativo). re.findall + [-1]
                # corrige bug que inflava preço quando seller estava em promoção.
                price_matches = re.findall(r'R\$\s*[\d.,]+', row_text)
                row_price = self._parse_brl(price_matches[-1]) if price_matches else None
                if row_price and row_price > max_price_in_table:
                    max_price_in_table = row_price

                # Find language from flag-icon span (specific selector)
                lang = None
                flag_el = row.select_one("span.flag-icon[title]")
                if flag_el:
                    lang = flag_el.get("title", "").strip()
                else:
                    # Fallback: check any [title] that matches a known language
                    for el in row.select("[title]"):
                        title_val = el.get("title", "").strip()
                        if title_val in ("Inglês", "Português", "Japonês", "Italiano",
                                         "Espanhol", "Francês", "Alemão", "Coreano",
                                         "English", "Portuguese", "Japanese"):
                            lang = title_val
                            break

                if lang not in ("Inglês", "English"):
                    continue

                # Filter: NM (Near Mint) only — skip Played, Damaged, etc.
                row_upper = row_text.upper()
                is_nm = ("NM" in row_upper or "QUASE NOVA" in row_upper
                         or "NEAR MINT" in row_upper)
                if not is_nm:
                    continue

                # EN + NM seller — preço já extraído acima
                if row_price:
                    en_prices.append(row_price)
                    en_sellers += 1
                    en_in_table += 1

            per_table_stats.append({
                "rows": rows_in_table,
                "en": en_in_table,
                "max_price": max_price_in_table,
            })

        # Heurística de truncamento refinada (v5.3+): só dispara quando há
        # evidência de que listings escondidos PODEM ser mais baratos que o EN
        # reportado. Caso clássico Psyduck: Table 1 com 20 PT/JP, todos abaixo
        # de R$415 (lowest EN reportado de Table 0). Hidden listings (sorted asc
        # acima do visível) podem incluir EN entre [visible_max, lowest_en),
        # exatamente o que aconteceu com bartsimpson R$300. Quando max visível
        # já é >= lowest_en reportado, hidden listings começam acima disso e
        # não podem ser EN mais barato → não flag.
        truncation_risk = False
        lowest_en_seen = min(en_prices) if en_prices else None
        if lowest_en_seen is not None:
            for ts in per_table_stats:
                if (ts["rows"] >= TABLE_CAP_THRESHOLD
                        and ts["en"] == 0
                        and ts["max_price"] > 0
                        and ts["max_price"] < lowest_en_seen):
                    truncation_risk = True
                    break

        # If no EN+NM sellers found, skip
        if not en_prices:
            self._stats["skipped_no_en_sellers"] += 1
            return None

        # Filter: minimum price threshold
        lowest_en = min(en_prices)
        if lowest_en < MIN_PRICE_BRL:
            self._stats["skipped_low_price"] += 1
            return None

        card.language = "EN"
        card.condition = "NM"
        card.myp_lowest_en_nm = min(en_prices)
        card.en_nm_sellers = en_sellers
        card.en_truncation_risk = truncation_risk
        if truncation_risk:
            self._stats["en_truncation_risks"] += 1
            log.warning(
                f"  🚨 EN truncation risk: {card.name} | "
                f"alguma seller table está com ≥{TABLE_CAP_THRESHOLD} rows sem EN visível "
                f"→ lowest EN-NM R${card.myp_lowest_en_nm:.2f} pode estar superestimado. "
                f"Validar manualmente."
            )

        # ── Rarity ──
        rarity_keywords = [
            "Illustration Rare", "Special Art Rare", "Hyper Rare",
            "Ultra Rare", "Secret Rare", "Art Rare", "Double Rare",
            "Rara Hiper", "Rara Ultra", "Rara Secreta", "Rara",
            "Incomum", "Comum",
        ]
        for rarity in rarity_keywords:
            if rarity.lower() in page_text.lower():
                card.rarity = rarity
                break

        # ── Calculate margin: lowest EN NM on MYP vs TCG Player EN ──
        if card.myp_lowest_en_nm and card.tcg_player_price and card.myp_lowest_en_nm > 0:
            card.margin_brl = card.tcg_player_price - card.myp_lowest_en_nm
            card.margin_pct = card.margin_brl / card.myp_lowest_en_nm

        # H3 fix (2026-05-12, refinado 2026-05-12 v5.3): heurística SIR/HR/SAR/IR misclassificado.
        # Bug documentado: cards supranumeráros (#>set_total) aparecem como rarity="Comum"
        # no MYP. Refinamento: extrai card_num/set_total do nome pra evitar falso
        # alarm em commons in-set genuinamente caros (raro mas possível).
        card_num_match = re.search(r"\((\d+)/(\d+)\)", card.name or "")
        is_supranumerary = False
        if card_num_match:
            try:
                num = int(card_num_match.group(1))
                total = int(card_num_match.group(2))
                is_supranumerary = num > total
            except (ValueError, TypeError):
                is_supranumerary = False  # unparseable, default to safe (no alarm)
        else:
            # Sem (X/Y) extraível, mantém heurística antiga como fallback
            is_supranumerary = True

        should_warn = (
            card.rarity in ("Comum", "Incomum")
            and card.tcg_player_price > SUPRANUMERARY_PRICE_THRESHOLD
            and is_supranumerary
        )
        if should_warn:
            self._stats["supranumerary_warnings"] += 1
            log.warning(
                f"  ⚠️ Possível SIR/HR/SAR misclassificado: {card.name} | "
                f"rarity='{card.rarity}' mas TCG R${card.tcg_player_price:.0f} é alto. "
                f"Validar manualmente antes de operar."
            )

        return card

    # ── Main scan ────────────────────────────────────────────────────
    def scan(self, max_editions: int = 0, max_products: int = 0,
             edition_filter: list[str] = None) -> list[CardData]:
        log.info("═" * 60)
        log.info("  MYP Cards Arbitrage Scanner")
        log.info(f"  Threshold: {MARGIN_THRESHOLD*100:.0f}% | Language: EN only | Condition: NM")
        log.info(f"  Min price: R${MIN_PRICE_BRL:.0f}")
        if edition_filter:
            log.info(f"  Edition filter: {', '.join(edition_filter)}")
        log.info("═" * 60)

        editions = self.get_all_editions()

        # Filter by specific edition names (case-insensitive substring match)
        if edition_filter:
            filtered = []
            filter_lower = [f.lower().strip() for f in edition_filter]
            for ed in editions:
                title_lower = ed["title"].lower()
                for f in filter_lower:
                    if f in title_lower:
                        filtered.append(ed)
                        log.info(f"  ✅ Matched: '{ed['title']}' (filter: '{f}')")
                        break
            editions = filtered
            if not editions:
                log.warning("No editions matched the filter! Check edition names.")
                return []

        if max_editions:
            editions = editions[:max_editions]

        for i, ed in enumerate(editions):
            log.info(f"\n[{i+1}/{len(editions)}] 📦 {ed['title']}")

            product_urls = self.get_edition_products(ed["url"])
            if max_products:
                product_urls = product_urls[:max_products]
            log.info(f"  → {len(product_urls)} products found")

            for j, purl in enumerate(product_urls):
                self._stats["products_scanned"] += 1
                if (j + 1) % 10 == 0:
                    log.info(f"  Scanning {j+1}/{len(product_urls)}...")

                card = self.scrape_product(purl, ed["title"])
                if not card:
                    continue

                self._stats["en_found"] += 1
                card.edition_url = ed["url"]
                self.cards.append(card)

                if card.margin_pct is not None and card.margin_pct >= MARGIN_THRESHOLD:
                    log.info(
                        f"  🔥 DEAL: {card.name} | "
                        f"EN NM lowest: R${card.myp_lowest_en_nm:,.2f} | "
                        f"TCG: R${card.tcg_player_price:,.2f} | "
                        f"Margin: {card.margin_pct*100:.1f}%"
                    )
                elif card.margin_pct is not None and card.margin_pct < 0:
                    log.debug(
                        f"  ⬇️ {card.name} | EN NM: R${card.myp_lowest_en_nm:,.2f} "
                        f"> TCG: R${card.tcg_player_price:,.2f} (negative)"
                    )

        # Summary
        deals = [c for c in self.cards if c.margin_pct and c.margin_pct >= MARGIN_THRESHOLD]
        log.info("\n" + "═" * 60)
        log.info(f"  Pages fetched: {self._stats['pages_fetched']}")
        log.info(f"  Products scanned: {self._stats['products_scanned']}")
        log.info(f"  EN cards found: {self._stats['en_found']}")
        log.info(f"  Cards with prices: {len(self.cards)}")
        log.info(f"  🔥 Deals (≥{MARGIN_THRESHOLD*100:.0f}%): {len(deals)}")
        # M5 fix: funnel stats pra auditoria
        log.info(f"  ── Skipped breakdown (M5):")
        log.info(f"      No TCG price: {self._stats['skipped_no_tcg_price']}")
        log.info(f"      No EN sellers: {self._stats['skipped_no_en_sellers']}")
        log.info(f"      Low price (<R${MIN_PRICE_BRL:.0f}): {self._stats['skipped_low_price']}")
        log.info(f"  ── Other diagnostics:")
        log.info(f"      Supranumerary warnings (H3): {self._stats['supranumerary_warnings']}")
        log.info(f"      EN truncation risks (T1): {self._stats['en_truncation_risks']}")
        log.info(f"      HTTP retries (M1): {self._stats['http_retries']}")
        log.info("═" * 60)

        return self.cards


# ══════════════════════════════════════════════════════════════════════
# XLSX GENERATOR
# ══════════════════════════════════════════════════════════════════════
def generate_xlsx(cards: list[CardData], output_path: str, threshold: float):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()

    # ── Styles ──
    hdr_font = Font(bold=True, color="FFFFFF", size=11, name="Arial")
    hdr_fill = PatternFill("solid", fgColor="2F5496")
    hdr_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    border = Border(
        left=Side("thin", "D9D9D9"), right=Side("thin", "D9D9D9"),
        top=Side("thin", "D9D9D9"), bottom=Side("thin", "D9D9D9"),
    )
    green_fill = PatternFill("solid", fgColor="C6EFCE")
    yellow_fill = PatternFill("solid", fgColor="FFEB9C")
    red_fill = PatternFill("solid", fgColor="FFC7CE")
    normal = Font(name="Arial", size=10)
    bold_green = Font(name="Arial", size=10, bold=True, color="006100")

    headers = [
        "Card Name", "Edition", "Rarity",
        "MYP EN NM (R$)", "TCG Player (R$)",
        "Margin %", "Diff (R$)", "NM Sellers", "⚠️ EN Trunc", "URL", "Updated",
    ]
    widths = [38, 32, 16, 16, 16, 11, 13, 10, 11, 55, 16]

    def write_headers(ws):
        for col, h in enumerate(headers, 1):
            c = ws.cell(row=1, column=col, value=h)
            c.font = hdr_font
            c.fill = hdr_fill
            c.alignment = hdr_align
            c.border = border
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "A2"

    def write_card_row(ws, row, card):
        diff = (card.tcg_player_price or 0) - (card.myp_lowest_en_nm or 0)
        trunc_flag = "⚠️ MAYBE" if card.en_truncation_risk else ""
        vals = [
            card.name, card.edition, card.rarity,
            card.myp_lowest_en_nm, card.tcg_player_price,
            card.margin_pct, diff, card.en_nm_sellers, trunc_flag,
            card.product_url, card.last_updated,
        ]
        for col, v in enumerate(vals, 1):
            c = ws.cell(row=row, column=col, value=v)
            c.font = normal
            c.border = border
            if col in (4, 5, 7):      # price columns
                c.number_format = '#,##0.00'
            if col == 6:               # margin %
                c.number_format = '0.0%'
                if v and v >= 0.50:
                    c.font = bold_green
                    c.fill = green_fill
                elif v and v >= threshold:
                    c.fill = yellow_fill
                elif v and v < 0:
                    c.fill = red_fill
            if col == 9 and card.en_truncation_risk:  # ⚠️ EN Trunc column
                c.fill = red_fill
                c.alignment = Alignment(horizontal="center")

    # ── Sheet 1: Deals ──
    ws1 = wb.active
    ws1.title = "🔥 Deals"
    write_headers(ws1)

    deals = sorted(
        [c for c in cards if c.margin_pct and c.margin_pct >= threshold],
        key=lambda x: x.margin_pct or 0, reverse=True,
    )
    for i, card in enumerate(deals, 2):
        write_card_row(ws1, i, card)
        if card.margin_pct and card.margin_pct >= 0.50:
            for col in range(1, 4):
                ws1.cell(row=i, column=col).fill = green_fill

    ws1.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(len(deals)+1, 2)}"

    # ── Sheet 2: All EN Cards ──
    ws2 = wb.create_sheet("All EN Cards")
    write_headers(ws2)
    all_sorted = sorted(cards, key=lambda x: x.margin_pct or -999, reverse=True)
    for i, card in enumerate(all_sorted, 2):
        write_card_row(ws2, i, card)

    # ── Sheet 3: Top 50 by Margin (visual review pool) ──
    # Operador inspeciona visualmente pra decidir se é chase (pokémon
    # icônico, arte bonita, etc.) — não filtra por threshold.
    ws_top = wb.create_sheet("🏆 Top 50 Margin")
    write_headers(ws_top)
    top50 = all_sorted[:50]
    for i, card in enumerate(top50, 2):
        write_card_row(ws_top, i, card)
    ws_top.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(len(top50)+1, 2)}"

    # ── Sheet 4: 🚨 Validate Manually (cards com en_truncation_risk) ──
    # 2026-05-12 v5.3: cards onde alguma seller table bateu cap sem EN visível.
    # Lowest EN-NM reportado é teto — listing real pode ser mais barato. Operador
    # valida buscando perfil de seller direto (ex.: bartsimpson teve Psyduck R$300 EN
    # truncado da página enquanto scanner reportou R$415).
    ws_val = wb.create_sheet("🚨 Validate Manually")
    write_headers(ws_val)
    validate = sorted(
        [c for c in cards if c.en_truncation_risk],
        key=lambda x: x.margin_pct or -999, reverse=True,
    )
    for i, card in enumerate(validate, 2):
        write_card_row(ws_val, i, card)
    if validate:
        ws_val.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(validate)+1}"

    # ── Sheet 5: Summary ──
    ws3 = wb.create_sheet("Summary")
    ws3.column_dimensions['A'].width = 32
    ws3.column_dimensions['B'].width = 25
    title_font = Font(bold=True, size=16, name="Arial")
    label_font = Font(bold=True, name="Arial", size=11)

    ws3.cell(row=1, column=1, value="MYP Arbitrage Scanner").font = title_font
    ws3.cell(row=2, column=1, value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}").font = normal
    ws3.cell(row=4, column=1, value="Margin Threshold").font = label_font
    ws3.cell(row=4, column=2, value=f"{threshold*100:.0f}%").font = normal
    ws3.cell(row=5, column=1, value="Language Filter").font = label_font
    ws3.cell(row=5, column=2, value="English (EN)").font = normal
    ws3.cell(row=6, column=1, value="Total EN Cards").font = label_font
    ws3.cell(row=6, column=2, value=len(cards)).font = normal
    ws3.cell(row=7, column=1, value="Deals Found").font = label_font
    ws3.cell(row=7, column=2, value=len(deals)).font = bold_green

    ws3.cell(row=9, column=1, value="Top 10 Deals:").font = Font(bold=True, size=12, name="Arial")
    for i, d in enumerate(deals[:10], 10):
        ws3.cell(row=i, column=1, value=d.name).font = normal
        margin_cell = ws3.cell(row=i, column=2, value=f"{d.margin_pct*100:.1f}% — R${d.margin_brl:,.2f}")
        margin_cell.font = bold_green

    wb.save(output_path)
    log.info(f"📊 Spreadsheet saved: {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="MYP Cards Arbitrage Scanner — Pokémon TCG Singles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python myp_arbitrage_scanner.py                           # Scan completo
  python myp_arbitrage_scanner.py --max-editions 3          # Teste com 3 edições
  python myp_arbitrage_scanner.py --threshold 40 --delay 2  # 40% margin, 2s delay
  python myp_arbitrage_scanner.py -o deals.xlsx             # Output customizado
  python myp_arbitrage_scanner.py --editions "Ascended Heroes" "Prismáticas"  # Edições específicas
        """,
    )
    parser.add_argument("--max-editions", type=int, default=0,
                       help="Limite de edições (0 = todas, ~326 total)")
    parser.add_argument("--max-products", type=int, default=0,
                       help="Limite de produtos por edição (0 = todos)")
    parser.add_argument("--threshold", type=float, default=25,
                       help="Margem mínima %% para alerta (default: 25)")
    parser.add_argument("--min-price", type=float, default=80,
                       help="Preço mínimo EN em R$ (default: 80)")
    parser.add_argument("--delay", type=float, default=1.5,
                       help="Delay entre requests em segundos (default: 1.5)")
    parser.add_argument("--editions", nargs="+", type=str, default=None,
                       help="Filtrar por edições específicas (substring match). Ex: --editions \"Ascended Heroes\" \"Prismáticas\"")
    parser.add_argument("-o", "--output", type=str, default="",
                       help="Caminho do arquivo .xlsx de saída")
    args = parser.parse_args()

    # C1 fix (2026-05-12): MYP usa percent integer (35 = 35%), oposto do CT
    # scanner que usa fração (0.35). Se o operador passar < 1.0, é provável
    # que tenha confundido as convenções. Auto-converte com warning.
    if args.threshold < 1.0:
        log.warning(
            f"--threshold {args.threshold} < 1.0 parece fração (convenção CT scanner), "
            f"mas MYP usa percent. Convertendo para {args.threshold * 100}."
        )
        args.threshold = args.threshold * 100

    MARGIN_THRESHOLD = args.threshold / 100
    MIN_PRICE_BRL = args.min_price
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    output_path = args.output or f"myp_arbitrage_{timestamp}.xlsx"

    scraper = MYPScraper(delay=args.delay)
    cards = scraper.scan(max_editions=args.max_editions, max_products=args.max_products,
                         edition_filter=args.editions)

    if cards:
        generate_xlsx(cards, output_path, MARGIN_THRESHOLD)
        print(f"\nDone! Open: {output_path}")
    else:
        log.warning("No English cards found with both MYP and TCG Player prices.")
        log.info("Tips: try --max-editions 5 for a quick test, or increase --delay")
