---
description: Roda o scan canônico do MYP em GRUPOS de sets (6 grupos, do mais recente ao vintage, cada um dimensionado pra ≤2h30) e entrega via myp_summary.py verbatim. SEMPRE pergunta ao operador quais grupos rodar antes de começar. Argumento opcional = números de grupo (ex.: "1 3") pra pular a pergunta.
allowed-tools: Bash, Read, Grep, Glob, AskUserQuestion
---

Você foi acionado pelo comando **`/scan`** do operador. Sua missão é rodar o
scanner MYP **por grupos de edições** — nunca o catálogo inteiro numa tacada —
e entregar cada grupo no formato obrigatório do `myp_summary.py`. Este runbook
existe porque runs longos (>~2h30) morrem sem entregar nada; cada grupo é
dimensionado pra caber nesse teto e cada grupo entrega **sozinho** (se o
seguinte morrer, o anterior já foi entregue).

**Argumento recebido (grupos opcionais, ex. `1 3`):** `$ARGUMENTS`

---

## 1. SEMPRE pergunte quais grupos rodar (obrigatório)

Se `$ARGUMENTS` **não** trouxer números de grupo válidos (1–6), **pergunte ao
operador via `AskUserQuestion`** quais grupos rodar antes de qualquer scan
(multiSelect; como o limite é 4 opções por pergunta, divida em duas: "grupos
recentes (1–4)?" e "grupos antigos (5–6)?" — seleção vazia/"Other: nenhum" =
não rodar aquela faixa). Nunca escolha grupos sozinho.

## 2. Os 6 grupos (substrings VERIFICADAS — nunca invente/deduza outras)

Todas as substrings abaixo vêm do mapa de produção
`MYP_EDITION_SUBSTR_TO_PTCG` do próprio scanner (match case-insensitive por
substring do título MYP). **Proibido** acrescentar substring deduzida —
aliases chutados já saíram alucinados (lição ASI-Evolve). Edições fora do mapa
(bases de era antigas, promos avulsas) ficam fora de propósito: sem referência
de preço real a margem não é confiável.

**Grupo 1 — Mega Evolution + SV mais recentes (inclui até o Chaos Rising)** · ~11 edições · est. ~1h15–1h45
`"Mega Evolution" "Ascended Heroes" "Perfect Order" "Chaos Rising" "Black Bolt" "White Flare" "Destined Rivals" "Journey Together" "Prismatic Evolutions"`
(`"Mega Evolution"` cobre ME base, Phantasmal Flames e os promos ME.)

**Grupo 2 — resto da era Scarlet & Violet** · 10 edições · est. ~1h05–1h50
`"Surging Sparks" "Stellar Crown" "Shrouded Fable" "Twilight Masquerade" "Temporal Forces" "Paldean Fates" "Paradox Rift" "Obsidian Flames" "151" "Paldea Evolved"`

**Grupo 3 — era Sword & Shield + Celebrations + Pokémon GO** · ~16 edições · est. ~1h30–1h50
`"Crown Zenith" "Silver Tempest" "Lost Origin" "Astral Radiance" "Brilliant Stars" "Fusion Strike" "Evolving Skies" "Chilling Reign" "Battle Styles" "Vivid Voltage" "Champion's Path" "Darkness Ablaze" "Rebel Clash" "Shining Fates" "Celebrations" "Pokémon GO"`

**Grupo 4 — era Sun & Moon (completa, uma substring)** · ~15 edições · est. ~1h15–1h30
`"Sun & Moon"`
(prefixo observado em todos os títulos SM do mapa; pega também o título bilíngue de promos SM — ok, é escopo de scan.)

**Grupo 5 — eras XY + Black & White** · ~23 edições · est. ~1h30–1h50
`"Flashfire" "Furious Fists" "Phantom Forces" "Primal Clash" "Roaring Skies" "Ancient Origins" "BREAKthrough" "Fates Collide" "Steam Siege" "XY 12: Evolutions" "Kalos Starter" "Double Crisis" "Black & White"`
(⚠️ NÃO use `XY` solto — substring casaria "gala**xy**" etc.; `"XY 12: Evolutions"` é completo porque "Evolutions" sozinho colide com Prismatic/Mega. `"Black & White"` cobre BW 2–10, Dragon Vault e promos BW.)

**Grupo 6 — vintage: EX / DP / Platinum / HGSS / Neo / Gym / E-Card / Legendary** · ~39 edições · est. ~2h00–2h25 (o mais apertado)
`"Ruby & Sapphire" "Sandstorm" "EX 3: Dragon" "Team Magma" "Hidden Legends" "Fire Red & Leaf Green" "Deoxys" "Emerald" "Unseen Forces" "Delta Species" "Legend Maker" "Holon Phantoms" "Crystal Guardians" "Dragon Frontiers" "Power Keepers" "Mysterious Treasures" "Secret Wonders" "Great Encounters" "Majestic Dawn" "Legends Awakened" "Stormfront" "Platinum" "HeartGold & SoulSilver" "Neo" "Gym Heroes" "Gym Challenge" "E-Card" "Legendary Collection"`
(`"EX 3: Dragon"` completo porque "Dragon" solto colide com Dragon Vault/Majesty/Frontiers.)

## 3. Rodar (um comando POR GRUPO, sempre sequencial)

Para cada grupo escolhido, **na ordem**, um run separado com XLSX próprio:

```bash
python myp_arbitrage_scanner.py \
  --editions <substrings do grupo, entre aspas> \
  --threshold 30 --min-price 50 --delay 1.5 \
  -o results/grupo<N>_<AAAAMMDD_HHMM>.xlsx
```

- `--threshold` aqui é **PERCENT INTEIRO** (`30` = 30%) — convenção OPOSTA à do
  CardTrader. Nunca passe fração.
- **NUNCA rode dois grupos em paralelo** — 2 sessões no mesmo IP = 403 da
  Cloudflare. Sequencial, sempre.
- Rode **em background** e monitore. Se um grupo passar de ~2h30 de relógio,
  anote a duração real no resumo final e proponha re-dividir o grupo — não
  deixe virar run infinito.
- `POKEMONTCG_API_KEY` presente = sleep adaptativo (run ~25% mais rápido). Em
  runner do GitHub use `--tcg-source tcgcsv` (pokemontcg.io é inalcançável lá).
- Grupo que falhar/cair **não cancela os demais**: registre a falha com a saída
  real e siga pro próximo. O que já rodou, entrega.

## 4. Entrega (por grupo, formato OBRIGATÓRIO)

Assim que **cada grupo** terminar (não espere os outros):

```bash
python myp_summary.py results/grupo<N>_<stamp>.xlsx --type daily -o results/grupo<N>-<data>.md
```

Cole no chat o markdown gerado **VERBATIM** — contrato de entrega do
`CLAUDE.md` deste repo: todas as linhas de todos os buckets, coluna `Carta` =
nome+número, coluna `Links` = `[oferta](url) · [TCG](url)` em TODA linha,
buckets suspeitos marcados "validar manualmente". **PROIBIDO** remontar
tabela, dropar link ou entregar XLSX por padrão. Não recomende compra.

## 5. Fechamento

Resumo curto no final: grupos rodados, duração REAL de cada um (pra calibrar
as estimativas), deals por bucket, grupos que falharam/estouraram tempo, e o
caminho dos XLSX/`.md` de apoio. Outputs de scan são gitignored — nunca
commite dados de scan.
