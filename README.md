# MYP Arbitrage Scanner

Scanner de arbitragem que compara preços de singles Pokémon TCG (EN, Near Mint) no [mypcards.com](https://mypcards.com) contra a referência TCGplayer exibida na própria página do produto. Roda local ou no GitHub Actions (matrix paralelo) e gera planilha xlsx + summary markdown auto-commitado.

**TL;DR pra ver os últimos resultados sem instalar nada:**

- **Daily quick scan** (recente, hot sets): https://github.com/matheuscllm-lgtm/myp-arbitrage-scanner/blob/main/results/latest-daily.md
- **Weekly full scan** (catálogo completo): https://github.com/matheuscllm-lgtm/myp-arbitrage-scanner/blob/main/results/latest-weekly.md

GitHub renderiza markdown nativo — abre direto no celular ou desktop.

---

## Sumário

- [Como o scanner funciona](#como-o-scanner-funciona)
- [Setup local](#setup-local)
- [Rodar local](#rodar-local)
- [Flags do scanner (CLI)](#flags-do-scanner-cli)
- [GitHub Actions — workflows automatizados](#github-actions--workflows-automatizados)
- [Arquitetura: matrix job + aggregate](#arquitetura-matrix-job--aggregate)
- [Onde estão os resultados](#onde-estão-os-resultados)
- [Schedules e budget de CI minutes](#schedules-e-budget-de-ci-minutes)
- [Heurísticas defensivas](#heurísticas-defensivas)
- [Troubleshooting](#troubleshooting)
- [Por que NÃO usa a API pública do MYP](#por-que-não-usa-a-api-pública-do-myp)
- [Limitações conhecidas](#limitações-conhecidas)

---

## Como o scanner funciona

```
1. GET /pokemon/edicoes (paginação) → lista de ~348 edições
2. Filtragem por --editions substring (opcional)
3. Slicing por chunk (interleaved se chunk_total > 1)
4. Pra cada edição:
     GET /pokemon/edicao-X/?page=1..N → URLs de produtos
     Pra cada produto:
       GET /pokemon/produto/<id>/<slug>
       Parse 2 seller tables (lojistas ~15 rows + marketplace ~20 rows)
       Filtra <tr> por flag-icon[title=Inglês] + condition NM
       Extrai lowest EN-NM price + tcg_player reference
       Calcula margem (TCG - MYP_lowest_EN_NM) / MYP_lowest_EN_NM
5. Output: xlsx com 5 sheets + markdown summary
```

**Margem calculada:**
```
margem% = (TCG_player_price - MYP_lowest_EN_NM) / MYP_lowest_EN_NM
```
Não inclui: frete, taxas, markup de revenda, impostos. **Bruta, não líquida.**

---

## Setup local

Precisa de Python 3.10+ (testado em 3.12 e 3.14).

```bash
# Clonar repo
git clone https://github.com/matheuscllm-lgtm/myp-arbitrage-scanner.git
cd myp-arbitrage-scanner

# Criar venv (recomendado)
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Windows Git Bash / WSL:
.venv/Scripts/python -m pip install -r requirements.txt

# Linux/Mac:
source .venv/bin/activate
pip install -r requirements.txt
```

**Dependências** (`requirements.txt`):
- `cloudscraper>=1.2.71` — bypass do CloudFlare do MYP
- `beautifulsoup4>=4.12.0` + `lxml>=4.9.0` — parser HTML
- `openpyxl>=3.1.0` — geração de xlsx

**Sem secrets necessários** — MYP é scrape público, sem API key.

---

## Rodar local

### Encoding obrigatório no Windows
Scanner emite emojis no log (`🔥`, `⚠️`, `🚨`). Sem `PYTHONIOENCODING=utf-8`, falha com `UnicodeEncodeError` no Windows (cp1252 default).

```powershell
# PowerShell (uma vez por sessão):
$env:PYTHONIOENCODING = "utf-8"

# Bash:
export PYTHONIOENCODING=utf-8
```

### Comandos comuns

```bash
# Scan completo (todas edições, threshold 25%, ~7h)
python myp_arbitrage_scanner.py

# Scan rápido pra teste (3 edições, ~5min)
python myp_arbitrage_scanner.py --max-editions 3

# Scan filtrado em sets específicos (substring match)
python myp_arbitrage_scanner.py --editions "Ascended Heroes" "Black Bolt" "White Flare"

# Output customizado
python myp_arbitrage_scanner.py --editions "Prismatic" -o my_scan.xlsx

# Threshold mais permissivo (vê deals borderline)
python myp_arbitrage_scanner.py --threshold 15

# Delay maior se site instável (default 1.5s)
python myp_arbitrage_scanner.py --delay 3.0
```

### Smoke test rápido (1 minuto)

```bash
python myp_arbitrage_scanner.py --max-editions 1 --max-products 5
```

Se sai com erro, ver `.debug/debug_1.html` (página da catálogo de edições) pra diagnóstico.

---

## Flags do scanner (CLI)

| Flag | Default | Descrição |
|---|---|---|
| `--editions <substr>...` | (todas) | Substring match contra título da edição MYP. Ex.: `--editions Mega Ascended "Black Bolt"` |
| `--threshold <int>` | 25 | Margem mínima % pra alerta (`< 1.0` auto-converte com warning — convenção oposta do CT scanner) |
| `--min-price <float>` | 80 | Preço mínimo EN-NM em R$ pra incluir |
| `--delay <float>` | 1.5 | Segundos entre requests (aumentar se site instável) |
| `--max-editions <int>` | 0 | Limita número de edições processadas (debug; 0 = sem limite) |
| `--max-products <int>` | 0 | Limita produtos por edição (debug; 0 = sem limite) |
| `--chunk-index <int>` | 0 | (matrix) Índice deste chunk (0-based). Usado com `--chunk-total`. |
| `--chunk-total <int>` | 1 | (matrix) Total de chunks. `editions[N::M]` interleaved slicing. |
| `-o`, `--output <path>` | timestamp auto | Caminho do xlsx de saída |

**Exit codes:**

| Code | Significado |
|---|---|
| 0 | Healthy run (com ou sem deals; ou chunk vazio legítimo) |
| 1 | Scraper provavelmente quebrado (zero cards OU `pages>100 AND en_found==0` invariant) |
| 2 | `--editions` filter não casou nenhuma edição (typo no operador) |

### Output: 5 sheets no xlsx

| Sheet | Conteúdo |
|---|---|
| 🔥 Deals | Cards com margem ≥ threshold, ordenados desc |
| All EN Cards | Todos cards EN-NM encontrados, ordenados por margem desc |
| 🏆 Top 50 Margin | Top 50 por margem sem filtro — pool visual chase-card |
| 🚨 Validate Manually | Cards com flag `en_truncation_risk` |
| Summary | Métricas (pages, deals, skips, warnings) |

---

## GitHub Actions — workflows automatizados

Dois workflows independentes, ambos usam matrix job + aggregate (ver [Arquitetura](#arquitetura-matrix-job--aggregate)):

### 1. `daily-scan.yml` — Daily Quick Scan

Foco em sets hot/recentes onde preços se movem mais.

| Aspecto | Valor |
|---|---|
| **Cron** | `0 13 */2 * *` (a cada 2 dias, 13:00 UTC = 10:00 BRT) |
| **Default editions** | `Mega Ascended "Black Bolt" "White Flare" "Destined Rivals" "Journey Together" "Surging Sparks" "Stellar Crown" Prismatic` |
| **Chunks paralelos** | 2 |
| **Wall time** | ~15-25 min |
| **Timeout/chunk** | 60 min |
| **Retention artifact** | 14 dias |
| **Concurrency group** | `myp-scan-daily` (independente do weekly) |

### 2. `weekly-scan.yml` — Weekly Full Scan

Catálogo completo, sem filtro.

| Aspecto | Valor |
|---|---|
| **Cron** | `0 12 1,15 * *` (dias 1 e 15 do mês, 12:00 UTC = 09:00 BRT) |
| **Default editions** | (todas as ~348) |
| **Chunks paralelos** | 6 |
| **Wall time** | ~75 min |
| **Timeout/chunk** | 120 min |
| **Retention artifact** | 30 dias |
| **Concurrency group** | `myp-scan` |

### Como triggar manualmente

**Via GitHub UI:**
1. https://github.com/matheuscllm-lgtm/myp-arbitrage-scanner/actions
2. Clica em "Daily MYP Quick Scan" ou "Weekly MYP Scan" no menu lateral
3. "Run workflow" (botão direito)
4. Preenche os inputs (todos opcionais — defaults são sensíveis)
5. "Run workflow" verde

**Via gh CLI:**

```bash
# Daily com defaults
gh workflow run daily-scan.yml --repo matheuscllm-lgtm/myp-arbitrage-scanner

# Weekly com defaults
gh workflow run weekly-scan.yml --repo matheuscllm-lgtm/myp-arbitrage-scanner

# Daily customizado (só Ascended, threshold 30%)
gh workflow run daily-scan.yml --repo matheuscllm-lgtm/myp-arbitrage-scanner \
  -f editions="Ascended" \
  -f threshold=30 \
  -f chunk_total=2

# Weekly com 12 chunks paralelos (mais rápido, mais minutos)
gh workflow run weekly-scan.yml --repo matheuscllm-lgtm/myp-arbitrage-scanner \
  -f chunk_total=12

# Smoke test mínimo (3 chunks, só Ascended → 1 chunk trabalha, 2 vazios)
gh workflow run weekly-scan.yml --repo matheuscllm-lgtm/myp-arbitrage-scanner \
  -f editions="Ascended" \
  -f chunk_total=3
```

### Inputs aceitos (workflow_dispatch)

**Daily:**
| Input | Default | Notas |
|---|---|---|
| `editions` | (9 substrings hot sets) | Substrings separadas por espaço; `"x y"` agrupa |
| `threshold` | `25` | Percent integer |
| `min_price` | `50` | BRL (piso padrão cross-scanner: carta valiosa = > R$50) |
| `delay` | `1.5` | Segundos entre requests |
| `chunk_total` | `2` | Cap 1-20 |

**Weekly:**
| Input | Default | Notas |
|---|---|---|
| `editions` | (vazio = todas) | |
| `threshold` | `25` | |
| `min_price` | `50` | BRL (piso padrão: > R$50) |
| `delay` | `1.5` | |
| `chunk_total` | `6` | Cap 1-20 |

### Acompanhar uma run

```bash
# Listar últimas runs
gh run list --repo matheuscllm-lgtm/myp-arbitrage-scanner --limit 5

# Ver status de run específica
gh run view <run-id> --repo matheuscllm-lgtm/myp-arbitrage-scanner

# Acompanhar em tempo real até finalizar
gh run watch <run-id> --repo matheuscllm-lgtm/myp-arbitrage-scanner

# Baixar artifacts (xlsx + .debug)
gh run download <run-id> --repo matheuscllm-lgtm/myp-arbitrage-scanner

# Baixar só o consolidated (sem chunks individuais)
gh run download <run-id> --repo matheuscllm-lgtm/myp-arbitrage-scanner \
  -n myp-scan-consolidated-<run-id>     # weekly
gh run download <run-id> --repo matheuscllm-lgtm/myp-arbitrage-scanner \
  -n myp-daily-consolidated-<run-id>    # daily

# Ver log completo (depois de completar)
gh run view --job=<job-id> --repo matheuscllm-lgtm/myp-arbitrage-scanner --log
```

---

## Arquitetura: matrix job + aggregate

Full scan single-thread = ~7h (348 editions × ~50 prods × 1.5s delay), não cabe em job único do GitHub Actions (limite 6h). Solução: **matrix paralelo + aggregator**.

### Os 3 jobs por run

```
┌─────────────────┐
│  1. plan        │  Computa N chunks baseado em chunk_total input
│  (Ubuntu, ~5s)  │  Output: chunk_indices=[0,1,2,3,4,5]
└────────┬────────┘
         │
         ▼ matrix expand
┌─────────────────────────────────────────────────────────────┐
│  2. scan (matrix, fail-fast: false)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ... ┌──────────┐    │
│  │ chunk 0  │ │ chunk 1  │ │ chunk 2  │     │ chunk N  │    │
│  │ ~70min   │ │ ~70min   │ │ ~70min   │     │ ~70min   │    │
│  └──────────┘ └──────────┘ └──────────┘     └──────────┘    │
│  Cada chunk: editions[N::M] interleaved (load balanced),    │
│  scan, gera myp_chunk_N.xlsx, upload como artifact          │
│  myp-chunk-N (weekly) ou myp-daily-chunk-N (daily)          │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼ if always() && != cancelled
┌─────────────────┐
│  3. aggregate   │  Baixa todos artifacts via merge-multiple
│  (Ubuntu, ~30s) │  Roda myp_aggregate.py chunks/myp_chunk_*.xlsx
│                 │  Gera xlsx final consolidado
│                 │  Gera markdown summary via myp_summary.py
│                 │  Commita results/{daily,weekly}-DATE.md
│                 │  Upload xlsx final como artifact
└─────────────────┘
```

### Por que interleaved slicing (não sequential blocks)?

Edições têm tamanhos muito diferentes (5 a 226 produtos). Sequential blocks (`editions[0:58]`, `editions[58:116]`...) concentraria todas as massivas num único chunk → load desbalanceado.

Interleaved (`editions[0::6]`, `editions[1::6]`, `editions[2::6]`...) distribui edições alternadamente, balanceando carga.

### Aggregator (`myp_aggregate.py`)

- Lê todos os `myp_chunk_*.xlsx` recebidos
- Reconstrói `CardData` da sheet `All EN Cards` de cada um
- Dedupe defensivo por `product_url` (não deveria haver duplicata em interleaved, mas garante)
- Reusa `generate_xlsx` do scanner (single source of truth pro formato)
- Output: xlsx idêntico a um scan single-thread

### Empty chunk handling

Se `--editions` filtrar pra menos edições que `chunk_total` (ex.: 1 edição com 6 chunks), os chunks vazios saem com **exit 0** + log explícito `Chunk N/M vazio após slicing` em vez de marcar o job como falha. Aggregate ignora chunks sem xlsx.

---

## Onde estão os resultados

Cada scan deixa o resultado em **3 lugares**:

### 1. Markdown summary no repo (visível direto no browser)

Após cada scan, o aggregate job gera markdown summary e commita em:
- `results/latest-daily.md` ← ponteiro pro último daily
- `results/latest-weekly.md` ← ponteiro pro último weekly
- `results/daily-YYYY-MM-DD.md` ← histórico de cada daily
- `results/weekly-YYYY-MM-DD.md` ← histórico de cada weekly

**Acesso direto** (GitHub renderiza markdown nativo):
- https://github.com/matheuscllm-lgtm/myp-arbitrage-scanner/blob/main/results/latest-daily.md
- https://github.com/matheuscllm-lgtm/myp-arbitrage-scanner/blob/main/results/latest-weekly.md

**Conteúdo do markdown:**
- Frontmatter Obsidian (tags, date, type) — já formatado pra vault
- Stats (cards EN, deals, threshold, truncations)
- Top 15 deals **limpos** (sem flag SIR/HR/SAR — confiáveis)
- Top 10 deals **supranumerários** (margem suspeita, validar manual)
- EN truncation risks
- Link pro artifact xlsx (se quiser detalhe)

### 2. XLSX consolidado (artifact do GH Actions)

Disponível por 14-30 dias após cada run.

```bash
gh run download <run-id> --repo matheuscllm-lgtm/myp-arbitrage-scanner
```

### 3. Local (se rodou local)

Arquivo `myp_arbitrage_YYYYMMDD_HHMM.xlsx` na CWD ou no path do `-o`.

---

## Schedules e budget de CI minutes

GitHub Actions cobra **minutos de execução** em repos privados. Plan free = 2.000 min/mês.

| Workflow | Cron | Cadência | Wall | Min/run | Runs/mês | Min/mês |
|---|---|---|---|---|---|---|
| Daily quick | `0 13 */2 * *` | a cada 2 dias 10 BRT | ~20min | ~30 | ~15 | **~450** |
| Weekly full | `0 12 1,15 * *` | dias 1 e 15 do mês 09 BRT | ~75min | ~420 | 2 | **~840** |
| | | | | | **TOTAL** | **~1.290** |

Sobra ~700 min/mês pra triggers manuais, smoke tests e re-runs em caso de falha.

**Cuidado:** rodar weekly toda semana (4×/mês) explodiria o budget pra ~2.580 min — acima do free tier. Por isso bi-weekly.

---

## Heurísticas defensivas

### H3 — Supranumerário rarity mismatch

Cards com `card_num > set_total` (ex.: `226/217`) frequentemente são variantes IR/SIR/SAR misclassificadas como "Comum" no MYP. Quando rarity=Comum/Incomum + TCG>R$200 + supranumerário, emite warning. Reduz falso positivo em cross-variant mismatch (regular vs raro).

### T1 — EN truncation risk

Página do produto MYP tem 2 seller tables (lojistas ~15 + marketplace ~20), ordenadas por preço asc agnóstico de idioma. Quando uma tabela atinge cap sem nenhuma listing EN visível **E** o `max_price` visível < `lowest_EN` reportado, há risco de listings EN-NM escondidos serem mais baratos.

Caso concreto: Psyduck (226/217) ME:AH — scanner reportou R$415 lowest EN-NM, seller "bartsimpson" tinha o mesmo card a R$300 EN-NM truncado por 20 listings PT/JP.

### v5.4 invariants (production hardening)

- `MIN_EDITIONS_EXPECTED = 200`: catalog scrape de menos editions = warning loud (esperado ~348)
- `MAX_EDITION_PAGES = 50`: cap em `get_all_editions` previne infinite loop
- `KNOWN_LANGUAGES`: títulos de flag-icon fora dessa lista contam pra `skipped_unknown_lang_titles` + warn-once (previne silent zero-deals se MYP renomear `"Inglês"` → `"Ingles"`)
- Pagination loop detection: page N retornar mesma primeira URL de page N-1 = loud stop
- `--editions` typo → `sys.exit(2)` (cron job falha visivelmente)
- Invariant: `pages_fetched > 100 AND en_found == 0 → sys.exit(1)` (catches todos silent failures)

---

## Troubleshooting

### `UnicodeEncodeError: 'charmap' codec can't encode character '✅'` no Windows

Falta `PYTHONIOENCODING=utf-8`. Ver [Encoding](#encoding-obrigatório-no-windows).

### `403 Forbidden` ou `cloudflare` no log

Site bloqueando scraper. Tentativas:
1. Aumentar delay: `--delay 3.0`
2. Verificar se `cloudscraper` está instalado e atualizado: `pip install -U cloudscraper`
3. Se persistente, MYP pode ter atualizado proteção CloudFlare — atualizar `cloudscraper`

### Workflow GH Actions falha com timeout

Wall time excedeu `timeout-minutes`. Opções:
1. Aumentar `chunk_total` no input (mais paralelismo, menos work por chunk)
2. Reduzir escopo via `--editions` filter
3. Verificar se MYP está respondendo lento (delay 1.5s pode estar aplicando 3-4s real)

### `0 deals encontrados` num scan que historicamente tinha deals

Provável: heurística defensiva disparou. Checar log:
- "Catalog scrape suspeito: <200 editions" → MYP mudou layout, atualizar selectors
- "Idioma desconhecido detectado: 'X'" → MYP renomeou flag-icon title; adicionar a `KNOWN_LANGUAGES`
- "Pagination loop detectado" → MYP retornando page 1 quando page=N (servidor degradado)

### Markdown summary não aparece em `results/`

Aggregate job pode ter falhado. Verificar:
1. `permissions: contents: write` está no workflow yaml
2. Step "Commit markdown to repo" não foi pulado por `git diff --cached --quiet` (= conteúdo idêntico ao último, sem mudança)
3. Logs do step "Generate markdown summary" — `myp_summary.py` falhou?

### `myp_aggregate.py` reporta zero cards consolidados

Algum chunk produziu xlsx mas com sheet `All EN Cards` vazia, OU nenhum chunk produziu xlsx. Checar:
1. Logs dos chunks individuais — algum failure?
2. Empty chunk legítimo deveria sair com exit 0 mas SEM xlsx; aggregate ignora
3. Se TODOS chunks empty, é bug — provavelmente filter `--editions` não casou nada

---

## Por que NÃO usa a API pública do MYP

A MYP tem REST API em `https://mypcards.com/api/v1` (descoberta 2026-05-07, sem auth, OpenAPI 3.1). Schema `Produto` retorna `min_price`, `avg_price`, `max_price` em BRL agregados + `tcg_price` USD da TCGPlayer.

**Vício:** preços agregados (`min_price` etc.) **misturam todas as línguas** (PT + JP + EN + IT + ES + ...) num campo único. Não há filtro `?language=en` no servidor. Pra arbitragem EN-NM (que vendemos no TCGPlayer), o `min_price` pode estar refletindo uma listing PT/JP irrelevante.

**Sintoma real (2026-05-07):** Terapagos ex scr 170 — API mostrou R$100 floor com 14 listings. HTML scrape confirmou: **0 EN, 13 PT**. Sem o scrape, teríamos cancelado R$580 de deals válidos do CT achando que MYP dominava.

**Bonus quirk — apostrophe bug:** endpoint `/carta/{nome}` retorna HTTP 200 + cards vazios pra nomes com `'`. Cards "Team Rocket's X", "N's Plan", "Lillie's X", "Morty's X" não retornam match mesmo existindo. Workaround: URL-encode `%27` ou skip via pattern.

**Por isso este scanner vai direto no HTML scrape per-product:**
- Parser pega cada `<tr>` da seller table
- Lê `flag-icon[title]` pra detectar idioma
- Filtra `Inglês` + `NM`
- Ground truth por listing — API não substitui

**Quando a API ainda é útil (em ferramenta separada):**
- Cross-reference rápido de 1 card CT contra MYP (lookup pontual em ~1s)
- Pre-filtro pra batch grande (200+ deals) antes de targeted scrape

---

## Limitações conhecidas

- **Truncamento de sellers**: MYP não expõe paginação per-language no rendered HTML. Cards com flag T1 indicam onde isso provavelmente acontece, mas o scanner não lista os sellers truncados — validação manual via perfil de seller é necessária.
- **Tempo de scan**: ~16 produtos/min com delay 1.5s. 2.000+ produtos = ~2h. Catálogo total ~16k produtos = ~7h (motivo do matrix job).
- **Margem bruta, não líquida**: frete + taxas + impostos não aplicados. Pra arbitragem real, descontar manualmente.
- **Reproducibilidade**: depende de listings ativos no momento do scan. Snapshots variam entre runs.

---

## Histórico de versões

Ver `CHANGELOG.md` no repo. Marcos:

- **v5.0** (2026-04-15): primeira versão production
- **v5.1** (2026-05-12): 5 fixes C/H/M (auditoria)
- **v5.2** (2026-05-12): default threshold 35→25, sheet `🏆 Top 50 Margin`
- **v5.3** (2026-05-12): EN truncation flag T1, sheet `🚨 Validate Manually`, bugfix promo strikethrough
- **v5.4** (2026-05-14): production hardening pós code review formal — 9 fixes (catalog sanity floor, narrow exception, KNOWN_LANGUAGES warn-once, price min(), pagination loop detection, MAX_EDITION_PAGES, --editions exit code, zero cards exit, Top 50 None filter, scan invariant)
- **v5.5** (2026-05-14): matrix job + aggregation (resolve timeouts de 5h+)
- **v5.5.1** (2026-05-14): empty chunk legitimacy (exit 0 quando slicing deixa chunk vazio)
- **v5.6** (2026-05-14): markdown summary auto-commit no `results/` folder

---

## Author

Matheus Chillemi
