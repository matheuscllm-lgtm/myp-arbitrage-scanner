---
tags: [tcg, scanner, myp, arbitrage, revalidation]
date: 2026-06-04
type: revalidation
source: full live re-scrape (scrape_product) dos deals do scan 02:34 UTC
---

# MYP Revalidação ao vivo — 2026-06-04

Re-scrape completo (preço EN NM + margem recalculados ao vivo) dos 15 deals do
sheet `🔥 Deals`. Motivo: o snapshot das 02:34 capturou um listing EN do
**Mega Gengar ex (269/217)** a R$230 que **já foi vendido** — o menor EN real
agora é R$335. Marketplace MYP rotaciona rápido; o listing mais barato some
primeiro. Revalidação confirma quais deals ainda existem.

**Resultado:** 14 HOLD (≥25%) · 1 sumiu/abaixo · 0 erro

## ✅ Deals que ainda existem (≥25%, preço ao vivo)

| # | Carta | Edição base | MYP EN NM R$ | TCG R$ | Margem | Flag |
|---|---|---|---:|---:|---:|---|
| 1 | Ursaluna Lua Sangrenta ex (168/131) | SV Evoluções | R$180,00 | R$392,35 | **118%** | ⚠️ VARIANT |
| 2 | Mimikyu da Equipe Rocket (238/217) | ME Ascended | R$100,00 | R$160,95 | **61%** | ⚠️ VARIANT |
| 3 | Mega Dragonite ex (271/217) | ME Ascended | R$200,00 | R$300,15 | **50%** | ⚠️ VARIANT |
| 4 | Moltres ex da Equipe Rocket (229/182) | ME Ascended | R$400,00 | R$596,95 | **49%** | ⚠️ VARIANT |
| 5 | Emolga (112/086) | SV Black Bolt/White Flare | R$89,97 | R$130,85 | **45%** | ⚠️ VARIANT |
| 6 | Psyduck (226/217) | ME Ascended | R$398,00 | R$557,40 | **40%** | ⚠️ VARIANT |
| 7 | Tepig (096/086) | SV Black Bolt/White Flare | R$118,00 | R$162,00 | **37%** | ⚠️ VARIANT |
| 8 | Mega Gengar ex (269/217) | ME Ascended | R$335,00 | R$446,00 | **33%** | ⚠️ VARIANT (era R$230/94% no snapshot — vendido) |
| 9 | Alakazam (003) | ME Black Star Promo | R$80,00 | R$104,85 | **31%** | — (único limpo) |
| 10 | Mega Hawlucha ex (283/217) | ME Ascended | R$290,00 | R$375,95 | **30%** | ⚠️ VARIANT |
| 11 | Mega Zygarde ex (124/088) | ME | R$650,00 | R$839,35 | **29%** | ⚠️ VARIANT |
| 12 | Tangela da Érica (218/217) | ME Ascended | R$105,00 | R$135,50 | **29%** | ⚠️ VARIANT |
| 13 | Mega Feraligatr ex (274/217) | ME Ascended | R$700,00 | R$876,35 | **25%** | ⚠️ VARIANT |
| 14 | Zoroark ex do N (286/217) | ME Ascended | R$749,00 | R$937,30 | **25%** | ⚠️ VARIANT |

## ✖ Sumiu / caiu abaixo de 25%

| Carta | Edição | Era (snapshot) | Status ao vivo |
|---|---|---|---|
| Mega Charizard X ex (109/094) | ME | R$129 / 40% | Sem seller EN NM (ou < threshold) — listing vendido |

## Leitura

- **13 dos 14 sobreviventes são `⚠️ VARIANT`** (collector# > set total → SIR/HR/SAR).
  Todos precisam de validação visual da página direta antes de operar: o
  `.estat-tcg` do MYP pode refletir um print/acabamento diferente do listing.
- **Único deal verdadeiramente limpo:** Alakazam (003) — R$80 → R$104,85 (+31%, lucro R$24,85).
- Confirmado que o caso Mega Gengar foi **staleness de snapshot**, não bug de
  parsing: a row R$230 atual é Português (corretamente pulada) e os EN reais
  começam em R$335.

---

*Gerado em 2026-06-04 ~19:54 UTC via re-scrape `scrape_product` ao vivo.*
