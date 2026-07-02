---
name: myp-scan
description: Roda o scan de arbitragem do MYP (mypcards.com) e entrega os deals no formato canônico do repo. Use quando o operador pedir "roda o MYP", "scan MYP", "deals do MYP", "resultados do MYP" ou variações. Caminho único e determinístico — mesmo run, mesma entrega, sempre. Sem argumento, pergunta quais dos 6 grupos canônicos de sets rodar.
argument-hint: [grupos (ex. G1, "grupos 1 e 2") OU edições explícitas entre aspas; vazio = perguntar quais grupos rodar]
---

Você foi acionado pela skill **`/myp-scan`**. Este arquivo é o **caminho único**
para rodar o scanner MYP e entregar o resultado. Não improvise fora dele: todo
scan corre da mesma maneira e toda entrega sai no mesmo formato. O contrato de
fundo é o `CLAUDE.md` deste repo (seções 🚨 CONTRATO DE ENTREGA e 📤) — esta
skill só o operacionaliza passo a passo.

**Argumento recebido (grupos ou edições, se houver):** `$ARGUMENTS`

---

## 0. Escolha de grupos (SEMPRE antes de rodar)

O catálogo com preço de referência real (108 sets) é dividido em **6 grupos
canônicos por recência**, definidos em `scan_groups.py` (fonte única; o
`test_scan_groups.py` trava a partição contra o mapa do scanner). Cada grupo
tem ≤21 edições **de propósito**: é o teto que mantém qualquer run dentro de
~2h30 — runs maiores vinham sendo mortos por timeout **sem entregar nada**
(CHANGELOG v5.5: runs de 180 e 350 min, zero XLSX).

| Grupo | Era | Edições | Via Actions | Local seq. |
|---|---|---|---|---|
| **G1** | Mega Evolution (até Chaos Rising) + SV recente | 18 | ~25-40 min | ~2h06 |
| **G2** | SV inicial + Sword & Shield | 18 | ~25-40 min | ~2h06 |
| **G3** | Sun & Moon + XY final | 18 | ~25-40 min | ~2h06 |
| **G4** | XY inicial + Black & White | 18 | ~25-40 min | ~2h06 |
| **G5** | HGSS + DP/Platinum + EX tardio | 18 | ~25-40 min | ~2h06 |
| **G6** | EX inicial + e-Card + WotC | 18 | ~25-40 min | ~2h06 |

(A lista completa de cada grupo: `python scan_groups.py --list`.)

Como decidir o escopo do run:

1. **`$ARGUMENTS` nomeia grupos** ("G1", "grupo 1 e 2", "1,2,3") → rode esses
   grupos, sem perguntar.
2. **`$ARGUMENTS` traz edições explícitas** (substrings entre aspas) → use-as
   como hoje, sem perguntar.
3. **`$ARGUMENTS` vazio ou genérico** ("roda o MYP") → **PERGUNTE ao operador**
   (AskUserQuestion, multiSelect) quais grupos rodar, mostrando a tabela acima
   (G1 primeiro — é onde os deals moram; G5/G6 são mercado eficiente, quase
   nunca rendem). **Não** assuma um default silenciosamente.

**Grupos múltiplos = runs SEQUENCIAIS**, um por vez: o workflow tem
`concurrency: myp-scan` (um segundo dispatch fica pendente e um terceiro
CANCELA o segundo). Dispare o próximo grupo só quando o anterior concluir, e
**entregue a tabela de cada grupo assim que o run dele terminar** (não espere
todos). As ~250 edições fora dos 6 grupos (promos/vintage não mapeado) não têm
preço de referência real — só entram se o operador pedir explicitamente, e a
margem delas sai como fallback "validar manualmente".

## 1. Parâmetros fixos (NUNCA mudar sem ordem explícita do operador)

| Parâmetro | Valor | Nota |
|---|---|---|
| Threshold | `30` | percent **INTEIRO** (30 = 30%). Nunca `0.30` — fração é convenção do CardTrader/COMC, não deste repo |
| Piso de preço | `--min-price 50` | R$50 — filtro de relevância, fora do cálculo de margem |
| Condição | NM-only | match EXATO `== "NM"`, invariante do scanner |
| Margem | BRUTA pura | `(TCG − MYP) / MYP`, zero taxa embutida |
| Delay | `1.5` | anti-Cloudflare; não paralelize fetches no mesmo IP |

`$ARGUMENTS` define **só o escopo** (grupos ou edições — ver §0); nunca os
parâmetros da tabela. Se o operador pedir outro threshold/piso na mesma frase,
ele manda — mas registre na entrega que o run saiu do padrão.

## 2. Rota A — PADRÃO: workflow do GitHub Actions (nuvem e PC)

É o jeito rápido e reproduzível (~10-15 min; cada chunk roda num runner com IP
próprio, sem conflito de Cloudflare; preço TCG **real** via `tcgcsv`).

1. **Dispara** o workflow `quick-scan.yml` no repo
   `matheuscllm-lgtm/myp-arbitrage-scanner`, ref `main`:
   - via MCP: `mcp__github__actions_run_trigger` (method `run_workflow`);
   - no PC local: `gh workflow run quick-scan.yml`.
   - Input `editions` = a saída de `python scan_groups.py --group <N>` (a
     string já vem pronta, multi-palavra entre aspas — **não** digite as
     edições à mão) ou, se o operador deu edições explícitas, elas entre
     aspas. Não passe threshold/min_price/delay — os defaults do workflow já
     são os canônicos da tabela acima.
2. **Aguarda** o run terminar. Poll com `actions_get`/`gh run watch` em
   intervalos de ~2-4 min — **nunca** busy-wait com `sleep` curto em loop.
3. **Baixa** o artifact consolidado `myp-quick-consolidated-<run_id>` do run.
   Dentro dele já vêm:
   - `myp_quick_<stamp>.xlsx` — o XLSX consolidado (matéria-prima);
   - `results/quick-<data>.md` (= `results/latest-quick.md`) — **a entrega
     pronta**, já gerada pelo `myp_summary.py --type daily` no próprio workflow.
4. Vá direto ao passo 4 (Entrega) com esse `.md`. Se o `.md` faltar no artifact
   (warning no run), gere você mesmo a partir do XLSX baixado:
   `python myp_summary.py <xlsx> --type daily -o results/<scope>-<data>.md`.

## 3. Rota B — FALLBACK: run local (só se o Actions estiver indisponível)

Use somente quando o workflow não puder rodar (Actions fora, sem acesso ao
repo, ou o operador mandou rodar local).

```bash
pip install -r requirements.txt          # brotli é obrigatório
export PYTHONIOENCODING=utf-8
python myp_arbitrage_scanner.py --editions <edições> \
  --threshold 30 --min-price 50 --delay 1.5 \
  -o results/<set>_<stamp>.xlsx
python myp_summary.py results/<set>_<stamp>.xlsx --type daily \
  -o results/<scope>-<data>.md
```

- `<edições>` = as edições do grupo escolhido (`scan_groups.py --group <N>`
  imprime a string; re-parseie com `eval set --` pra virar N argumentos) —
  **um grupo por run**. Um grupo (≤21 edições) leva ~2h06 sequencial; se
  estourar ~2h30, PARE e retome num run novo com `--resume` — não deixe um run
  gigante ser morto sem entregar nada.
- Scan largo pode passar de 1h — rode **detached/background**, nunca preso num
  terminal que pode fechar.
- Single-session sequencial (2 sessões no mesmo IP = 403 Cloudflare).
- `--type` aceita só `daily` (quick/diário) ou `weekly` (catálogo completo).
- Cloudflare 403 no teste "puro" do cloudscraper é falsa pista — o scanner já
  usa fingerprint firefox por padrão; apenas rode.

## 4. Entrega — regras DURAS (não negociáveis)

1. **Cole o `.md` do `myp_summary.py` VERBATIM no chat.** PROIBIDO remontar,
   reformatar, renomear/reordenar colunas, "economizar largura" ou tirar
   qualquer link. Se o que você vai colar não saiu do `myp_summary.py`, PARE e
   gere por ele.
2. **Toda linha tem os 2 links** — `[oferta](url MYP)` · `[TCG](url TCGplayer)`
   — em TODOS os buckets (limpos, supranumerário, suspeito, fallback e qualquer
   verificação manual). Links são LIDOS do XLSX; **nunca** invente/monte URL.
3. **Todos os deals, sem amostra curada** — os 4 buckets completos, com os
   avisos "(validar manualmente)" que o script já põe.
4. **Honestidade de preço:** fallback `.estat-tcg` NUNCA é tratado como preço
   real (a margem dele pode ser ilusória — o script já o separa no bucket 4).
   Consolidado com **0 preço real** = FALHA do tcgcsv a investigar, não um
   resultado normal.
5. **Nunca recomende compra.** Você reporta margem, flags e fontes; capital é
   decisão do operador.
6. **Nunca anexe XLSX/CSV por padrão.** Arquivo só se o operador pedir
   explicitamente. A entrega É a tabela no chat.
7. **Dados de deal não entram em commit** (repo público + discreto): `results/`
   é gitignored; não commite planilha, `.md` de resultado nem números de deal.
