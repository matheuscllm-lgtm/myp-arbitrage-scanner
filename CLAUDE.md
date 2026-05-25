# CLAUDE.md — MYP Arbitrage Scanner

Notas pra sessões Claude futuras trabalhando neste repo. Workflow patterns
descobertos em sessões anteriores que valem ser repetidos automaticamente.

## Workflow canônico: scan → summary → PSA triage

Quando o operador roda o MYP scanner (qualquer modo: principais, frequent-
deals, weekly full, ou filtrado), **se o scan produzir ≥3 deals** no sheet
`🔥 Deals`, **rode proativamente** o PSA triage logo após gerar o markdown
summary. Não pergunte — só rode e mostre o resultado.

```bash
# 1. Scan
python3 myp_arbitrage_scanner.py --editions <sets...> -o results/scan-XXXX.xlsx

# 2. Markdown summary (canônico)
python3 myp_summary.py results/scan-XXXX.xlsx -o results/manual-YYYY-MM-DD-<label>.md --type daily

# 3. PSA price triage — RODAR PROATIVAMENTE se Deals.rows ≥ 3
python3 scripts/scrape_pricecharting_psa.py results/scan-XXXX.xlsx

# 4. Commit ambos (summary md + psa-prices md) no mesmo commit ou em sequência
```

O xlsx é gitignored — só os .md vão pro commit.

## PriceCharting scraping — gotchas conhecidos

- **Use cloudscraper, não httpx/requests**. WebFetch e httpx default batem em
  403 no PriceCharting (anti-bot Cloudflare). Cloudscraper com
  `browser={"browser":"firefox","platform":"windows"}` passa — mesmo
  fingerprint que funciona pro MYP. Isso já está no `scripts/scrape_pricecharting_psa.py`.

- **Slug disambiguation por número.** Search `?q=...&type=prices` retorna
  links absolutos `https://www.pricecharting.com/game/...`. O PRIMEIRO hit
  NÃO é confiável — ranking prioriza popularidade. Sets novos (ex.: Ascended
  Heroes) sempre caem no Mega Gengar 284 sem filtro. Filtro correto: pegar
  slug cujo tail `-(\d+)$` casa com o número da carta (`lstrip('0')` em ambos
  pra `003` ≈ `3`).

- **Card name → search query mapping.** MYP frequentemente formata como
  `<PT> (NNN/MMM)<EN>` (ex.: `Mimikyu da Equipe Rocket (238/217)Team
  Rocket's Mimikyu`). Use a parte EN quando presente. Sem EN, aplicar
  `PT_EN_MAP` do script (`da Equipe Rocket → Team Rocket`, `do N → N's`,
  etc).

- **Set name keywords.** PriceCharting search é fuzzy — `<card_name>
  <set_kw>` casa bem. `EDITION_KEYWORDS` do script mapeia titles MYP
  (PT+EN concatenado) → keyword EN curta (`fogo fantasmagórico → Phantasmal
  Flames`, `equilíbrio perfeito → Perfect Order`).

## MYP scanner — gotchas

- **`*.xlsx` é gitignored** (`.gitignore` linha `*.xlsx`). Só comita os `.md`.

- **Background scans.** Scans completos levam 1-7h (depende do escopo).
  Rodar com `run_in_background=true`. NÃO usar sleep loops pra esperar —
  notificação async chega quando termina.

- **Versão atual do scanner: v5.8.7** (T1 fallback paginado, 2026-05-22).
  Resolve cards onde a tabela "demais vendedores" do MYP esconde EN-NM
  baratos atrás do cap de 20 sellers visíveis. Reduziu T1 truncation
  flagged de 19 → 7 num scan principais.

- **Quando T1 ainda dispara após o fallback v5.8.7**, é caso legítimo:
  marketplace foi paginado mas genuinamente não tem EN escondido. Não é
  bug — é estoque de fato pequeno (variants SIR de baixa liquidez).

## Branch convention

Esta repo usa branches `claude/<topic>-<6chars>` pra trabalho de sessões
Claude. Branch padrão da sessão atual sobrescreve qualquer convenção
local — sempre confira o git branch antes de criar commits novos.

## Próximos passos (backlog observado mas não pedido)

- **Folddown do cloudscraper no PSA-Arbitrage-Scanner.** PSA scanner usa
  httpx + CLAUDE.md menciona "curl_cffi if/when needed". Cloudscraper
  resolve PriceCharting hoje; vale folddown como adapter dedicado quando
  httpx começar a quebrar consistentemente.

- **Auto-cleanup do MYP Last Sale field.** TCG_SUSPECT_RATIO_THRESHOLD=10x
  pega Jirachi-style bugs mas alguns supranumerários SIR (Darumaka 2506%)
  também batem o threshold legitimamente — vale revisitar a regra pra não
  falsamente excluir SIR reais da Deals sheet. (Hoje vão pra Validate
  Manually corretamente — só seria upside pequeno.)
