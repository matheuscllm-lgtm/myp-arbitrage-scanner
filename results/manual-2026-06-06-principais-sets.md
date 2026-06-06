---
tags: [tcg, scanner, myp, arbitrage, scan-manual]
date: 2026-06-06
type: manual
scope: principais-sets
source: local scan
---

# MYP Scan — Principais Sets (manual, local) — 2026-06-06

*Run manual local (v5.9) cobrindo os 9 filtros de "sets principais/hot" do daily
scan → **20 edições** casadas: todas as Mega Evolution (ME01–ME04, M2a, Brave,
Symphonia, Energy, Black Star Promos, JP Promos), ME: Ascended Heroes, SV: Black
Bolt (+SV11B), SV: White Flare (+SV11W), Destined Rivals, Journey Together,
Prismatic Evolutions, Surging Sparks e Stellar Crown. XLSX:
`results/principais-sets_2026-06-06.xlsx` (gitignored — só este resumo entra no
repo).*

**Cards EN escaneados:** 261 | **Deals (≥25%):** 27 | **Limpos:** 2 | **🚨 TCG suspects:** 2 | **Truncation:** 0

## Métricas do scan

| | |
|---|---:|
| Edições varridas | 20 |
| Produtos varridos | 3124 |
| Páginas HTTP buscadas | 4027 |
| Páginas de seller paginadas (v5.9) | 759 |
| Falhas de fetch de página | 0 |
| EN cards com preço | 261 |
| **🔥 Deals (≥25%) no XLSX** | **27** |
| **🟢 Deals limpos (sem flag VARIANT/suspect)** | **2** |
| Oversized collector# (VARIANT) | 243 |
| TCG suspects (.estat-tcg inflado) | 34 |
| Single-EN-seller risks | 84 |
| Skipped: sem TCG / sem EN / <R$50 | 418 / 736 / 1706 |
| Wall time | ~2h42 (17:59→20:42 UTC, delay 1.5s, single-session) |

> ⚠️ **Leitura rápida:** dos 27 deals do XLSX, só **2 são limpos** (Piplup e
> Alakazam, Mega Evolution Black Star Promos). O grosso são variants de
> collector# oversized (secret/illustration rares de Black Bolt/White Flare
> base-086 e Ascended base-217) onde o MYP marca rarity='Comum' mas o TCG
> reflete a variante cara → margens >200% são quase certamente artefato.
> **Validar visualmente variante + condição NM + idioma EN antes de operar.**

## 🟢 Top 15 deals limpos (sem flag SIR/HR/SAR)

| # | Carta | Edição | MYP R$ | TCG R$ | Margem | Lucro R$ |
|---|---|---|---:|---:|---:|---:|
| 1 | Piplup (042) | Mega Evolution: Series Black S | R$54,00 | R$75,15 | **39.2%** | R$21,15 |
| 2 | Alakazam (003) | Mega Evolution: Series Black S | R$80,00 | R$105,10 | **31.4%** | R$25,10 |

## ⚠️ Deals com flag supranumerário (validar manualmente)

> Cards com `card_num > set_total` aparecem como rarity='Comum' no MYP mas o TCG pode estar refletindo a variant secret/illustration rare. Margens absurdas (>200%) são quase certamente artefato. Não confiar sem validar.

| # | Carta | Edição | MYP R$ | TCG R$ | Margem (suspeita) |
|---|---|---|---:|---:|---:|
| 1 | Darumaka (097/086) | SV: Black Bolt | R$120,00 | R$2.867,75 | 2289.8% |
| 2 | Cubchoo (109/086) | SV: Black Bolt | R$95,00 | R$1.084,50 | 1041.6% |
| 3 | Simipour (102/086) | SV: Black Bolt | R$50,00 | R$331,70 | 563.4% |
| 4 | Sandile (135/086) | SV: Black Bolt | R$56,43 | R$309,00 | 447.6% |
| 5 | Jellicent ex (168/086) | SV: White Flare | R$195,00 | R$1.046,10 | 436.5% |
| 6 | Lampent (102/086) | SV: White Flare | R$100,00 | R$469,30 | 369.3% |
| 7 | Palpitoad (104/086) | SV: Black Bolt | R$60,00 | R$277,10 | 361.8% |
| 8 | Genesect ex (169/086) | SV: Black Bolt | R$340,00 | R$1.295,85 | 281.1% |
| 9 | Watchog (153/086) | SV: White Flare | R$50,00 | R$178,35 | 256.7% |
| 10 | Petilil (091/086) | SV: Black Bolt | R$50,00 | R$170,05 | 240.1% |

## 🚨 TCG Suspect (campo .estat-tcg inflado pelo MYP)

> Cards onde TCG declarado pelo MYP é >10x a última venda real do próprio MYP. Provável bug do `.estat-tcg`. Caso Jirachi PR-SM_SM161: MYP declarava R$1499 vs última venda R$19,99 (75x). Margens absurdas aqui são quase certamente artefato. **Já excluídos do Top 15 limpos**, listados aqui pra auditoria.

| # | Carta | Edição | MYP R$ | TCG decl R$ | Última venda R$ | Margem (fake) |
|---|---|---|---:|---:|---:|---:|
| 1 | Darumaka (097/086) | SV: Black Bolt | R$120,00 | R$2.867,75 | R$32,00 | 2289.8% |
| 2 | Cubchoo (109/086) | SV: Black Bolt | R$95,00 | R$1.084,50 | R$49,99 | 1041.6% |

---

*Gerado em 2026-06-06 20:43 UTC via `myp_summary.py` (single source: XLSX consolidado).*