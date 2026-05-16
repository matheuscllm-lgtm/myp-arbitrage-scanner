# SESSION HANDOFF — 2026-05-16 (consolidado)

> **Consolidação de duas sessões paralelas em 2026-05-15/16:**
> Sessão A (MYP Weekly Rescue) + Sessão B (EV Scanner v0.1 raw→graded).
> Próxima sessão lê este arquivo + memories listadas abaixo + ativa = continue.

---

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

## Commits desta janela (main)

| Commit | Sessão | Descrição |
|---|---|---|
| `30d1fc1` | B | experimental: EV scanner v0.1 + README + .gitignore |
| `6067fc5` | A | scripts/run_weekly_local.ps1 wrapper |
| `6aa624d` | A | **weekly-scan: cron auto REMOVIDO** |
| `0251139` | A | weekly-scan: bi-weekly → monthly (provisório) |
| `ee48b06` | A | weekly-scan: default chunk_total 6→20 |
| `90c2cf1` | B | results/weekly-2026-05-15.md (local aggregate) |

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
- [ ] **Bump CHANGELOG pra v5.7.2** (commits `ee48b06` + `6aa624d` mudaram comportamento sem versionar).

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

*Sessão fechada 2026-05-16 ~06:00 BRT. Branch `main` em sync com origin. Próximo deliverable depende de Pop fill manual ou decisão sobre canonical identity layer.*
