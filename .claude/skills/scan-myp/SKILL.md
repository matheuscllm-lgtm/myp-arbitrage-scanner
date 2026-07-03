---
name: scan-myp
description: >-
  Rodar o scan de arbitragem do MYP (mypcards.com vs TCGplayer) por GRUPOS de
  edições e entregar via myp_summary.py. Use SEMPRE que o operador pedir para
  rodar o scanner do MYP / "rodar o skill do MYP" / escanear edições do MYP:
  antes de rodar, PERGUNTE quais dos 6 grupos ele quer (o catálogo é dividido
  em 6 grupos por recência, cada um dimensionado para caber em ≤2h30 de scan,
  para o scan não morrer no meio sem entregar resultado).
---

# Scan do MYP por grupos — pergunte, rode, entregue

O catálogo mapeado do MYP (as ~112 edições com preço TCGplayer REAL — ver
`MYP_EDITION_SUBSTR_TO_PTCG` no scanner) está dividido em **6 grupos por
recência**, cada um dimensionado para **≤ ~2h30 de scan** (média ~2h; base:
~7 min/edição do benchmark 2026-05-15; com `POKEMONTCG_API_KEY` ~6 min).
Motivo (operador, 2026-07-02): scans longos vinham sendo mortos por causa
não identificada e não entregavam nada — grupos curtos + `--resume` + XLSX
por grupo garantem entrega.

## Passo 1 — SEMPRE perguntar quais grupos rodar

Ao ser invocado, **pergunte ao operador** (AskUserQuestion, multiSelect)
quais grupos rodar nesta sessão — nunca assuma. Apresente os 6 grupos com a
estimativa de duração. Se ele escolher vários, rode **em sequência** (nunca
em paralelo no mesmo IP — 2 sessões = 403 Cloudflare).

## Os 6 grupos (substrings EXATAS — copiar verbatim, NUNCA inventar/alterar)

> ⚠️ Toda substring abaixo vem verbatim do dict `MYP_EDITION_SUBSTR_TO_PTCG`
> do scanner (verificado contra o scrape real de 362 edições, 2026-06-22) ou
> dos workflows de produção (`Mega`, do daily-scan.yml). Substring deduzida
> "de cabeça" já saiu alucinada no passado — é proibido.

### Grupo 1 — Mega Evolution + SV recente (13 ed., ~1h31)
Inclui a era ME inteira — até **Chaos Rising**, exigência do operador.
```
--editions Mega "Ascended Heroes" "Perfect Order" "Chaos Rising" "Scarlet & Violet: Destined Rivals" "SV09: Journey Together" "Prismatic Evolutions" "Surging Sparks" "Stellar Crown" "Shrouded Fable" "Twilight Masquerade" "Temporal Forces"
```
(`Mega` cobre todas as ME0x, incl. Phantasmal Flames; `Ascended Heroes` /
`Perfect Order` / `Chaos Rising` entram explícitas porque o título MYP
delas não contém "Mega" em todos os casos — redundância é inofensiva, o
filtro é OR.)

### Grupo 2 — SV restante + Black Bolt/White Flare + SWSH moderno (14 ed., ~1h38)
```
--editions "Paldean Fates" "Paradox Rift" "Obsidian Flames" 151 "Paldea Evolved" "Black Bolt" "White Flare" "Crown Zenith" "Silver Tempest" "Lost Origin" "Astral Radiance" "Brilliant Stars" "Fusion Strike" "Evolving Skies"
```

### Grupo 3 — SWSH antigo + Pokémon GO + Sun & Moon recente (20 ed., ~2h20)
```
--editions "Sword & Shield 6: Chilling Reign" "Sword & Shield 5: Battle Styles" "Shining Fates" "Sword & Shield 4: Vivid Voltage" "Sword & Shield 3.5: Champion's Path" "Sword & Shield 3: Darkness Ablaze" "Sword & Shield 2: Rebel Clash" "Celebrations: Classic Collection" "Pokémon GO" "Sun & Moon 12: Cosmic Eclipse" "Sun & Moon 11.5: Hidden Fates" "Sun & Moon 11: Unified Minds" "Sun & Moon 10: Unbroken Bonds" "Sun & Moon 9: Team Up" "Sun & Moon 8: Lost Thunder" "Sun & Moon 7.5: Dragon Majesty" "Sun & Moon 7: Celestial Storm" "Sun & Moon 6: Forbidden Light" "Sun & Moon 5: Ultra Prism" "Sun & Moon 4: Crimson Invasion"
```

### Grupo 4 — Sun & Moon restante + XY + HGSS (18 ed., ~2h06)
```
--editions "Sun & Moon 3.5: Shining Legends" "Sun & Moon 3: Burning Shadows" "Sun & Moon 2: Guardians Rising" "XY 12: Evolutions" "XY 11: Steam Siege" "XY 10: Fates Collide" "XY 8: BREAKthrough" "XY 7: Ancient Origins" "XY 6: Roaring Skies" "XY 5: Primal Clash" "XY 4: Phantom Forces" "XY 3: Furious Fists" "XY 2: Flashfire" "XY: Double Crisis" "XY: Kalos Starter Set" "HeartGold & SoulSilver 2: Unleashed" "HeartGold & SoulSilver 3: Undaunted" "HeartGold & SoulSilver 4: Triumphant"
```

### Grupo 5 — Black & White + DP/Platinum + EX final (21 ed., ~2h27)
```
--editions "Black & White 2: Emerging Powers" "Black & White 3: Noble Victories" "Black & White 4: Next Destinies" "Black & White 5: Dark Explorers" "Black & White 6: Dragons Exalted" "Black & White 7: Boundaries Crossed" "Black & White 8: Plasma Storm" "Black & White 9: Plasma Freeze" "Black & White 10: Plasma Blast" "Black & White: Dragon Vault" "Platinum 3: Supreme Victors" "Platinum 4: Arceus" "Mysterious Treasures" "Secret Wonders" "Great Encounters" "Majestic Dawn" "Legends Awakened" "Diamond & Pearl 7: Stormfront" "EX 16: Power Keepers" "EX 15: Dragon Frontiers" "EX 14: Crystal Guardians"
```

### Grupo 6 — EX restante + e-Card + WOTC (22 ed., ~2h34*)
```
--editions "EX 1: Ruby & Sapphire" "EX 2: Sandstorm" "EX 3: Dragon" "EX 4: Team Magma vs Team Aqua" "EX 5: Hidden Legends" "EX 6: Fire Red & Leaf Green" "EX 8: Deoxys" "EX 9: Emerald" "EX 10: Unseen Forces" "EX 11: Delta Species" "EX 12: Legend Maker" "EX 13: Holon Phantoms" "E-Card 1: Expedition Base Set" "E-Card 2: Aquapolis" "E-Card 3: Skyridge" "Neo Genesis" "Neo Discovery" "Neo Revelation" "Neo Destiny" "Gym Heroes" "Gym Challenge" "Legendary Collection"
```
(*estimativa conservadora; edições vintage têm bem menos produtos EN no MYP
— na prática costuma ficar abaixo; com API key ~2h12.)

## Passo 2 — rodar (rota DETERMINÍSTICA por ambiente — não há escolha ad-hoc)

> O objetivo do skill é HOMOGENEIDADE (operador, 2026-07-02): o scanner roda
> **sempre da mesma maneira** para o mesmo ambiente. A rota é decidida pela
> tabela abaixo, nunca improvisada caso a caso.

| Onde a sessão está rodando | Rota ÚNICA |
|---|---|
| **Sessão na nuvem / container** (Claude Code web, CI — IP de datacenter) | **SEMPRE** o workflow `Quick MYP Scan (chunked)` — dispatch abaixo. **NUNCA** rodar o scraper local no container (Cloudflare/IP não confiável; o runner do GitHub comprovadamente passa). |
| **Máquina local do operador** (Windows) | **SEMPRE** o comando local abaixo, em background/detached, com `--resume`. |

### Rota nuvem (workflow_dispatch — sempre estes inputs)

Disparar `quick-scan.yml` no repo `matheuscllm-lgtm/myp-arbitrage-scanner`,
`ref: main`, com EXATAMENTE:
- `editions` = a lista verbatim do grupo escolhido (seção acima);
- `chunk_total` = `"6"` (fixo);
- demais inputs nos defaults (threshold 30 / min_price 50 / delay 1.5).

Depois: monitorar o run até `completed`; baixar o artifact
**`myp-quick-consolidated-<run_id>`**; salvar o XLSX como
`results/grupoN_<AAAA-MM-DD>.xlsx`. Um grupo por vez — só disparar o
próximo depois de ENTREGAR o anterior (o concurrency group `myp-scan`
também impede simultâneos).

### Rota local (sempre este comando)

```bash
python myp_arbitrage_scanner.py \
  --editions <SUBSTRINGS DO GRUPO ESCOLHIDO, verbatim acima> \
  --threshold 30 --min-price 50 --delay 1.5 \
  -o results/grupoN_<AAAA-MM-DD>.xlsx --resume
```

- **`--resume` é obrigatório**: se o processo morrer, re-rodar o MESMO
  comando retoma do checkpoint (`<output>.resume.json`) — é a defesa contra
  o scan ser morto sem entregar.
- Em background/detached (nunca preso num terminal que pode fechar);
  monitorar o processo e o crescimento do XLSX.
- `--threshold 30` é percent INTEIRO (convenção MYP; CardTrader usa fração).
- Um grupo por vez, sequencial. Nunca 2 scans no mesmo IP.

## Passo 3 — entregar (ritual FIXO, contrato do repo, não negociável)

O formato de entrega é **sempre exatamente o mesmo**, para qualquer grupo e
qualquer ambiente:

```bash
python myp_summary.py results/grupoN_<AAAA-MM-DD>.xlsx --type daily -o results/grupoN_<AAAA-MM-DD>.md
```

1. Colar o conteúdo do `.md` **VERBATIM** no chat — nunca remontar tabela à
   mão, nunca renomear/reordenar colunas, nunca dropar o link `[TCG]`.
2. A ÚNICA moldura permitida fora do verbatim: uma linha de contexto antes
   ("Grupo N — run <id>/local, data") e, depois da tabela, notas de leitura
   que NÃO alterem nem resumam a tabela (ex.: apontar os itens "validar").
3. Sem recomendação de compra, todos os buckets, todos os deals, e sempre
   reportar a linha "Cobertura de preço TCG real" (real vs fallback).

## Regras que este skill NÃO muda

- Margem BRUTA, threshold 30 inteiro, piso `--min-price 50` (piso vale só
  para CARTAS; produtos selados não têm piso — selados são do repo
  sealed-scanner, fora do escopo do MYP).
- Honestidade de preço: real (`tcgcsv`/`pokemontcg.io`) vs fallback
  `.estat-tcg` sempre rotulado; nunca tratar fallback como real.
- As ~250 edições fora dos 6 grupos são as SEM mapeamento de preço real
  (só renderiam margem fallback não-confiável) — ficam fora de propósito.
  Se uma edição nova ganhar mapeamento no dict, adicione-a ao grupo da era
  correspondente NESTE arquivo (mantendo o teto de ~21 edições/grupo).
