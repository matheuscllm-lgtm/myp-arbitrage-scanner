# SESSION-HANDOFF.md — handoff CANÔNICO (leia este)

> ⚠️ **Este é o ÚNICO handoff ativo do repo.** Nome fixo, a verdade mora no
> `main`. Qualquer sessão (Claude num terminal/web) que for retomar lê **este**
> arquivo. Não existe "qual handoff assumir" — é sempre este, no `main`.

## 📏 Regra pra sessões paralelas (o motivo desta seção existir)

Cada sessão web cria sua própria branch, então várias conversas rodam em
paralelo. Pra não virar bagunça de handoffs divergentes:

1. **Só há UM handoff ativo: este (`SESSION-HANDOFF.md`), no `main`.** NÃO crie
   `SESSION-HANDOFF-<data>.md` por sessão — é exatamente isso que gera o
   "não sei qual assumir".
2. **A verdade é o `main`.** Branch/PR aberta = *proposta*, não estado oficial.
3. Quem mergear pro `main` **atualiza este arquivo no mesmo PR**.
4. Se duas branches editarem este arquivo, o merge **conflita de propósito** —
   isso força consolidar em vez de divergir em silêncio.
5. `HANDOFF-*-<data>.md` e a seção `🗄️ HISTÓRICO` abaixo são **arquivo morto**
   (referência), não estado atual.

## ▶️ PRÓXIMO PASSO (faça isto primeiro)

**Estado em 2026-06-17 (fim do dia):** `main` está na **v5.13**. Mergeado nesta
sessão: **v5.12** (#40 — batch pokemontcg.io por set, `ptcg_calls` 16→0),
**v5.13** (#41 — Iteração #2: atribuição de cobertura do fallback em 4 baldes +
`bench.py` agora mede `deals`/`deals_clean`, não só velocidade) e **#39**
(gitignore `/_*.sh`). Daily scan completo do dia: 20/20 edições, 276 EN cards,
25 deals ≥30% (ver `results/daily-2026-06-17.md`).

### ⚙️ Modelo de ativação do scanner (LEIA — corrige doc anterior)

**O modelo PRINCIPAL é rodar o scanner LOCAL / no container** (sessão Claude Code
na nuvem ou PC local), via `myp_arbitrage_scanner.py` direto. **Não dependa dos
workflows do GitHub Actions** (`quick-scan.yml` / `daily-scan.yml`): eles só
rodam quando há **créditos de Actions disponíveis**, o que é **raro** — logo o
dispatch via Actions é um **fallback ocasional, NÃO o caminho preferido**.
(Qualquer doc dizendo "`quick-scan.yml` é o workflow preferido / `daily-scan.yml`
deprecado" está **errada** — corrigida aqui.)

- **Run local/container** (principal): single-session sequencial, ~2-2.5h pro
  conjunto largo. Use `--resume` (v5.11.4) em scans longos — o container é
  reciclado por inatividade e o checkpoint `.resume.json` retoma de onde parou.
  ⚠️ Mantenha a sessão "viva" durante o scan (ex.: um monitor/keep-alive ativo);
  processo background sem keep-alive pode ser ceifado pelo ambiente no meio
  (causa investigada e confirmada em 2026-06-17 — não é bug do scanner).
- **Workflow Actions** (fallback, só com créditos): `gh workflow run
  quick-scan.yml` distribui em runners com IP próprio (sem conflito de CF).

1. **`POKEMONTCG_API_KEY`** já setada no environment do Claude Code (toda sessão
   nasce com ela) e como secret de Actions (#30) — sleep adaptativo 0.3s ativo,
   sem 429. Nada a fazer.
2. **Próxima iteração do loop (v5.14, precisa de `--live`):** ler qual balde de
   `fallback_*` (v5.13) domina num scan ao vivo e fechar o maior FIXÁVEL —
   tipicamente `unmapped_set` (1 setcode em `MYP_EDITION_SUBSTR_TO_PTCG` cobre o
   set inteiro → preço real resolve → supranumerário/`tcg_suspect` encolhe por
   cobertura, não por threshold).

## 🧭 Meta / o que o projeto faz

MYP Arbitrage Scanner: compara preço de singles Pokémon **EN-NM** no
**mypcards.com** (Brasil) vs **TCG Player**, e lista cards onde MYP < TCG por
margem **≥30%** (arbitragem; default desde v5.10). Roda scans (daily/weekly),
gera resumo markdown em `results/`. O operador revisa os deals e opera os
**limpos** — os supranumerários (`card_num > set_total`) e TCG-suspect são quase
sempre artefato (`.estat-tcg` inflado), **validar manual antes de comprar**.

- Scanner canônico: `myp_arbitrage_scanner.py` (**v5.13** no `main`). Como rodar: `CLAUDE.md`.
- Resumo: `myp_summary.py` (entrega via ele é convenção OBRIGATÓRIA — #36). `.xlsx`
  é **gitignored** (só markdown entra no repo).

## 📋 Contexto desta sessão (2026-06-06)

Rodamos no **Claude Code web** (container efêmero, não o PC local). Descobertas:
- **O scanner roda na web sem CF 403** — a memória antiga dizia "datacenter IP =
  403"; **não vale mais** (scan de 3.124 produtos, 0 falhas, fingerprint firefox
  pega 200). Dá pra rodar scan real aqui.
- Daily Quick = **~2h41** single-session. Rodar em background; pedir o `.xlsx` no chat.
- **Sprawl:** cada sessão web cria 1 branch → tinha **5 PRs abertas** quase todas
  com scans redundantes + handoffs duplicados. Consolidado (ver PRs abaixo).

## ✅ Alterações desta sessão

1. **Scan Daily Quick 2026-06-05** (20 edições) → `results/daily-2026-06-05.md`. [#18]
2. **Fix top-50** no `myp_summary.py`: mostrava só top-15/10 e escondia deals →
   agora mostra todos. [#18]
3. **Portado** `results/daily-2026-06-04.md` da antiga #17. [#18]
4. **Handoff canônico** (este arquivo) + **regra anti-sprawl** + `CLAUDE.md`
   aponta pra ele. [#18]
5. **Cost gate v5.9.1** (PR #9 reescrita): não paginar truncation quando
   `TCG < min_price` (~85% menos requests, scan mais rápido). 13 testes offline
   ✓, smoke ao vivo ✓. [#9]
6. **Consolidação:** fechadas #7, #15, #17 (redundantes), com motivo em cada.

## 🔧 Correções feitas

- **Summary truncava deals** → top-50 em todas as categorias.
- **Ambiguidade de handoff** (vários por sessão) → 1 só canônico + regra.
- **PR #9 era reimplementação paralela** (core já no `main` via #13) → resetada
  pro `main` + só o cost gate único portado (sem rebase conflituoso). Usa
  `self.min_price` (per-instância) em vez do constante global.
- **Teste mal nomeado** ("cost gate" que testava o truncation gate) → relabel +
  teste de cost gate real adicionado.

## 📦 Resultado do scan 2026-06-05

204 EN cards · **31 deals ≥25%** (1 limpo: **Alakazam 003 = 31.1%**; 30
supranumerários; 3 TCG-suspect) · 0 truncation · 3.970 pages / 3.124 products /
702 seller-pages paginadas (0 falhas). Daily 06-04: 205 EN, 31 deals.

## 🗂️ Estado das PRs (pós-consolidação)

| PR | Status | Conteúdo |
|---|---|---|
| **#18** | open, **Ready** | daily 06-04/06-05 + top-50 + handoff canônico + regra |
| **#9** | open, **draft** | cost gate v5.9.1 (código, pra revisar) |
| #7 / #15 / #17 | 🔒 fechadas | redundantes (06-04 portado p/ #18 antes de fechar) |

---

# 🗄️ HISTÓRICO — frente EV scanner / MYP weekly (2026-05-16)

> Conteúdo abaixo é de sessões anteriores (EV scanner v0.1 + weekly rescue).
> Pendências P0–P4 e lições ainda podem valer; o **estado atual** está no topo.

## ✅ Entregas realizadas

### A) MYP Weekly Scan 2026-05-15

**XLSX entregue:** `C:\Users\mathe\myp-arbitrage-scanner\myp_arbitrage_20260515_weekly.xlsx` (150KB, **1260 cards EN**, 102 deals, +1 sheet EV nova)

| Sheet | Conteúdo | Hyperlinks |
|---|---|---|
| **💰 EV v0.1** | Análise raw→graded (sessão B) | Card Name → MYP · PriceCharting → site |
| 🔥 Deals | 102 cards margem ≥25% | Card Name → MYP |
| All EN Cards | 1260 rows | Card Name → MYP |
| 🏆 Top 50 Margin | Ranking pra triagem | Card Name → MYP |
| 🚨 Validate Manually | 17 cards SIR/HR + EN truncation | Card Name → MYP |
| 📝 EV Notes | Metodologia, config, instruções Pop fill | — |
| Summary | Estatísticas agregadas | — |

### B) EV Scanner v0.1 (commit `30d1fc1`)

Prototype raw→graded em `experimental/ev_scanner_v01.py`. Tese: comprar raw no MYP, gradar PSA, vender graded. EV = Σ P(grade) × net(grade) − (buy + submission).

**Resultado em 40 deals top-margem:**
- 1 STRONG_POSITIVE_EV (Jolteon Star, +86% EV, Pop manual validado)
- 17 PEND_POP_DATA (preço OK, Pop manual fill pendente)
- 22 PEND_PRICE_DATA (PriceCharting search falhou — canonical card identity gap)

### C) v5.8 — TCG Suspect end-to-end (PR #3, squash `e6b291c`)

Bug identificado no scan 2026-05-15: Jirachi PR-SM_SM161 aparecia como deal #1 a +1400% com TCG declarado R$1499 vs última venda real R$19,99 (75x off, `.estat-tcg` do MYP estava inflado). Heurística `tcg_suspect` já existia em `CardData` desde commit `0ca15d2` mas era invisível — não ia pro XLSX, não filtrava sheets, não aparecia no markdown.

**6 fixes:** scanner XLSX (+2 colunas, sheet 🚨 TCG Suspect, filtro em 🔥 Deals), aggregator preserva campos entre chunks, markdown summary com section dedicada, constante `TCG_SUSPECT_RATIO_THRESHOLD=10.0` extraída como single source of truth, `scripts/revalidate_deals.py` importa em vez de duplicar.

**Validação:** `test_v5_8_offline.py` (5 asserts, ~2s, zero rede) — passa green. Tentativa de validar em produção via Daily Quick Scan + GH Actions falhou (billing exhausted) e via este ambiente cloud falhou (CloudFlare 403 em IP de datacenter). Validação real de scraping (`.estatistica-ultimo` selector) acontece no weekly local de domingo 17/05 01:00 BRT — operador checa contador `🚨 TCG Suspects: N` no Summary do XLSX.

## Commits desta janela (main)

| Commit | Sessão | Descrição |
|---|---|---|
| `30d1fc1` | B | experimental: EV scanner v0.1 + README + .gitignore |
| `6067fc5` | A | scripts/run_weekly_local.ps1 wrapper |
| `6aa624d` | A | **weekly-scan: cron auto REMOVIDO** |
| `0251139` | A | weekly-scan: bi-weekly → monthly (provisório) |
| `ee48b06` | A | weekly-scan: default chunk_total 6→20 |
| `90c2cf1` | B | results/weekly-2026-05-15.md (local aggregate) |
| `f0e87f7` | C | scanner v5.8 H1 — detectar idioma via condição textual |
| `0ca15d2` | C | scanner v5.8 H2 — sanity check TCG vs última venda |
| `8578121` | C | ops: drop daily cron schedule (dispatch only) |
| `b6b61fc` | C | scanner v5.8 — surface tcg_suspect end-to-end |
| `e6b291c` | C | **PR #3 squash-merge (6 fixes + offline test)** |

## Modelo operacional atual

| Tipo | Onde | Quando | Custo |
|---|---|---|---|
| Daily Quick Scan | GitHub Actions | a cada 2 dias 10:00 BRT | ~150min/mês free |
| Weekly Full Scan | **PC local** (Task Scheduler) | domingo 01:00 BRT | $0 |
| Scans ad-hoc | local via `scripts/run_weekly_local.ps1` | sob demanda | $0 |
| Emergência | `workflow_dispatch` em weekly-scan.yml | só se PC fora | bate quota |
| EV scoring | local via `experimental/ev_scanner_v01.py` | manual (Q→A iteration) | $0 |

**Custo GitHub total:** ~$0/mês (consumo ~150min de 2000min). Quota exhaustion temporária pós-15/05 reseta 01/06.

---

## 🎯 Pendências (priorizadas — fazer próxima sessão)

### P0 — Operador-side (alto valor, sem dependência técnica)
- [ ] **Pop manual fill nos 17 PEND_POP_DATA** da sheet `💰 EV v0.1` (~3min/carta × 17 ≈ 50min). Procedimento: psacard.com/pop/search → "card_name + number" → "Show Population" → cola counts em Pop 10/9/8/7/≤6. Re-rodar `ev_scanner_v01.py` recalcula EV automaticamente.
- [ ] **Validar match top deals** abrindo URL PriceCharting da sheet — confirmar que matched é o card certo (especialmente Jolteon Star, M-Rayquaza-EX 098/98, Magikarp & Wailord-GX 551%).
- [ ] **Verificar GH billing** em https://github.com/settings/billing (informativo; não bloqueia operação).
- [ ] **Decidir PC ligado domingos à noite** — afeta Task Scheduler (task user-scope não acorda PC).

### P1 — Técnica (destrava mais sinal)
- [ ] **Canonical card identity layer** (Codex critique #4) → set slug map MYP↔PriceCharting↔PSA Pop. Destrava 22 PEND_PRICE_DATA. Eng 1-2 dias.
- [ ] **FX stress test** — rodar XLSX com FX 4,50 / 5,00 / 5,50; ver quais verdicts mudam.
- [x] ~~**Bump CHANGELOG pra v5.7.2**~~ — feito em 2026-05-16 junto com v5.8.

### P2 — Modelo (Codex critiques pendentes)
- [ ] **VaR / CVaR / P(loss > X)** — gating por bankroll, não só EV positivo
- [ ] **Break-even probability** complementar
- [ ] **Sell-side spread real** — substituir PriceCharting last sale por eBay sold-comp median net
- [ ] **Holding cost variável** — PSA Bulk turnaround 140-200 dias (não 7m fixo)
- [ ] **Fail-grade haircut** — testar 30/40/50/60% sobre raw, comparar verdicts

### P3 — Migração arquitetural
- [ ] **PSA-Arbitrage-Scanner Phase 6** está mid-flight com TDD próprio. Aguardar adapter PriceCharting v1 merge → **migrar EV calculator pra PSA repo** como feature first-class. NÃO duplicar trabalho até lá.
- [ ] PR #22 PSA ainda pendente
- [ ] Phase 7-A (CT_JWT) ainda aberta
- [ ] PriceCharting search robustness — parse list page → seguir 1º link (parcialmente feito; ~40% deals ainda falham)

### P4 — Investigação (não-prioritário)
- [ ] PSA Pop auto-scrape — CF block confirmado, requer headless Chrome. Postpone.
- [ ] GemRate / CardGrade como alternativa Pop (paid)
- [ ] Paralelismo local via subprocess (reduzir 6h → ~1h scan local)

---

## 📅 Próximo evento agendado

**Domingo 17/05/2026 às 01:00 BRT** — Task Scheduler dispara `run_weekly_local.ps1`. ETA término ~07:00 BRT. Arquivo em `C:\Users\mathe\Downloads\myp_weekly_*.xlsx` + `.log`.

---

## 🛠️ Comandos prontos

```powershell
# === MYP Weekly Local ===
schtasks /Run /TN "MYP_Weekly_Local_Scan"             # disparar manual
schtasks /Query /TN "MYP_Weekly_Local_Scan" /V /FO LIST  # status
schtasks /Change /TN "MYP_Weekly_Local_Scan" /DISABLE    # pausar

# === Scan targeted ===
cd C:\Users\mathe\myp-arbitrage-scanner
$env:PYTHONIOENCODING="utf-8"
python myp_arbitrage_scanner.py --editions "<edicao>" --threshold 25 `
  --output "C:\Users\mathe\Downloads\myp_targeted.xlsx"

# === EV Scanner v0.1 (após Pop fill manual) ===
cd C:\Users\mathe\myp-arbitrage-scanner
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe experimental\ev_scanner_v01.py
# → modifica em-place o myp_arbitrage_*.xlsx mais recente

# === Aggregate local (se CI falhar) ===
cd C:\Users\mathe\myp-rerun-20260515
gh run download <run_id> --repo matheuscllm-lgtm/myp-arbitrage-scanner --dir chunks/
cd C:\Users\mathe\myp-arbitrage-scanner
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe myp_aggregate.py `
  C:\Users\mathe\myp-rerun-20260515\chunks\myp-chunk-*\myp_chunk_*.xlsx `
  --output "myp_arbitrage_$(Get-Date -Format yyyyMMdd_HHmm).xlsx" `
  --threshold 0.25
```

---

## 💾 Memórias salvas (próxima sessão Claude lê auto)

**Sessão A (rescue):**
- `myp_weekly_chunk_sizing` — root cause chunk_total
- `gh_run_watch_rate_limit` — `gh run watch` tóxico em runs longos
- `gh_actions_billing_fallback` — recovery local aggregate
- `myp_operational_model_2026_05` — modelo novo
- `myp_local_task_scheduler` — setup Task Scheduler
- `session_log_2026_05_15_16_myp_weekly_rescue` — log consolidado

**Sessão B (EV scanner):**
- `session_2026_05_16_ev_scanner_v01` — log consolidado + 4 pendências top
- `fx_brl_usd_2026_05_16` — FX bid R$ 5,05 + live fetch obrigatório
- `feedback_xlsx_card_name_hyperlink` — preferência hyperlink Card Name
- `feedback_per_topic_review_save` — protocolo review+save por tópico
- `schedule_remote_vs_gh_actions` — desambiguação /schedule vs cron repo
- `gh_actions_quota_exhausted` (atualizado cross-scanner)

---

## 📖 Documentação canônica (vault Obsidian)

| Arquivo | Conteúdo |
|---|---|
| `MYP Cards Scan - 2026-05-15.md` | Sessão A completa + link Sessão B |
| `Grading & Authentication/EV Scanner v0.1 - Tese raw-to-graded - 2026-05-16.md` | Sessão B completa + Codex review + risk matrix |
| `MYP Arbitrage Scanner - Projeto.md` | Documentação geral do scanner (não tocado nesta sessão) |
| `METODOLOGIA-Scanners-TCG.md` | Metodologia cross-scanner (não tocado nesta sessão) |

---

## 🎓 Lições gravadas (não-óbvias)

### Da sessão A (rescue):
1. Default `chunk_total` precisa benchmark real, não chute (~7min/edição interleaved)
2. `gh run watch` (polling 3s) esgota rate limit GH API em ~25min — usar `sleep` + poll
3. GH Actions billing barra jobs individuais — chunks podem OK, aggregate (último) é barrado por quota
4. Aggregate local sempre viável (`myp_aggregate.py` é self-contained)
5. Modelo local-first elimina billing entirely, requer só PC ligado no horário

### Da sessão B (EV scanner):
6. **"MYP raw < TCG raw" é métrica errada** pra arbitragem raw→graded. EV = Σ P(grade) × net(grade) − costs é a métrica correta.
7. **PSA Pop puro tem viés de seleção** — só quem acha que tira nota alta submete. Usar como prior fraco, não engine.
8. **PSA submission cost $25 é só o PSA fee** — all-in BR (intermediário + courier + insurance + tax buffer) é ~R$300/card no Bulk Value.
9. **Sell-side haircut 20% é conservador padrão** (eBay 13% + payment 3% + FX 2% + ship 2%).
10. **FX hardcoded fica stale rápido** — diferença 5,80 vs 5,05 em 2 dias = 26pp no EV % final. Live fetch obrigatório.
11. **Fat-tail dependency é o risco oculto** — Jolteon Star tem +86% EV mas 45% vem de PSA 10 com 3,6% probabilidade. Sem PSA 10, EV cai pra +17%.
12. **Card identity matching é blocker arquitetural** — sem canonical layer, 55% dos deals falham scrape PriceCharting.

---

## 🚀 Como retomar (próxima sessão)

1. Ler este arquivo + `session_2026_05_16_ev_scanner_v01.md` + `session_log_2026_05_15_16_myp_weekly_rescue.md`
2. Verificar XLSX atual em `C:\Users\mathe\myp-arbitrage-scanner\myp_arbitrage_*_weekly.xlsx` (mais recente)
3. Verificar se operador já fez Pop fill manual (sheet `💰 EV v0.1` colunas Pop 10/9/8/7/≤6)
4. Se sim: re-rodar `experimental\ev_scanner_v01.py` pra recompute → mais STRONG_POSITIVE_EV deals esperados
5. Se não: avisar operador que P0 é Pop fill, OU avançar P1 (canonical identity layer)
6. Verificar status do weekly Domingo (se 17/05 já passou): `Get-ChildItem C:\Users\mathe\Downloads\myp_weekly_*.xlsx`

---

*Sessão fechada 2026-05-16 ~06:00 BRT. Re-aberta ~19:00 BRT (sessão C: v5.8 surfacing + offline test). Fechada 2026-05-16 ~21:30 BRT após merge PR #3. Branch `main` em sync com origin (commit `e6b291c`). Próximo deliverable: validar weekly local domingo 17/05 01h BRT (checar `🚨 TCG Suspects: N` no Summary do XLSX), depois Pop fill manual OU canonical identity layer.*
