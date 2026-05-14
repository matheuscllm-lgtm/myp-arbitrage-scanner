# Changelog

## v5.4 — 2026-05-14 — Production hardening (code review fixes)

Code review formal pelo agente `pr-review-toolkit:code-reviewer` rodado pré-entrega
matinal de scanners funcionantes. 9 fixes aplicados (3 CRITICAL + 4 HIGH + 2 MEDIUM
+ 1 invariant). Foco: eliminar silent failure modes, dar exit codes claros pro cron.

### CRITICAL
- **C2 (catalog scrape sanity):** `get_all_editions()` agora warning loud se
  `len(editions) < MIN_EDITIONS_EXPECTED` (200). Esperado ~326. Floor previne
  Strategy 3 fallback truncar silenciosamente em mid-catalog selector breakage.
- **C3 (narrow exception):** `_get()` retry loop agora pega só
  `requests.RequestException`, `ConnectionError`, `TimeoutError`, `OSError`.
  Parser bugs (lxml/bs4), `AttributeError`, `MemoryError` etc propagam como
  crash — não viram silent skip + `skipped_no_tcg_price++`.

### HIGH
- **H1 (unknown language warn-once):** títulos de flag-icon fora de
  `KNOWN_LANGUAGES` (constante nova) agora são contados em
  `skipped_unknown_lang_titles` e logam warning na primeira ocorrência.
  Previne silent zero-deals se MYP normalizar `"Inglês"` → `"Ingles"`.
- **H2 (price min em vez de last):** strikethrough fix passa de `[-1]` pra
  `min(parsed_prices)`. Defensivo contra MYP injetar 3º R$ (frete, "you save").
  Debug log quando `>2` matches.
- **H3 (pagination loop detection):** `get_edition_products()` compara primeira
  URL de page N vs N-1. Iguais = MYP retornando mesma página → log loud + stop.
  Previne silent under-coverage por bug de query param.
- **H4 (MAX_EDITION_PAGES cap):** `get_all_editions()` agora capada em 50
  pages (era `while True:`). Atinge cap sem natural exit → warning.
- **H5 (filter typo exit):** `--editions` que não casa nada agora `sys.exit(2)`
  com mensagem clara. Cron job vai falhar visivelmente em vez de "success+empty".

### MEDIUM
- **M1 (empty result exit code):** runs com zero cards `sys.exit(1)`. CI distingue
  "scan saudável zero deals" (exit 0 com XLSX) de "scraper broken" (exit 1).
- **M3 (Top 50 sem padding None):** sheet `🏆 Top 50 Margin` filtra `margin_pct
  is not None` antes do slice. Evita padding visual em runs com <50 válidos.

### Invariant (single highest-leverage fix)
- **`pages_fetched > 100 and en_found == 0` → `sys.exit(1)`**. Catches todos
  os silent-failure modes ao mesmo tempo (selector break, language detector
  quebrado, MYP rebuild) sem precisar saber em qual etapa quebrou.

### Não aplicados (intencionalmente — flagged como maintenance landmines)
- **C1/H6 (`MARGIN_THRESHOLD` global rebind):** funciona por late-binding mas é
  fragile. Refator pra constructor param fica pra v6.0 (mudança maior de API).
- **M2 (regex `pokemon_[a-z]{2,3}_[\w/]+` greedy):** cosmetic, product_code
  é informational only.
- **M4 (zero-truthiness em `card.tcg_player_price or 0`):** `_parse_brl` já
  retorna None pra zero, defensive logic OK.
- **M5 (ETA logging):** nice-to-have, cron tem timeout próprio.
- **L1-L4:** polish only.

REVIEW.md no repo tem o relatório completo. Code review levou ~2min via agente.

## v5.3 — 2026-05-12

Refinamentos após caso Psyduck/bartsimpson revelar truncamento de seller table no MYP.

- **T1 (EN truncation flag):** novo campo `CardData.en_truncation_risk`. Parser itera por seller table individualmente (Tabela 0=lojistas/cap~15, Tabela 1=marketplace/cap~20). Heurística: dispara quando uma tabela está no cap (≥15 rows), com zero EN visível, e `max_price_visible < lowest_en_reported`. Evita false alarm quando max visível já está acima do lowest_en (hidden não pode quebrar).
- **H3 refinada:** agora também exige `card_num > set_total` quando o sufixo `(X/Y)` é extraível do nome — evita falso alarm em commons in-set caros.
- **Nova sheet `🚨 Validate Manually`** no xlsx: lista cards com `en_truncation_risk` pra punch-list de validação manual.
- **Nova coluna `⚠️ EN Trunc`** nas sheets de cards.
- **Novo stat counter** `en_truncation_risks` no summary final.
- **Bug fix: pricing promocional.** Rows com `R$ X (riscado) R$ Y` usavam X (preço antigo, mais caro) via `re.search`; agora `re.findall + [-1]` pega Y (preço ativo). Caso: MatchampTCG Psyduck "R$ 275,00 R$ 220,00" lido como R$275 quando deveria ser R$220.

## v5.2 — 2026-05-12

- **Default `--threshold` de 35 → 25** (mais discovery, menos filtragem).
- **Nova sheet `🏆 Top 50 Margin`** no xlsx: cards ordenados por margem desc sem filtro, pra inspeção visual chase-card.

## v5.1 — 2026-05-12

Auditoria C/H/M (mesma metodologia do scanner CT).

- **C1:** `--threshold < 1.0` auto-converte com warning (UX guard contra trap inverso ao CT scanner — MYP usa percent integer, CT usa fração).
- **H3:** detecção heurística SIR/HR/SAR — warning quando rarity="Comum" mas TCG price alto (>R$200). Reduz falso positivo documentado.
- **M1:** HTTP retry com backoff (3 tentativas, 2s→4s) em transient errors.
- **M4:** `debug_*.html` agora salvo em subpasta `.debug/` do script, não polui CWD.
- **M5:** novos stat counters (`skipped_no_tcg`, `skipped_no_en_sellers`, `skipped_low_price`) pra auditoria do funnel.

## v5 — 2026-04-15

Versão base. Scanner inicial com:
- Scrape mypcards.com via cloudscraper (CloudFlare bypass)
- Filtro EN-NM via flag-icon span
- Cálculo de margem vs TCGplayer reference price (BRL convertida no MYP)
- Output xlsx com 3 sheets (Deals, All EN Cards, Summary)
