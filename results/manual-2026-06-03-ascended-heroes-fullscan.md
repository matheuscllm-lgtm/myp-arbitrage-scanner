# Scan completo — ME: Ascended Heroes (v5.9)

*2026-06-03 16:01 — primeiro full scan da edição com o fix de paginação de
truncation (v5.9). XLSX: `results/ah_20260603_full_v59.xlsx` (gitignored — só o
resumo MD entra no repo).*

## Métricas

| | |
|---|---:|
| Produtos varridos | 295 |
| Páginas HTTP buscadas | 384 |
| **Páginas de seller paginadas (v5.9)** | **69** |
| **Falhas de fetch de página** | **0** |
| EN cards com preço | 27 |
| **🔥 Deals (≥25%)** | **7** |
| TCG suspects excluídos | 2 (sub-R$80, fora das sheets) |
| EN truncation risks residuais | 0 |
| Oversized collector# (VARIANT) | 27 |
| Skipped: sem TCG / sem EN / <R$80 | 0 / 2 / 266 |

## 🔥 Deals (todas as 7, ordenadas por margem)

| Card | MYP EN-NM | TCG | Margem | Diff | Sellers | Flag |
|---|---:|---:|---:|---:|---:|:--|
| [Mega Gengar ex (269/217)](https://mypcards.com/pokemon/produto/310506/mega-gengar-ex) | R$290 | R$446,00 | **+54%** | R$156,00 | 21 | ⚠️ VARIANT |
| [Mega Dragonite ex (271/217)](https://mypcards.com/pokemon/produto/310508/mega-dragonite-ex) | R$200 | R$300,15 | **+50%** | R$100,15 | 20 | ⚠️ VARIANT |
| [Psyduck (226/217)](https://mypcards.com/pokemon/produto/310463/psyduck) | R$398 | R$557,40 | **+40%** | R$159,40 | 15 | ⚠️ VARIANT |
| [Mega Hawlucha ex (283/217)](https://mypcards.com/pokemon/produto/310520/mega-hawlucha-ex) | R$290 | R$375,95 | **+30%** | R$85,95 | 5 | ⚠️ VARIANT |
| [Tangela da Érica (218/217)](https://mypcards.com/pokemon/produto/310455/tangela-da-erica) | R$105 | R$135,50 | **+29%** | R$30,50 | 9 | ⚠️ VARIANT |
| [Mega Feraligatr ex (274/217)](https://mypcards.com/pokemon/produto/310511/mega-feraligatr-ex) | R$700 | R$876,35 | **+25%** | R$176,35 | 6 | ⚠️ VARIANT |
| [Zoroark ex do N (286/217)](https://mypcards.com/pokemon/produto/310523/zoroark-ex-do-n) | R$749 | R$937,30 | **+25%** | R$188,30 | 10 | ⚠️ VARIANT |

## O que o fix v5.9 mudou neste scan

- **69 páginas de marketplace seguidas em 26 produtos truncados, 0 falhas.**
  Dos 7 deals, **3 só existem por causa do fix** — Mega Gengar, Mega Dragonite e
  Psyduck estavam sub-threshold (ou marginalmente positivos) na página 1 e
  cruzaram o threshold quando o EN-NM mais barato das páginas 2+ foi lido. O
  scanner v5.8 teria reportado ~4 deals aqui, não 7.
- **0 truncation risks residuais** no run final. O único cap-hit observado
  durante o scan (`Tangela da Érica 007/217`, 11 págs > cap 10) é sub-R$80 →
  caiu no filtro de preço, não chegou aos deals.
- **0 em 🚨 Validate Manually / 🚨 TCG Suspect** — os 2 TCG suspects eram
  sub-R$80 (`Transmissor da Equipe Rocket 209/217` etc.), filtrados antes das
  sheets.

## ⚠️ Caveats (dados pra decisão do operador — não são recomendações de compra)

1. **As 7 são `⚠️ VARIANT`** (collector# > 217 → SIR/special-art de Ascended
   Heroes). O link TCG é busca por nome (não direto). Antes de importar:
   confirmar visualmente **variante + condição NM + idioma EN** do listing mais
   barato.
2. Margem usa o modelo padrão (custo = preço × 1.06, frete 0). FX/spread não
   entram.
