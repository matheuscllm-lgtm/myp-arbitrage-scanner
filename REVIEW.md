# MYP Arbitrage Scanner v5.3 — Production Readiness Review

Reviewed: `C:\Users\mathe\myp-arbitrage-scanner\myp_arbitrage_scanner.py` (~825 lines)
Date: 2026-05-14
Reviewer focus: silent failures, scraping fragility, output correctness, operator visibility.

---

## CRITICAL (would burn the operator at 3am)

### C1. `MARGIN_THRESHOLD` reassignment at module bottom is a no-op for the scanner
**Confidence: 95** | File: `myp_arbitrage_scanner.py:810`

```python
MARGIN_THRESHOLD = args.threshold / 100
MIN_PRICE_BRL = args.min_price
```
These two lines rebind module-level names, but `MYPScraper.scan()` reads `MARGIN_THRESHOLD` and `MIN_PRICE_BRL` as **module globals from inside the class** (lines 534, 535, 582, 596, 602, 607, 462). At the moment those lines execute they look up the global at call-time — which works *only* because Python resolves them late. So this happens to work. **However,** `generate_xlsx` is called with `MARGIN_THRESHOLD` (line 820) — the *new* value — but the scan log lines 534/602 print `MARGIN_THRESHOLD*100`, which by that point is also the new value. OK so far.

**The actual bug:** `MIN_PRICE_BRL` is also reassigned (line 811) — but this is **after** `MYPScraper.__init__` already captured nothing from it (it's read inside `scrape_product` at line 462 as a global). That works. **But** `--min-price` default is `80` (line 791) and the global default is also `80.0` (line 86). If the operator passes `--min-price 150`, the rebind at line 811 *does* take effect. Good.

So this is fragile but functional. **Recommended fix:** pass `threshold` and `min_price` as constructor args to `MYPScraper` rather than relying on global rebinding. The current pattern silently breaks the moment someone refactors `scan()` into a method that captures globals at import time, or runs the scraper from another module that imports before CLI parsing.

**Severity downgrade:** Currently working. Flagged as a maintenance landmine, not an active bug.

---

### C2. `get_all_editions()` has a multi-strategy fallback that silently keeps going on broken HTML
**Confidence: 88** | File: `myp_arbitrage_scanner.py:222-249`

If Strategy 1 (`a.edicao-link`) and Strategy 2 (`[class*="edicao"]`) both fail and Strategy 3 finds *something* via the regex `^/pokemon/[a-z0-9][\w-]+$`, the scanner will happily proceed even if MYP changed their layout entirely and Strategy 3 is now matching an unrelated link pattern. The only loud signal is on **page 1 with zero matches** (line 247-248). On page 2+, a structural break produces a `break` and the scanner reports `Found N editions` where N is whatever it scraped before the break — silently truncated.

**Root cause:** `break` on line 249 exits the pagination loop without distinguishing "end of catalog" from "selectors broke mid-catalog."

**Suggested fix:** Track expected edition count (~326 per CLAUDE memory). If `len(editions) < 200` after a "natural" exit, log a CRITICAL warning that the catalog scrape may be incomplete. Or compare consecutive runs and alert on >20% drop in edition count.

---

### C3. Bare `except Exception` in `_get()` retry loop swallows ALL errors including `KeyboardInterrupt`-adjacent and programming bugs
**Confidence: 85** | File: `myp_arbitrage_scanner.py:181`

```python
except Exception as e:
    last_err = e
```
This catches `AttributeError`, `TypeError`, `MemoryError`, etc. — not just network errors. If `lxml` crashes on malformed HTML or `BeautifulSoup` raises on a parser bug, the scanner retries 3x, sleeps 6s total, then proceeds as if the page was empty. The product is silently skipped (`return None` on line 192), counted as `skipped_no_tcg_price`, and the operator sees no error.

**Suggested fix:** Catch only `requests.RequestException`, `cloudscraper.exceptions.CloudflareException`, `socket.timeout`, and `ConnectionError`. Let parser errors bubble up — those indicate a code bug or HTML format change worth crashing for.

---

## HIGH (real risk, operator should know)

### H1. Per-row language detection silently treats unknown languages as non-EN
**Confidence: 90** | File: `myp_arbitrage_scanner.py:399-415`

The flag-icon detector (line 401) returns `lang = title_val` from whatever attribute the page provides. The fallback list (lines 408-411) only contains 11 strings. If MYP adds a new language (e.g. `"Chinês"`, `"Tailandês"`) or changes the existing strings (`"Inglês "` with trailing space, `"english"` lowercase), every row gets dropped. The product is then skipped with `skipped_no_en_sellers++` — silently.

**Worst case:** MYP normalizes their flag titles (e.g. drops accents → `"Ingles"`), and the scanner reports zero deals for the entire run. The summary will show `EN cards found: 0` and the operator might assume "no opportunities this week."

**Suggested fix:** When `lang` is non-empty but doesn't match the EN set, increment a new counter `skipped_unknown_lang_titles` and log the unknown title once per run. The first occurrence of an unrecognized title should warn loudly.

---

### H2. Promo strikethrough fix uses LAST `R$` regex match — vulnerable to seller table layout changes
**Confidence: 87** | File: `myp_arbitrage_scanner.py:394-395`

```python
price_matches = re.findall(r'R\$\s*[\d.,]+', row_text)
row_price = self._parse_brl(price_matches[-1]) if price_matches else None
```

The fix correctly handles `"R$ 275,00 R$ 220,00"` (strikethrough → active). However, if MYP adds a *third* price element to the row — e.g., shipping cost (`"+ R$ 15,00 frete"`), seller credit, or a "you save" widget — `[-1]` will pick the wrong one. There's also no sanity check that the last price is *less than or equal to* the first (which would always be true for a legit promo).

**Suggested fix:**
```python
if len(price_matches) >= 2:
    candidates = [self._parse_brl(p) for p in price_matches]
    candidates = [c for c in candidates if c]
    row_price = min(candidates) if candidates else None  # promo = lowest visible
else:
    row_price = self._parse_brl(price_matches[0]) if price_matches else None
```
Min-of-prices is more defensible than last-of-prices. Add a debug log when `>2` matches found so the operator notices structural drift.

---

### H3. Pagination terminates on `new_count == 0` — masks duplicate-link bugs as "end of pagination"
**Confidence: 82** | File: `myp_arbitrage_scanner.py:296-322` and `211-290`

In both `get_edition_products` (line 318) and `get_all_editions` (line 288), the loop exits when no new URLs are found on a page. If MYP returns the same product list on page 2 due to a query parameter bug (e.g. `?page=` is silently ignored on overflow and returns page 1), the scanner thinks the edition has 1 page when it has 30. **Silent under-coverage.**

**Suggested fix:** Compare the first product URL of page N to page N-1. If identical, the site is returning the same page → log CRITICAL and stop. Otherwise the current `new_count == 0` test is too loose.

---

### H4. `get_all_editions()` has no `MAX_PAGES` guard — infinite loop possible
**Confidence: 88** | File: `myp_arbitrage_scanner.py:215`

`while True:` with `page += 1` and exit only on `not soup` (request fully failed) or `not links` (no selectors matched) or `found_on_page == 0`. If MYP ever returns "the same N edition links on every page past page X" and at least one is new each page (e.g. due to a broken caching layer recycling IDs), this loops forever. Compare to `get_edition_products` which at least caps at `MAX_PAGES_PER_EDITION = 30`.

**Suggested fix:** Add `MAX_EDITION_PAGES = 50` cap. With ~326 editions and typical 20/page pagination, ~17 pages is realistic. 50 is a generous safety net.

---

### H5. `--editions` filter silently produces zero results if none of the substrings match
**Confidence: 82** | File: `myp_arbitrage_scanner.py:543-556`

If the operator types `--editions "Ascendend Heroes"` (typo), the warning logs and returns `[]`. The main block then logs `"No English cards found"` (line 823). Two warnings, no error exit code. A CI cron job will report "success" with an empty XLSX (well — actually no XLSX, since `if cards:` guards it on line 819). But the GitHub Actions workflow won't fail loudly.

**Suggested fix:** If `--editions` is provided AND filtered result is empty, `sys.exit(2)` with a clear "no editions matched filter" message. Cron job will then send a failure notification.

---

### H6. `MARGIN_THRESHOLD` is read at multiple times during scan — one is module-default, others are CLI value
**Confidence: 85** | File: `myp_arbitrage_scanner.py:534, 582, 596, 602`

After CLI parsing reassigns `MARGIN_THRESHOLD = args.threshold / 100` (line 810), the global is updated. `scan()` reads it at line 534 (log header), line 582 (deal threshold), line 596 (deals filter), line 602 (deal count log). All four reads happen *after* the rebind because `scan()` is called on line 816, after line 810. So this works.

**However** — the docstring constant (line 85) `MARGIN_THRESHOLD = 0.25` is what gets used if anyone imports `MYPScraper` and calls `scan()` *without* going through `__main__`. Same issue as C1.

**Suggested fix:** Constructor param. See C1 fix.

---

## MEDIUM (worth fixing, low immediate risk)

### M1. Empty XLSX output when `cards == []` — operator gets no file at all
**Confidence: 80** | File: `myp_arbitrage_scanner.py:819-824`

```python
if cards:
    generate_xlsx(...)
else:
    log.warning("No English cards found...")
```

If a weekly cron returns zero results due to (a) site downtime, (b) selector breakage, (c) edition filter typo — the operator gets no XLSX and no email/notification (depending on how the cron is wired). Generate an empty XLSX with a "DIAGNOSTIC" sheet showing the funnel stats so the operator can distinguish "site healthy, no deals" from "scraper broken."

**Suggested fix:**
```python
if not cards:
    generate_diagnostic_xlsx(scraper._stats, output_path)
    log.warning("Empty result set — diagnostic XLSX written.")
    sys.exit(1)  # Non-zero exit so cron alerts
```

---

### M2. `re.search(r'pokemon_[a-z]{2,3}_[\w/]+', page_text)` for product code is greedy and may grab garbage
**Confidence: 80** | File: `myp_arbitrage_scanner.py:348`

`[\w/]+` is greedy and includes underscore + slash. If the page text has `pokemon_en_swsh1/100/random_other_text`, the match grabs everything until a non-word, non-slash boundary. This may not break anything (the field is informational only), but the `product_code` displayed to the operator could be polluted with adjacent template text.

**Suggested fix:** Bound it: `r'pokemon_[a-z]{2,3}_[\w]+(?:/\d+)?'` or limit to known patterns.

---

### M3. `Top 50 Margin` sheet sorts by `margin_pct or -999` — None values land at the bottom but no separation
**Confidence: 75** | File: `myp_arbitrage_scanner.py:707, 716`

`all_sorted` includes cards with `margin_pct = None` (sorted to bottom via `-999`). `top50 = all_sorted[:50]` will normally be fine because there are usually >50 cards with valid margins. But during a partial-failure scan with <50 valid cards, the sheet will include None-margin cards padded at the end. Visually confusing.

**Suggested fix:** `top50 = [c for c in all_sorted if c.margin_pct is not None][:50]`

---

### M4. `card.tcg_player_price` truthiness check accepts 0.0 as falsy — but `_parse_brl` already returns None for zero
**Confidence: 70** | File: `myp_arbitrage_scanner.py:357, 493`

Defensive logic is correct via `_parse_brl` returning `None` for `val <= 0` (line 206). However, in `generate_xlsx` line 660: `(card.tcg_player_price or 0)` — if a future change to `_parse_brl` allows 0, the diff calc silently treats missing price as 0. Low risk, but a tightening: use explicit `is None` checks throughout.

---

### M5. No timeout on the overall scan — could run 8+ hours and the operator has no progress ETA
**Confidence: 78** | File: `myp_arbitrage_scanner.py:561-593`

With `~326 editions × ~50 products × 1.5s delay = ~7 hours minimum`. The `Scanning N/M...` log every 10 products is helpful but there's no ETA, no global progress %, no time-elapsed reminder. For a weekly cron this is fine (cron has its own timeout). For an interactive run, the operator may not know if it's stuck.

**Suggested fix:** Log `"Edition X/Y complete | elapsed: Hh Mm | est remaining: Hh Mm"` after each edition.

---

## LOW (mostly polish)

- **L1** (line 91): `DEBUG_DIR` uses `Path(__file__).resolve().parent` — fails if script is invoked through `runpy` or `exec`. Acceptable for a CLI tool.
- **L2** (line 484-486): rarity_keywords list has overlap (`"Rara Hiper"` will also match if `"Rara"` comes first if order changed). Order-dependent. Currently ordered correctly (specific → general).
- **L3** (line 702, 719, 735): `auto_filter.ref` uses `max(N+1, 2)` — if `N == 0`, sets filter on row 2 of an empty sheet. Cosmetic only.
- **L4** (line 462): `MIN_PRICE_BRL` is read as a module global from inside an instance method. Accidental coupling but works.

---

## NOT FLAGGED (intentional design per operator)

- `--threshold < 1.0` auto-conversion (line 803-808) — operator confirmed intentional UX guard
- HTML scrape over public API — operator confirmed deliberate
- `--editions` substring match — operator confirmed
- Default threshold of 25 — operator's discovery preference

---

## Summary

**Most dangerous patterns:**
1. **Silent skips on parse failures** (C3, H1) — bare exception handling and unknown-language fallthrough turn structural breakage into "no deals this week"
2. **Pagination loop termination ambiguity** (C2, H3, H4) — "no new results" conflates end-of-data with bugs
3. **CLI exit code on empty results** (M1, H5) — cron job can't distinguish healthy zero from broken scraper

**Single highest-leverage fix:** Add a sanity check at scan completion that compares `pages_fetched` vs `products_scanned` vs `en_found` and raises `sys.exit(1)` if the funnel collapses (e.g. `pages_fetched > 100` but `en_found == 0`). This catches all silent-failure modes at once without changing the scraper logic.
