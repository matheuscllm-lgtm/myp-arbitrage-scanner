# Loop iterativo de otimização do MYP scanner

> Como usar o **loop de dev do Claude Code** (*medir → mudar → verificar →
> repetir*) pra otimizar o `myp_arbitrage_scanner.py` com evidência, em vez de
> chutar. Este é o caminho canônico — qualquer sessão (terminal/web/nuvem) roda
> igual.

## Por que existe

Não há um comando "loop engineering" no Claude Code. O que otimiza o scanner é
um **ciclo iterativo** apoiado em: subagentes `Explore`/`Plan`, as skills
`/code-review` e `/simplify`, o gate de teste offline e o `bench.py`. (A skill
`/loop` é um **agendador** — re-executa um prompt em intervalo; serve pra
re-rodar/monitorar, não pra otimizar.)

O scanner é **lento por design** (~2h41 num quick) e até a v5.11.7 **não media
tempo** — só contava eventos. Sem medir, não dá pra iterar. Por isso a fundação
(v5.11.8) é: **instrumentação de tempo** + **`bench.py`** + a flag já existente
**`--max-products`** (ciclo interno rápido).

## O ciclo (uma iteração)

1. **Medir** — `python bench.py > before.txt`. Baseline reprodutível.
2. **Hipótese** — pegue **um** item do backlog com alvo numérico
   (ex.: "derrubar `ptcg_calls` de ~O(cards) pra ~O(sets)").
3. **Mudar** — a menor mudança possível. `Explore` pra localizar; `Plan` pra
   desenhar algo não-trivial.
4. **Verificar** (gate duplo, obrigatório):
   - **Correção:** `python test_v5_8_offline.py` → exit 0 (24 testes, ~2s, sem
     rede). Mexeu em preço? rode o oráculo `python scripts/cross_check_myp_api.py <xlsx>`.
   - **Efeito:** `python bench.py > after.txt && diff before.txt after.txt`.
5. **Revisar** — `/code-review` (bugs) e `/simplify` (limpeza) no diff.
6. **Fechar** — commit + entrada no `CHANGELOG.md` com o antes/depois do bench.
   Repetir.

## Ferramentas por passo

| Passo | Ferramenta Claude Code |
|---|---|
| Localizar código | subagente `Explore` |
| Desenhar mudança não-trivial | subagente `Plan` |
| Verificar correção | `python test_v5_8_offline.py` + `scripts/cross_check_myp_api.py` |
| Medir efeito | `python bench.py` (+ contadores de `self._stats`) |
| Revisar o diff | `/code-review`, `/simplify` |
| Re-rodar/monitorar em intervalo | skill `/loop` (ex.: re-checar CI) |
| Medir em escala (scan real) | workflow `quick-scan.yml` (1 IP por runner) |

## `bench.py` — como ler

```
python bench.py                  # mockado, sem rede (CI-safe). Foco: ptcg_calls.
python bench.py --live --editions "Surging Sparks" --limit-products 5   # tempo real
```

- **Modo mockado (default):** substitui só a **rede** (`session.get` + câmbio);
  `scrape_product`, `_get`, `_real_tcg_brl`, `_fetch_ptcg_usd` e o cache rodam de
  verdade. Logo **`ptcg_calls` é real** (round-trips à pokemontcg.io) — é a
  métrica que a otimização "batch por set" deve derrubar. Os `t_*` ficam ~0
  (I/O fake é instantânea).
- **`--live`:** scan real → os `t_*` viram tempo de relógio (precisa de rede e,
  de preferência, `POKEMONTCG_API_KEY`). Use `--repeat N` pra mediana.

Métricas no relatório: `wall_total_s`, `products_scanned`, `pages_fetched`,
`ptcg_calls`, `t_http_total_s`, `t_ptcg_total_s`, `t_editions_total_s`,
`en_found`, `tcg_from_real`, `tcg_from_myp_fallback`. As mesmas linhas saem no
summary do scanner (`log`, ao fim de `scan()`).

## Instrumentação (onde o tempo é medido)

Aditiva, sempre ligada, overhead desprezível (`time.perf_counter`):
- `_get()` → `_stats["t_http_total"]` (sleep + fetch + parse de toda página MYP).
- `_fetch_ptcg_usd()` → `_stats["t_ptcg_total"]` + `_stats["ptcg_calls"]`
  (conta **só round-trip real** — cache-hit não passa por aqui).
- loop por edição em `scan()` → `_stats["t_editions_total"]`.

## Backlog (as iterações, priorizadas)

**Velocidade**
- **V3 — batch pokemontcg.io por set** *(Iteração #1 — ✅ v5.12)*: 1 `GET /v2/cards?q=set.id:<setcode>`
  paginado pré-popula `_ptcg_cache` da edição → derruba `ptcg_calls` de ~O(cards)
  pra ~O(sets). Estratégia de menor risco: **cache positivo** — cids ausentes
  caem no `_fetch_ptcg_usd` atual (preserva 404→fallback). Cuidado com a chave
  `{setcode}-{num}` (`num.lstrip("0")`) e a seleção `min(market|mid)`.
- V4 — sondar o piso do `--delay` (1.5s domina todo GET) medindo 403 vs delay.

**Correção / falso-positivo**
- C1 — ampliar cobertura `MYP_EDITION_SUBSTR_TO_PTCG` + número→id de variantes
  supranumerárias (097/086) → preço **real** em vez do `.estat-tcg` inflado.
- C2 — `tcg_suspect` sem preço real ⇒ suprimir/rebaixar a margem (não reportar
  deal falso). Travar com a fixture Jirachi.
- C3 — fixtures offline dos casos base-086 (Black Bolt/White Flare).

**Custo / rate-limit**
- Co1 — V3 também corta requests e risco de 429.
- Co2 — confirmar `POKEMONTCG_API_KEY` em todos os workflows + env local.
- Co3 — medir `pagination_skipped_low_tcg` (cost gate v5.10.1 já corta ~85%).

**Qualidade**
- Q1 *(Iteração #2)* — refatorar `scrape_product()` (~377 linhas) em helpers;
  verificável 100% pelos testes offline (refactor puro). Demonstra `/code-review`
  + `/simplify`.

## Regras que NÃO mudam no loop

- Margem é **BRUTA pura** `(tcg − br)/br` — nada de fee/markup no cálculo.
- Invariante **EN-NM only**.
- **Não paralelizar fetches no mesmo IP** (403 CF). Paralelismo só por chunk no
  CI (`--chunk-index`/`--chunk-total`, 1 IP por runner).
- Toda iteração mantém os **24 testes** verdes; mudança de preço passa pelo
  oráculo `cross_check_myp_api.py`.
