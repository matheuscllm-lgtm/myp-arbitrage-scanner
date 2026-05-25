# PriceCharting PSA Prices — 2026-05-25

Spot-check de preços graded pros deals em `scan-principais-2026-05-24-v587.xlsx`. Fonte: PriceCharting (cloudscraper bypassa anti-bot). Médias = `info_box`; PSA9 eBay = mediana das vendas recentes filtradas por título `PSA 9`. FX assumido **BRL/USD = 5.30** (ajustar via `--fx`). Custo grading+freight assumido **US$50/carta** (ajustar via `--grading-cost`). **Outros custos não incluídos:** eBay fees (~13%), tax — net realistic líquido ≈ valor da tabela × 0.87.

## Preços por grade (USD)

| # | Carta | Slug PC | Ungraded | PSA 8 | PSA 9 | PSA 10 | PSA9 eBay (mediana / N) |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | Mega Dragonite ex (271/217) | `pokemon-ascended-heroes/mega-dragonite-ex-271` | $63.00 | — | **$117.75** | $390.00 | $122.50/28 |
| 2 | Mimikyu da Equipe Rocket (238/217)Team Rocket's Mimikyu | `pokemon-ascended-heroes/team-rocket%27s-mimikyu-238` | $30.00 | $26.55 | **$65.34** | $457.50 | $61.88/7 |
| 3 | Salamence ex (187/159) | `pokemon-journey-together/salamence-ex-187` | $60.00 | $53.41 | **$63.99** | $304.50 | $64.99/29 |
| 4 | Mega Feraligatr ex (274/217) | `pokemon-ascended-heroes/mega-feraligatr-ex-274` | $168.69 | — | **$218.07** | $690.00 | $192.50/11 |
| 5 | Psyduck (226/217) | `pokemon-ascended-heroes/psyduck-226` | $100.77 | $112.50 | **$185.50** | $700.00 | $185.50/27 |
| 6 | Audino (151/086) | `pokemon-black-bolt/audino-151` | $30.17 | $18.80 | **$29.00** | $253.11 | $25.00/27 |
| 7 | Moltres ex da Equipe Rocket (229/182)Team Rocket's Moltres ex | `pokemon-destined-rivals/team-rocket%27s-moltres-ex-229` | $100.18 | $78.82 | **$103.95** | $377.44 | $104.40/27 |
| 8 | Mega Gengar ex (269/217) | `pokemon-ascended-heroes/mega-gengar-ex-269` | $83.16 | $80.00 | **$152.50** | $520.40 | $162.50/29 |
| 9 | Mega Froslass ex (275/217) | `pokemon-ascended-heroes/mega-froslass-ex-275` | $81.00 | — | **$74.97** | $450.13 | $75.00/9 |
| 10 | Meowth ex (121/088) | `pokemon-perfect-order/meowth-ex-121` | $207.70 | — | **$303.49** | $1125.00 | $429.95/3 |
| 11 | Alakazam (003) | `pokemon-promo/alakazam-stamped-3` | $22.84 | — | **$40.71** | $133.75 | —/0 |
| 12 | Tangela da Érica (218/217)Erika's Tangela | `pokemon-ascended-heroes/erika%27s-tangela-218` | $26.27 | $30.48 | **$49.99** | $283.33 | $50.50/8 |
| 13 | Zoroark ex do N (286/217)N's Zoroark ex | `pokemon-ascended-heroes/n%27s-zoroark-ex-286` | $177.50 | $148.50 | **$171.48** | $735.00 | $153.25/20 |

## Arbitragem MYP → PSA (líquido após +US$50 grading/freight)

Diff = PSA grade − (MYP USD + grading). Sort por **Diff PSA 9** (piso conservador). Diff PSA 10 é o jackpot upside se a carta entrar 10 em vez de 9.

| Carta | MYP R$ | MYP US$ | +grading | PSA 9 US$ | Diff PSA 9 | PSA 10 US$ | Diff PSA 10 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Meowth ex (121/088) | R$800.00 | $150.94 | $200.94 | $303.49 | **+$102.55** | $1125.00 | **+$924.06** |
| Psyduck (226/217) | R$340.00 | $64.15 | $114.15 | $185.50 | **+$71.35** | $700.00 | **+$585.85** |
| Mega Feraligatr ex (274/217) | R$599.00 | $113.02 | $163.02 | $218.07 | **+$55.05** | $690.00 | **+$526.98** |
| Mega Gengar ex (269/217) | R$335.00 | $63.21 | $113.21 | $152.50 | **+$39.29** | $520.40 | **+$407.19** |
| Mega Dragonite ex (271/217) | R$209.90 | $39.60 | $89.60 | $117.75 | **+$28.15** | $390.00 | **+$300.40** |
| Mimikyu da Equipe Rocket (238/217)Team Rocket's Mimikyu | R$100.00 | $18.87 | $68.87 | $65.34 | -$3.53 | $457.50 | **+$388.63** |
| Zoroark ex do N (286/217)N's Zoroark ex | R$699.00 | $131.89 | $181.89 | $171.48 | -$10.41 | $735.00 | **+$553.11** |
| Tangela da Érica (218/217)Erika's Tangela | R$105.00 | $19.81 | $69.81 | $49.99 | -$19.82 | $283.33 | **+$213.52** |
| Moltres ex da Equipe Rocket (229/182)Team Rocket's Moltres ex | R$400.00 | $75.47 | $125.47 | $103.95 | -$21.52 | $377.44 | **+$251.97** |
| Alakazam (003) | R$80.00 | $15.09 | $65.09 | $40.71 | -$24.38 | $133.75 | **+$68.66** |
| Salamence ex (187/159) | R$239.90 | $45.26 | $95.26 | $63.99 | -$31.27 | $304.50 | **+$209.24** |
| Audino (151/086) | R$80.00 | $15.09 | $65.09 | $29.00 | -$36.09 | $253.11 | **+$188.02** |
| Mega Froslass ex (275/217) | R$370.00 | $69.81 | $119.81 | $74.97 | -$44.84 | $450.13 | **+$330.32** |

## Top picks net-positive (Diff PSA 9 > 0 com US$50 grading)

- **Meowth ex (121/088)** — MYP R$800.00 → PSA 9 líquido **+$102.55**, PSA 10 jackpot +$924.06
- **Psyduck (226/217)** — MYP R$340.00 → PSA 9 líquido **+$71.35**, PSA 10 jackpot +$585.85
- **Mega Feraligatr ex (274/217)** — MYP R$599.00 → PSA 9 líquido **+$55.05**, PSA 10 jackpot +$526.98
- **Mega Gengar ex (269/217)** — MYP R$335.00 → PSA 9 líquido **+$39.29**, PSA 10 jackpot +$407.19
- **Mega Dragonite ex (271/217)** — MYP R$209.90 → PSA 9 líquido **+$28.15**, PSA 10 jackpot +$300.40

---

*Gerado em 2026-05-25 14:05 UTC via `scripts/scrape_pricecharting_psa.py`. Próximo passo: rodar `psa-arb analyze-live` nos top picks com pop counts manuais (psacard.com/pop) pra decisão final com P(PSA 10).*
