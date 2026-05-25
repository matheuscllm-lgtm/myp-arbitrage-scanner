# SESSION HANDOFF — 2026-05-22 → 2026-05-25

> Sessão de 3 dias cobrindo: 2 scans MYP, fix v5.8.7 do T1 truncation,
> integração nova com PriceCharting pra triagem PSA, e estabelecimento
> do workflow proativo "scan → summary → PSA triage" via CLAUDE.md.

**Branch:** `claude/myp-scanner-frequent-deals-6p1Li`
**PR:** [#7 — Ready for review](https://github.com/matheuscllm-lgtm/myp-arbitrage-scanner/pull/7)
**Commits totais:** 8

---

## ✅ Entregas realizadas

### 1. Scans MYP rodados

| Run | Data | Edições | Cards EN | Deals brutos | T1 flagged | Wall time | Output |
|---|---|---:|---:|---:|---:|---:|---|
| Frequent-deals (v5.8.6) | 22/05 | 10 | 113 | 15 | 11 | 57min | `manual-2026-05-22-4sets.md` |
| Principais default (v5.8.6) | 22/05 | 20 | 191 | 18 | 19 | 2h05 | `manual-2026-05-22-principais.md` |
| **Principais default (v5.8.7)** | 24-25/05 | 20 | 191 | **22** | **7** | 2h28 | `manual-2026-05-24-principais-v587.md` |

Comparação pós-fix v5.8.7 (mesma edição):
- **+4 deals descobertos** (18 → 22)
- **−12 T1 flagged** (19 → 7) — 93 cards tiveram lowest EN-NM corrigido pelo fallback paginado
- **+23min** wall time (overhead de 476 páginas extras do fallback)

### 2. Fix v5.8.7 — T1 fallback paginado (commit `59d8eaf`)

**Bug:** scanner reportava `lowest EN-NM` da tabela lojistas mesmo quando a
tabela "demais vendedores" (marketplace) tinha cap de 20 sellers sem nenhum
EN visível, escondendo EN-NM mais baratos atrás do cap. Caso disparador:
Psyduck (226/217) ME: Ascended Heroes — operador validou manualmente que
Deived1987 listava EN-NM a **R$340**, mas scanner reportava **R$519,90**
(única EN visível em lojistas). Margem fake −7,6% vs real +41,3%.

**Mecânica:** MYP pagina a tabela "demais vendedores" via
`?estoque-outros-page=N` (lojistas-certificados não pagina — cap estrutural
~15). Fallback detecta T1 truncation_risk → itera pgs 2..min(max,5) →
re-parseia EN-NM → atualiza `myp_lowest_en_nm` → limpa T1 quando achar.

**Mudanças no código:**
- Extraído `MYPScraper._parse_seller_table()` (per-row parsing antes inline)
- Novo `_fetch_demais_pages_for_en(soup, product_url)` com cap
  `MAX_DEMAIS_PAGES_FALLBACK = 5`
- Stats novos: `demais_pages_fetched`, `truncation_resolved_by_fallback`
- Header bump v5.8.6 → v5.8.7

**Validação E2E:** `/tmp/test_psa_v3.md` confirmou Psyduck R$519 → R$340.
**Validação em produção:** scan principais v5.8.7 resolveu 93 cards.

### 3. PSA price triage — `scripts/scrape_pricecharting_psa.py` (commits `226ef78`, `f07757e`)

Novo script que lê o xlsx do MYP scanner e cruza com PriceCharting pra
mostrar arbitragem MYP raw → PSA 9 / PSA 10. **Cloudscraper passa o
anti-bot do PriceCharting** (mesma config firefox/windows que uso pro MYP).

**Pipeline:**
1. Lê `🔥 Deals` do xlsx (opcional `--include-validate`)
2. Extrai card name EN + número do `Card Name` (MYP concatena `<PT> (NNN/MMM)<EN>` — usa EN quando presente, senão aplica `PT_EN_MAP`)
3. Mapeia edition MYP → keyword EN curta via `EDITION_KEYWORDS`
4. Search no PriceCharting via `search-products?q=...&type=prices`
5. **Filtra slug por tail-number** `-(NNN)$` — crítico, sem isso o ranking de popularidade joga todas as Ascended Heroes pro Mega Gengar 284
6. Parseia grade matrix (`info_box` td#used_price/graded_price/manual_only_price) + recent eBay sales `tr[id^=ebay-]`
7. Renderiza markdown: preços por grade + arbitragem com Diff PSA 9 + Diff PSA 10 + top picks net-positive

**Flags:**
- `--fx <X>` — BRL/USD (default 5.30)
- `--grading-cost <USD>` — pro cálculo de Diff (default 40)
- `--include-validate` — cobre 🚨 Validate Manually também
- `--delay <s>` — request delay (default 1.0)

**Output:** `results/psa-prices-YYYY-MM-DD.md` (3 sections: preços por grade,
arbitragem ranked por Diff PSA 9, top picks net-positive).

### 4. Workflow proativo — `CLAUDE.md` (commit `226ef78`)

Documenta gatilho automático pra futuras sessões: "quando scan produzir ≥3
deals em 🔥 Deals, rodar PSA triage logo após o markdown summary, sem
perguntar". Captura também os gotchas (cloudscraper > httpx pra PC, slug
por número, PT→EN do card name) pra ninguém redescobrir.

---

## 📊 Análise PSA atual @ US$50 grading

Operador definiu **US$50 como custo de submissão realista** (PSA Value
fee $25 + freight BR↔US estimado $25). Tabela filtrada para cards onde
`PSA 9 USD > MYP_USD + $50` (FX BRL/USD = 5.30):

| # | Carta | MYP R$ | MYP US$ | +$50 | PSA 9 | **Diff PSA 9** | PSA 10 | **Diff PSA 10** |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | **Meowth ex (121/088)** Equilíbrio Perfeito | R$800 | $150.94 | $200.94 | $303.49 | **+$102.55** | $1125.00 | **+$924.06** |
| 2 | **Psyduck (226/217)** ME: Ascended Heroes | R$340 | $64.15 | $114.15 | $185.50 | **+$71.35** | $700.00 | **+$585.85** |
| 3 | **Mega Feraligatr ex (274/217)** ME: Ascended Heroes | R$599 | $113.02 | $163.02 | $218.07 | **+$55.05** | $690.00 | **+$526.98** |
| 4 | **Mega Gengar ex (269/217)** ME: Ascended Heroes | R$335 | $63.21 | $113.21 | $152.50 | **+$39.29** | $520.40 | **+$407.19** |
| 5 | **Mega Dragonite ex (271/217)** ME: Ascended Heroes | R$210 | $39.60 | $89.60 | $117.75 | **+$28.15** | $390.00 | **+$300.40** |

Exatamente **5 cards** passam o filtro a US$50 (a US$40 eram 6 — Mimikyu
Team Rocket era +$6.47, agora vira −$3.53 e cai fora).

**Caveats:**
- Diff é bruto. Falta eBay fees (~13%) e tax → net realistic ≈ × 0.87
- Sem P(PSA 10) — precisa pop counts do PSA Pop Report pra decisão real
- 4 dos 5 são ME: Ascended Heroes (set 2026 recém-lançado) — preços PSA
  podem ser voláteis, pop pequena, flips iniciais podem inflar mediana
- Validar variant SIR/IR visualmente antes de operar (todos são
  supranumerários — número da carta > total do set)

---

## 📁 Arquivos commitados nesta sessão (PR #7)

| Path | Mudança |
|---|---|
| `myp_arbitrage_scanner.py` | Fix v5.8.7 + refactor `_parse_seller_table` + novo `_fetch_demais_pages_for_en` |
| `CHANGELOG.md` | Entrada v5.8.7 detalhada |
| `CLAUDE.md` | **NOVO** — workflow proativo + gotchas |
| `README.md` | Nova seção "PSA price triage (workflow pós-scan)" |
| `scripts/scrape_pricecharting_psa.py` | **NOVO** — triagem PSA via PC |
| `results/manual-2026-05-22-4sets.md` | Scan frequent-deals |
| `results/manual-2026-05-22-principais.md` | Scan principais v5.8.6 |
| `results/manual-2026-05-24-principais-v587.md` | Scan principais v5.8.7 (canonical) |
| `results/t1-fallback-validation-2026-05-24.md` | Validação 19 T1 cards |
| `results/psa-prices-2026-05-25.md` | Triagem PSA @ US$50 (canonical) |

---

## 🎓 Lições gravadas (não-óbvias)

1. **PriceCharting bloqueia httpx/requests/WebFetch com 403** (CF-style
   anti-bot). Cloudscraper firefox/windows passa — mesmo fingerprint que
   funciona pro MYP. PSA-Arbitrage-Scanner usa httpx + tem `curl_cffi`
   como "fallback if/when needed"; vale folddown do cloudscraper como
   adapter dedicado se httpx começar a quebrar consistentemente.

2. **Search-by-relevance do PriceCharting é traiçoeiro** em sets novos.
   "Mega Dragonite ex Ascended Heroes" sem filtro de número cai no Mega
   Gengar ex 284 (mais popular). Filtro por tail-number `-(NNN)$` do
   slug é obrigatório. `lstrip('0')` em ambos pra `003 ≈ 3`.

3. **T1 truncation é mais comum do que parece** — scan principais v5.8.7
   resolveu 93 cards em 191 (49%). Quase metade dos cards EN passa pela
   condição "marketplace cap atingido". Sem o fallback, scanner reportava
   preços inflados que mascaravam deals reais.

4. **MYP concatena PT+EN no Card Name** — formato `<PT> (NNN/MMM)<EN>`.
   Ex.: `Mimikyu da Equipe Rocket (238/217)Team Rocket's Mimikyu`. Usar
   parte EN quando presente é a forma confiável de gerar query EN-only
   pro PriceCharting (search EN funciona melhor que PT).

5. **Workflow pós-scan tem custo zero adicional via CLAUDE.md** — futuras
   sessões Claude leem automaticamente, rodam o pipeline completo (scan
   → summary → PSA triage) sem reorientação. Memoria institucional vive
   no repo, não no cliente.

6. **Custo de grading realista BR > US$25 PSA fee** — operador estimou
   US$50 (PSA Value + freight ida/volta). Pra realismo conservador maior
   (PSA Regular + insurance + return tax buffer), usar US$70. Cada
   incremento de US$10 derruba cards do limite top.

---

## 🚀 Como retomar próxima sessão

1. **Ler primeiro:** este arquivo + `CLAUDE.md` (workflow patterns) +
   `CHANGELOG.md` (versão atual v5.8.7).

2. **Status do PR #7:** Ready for review, esperando merge pra `main`.
   Quando mergear, próximas runs agendadas (`daily-scan.yml` 13:00 UTC
   alt days / `weekly-scan.yml` dias 1+15) começam a entregar com fix
   v5.8.7 automaticamente.

3. **Ações pendentes na ordem de prioridade:**
   - **(A)** Validar visualmente os 5 top picks PSA — confirmar que MYP
     listings são da variant SIR/IR correta (não a Comum). Listings: usar
     URLs do xlsx (`scan-principais-2026-05-24-v587.xlsx` sheet 🔥 Deals).
   - **(B)** Rodar `psa-arb analyze-live` no PSA-Arbitrage-Scanner pros
     top 3 (Meowth, Psyduck, Mega Feraligatr) com pop counts manuais
     de psacard.com/pop — daí sai decisão COMPRAR/NEGOCIAR/PEDIR_FOTOS
     com P(PSA 10) real.
   - **(C)** Considerar bump de `--grading-cost` pra 70 e re-rodar pra
     ver quantos passam o threshold mais conservador.

4. **Se for rodar novo scan:** o CLAUDE.md tem o pipeline padronizado.
   Comando canônico:
   ```bash
   python3 myp_arbitrage_scanner.py --editions <sets...> -o results/scan-<label>.xlsx
   python3 myp_summary.py results/scan-<label>.xlsx -o results/manual-<date>-<label>.md --type daily
   python3 scripts/scrape_pricecharting_psa.py results/scan-<label>.xlsx --grading-cost 50
   ```
   Commit os dois `.md` (xlsx é gitignored).

5. **Branches em outros repos do operador** (NÃO TOCADOS nesta sessão):
   `card-trader-scanner`, `oncology`, `PSA-Arbitrage-Scanner`,
   `scraping-tools`, `tcg-arbitrage-scanners` — todos têm a mesma branch
   `claude/myp-scanner-frequent-deals-6p1Li` configurada mas vazia.

---

## 🔗 Referências

- PR #7: https://github.com/matheuscllm-lgtm/myp-arbitrage-scanner/pull/7
- Commits chave (em ordem):
  - `c64da0b` — scan frequent-deals
  - `59d8eaf` — **feat v5.8.7 T1 fallback**
  - `d5a6e88` — scan principais v5.8.6 baseline
  - `65a8ec2` — validação 19 T1
  - `3f2aed8` — scan principais v5.8.7 (com fix)
  - `e1b2796` — PSA prices report inicial (ad-hoc)
  - `226ef78` — **feat scripts/scrape_pricecharting_psa.py + CLAUDE.md**
  - `f07757e` — feat PSA 10 + flag `--grading-cost`

---

*Sessão fechada 2026-05-25 ~03:30 UTC. PR #7 com 8 commits, ready for
review. Container do ambiente Claude Code on the Web é efêmero — toda
state durável vive no GitHub. Próxima sessão lê este arquivo + CLAUDE.md
pra continuar sem reorientação.*
