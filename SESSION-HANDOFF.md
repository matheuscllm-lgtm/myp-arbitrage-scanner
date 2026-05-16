# SESSION HANDOFF — 2026-05-16 (fechamento)

## ✅ Entrega realizada

**XLSX:** `C:\Users\mathe\Downloads\myp_arbitrage_20260515_0922_LOCAL.xlsx` (152KB, 102 deals)

| Sheet | Conteúdo |
|---|---|
| 🔥 Deals | 102 cards margem ≥25% |
| All EN Cards | 1260 rows |
| 🏆 Top 50 Margin | Ranking pra triagem |
| 🚨 Validate Manually | 17 cards SIR/HR + EN truncation risk |
| Summary | Estatísticas agregadas |

## Mudanças aplicadas no repo

| Commit | Descrição |
|---|---|
| `ee48b06` | weekly-scan: default chunk_total 6→20 (resolve timeout) |
| `0251139` | weekly-scan: bi-weekly → monthly (provisório) |
| `6aa624d` | **weekly-scan: cron auto REMOVIDO** |
| `6067fc5` | scripts/run_weekly_local.ps1 wrapper |

## Modelo operacional atual

**Automação:**
- Daily Quick Scan: GitHub Actions a cada 2 dias (~150min/mês)
- Weekly Full Scan: **Windows Task Scheduler local** (`MYP_Weekly_Local_Scan`) domingo 01:00 BRT

**Sob demanda:**
- Scans ad-hoc: local via `scripts/run_weekly_local.ps1` ou comando direto
- Emergência: `workflow_dispatch` em weekly-scan.yml (preservado)

**Custo GitHub:** ~$0/mês (consumo ~150min de 2000min free tier).

## Pendências em aberto

- [ ] **Operador:** validar billing em https://github.com/settings/billing (informativo)
- [ ] **Operador:** decidir se PC fica ligado domingos à noite (afeta Task Scheduler — task user-scope não acorda PC do sleep)
- [ ] Bump CHANGELOG pra v5.7.2 (commits `ee48b06` + `6aa624d` mudaram comportamento sem versionar)
- [ ] Backlog: paralelismo local via subprocess (reduzir 6h → ~1h scan)

## Próximo evento agendado

**Domingo 17/05/2026 às 01:00 BRT** — Task Scheduler dispara `run_weekly_local.ps1`. ETA término ~07:00 BRT. Arquivo em `Downloads\myp_weekly_*.xlsx` + `.log`.

## Comandos de manutenção

```powershell
# Disparar weekly manual agora
schtasks /Run /TN "MYP_Weekly_Local_Scan"

# Status da task
schtasks /Query /TN "MYP_Weekly_Local_Scan" /V /FO LIST

# Pausar/reabilitar
schtasks /Change /TN "MYP_Weekly_Local_Scan" /DISABLE
schtasks /Change /TN "MYP_Weekly_Local_Scan" /ENABLE

# Scan targeted (edições específicas)
cd C:\Users\mathe\myp-arbitrage-scanner
$env:PYTHONIOENCODING="utf-8"
python myp_arbitrage_scanner.py --editions "<edicao>" --threshold 25 --output "C:\Users\mathe\Downloads\myp_targeted.xlsx"
```

## Memórias salvas (próxima sessão Claude lê automaticamente)

- `myp_weekly_chunk_sizing.md` — root cause + cálculo
- `gh_run_watch_rate_limit.md` — `gh run watch` é tóxico em runs longos
- `gh_actions_billing_fallback.md` — recovery quando aggregate GH falha por billing
- `myp_operational_model_2026_05.md` — modelo operacional novo
- `myp_local_task_scheduler.md` — setup completo do Task Scheduler
- `session_log_2026_05_15_16_myp_weekly_rescue.md` — log consolidado

## Lições gravadas

1. Default `chunk_total` precisa benchmark real, não chute (~7min/edição interleaved real, não 1.5s/produto raw)
2. `gh run watch` (polling 3s) esgota rate limit GH API em ~25min
3. GH Actions billing barra jobs individuais — chunks podem OK, aggregate (último) é barrado
4. Aggregate local sempre viável (myp_aggregate.py é self-contained)
5. Modelo local-first elimina billing entirely, requer só PC ligado no horário

---

*Sessão fechada 2026-05-16. Estado git: branch main, commits acima pushed. Vault Obsidian: `MYP Cards Scan - 2026-05-15.md`.*
