# CLAUDE.md — instruções para agentes (Claude Code) neste repo

> Objetivo: "rodar o MYP scanner" tem **um caminho só**. Siga este arquivo e
> evite re-descobrir coisas que já estão resolvidas no código.

## ▶️ Retomar de onde paramos (leia primeiro)

Ao retomar, **leia antes de agir** o handoff canônico:
[`SESSION-HANDOFF.md`](SESSION-HANDOFF.md). É o **único** handoff ativo (nome
fixo, a verdade mora no `main`) — diz o que foi feito, onde paramos e o próximo
passo. **Não crie um handoff datado por sessão** (`SESSION-HANDOFF-<data>.md`):
atualize o `SESSION-HANDOFF.md` e deixe a verdade no `main` — branches/PRs são
propostas. Depois use o resto deste arquivo pro "como rodar".

## Este é o repo canônico

`matheuscllm-lgtm/myp-arbitrage-scanner` é a **fonte de verdade única** do MYP
scanner (extraído do antigo monorepo `tcg-arbitrage-scanners` em 2026-05-13).
Se você encontrar um `myp_arbitrage_scanner.py` em qualquer outro lugar
(`tcg-arbitrage-scanners`, `Scripts/`, cópia em Drive/Obsidian), é **STALE
pré-extração** — não rode. Confira o cabeçalho: `Versão: v5.10` (ou superior).

## Setup (env novo)

```bash
pip install -r requirements.txt   # cloudscraper, bs4, lxml, openpyxl, brotli
export PYTHONIOENCODING=utf-8      # Windows PowerShell: $env:PYTHONIOENCODING="utf-8"
```
`brotli` é **obrigatório**: a Cloudflare serve `Content-Encoding: br`; sem ele o
HTML volta cru e o parser acha 0 edições silenciosamente.

## ⚠️ Cloudflare — NÃO perca tempo testando fingerprint

A Cloudflare bloqueia o fingerprint **chrome** do cloudscraper (HTTP **403**).
**Não** "valide" o acesso com um `cloudscraper.create_scraper()` puro — ele vai
dar 403 e te levar a uma falsa pista de bloqueio. O scanner **já resolve isso**:
usa `browser={"browser":"firefox","platform":"windows"}` por padrão (env
`MYP_CLOUDSCRAPER_BROWSER`, default `firefox`), que retorna **200**. Apenas rode
o scanner.

## Rodar

```bash
python myp_arbitrage_scanner.py --editions "Ascended Heroes" \
  --threshold 30 --min-price 50 --delay 1.5 \
  -o results/<set>_<stamp>.xlsx
```

- `--editions` = **substring** do título da edição MYP (ex.: `"Ascended Heroes"`
  casa `"ME: Ascended Heroes"`; `Mega` casa todos os ME0x). Não são aliases.
- `--threshold` é **percent integer** (`30` = 30%; valor <1.0 auto-converte com
  warning). Convenção oposta à do CardTrader scanner (lá é fração). Default
  **30** desde v5.10.
- **Margem é BRUTA pura** (política cross-scanner 2026-06-06): o número reportado
  é só `(preço_alvo TCG − preço_BR) / preço_BR`, **SEM nenhuma taxa/fee/markup
  embutido** no cálculo (diferente do CardTrader, que usa `custo = preço × 1.06`).
  O operador calcula frete/câmbio/comissão por fora. **Não** adicionar
  multiplicador de custo ao cálculo de margem.
- **Preço TCG = TCGplayer REAL via pokemontcg.io (v5.11)**, convertido USD→BRL
  com câmbio ao vivo. O campo `.estat-tcg` do MYP **não** é mais a fonte primária
  (ele mapeava a carta errada em Black Bolt/White Flare base-086 → preço furado);
  vira **fallback** só onde o pokemontcg.io não cobre. A conversão de moeda **não**
  é taxa — é só pra comparar BRL com BRL. **Defina `POKEMONTCG_API_KEY`** (env;
  key grátis em dev.pokemontcg.io, 20k req/dia): elimina o throttle 429
  (backoff 5/15/30s) **e** ativa o sleep adaptativo de 0.3s (v5.11.2) — num
  scan quick de 8 edições o ganho passa de **15-24 min**. No PowerShell:
  `$env:POKEMONTCG_API_KEY="..."` (ou User env var pra persistir).
  - ✅ **Onde a key mora (3 lugares automáticos, setados 1× pelo operador):**
    1. **CI (workflows):** secret do GitHub Actions `POKEMONTCG_API_KEY`
       (*Settings → Secrets and variables → Actions*). Os 3 workflows
       (daily/weekly/quick) injetam no `env` do step de scan sozinhos (desde
       #30). Toda run de workflow já usa — automático. *(Nota 2026-06-18: o
       operador decidiu **não** custear o GitHub Actions; o fluxo de CI fica
       inativo até regularizar billing — priorize o run LOCAL abaixo.)*
    2. **Máquina local do operador (fluxo canônico — local-first):**
       `POKEMONTCG_API_KEY` setada como **variável de ambiente de usuário do
       Windows** (`[Environment]::SetEnvironmentVariable("POKEMONTCG_API_KEY",
       "<key>", "User")`). Persiste entre reinícios; **toda sessão/terminal
       novo** já nasce com a key no `os.environ`. ⚠️ Setar em escopo User **não**
       atualiza um processo/sessão já aberto — vale a partir do próximo shell
       (ou exporte inline na sessão atual).
    3. **Sessões Claude Code na nuvem (run local no container):** configure
       `POKEMONTCG_API_KEY` como **variável de ambiente do environment** do
       Claude Code (config do environment em code.claude.com). Aí **toda sessão**
       já nasce com a key no `os.environ` — o scanner usa automático, sem
       re-passar. (Container é efêmero; export manual no shell só vale a sessão
       atual.)
    - **Nunca** commitar o valor da key em arquivo (o repo é versionado).
      Obter/conferir/rotacionar a key: **dev.pokemontcg.io** → Dashboard.
- `--min-price 50` = piso de relevância ("carta valiosa" > R$50). É **filtro**,
  não taxa — fica fora do cálculo de margem.
- Scan é **lento por design** (`--delay` × centenas de produtos × N edições →
  pode passar de 1h em scan largo). Para runs longos, rode detached/background.
- Single-session sequencial. **Não paralelize fetches no mesmo IP** (a v5.9 segue
  paginação `?estoque-outros-page=N` da tabela marketplace; 2 sessões no mesmo IP
  = 403 CF).
- **Jeito RÁPIDO de rodar o quick (2026-06-10): workflow `Quick MYP Scan
  (chunked)`** — `gh workflow run quick-scan.yml` (ou pela aba Actions). Cada
  chunk roda num runner do GitHub com **IP próprio** (sem conflito de CF), 6
  chunks default ≈ **10-15 min** de relógio pras 11 edições do quick
  (principais SV + Ascended Heroes/Perfect Order/Chaos Rising). Usa o secret
  `POKEMONTCG_API_KEY` (sleep adaptativo, sem 429). Sai XLSX consolidado como
  artifact + `results/latest-quick.md` commitado. Edições custom: input
  `editions` (multi-palavra entre aspas — o quick parseia certo via `eval
  set --`; o weekly tem bug latente com multi-palavra no `$ARGS` cru).

## Otimizar o scanner (loop iterativo)

Pra otimizar (velocidade/correção/custo/qualidade) há **um caminho só**: o loop
iterativo de dev documentado em
[`docs/optimization-loop.md`](docs/optimization-loop.md) — *medir
(`python bench.py`) → mudar → verificar (`python test_v5_8_offline.py`) →
repetir*. Não improvise: o playbook tem o ciclo, as ferramentas por passo e o
backlog priorizado. **Não** existe comando "loop engineering"; a skill `/loop` é
só agendador.

## Saída e commit

- Outputs vão pra `results/` como **subproduto de trabalho local** — **tudo
  gitignored de propósito**: o `.xlsx` (`*.xlsx`) **e** o resumo markdown
  (`results/*.md`). **Repo é público + discreto (desde #47/#49):** dados de deal
  (margens, preços, cartas) **NÃO entram no repo**. A **entrega é a tabela no
  chat** (gerada pelo `myp_summary.py` — ver seção 📤 abaixo); o `.md` é só o
  insumo que você cola/mostra, não um arquivo versionado. Resultados são
  reproduzíveis re-rodando o scan localmente, então não há perda em não commitar.
- Mudanças de **código/doc** (scanner, summary, este CLAUDE.md, etc.) seguem o
  workflow normal = **branch + PR** (não dê push direto em `main`; ele é gateado).
  Só **dados de scan** é que ficam fora do repo.

## Não confundir

Existe um scanner irmão de **CardTrader** (repo `card-trader-scanner`, usa
`.venv`, `--max-expansions`, threshold **fracionário**). É outro projeto.

---

## 📤 Entrega de resultados — tabela na plataforma, NUNCA arquivo

**Regra dura (operador, 2026-06-06). Vale para TODOS os scanners (CardTrader / MYP / Liga / sealed / PSA).**

O resultado de um scan é entregue ao operador **como tabela no chat do Claude Code** — no **terminal ou no app**. **NÃO** entregar como arquivo `.xlsx`/`.csv` para download por padrão.

- O scanner/postprocess **pode escrever** uma planilha local como subproduto de trabalho (gitignored) — tudo bem. O ponto é a **ENTREGA**: ela é a tabela na plataforma, não um anexo de arquivo.
- Gerar/anexar arquivo **só quando o operador pedir explicitamente** (ex.: "me manda o XLSX pra importar em lote"). Sem pedido = sem arquivo.
- A tabela traz **todos** os deals (não amostra curada) + as colunas relevantes da fonte.

### ⛔ Formato da entrega é OBRIGATÓRIO — gere via `myp_summary.py`, NUNCA monte tabela à mão

**Regra dura (operador, 2026-06-13). Não negociável, para qualquer agente — inclusive
um Claude Code da nuvem que clonou este repo.**

Quando você for **entregar o resultado de um scan**, há **um caminho só**:

> **Rode `myp_summary.py` sobre o XLSX do scan e cole/mostre o markdown que ele
> gerou.** Você **não** redesenha, reordena nem reescreve a tabela. Você **não**
> monta uma tabela "na mão" a partir dos números do XLSX num layout antigo
> (sem links, com colunas diferentes). A formatação canônica vive **dentro** do
> `myp_summary.py` — é a única fonte de verdade do formato. Se a entrega que você
> está prestes a colar **não** veio do `myp_summary.py`, **pare e gere por ele.**

Em português simples pro operador: o "jeito certo de te mostrar os deals" está
programado no script. O agente sempre roda o script e te entrega o que saiu —
nunca improvisa um formato diferente.

#### O que o `myp_summary.py` gera (e que você entrega assim, sem mexer)

São **três tabelas**, e **TODAS as três** trazem a coluna **`Carta`** (nome +
número) e a coluna **`Links`** (`[oferta](url_MYP) · [TCG](url_TCGplayer)`):

1. **🟢 Top 50 deals limpos** (sem flag SIR/HR/SAR — os confiáveis). Colunas, nesta ordem:
   ```
   | # | Margem % | MYP R$ | TCG US$ | Dif | Carta | Set | Raridade | Cond | Qtd | Links |
   ```
2. **⚠️ Deals com flag supranumerário** (`card_num > set_total`, ex. `226/217` —
   raridade dita "Comum" no MYP mas provavelmente IR/SIR/SAR). Marcados
   **"(validar manualmente)"** no título da seção. Colunas:
   ```
   | # | Carta | Edição | MYP R$ | TCG R$ | Margem (suspeita) | Links |
   ```
3. **🚨 Deals com flag TCG suspect** (preço TCG declarado destoa da última venda —
   mapeamento de carta provavelmente furado). Também **"(validar manualmente)"**.
   Colunas:
   ```
   | # | Carta | Edição | MYP R$ | TCG decl R$ | Última venda R$ | Margem (fake) | Links |
   ```

Significado das colunas:

- **`Carta`** = nome + número do colecionador numa coluna só (ex. `Pikachu 173/165`).
  Se o nome já embute o número, **não duplica** (helper `carta_label`).
- **`Links`** = **dois links markdown clicáveis**: `oferta` → página do produto MYP
  (conferir preço/seller); `TCG` → produto/busca TCGplayer pro **workflow manual de
  validação do preço NM**. **Os dois links são LIDOS do XLSX** — `oferta` da coluna
  `URL`, `TCG` da coluna `TCG URL` (texto plano, v5.11.2). **NUNCA invente, adivinhe
  ou "monte" uma URL** — se a coluna não tem link, a célula fica sem aquele link, e
  ponto. (O `myp_summary.py` cai num redirect/busca por nome só internamente, via
  helper; você não fabrica URLs.)
- **`TCG US$`** = preço **real** do TCGplayer em USD (via pokemontcg.io). `—` onde
  só houve fallback `.estat-tcg` (sem USD real).
- **`Dif`** = lucro **bruto** em R$ (`TCG R$ − MYP R$`). A margem segue BRUTA pura.
- **`Cond`** = `NM` (invariante NM-only).
- **`Qtd`** = nº de ofertas EN-NM (`NM Sellers`). O scanner **não** captura estoque
  por seller, então é a contagem de ofertas EN-NM, não unidades.

#### Mostre TODOS os deals — nada de amostra curada

A entrega traz **todos** os deals de cada bucket (limpos / supranumerário / suspeito),
**não** uma seleção curada de "os melhores". Os buckets supranumerário e suspeito
**sempre** vão marcados como **"validar manualmente"** com o caveat de que a
margem pode ser falsa (mapeamento de carta errado / variante misclassificada).
Você reporta margem, flags e fontes; **a decisão de comprar é do operador** — não
rankeie "BUY NOW" nem recomende capital.

#### Comando literal pra gerar a entrega

```bash
# scan diário/quick (hot sets) → use --type daily
python myp_summary.py results/<scan>.xlsx --type daily  -o results/<scope>-<data>.md

# scan semanal (catálogo completo) → use --type weekly
python myp_summary.py results/<scan>.xlsx --type weekly -o results/<scope>-<data>.md
```

- `--type` aceita **só `daily` ou `weekly`** (afeta título + tags do markdown).
  **Não existe `--type quick`** — o **scan quick usa `--type daily`** (é o que o
  `quick-scan.yml` faz). Passar um valor fora desses dois faz o script errar com
  argparse.
- `-o`/`--output` é **obrigatório** (o script grava o `.md`; você abre/cola o conteúdo).
- O markdown gerado é o que você entrega no chat (terminal **ou** app). Lembre:
  **entrega = tabela na plataforma**, arquivo `.xlsx`/`.csv` **só** se o operador
  pedir explicitamente.

#### O XLSX é matéria-prima, NÃO é a entrega

O XLSX/CSV continua com **colunas separadas e URLs cruas** (`Card Name`, `Edition`,
`URL`, …) + a coluna `TCG US$` (v5.11.1) + a coluna `TCG URL` (v5.11.2, texto plano,
última coluna — é de onde a entrega lê o link TCGplayer, e que o scanner integrado
consome). O formato composto (`Carta` + `Links` clicáveis) **só** existe na tabela
markdown de entrega que o `myp_summary.py` produz. Ou seja: o XLSX é o insumo; a
entrega é o markdown do `myp_summary.py`. **Não tente entregar o XLSX "formatado à
mão" — rode o script.**
