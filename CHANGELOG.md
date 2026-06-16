# Changelog

## v5.11.4 — 2026-06-13 — Carta + Links nas tabelas de supranumerário/suspeito

As seções **supranumerário** e **TCG suspect** do markdown de entrega
(`myp_summary.py`) saíam **sem coluna `Links`** e usavam o `Card Name` cru em vez
do `Carta` canônico (nome + número). Como os deals supranumerários são a **maior
parte da entrega** do operador (raridade='Comum' no MYP, número > total do set),
ele recebia a maioria das linhas **sem link clicável** pra validar a oferta MYP e
o preço TCGplayer NM.

### Mudanças

1. **`delivery_links` aceita `tcg_url` explícito.** Novo parâmetro que prefere a
   coluna **`TCG URL`** do XLSX (plain-text desde v5.11.2) sobre o recompute via
   import do scanner. A entrega passa a usar o **mesmo** link que o XLSX carrega,
   e funciona mesmo quando `myp_arbitrage_scanner` não é importável.
2. **Tabela de supranumerário** ganha coluna `Carta` (via `carta_label`, nome +
   número sem duplicar) + coluna `Links` (`[oferta](MYP) · [TCG](TCGplayer)`).
3. **Tabela de TCG suspect** ganha as mesmas colunas `Carta` + `Links`.
4. A tabela de **deals limpos** também passa o `tcg_url` do XLSX (consistência).

**Validação:** smoke test sobre o XLSX parcial consolidado
(`myp_arbitrage_PARTIAL_run27559472691.xlsx`, 87 deals, 19/20 chunks) — as 18
linhas supranumerárias agora trazem `Links` preenchido (oferta MYP + TCG). Sem
mudança em delay/CF, threshold ou invariante NM-only.

## v5.11.3 — 2026-06-10 — Fixes de recall do preço real (resgate do PR #25)

O PR #25 (draft, conflitante) tinha 2 fixes de comportamento que nunca chegaram
à main — resgatados aqui sem a parte redundante (coluna "TCG Source", cuja
proveniência o `TCG US$` do v5.11.1 já cobre). #25 fechado em favor deste.

- **A1 — `tcg_suspect` obsoleto após override (falso negativo).** O flag de
  inflação era calculado com o `.estat-tcg` declarado, ANTES do override pelo
  preço real. Quando o pokemontcg.io corrigia o preço, o flag persistia e o
  card era **excluído da sheet 🔥 Deals** mesmo com margem real legítima.
  Agora, quando o preço vem da fonte real, `tcg_suspect` é limpo (counter
  ajustado).
- **A2 — card sem `.estat-tcg` ganha chance do preço real.** O skip por "sem
  TCG" era prematuro (antes do fetch real), descartando cards que a fonte
  cobre. Agora o skip só ocorre se **nem declarado nem real** existirem.
  Suspect-check guardado contra `tcg_player_price` ausente.

**Validação:** 21 testes offline ✓ (3 novos: A1, A2-precifica, A2-skip).

## v5.11.2 — 2026-06-10 — Coluna "TCG URL" no XLSX + sleep adaptativo pokemontcg.io

Motivação: o **scanner integrado** (`~/integrated-scanner`) consome o XLSX deste
scanner lendo por nome de header (dict-by-name) — hyperlink de célula não
sobrevive a essa leitura, então os deals MYP saíam **sem Link TCG** na tabela
unificada. E o quick do integrado media **71 min** no MYP, em parte por sleeps
cheios no pokemontcg.io.

### Mudanças

1. **`generate_xlsx` — coluna `TCG URL`** (texto plano, **17ª/última** coluna):
   o mesmo link que já era computado pro hyperlink da célula `TCG Player (R$)`
   (direct `prices.pokemontcg.io/tcgplayer/<setcode>-<num>` quando mapeado,
   senão busca por nome). Append no fim → índices posicionais e leitores
   dict-by-name (`myp_summary.py`, `myp_aggregate.py`, integrado) não quebram.
2. **Sleep adaptativo pokemontcg.io**: com `POKEMONTCG_API_KEY` definida
   (grátis, dev.pokemontcg.io, 20k req/dia), o sleep por cache miss cai de
   `--delay` (1.5s) pra **0.3s**. Ganho estimado em scan quick (8 edições):
   **15-24 min**. O delay anti-CF das páginas MYP **não muda**.
3. **Warning de startup** quando a key está ausente (throttle 429 + sleep cheio).
4. **Teste offline** `test_tcg_url_column` (17 colunas, texto == hyperlink,
   direct + fallback). Suite: **18/18 passam**.

### O que NÃO mudou

- Threshold (30% percent-integer), margem BRUTA pura, piso R$50, NM-only,
  EN-only, delay 1.5s das páginas MYP, chunking, paginação v5.9 — **tudo
  intacto**.

## v5.11.1 — 2026-06-09 — Tabela de ENTREGA com links clicáveis (padrão cross-scanner COMC)

Padroniza a **entrega de resultados** do markdown (`myp_summary.py`) no formato
aprovado pelo operador no scanner COMC: tabela chat-first com **links
verificáveis clicáveis** (oferta MYP + TCGplayer). **Nada de threshold, filtro
ou invariante mudou** — só o formato de saída.

### Mudanças

1. **`myp_summary.py` — nova tabela de entrega.** A seção "🟢 Top 50 deals
   limpos" agora emite:
   ```
   | # | Margem % | MYP R$ | TCG US$ | Dif | Carta | Set | Raridade | Cond | Qtd | Links |
   ```
   - `Carta` = nome + número numa coluna só (`Pikachu 173/165`), sem duplicar
     (helper `carta_label`).
   - `TCG US$` = preço real do TCGplayer em USD (pokemontcg.io); `—` no fallback
     `.estat-tcg`.
   - `Cond` = NM (invariante). `Qtd` = nº de ofertas EN-NM (`NM Sellers`).
   - `Links` = `[oferta](MYP) · [TCG](TCGplayer)` clicáveis. Link TCG é o redirect
     direto `prices.pokemontcg.io/tcgplayer/<setcode>-<num>` (ou busca por nome no
     fallback) — pro workflow manual de validação do preço NM.
2. **`generate_xlsx` — coluna `TCG US$`** (de `card.tcg_real_usd`) exposta no
   XLSX entre `TCG Player (R$)` e `MYP Last Sale (R$)`, alimentando a tabela de
   entrega. Lida por nome de header → aggregate e chunks antigos não quebram.
3. **`myp_aggregate.py`** preserva `tcg_real_usd` (`TCG US$`) entre chunks
   (weekly chunked não perde o USD real na consolidação).
4. **`myp_summary.py` refatorado:** corpo extraído de `main()` p/ `build_markdown()`
   (testável sem argv); fecha o handle do XLSX após extrair (Windows).
5. **Teste offline** `test_delivery_table_format` (round-trip XLSX→markdown +
   helpers de coluna). Suite: **17/17 passam**.

### O que NÃO mudou

- Threshold (30% percent-integer), margem BRUTA pura, piso R$50, NM-only, EN-only,
  stack HTTP/cloudscraper, delay 1.5s, chunking, paginação v5.9, fonte TCG real
  v5.11 — **tudo intacto**. O XLSX/CSV segue com colunas separadas + URLs cruas; o
  formato composto (Carta/Links) é só da tabela de entrega markdown.

## v5.11 — 2026-06-07 — Preço TCG REAL via pokemontcg.io (fim do `.estat-tcg` furado)

**Problema (decisão do operador 2026-06-07).** O "TCG R$" vinha do campo
`.estat-tcg` que o **MYP declara** na página do produto. Em sets base-086
(**Black Bolt / White Flare**) e parte de **Destined Rivals**, esse campo mapeia
a carta errada → preço furado. Caso medido: Darumaka 097/086 — MYP declarava
**R$2.867,75** vs TCGplayer **real US$13,42** (~R$73). Resultado: "deals" de
+2289% que eram puro artefato.

**Mudança.** O scanner passa a buscar o **preço REAL do TCGplayer via
`pokemontcg.io`** (USD) e converter pra BRL com **câmbio ao vivo**, com
**FALLBACK** pro `.estat-tcg` do MYP onde o pokemontcg.io não tem cobertura.

### Como funciona
1. **Câmbio USD→BRL** buscado **uma vez por run** (`fetch_usd_brl`): frankfurter.app
   (ECB), fallback open.er-api.com. Sem câmbio → real-price desativado na run
   (cai pro `.estat-tcg`, com warning).
2. **Preço real** (`_real_tcg_brl` / `_fetch_ptcg_usd`): resolve set via
   `MYP_EDITION_SUBSTR_TO_PTCG` + número (NNN/MMM) → `pokemontcg.io/v2/cards/{setcode}-{num}`
   → menor `market` (senão `mid`) entre as variantes (conservador, não infla a
   margem). Cache por card id; `sleep(delay)` só em cache-miss; backoff robusto
   em 429 (5/15/30s); suporta `POKEMONTCG_API_KEY` (env) p/ eliminar throttle.
3. **Gate de custo:** preço real só é buscado pra **candidatos** (EN-NM ≥
   `min_price`) — limita as requisições aos cards relevantes.
4. **Híbrido:** onde houver cobertura, usa o real; senão mantém o `.estat-tcg`
   (ex.: `me2pt5-269` Mega Gengar AH sem preço lá → fallback). Counters
   `tcg_from_real` / `tcg_from_myp_fallback` no summary.

### Sets adicionados ao mapa pokemontcg.io
- **Black Bolt → `zsv10pt5`**, **White Flare → `rsv10pt5`** (estavam omitidos
  esperando confirmar cobertura; probe ao vivo 2026-06-07 confirmou base+oversized).

### Campos novos no CardData (auditoria)
- `tcg_source` (`pokemontcg.io` | `myp_estat`), `tcg_real_usd`, `myp_declared_tcg_brl`.

### Validação
- **16 testes offline ✓** (3 novos: override real, fallback sem cobertura, inerte
  sem câmbio). O caminho real-price é **inerte offline** (fx None sem `scan()`).
- Smoke ao vivo (Black Bolt): câmbio 5,06 buscado, 5/7 cards com preço real
  (Zekrom ex corrigido p/ R$2.634 real = 31,7%), 2 fallback.

### Notas / limitações
- A margem segue **bruta pura**; a conversão USD→BRL é só pra deixar os dois
  preços na mesma moeda — não é fee.
- **Sem `POKEMONTCG_API_KEY`**, scans grandes podem sofrer 429 e (após backoff)
  cair no `.estat-tcg` de alguns cards. Recomendado definir a key p/ runs largos.

## v5.10.1 — 2026-06-07 — Cost gate: não paginar cards que não podem ser deal

A paginação de truncation da v5.9 gasta 1+N requests por card truncado. Medição
no full scan: a **maioria** dos cards truncados eram commons baratos filtrados
depois pelo `--min-price` — paginar pra "resolver" o preço deles era desperdício
(~85% das paginações).

**Gate:** um card só vira deal se MYP-EN ≥ `min_price` E margem ≥ `threshold`,
logo `TCG ≥ (1+threshold)·min_price > min_price`. Se `TCG < min_price` o card
**nunca** é deal. Então só paginamos sob o gate de truncation **quando**
`card.tcg_player_price ≥ self.min_price` (per-instância — respeita `--min-price`,
diferente do constante global da implementação paralela original).

- Novo counter `pagination_skipped_low_tcg` no summary.
- **Zero deals perdidos** — só pula cards que seriam filtrados de qualquer forma.
- Validação: smoke ME04 ao vivo → 2 cards de valor (Cinccino ex, Frogadier) ainda
  paginam, 2 commons baratos pulados pelo gate. Teste offline novo
  `test_pagination_cost_gate_low_tcg` (truncado + TCG R$50 < R$80 ⟹ 0 páginas,
  counter = 1). **13 testes offline ✓**.

> Nota: rebaseado sobre o `main` v5.10 (PR #9). Re-versionado v5.9.1 → v5.10.1
> pra não criar gap após o threshold default 30% (v5.10). Mudança ortogonal ao
> threshold — só evita requests de paginação desperdiçados, não altera quais
> cards viram deal.

## v5.10 — 2026-06-06 — Threshold default 30% margem BRUTA (política cross-scanner)

Decisão do operador 2026-06-06 (vale para todos os scanners de TCG): usar
**margem bruta de 30%** — só a diferença de preço entre produtos, **SEM taxa
embutida** no cálculo. O operador calcula as taxas (frete, câmbio, comissões)
por fora.

### Mudanças

1. **`--threshold` default 25 → 30** (percent integer; `30` = 30%). A
   auto-conversão `<1.0` (warning + ×100) **continua funcionando** — convenção
   permanece percent integer, oposta ao CardTrader scanner (fração).
   - `MARGIN_THRESHOLD = 0.25 → 0.30`.
2. **Workflows** `daily-scan.yml` / `weekly-scan.yml`: fallback de threshold
   `'25' → '30'` (input default + `|| '30'`) pra bater com a política.
3. **Margem confirmada BRUTA PURA** — auditado: o cálculo já era
   `margin_brl = tcg_player_price − myp_lowest_en_nm` e
   `margin_pct = margin_brl / myp_lowest_en_nm`. **Não havia** nenhuma
   taxa/fee/markup/multiplicador embutido (diferente do CardTrader, que usa
   `custo = preço × 1.06`). Nada foi removido — só documentado (docstring +
   comentário no site do cálculo) que está conforme.
4. **Piso de preço R$50 MANTIDO** — é filtro de relevância ("carta valiosa"),
   não taxa; fora do cálculo de margem.

### O que NÃO mudou

- Stack HTTP (cloudscraper firefox), delay 1.5s, chunking, truncation/paginação
  v5.9, NM-only, EN-only — tudo intacto. Refactor zero na heurística de scrape.

## v5.9 — 2026-06-03 — Truncation RESOLVIDO: paginação da tabela marketplace

**Root cause achado.** A tabela "demais vendedores" (`#lista-anuncio-demais-vendedores`)
é **paginada** via `?estoque-outros-page=N`, ordenada por preço crescente
across-idiomas. O scanner só lia a **página 1**, então quando ela enchia de
listings PT/JP baratos, os EN-NM mais baratos ficavam nas páginas 2+ e nunca
eram vistos → o "lowest EN-NM" reportado vinha inflado da tabela de lojistas.

Sessões anteriores marcaram isso como "irresolvível" (tinham testado só
`?idioma=`, que o servidor ignora). A paginação real foi confirmada ao vivo.

### Prova (Psyduck 226/217)

| Fonte | Lowest EN-NM |
|---|---|
| Scanner antigo (só página 1) | R$498,70 (tabela lojistas) |
| Página 2 marketplace | **R$398,00** ← EN-NM oculto |
| **Resultado v5.9** | **R$398,00** → margem vs TCG R$557,40 pula de +12% → **+40%** |

Validado end-to-end (scrape ao vivo) + 2 testes offline novos.

### Implementação (`scrape_product`)

1. Parsing de row extraído pra `_parse_seller_table()` (reusado em página 1 e
   nas páginas paginadas; comportamento idêntico — NM-only exato, skip Jumbo,
   flag-icon, promo `min()`, warn-once de idioma).
2. `_max_seller_page(soup)` lê o maior `estoque-outros-page=N` dos hrefs.
3. **Gate de custo:** só pagina quando a página 1 sinaliza truncation (alguma
   tabela ≥15 rows, 0 EN visível, `max_price` < lowest EN). Produtos normais
   não pagam o custo de requests extras.
4. Segue páginas 2..min(max, `MAX_SELLER_PAGES`=10), parseando **só** o
   container marketplace (lojistas não é recontada), single-session sequencial
   respeitando `--delay` (CloudFlare: não paralelizar).
5. `en_truncation_risk` re-significado: agora True **só** quando um fetch de
   página falha ou o cap de páginas é excedido (risco residual). Novos counters
   `seller_pages_followed` / `seller_page_fetch_failures` no summary.

## v5.8.10 — 2026-06-01 — Code health: DRY no parsing, config por-instância, +cobertura

Refactor **comportamento-preservante** (sem mudança na heurística de
scraping/scoring). Valida via `test_v5_8_offline.py`.

### DRY — regex de preço centralizado

`re.findall(r'R\$\s*[\d.,]+', …)` estava duplicado em 5 call-sites (3 no
scanner, 2 no `revalidate_deals.py`). Extraído pra constante `PRICE_RE` +
staticmethod `MYPScraper._last_brl()`. Drift no markup do MYP agora muda 1 lugar.

### Config por-instância (fim do estado global mutável)

`threshold`/`min_price` eram globais (`MARGIN_THRESHOLD`/`MIN_PRICE_BRL`)
reatribuídas no `__main__` — frágil (vazava estado entre instâncias) e
inconsistente com `min_en_sellers` (já de instância). Agora são parâmetros
de `MYPScraper.__init__` (default = constante do módulo). `MYPScraper()` sem
args mantém o comportamento legado.

### Código morto removido

- `JUMBO_FOIL_RE`/`JUMBO_TITLE_RE`: aliases retrocompat de um
  `postprocess_v583_flags.py` que não existe no repo. Zero consumidores.
- `SINGLE_EN_SELLER_RISK_THRESHOLD`: legacy alias só citado em comentário.
- `parse_brl` wrapper + `import re` em `revalidate_deals.py` (→ `_last_brl`).

### Cobertura nova (funções puras antes sem teste direto)

- `_parse_brl`: 12 casos BR/US (regressão do bug v5.8.2 `'30.00'`→3000.0).
- `_last_brl`: extração do último R$ em texto multi-preço.
- `OVERSIZED_TITLE_RE`/`OVERSIZED_FOIL_RE`: filtros jumbo/oversized.

## v5.8.9 — 2026-05-29 — TCG link DIRETO via pokemontcg.io (com fallback search)

A célula "TCG Player (R$)" passou a apontar pro **produto exato** no TCGplayer
(quando o set é mapeável), em vez da busca-por-nome do v5.8.8. Mesma mecânica
que o CardTrader scanner usa em `Link TCG`: a URL
`https://prices.pokemontcg.io/tcgplayer/{setcode}-{num}` é um redirect oficial
do pokemontcg.io pro produto TCGplayer exato — zero latência extra (string
build), sem dependência da API morta `mypcards.com/api/v1`.

**Mudanças:**
1. `MYP_EDITION_SUBSTR_TO_PTCG` — mapa de 25 sets cobrindo SV / Mega Evolution
   / SWSH eras. Substrings em forma EN ("Temporal Forces", "Stellar Crown") pra
   tolerar o bilingual concat do MYP. Black Bolt / White Flare propositalmente
   omitidos (cobertura pokemontcg.io instável quando este mapa foi montado;
   adicionar quando weekly probe confirmar 200 estável em base+oversized).
2. `myp_edition_to_ptcg_setcode(edition)` — longest-substring match (evita
   ambiguidade tipo "151" engolindo outros). Case-insensitive.
3. `tcg_direct_url(card_name, edition, oversized_collector_risk=False)` —
   monta a URL ou retorna `None` quando: edition não mapeada, sem `(NNN/MMM)`
   parseável, OU oversized_collector_risk=True (SIR/HR variant fora de range
   → frequentemente 404 = link morto pior que busca).
4. `write_card_row` integra: `tcg_direct_url(...) or tcg_search_url(...)` —
   direto onde mapeia, fallback search no resto. Coverage honesta no XLSX de
   produção 2026-05-27 (1190 cards): **20.9% direto** em "All EN Cards" e
   **10.2% direto** em "🔥 Deals". Vintage/promo/pre-SWSH caem em search por
   design (pokemontcg.io não cobre).
5. 2 testes novos em `test_v5_8_offline.py`: `test_tcg_direct_url` (mapeamento
   + None nos casos de fallback) e `test_price_cell_hyperlinks` expandido pra
   aceitar ambos esquemas (search OR direct redirect).

**Não muda:** formato `(NNN/MMM)` do Card Name (load-bearing pro merge), nem
o hyperlink MYP EN NM (produto direto via `card.product_url`).

## v5.8.8 — 2026-05-29 — Hyperlinks nas células de preço (MYP + TCGplayer)

As células de preço do XLSX viraram clicáveis pra conferência rápida na fonte,
sem sair da planilha:

1. **"MYP EN NM (R$)"** → hyperlink pra página do produto no MYP
   (`card.product_url`). A coluna "URL" já trazia esse link em 100% das rows
   (verificado no XLSX 2026-05-27: 0/88 vazias em Deals); a célula de preço
   agora reusa o mesmo URL.
2. **"TCG Player (R$)"** → hyperlink pra **busca** TCGplayer por nome
   (`https://www.tcgplayer.com/search/pokemon/product?...&q=<nome>`).

### Por que busca-por-nome e não link direto de produto

Probe 2026-05-29: a página de produto MYP (HTML-scrape, cloudscraper) **não
embute** `tcg_productId` nem qualquer link TCGplayer (0 hits). O
`mypcards.com/api/v1` — que a memória `mypcards_api_discovery` registrava
embutindo `tcg_productId` — retorna **404** hoje (surface instável desde
2026-05-07). Wirar uma chamada de API por carta adicionaria um round-trip a
mais por produto (estoura o floor ~7h do full inventory) sobre um endpoint
que já não responde. Logo, o caminho barato e estável é busca por nome.
`tcg_search_url(name)` remove o sufixo `(NNN/MMM)`/`(PR-...)` e url-encoda o
nome limpo. Retorna `None` (não linka) quando o nome é vazio.

### Implementação

- Novo helper module-level `tcg_search_url()` + constante de estilo
  `HYPERLINK_FONT` (Arial 10, `0563C1`, underline single — mesmo azul que
  `add_card_hyperlinks.py` / `revalidate_deals.py` usam no Card Name).
- `write_card_row` anexa `cell.hyperlink` nas colunas 4 (MYP) e 5 (TCG); o
  valor exibido continua o número e o `number_format='#,##0.00'` é preservado.
- Aplicado nas 5 sheets de cards: `🔥 Deals`, `All EN Cards`,
  `🏆 Top 50 Margin`, `🚨 Validate Manually`, `🚨 TCG Suspect`. `Summary` não
  tem essas colunas (não afetada).
- **Não** mexe no Card Name (formato `(NNN/MMM)` intacto, load-bearing pro
  merge) nem na coluna URL.

### Teste

`test_v5_8_offline.py`: 2 testes novos (`tcg_search_url` + round-trip de
hyperlink nas 5 sheets, asserindo domínio mypcards na célula MYP e tcgplayer
na célula TCG, valor numérico preservado, Card Name `(NNN/MMM)` intacto).
Smoke test real (`--max-editions 1 --max-products 5`) confirmou links corretos
em dados scrapeados ao vivo.

**Fix colateral:** `test_v5_8_offline.py` estava **quebrado em ImportError
desde o commit a4d2111** (importava `PT_CONDITION_MARKERS` /
`EN_CONDITION_MARKERS`, removidos quando a detecção de idioma migrou pra
célula dedicada). Os 2 testes que dependiam desses símbolos foram removidos
(testavam lógica inexistente); a suíte volta a rodar verde (5/5).

## v5.8.7 — 2026-05-29 — Card Name cleanup (copy-paste + merge fix)

O `<h1>` da página de produto MYP concatena, SEM separador, o título PT
`"Nome (NNN/MMM)"` seguido de uma cópia do nome EN. `h1.get_text(strip=True)`
colapsava isso em strings como `"Heatran-EX (109/116)Heatran-EX"` ou
`"Kyogre da Equipe Aqua (003/95)Team Aqua's Kyogre"`. No XLSX 2026-05-27
isso atingia **275 de 1190 rows (23%)**.

Dois problemas resolvidos de uma vez:

1. **Copy-paste sujo.** O operador cola o nome da carta no MYP/TCGplayer pra
   buscar/validar. O nome EN duplicado colado no fim atrapalha a busca. Agora
   o Card Name termina limpo em `"Heatran-EX (109/116)"`.
2. **Merge silenciosamente quebrado.** `Scripts/merge_myp_ct.py` casa cartas
   via `NUM_IN_NAME_RE = r"\(\s*(\d+)\s*/\s*(\d+)\s*\)\s*$"` — **ancorado no
   fim da string**. O lixo após `(NNN/MMM)` fazia o regex falhar, e essas 275
   linhas eram descartadas do índice de cross-reference (só 816/1190 = 69%
   casavam). Com o nome limpo, todas as 1091 linhas que têm `(NNN/MMM)` voltam
   a casar.

### Fix — `clean_card_name` + truncate-at-paren (extração)

Novo helper `clean_card_name(raw)` + regex `NAME_NNN_MMM_RE`: quando o nome
contém `(NNN/MMM)`, trunca logo após o `)`, removendo o nome EN duplicado.

- **Formato `(NNN/MMM)` PRESERVADO** — load-bearing pro merge. A limpeza só
  remove texto *depois* do close-paren; o token que o merge ancora fica
  intacto.
- Promos `(PR-...)`, formatos `RCxx/RCyy`, e nomes sem número ficam
  **intocados** (não casam o padrão digit/digit) — zero regressão.
- Aplicado **após** o skip de Jumbo (v5.8.3), que checa o nome RAW: o keyword
  "Jumbo"/"oversized" costuma vir DEPOIS do `(NNN/MMM)`; limpar antes do skip
  removeria o keyword e burlaria a guarda. Ordem invertida pra preservar.
- Não foi adicionada coluna nova: o Card Name já trazia name+número numa
  célula só; o pedido (copy-paste-friendly) é atendido limpando o existente,
  sem inflar o schema que o `myp_aggregate.py` lê via dict-by-name.

Teste: unit em `clean_card_name` (6 casos garbage reais + 5 não-alvo +
non-str) verificando round-trip contra o regex do merge; smoke real-scrape
(1 edição / 8 produtos) confirmou 7/7 Card Names limpos e casando o merge.

## v5.8.6 — 2026-05-19 — Postprocess robustness (5 bugs in download pipeline)

Sweep pós-scan v5.8.3 entregou XLSX usável mas com 5 bugs latentes no
pipeline `scanner → add_card_hyperlinks → revalidate → cross_check`.
Operador catalogou e aprovou batch. Cada bug = commit standalone.

### Bug #1 + #4 — `add_card_hyperlinks.py` formula → native (`76e9b1f`)

`scripts/add_card_hyperlinks.py` escrevia `=HYPERLINK("url","text")` como
fórmula Excel. Downstream usa `load_workbook(data_only=True)`, que retorna
None pra fórmula sem cache calc. Card Name=None quebrou revalidate +
cross_check.

Fix: `cell.value = display_name`, `cell.hyperlink = url` (openpyxl native).
Excel ainda renderiza clicável; readers data_only veem string.

### Bug #2 — `revalidate_deals.py` falha silenciosa (`6138741`)

Quando 100% rows skipped (Card Name=None pra todas), script saía com
"0 limpos | 0 suspeitos" + exit 0. Operador descobria só ao abrir XLSX
vazio. Agora: log.error + `sys.exit(2)` + mensagem aponta causa provável
(formula→None) e remediação.

### Bug #3 — line buffering em scripts longos (`fa799bd`)

`revalidate_deals.py` (5-30min em runs com 200+ deals) e
`cross_check_myp_api.py` (idem em runs full) escondiam progresso até
término pelo buffer 4KB padrão do Python. Fix: `sys.stdout.reconfigure
(line_buffering=True)` + flush explícito em heartbeats.

### Bug #5 — Margin number_format consistency (`e770632`)

Scanner usava `'0.0%'`, revalidate não aplicava format nenhum → célula
mostrava "0.48" (raw float) ou "48.3%" dependendo da origem. Header é
"Margin %", semântica esperada é percentage com 2 decimais.

Fix: `'0.00%'` no scanner + novo helper `_apply_data_formats` em
revalidate aplica `0.00%` em colunas Margin + `#,##0.00` em colunas
"(R$)" em todas as sheets de output.

### Follow-up — Hyperlink preservation no revalidate (`8c49956`)

Smoke do pipeline descobriu: revalidate lê com `values_only=True` e
escreve via `ws.append(row)`, que **strip-a hyperlink metadata**. XLSX
com hyperlinks injetados → revalidate → hyperlinks sumidos. Fix em
`_apply_data_formats`: re-attach Card Name → URL quando URL é http
válida e cell.value é string. Mesmo Font azul/sublinhado.

### Smoke pipeline end-to-end

```
myp_weekly_20260518_1844.xlsx → cópia →
add_card_hyperlinks (2320 hyperlinks native, 6 sheets) →
revalidate (38/38 deals processed, Card Name lido como string) →
cross_check (trim 5 deals, 5 API hits, sheet "❌ TCG API Mismatch" criada)
```

Streaming live: cross_check escreveu progress lines no log conforme
processava (não buffer-hold) — bug #3 validado em produção.

## v5.8.5 — 2026-05-19 — Source-direct cross-checks (Heurística #A oversized collector#)

Próxima camada de filtragem após v5.8.4: detectar variants fora do set numerado
sem precisar de network call.

### Heurística #A — `oversized_collector_risk` (collector# > set_size)

Cards com `(NNN/MMM)` onde `numerator > denominator` são variants SIR/HR/promo
extra/special illustration rare (frequentemente JP-only com preço TCG inflado
em USD). Casos do XLSX 2026-05-15 contaminado:

- **Darumaka (097/086)** — SV Black Bolt SIR
- **Cubchoo (109/086)** — SV Black Bolt SIR
- **Mew ex (232/091)** — SV 151 SIR
- **Charizard ex (234/091)** — SV 151 SIR

Mudanças:
- Novo campo `CardData.oversized_collector_risk: bool = False`
- Parse `(NNN/MMM)` em `scrape_product` (reusa regex já presente pro
  supranumerary check H3) → flag quando `num > total`
- Counter `oversized_collector_risks` no `_stats`
- Nova coluna XLSX `⚠️ COLLECTOR#` (fill amarelo, mostra "⚠️ VARIANT")
- Aggregate preserva flag entre chunks (`bool(rec.get("⚠️ COLLECTOR#"))`)
- Filtro `🔥 Deals`: oversized SOZINHO mantém em Deals (com flag visual);
  combinado com `single_en_seller_risk` escala pra `🚨 Validate Manually`
  (variant + idioma duvidoso = JP-mislabeled-as-EN)

Synthetic test confirma:
- Cubchoo/Mew ex (oversized only) → Deals ✓
- Darumaka/Charizard ex (oversized+single) → Validate Manually ✓
- Flareon VMAX (single only) → mantém em Deals (per v5.8.4) ✓

## v5.8.4 — 2026-05-19 — Reviewer quick fixes (DRY, CLI, regex broader, refined filter)

Round 1 dos pontos do code review pós-v5.8.3. Todos LOW RISK, sem mudar
arquitetura.

### Fix #1 — `_parse_brl` resiliente a None / non-str
`_parse_brl(None)` antes lançava `AttributeError` no `.strip()`. Guard
explícito no topo da função aceita None/int/float e retorna None.
Defensivo contra refatorações futuras que possam passar `Optional[str]`
do parser. Reviewer flagged regression risk em call sites tipo
`row[idx]` (openpyxl pode emitir None pra células vazias).

### Fix #2 — DRY `_parse_brl` (revalidate_deals)
`scripts/revalidate_deals.py` duplicava o parser BR/US. v5.8.2 BR-thousands
fix teve que ser reaplicado em DOIS lugares. Agora `parse_brl` no script
delega pra `MYPScraper._parse_brl` (single source of truth).

### Fix #3 — CLI flag `--min-en-sellers`
Threshold de "single seller risk" agora é configurável. Default 2
(reproduz comportamento v5.8.3 que checava `≤ 1`). `MYPScraper.__init__`
aceita `min_en_sellers` arg; usa `en_sellers < self.min_en_sellers`
(strict less-than). Operador pode `--min-en-sellers 3` pra cenário
mais conservador.

### Fix #4 — Regex `OVERSIZED_*` broader + `\b` consistency
`JUMBO_FOIL_RE` (sem word boundary) e `JUMBO_TITLE_RE` (com `\b`) eram
inconsistentes. Renomeados para `OVERSIZED_FOIL_RE` / `OVERSIZED_TITLE_RE`
com regex broader cobrindo também `oversized`, `box topper`, `poster card`
(variantes que MYP eventualmente lista). Aliases `JUMBO_*` mantidos como
retrocompat (postprocess_v583_flags.py importa o nome antigo).

### Fix #5 — Deals NÃO esvazia por single-seller sozinho
v5.8.3 excluía agressivamente qualquer `single_en_seller_risk=True` de
`🔥 Deals`. Operador relatou que isso esvaziou Deals em scans onde chase
cards genuinamente raros tinham só 1 seller EN listando. v5.8.4 refina:
single-seller SOZINHO permanece em Deals (com coluna visual `⚠️ 1 SELLER`).
Só sai pra Validate Manually quando acompanhado de `tcg_suspect` OU
`en_truncation_risk` (combinação eleva confiança de problema real).

### Notes
- Smoke test: `--editions "Black Bolt" --max-products 8` rodou clean.
  Default `--min-en-sellers 2` flagou 4 single-seller risks (Zekrom ex 172,
  Zekrom ex 166, Servine 088, Haxorus 147). XLSX gerado com 6 sheets
  esperadas.
- Synthetic test do filtro de deals: A (single-only) entra ✓, B (single+suspect)
  sai ✓, C (single+truncation) sai ✓, D (clean) entra ✓.

## v5.8.3 — 2026-05-18 — Skip Jumbo + single-seller-EN risk surfacing

Dois bugs reportados pelo operador no XLSX `myp_weekly_20260517_1519`:

### Bug A — Jumbo sellers no mesmo produto da carta standard
Cartas Jumbo (oversized ~25×35cm de colecionador) têm mercado/preço distintos
da versão standard. **MYP agrupa standard + jumbo na MESMA página de produto**;
a variante é indicada por seller-row na coluna `td.estoque-lista-nomeenfoil`
("Foil"). Caso M-Rayquaza-EX (098/98) XY 7 produto 32737:
- h1 = `"M-Rayquaza-EX (098/98)M Rayquaza-EX"` (sem "Jumbo")
- 5 sellers com Foil="Jumbo" a R$650
- TCG declarado R$4801,45 (preço da standard)
- Margem fictícia: 638%

- **Camada 1 — per-row filter** (`JUMBO_FOIL_RE`): rows onde
  `td.estoque-lista-nomeenfoil` casa `/jumbo/i` são puladas. Counter
  `jumbo_rows_filtered` no `_stats`.
- **Camada 2 — title filter** (`JUMBO_TITLE_RE`, `\bjumbo\b` case-insensitive):
  skip cedo se o título do produto contém "Jumbo" (caso MYP algum dia separe
  em produto standalone). Counter `skipped_jumbo` no `_stats`.

### Bug B — Flareon VMAX 018/203 single-seller EN mislabeling
Investigação do HTML real (`scripts/_investigate_flareon_jumbo.py`) confirmou que
o produto tem **1 único seller** (`gvrgyn`) marcado como `flag-icon[title="Inglês"]`,
condição NM, R$ 89,90 contra TCG R$ 456,20. Não há bug de detecção do scanner —
o site afirma que é EN. Hipótese mais plausível: seller mislabeling de idioma
em carta que não tem print EN nessa edição (Prize Pack Series).

Sem cross-check externo (pokemontcg.io card-ID per-edition) não dá pra confirmar
o "EN não existe" de forma automatizada. Solução defensiva sem suprimir deals
genuínos:

- **Novo campo** `CardData.single_en_seller_risk: bool` (default False).
- **Threshold** `SINGLE_EN_SELLER_RISK_THRESHOLD = 1` — flag quando `en_nm_sellers <= 1`.
- **Exclui de `🔥 Deals`**, **inclui em `🚨 Validate Manually`** (já existente).
- **Nova coluna XLSX** `"⚠️ Single Seller"` em todas as sheets de cards.
- **Counter** `single_en_seller_risks` no `_stats`, logado ao final.
- **Aggregator** (`myp_aggregate.py`) preserva o flag entre chunks (mesmo padrão
  do tcg_suspect do v5.8).

## v5.8 — 2026-05-16 — TCG suspect surfacing (Jirachi-style inflation fix)

Bug pós-scan 2026-05-15: Jirachi PR-SM_SM161 apareceu como deal #1 a +1400% margem
com TCG declarado R$1499 — última venda real R$19,99 (75x off, MYP bug em `.estat-tcg`).
A heurística H2 v5.8 já existia em `CardData` (`tcg_suspect`, `myp_last_sale_brl`)
mas era completamente invisível: nem entrava no XLSX, nem filtrava sheets, nem
aparecia no markdown summary. Esta release surface o sanity check end-to-end.

### Scanner (`myp_arbitrage_scanner.py`)
- Nova constante `TCG_SUSPECT_RATIO_THRESHOLD = 10.0` (era hardcoded inline).
- Novo counter `tcg_suspects` em `_stats`, logado ao final do scan.
- Log warning **loud** ao detectar suspect (com ratio + valores) no `scrape_product`.
- `generate_xlsx`: 2 colunas novas — `MYP Last Sale (R$)` e `⚠️ TCG Suspect`.
- Sheet `🔥 Deals` **exclui** cards com `tcg_suspect=True` (Jirachi sai do topo).
- Nova sheet `🚨 TCG Suspect` análoga à `🚨 Validate Manually`.
- Summary sheet: linha "🚨 TCG Suspects" com contagem.

### Aggregator (`myp_aggregate.py`)
- `card_from_row` agora preserva `myp_last_sale_brl` e `tcg_suspect` lendo das
  colunas correspondentes. Antes esses campos eram strip-ados na consolidação,
  e o XLSX final do GH Actions voltava a mostrar Jirachi como deal #1.

### Markdown summary (`myp_summary.py`)
- Top 15 limpos agora exclui supranumerários **E** tcg_suspect.
- Nova section `## 🚨 TCG Suspect` no markdown com colunas extra
  (TCG declarado, última venda, margem fake) pra auditoria.
- Stats line inclui contagem de suspects.

### Single source of truth
- `scripts/revalidate_deals.py` agora importa `TCG_SUSPECT_RATIO_THRESHOLD`
  do scanner em vez de duplicar a constante. Mudar o threshold em um lugar
  só agora afeta scan-time + revalidação.

### Regression guard (`test_v5_8_offline.py`)
- Novo teste offline com 5 asserts: threshold constant, PT/EN markers
  disjuntos, math do caso Jirachi (75x), lógica H1 de language-by-condition,
  e XLSX end-to-end (Jirachi excluído de Deals + presente em TCG Suspect +
  borderline 9.5x sem false-positive). Roda em ~2s, zero rede. Próxima
  alteração no filtro/surface quebra o build se regredir.

## v5.7.2 — 2026-05-15/16 — Operacional (sem mudança de código)

Mudanças de processo/cron que afetam comportamento sem mexer no scanner:
- `weekly-scan.yml`: cron schedule **removido**. Weekly full agora roda local
  via Task Scheduler do PC do operador, eliminando consumo de CI minutes
  (~840min/mês). Workflow ainda triggable via `workflow_dispatch`.
- `daily-scan.yml`: cron schedule **removido** (decisão pós-exaustão da quota
  GH Actions em 2026-05-15). Daily roda só manual via dispatch.
- Default `chunk_total` 6 → 20 no `weekly-scan.yml` (validated pelo benchmark
  do scan 2026-05-15: ~7min/edição interleaved).
- Novo `scripts/run_weekly_local.ps1` wrapper pra Task Scheduler do PC.

## v5.5 — 2026-05-14 — Matrix job + aggregation (infraestrutura escalável)

Full scan single-thread = ~7h (348 editions × ~50 prods × 1.5s delay) — não cabe
em GH Actions free tier (max 6h/job). Duas runs em 2026-05-14 estouraram 180min
e 350min timeouts respectivamente; zero XLSX gerado em ambas. **Decisão arquitetural:
matrix job paralelo + step de aggregation.**

### Scanner

- Novas flags `--chunk-index N` `--chunk-total M` em `myp_arbitrage_scanner.py`.
  Após `get_all_editions()` + filter, faz `editions[N::M]` (interleaved slicing).
  Interleaved escolhido sobre block para load balancing — edição sizes variam
  muito, blocos sequenciais poderiam concentrar todas as massivas num único chunk.
- Validação: `0 <= chunk_index < chunk_total`, senão `raise ValueError`.

### Aggregator

- Novo arquivo `myp_aggregate.py`. Lê todos os `myp_chunk_*.xlsx`, reconstrói
  `CardData` da sheet `"All EN Cards"` de cada um, dedupe defensivo por
  `product_url` (chunks interleaved NÃO deveriam gerar duplicata, mas se
  operador rodar 2 chunks sobrepostos, evita inflar relatório), depois
  invoca `generate_xlsx` reusando single source of truth do scanner.
- Suporta glob nos inputs (Windows shell não expande).
- Imprime stats por chunk + count de duplicates removidas.
- Sheets resultantes idênticas ao formato single-thread: `🔥 Deals`,
  `All EN Cards`, `🏆 Top 50 Margin`, `🚨 Validate Manually`, `Summary`.

### Workflow (`weekly-scan.yml`)

Refator pra 3 jobs:

1. **`plan`** — gera matrix de chunk indices baseado em `chunk_total`
   (default 6, cap 1-20). Output: `chunk_indices=[0,1,2,3,4,5]`.
2. **`scan`** (matrix, `fail-fast: false`) — cada chunk roda o scanner com
   `--chunk-index N --chunk-total M`, faz upload de `myp_chunk_N.xlsx` como
   artifact `myp-chunk-N`. Timeout 120min por chunk (sobra folga vs ~70min real).
3. **`aggregate`** (`needs: scan`, `if: always() && != cancelled`) — baixa todos
   os artifacts `myp-chunk-*` via `download-artifact@v4` com `merge-multiple: true`,
   roda `myp_aggregate.py chunks/myp_chunk_*.xlsx`, faz upload do consolidated
   xlsx como `myp-scan-consolidated-{run_id}`.

### Trade-offs documentados

- **Interleaved vs block:** interleaved, load balancing > previsibilidade
- **6 chunks default:** balanceia parallelismo vs overhead de startup × 6 jobs
- **fail-fast: false:** preserva chunks que completaram se um falhar
- **Aggregate roda mesmo com falha parcial:** entrega XLSX dos chunks bem-sucedidos
- **Novo input `chunk_total`:** operador pode override (3 chunks pra teste rápido,
  10 chunks pra max speed)
- **Sem cache de catalog scrape entre chunks:** cada chunk re-baixa `/pokemon/edicoes`
  (~30s overhead × 6 = 3min total, aceitável)
- **CI minutes consumption:** 6 chunks × ~70min = ~420 minutes-instance, vs 7h × 1 = 420
  minutes single-thread. Mesmo consumo total, mas paralelo = wall-time ~1h em vez de 7h.

### Smoke test (run 25875239320, 2026-05-14)

`chunk_total=3 editions=Ascended` — só 1 edição casou, chunks 1+2 vazios após slicing.

- ✅ `plan` ok (output `chunk_indices=[0,1,2]`)
- ✅ `scan (0)` 14m17s — processou Ascended Heroes (99 produtos, 3 deals)
- ✅ `scan (1)` ~30s — empty chunk legítimo, exit 0, log: `Chunk slicing: 1 editions → 0 (chunk 1/3)` + `✓ Chunk 1/3 vazio após slicing`
- ✅ `scan (2)` ~30s — idem
- ✅ `aggregate` 17s — `myp_aggregate.py chunks/myp_chunk_*.xlsx` consolidou em XLSX final
- ✅ Final XLSX: 31 EN cards, 3 deals, 5 sheets idênticas ao formato single-thread (`🔥 Deals`, `All EN Cards`, `🏆 Top 50 Margin`, `🚨 Validate Manually`, `Summary`)

Estrutura matrix + aggregation validada end-to-end. v5.5.1 fix (`bd707f3`)
crítico — sem ele, chunks vazios marcariam o job como red.

## v5.4 — 2026-05-14 — Production hardening (code review fixes)

Code review formal pelo agente `pr-review-toolkit:code-reviewer` rodado pré-entrega
matinal de scanners funcionantes. 9 fixes aplicados (3 CRITICAL + 4 HIGH + 2 MEDIUM
+ 1 invariant). Foco: eliminar silent failure modes, dar exit codes claros pro cron.

### CRITICAL
- **C2 (catalog scrape sanity):** `get_all_editions()` agora warning loud se
  `len(editions) < MIN_EDITIONS_EXPECTED` (200). Esperado ~326. Floor previne
  Strategy 3 fallback truncar silenciosamente em mid-catalog selector breakage.
- **C3 (narrow exception):** `_get()` retry loop agora pega só
  `requests.RequestException`, `ConnectionError`, `TimeoutError`, `OSError`.
  Parser bugs (lxml/bs4), `AttributeError`, `MemoryError` etc propagam como
  crash — não viram silent skip + `skipped_no_tcg_price++`.

### HIGH
- **H1 (unknown language warn-once):** títulos de flag-icon fora de
  `KNOWN_LANGUAGES` (constante nova) agora são contados em
  `skipped_unknown_lang_titles` e logam warning na primeira ocorrência.
  Previne silent zero-deals se MYP normalizar `"Inglês"` → `"Ingles"`.
- **H2 (price min em vez de last):** strikethrough fix passa de `[-1]` pra
  `min(parsed_prices)`. Defensivo contra MYP injetar 3º R$ (frete, "you save").
  Debug log quando `>2` matches.
- **H3 (pagination loop detection):** `get_edition_products()` compara primeira
  URL de page N vs N-1. Iguais = MYP retornando mesma página → log loud + stop.
  Previne silent under-coverage por bug de query param.
- **H4 (MAX_EDITION_PAGES cap):** `get_all_editions()` agora capada em 50
  pages (era `while True:`). Atinge cap sem natural exit → warning.
- **H5 (filter typo exit):** `--editions` que não casa nada agora `sys.exit(2)`
  com mensagem clara. Cron job vai falhar visivelmente em vez de "success+empty".

### MEDIUM
- **M1 (empty result exit code):** runs com zero cards `sys.exit(1)`. CI distingue
  "scan saudável zero deals" (exit 0 com XLSX) de "scraper broken" (exit 1).
- **M3 (Top 50 sem padding None):** sheet `🏆 Top 50 Margin` filtra `margin_pct
  is not None` antes do slice. Evita padding visual em runs com <50 válidos.

### Invariant (single highest-leverage fix)
- **`pages_fetched > 100 and en_found == 0` → `sys.exit(1)`**. Catches todos
  os silent-failure modes ao mesmo tempo (selector break, language detector
  quebrado, MYP rebuild) sem precisar saber em qual etapa quebrou.

### Não aplicados (intencionalmente — flagged como maintenance landmines)
- **C1/H6 (`MARGIN_THRESHOLD` global rebind):** funciona por late-binding mas é
  fragile. Refator pra constructor param fica pra v6.0 (mudança maior de API).
- **M2 (regex `pokemon_[a-z]{2,3}_[\w/]+` greedy):** cosmetic, product_code
  é informational only.
- **M4 (zero-truthiness em `card.tcg_player_price or 0`):** `_parse_brl` já
  retorna None pra zero, defensive logic OK.
- **M5 (ETA logging):** nice-to-have, cron tem timeout próprio.
- **L1-L4:** polish only.

REVIEW.md no repo tem o relatório completo. Code review levou ~2min via agente.

## v5.3 — 2026-05-12

Refinamentos após caso Psyduck/bartsimpson revelar truncamento de seller table no MYP.

- **T1 (EN truncation flag):** novo campo `CardData.en_truncation_risk`. Parser itera por seller table individualmente (Tabela 0=lojistas/cap~15, Tabela 1=marketplace/cap~20). Heurística: dispara quando uma tabela está no cap (≥15 rows), com zero EN visível, e `max_price_visible < lowest_en_reported`. Evita false alarm quando max visível já está acima do lowest_en (hidden não pode quebrar).
- **H3 refinada:** agora também exige `card_num > set_total` quando o sufixo `(X/Y)` é extraível do nome — evita falso alarm em commons in-set caros.
- **Nova sheet `🚨 Validate Manually`** no xlsx: lista cards com `en_truncation_risk` pra punch-list de validação manual.
- **Nova coluna `⚠️ EN Trunc`** nas sheets de cards.
- **Novo stat counter** `en_truncation_risks` no summary final.
- **Bug fix: pricing promocional.** Rows com `R$ X (riscado) R$ Y` usavam X (preço antigo, mais caro) via `re.search`; agora `re.findall + [-1]` pega Y (preço ativo). Caso: MatchampTCG Psyduck "R$ 275,00 R$ 220,00" lido como R$275 quando deveria ser R$220.

## v5.2 — 2026-05-12

- **Default `--threshold` de 35 → 25** (mais discovery, menos filtragem).
- **Nova sheet `🏆 Top 50 Margin`** no xlsx: cards ordenados por margem desc sem filtro, pra inspeção visual chase-card.

## v5.1 — 2026-05-12

Auditoria C/H/M (mesma metodologia do scanner CT).

- **C1:** `--threshold < 1.0` auto-converte com warning (UX guard contra trap inverso ao CT scanner — MYP usa percent integer, CT usa fração).
- **H3:** detecção heurística SIR/HR/SAR — warning quando rarity="Comum" mas TCG price alto (>R$200). Reduz falso positivo documentado.
- **M1:** HTTP retry com backoff (3 tentativas, 2s→4s) em transient errors.
- **M4:** `debug_*.html` agora salvo em subpasta `.debug/` do script, não polui CWD.
- **M5:** novos stat counters (`skipped_no_tcg`, `skipped_no_en_sellers`, `skipped_low_price`) pra auditoria do funnel.

## v5 — 2026-04-15

Versão base. Scanner inicial com:
- Scrape mypcards.com via cloudscraper (CloudFlare bypass)
- Filtro EN-NM via flag-icon span
- Cálculo de margem vs TCGplayer reference price (BRL convertida no MYP)
- Output xlsx com 3 sheets (Deals, All EN Cards, Summary)
