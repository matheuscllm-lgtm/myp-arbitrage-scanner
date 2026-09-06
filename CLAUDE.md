> **Regra vigente de entrega:** [DELIVERY_CHAT.md](DELIVERY_CHAT.md). Resultados somente no chat, referência clicável e coleta nova por solicitação; substitui orientações antigas de entrega via GitHub ou preços reutilizados.

# CLAUDE.md — myp-arbitrage-scanner

Scanner de arbitragem de singles Pokémon (EN, Near Mint): compara preços no
**mypcards.com** (BR, R$) contra o preço real do **TCGplayer** (US$→R$) e lista
deals com margem bruta ≥ 30%. Instruções para qualquer sessão Claude Code
(local ou nuvem) que trabalhe neste repo: "rodar o MYP scanner" tem **um
caminho só** — siga este arquivo e evite re-descobrir o que já está resolvido.

## 🚨 CONTRATO DE ENTREGA (LEIA ANTES DE MOSTRAR QUALQUER RESULTADO)

> **Erro recorrente real (2026-06-26):** o agente rodou o `myp_summary.py` (que
> já gera certo), mas **remontou a tabela à mão** e **dropou o link `[TCG]` de
> referência** pra "economizar largura". Isso quebra o padrão. NÃO repita.

**Toda linha entregue tem que ter os DOIS links, sempre, em TODO bucket**
(limpos, supranumerário, suspeito, fallback, e qualquer verificação manual):
- **`[oferta]`** → página do produto MYP (onde comprar);
- **`[TCG]`** → TCGplayer/referência (onde validar o preço).

**Caminho único:** rode `myp_summary.py` sobre o XLSX e **cole a saída VERBATIM**
(ela já põe `Carta` = nome+número e `Links` = `[oferta](url) · [TCG](url)` em
cada linha, lidos das colunas `URL` e `TCG URL` do XLSX). **PROIBIDO** remontar,
reformatar, renomear/reordenar colunas ou tirar um link. Se a entrega não saiu
do `myp_summary.py`, **pare e gere por ele**. Verificação que a ferramenta não
cobre (ex.: promos sem preço real) **ainda** leva os 2 links por linha. Detalhe
completo na seção 📤 lá embaixo. Contrato fleet-wide no `~/.claude/CLAUDE.md`.

## 🛰️ Convenções da frota (cross-scanner)

> **Manual completo** (repo privado): https://github.com/matheuscllm-lgtm/scanners-commons — erros comuns, referências de preço, chaves, GitHub Actions e modelo de entrega de TODOS os scanners. Cópia-mestra local (PC do operador): `C:\Users\mathe\scanners-commons\`.

Invariantes que valem para TODOS os scanners:

- **Margem BRUTA, mínimo 30%** — só `(revenda − compra)/compra`, sem nenhuma taxa embutida (frete, cartão, IOF — o operador calcula por fora).
- **Piso de relevância R$50 (~US$10) — SÓ para cartas avulsas (singles).** Produtos SELADOS não têm piso (decisão do operador, 2026-06-27); lá o único critério é a margem ≥30%.
- **Só Near Mint** — condição por match EXATO `== "NM"`, nunca substring (já vazou SP).
- **Nunca inventar preço** — fonte falhou → marca fallback/erro e segue; jamais fabrica número.
- **Nunca recomendar compra** — o scanner reporta margem, flags e fontes; a decisão de capital é do operador.
- **Entrega = tabela markdown no chat** (nunca XLSX/CSV por padrão), gerada pela ferramenta do repo — nunca montada à mão —, mostrando TODAS as linhas (aprovadas + rejeitadas). Coluna `Carta` = nome + número; coluna `Links` combinada = `[oferta](url) · [TCG/referência](url)`.
- ⚠️ **Convenção de threshold:** percentual inteiro (`30`) = MYP, Liga, eBay; fração (`0.30`) = CardTrader, COMC, Selados.

Erros recorrentes (3 famílias — detalhe no manual):

1. **Segredo/ambiente:** BOM/zero-width numa chave → crash latin-1 no header → scan "verde mas vazio". Setar sem BOM (`printf '%s' 'KEY' | gh secret set`) **e** sanitizar ao ler no código (`.strip()` NÃO tira BOM).
2. **Git:** branch ou `main` local defasado por squash-merge PARECE pendência. O teste real de "já mergeado" é `git diff --stat origin/main <branch>` estar vazio (não `git merge-base`).
3. **Honestidade de preço:** inflação de referência, fallback tratado como real, NM frouxo → sempre validar versão/condição e rotular fallback.

**Este scanner:** referência de preço = `tcgcsv.com` (real, na nuvem via `--tcg-source tcgcsv`; mapa de sets ampliado em v5.16 e de novo em v5.18/v5.19 — cobertura ME: Perfect Order me3, Chaos Rising me4, Pitch Black me5) → pokemontcg.io (secundário) → `.estat-tcg` (fallback rotulado); chaves = `POKEMONTCG_API_KEY` (preço) e `FIRECRAWL_API_KEY` (canário `drift_check.py` no daily).

## ▶️ Retomar de onde paramos (leia primeiro)

Ao retomar, **se existir** um `SESSION-HANDOFF.md` na raiz, **leia-o antes de
agir**: é o handoff canônico (nome fixo) — diz o que foi feito, onde paramos e o
próximo passo. ⚠️ Esse arquivo é **local-only / gitignored** (`.gitignore`): foi
tirado do repo no preparo de release público (#47) e **não vem num clone limpo**
(ex.: sessão Claude Code na nuvem) — sua ausência é **esperada**, não é erro.
Sem ele, a **fonte de verdade é o `main` + `CHANGELOG.md`** (o estado real mora
no código mergeado; branches/PRs são propostas). **Não crie um handoff datado por
sessão** (`SESSION-HANDOFF-<data>.md`): se for manter um handoff, atualize o
`SESSION-HANDOFF.md` local. Depois use o resto deste arquivo pro "como rodar".

## Este é o repo canônico

`matheuscllm-lgtm/myp-arbitrage-scanner` é a **fonte de verdade única** do MYP
scanner (extraído do antigo monorepo `tcg-arbitrage-scanners` em 2026-05-13).
Se você encontrar um `myp_arbitrage_scanner.py` em qualquer outro lugar
(`tcg-arbitrage-scanners`, `Scripts/`, cópia em Drive/Obsidian), é **STALE
pré-extração** — não rode. Confira o cabeçalho: `Versão: v5.19.3` (ou
superior; a versão atual vive no cabeçalho de `myp_arbitrage_scanner.py` e no
topo do `CHANGELOG.md` — histórico completo, uma entrada por versão, mora lá).

## Setup (env novo)

```bash
pip install -r requirements.txt   # cloudscraper, bs4, lxml, openpyxl, brotli
export PYTHONIOENCODING=utf-8      # Windows PowerShell: $env:PYTHONIOENCODING="utf-8"
```

- `brotli` é **obrigatório**: a Cloudflare serve `Content-Encoding: br`; sem ele
  o HTML volta cru e o parser acha 0 edições silenciosamente.
- **Python 3.12** é o requisito (o CI fixa 3.12 em `tests.yml`; a suíte de
  testes usa f-string com backslash — `SyntaxError` em 3.11).

## ⚠️ Cloudflare — NÃO perca tempo testando fingerprint

A Cloudflare bloqueia o fingerprint **chrome** do cloudscraper (HTTP **403**).
**Não** "valide" o acesso com um `cloudscraper.create_scraper()` puro — ele vai
dar 403 e te levar a uma falsa pista de bloqueio. O scanner **já resolve isso**:
usa `browser={"browser":"firefox","platform":"windows"}` por padrão (env
`MYP_CLOUDSCRAPER_BROWSER`, default `firefox`), que retorna **200**. Apenas rode
o scanner.

## Rodar

> 🎯 **Skill `scan-myp`** (`.claude/skills/scan-myp/SKILL.md`, 2026-07-02):
> o catálogo mapeado (~112 edições com preço TCG real) está dividido em
> **6 grupos por recência**, cada um dimensionado pra **≤ ~2h30 de scan**
> (grupo 1 = era Mega Evolution até Chaos Rising + SV recente). Quando o
> operador pedir pra "rodar o MYP", o agente **pergunta quais grupos rodar**
> e roda um por vez com `--resume` — defesa contra scans longos que morrem
> sem entregar. As listas de substrings dos grupos estão no skill (verbatim
> do `MYP_EDITION_SUBSTR_TO_PTCG`; validadas por script — nunca editar de
> cabeça).

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
- `--min-price 50` = piso de relevância ("carta valiosa" > R$50). É **filtro**,
  não taxa — fica fora do cálculo de margem.
- Outras flags úteis: `--max-editions N` / `--max-products N` (limitar escopo,
  útil em smoke test), `--min-en-sellers N`, `--resume` (retoma scan que caiu),
  `--chunk-index` / `--chunk-total` (particionam as edições — é o que os
  workflows chunked usam). `--help` lista tudo.
- Scan é **lento por design** (`--delay` × centenas de produtos × N edições →
  pode passar de 1h em scan largo). Para runs longos, rode detached/background.
- Single-session sequencial. **Não paralelize fetches no mesmo IP** (a v5.9 segue
  paginação `?estoque-outros-page=N` da tabela marketplace; 2 sessões no mesmo IP
  = 403 CF).
- Existe também o comando `/auto` da frota (`.claude/commands/auto.md`) — modo
  autônomo master; use quando o operador o invocar.

### Preço TCG: fontes e onde a key mora

- **Preço TCG = TCGplayer REAL (v5.11+)**, convertido USD→BRL com câmbio ao
  vivo. O campo `.estat-tcg` do MYP **não** é a fonte primária (ele mapeava a
  carta errada em Black Bolt/White Flare base-086 → preço furado); vira
  **fallback** só onde não houver preço real. A conversão de moeda **não** é
  taxa — é só pra comparar BRL com BRL.
- **v5.15 — duas rotas pro mesmo preço real (flag `--tcg-source`):**
  - **`tcgcsv`** (dump diário grátis do TCGplayer via `tcgcsv.com`) é a **ÚNICA
    fonte que funciona nos runners do GitHub Actions** — é o que o **CI usa**
    (os 3 workflows de scan passam `--tcg-source tcgcsv`). Cross-check confirmou
    que tcgcsv = pokemontcg.io em **0–0,3%** (mesmo preço TCGplayer), e tcgcsv
    ainda TEM preço pros sets **ME** (Ascended Heroes etc.) que a pokemontcg.io
    devolve sem preço. Não usa key. O mapa de sets tcgcsv foi ampliado em
    v5.16, v5.18 (Chaos Rising me4/CRI + Perfect Order me3/POR) e v5.19
    (Pitch Black me5/ME05).
  - **`pokemontcg`** (`api.pokemontcg.io`) é o caminho **local** clássico (o
    PC alcança; os runners do GitHub não). Precisa de `POKEMONTCG_API_KEY` pra
    evitar throttle 429.
  - **`auto`** (default): tcgcsv primeiro; pokemontcg.io complementa por set
    sem groupId tcgcsv. Em qualquer modo, sem fonte real = fallback honesto.
- **`POKEMONTCG_API_KEY`** (env; key grátis em dev.pokemontcg.io, 20k req/dia):
  elimina o throttle 429 (backoff 5/15/30s) **e** ativa o sleep adaptativo de
  0.3s (v5.11.2) — num scan quick de 8 edições o ganho passa de **15-24 min**.
  No PowerShell: `$env:POKEMONTCG_API_KEY="..."` (ou User env var pra persistir).
- ✅ **Onde a key mora (3 lugares automáticos, setados 1× pelo operador):**
  1. **CI (workflows):** secret do GitHub Actions `POKEMONTCG_API_KEY`
     (*Settings → Secrets and variables → Actions*). Os 3 workflows de scan
     (daily/weekly/quick) injetam no `env` do step de scan sozinhos (desde
     #30). *(Atualização 2026-06-20: os repos foram tornados **públicos** →
     minutos de GitHub Actions são gratuitos.)*
     - ✅ **CI serve preço REAL sozinho (v5.15 — supersede o 🛑 de
       2026-06-20):** os runners do GitHub **não alcançam** `api.pokemontcg.io`
       (CF da API bloqueia os IPs de datacenter — achado 2026-06-20, ainda
       vale pra **essa** fonte). A v5.15 resolveu **trocando a fonte do CI** pro
       **`tcgcsv.com`**, que o runner **ALCANÇA** (sonda `probe-price-sources.yml`
       run `27918333945`: HTTP 200, JSON real) e que tem o **mesmo** preço
       TCGplayer (cross-check 0–0,3%). Os 3 workflows passam `--tcg-source
       tcgcsv` → o CI entrega preço **real** (`TCG Source = real (tcgcsv)`),
       sozinho, **sem nenhum passo manual de enriquecimento**. A
       `POKEMONTCG_API_KEY` continua injetada, mas é **irrelevante** em modo
       tcgcsv (o tcgcsv não usa key). O sinal real-vs-fallback segue
       **explícito** (coluna `TCG Source` + linha "Cobertura de preço TCG real"
       do `myp_summary.py`): real = `pokemontcg.io`/`tcgcsv`, fallback =
       `.estat-tcg`. A cobertura é medida sobre **todas** as cartas EN
       (universo, aba `All EN Cards`), não sobre o balde de deals (v5.14.1).
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

### Workflows do GitHub Actions

Seis workflows em `.github/workflows/`:

- **`quick-scan.yml` — `Quick MYP Scan (chunked)` — o jeito RÁPIDO de rodar o
  quick (2026-06-10):** `gh workflow run quick-scan.yml` (ou pela aba Actions).
  Cada chunk roda num runner do GitHub com **IP próprio** (sem conflito de CF),
  6 chunks default ≈ **10-15 min** de relógio pras 11 edições do quick
  (principais SV + Ascended Heroes/Perfect Order/Chaos Rising). Usa o secret
  `POKEMONTCG_API_KEY` (sleep adaptativo, sem 429). Sai XLSX consolidado +
  `results/latest-quick.md` como **artifact do run — nunca commitado** (postura
  de repo público: dado de deal não entra no repo). Edições custom: input
  `editions` (multi-palavra entre aspas — o input chega via env
  `EDITIONS_INPUT` e é re-parseado com `eval set --`, então edição com
  apóstrofo, ex. "Champion's Path" do grupo 3 do scan-myp, também é segura).
- **`daily-scan.yml`** (hot sets, `--type daily`) e **`weekly-scan.yml`**
  (catálogo, `--type weekly`) — ambos com `--tcg-source tcgcsv`. O weekly
  também recebe `editions` via env `EDITIONS_INPUT` + `eval set --` (o antigo
  bug latente de multi-palavra no `$ARGS` cru foi corrigido). O daily roda o
  canário `drift_check.py` antes do scan (ver Arquitetura).
- **`tests.yml`** — CI de testes: `python -m pytest -q` em Python 3.12.
- **`probe-price-sources.yml`** — sonda de alcance das fontes de preço a
  partir dos runners; desde 2026-08-03 também carrega a sonda do catálogo
  Dragon Ball (`probe-myp-dragonball`) e o smoke real do scanner DBZ
  (`smoke-dbz-scanner`); desde 2026-08-09, a sonda do catálogo One Piece
  (`probe-myp-onepiece`) e o smoke real do scanner OP (`smoke-op-scanner`).
  Tudo roda em PR que toque o próprio arquivo.
- **`dbz-scan.yml`** ("DBZ MYP Scan") — rota NUVEM do scanner paralelo de
  Dragon Ball (ver seção própria). Só dispatch manual; resultado só como
  artifact.
- **`op-scan.yml`** ("OP MYP Scan") — rota NUVEM do scanner paralelo de
  One Piece (ver seção própria). Só dispatch manual; resultado só como
  artifact. (Sétimo workflow, 2026-08-09.)

## 🔀 Preço TCG REAL no catálogo COMPLETO

> **v5.17 — `myp_enrich.py` aposentado.** Não existe mais passo manual de
> enriquecimento off-runner. Desde a v5.15/v5.16 o **próprio workflow do GitHub
> já entrega preço TCGplayer real** (via `tcgcsv.com`, a fonte que os
> computadores do GitHub conseguem acessar): rode o workflow e o resultado já vem
> com preço de verdade (`TCG Source = real (tcgcsv)`), sozinho. O script
> `myp_enrich.py` (que injetava preço da pokemontcg.io num XLSX consolidado) virou
> redundante e foi removido — o caminho dele já está coberto pelo scanner local
> (default `auto`: tcgcsv + pokemontcg.io). Se um consolidado vier **0 preço
> real**, isso é uma **FALHA do tcgcsv** (indisponível, sets sem groupId, ou
> perda da fonte na agregação dos chunks) a **investigar** — não é mais "rode o
> enrich".

Quando você precisa de **preço TCG real no catálogo inteiro** (não só nos hot
sets de um scan local):

- **Mais simples:** rode o **workflow** — ele já entrega preço real (tcgcsv) no
  catálogo inteiro, sozinho. Baixe o XLSX consolidado e entregue via
  `myp_summary.py`.
- **Local:** rode o scanner **LOCAL** (`python myp_arbitrage_scanner.py …`) — o
  preço já nasce real (default `auto`: tcgcsv + pokemontcg.io). Pode passar de
  1h num scan largo; rode detached.

> **Honestidade (regra dura):** a coluna `TCG Source` do XLSX e a linha
> "Cobertura de preço TCG real" do `myp_summary.py` declaram, por card, se o
> preço é **real** (`tcgcsv`/`pokemontcg.io`) ou **fallback** (`.estat-tcg`,
> margem NÃO-confiável). **Nunca** trate fallback como real — o output não deixa.

## 📤 Entrega de resultados — tabela na plataforma, NUNCA arquivo

**Regra dura (operador, 2026-06-06). Vale para TODOS os scanners (CardTrader / MYP / Liga / sealed / PSA).**

O resultado de um scan é entregue ao operador **como tabela no chat do Claude Code** — no **terminal ou no app**. **NÃO** entregar como arquivo `.xlsx`/`.csv` para download por padrão.

- O scanner/postprocess **pode escrever** uma planilha local como subproduto de trabalho (gitignored) — tudo bem. O ponto é a **ENTREGA**: ela é a tabela na plataforma, não um anexo de arquivo.
- Gerar/anexar arquivo **só quando o operador pedir explicitamente** (ex.: "me manda o XLSX pra importar em lote"). Sem pedido = sem arquivo.
- A tabela traz **todos** os deals (não amostra curada) + as colunas relevantes da fonte.

### ⛔ Formato da entrega é OBRIGATÓRIO — gere via `myp_summary.py`, NUNCA monte tabela à mão

**Regra dura (operador, 2026-06-13). Não negociável, para qualquer agente — inclusive
uma sessão Claude Code da nuvem que clonou este repo.**

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

São até **quatro tabelas de deals** (a 4ª só aparece se houver deals com preço
fallback) — mais uma **5ª seção diagnóstica condicional** (`🚨 EN truncation
risk`, sobre o universo de cartas, não sobre deals; por isso é a única sem
coluna Links). **TODAS as tabelas de deals** trazem a coluna **`Carta`**
(nome + número) e a coluna **`Links`** (`[oferta](url_MYP) · [TCG](url_TCGplayer)`):

1. **🟢 Top 50 deals limpos** (sem flag SIR/HR/SAR **e com preço REAL** — os
   confiáveis). Colunas, nesta ordem:
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
4. **⚠️ Deals com preço FALLBACK `.estat-tcg`** (v5.14.3 — preço TCG é estimativa
   do MYP, **não** o real do TCGplayer; margem pode ser ILUSÓRIA). Saem do balde
   limpo de propósito; **"(validar manualmente)"**. Desde a v5.15 o CI usa
   `--tcg-source tcgcsv` e entrega preço REAL — um deal só cai neste balde
   (localmente ou no CI) quando **nenhuma** fonte real cobriu o set. Colunas:
   ```
   | # | Margem (estimada) | MYP R$ | TCG est. R$ | Dif (est.) | Carta | Set | Raridade | Cond | Qtd | Links |
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
- **`TCG US$`** = preço **real** do TCGplayer em USD (via `tcgcsv.com` ou
  pokemontcg.io — a coluna `TCG Source` do XLSX diz qual). `—` onde só houve
  fallback `.estat-tcg` (sem USD real).
- **`Dif`** = lucro **bruto** em R$ (`TCG R$ − MYP R$`). A margem segue BRUTA pura.
- **`Cond`** = `NM` (invariante NM-only).
- **`Qtd`** = nº de ofertas EN-NM (`NM Sellers`). O scanner **não** captura estoque
  por seller, então é a contagem de ofertas EN-NM, não unidades.

#### Mostre TODOS os deals — nada de amostra curada

A entrega traz **todos** os deals de cada bucket (limpos / supranumerário /
suspeito / fallback), **não** uma seleção curada de "os melhores". Os buckets
supranumerário, suspeito e fallback **sempre** vão marcados como **"validar
manualmente"** com o caveat de que a margem pode ser falsa (mapeamento de carta
errado / variante misclassificada / preço estimado). Você reporta margem, flags
e fontes; **a decisão de comprar é do operador** — não rankeie "BUY NOW" nem
recomende capital.

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
- Flags opcionais: `--run-id` (carimba o run do workflow no markdown) e
  `--repo` (default `matheuscllm-lgtm/myp-arbitrage-scanner`).
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

## Scanner paralelo: Dragon Ball (`myp_dbz_scanner.py`)

> **Pedido do operador (2026-08-03):** skill "MYP cards" para Dragon Ball no
> mesmo formato do Pokémon. Segue o precedente da frota (dbs/op scanners do
> card-trader-scanner): jogo paralelo = **script separado**, sem tocar o
> fluxo Pokémon (o modo `--game` embutido foi rejeitado lá, PR #56 fechado
> como superado).

- **O que faz:** varre as DUAS seções Dragon Ball do MYP — **`dbsfusion`**
  (Fusion World, 35 edições) e **`dbsmasters`** (DBS clássico, 88 edições),
  slugs provados pela sonda `probe-myp-dragonball` (PR #95) — com a MESMA
  infra de plataforma do scanner Pokémon (sessão cloudscraper firefox,
  parser de seller NM/EN herdado por import, paginação marketplace,
  checkpoint/`--resume`), e compara a menor oferta EN NM com o **market
  price do TCGplayer** via tcgcsv.com (**cat 80** = Fusion World, **cat
  27** = Masters; USD→BRL com câmbio ao vivo — sem câmbio real o run FALHA
  ALTO, não há fallback de preço no DBZ).
- **Join determinístico (nunca fuzzy), em camadas:** edição→grupo tcgcsv
  (nome exato → código de set canônico único, com classes de alias
  {B≡BT}/{BE≡EB≡EX} → contenção de nome única); carta por **código**
  ("FB11-112" no h1 do dbsfusion; no dbsmasters o código vem do campo
  `Código` da página — `dbsm_bt1-073_spr`, que também traz o **sufixo de
  variante**: `_spr` só casa o produto `(SPR)` do TCGplayer, nunca o base) e
  desambiguação por nome EN exato; sem código → grupo+nome exato. Ambíguo/
  sem match → aba **"Sem Ref TCG"** com motivo (nunca margem inventada; sem
  fallback `.estat-tcg` — decisão v1).
- **Convenções:** margem BRUTA base compra `(TCG_BRL − MYP_BRL)/MYP_BRL`;
  `--threshold` percent INTEIRO (30); piso R$50; NM/EN herdados; guardas da
  frota: oferta <50% da ref = flag **possível lixo**, market vs menor
  anúncio TCG >2× = flag **ref volátil** — ambos rebaixam pra REVISAR na
  entrega.
- **Entrega** = `myp_dbz_summary.py` (espelho do `myp_summary.py`): buckets
  🟢 limpos / 🚨 REVISAR (flag por linha) / ⚠️ Sem referência / 🚨 EN
  truncation, TODOS com `Carta` = nome+código e 2 links por linha
  (`[oferta] · [TCG]`; linha sem produto casado leva link de BUSCA). Colar
  VERBATIM — mesmo contrato de entrega do Pokémon.
- 🎯 **Skill `scan-myp-dbz`** (`.claude/skills/scan-myp-dbz/SKILL.md`):
  mesmo formato do `scan-myp` — 123 edições em **6 grupos por recência**
  (G1-G2 Fusion World, G3-G6 Masters), pergunta quais rodar, um por vez,
  rota nuvem = workflow `dbz-scan.yml` / rota local = `--resume`. Partição
  travada por `test_scan_dbz_skill_profiles.py` (cobertura 123/123, zero
  sobreposição).
- **Como rodar (fora do skill, debug):**

  ```bash
  python myp_dbz_scanner.py --list-editions
  python myp_dbz_scanner.py --sections dbsfusion --editions "Rivals Clash" \
    --threshold 30 --min-price 50 --delay 1.5 -o results/dbz.xlsx --resume
  python myp_dbz_summary.py results/dbz.xlsx -o results/dbz.md
  ```

- **Contratos travados em teste:** `test_myp_dbz_offline.py` (30 testes
  offline: parsing de título/edição/campo Código, join variant-aware SPR/Alt
  Art, escopo grupo-principal vs Release Event, threshold inteiro, XLSX +
  summary com 2 links) + `test_scan_dbz_skill_profiles.py` (4). Fatos de
  estrutura do site provados pela sonda estão no cabeçalho do scanner — não
  re-descobrir.

## Scanner paralelo: One Piece (`myp_op_scanner.py`)

> **Pedido do operador (2026-08-09):** skill "MYP cards" para One Piece no
> mesmo formato do Pokémon — mesmo precedente do Dragon Ball (PR #95):
> jogo paralelo = **script separado**, sem tocar o fluxo Pokémon.

- **O que faz:** varre a seção One Piece do MYP — **`/onepiece`** (65
  edições: OP01→OP17, ST01→ST-36, EB, PRB, LT, SD, promos; slug e catálogo
  provados pela sonda `probe-myp-onepiece`, PR #98, run 31300834735) — com
  a MESMA infra de plataforma do scanner Pokémon (sessão cloudscraper
  firefox, parser de seller NM/EN herdado por import, paginação
  marketplace, checkpoint/`--resume`), e compara a menor oferta EN NM com o
  **market price do TCGplayer** via tcgcsv.com (**cat 68** = One Piece Card
  Game, catálogo INGLÊS; USD→BRL com câmbio ao vivo — sem câmbio real o
  run FALHA ALTO, não há fallback de preço no OP).
- **Join determinístico (nunca fuzzy), em camadas:** edição→grupo tcgcsv
  (nome exato → código de set canônico único **sem** os aliases do DBZ —
  em One Piece EB = Extra Booster, nunca ≡ EX → contenção de nome única);
  carta por **código** do campo `Código` da página (`one_st-35_op13-004` —
  o código é o ÚLTIMO token com formato de carta, porque o token de edição
  também tem hífen) com escopo em camadas (grupo da edição → grupos
  principais → global — crítico: starter decks REIMPRIMEM números OPxx com
  produto/preço próprios no tcgcsv); desambiguação por nome com a
  equivalência de vocabulário **{"(Alternate Art)" MYP ≡ "(Parallel)"
  TCGplayer}** e a regra dura: nome qualificado nunca casa o produto base
  (nem vice-versa). ⚠️ O marcador `p1` do campo Código **NÃO** é sinal de
  variante — a sonda provou par com códigos invertidos (Edward.Newgate
  OP17-001); quem marca variante é o qualificador do h1. Ambíguo/sem
  match → aba **"Sem Ref TCG"** com motivo (nunca margem inventada; sem
  fallback `.estat-tcg` — decisão v1, igual ao DBZ).
- **Convenções:** margem BRUTA base compra `(TCG_BRL − MYP_BRL)/MYP_BRL`;
  `--threshold` percent INTEIRO (30); piso R$50; NM/EN herdados (idioma é
  o risco nº 1 em One Piece — lição do op_scanner do card-trader; o filtro
  EN herdado é o guard); guardas da frota: oferta <50% da ref = flag
  **possível lixo**, market vs menor anúncio TCG >2× = flag **ref
  volátil** — ambos rebaixam pra REVISAR na entrega.
- **Entrega** = `myp_op_summary.py` (espelho do `myp_dbz_summary.py`):
  buckets 🟢 limpos / 🚨 REVISAR (flag por linha) / ⚠️ Sem referência /
  🚨 EN truncation, TODOS com `Carta` = nome+código e 2 links por linha
  (`[oferta] · [TCG]`; linha sem produto casado leva link de BUSCA). Colar
  VERBATIM — mesmo contrato de entrega do Pokémon.
- 🎯 **Skill `scan-myp-op`** (`.claude/skills/scan-myp-op/SKILL.md`):
  mesmo formato do `scan-myp` — 65 edições em **6 grupos por recência**,
  pergunta quais rodar, um por vez, rota nuvem = workflow `op-scan.yml` /
  rota local = `--resume`. Partição travada por
  `test_scan_op_skill_profiles.py` (cobertura 65/65, zero sobreposição).
- **Como rodar (fora do skill, debug):**

  ```bash
  python myp_op_scanner.py --list-editions
  python myp_op_scanner.py --editions "Romance Dawn" \
    --threshold 30 --min-price 50 --delay 1.5 -o results/op.xlsx --resume
  python myp_op_summary.py results/op.xlsx -o results/op.md
  ```

- **Contratos travados em teste:** `test_myp_op_offline.py` (27 testes
  offline: normalização OP com número curto "(001)", equivalência
  Alternate Art≡Parallel, campo Código one_ com último-token, joins por
  escopo incl. reprint de starter deck, box topper, threshold inteiro,
  XLSX + summary com 2 links) + `test_scan_op_skill_profiles.py` (4).
  Fatos de estrutura do site provados pela sonda estão no cabeçalho do
  scanner — não re-descobrir. Cache tcgcsv próprio em `results/op_cache/`
  (nunca compartilhado com o `dbz_cache/`).

## Testes

```bash
python -m pytest -q               # suíte completa (é o que o CI roda em tests.yml)
python test_v5_8_offline.py       # runner standalone offline (mesma suíte principal)
```

- Requer **Python 3.12** (f-string com backslash na suíte → `SyntaxError` em 3.11).
- O pytest coleta `test_v5_8_offline.py` **e** `scripts/test_validate_setcode_map.py`.
- Tudo offline, sem rede/segredos. Não commite mudança de código com teste vermelho.

## Otimizar o scanner (loop iterativo)

Pra otimizar (velocidade/correção/custo/qualidade) há **um caminho só**: o loop
iterativo de dev — **medir → mudar → verificar → repetir**:

1. **Medir** o baseline: `python bench.py > before.txt` (modo mockado, sem rede).
   No default (`--tcg-source auto`, a rota tcgcsv do CI/prod, v5.19.2) as
   métricas-chave são `tcgcsv_prefill_sets`/`tcg_from_tcgcsv` — e `ptcg_calls`
   fica **0 por design** (a pokemontcg.io não é tocada quando o tcgcsv cobre o
   set). Pra medir a rota legada (métrica `ptcg_calls`, os round-trips à
   pokemontcg.io), rode `python bench.py --tcg-source pokemontcg`. `--live`
   mede tempo real contra o site + a fonte (aceita `--editions`,
   `--limit-products`; `--help` lista o resto).
2. **Mudar** uma coisa por vez (uma otimização isolada).
3. **Verificar**: `python bench.py > after.txt && diff before.txt after.txt`
   (ganho mensurável?) **e** `python -m pytest -q` tudo verde (ou o runner
   `python test_v5_8_offline.py`) — nenhuma regressão.
4. **Repetir**. Não improvise fora desse ciclo.

> O playbook detalhado (`docs/optimization-loop.md`) e seu backlog priorizado são
> **local-only / gitignored** (tirados do repo público no #47) — podem **não
> existir** num clone limpo; sua ausência é esperada. O ciclo acima é o
> essencial e basta. **Não** existe comando "loop engineering"; a skill `/loop` é
> só agendador.

## Arquitetura

```
myp_arbitrage_scanner.py   o scanner (MYP → preço TCG real → XLSX). Cabeçalho traz a versão
myp_summary.py             a ENTREGA canônica: XLSX → markdown (4 buckets de deals + seção diagnóstica condicional) — ver seção 📤
myp_dbz_scanner.py         scanner PARALELO de DRAGON BALL (dbsfusion+dbsmasters vs tcgcsv 80/27) — ver seção própria
myp_dbz_summary.py         a ENTREGA do scan DBZ (espelho do myp_summary.py)
myp_op_scanner.py          scanner PARALELO de ONE PIECE (/onepiece vs tcgcsv 68) — ver seção própria
myp_op_summary.py          a ENTREGA do scan OP (espelho do myp_dbz_summary.py)
myp_aggregate.py           agrega os XLSX dos chunks dos workflows num consolidado
bench.py                   micro-benchmark do loop de otimização (mockado; --live = real)
drift_check.py             canário de drift: roda ANTES do scan no daily workflow, valida
                           via Firecrawl (FIRECRAWL_API_KEY) 2 páginas canário (catálogo +
                           página de produto estável); site rebrandeou/markup mudou → falha
                           LOUD antes de gastar 30min de CI em HTML quebrado
test_v5_8_offline.py       suíte de testes offline (coletada pelo pytest)
test_myp_dbz_offline.py    suíte offline do scanner DBZ (30 testes)
test_scan_dbz_skill_profiles.py  trava a partição dos 6 grupos do skill DBZ
test_myp_op_offline.py     suíte offline do scanner ONE PIECE (27 testes)
test_scan_op_skill_profiles.py   trava a partição dos 6 grupos do skill OP
scripts/                   utilitários: validate_setcode_map.py (validação do mapa de
                           setcodes, com teste próprio no pytest), revalidate_deals.py,
                           cross_check_myp_api.py, add_card_hyperlinks.py,
                           run_weekly_local.ps1 (PC do operador)
experimental/              protótipos exploratórios, não-produção (ev_scanner_v01.py)
.github/workflows/         daily-scan / weekly-scan / quick-scan / dbz-scan / op-scan / tests / probe-price-sources
.claude/skills/scan-myp/       skill canônica de scan Pokémon (6 grupos)
.claude/skills/scan-myp-dbz/   skill de scan DRAGON BALL (6 grupos próprios)
.claude/skills/scan-myp-op/    skill de scan ONE PIECE (6 grupos próprios)
.claude/commands/auto.md   comando /auto da frota (modo autônomo)
```

> ⚠️ **Pegadinha do `myp_aggregate.py`:** o `--threshold` dele é **FRAÇÃO**
> (default `0.30` = 30%, classifica/colore as sheets do consolidado) —
> convenção **OPOSTA** à do scanner (percent inteiro `30`). Os workflows já
> passam o valor certo; se for rodar à mão, releia isto antes.

## Saída e commit

- Outputs vão pra `results/` como **subproduto de trabalho local** — o
  `.gitignore` ignora o diretório **`results/` inteiro** (além de `*.xlsx`
  globais, `*.resume.json`, logs, `.env`, `SESSION-HANDOFF*.md`,
  `docs/optimization-loop.md` etc.). **Repo é público + discreto (desde
  #47/#49):** dados de deal (margens, preços, cartas) **NÃO entram no repo**.
  A **entrega é a tabela no chat** (gerada pelo `myp_summary.py` — ver seção 📤
  acima); o `.md` é só o insumo que você cola/mostra, não um arquivo versionado.
  Resultados são reproduzíveis re-rodando o scan localmente, então não há perda
  em não commitar.
- Mudanças de **código/doc** (scanner, summary, este CLAUDE.md, etc.) seguem o
  workflow normal = **branch + PR** (não dê push direto em `main`; ele é gateado).
  Só **dados de scan** é que ficam fora do repo.
- Segredos (`POKEMONTCG_API_KEY`, `FIRECRAWL_API_KEY`) **nunca** vão em arquivo
  versionado — vivem em env vars/secrets (ver "Onde a key mora").

## Não confundir

Existe um scanner irmão de **CardTrader** (repo `card-trader-scanner`, usa
`.venv`, `--max-expansions`, threshold **fracionário** — ver a convenção de
threshold no bloco da frota). É outro projeto.

## Estado e histórico

- Versão atual: **v5.19.3** (2026-07-03). O histórico completo — uma entrada
  detalhada por versão, com racional de cada decisão — está no **`CHANGELOG.md`**
  (fonte de verdade do estado, junto com o `main`).
- **Pós-v5.19.3 mergeado** (scripts paralelos, fora do versionamento do
  scanner Pokémon): `myp_dbz_scanner.py` v1.0/v1.1 + `myp_dbz_summary.py` +
  skill `scan-myp-dbz` + workflow `dbz-scan.yml` (2026-08-03, PR #95;
  v1.1 no #97) — ver a seção "Scanner paralelo: Dragon Ball"; e
  `myp_op_scanner.py` v1.0 + `myp_op_summary.py` + skill `scan-myp-op` +
  workflow `op-scan.yml` (2026-08-09, PR #98) — ver a seção "Scanner
  paralelo: One Piece".
- Marcos já incorporados neste arquivo: margem bruta pura (2026-06-06), entrega
  obrigatória via `myp_summary.py` (2026-06-13), quick chunked no Actions
  (2026-06-10), balde fallback dedicado (v5.14.3), coluna `TCG Source` +
  cobertura sobre o universo EN (v5.14/v5.14.1), tcgcsv no CI (v5.15),
  ampliações do mapa de sets (v5.16/v5.18/v5.19), aposentadoria do
  `myp_enrich.py` (v5.17), skill `scan-myp` em 6 grupos (2026-07-02).
