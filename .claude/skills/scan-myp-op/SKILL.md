---
name: scan-myp-op
description: >-
  Rodar o scan de arbitragem do MYP para ONE PIECE (mypcards.com /onepiece
  vs TCGplayer via tcgcsv cat 68) por GRUPOS de edições e entregar via
  myp_op_summary.py. Use SEMPRE que o operador pedir para rodar o scanner de
  One Piece do MYP / "rodar o MYP OP" / "scan one piece" / "skill myp cards
  one piece" / escanear edições One Piece no MYP: antes de rodar, PERGUNTE
  quais dos 6 grupos ele quer (o catálogo de 65 edições é dividido em 6
  grupos por recência — grupos curtos terminam e entregam; scan longo demais
  morre sem entregar).
---

# Scan MYP → ONE PIECE por grupos — pergunte, rode, entregue

Mesmo formato dos skills Pokémon (`scan-myp`) e Dragon Ball (`scan-myp-dbz`),
para o scanner PARALELO `myp_op_scanner.py` (One Piece). O MYP tem **uma
seção** One Piece, que espelha a categoria 68 do tcgcsv (referência de preço
REAL — catálogo INGLÊS do TCGplayer):

| Seção MYP | Jogo | Referência |
|---|---|---|
| `onepiece` (65 edições) | One Piece Card Game | tcgcsv categoria 68 (84 groups) |

O catálogo completo (65 edições, enumeração real da sonda
`probe-myp-onepiece`, PR #98, 2026-08-09) está dividido em **6 grupos por
recência**. ⚠️ **Estimativas de duração são PRELIMINARES** (sem benchmark
real ainda — boosters OP têm ~120-160 cartas + parallels; starter decks são
pequenos; calibrar após os primeiros runs e atualizar AQUI).

## Passo 1 — SEMPRE perguntar quais grupos rodar

Ao ser invocado, **pergunte ao operador** (AskUserQuestion, multiSelect)
quais grupos rodar nesta sessão — nunca assuma. Se ele escolher vários, rode
**em sequência** (nunca em paralelo no mesmo IP — 2 sessões = 403
Cloudflare; o concurrency group `myp-scan` também serializa na nuvem).

## Os 6 grupos (substrings VERBATIM do catálogo real — nunca inventar/alterar)

> ⚠️ Toda substring vem verbatim da enumeração de edições da sonda de
> 2026-08-09 (run 31300834735). Substring deduzida "de cabeça" já saiu
> alucinada no passado (lição da frota) — é proibido. A partição é travada
> por teste (`test_scan_op_skill_profiles.py`): cobertura total das 65
> edições, sem sobreposição entre grupos. Prefixo cobre sufixo de propósito
> (ex.: "Adventure on Kami's Island" cobre também os Release Event Cards;
> "Premium Booster" cobre o Vol. 2 E o de 2024 — o filtro é substring OR).

### Grupo 1 — Pré-venda/2026: OP17 + Starter Decks 31-36 + SD01 (9 ed.)
```
--editions "Set Sail Deck Set" "The World's Strongest Warriors" "Starter Deck 35" "Starter Deck 36" "Starter Deck 31" "Starter Deck 34" "Starter Deck 33" "Starter Deck 32" "Starter Deck EX: Luffy & Ace"
```
(Muita coisa aqui ainda é pré-venda — poucas ofertas vivas; grupo rápido.)

### Grupo 2 — OP14→OP16 + EB03 + ST29 (2025-2026; 8 ed.)
```
--editions "The Time of Battle" "Adventure on Kami's Island" "Extra Booster: One Piece Heroines Edition" "Starter Deck 29" "The Azure Sea's Seven" "Carrying On His Will" "Learn Together Deck Set"
```
("Adventure on Kami's Island" cobre também o "…Release Event Cards".)

### Grupo 3 — OP11/OP12 + PRB + ST22-ST28 + EB02 (2025; 12 ed.)
```
--editions "Premium Booster" "Starter Deck 22" "Legacy of the Master" "Starter Deck 28" "Starter Deck 27" "Starter Deck 26" "Starter Deck 25" "Starter Deck 24" "Starter Deck 23" "A Fist of Divine Speed" "Extra Booster: Anime 25th Collection"
```
("Premium Booster" cobre o Vol. 2 de 2025 E o "-The Best-" de 2024 — por
isso o de 2024 fica NESTE grupo, não no 4: evita re-escanear em dois grupos.)

### Grupo 4 — OP08→OP10 + ST15-ST21 + OPRP (2024-2025; 12 ed.)
```
--editions "Royal Blood" "Starter Deck EX: Gear 5" "Emperors in the New World" "Revision Pack Cards" "Starter Deck 20" "Starter Deck 19" "Starter Deck 18" "Starter Deck 17" "Starter Deck 16" "Starter Deck 15" "Two Legends"
```
("Emperors in the New World" cobre também o "…2nd Anniversary Tournament
Cards".)

### Grupo 5 — OP04→OP07 + EB01 + ST10-ST14 (2023-2024; 9 ed.)
```
--editions "Starter Deck 14" "500 Years In the Future" "Memorial Collection" "Ultra Deck: The Three Brothers" "Wings of the Captain" "Starter Deck 11" "AWAKENING OF THE NEW ERA" "Ultra Deck: The Three Captains" "Kingdoms of Intrigue"
```

### Grupo 6 — OP01→OP03 + ST01-ST09/ST12 + promos (2022-2023 back-catalog; 15 ed.)
```
--editions "Starter Deck 9" "Starter Deck 8" "Starter Deck 7" "Pillars of Strength" "Zoro and Sanji" "Absolute Justice" "Paramount War" "One Piece Film Edition" "Animal Kingdom Pirates" "The Seven Warlords of the Sea" "Worst Generation" "Straw Hat Crew" "Romance Dawn" "Promotion Cards" "Gift Collection 2023"
```
(Back-catalog eficiente — a auditoria da frota mostra que deal mora em
lançamento; rode este grupo com expectativa de poucos hits.)

## Passo 2 — rodar (rota DETERMINÍSTICA por ambiente)

| Onde a sessão está rodando | Rota ÚNICA |
|---|---|
| **Sessão na nuvem / container** (Claude Code web, CI) | **SEMPRE** o workflow `OP MYP Scan` — dispatch abaixo. **NUNCA** rodar o scraper no container (Cloudflare/IP de datacenter não confiável; o runner do GitHub comprovadamente passa — provado na sonda do PR #98). |
| **Máquina local do operador** (Windows) | **SEMPRE** o comando local abaixo, em background/detached, com `--resume`. |

### Rota nuvem (workflow_dispatch — sempre estes inputs)

Disparar `op-scan.yml` no repo `matheuscllm-lgtm/myp-arbitrage-scanner`,
`ref: main`, com EXATAMENTE:
- `editions` = a lista verbatim do grupo escolhido (seção acima), com as
  aspas;
- demais inputs nos defaults (threshold 30 / min_price 50 / delay 1.5).

Depois: monitorar o run até `completed`; baixar o artifact
**`myp-op-consolidated-<run_id>`**; usar o `.md` de dentro (já gerado pelo
`myp_op_summary.py`) ou regenerá-lo do XLSX. Um grupo por vez — só disparar
o próximo depois de ENTREGAR o anterior (o concurrency group `myp-scan`
também impede simultâneos, inclusive com scans Pokémon/DBZ).

### Rota local (sempre este comando)

```bash
python myp_op_scanner.py \
  <--editions DO GRUPO ESCOLHIDO, verbatim acima> \
  --threshold 30 --min-price 50 --delay 1.5 \
  -o results/op_grupoN_<AAAA-MM-DD>.xlsx --resume
```

- **`--resume` é obrigatório**: se o processo morrer, re-rodar o MESMO
  comando retoma do checkpoint (`<output>.xlsx.resume.json`).
- Em background/detached; um grupo por vez, sequencial. Nunca 2 scans no
  mesmo IP (nem junto com um scan Pokémon/DBZ).
- `--threshold 30` é percent INTEIRO (convenção MYP; CardTrader usa fração).

## Passo 3 — entregar (ritual FIXO, contrato do repo, não negociável)

```bash
python myp_op_summary.py results/op_grupoN_<AAAA-MM-DD>.xlsx -o results/op_grupoN_<AAAA-MM-DD>.md
```

1. Colar o conteúdo do `.md` **VERBATIM** no chat — nunca remontar tabela à
   mão, nunca renomear/reordenar colunas, nunca dropar o link `[TCG]`.
2. A ÚNICA moldura permitida fora do verbatim: uma linha de contexto antes
   ("Grupo N — run <id>/local, data") e, depois, notas de leitura que NÃO
   alterem nem resumam a tabela.
3. Sem recomendação de compra; todos os buckets (🟢 limpos, 🚨 REVISAR,
   ⚠️ Sem referência, 🚨 truncation); sempre reportar a linha "Cobertura de
   referência real".

## Regras que este skill NÃO muda

- Margem BRUTA base compra `(TCG_BRL − MYP_BRL)/MYP_BRL`, threshold 30
  inteiro, piso `--min-price 50` (singles).
- NM-only (célula de qualidade, token exato) + EN-only (flag-icon) —
  parser herdado do scanner Pokémon. Idioma é o risco nº 1 em One Piece
  (lição do op_scanner do card-trader) — o filtro EN herdado é o guard.
- **Nunca inventar preço**: carta sem referência tcgcsv sai na seção
  "Sem referência TCG" com motivo — não existe fallback `.estat-tcg` no OP
  (decisão v1; referência real ou nada).
- Join determinístico por código de carta + qualificador de variante do h1
  ("(Alternate Art)" ≡ "(Parallel)" do TCGplayer; variante nunca casa o
  base) — detalhe no cabeçalho do `myp_op_scanner.py`. ⚠️ O marcador `p1`
  do campo Código NÃO é sinal de variante (provado invertido na sonda).
- Este skill é One Piece-only; Pokémon segue no `scan-myp` e Dragon Ball no
  `scan-myp-dbz`. Não misturar grupos de skills diferentes num mesmo run.
