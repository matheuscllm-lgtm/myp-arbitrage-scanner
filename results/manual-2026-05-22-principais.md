---
tags: [tcg, scanner, myp, arbitrage, scan-daily]
date: 2026-05-24
type: daily
source: local scan
---

# MYP Scan Daily Quick — 2026-05-24

**Cards EN escaneados:** 191 | **Deals (≥25%):** 9 | **Limpos:** 1 | **🚨 TCG suspects:** 2 | **Truncation:** 19

## 🟢 Top 15 deals limpos (sem flag SIR/HR/SAR)

| # | Carta | Edição | MYP R$ | TCG R$ | Margem | Lucro R$ |
|---|---|---|---:|---:|---:|---:|
| 1 | Alakazam (003) | Mega Evolution: Series Black S | R$80,00 | R$101,60 | **27.0%** | R$21,60 |

## ⚠️ Deals com flag supranumerário (validar manualmente)

> Cards com `card_num > set_total` aparecem como rarity='Comum' no MYP mas o TCG pode estar refletindo a variant secret/illustration rare. Margens absurdas (>200%) são quase certamente artefato. Não confiar sem validar.

| # | Carta | Edição | MYP R$ | TCG R$ | Margem (suspeita) |
|---|---|---|---:|---:|---:|
| 1 | Darumaka (097/086) | SV: Black Bolt | R$99,99 | R$2.605,80 | 2506.1% |
| 2 | Cubchoo (109/086) | SV: Black Bolt | R$95,00 | R$893,55 | 840.6% |
| 3 | Jellicent ex (168/086) | SV: White Flare | R$195,00 | R$1.014,75 | 420.4% |
| 4 | Genesect ex (169/086) | SV: Black Bolt | R$340,00 | R$1.240,60 | 264.9% |
| 5 | Excadrill ex (168/086) | SV: Black Bolt | R$140,00 | R$386,65 | 176.2% |
| 6 | Sandile (135/086) | SV: Black Bolt | R$100,00 | R$244,30 | 144.3% |
| 7 | Minccino (152/086) | SV: Black Bolt | R$159,99 | R$334,95 | 109.4% |
| 8 | Terrakion (135/086) | SV: White Flare | R$119,90 | R$218,05 | 81.9% |
| 9 | Mega Feraligatr ex (274/217) | ME: Ascended Heroes | R$599,00 | R$862,15 | 43.9% |
| 10 | Salamence ex (187/159) | Escarlate e Violeta: Amigos de | R$250,00 | R$355,65 | 42.3% |

## 🚨 TCG Suspect (campo .estat-tcg inflado pelo MYP)

> Cards onde TCG declarado pelo MYP é >10x a última venda real do próprio MYP. Provável bug do `.estat-tcg`. Caso Jirachi PR-SM_SM161: MYP declarava R$1499 vs última venda R$19,99 (75x). Margens absurdas aqui são quase certamente artefato. **Já excluídos do Top 15 limpos**, listados aqui pra auditoria.

| # | Carta | Edição | MYP R$ | TCG decl R$ | Última venda R$ | Margem (fake) |
|---|---|---|---:|---:|---:|---:|
| 1 | Darumaka (097/086) | SV: Black Bolt | R$99,99 | R$2.605,80 | R$33,00 | 2506.1% |
| 2 | Cubchoo (109/086) | SV: Black Bolt | R$95,00 | R$893,55 | R$35,00 | 840.6% |

## 🚨 EN truncation risk (preço pode estar superestimado)

> Seller table do MYP bateu cap com zero EN visível — listing real pode ser mais barato. Validar via página direta.

| Carta | Edição | MYP R$ reportado | TCG R$ |
|---|---|---:|---:|
| Mimikyu da Equipe Rocket (238/217)Team Rocket's Mimikyu | ME: Ascended Heroes | R$115,00 | R$148,40 |
| Tangela da Érica (218/217)Erika's Tangela | ME: Ascended Heroes | R$105,00 | R$133,25 |
| Mega Dragonite ex (271/217) | ME: Ascended Heroes | R$269,91 | R$317,50 |
| Mega Gengar ex (269/217) | ME: Ascended Heroes | R$450,00 | R$463,40 |
| Charmander (038) | Mega Evolution: Series Black S | R$210,00 | R$216,15 |
| Reshiram do N (167/159)N's Reshiram | Escarlate e Violeta: Amigos de | R$100,00 | R$100,65 |
| Articuno (161/159) | Escarlate e Violeta: Amigos de | R$139,90 | R$139,95 |
| Mega Sharpedo ex (127/094) | Mega Evolução — Fogo Fantasmag | R$129,90 | R$124,95 |
| Mega Lopunny ex (128/094) | Mega Evolução — Fogo Fantasmag | R$109,99 | R$105,70 |
| Squirtle (039) | Mega Evolution: Series Black S | R$160,00 | R$150,40 |

---

*Gerado em 2026-05-24 04:03 UTC via `myp_summary.py` (single source: XLSX consolidado).*