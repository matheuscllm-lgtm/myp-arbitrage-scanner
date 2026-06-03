# HANDOFF — Truncation RESOLVIDO (root cause + fix) — 2026-06-03

> **Para o Claude do terminal:** o operador quer que o scanner **encontre os preços
> EN-NM mais baixos quando estão em páginas posteriores** da tabela de vendedores.
> **Isto agora está diagnosticado e tem fix claro.** Rode o codex review em
> `myp_arbitrage_scanner.py` mirando a implementação descrita em §3.
>
> ⚠️ **Correção de uma sessão anterior:** eu havia concluído que truncation era
> "irresolvível". **Estava ERRADO.** Eu tinha testado `?idioma=` (que o servidor
> ignora) mas **não tinha achado a paginação real da tabela de marketplace**. Achei
> agora. O resto deste doc reflete a descoberta correta.

---

## 1. Root cause (confirmado com evidência ao vivo)

A página de produto tem 2 tabelas de vendedores:
- **Tabela 0 — lojistas** (`lista-anuncio-lojistas-certificados`)
- **Tabela 1 — marketplace / demais vendedores** (`#lista-anuncio-demais-vendedores`)

A tabela marketplace é **paginada** e ordenada por preço crescente across-idiomas. O
scanner hoje só lê a **página 1**. Quando a página 1 enche de listings PT/JP baratos,
os EN-NM ficam nas **páginas 2, 3...** que o scanner nunca busca → ele cai no preço EN
mais caro da tabela de lojistas e reporta um "lowest EN-NM" superestimado.

**A paginação existe e é trivial de seguir** — é um `<ul class="pagination">` padrão
com query param:

```
https://mypcards.com/pokemon/produto/310463/psyduck?estoque-outros-page=2
https://mypcards.com/pokemon/produto/310463/psyduck?estoque-outros-page=3
```

O nº total de páginas sai do próprio HTML: `re.findall(r'estoque-outros-page=(\d+)', html)` → pega o `max()`.

## 2. Prova (Psyduck 226/217, caso documentado no README)

| Fonte | Lowest EN-NM |
|---|---|
| Scanner hoje (só página 1) | **R$498,70** (veio da tabela de lojistas) |
| Página 1 marketplace | 0 EN-NM (só PT/JP, R$180–245) |
| **Página 2 marketplace** | **R$398,00** ← 7 listings EN-NM, todas < R$498 |
| Página 3 marketplace | R$450–650 |
| **TRUE lowest EN-NM** | **R$398,00** |

**Impacto no deal:** margem vs TCG (R$557,40) pula de **+12% → +40%**. O Psyduck
**vira um deal real ≥25%** que o scanner estava perdendo por completo. Isto é o caso
"bartsimpson R$300 truncado" que o README §T1 descreve — confirmado como paginação,
não como dado inacessível.

## 3. ✅ FIX a implementar (foco do codex review)

Local: `myp_arbitrage_scanner.py`, função **`scrape_product`** (linha ~673) — o bloco
que itera `seller_tables = soup.select("table.table-striped.table-bordered")` (~L781)
e coleta `en_prices` (~L770-920).

**Mudança:** depois de processar a página 1, **seguir a paginação da tabela marketplace**
e acumular as rows EN-NM de todas as páginas antes de computar `lowest_en`.

Recipe sugerido:
1. Após parsear a página 1, detectar `max_page = max(estoque-outros-page=N)` no HTML.
   Se não houver paginação → comportamento atual (1 página).
2. Para `pg in 2..max_page`: GET `f"{url}?estoque-outros-page={pg}"` (plain GET, **sem**
   headers XHR — testei: header `X-PJAX` custom dá HTTP 500; **GET simples dá 200**).
   - Opcional/otimização: `X-PJAX-Container: #pjax-estoque-outros` retorna fragmento de
     124KB em vez de 418KB (mais leve), mas o GET simples também funciona.
3. Parsear **só o container `#lista-anuncio-demais-vendedores`** nessas páginas (a tabela
   de lojistas não pagina — não re-processar) e adicionar rows EN-NM a `en_prices`.
4. `lowest_en = min(en_prices)` agora reflete todas as páginas.
5. **Aposentar / re-significar a flag `en_truncation_risk`**: com paginação seguida, o
   risco vira raro. Manter como sinal de "página de marketplace existe mas falhou fetch".

**Guard-rails (reusar padrões já no código):**
- Cap de páginas tipo `MAX_PAGES_PER_EDITION` (ver `get_edition_products` L630) pra não
  loopar infinito. Sugiro `MAX_SELLER_PAGES = 10`.
- `--delay` entre page-fetches (já existe). Cada produto vira 1+N requests — **isto
  multiplica o tempo de scan**; só paginar quando a página 1 sinaliza truncation
  (tabela marketplace cheia, EN-NM ausente/caro) pra não pagar o custo em todo produto.
- **CloudFlare:** single-session sequencial. 2 cloudscrapers no mesmo IP = 403
  (aprendido). Datacenter IP já é borderline; não paralelizar fetch de páginas.

**Teste de regressão:** adicionar caso offline em `test_v5_8_offline.py` usando
`/tmp/psyduck.html` (página 1) + um fixture de página 2 — assert que lowest EN-NM = 398,
não 498,70. (Salve os HTMLs como fixtures em vez de depender de rede.)

## 4. ⛔ O que NÃO é o caminho (já descartado com evidência)

Pra não desperdiçar o review:
- **API oficial** (`MYPCards/mypcards-api`, swagger lido): só preço agregado, sem
  endpoint de listings. Não serve.
- **`?idioma=`/`?lang=`**: servidor ignora, retorna mesmo set. Não é esse o filtro.
- **Endpoint `/preco/{id}`** sem prefixo de jogo → 404. (O certo seria
  `/pokemon/preco/{id}/{slug}` mas é a página de histórico, não as listings.)
- **Scrape de perfil de seller**: seria necessário SE não houvesse paginação. Como
  **há** paginação (§1), esse vetor ficou **desnecessário** — não precisa mais.

## 5. Estado entregue nesta sessão

- Scan AH 2026-06-03 (3 deals limpos). Análise de janela em
  `results/manual-2026-06-03-truncation-window.md` (no git, PR #13).
  ⚠️ Aquela análise assumia truncation irresolvível; com o fix de §3 ela vira
  **desnecessária** pros cards que o scanner passar a resolver sozinho.
- Os 7 cards flagados hoje (re-validar com o fix): Psyduck, Mega Dragonite 271, Mega
  Gengar ex, Mewtwo ex TR 281, Tangela da Érica, Grimmsnarl 287, Fezandipiti 288.

## 6. Comandos

```bash
pip install -r requirements.txt
export PYTHONIOENCODING=utf-8

# reproduzir a prova (Psyduck pág 2 tem EN-NM R$398):
python3 -c "
import cloudscraper, re
s=cloudscraper.create_scraper(browser={'browser':'firefox','platform':'windows'})
u='https://mypcards.com/pokemon/produto/310463/psyduck'
s.get(u,timeout=30)
h=s.get(u+'?estoque-outros-page=2',timeout=30).text
from bs4 import BeautifulSoup
c=BeautifulSoup(h,'lxml').select_one('#lista-anuncio-demais-vendedores')
print([tr.get_text(' ',strip=True)[:60] for tr in c.find_all('tr') if 'Inglês' in tr.get_text() and 'R\$' in tr.get_text()][:3])
"

# scan de 1 set pra testar o fix end-to-end:
python myp_arbitrage_scanner.py --editions \"Ascended Heroes\" -o ah.xlsx
```

---

## TL;DR pro review

Truncation **é resolvível** e o root cause está achado: a tabela de marketplace
(`#lista-anuncio-demais-vendedores`) **pagina** via `?estoque-outros-page=N`, e o
scanner só lê a página 1. **Fix:** em `scrape_product`, seguir as páginas posteriores
da tabela marketplace e acumular EN-NM antes de `min()`. Prova: Psyduck real é **R$398**
(página 2), não R$498 — vira deal de +40%. Custo: cada produto truncado vira 1+N
requests; pagine só quando a página 1 sinalizar truncation. Guard-rails: cap de páginas,
delay, single-session (CloudFlare). Fixture de teste: `/tmp/psyduck.html` + página 2.
