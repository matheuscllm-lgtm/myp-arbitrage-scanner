---
tags: [tcg, scanner, myp, arbitrage, scan-daily]
date: 2026-05-22
type: daily
source: local scan
---

# MYP Scan Daily Quick — 2026-05-22

**Cards EN escaneados:** 113 | **Deals (≥25%):** 7 | **Limpos:** 1 | **🚨 TCG suspects:** 2 | **Truncation:** 11

## 🟢 Top 15 deals limpos (sem flag SIR/HR/SAR)

| # | Carta | Edição | MYP R$ | TCG R$ | Margem | Lucro R$ |
|---|---|---|---:|---:|---:|---:|
| 1 | Alakazam (003) | Mega Evolution: Series Black S | R$80,00 | R$100,45 | **25.6%** | R$20,45 |

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
| 10 | Mega Gengar ex (269/217) | ME: Ascended Heroes | R$335,00 | R$463,40 | 38.3% |

## 🚨 TCG Suspect (campo .estat-tcg inflado pelo MYP)

> Cards onde TCG declarado pelo MYP é >10x a última venda real do próprio MYP. Provável bug do `.estat-tcg`. Caso Jirachi PR-SM_SM161: MYP declarava R$1499 vs última venda R$19,99 (75x). Margens absurdas aqui são quase certamente artefato. **Já excluídos do Top 15 limpos**, listados aqui pra auditoria.

| # | Carta | Edição | MYP R$ | TCG decl R$ | Última venda R$ | Margem (fake) |
|---|---|---|---:|---:|---:|---:|
| 1 | Darumaka (097/086) | SV: Black Bolt | R$99,99 | R$2.605,80 | R$30,00 | 2506.1% |
| 2 | Cubchoo (109/086) | SV: Black Bolt | R$95,00 | R$893,55 | R$25,00 | 840.6% |

## 🚨 EN truncation risk (preço pode estar superestimado)

> Seller table do MYP bateu cap com zero EN visível — listing real pode ser mais barato. Validar via página direta.

| Carta | Edição | MYP R$ reportado | TCG R$ |
|---|---|---:|---:|
| Mimikyu da Equipe Rocket (238/217)Team Rocket's Mimikyu | ME: Ascended Heroes | R$115,00 | R$148,40 |
| Tangela da Érica (218/217)Erika's Tangela | ME: Ascended Heroes | R$105,00 | R$133,25 |
| Mega Dragonite ex (271/217) | ME: Ascended Heroes | R$269,91 | R$317,50 |
| Charmander (038) | Mega Evolution: Series Black S | R$210,00 | R$216,15 |
| Mega Sharpedo ex (127/094) | Mega Evolução — Fogo Fantasmag | R$129,90 | R$124,95 |
| Mega Lopunny ex (128/094) | Mega Evolução — Fogo Fantasmag | R$109,99 | R$105,70 |
| Mewtwo ex da Equipe Rocket (281/217)Team Rocket's Mewtw | ME: Ascended Heroes | R$2.399,97 | R$2.264,60 |
| Psyduck (226/217) | ME: Ascended Heroes | R$519,90 | R$486,65 |
| Squirtle (039) | Mega Evolution: Series Black S | R$170,00 | R$150,40 |
| Mega Charizard X ex (109/094) | Mega Evolução — Fogo Fantasmag | R$230,00 | R$180,30 |

---

*Gerado em 2026-05-22 20:31 UTC via `myp_summary.py` (single source: XLSX consolidado).*