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
Data: 2026-04-15 (v5) | 2026-05-12 (v5.1 → v5.3) | 2026-05-14 (v5.4 → v5.6) | 2026-05-16 (v5.8) | 2026-05-19 (v5.8.4 → v5.8.6)
Versão: v5.8.6

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

# v5.6.1 fix: requests é transitive dep do cloudscraper E é referenciado em
# `except (requests.RequestException, ...)` no _get retry loop (v5.4 C3 fix).
# Antes era importado APENAS no fallback ImportError do cloudscraper, causando
# NameError em qualquer setup que tenha cloudscraper (todos os production runs).
import os
import requests
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

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
MAX_EDITION_PAGES = 50           # v5.4 H4: cap em get_all_editions (evita infinite loop)
MIN_EDITIONS_EXPECTED = 200      # v5.4 C2: catalog scrape sanity floor (~326 esperado, alarme em <200)
TIMEOUT = 20                     # timeout HTTP em segundos
HTTP_MAX_RETRIES = 3             # M1 fix: retries em transient errors
DEBUG_DIR = Path(__file__).resolve().parent / ".debug"   # M4 fix: subpasta dedicada
SUPRANUMERARY_PRICE_THRESHOLD = 200.0  # H3 fix: TCG R$ acima disso + rarity="Comum" = SIR/HR suspeito
# v5.8.3 (2026-05-18): cartas Jumbo (oversized ~25×35cm) têm mercado/preço
# distintos da versão standard. MYP agrupa standard + jumbo na MESMA página de
# produto; a variante é indicada por seller-row na coluna `.estoque-lista-nomeenfoil`
# ("Foil"). Detectamos e excluímos rows Jumbo da contagem EN. Caso M-Rayquaza-EX
# 098/98 XY 7 (produto 32737): h1 sem "Jumbo" mas 5 sellers com Jumbo no Foil col
# inflavam o min preço EN.
#
# v5.8.4 (2026-05-19): regex broader cobre também 'oversized', 'box topper',
# 'poster card'. MYP usa qualquer um desses pra produtos físicos não-standard.
# \b word-boundary em todos pra consistência (foil_re antes não tinha; rara
# colisão tipo "jumbocard" não documentada mas defensivo).
OVERSIZED_FOIL_RE = re.compile(
    r"\b(jumbo|oversized)\b", re.IGNORECASE,
)
# Filtro por título como segunda camada — caso MYP liste oversized como
# produto standalone (sem distinção via coluna foil).
OVERSIZED_TITLE_RE = re.compile(
    r"\b(jumbo|oversized|box\s?topper|poster\s?card)\b", re.IGNORECASE,
)
# Aliases retrocompat — `postprocess_v583_flags.py` ainda importa o nome
# antigo. Manter até refactor downstream completo. NÃO criar novos usos.
JUMBO_FOIL_RE = OVERSIZED_FOIL_RE
JUMBO_TITLE_RE = OVERSIZED_TITLE_RE
# v5.8.3 (2026-05-18): Flareon VMAX (018/203) "Prize Pack Series" — observado
# 1 seller único (`gvrgyn`) listando como Inglês quando a carta não tem print
# EN nessa edição (mislabeling). Sem cross-check pokemontcg.io confiável, a
# heurística defensiva é tratar 1-seller-EN como single_seller_risk e mover
# pra Validate Manually. Não suprime — apenas escala visibilidade.
# v5.8.4 (2026-05-19): CLI override via --min-en-sellers. Default permanece 1
# (legacy v5.8.3 behavior). Card é flagged quando `en_sellers <
# MIN_EN_SELLERS_FOR_DEALS` (strict less-than). Threshold pode ser elevado
# pra cenários mais conservadores (ex.: --min-en-sellers 2 trata 1 OU 2
# sellers como risco).
SINGLE_EN_SELLER_RISK_THRESHOLD = 1  # legacy alias (≤ threshold = risk)
MIN_EN_SELLERS_FOR_DEALS_DEFAULT = 2  # < default = flagged (matches legacy 1≤1)
# v5.8 H2 (2026-05-16): se TCG declarado >> última venda real, MYP infla o
# preço de referência. Caso Jirachi PR-SM_SM161: declarava R$1499 vs última
# venda real R$19,99 (75x). Threshold 10x captura inflação grosseira sem
# false-positive em cards com pouca liquidez (last sale antigo + alta).
TCG_SUSPECT_RATIO_THRESHOLD = 10.0
# v5.4 H1: idiomas EN reconhecidos. Tudo fora dessa lista que parecer um title de
# flag-icon (não vazio) é tratado como "unknown" e contado pra warn-once.
KNOWN_LANGUAGES = {
    "Inglês", "Português", "Japonês", "Italiano",
    "Espanhol", "Francês", "Alemão", "Coreano",
    "English", "Portuguese", "Japanese",
}
EN_LANGUAGES = {"Inglês", "English"}

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
    # v5.8 H2 (2026-05-16): MYP às vezes reporta .estat-tcg inflado (caso
    # Jirachi PR-SM_SM161: MYP=R$1499 vs TCGPlayer real $26=R$132 = 11x off).
    # Capturar última venda real do MYP pra sanity check.
    myp_last_sale_brl: Optional[float] = None
    tcg_suspect: bool = False                    # True se TCG declarado >> última venda real
    margin_pct: Optional[float] = None
    margin_brl: Optional[float] = None
    en_nm_sellers: int = 0                      # qtd vendedores EN NM
    en_truncation_risk: bool = False            # 2026-05-12: alguma seller table está no cap (15/20) sem EN visível → EN possivelmente escondido
    # v5.8.3 (2026-05-18): único seller EN visível → risco de mislabeling de idioma
    # (caso Flareon VMAX 018/203 Prize Pack: 1 seller gvrgyn lista como EN mas
    # carta não tem print EN nessa edição). Sinaliza pra Validate Manually.
    single_en_seller_risk: bool = False
    # v5.8.5 (2026-05-19): collector# > set_size = variant (SIR/HR/promo extra/
    # special illustration rare). Frequente JP-only. Caso Darumaka 097/086, Mew
    # ex 232/091, Charizard ex 234/091. Parse de (NNN/MMM) no card.name; quando
    # numerator > denominator, flag oversized_collector_risk = True.
    oversized_collector_risk: bool = False
    last_updated: str = ""


# ══════════════════════════════════════════════════════════════════════
# SCRAPER
# ══════════════════════════════════════════════════════════════════════
class MYPScraper:
    def __init__(
        self,
        delay: float = REQUEST_DELAY,
        min_en_sellers: int = MIN_EN_SELLERS_FOR_DEALS_DEFAULT,
    ):
        # v5.8.4 (2026-05-19): threshold configurable via CLI. Card é flagged
        # quando `en_sellers < min_en_sellers`. Default 2 reproduz v5.8.3
        # (que checava `en_sellers <= SINGLE_EN_SELLER_RISK_THRESHOLD=1`).
        self.min_en_sellers = min_en_sellers
        if HAS_CLOUDSCRAPER:
            # 2026-05-17: Cloudflare passou a bloquear o fingerprint chrome/windows
            # do cloudscraper (HTTP 403 cf-mitigated: challenge). Firefox/windows
            # ainda passa. Mantemos chrome no env var pra rollback fácil.
            browser_fp = os.environ.get("MYP_CLOUDSCRAPER_BROWSER", "firefox")
            self.session = cloudscraper.create_scraper(
                browser={"browser": browser_fp, "platform": "windows", "desktop": True},
            )
            log.info(f"Using cloudscraper (browser={browser_fp}, CloudFlare bypass enabled)")
            # Não sobrescreve User-Agent — o cloudscraper já configura UA coerente
            # com o TLS fingerprint do browser escolhido. Forçar UA Chrome num
            # fingerprint Firefox = mismatch detectado pelo CF (403).
            non_ua_headers = {k: v for k, v in HEADERS.items() if k.lower() != "user-agent"}
            self.session.headers.update(non_ua_headers)
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
            # v5.4 H1: títulos de idioma fora de KNOWN_LANGUAGES (drop silencioso)
            "skipped_unknown_lang_titles": 0,
            # v5.8 H2 (2026-05-16): cards com TCG declarado >> última venda
            # real (Jirachi PR-SM_SM161 caso). Não filtra do funnel — fica
            # em All EN Cards, mas é excluído da sheet 🔥 Deals.
            "tcg_suspects": 0,
            # v5.8.3 (2026-05-18): produtos Jumbo (oversized) skipados pelo
            # filtro de TÍTULO (camada 2). `.estat-tcg` reflete preço da carta
            # standard, deal é fictício.
            "skipped_jumbo": 0,
            # v5.8.3 (2026-05-18): seller rows com foil="Jumbo" filtradas pela
            # camada 1 (caso M-Rayquaza-EX XY 7: standard + jumbo no mesmo
            # produto, MYP diferencia via coluna `.estoque-lista-nomeenfoil`).
            "jumbo_rows_filtered": 0,
            # v5.8.3 (2026-05-18): cards com apenas 1 seller EN visível —
            # risco de seller mislabeling (caso Flareon VMAX 018/203).
            "single_en_seller_risks": 0,
            # v5.8.5 (2026-05-19): collector# > set_size (variant fora do
            # numbered set, frequentemente JP-only). Caso Darumaka 097/086.
            "oversized_collector_risks": 0,
        }
        # v5.4 H1: warn-once cache pra unknown language titles
        self._unknown_lang_seen: set[str] = set()

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
            except (requests.RequestException, ConnectionError, TimeoutError, OSError) as e:
                # v5.4 C3: catch só erros de rede. Parser bugs (lxml/bs4),
                # AttributeError, MemoryError etc devem propagar — indicam
                # mudança de HTML ou bug de código que merece crash, não retry.
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
    def _parse_brl(text) -> Optional[float]:
        """Parse price string. Handles BR canonical ('R$ 1.900,00') AND US
        decimal leakage ('R$ 30.00') that MYP sometimes emits in
        `.estatistica-ultimo`. v5.8.2 fix: previously '30.00' → 3000.0 (read
        as BR thousands), broke sanity-check ratio → false negatives.

        v5.8.4 (2026-05-19): defensive against None / non-str inputs. Reviewer
        flagged that `text.strip()` raises AttributeError if a caller ever
        passes an Optional[str] that turns out None (or a numeric from a
        future refactor). Guard before stripping.
        """
        if text is None or not isinstance(text, str):
            return None
        text = text.strip()
        if not text:
            return None
        text = re.sub(r'[R$\s\xa0]', '', text)
        if not text:
            return None
        has_comma = ',' in text
        has_dot = '.' in text
        if has_comma and has_dot:
            # Both present. Whichever appears LAST is the decimal separator.
            if text.rfind(',') > text.rfind('.'):
                # BR canonical: '1.500,00' → '1500.00'
                text = text.replace('.', '').replace(',', '.')
            else:
                # US thousands: '1,500.00' → '1500.00'
                text = text.replace(',', '')
        elif has_comma:
            # Only comma → BR decimal: '30,00' → '30.00'
            text = text.replace(',', '.')
        elif has_dot:
            # Only dot → disambiguate by suffix length.
            # 2-digit suffix → decimal ('30.00' = 30.0; '1234.56' = 1234.56)
            # 3-digit suffix with single dot → BR thousands ('30.000' = 30000)
            # Multiple dots → BR thousands ('1.500.000' = 1500000)
            parts = text.split('.')
            if len(parts) > 2:
                text = text.replace('.', '')
            elif len(parts[-1]) == 3:
                text = text.replace('.', '')
            # else: keep as-is (US decimal style)
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
        # v5.4 H4: cap em MAX_EDITION_PAGES previne infinite loop se MYP
        # alguma vez retornar pages que parecem ter conteúdo novo indefinidamente.
        while page <= MAX_EDITION_PAGES:
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
        else:
            # v5.4 H4: hit MAX_EDITION_PAGES sem natural exit — sinal de bug
            log.warning(
                f"  ⚠️ get_all_editions hit MAX_EDITION_PAGES={MAX_EDITION_PAGES} "
                f"sem encontrar fim natural. Possível recursão de paginação no MYP."
            )

        # v5.4 C2: sanity check — catalog scrape esperado tem ~326 editions.
        # Abaixo de MIN_EDITIONS_EXPECTED é forte indicador que selectors
        # quebraram mid-catalog (Strategy 3 fallback pode silenciosamente truncar).
        if len(editions) < MIN_EDITIONS_EXPECTED:
            log.warning(
                f"  🚨 Catalog scrape suspeito: {len(editions)} editions "
                f"encontradas (esperado >={MIN_EDITIONS_EXPECTED}). "
                f"Selectors podem ter quebrado mid-catalog. Validar manualmente."
            )
        log.info(f"Found {len(editions)} editions")
        return editions

    # ── Step 2: Get product URLs from edition listing ────────────────
    def get_edition_products(self, edition_url: str) -> list[str]:
        """Get all product URLs from an edition listing page."""
        product_urls = []
        seen = set()
        page = 1
        # v5.4 H3: detecta loop de página duplicada (MYP retornando page 1
        # quando page=N overflowing). Compara primeira URL de page N vs N-1.
        prev_first_url: Optional[str] = None

        while page <= MAX_PAGES_PER_EDITION:
            url = f"{edition_url}?page={page}"
            soup = self._get(url)
            if not soup:
                break

            links = soup.select('a[href*="/pokemon/produto/"]')

            # v5.4 H3: page first-URL fingerprint
            current_first_url: Optional[str] = None
            for link in links:
                href = link.get("href", "")
                if href:
                    current_first_url = (
                        f"{BASE_URL}{href}" if href.startswith("/") else href
                    )
                    break
            if (page > 1 and prev_first_url is not None
                    and current_first_url == prev_first_url):
                log.warning(
                    f"  🚨 Pagination loop detectado em {edition_url}: "
                    f"page {page} retornou mesma primeira URL de page {page-1}. "
                    f"Stopping para evitar under-coverage silencioso."
                )
                break
            prev_first_url = current_first_url

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

        # Name. v5.8.2: defensive fallback chain. h1 ausente acontece quando
        # MYP rota retorna template diferente (ex.: erro JS injetado) e o XLSX
        # 2026-05-17 saiu com Card Name=None em 1252/1252 rows. Backup: <title>
        # ou slug da URL.
        h1 = soup.select_one("h1")
        card.name = h1.get_text(strip=True) if h1 else ""
        if not card.name:
            title_tag = soup.find("title")
            if title_tag and title_tag.text:
                card.name = title_tag.text.split("|")[0].strip()
        if not card.name:
            slug = url.rstrip("/").split("/")[-1].replace("-", " ").strip()
            if slug and not slug.isdigit():
                card.name = slug.title()
        if not card.name:
            log.warning(f"  No name extractable from {url}")

        # v5.8.3 (2026-05-18): SKIP Jumbo (oversized) cards. `.estat-tcg` no MYP
        # reflete preço da carta standard, gerando deals fictícios com margem
        # gigante (ex.: M-Rayquaza-EX 098/98 XY 7 Jumbo). Skip ANTES de fetch
        # de tabela de seller pra economizar processamento e evitar contaminação.
        if card.name and OVERSIZED_TITLE_RE.search(card.name):
            self._stats["skipped_jumbo"] += 1
            log.info(f"  ⏭️  Skipping oversized card: {card.name}")
            return None

        # Product code
        page_text = soup.get_text()
        code_match = re.search(r'pokemon_[a-z]{2,3}_[\w/]+', page_text)
        card.product_code = code_match.group(0) if code_match else ""

        # ── TCG Player price (always EN reference) ──
        # 2026-05-14 v5.3: usa findall + [-1] (mesma defensive pattern do
        # strikethrough fix). Cobre o caso de .estat-tcg ter múltiplos R$
        # (ex.: "Last R$ X | Avg R$ Y") — pega o último valor numérico em
        # vez de falhar parse com texto multi-preço.
        tcg_el = soup.select_one(".estat-tcg")
        if tcg_el:
            tcg_matches = re.findall(r'R\$\s*[\d.,]+', tcg_el.get_text())
            if tcg_matches:
                card.tcg_player_price = self._parse_brl(tcg_matches[-1])

        # If no TCG Player price, skip this product entirely
        if not card.tcg_player_price:
            self._stats["skipped_no_tcg_price"] += 1
            return None

        # v5.8 H2 (2026-05-16): capturar última venda real MYP pra sanity check.
        # MYP às vezes infla `.estat-tcg` (Jirachi PR-SM_SM161: declarava R$1499
        # mas TCGPlayer real $26=R$132 e última venda MYP foi R$19,99 — diff 75x).
        # Se TCG declarado >> última venda, provavelmente bug do MYP.
        last_sale_el = soup.select_one(".estatistica-ultimo")
        if last_sale_el:
            ls_matches = re.findall(r'R\$\s*[\d.,]+', last_sale_el.get_text())
            if ls_matches:
                card.myp_last_sale_brl = self._parse_brl(ls_matches[-1])

        # Sanity check: ratio TCG declarado / última venda real
        if card.myp_last_sale_brl and card.myp_last_sale_brl > 0:
            ratio = card.tcg_player_price / card.myp_last_sale_brl
            if ratio > TCG_SUSPECT_RATIO_THRESHOLD:
                # TCG declarado é >Nx última venda → MYP bug provável
                card.tcg_suspect = True
                self._stats["tcg_suspects"] += 1
                log.warning(
                    f"  🚨 TCG suspect: {card.name or url} | "
                    f"TCG declarado R${card.tcg_player_price:.2f} é "
                    f"{ratio:.1f}x última venda R${card.myp_last_sale_brl:.2f}. "
                    f"Provável inflação do .estat-tcg — excluído da sheet 🔥 Deals."
                )

        # ── Parse seller tables: extract EN sellers only ──
        # 2026-05-12: itera por tabela individualmente (não plano em tr)
        # pra detectar truncamento de EN. Padrão MYP: Tabela 0 (lojistas, cap ~15)
        # + Tabela 1 (marketplace, cap ~20). Quando uma tabela bate o cap E não
        # tem EN visível, há risco de listing EN-NM real mais barato escondido
        # (caso bartsimpson Psyduck R$300 EN sendo truncado por 20 listings PT/JP).
        en_prices = []
        en_sellers = 0
        jumbo_rows_seen = 0  # v5.8.3: rows com foil="Jumbo" (caso M-Rayquaza-EX XY 7)
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
                # 2026-05-12 v5.3: row pode ter strikethrough promo
                # ("R$ 275,00 R$ 220,00" — R$275 antigo riscado, R$220 ativo).
                # v5.4 H2: usa min() em vez de [-1] — preço ativo é sempre
                # o menor (promo); [-1] quebrava se MYP injetasse 3º R$
                # (frete, "you save", etc). Min é defensivo a layout drift.
                price_matches = re.findall(r'R\$\s*[\d.,]+', row_text)
                row_price = None
                if price_matches:
                    parsed = [self._parse_brl(p) for p in price_matches]
                    parsed = [p for p in parsed if p is not None and p > 0]
                    if parsed:
                        row_price = min(parsed)
                    if len(price_matches) > 2:
                        log.debug(
                            f"  Row com {len(price_matches)} R$ matches "
                            f"(esperado 1-2): {row_text[:120]}"
                        )
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
                        if title_val in KNOWN_LANGUAGES:
                            lang = title_val
                            break

                # v5.4 H1: lang não-vazio mas fora do conhecido = drift potencial
                # (ex.: MYP normalizar "Inglês" → "Ingles" sem acento, ou novo
                # idioma adicionado). Counter + warn-once previne silent zero.
                if lang and lang not in KNOWN_LANGUAGES:
                    self._stats["skipped_unknown_lang_titles"] += 1
                    if lang not in self._unknown_lang_seen:
                        self._unknown_lang_seen.add(lang)
                        log.warning(
                            f"  ⚠️ Idioma desconhecido detectado: '{lang}' "
                            f"(não está em KNOWN_LANGUAGES). Pode ser drift de "
                            f"título flag-icon do MYP. Adicionar à constante "
                            f"se for mapeamento legítimo."
                        )

                if lang not in EN_LANGUAGES:
                    continue

                # v5.8.3 (2026-05-18): skip rows com foil="Jumbo" (oversized).
                # MYP agrupa standard + jumbo na mesma página de produto; a
                # coluna `td.estoque-lista-nomeenfoil` indica a variante. TCG
                # Player price refere-se à standard, então jumbo rows inflam
                # `min(en_prices)` artificialmente (caso M-Rayquaza-EX 098/98
                # XY 7: 5 sellers Jumbo a R$650 enquanto TCG standard era
                # R$4801 → margin fictícia de 638%).
                foil_el = row.select_one("td.estoque-lista-nomeenfoil")
                foil_txt = foil_el.get_text(strip=True) if foil_el else ""
                if OVERSIZED_FOIL_RE.search(foil_txt):
                    jumbo_rows_seen += 1
                    continue

                # Filter: NM (Near Mint) only — skip Played, Damaged, etc.
                # v5.8.7: lê a célula de condição DEDICADA
                # (td.estoque-lista-qualidadenome, ex.: "NM - Quase nova",
                # "SP - Pouco jogada") e casa o código EXATO antes do " - ".
                # Antes era substring "NM" na linha inteira, que vazava não-NM
                # quando "NM" aparecia em qualquer coluna (nick de vendedor,
                # obs, etc). NM-only é invariante do scanner; sem célula de
                # qualidade confirmável (drift de layout), a linha é pulada.
                qual_el = row.select_one("td.estoque-lista-qualidadenome")
                qual_txt = qual_el.get_text(" ", strip=True) if qual_el else ""
                qual_code = qual_txt.split("-", 1)[0].strip().upper()
                if qual_code != "NM":
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

        # v5.8.3: log se rows Jumbo foram filtradas
        if jumbo_rows_seen > 0:
            self._stats["jumbo_rows_filtered"] += jumbo_rows_seen
            log.info(
                f"  ⏭️  Skipped {jumbo_rows_seen} Jumbo seller row(s) "
                f"em {card.name or url}"
            )

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
        # v5.8.3 (2026-05-18): 1 seller EN só = risco de mislabeling
        # (caso Flareon VMAX 018/203 Prize Pack: seller único listava como EN
        # carta sem print EN). Flag pra Validate Manually em vez de skip,
        # pra não suprimir deals legítimos de cards realmente raros.
        # v5.8.4 (2026-05-19): threshold agora configurável via CLI
        # (--min-en-sellers). `en_sellers < self.min_en_sellers` = flag.
        # Default 2 reproduz comportamento v5.8.3 (que era ≤1).
        if en_sellers < self.min_en_sellers:
            card.single_en_seller_risk = True
            self._stats["single_en_seller_risks"] += 1
            log.warning(
                f"  ⚠️ Low EN seller count: {card.name or url} | "
                f"{en_sellers} seller(s) EN-NM visível (< {self.min_en_sellers}) — "
                f"possível mislabeling de idioma. Validar manualmente."
            )
        if truncation_risk:
            self._stats["en_truncation_risks"] += 1
            log.warning(
                f"  🚨 EN truncation risk: {card.name} | "
                f"alguma seller table está com ≥{TABLE_CAP_THRESHOLD} rows sem EN visível "
                f"→ lowest EN-NM R${card.myp_lowest_en_nm:.2f} pode estar superestimado. "
                f"Validar manualmente."
            )

        # ── Rarity ──
        # 2026-05-14 v5.3: page_text.lower() precomputed (era chamado N vezes
        # no loop, ~50µs cada para um page_text típico de 300KB).
        rarity_keywords = [
            "Illustration Rare", "Special Art Rare", "Hyper Rare",
            "Ultra Rare", "Secret Rare", "Art Rare", "Double Rare",
            "Rara Hiper", "Rara Ultra", "Rara Secreta", "Rara",
            "Incomum", "Comum",
        ]
        page_text_lower = page_text.lower()
        for rarity in rarity_keywords:
            if rarity.lower() in page_text_lower:
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
                # v5.8.5 (2026-05-19): mesma extração serve pra
                # oversized_collector_risk. Quando numerator > denominator, o
                # card é variant fora do set numerado (SIR/HR/promo extra/
                # special illustration rare), frequentemente JP-only e com
                # preço TCG inflado em USD. Casos: Darumaka 097/086 (Black
                # Bolt SIR), Mew ex 232/091 (151 SIR), Charizard ex 234/091.
                # Sinaliza pra triagem visual; combina com single_en_seller
                # pra escalar pra Validate Manually.
                if num > total:
                    card.oversized_collector_risk = True
                    self._stats["oversized_collector_risks"] += 1
                    log.info(
                        f"  ⚠️ Oversized collector#: {card.name} "
                        f"({num}>{total}) — provável variant SIR/HR/promo. "
                        f"Sinalizado pra triagem visual."
                    )
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
             edition_filter: list[str] = None,
             chunk_index: int = 0, chunk_total: int = 1) -> list[CardData]:
        log.info("═" * 60)
        log.info("  MYP Cards Arbitrage Scanner")
        log.info(f"  Threshold: {MARGIN_THRESHOLD*100:.0f}% | Language: EN only | Condition: NM")
        log.info(f"  Min price: R${MIN_PRICE_BRL:.0f}")
        if edition_filter:
            log.info(f"  Edition filter: {', '.join(edition_filter)}")
        if chunk_total > 1:
            log.info(f"  Chunk: {chunk_index}/{chunk_total} (interleaved)")
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

        # v5.5: chunk slicing interleaved (load balanceado vs sequential blocks).
        # editions[N::M] garante distribuição equilibrada quando edition sizes
        # variam (sequential blocks colocariam todas as massivas num único chunk).
        if chunk_total > 1:
            if not (0 <= chunk_index < chunk_total):
                raise ValueError(
                    f"chunk_index={chunk_index} fora do range [0,{chunk_total})"
                )
            total_before = len(editions)
            editions = editions[chunk_index::chunk_total]
            log.info(
                f"  Chunk slicing: {total_before} editions → {len(editions)} "
                f"(chunk {chunk_index}/{chunk_total})"
            )

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
        log.info(f"      Unknown lang titles (v5.4 H1): {self._stats['skipped_unknown_lang_titles']}")
        log.info(f"      Jumbo cards (title, v5.8.3): {self._stats['skipped_jumbo']}")
        log.info(f"      Jumbo seller rows filtered (v5.8.3): {self._stats['jumbo_rows_filtered']}")
        log.info(f"  ── Other diagnostics:")
        log.info(f"      Supranumerary warnings (H3): {self._stats['supranumerary_warnings']}")
        log.info(f"      EN truncation risks (T1): {self._stats['en_truncation_risks']}")
        log.info(f"      TCG suspects (H2 v5.8): {self._stats['tcg_suspects']}")
        log.info(f"      Single EN seller risks (v5.8.3): {self._stats['single_en_seller_risks']}")
        log.info(f"      Oversized collector# risks (v5.8.5): {self._stats['oversized_collector_risks']}")
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

    # v5.8 (2026-05-16): 2 colunas novas pra surfaçar o sanity check H2:
    #   - "MYP Last Sale (R$)" entre TCG Player e Margin %
    #   - "⚠️ TCG Suspect" depois de EN Trunc
    # Sem isso, o operador via Jirachi PR-SM_SM161 como deal #1 a 1400% mesmo
    # com TCG inflado 75x vs última venda real. Aggregate lê via dict-by-name,
    # então a ordem das colunas não quebra o pipeline.
    # v5.8.5 (2026-05-19): nova coluna `⚠️ COLLECTOR#` depois de Single Seller.
    # Sinaliza cards onde collector_number > set_size (variant SIR/HR/promo
    # extra, frequentemente JP-only). Casos Darumaka 097/086, Mew ex 232/091.
    # Aggregate lê via dict-by-name, então ordem não quebra o pipeline.
    headers = [
        "Card Name", "Edition", "Rarity",
        "MYP EN NM (R$)", "TCG Player (R$)", "MYP Last Sale (R$)",
        "Margin %", "Diff (R$)", "NM Sellers",
        "⚠️ EN Trunc", "⚠️ TCG Suspect", "⚠️ Single Seller", "⚠️ COLLECTOR#",
        "URL", "Updated",
    ]
    widths = [38, 32, 16, 16, 16, 17, 11, 13, 10, 11, 14, 14, 14, 55, 16]
    PRICE_COLS = {4, 5, 6, 8}       # MYP EN NM, TCG Player, Last Sale, Diff
    MARGIN_COL = 7
    EN_TRUNC_COL = 10
    TCG_SUSPECT_COL = 11
    SINGLE_SELLER_COL = 12
    COLLECTOR_COL = 13

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
        suspect_flag = "🚨 SUSPECT" if card.tcg_suspect else ""
        single_flag = "⚠️ 1 SELLER" if card.single_en_seller_risk else ""
        collector_flag = "⚠️ VARIANT" if card.oversized_collector_risk else ""
        vals = [
            card.name, card.edition, card.rarity,
            card.myp_lowest_en_nm, card.tcg_player_price, card.myp_last_sale_brl,
            card.margin_pct, diff, card.en_nm_sellers,
            trunc_flag, suspect_flag, single_flag, collector_flag,
            card.product_url, card.last_updated,
        ]
        for col, v in enumerate(vals, 1):
            c = ws.cell(row=row, column=col, value=v)
            c.font = normal
            c.border = border
            if col in PRICE_COLS:
                c.number_format = '#,##0.00'
            if col == MARGIN_COL:
                # v5.8.6 bug #5: standardize on 2-decimal % across the
                # pipeline (revalidate_deals.py also uses "0.00%"). Header
                # is "Margin %" — value is stored as fraction (e.g. 0.483)
                # so format must render as percentage to match semantics.
                c.number_format = '0.00%'
                if v and v >= 0.50:
                    c.font = bold_green
                    c.fill = green_fill
                elif v and v >= threshold:
                    c.fill = yellow_fill
                elif v and v < 0:
                    c.fill = red_fill
            if col == EN_TRUNC_COL and card.en_truncation_risk:
                c.fill = red_fill
                c.alignment = Alignment(horizontal="center")
            if col == TCG_SUSPECT_COL and card.tcg_suspect:
                c.fill = red_fill
                c.font = Font(bold=True, color="9C0006", name="Arial", size=10)
                c.alignment = Alignment(horizontal="center")
            if col == SINGLE_SELLER_COL and card.single_en_seller_risk:
                c.fill = yellow_fill
                c.alignment = Alignment(horizontal="center")
            if col == COLLECTOR_COL and card.oversized_collector_risk:
                c.fill = yellow_fill
                c.alignment = Alignment(horizontal="center")

    # ── Sheet 1: Deals ──
    # v5.8 (2026-05-16): exclui cards com tcg_suspect (TCG declarado >10x última
    # venda real). Jirachi PR-SM_SM161 era #1 a 1400% com TCG=R$1499 fictício;
    # ratio 75x da última venda. Suspects ainda aparecem em `All EN Cards` e na
    # sheet dedicada `🚨 TCG Suspect` pra inspeção.
    ws1 = wb.active
    ws1.title = "🔥 Deals"
    write_headers(ws1)

    # v5.8.3 (2026-05-18): excluía single_en_seller_risk de Deals.
    # v5.8.4 (2026-05-19): refinamento — single-seller SOZINHO mantém em
    # Deals (com coluna visual `⚠️ 1 SELLER`). Só vira Validate-Manually se
    # acompanhado de tcg_suspect OU en_truncation_risk.
    # v5.8.5 (2026-05-19): oversized_collector_risk segue mesma lógica:
    # sozinho mantém em Deals (coluna `⚠️ COLLECTOR#`), combinado com
    # single_en_seller_risk escala pra Validate Manually (ambos sinais
    # complementares — variant + idioma duvidoso = JP-mislabeled-as-EN).
    def _combined_single_seller_risk(c) -> bool:
        return c.single_en_seller_risk and (
            c.tcg_suspect
            or c.en_truncation_risk
            or c.oversized_collector_risk
        )
    deals = sorted(
        [c for c in cards
         if c.margin_pct and c.margin_pct >= threshold
         and not c.tcg_suspect
         and not _combined_single_seller_risk(c)],
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
    # v5.4 M3: filtra None-margin antes de slice (evita padding visual em
    # runs com <50 cards válidos).
    ws_top = wb.create_sheet("🏆 Top 50 Margin")
    write_headers(ws_top)
    top50 = [c for c in all_sorted if c.margin_pct is not None][:50]
    for i, card in enumerate(top50, 2):
        write_card_row(ws_top, i, card)
    ws_top.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(len(top50)+1, 2)}"

    # ── Sheet 4: 🚨 Validate Manually ──
    # Inclui cards com qualquer flag de risco de detecção:
    #   - en_truncation_risk (2026-05-12 v5.3): seller table no cap sem EN visível
    #   - single_en_seller_risk (v5.8.3 2026-05-18): 1 seller EN → possível mislabeling
    #   - v5.8.5 (2026-05-19): oversized_collector_risk SOZINHO permanece em Deals,
    #     mas combinado com single_en_seller_risk aparece aqui (variant +
    #     idioma duvidoso = JP-mislabeled-as-EN). Mantém escopo enxuto.
    ws_val = wb.create_sheet("🚨 Validate Manually")
    write_headers(ws_val)
    validate = sorted(
        [c for c in cards
         if c.en_truncation_risk
         or c.single_en_seller_risk
         or (c.oversized_collector_risk and c.single_en_seller_risk)],
        key=lambda x: x.margin_pct or -999, reverse=True,
    )
    for i, card in enumerate(validate, 2):
        write_card_row(ws_val, i, card)
    if validate:
        ws_val.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(validate)+1}"

    # ── Sheet 5: 🚨 TCG Suspect (v5.8) ──
    # Cards com TCG declarado >10x última venda real do MYP — provável bug do
    # campo .estat-tcg (caso Jirachi PR-SM_SM161). Excluídos de `🔥 Deals` mas
    # exibidos aqui pra inspeção manual antes de descartar definitivamente.
    ws_susp = wb.create_sheet("🚨 TCG Suspect")
    write_headers(ws_susp)
    suspects = sorted(
        [c for c in cards if c.tcg_suspect],
        key=lambda x: x.margin_pct or -999, reverse=True,
    )
    for i, card in enumerate(suspects, 2):
        write_card_row(ws_susp, i, card)
    if suspects:
        ws_susp.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(suspects)+1}"

    # ── Sheet 6: Summary ──
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
    ws3.cell(row=7, column=1, value="Deals Found (clean)").font = label_font
    ws3.cell(row=7, column=2, value=len(deals)).font = bold_green
    # v5.8: surface TCG suspects + truncation risks no Summary
    ws3.cell(row=8, column=1, value="🚨 TCG Suspects").font = label_font
    ws3.cell(row=8, column=2, value=len(suspects)).font = normal

    ws3.cell(row=10, column=1, value="Top 10 Deals:").font = Font(bold=True, size=12, name="Arial")
    for i, d in enumerate(deals[:10], 11):
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
    parser.add_argument("--min-en-sellers", type=int,
                       default=MIN_EN_SELLERS_FOR_DEALS_DEFAULT,
                       help=f"Min EN-NM sellers for Deals inclusion (default: "
                            f"{MIN_EN_SELLERS_FOR_DEALS_DEFAULT}; was hardcoded "
                            f"in v5.8.3). Cards abaixo são flagged como "
                            f"single_en_seller_risk e podem cair em Validate "
                            f"Manually conforme outras flags.")
    parser.add_argument("--editions", nargs="+", type=str, default=None,
                       help="Filtrar por edições específicas (substring match). Ex: --editions \"Ascended Heroes\" \"Prismáticas\"")
    parser.add_argument("-o", "--output", type=str, default="",
                       help="Caminho do arquivo .xlsx de saída")
    # v5.5: chunk slicing pra GH Actions matrix job
    parser.add_argument("--chunk-index", type=int, default=0,
                       help="Índice do chunk (0-based). Usado com --chunk-total pra dividir scan em jobs paralelos.")
    parser.add_argument("--chunk-total", type=int, default=1,
                       help="Total de chunks (1 = sem chunking). Editions são fatiadas via slicing interleaved.")
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

    scraper = MYPScraper(delay=args.delay, min_en_sellers=args.min_en_sellers)
    log.info(
        f"Config: threshold={args.threshold}%, min_price=R${args.min_price}, "
        f"delay={args.delay}s, min_en_sellers={args.min_en_sellers}"
    )
    cards = scraper.scan(max_editions=args.max_editions, max_products=args.max_products,
                         edition_filter=args.editions,
                         chunk_index=args.chunk_index, chunk_total=args.chunk_total)

    # v5.4 M1 + invariant check: cron precisa distinguir "scan saudável com
    # zero deals" de "scraper quebrado". Exit codes:
    #   0 = healthy run (com ou sem deals — tem cards, OU chunk vazio legítimo)
    #   1 = scraper provavelmente quebrado (funnel collapsou OU sem cards)
    #   2 = filter user-error (--editions não casou nada)
    import sys as _sys
    stats = scraper._stats

    # v5.5 fix: chunk vazio legítimo. Quando chunk_total > 1 e editions[N::M]
    # retorna lista vazia (ex.: --editions casou 1 edição mas chunk_total=6 →
    # só chunk 0 tem trabalho), o chunk deve sair limpo com exit 0, NÃO
    # marcar o job como falha. Aggregate ignora chunks que não produziram XLSX.
    is_empty_chunk = (
        args.chunk_total > 1
        and stats["products_scanned"] == 0
        and stats["pages_fetched"] > 0  # catalog scrape rodou OK
    )
    if is_empty_chunk:
        log.info(
            f"✓ Chunk {args.chunk_index}/{args.chunk_total} vazio após slicing "
            f"(zero editions atribuídas a este chunk). Saindo limpo, "
            f"aggregate ignora chunks sem XLSX."
        )
        _sys.exit(0)

    if not cards:
        # Distinção: filter typo vs site/scraper broken
        if args.editions:
            log.error(
                f"❌ --editions filter ({', '.join(args.editions)}) não casou "
                f"nenhuma edição. Verificar nomes (substring match contra title MYP)."
            )
            _sys.exit(2)
        # Sem filter, ou filter casou mas processou zero — likely broken
        log.error(
            f"❌ Scan retornou zero cards. Funnel: "
            f"pages={stats['pages_fetched']}, products={stats['products_scanned']}, "
            f"en_found={stats['en_found']}. Check .debug/ HTML samples."
        )
        _sys.exit(1)

    # v5.4 invariant: muita página fetchada mas zero EN encontrado = scraper broken
    if stats["pages_fetched"] > 100 and stats["en_found"] == 0:
        log.error(
            f"❌ Invariant violation: {stats['pages_fetched']} páginas baixadas "
            f"mas {stats['en_found']} EN cards encontrados. Provável: selector "
            f"break, language detector quebrado, ou MYP rebuild. Check warnings."
        )
        _sys.exit(1)

    generate_xlsx(cards, output_path, MARGIN_THRESHOLD)
    print(f"\nDone! Open: {output_path}")
