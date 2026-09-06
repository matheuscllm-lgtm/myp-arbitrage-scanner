---
name: scan-myp-dbz
description: >-
  Rodar o scan de arbitragem do MYP para DRAGON BALL (mypcards.com dbsfusion +
  dbsmasters vs TCGplayer via tcgcsv) por GRUPOS de edições e entregar via
  myp_dbz_summary.py. Use SEMPRE que o operador pedir para rodar o scanner de
  Dragon Ball do MYP / "rodar o MYP DBZ" / "scan dragon ball" / escanear
  Fusion World ou DBS Masters no MYP: antes de rodar, PERGUNTE quais dos 6
  grupos ele quer (o catálogo de 123 edições é dividido em 6 grupos por
  recência — grupos curtos terminam e entregam; scan longo demais morre sem
  entregar).
---

REGRA VIGENTE DO OPERADOR: ler DELIVERY_CHAT.md na raiz do repositório. Entrega somente no chat, preço de referência clicável, coleta nova sob demanda; não executar scans no GitHub Actions nem publicar resultados. Esta regra substitui instruções antigas conflitantes abaixo.



# Scan MYP → DRAGON BALL por grupos — pergunte, rode, entregue

Mesmo formato do skill Pokémon (`scan-myp`), para o scanner PARALELO
`myp_dbz_scanner.py` (Dragon Ball). O MYP tem **duas seções** DBZ, que
espelham as duas categorias do tcgcsv (referência de preço REAL):

| Seção MYP | Jogo | Referência |
|---|---|---|
| `dbsfusion` (35 edições) | DBS Card Game: **Fusion World** | tcgcsv categoria 80 |
| `dbsmasters` (88 edições) | DBS Card Game "**Masters**" (clássico) | tcgcsv categoria 27 |

O catálogo completo (123 edições, enumeração real da sonda
`probe-myp-dragonball`, PR #95, 2026-08-03) está dividido em **6 grupos por
recência**. ⚠️ **Estimativas de duração são PRELIMINARES** (sem benchmark
real ainda — o catálogo DBZ tem bem menos produto/edição que o Pokémon;
calibrar após os primeiros runs e atualizar AQUI).

## Passo 1 — SEMPRE perguntar quais grupos rodar

Ao ser invocado, **pergunte ao operador** (AskUserQuestion, multiSelect)
quais grupos rodar nesta sessão — nunca assuma. Se ele escolher vários, rode
**em sequência** (nunca em paralelo no mesmo IP — 2 sessões = 403
Cloudflare; o concurrency group `myp-scan` também serializa na nuvem).

## Os 6 grupos (substrings VERBATIM do catálogo real — nunca inventar/alterar)

> ⚠️ Toda substring vem verbatim da enumeração de edições da sonda de
> 2026-08-03 (runs 30781111250/30781617752). Substring deduzida "de cabeça"
> já saiu alucinada no passado (lição da frota) — é proibido. A partição é
> travada por teste (`test_scan_dbz_skill_profiles.py`): cobertura total das
> 123 edições, sem sobreposição entre grupos. Prefixo cobre sufixo de
> propósito (ex.: "Cross Force" cobre também "Cross Force Release Event
> Cards" — o filtro é substring OR).

### Grupo 1 — Fusion World recente (FB06→FB11 + starters novos; 16 ed.)
```
--sections dbsfusion --editions "Brightness of Hope" "Story Booster 01" "Cross Force" "Dual Evolution" "Starter Deck EX" "Saiyan's Pride" "Manga Booster" "Wish For Shenron" "Starter Deck 10" "Starter Deck 9" "Rivals Clash" "Starter Deck 8"
```

### Grupo 2 — Fusion World inicial + promos/EM (FB01→FB05, FS01–FS07; 19 ed.)
```
--sections dbsfusion --editions "New Adventure" "Ultra Limit" "Raging Roar" "Starter Deck 7" "Starter Deck 6" "Starter Deck 5" "Blazing Aura" "Awakened Pulse" "Starter Deck 4" "Starter Deck 3" "Starter Deck 2" "Starter Deck 1: Son Goku" "Tournament and Championship Promos" "Fusion World Promotion" "Energy Markers"
```
("Starter Deck 1: Son Goku" vai com o nome completo de propósito — só
"Starter Deck 1" casaria também o Starter Deck 10 do grupo 1.)

### Grupo 3 — Masters moderno + era Zenkai (BT18→BT28, SD17–SD22; 22 ed.)
```
--sections dbsmasters --editions "Prismatic Clash" "Beyond Generations" "Perfect Combination" "Premium Anniversary Box 2023" "Critical Blow" "Wild Resurgence" "Proud Warrior" "Zenkai" "Ultimate Awakened Power" "Ultimate Deck 2023" "Ultimate Deck 2022" "5th Anniversary Set" "Z-Series Pack"
```
("Zenkai" cobre os 3 boosters BT18–BT20 — inclusive o título com typo real
"Zenkai Sereis Power Absorbed" — e os 4 Zenkai Starter Decks.)

### Grupo 4 — Masters 2021-2022 (B10→B17 + Unison/Collector's; 21 ed.)
```
--sections dbsmasters --editions "Ultimate Squad" "Realm of the Gods" "Mythic Booster" "Saiyan Showdown" "Cross Spirits" "Saiyan Boost" "Namekian Boost" "Supreme Rivalry" "Vicious Rejuvenation" "Battle Enhanced" "Battle Advanced" "Giant Force" "Vermilion Bloodline" "CollectorsSelection" "Theme Selection" "Darkness Reborn" "Pride of the Saiyans" "Battle Evolution Booster" "Rise of the Unison Warrior"
```

### Grupo 5 — Masters 2019-2020 (BT7→BT9 + Surge/Unison/XD; 20 ed.)
```
--sections dbsmasters --editions "Universe 7 Unison" "Universe 11 Unison" "The Ultimate Life Form" "Spirit of Potara" "Clan Collusion" "Saiyan Wonder" "Fusion Hero" "Forsaken Warrior" "Android Duality" "Dragon Brawl" "Parasitic Overlord" "Instinct Surpassed" "Universal Onslaught" "Namekian Surge" "Saiyan Surge" "Promotion Cards" "Divine Multiverse" "Malicious Machinations" "Universe 6 Assailants" "Saiyan Legacy"
```

### Grupo 6 — Masters clássico 2017-2019 (BT1→BT7, EX/TB/SD iniciais; 25 ed.)
```
--sections dbsmasters --editions "Assault of the Saiyans" "Special Anniversary Box" "Unity Of Saiyans" "Unity Of Destruction" "Rising Broly" "Destroyer Kings" "Clash Of Fates" "Shenron" "Miraculous Revival" "World Martial Arts Tournament" "Ultimate Box" "Colossal Warfare" "Tournament Of Power" "Cross Worlds" "Union Force" "Galactic Battle" "Mighty Heroes" "Dark Demon" "The Awakening" "The Extreme Evolution" "The Dark Invasion" "The Guardian Of Namekians" "The Crimson Saiyan" "Resurrected Fusion"
```
("Special Anniversary Box" cobre AS DUAS caixas — a de 2019/EX6 e a
"…2020"/EX13 — por isso a de 2020 fica NESTE grupo, não no 5: evita
re-escanear a mesma edição em dois grupos. Sets clássicos têm pouco estoque
EN no MYP → o grupo é grande em edições mas rápido na prática.)

## Passo 2 — rodar (rota DETERMINÍSTICA por ambiente)

| Onde a sessão está rodando | Rota ÚNICA |
|---|---|
| **Sessão na nuvem / container** (Claude Code web, CI) | **SEMPRE** o workflow `DBZ MYP Scan` — dispatch abaixo. **NUNCA** rodar o scraper no container (Cloudflare/IP de datacenter não confiável; o runner do GitHub comprovadamente passa — provado na sonda do PR #95). |
| **Máquina local do operador** (Windows) | **SEMPRE** o comando local abaixo, em background/detached, com `--resume`. |

### Rota nuvem (workflow_dispatch — sempre estes inputs)

Disparar `dbz-scan.yml` no repo `matheuscllm-lgtm/myp-arbitrage-scanner`,
`ref: main`, com EXATAMENTE:
- `sections` = a(s) seção(ões) do grupo escolhido (ex.: `dbsfusion`);
- `editions` = a lista verbatim do grupo (seção acima), com as aspas;
- demais inputs nos defaults (threshold 30 / min_price 50 / delay 1.5).

Depois: monitorar o run até `completed`; baixar o artifact
**`myp-dbz-consolidated-<run_id>`**; usar o `.md` de dentro (já gerado pelo
`myp_dbz_summary.py`) ou regenerá-lo do XLSX. Um grupo por vez — só disparar
o próximo depois de ENTREGAR o anterior (o concurrency group `myp-scan`
também impede simultâneos, inclusive com scans Pokémon).

### Rota local (sempre este comando)

```bash
python myp_dbz_scanner.py \
  <--sections e --editions DO GRUPO ESCOLHIDO, verbatim acima> \
  --threshold 30 --min-price 50 --delay 1.5 \
  -o results/dbz_grupoN_<AAAA-MM-DD>.xlsx --resume
```

- **`--resume` é obrigatório**: se o processo morrer, re-rodar o MESMO
  comando retoma do checkpoint (`<output>.xlsx.resume.json`).
- Em background/detached; um grupo por vez, sequencial. Nunca 2 scans no
  mesmo IP (nem junto com um scan Pokémon).
- `--threshold 30` é percent INTEIRO (convenção MYP; CardTrader usa fração).

## Passo 3 — entregar (ritual FIXO, contrato do repo, não negociável)

```bash
python myp_dbz_summary.py results/dbz_grupoN_<AAAA-MM-DD>.xlsx -o results/dbz_grupoN_<AAAA-MM-DD>.md
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
  parser herdado do scanner Pokémon.
- **Nunca inventar preço**: carta sem referência tcgcsv sai na seção
  "Sem referência TCG" com motivo — não existe fallback `.estat-tcg` no DBZ
  (decisão v1; referência real ou nada).
- Join determinístico por código de carta/variante (`dbsm_bt1-073_spr` →
  produto `(SPR)` do TCGplayer; nunca casar variante com base) — detalhe no
  cabeçalho do `myp_dbz_scanner.py`.
- Este skill é DBZ-only; o Pokémon segue no `scan-myp` (6 grupos próprios).
  Não misturar grupos dos dois skills num mesmo run.
