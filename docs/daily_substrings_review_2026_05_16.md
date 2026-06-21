# Daily MYP Substrings — Review 2026-05-16

**Status:** Recomendação, NÃO aplicado. Operador aprova antes de mudar workflow.

## Contexto

- `.github/workflows/daily-scan.yml` define 9 substrings default (não 8 — recontagem corrige briefing) que filtram quais edições MYP entram no scan diário rápido. Substring match em `Edition` (texto contém), NÃO aliases CT.
- Lista atual: `Mega Ascended "Black Bolt" "White Flare" "Destined Rivals" "Journey Together" "Surging Sparks" "Stellar Crown" Prismatic`
- Ground truth deste review: `myp_arbitrage_20260515_0922_LOCAL_REVALIDATED.xlsx` (aggregate local do weekly run 25898507612, 20 chunks × full inventory 348 edições, deals já filtrados pelo postprocess H2 anti `.estat-tcg`). 91 deals limpos em 60 edições distintas.
- Único weekly dos últimos 30 dias disponível (cron weekly foi removido; Task Scheduler local agendado para domingos a partir de 2026-05-17).

## Métrica por substring atual

| # | Substring | Deals (90d / 1 weekly) | Edições matched | Top edição | Veredito |
|---|---|---:|---:|---|---|
| 1 | `Mega` | 1 | 1 | Mega Evolution Black Star Promos | **REMOVER** (Mega Evolution main sets `me1..me4` ainda não dropparam — esperado 0; promos pontuais não justificam) |
| 2 | `Ascended` | 3 | 1 | ME: Ascended Heroes | **MANTER** (set recém-released, sinal real) |
| 3 | `Black Bolt` | 4 | 1 | SV: Black Bolt | **MANTER** (top hit do weekly) |
| 4 | `White Flare` | 1 | 1 | SV: White Flare | **MANTER** (set irmão do Black Bolt; volume baixo mas relevante) |
| 5 | `Destined Rivals` | 2 | 1 | SV: Destined Rivals | **MANTER** |
| 6 | `Journey Together` | 1 | 1 | SV: Journey Together | **MANTER (marginal)** — meta-set ainda viável |
| 7 | `Surging Sparks` | 0 | 0 | — | **REMOVER** (0 deals; set frio neste snapshot) |
| 8 | `Stellar Crown` | 0 | 0 | — | **REMOVER** (0 deals; set frio neste snapshot) |
| 9 | `Prismatic` | 1 | 1 | SV: Prismatic Evolutions | **MANTER (marginal)** — alta visibilidade no mercado |

**Cobertura efetiva atual:** 13 / 91 deals = **14.3%** do weekly. 85.7% dos sinais estão em edições não cobertas pelo daily.

## Gap analysis — top edições não cobertas (≥2 deals no weekly)

| Edição | Deals | Substring proposta |
|---|---:|---|
| Prize Pack Series | 5 | `"Prize Pack"` |
| Sol & Lua PromosSun & Moon Promos | 4 | `"Sun & Moon Promos"` ou `"Sol & Lua Promos"` (BR título dupla) |
| Platinum 4: Arceus | 3 | `Platinum` (cobre Platinum 1..4) |
| Sun & Moon 10: Unbroken Bonds | 3 | `"Unbroken Bonds"` |
| HeartGold & SoulSilver | 3 | `HeartGold` |
| XY 7: Ancient Origins | 2 | `"Ancient Origins"` |
| EX 11: Delta Species | 2 | `"Delta Species"` |
| XY Promos | 2 | `"XY Promos"` |
| EX 4: Team Magma vs Team Aqua | 2 | `"Team Magma"` |
| Neo Revelation | 2 | `"Neo Revelation"` ou apenas `Neo` (cobre Neo Genesis/Discovery/Revelation/Destiny) |
| BW 10: Plasma Blast | 2 | `"Plasma Blast"` |
| EX 2: Sandstorm | 2 | `Sandstorm` |
| BW 5: Dark Explorers | 2 | `"Dark Explorers"` |
| Nintendo Black Star Promos | 2 | `"Nintendo Black Star"` (NÃO usar `Black Star` puro — colidiria com vários sets BR) |
| SV: Paradox Rift | 2 | `"Paradox Rift"` |
| Black & White Promos | 2 | `"Black & White Promos"` |
| EX 5: Hidden Legends | 2 | `"Hidden Legends"` |

Observação: 85% das edições não cobertas são **legacy/vintage** (Neo, EX, BW, XY, HGSS, Platinum). Sinal real mostra que o daily atual está miopicamente focado em sets modernos (SV-era + Mega) quando a margem real está dispersa no catálogo legacy + Prize Pack + Promos.

## Lista proposta (rebalance)

**Substrings mantidas (6):** `Ascended` `"Black Bolt"` `"White Flare"` `"Destined Rivals"` `"Journey Together"` `Prismatic`

**Substrings removidas (3):**
- `Mega` — só 1 hit (promo), Mega Evolution ainda quente mas não no weekly
- `Surging Sparks` — 0 hits
- `Stellar Crown` — 0 hits

**Substrings adicionadas (10) — escolhidas pelo critério ≥2 deals no weekly OU bucket genérico com cobertura ampla:**
1. `"Prize Pack"` — 5 deals (maior bucket isolado)
2. `"Sun & Moon Promos"` — 4 deals (substring match casa com título BR duplo `Sol & Lua PromosSun & Moon Promos`)
3. `Platinum` — 3 deals + cobre Platinum 1..4 (Arceus, Supreme Victors, Rising Rivals, Platinum base)
4. `"Unbroken Bonds"` — 3 deals
5. `HeartGold` — 3 deals
6. `"Paradox Rift"` — 2 deals (SV-era ainda quente)
7. `"Nintendo Black Star"` — 2 deals (única SP especificável sem colisão)
8. `"Ancient Origins"` — 2 deals
9. `Neo` — 2 deals + bucket vintage (Neo Genesis/Discovery/Revelation/Destiny todas em circulação)
10. `EX` — meta-bucket vintage. **CUIDADO:** match substring `EX` é PERIGOSO (cola em "EX 1: Ruby & Sapphire" mas também em qualquer título contendo as letras EX). Verificar se MYP usa `EX` prefix consistente — se não, **NÃO adicionar** este bucket; preferir adicionar individualmente `"Delta Species"`, `"Hidden Legends"`, `"Team Magma"`, `Sandstorm`. Pre-flight: rodar local com `--editions EX` em dry-run antes de approve.

**Total proposto:** 9 (sem `EX`) ou 10 (com `EX` pós-validação) substrings.

### Cobertura projetada

Com 9 substrings nova lista (sem `EX`): **~36 deals / 91 = 39.6%** (vs 14.3% atual). Triplica o sinal capturado pelo daily, mantendo escopo limitado (não vira full scan).

Se substituir `EX` pelas 4 substrings individuais (`"Delta Species"` `"Hidden Legends"` `"Team Magma"` `Sandstorm`): **~42 deals / 91 = 46.2%**, totalizando 13 substrings. Daily wall time esperado: ~25-35min (vs 15-25min atual) — ainda dentro do budget de 60min.

## Recomendação operacional

**Aplicar a opção 9-substrings (sem `EX`)** como primeiro passo. Reavaliar após 2 weeklies (4 semanas) — se gap legacy persistir, expandir granularidade individual.

## Caveats metodológicos

- **N=1 weekly.** Recomendação é direcional, não estatisticamente robusta. Repetir a análise quando houver 3-4 weeklies acumulados (junho/julho).
- **Snapshot temporal.** Surging Sparks/Stellar Crown podem voltar a ter deals em ciclos de release/rotation. Remover do daily não tira do weekly (que vê tudo).
- **Threshold/min_price fixados.** Análise usa default daily (`--threshold 25 --min-price 80`); mudar thresholds muda mix de deals.
- **Postprocess H2 já aplicado.** Os 91 deals do REVALIDATED já excluem os 11 contaminados pelo bug `.estat-tcg`. Sinal limpo.

## Próximos passos

1. Operador aprova lista 9-substrings (ou 13 com expansão EX individual)
2. PR de update em `.github/workflows/daily-scan.yml` (linhas 30 + 138, manter sincronizadas)
3. Próximo dispatch daily valida wall time real
4. Após próximo weekly, refazer este review com 2 datapoints
