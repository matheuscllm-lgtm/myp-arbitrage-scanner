# HANDOFF — Truncation (EN seller truncation) — 2026-06-03

> **Para o Claude do terminal:** o operador quer rodar um **codex review** no código
> (`myp_arbitrage_scanner.py`) com um objetivo específico: **resolver o EN truncation**
> — o caso em que o MYP esconde um listing EN-NM mais barato e o scanner reporta um
> preço EN superestimado. Este arquivo te dá o contexto pra o review ser cirúrgico,
> e **principalmente** lista o que JÁ foi testado e descartado com evidência nesta
> sessão, pra você não gastar o review re-investigando beco sem saída.

---

## 1. O que é o truncation (resumo de 30s)

A página de produto do MYP renderiza **2 seller tables** capadas (~15 lojistas + ~20
marketplace), ordenadas por preço **across-idiomas** e cortadas **server-side**. Quando
uma tabela enche de listings PT/JP baratos, um **EN-NM mais barato pode ficar numa
"página 2" que não existe** no HTML nem na API. O scanner então reporta como "lowest
EN-NM" um preço EN mais caro do que o real → falso negativo de deal.

**Código relevante** (`myp_arbitrage_scanner.py`):
- `TABLE_CAP_THRESHOLD = 15` — linha ~779
- Lógica de detecção `truncation_risk` — linhas ~897-905 (dispara quando uma tabela
  está no cap, com 0 EN visível, e `max_price_visivel < lowest_en_reportado`)
- Campo `CardData.en_truncation_risk` — linha ~351
- Hoje (2026-06-03) o scan de Ascended Heroes flagou **7 cards** com truncation.

---

## 2. ⛔ JÁ DESCARTADO COM EVIDÊNCIA (não repetir no review)

Investiguei estes caminhos NESTA sessão. Todos confirmados como **sem saída** —
não proponha eles como "solução" sem trazer evidência nova que contradiga:

| Hipótese de solução | Testado | Resultado |
|---|---|---|
| **API oficial do MYP expõe listings per-idioma** | Li o `swagger.yaml` oficial cru (`MYPCards/mypcards-api`, atualizado 2026-06-01) | ❌ 5 endpoints, todos preço **agregado** (`min/avg/max`). grep por `offer\|listing\|seller\|idioma\|qualidade` = **0 matches**. Sem endpoint de offers. |
| **Página chama AJAX "ver mais ofertas"** | Inspecionei o JS da página do produto | ❌ Único XHR é cookie-consent. `/preco/{id}/{slug}` referenciado → **404** ao chamar direto. |
| **Dados completos embutidos no HTML (hidden rows)** | Contei `<tr>` no documento inteiro do Psyduck | ❌ Exatamente **40 rows** (cap 20+20). Flags no doc todo: **3 EN / 31 PT / 6 JP**. Nada escondido — corte é server-side antes do render. |
| **Query param de idioma no servidor** | Testei `?idioma=Inglês`, `?lang=en`, `?lingua=ingles`, `ProdutoSearch[idioma]=Inglês` (6 variações) | ❌ TODAS retornam o mesmo set truncado (3 EN). Servidor **ignora** o param. |
| **Outro repo no GitHub já resolveu** | Busquei todos os repos que tocam mypcards.com | ❌ `MtgDesktopCompanion` (scrape agregado), `webscraping-mypcards` (catálogo 2023), `myp-enhancer` (só UI), `mypcards-script` (vazio). Ninguém resolve. |

**Conclusão da pesquisa:** a causa é **arquitetural no lado do MYP**. O preço do EN-NM
mais barato **não sai do servidor deles** por nenhum canal que um scraper alcance
(HTML ou API). Portanto **não existe fix de parser** que resolva — o scanner já está
fazendo o certo ao *flaggar*; ele não pode inventar a row escondida.

Artefatos da investigação (fora do repo, efêmeros): `/tmp/myp_swagger.yaml`,
`/tmp/trunc_resolved.json`.

---

## 3. ✅ O ÚNICO VETOR QUE SOBROU (foco do review/trabalho futuro)

**Scrape do PERFIL DO SELLER.** Quando a tabela cheia (marketplace) tem sellers PT/JP
baratos, o MYP trunca a *exibição no produto* — MAS o **estoque do próprio seller é
navegável no perfil dele**. Se um desses sellers tiver o mesmo card em EN-NM, esse é o
preço real escondido.

**Isto NÃO foi testado ainda** — é a tarefa de maior valor. Um codex review / prototype
deveria mirar:

1. Da página do produto, extrair os **handles dos sellers** das rows da tabela cheia
   (hoje o parser joga as rows fora; precisa capturar o seller id/link).
2. Para cada seller, abrir o perfil e procurar o **mesmo card (mesmo `product_code` /
   collector#) em EN-NM** no estoque dele.
3. Se achar EN-NM ≤ piso da janela (ver §4) → preço real recuperado, recalcula margem.

**Riscos/incógnitas a validar no review:**
- O MYP expõe estoque do seller por URL navegável? (provável: tem página de seller,
  mas não confirmei estrutura/paginação)
- Custo: N sellers × M cards = muito request. Precisa de rate-limit + só rodar nos
  cards já flagados (7, não o catálogo todo).
- CloudFlare: este ambiente cloud toma **403 em IP de datacenter** com requests
  concorrentes. Rodar **single-session, sequencial, com delay** (aprendido nesta
  sessão — 2 cloudscrapers no mesmo IP = 403).

---

## 4. O que JÁ foi entregue nesta sessão (pra não refazer)

- **Scan AH 2026-06-03** rodado (3 deals limpos: Mega Hawlucha 30%, Mega Feraligatr
  25%, Zoroark ex do N 25%). XLSX é gitignored (efêmero).
- **Resolução per-card dos 7 truncation flags** + sheet `🔎 Truncation Resolved` no XLSX.
- **Análise da janela de incerteza** commitada em
  `results/manual-2026-06-03-truncation-window.md` (no git). Quantifica, por card, o
  **piso** (onde um EN-NM oculto poderia estar) e a **margem potencial** no melhor caso.
  Prioriza os 7: **5 ALTA** (vale abrir perfil) / **2 BAIXA** (pular).
  - Top alvos: **Psyduck** (+12% → até ~128% se EN-NM ~R$245) e
    **Mega Dragonite ex 271/217** (0% → até ~122% se EN-NM ~R$135).
- Aberto **PR #13 (draft)** com essa análise. PR #12 (daily scan + gitignore) já mergeado.

---

## 5. Comandos úteis

```bash
# deps (ambiente vem sem elas)
pip install -r requirements.txt
export PYTHONIOENCODING=utf-8

# scan só Ascended Heroes (~12 min)
python myp_arbitrage_scanner.py --editions "Ascended Heroes" -o ah.xlsx

# os 7 cards flagados hoje (URLs pra prototipar seller-profile scrape):
#   Psyduck            https://mypcards.com/pokemon/produto/310463/psyduck
#   Mega Dragonite 271 https://mypcards.com/pokemon/produto/310508/mega-dragonite-ex
#   Mega Gengar ex     https://mypcards.com/pokemon/produto/310506/mega-gengar-ex
#   Mewtwo ex TR 281   https://mypcards.com/pokemon/produto/310518/mewtwo-ex-da-equipe-rocket
#   Tangela da Érica   https://mypcards.com/pokemon/produto/310455/tangela-da-erica
#   Grimmsnarl 287     https://mypcards.com/pokemon/produto/310524/grimmsnarl-ex-da-marine
#   Fezandipiti 288    https://mypcards.com/pokemon/produto/310525/fezandipiti-ex
```

---

## TL;DR pro review

Não há fix de parser pra truncation — confirmado que o dado não existe no HTML/API do
MYP (§2, com evidência). **Não gaste o codex review tentando melhorar a detecção ou
achar um endpoint mágico.** O único caminho real é **scrapear o perfil dos sellers**
da tabela cheia pra achar o EN-NM escondido (§3) — esse vetor está **não-testado** e é
onde o review/prototype agrega valor. Comece pelo Psyduck (maior upside, §4).
