# Experimental — prototype scripts

**Status:** exploratório, não-production. Scripts aqui são protótipos pra validar tese antes de virar feature first-class em outro repo.

## `ev_scanner_v01.py`

**Tese sendo testada:** raw→graded arbitrage. Vale comprar carta raw no MYP, gradar PSA, vender graded? Cálculo do EV considerando custos reais e probabilidade por grade.

**Fórmula:**
```
EV = Σ P(grade) × net_realiz(grade) − (buy_cost + submission_cost)
```

**Inputs:**
- `myp_arbitrage_*.xlsx` (output do scanner principal) — preços raw BR
- PriceCharting scrape — preços PSA 10/9/8/7 + raw (USD → BRL via live FX)
- PSA Pop Report — distribuição populacional por grade (manual fill por enquanto)
- Config tier PSA (Bulk Value $24.99 + intermediário BR + courier amortizado)

**Output:** sheet `💰 EV v0.1` no XLSX de input, com verdict por carta (STRONG_POSITIVE_EV, NEEDS_FAT_TAIL, NEGATIVE_EV, etc).

**FX automático:** fetch da AwesomeAPI bid no início do run; fallback open.er-api; fallback hardcoded.

**Pop fill:** `KNOWN_POP` dict tem cards manualmente verificados. Operador adiciona entries lendo psacard.com/pop/search.

**Limitações conhecidas:**
- 22 de 40 deals do último run retornam `PEND_PRICE_DATA` (PriceCharting search falha sem set canonical layer — Codex critique #4)
- Pop fill é manual; tentativa de scrape via cloudscraper/firecrawl bateu CF (RC-02 do PSA-Arbitrage-Scanner já documentou impossibilidade)
- Sell-side haircut 20% é estimativa; spread bid/ask real desconhecido
- Fail-grade haircut 50% sobre raw é conservador

## Por que aqui e não no PSA-Arbitrage-Scanner

Aquele repo está em Phase 6 com TDD estruturado (adapter PriceCharting sendo construído com fixtures reais). Adicionar prototype lá poluiria a arquitetura. Quando o adapter v1 deles estiver production-ready, este script vira a base do EV calculator first-class no PSA repo.

## Como rodar

```bash
cd C:/Users/mathe/myp-arbitrage-scanner
PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe experimental/ev_scanner_v01.py
```

Modifica em-place o XLSX `myp_arbitrage_*_weekly.xlsx` mais recente adicionando sheets `💰 EV v0.1` + `📝 EV Notes`.

## Histórico

- v0 (2026-05-15): break-even P(10) framing. SAFE_AT_PSA9 verdict assumindo PSA 9 é floor (errado — não pondera probabilidade).
- v0.1 (2026-05-16): grade-weighted EV via Pop Report. Codex review identificou 7 áreas (FX volatility, sell-side spread, etc).
- v0.1.1 (2026-05-16): live FX fetch (AwesomeAPI bid) substitui hardcode stale.
