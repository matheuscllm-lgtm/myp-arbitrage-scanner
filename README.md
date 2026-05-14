# MYP Arbitrage Scanner

Scanner de arbitragem que compara preços de singles Pokémon TCG (EN, Near Mint) no [mypcards.com](https://mypcards.com) contra a referência TCGplayer exibida na própria página do produto MYP. Saída em planilha `.xlsx` com sheets de deals, top-50 por margem, e candidatos a validação manual.

## Saída

O scanner gera um xlsx com 5 sheets:

| Sheet | Conteúdo |
|---|---|
| 🔥 Deals | Cards com margem ≥ threshold (default 25%) ordenados desc |
| All EN Cards | Todos cards EN-NM encontrados, ordenados por margem desc |
| 🏆 Top 50 Margin | Top 50 por margem sem filtro de threshold — pool de inspeção visual chase-card |
| 🚨 Validate Manually | Cards com flag `en_truncation_risk` (lowest EN reportado pode estar superestimado) |
| Summary | Métricas do scan (pages, deals, skips, warnings) |

## Margem calculada

```
margem% = (TCG_player_price - MYP_lowest_EN_NM) / MYP_lowest_EN_NM
```

**Não inclui:** frete, taxas, markup de revenda, impostos. Margem reportada é bruta, não líquida.

## Heurísticas defensivas

### H3 — Supranumerário rarity mismatch
Cards com `card_num > set_total` (ex.: `226/217`) frequentemente são variantes IR/SIR/SAR misclassificadas como "Comum" no MYP. Quando rarity=Comum/Incomum + TCG>R$200 + supranumerário, emite warning. Reduz falso positivo em cross-variant mismatch (regular vs raro).

### T1 — EN truncation risk
A página do produto MYP tem 2 seller tables (lojistas ~15 rows + marketplace ~20 rows), ordenadas por preço ascendente agnóstica de idioma. Quando uma tabela atinge cap sem nenhuma listing EN visível **E** o max_price visível < lowest_EN reportado, há risco de listings EN-NM escondidos serem mais baratos. Flag emitido pra validação manual.

Caso concreto documentado: Psyduck (226/217) ME:AH — scanner reportou R$415 lowest EN-NM, seller "bartsimpson" tinha o mesmo card a R$300 EN-NM truncado da página por 20 listings PT/JP.

## Uso

```bash
# Instalar dependências (recomendado em venv)
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt

# Scan default (todas edições, threshold 25%)
python myp_arbitrage_scanner.py

# Scan filtrado em sets específicos (substring match contra título da edição)
python myp_arbitrage_scanner.py --editions "Ascended Heroes" "Black Bolt" "White Flare"

# Output customizado
python myp_arbitrage_scanner.py --editions "Prismatic Evolutions" -o my_scan.xlsx
```

## Flags

| Flag | Default | Descrição |
|---|---|---|
| `--editions <substr>...` | (todas) | Substring match contra título da edição MYP |
| `--threshold <int>` | 25 | Margem mínima % pra alerta (note: < 1.0 auto-converte com warning) |
| `--min-price <float>` | 80 | Preço mínimo EN-NM em R$ pra incluir |
| `--delay <float>` | 1.5 | Segundos entre requests (aumentar se site instável) |
| `--max-editions <int>` | 0 | Limita número de edições (debug) |
| `--max-products <int>` | 0 | Limita produtos por edição (debug) |
| `-o`, `--output <path>` | timestamp auto | Caminho do xlsx de saída |

## GitHub Actions — rodar na nuvem

O workflow `.github/workflows/weekly-scan.yml` executa o scanner no GitHub:

- **Manual:** Actions → "Weekly MYP Scan" → Run workflow. Inputs: `editions` (substrings em "", vazio = scan tudo), `threshold`, `min_price`, `max_editions`, `max_products`, `delay`.
- **Automático:** semanal (domingo 09:00 BRT / 12:00 UTC). Default = scan completo (todas edições, threshold 25%).
- **Output:** xlsx + `.debug/` enviados como workflow artifact, retenção 30 dias. Download via Actions UI.

Sem secrets necessários — MYP API/scrape é anônimo. Timeout 180min cobre worst-case (~2h scan completo). Concurrency group `myp-scan` previne overlaps.

## Encoding

No Windows, exportar `PYTHONIOENCODING=utf-8` antes de invocar — o scanner emite emojis no log que falham com `cp1252` default.

```powershell
$env:PYTHONIOENCODING = "utf-8"
py myp_arbitrage_scanner.py --editions "Ascended Heroes"
```

## ⚠️ Vício conhecido da MYP API (por que este scanner NÃO usa API)

A MYP tem uma REST API pública em `https://mypcards.com/api/v1` (descoberta 2026-05-07, sem auth, OpenAPI 3.1). Schema `Produto` retorna `min_price`, `avg_price`, `max_price` em BRL agregados + `tcg_price` USD da TCGPlayer.

**Vício:** os preços agregados (`min_price` etc.) **misturam todas as línguas** (PT + JP + EN + IT + ES + ...) num campo único. Não há filtro `?language=en` no servidor. Para arbitragem EN-NM (que é o que vendemos no TCGPlayer), o `min_price` pode estar refletindo uma listing PT/JP irrelevante.

**Sintoma real (2026-05-07):** Terapagos ex scr 170 — API mostrou R$100 floor com 14 listings. HTML scrape confirmou: **0 EN, 13 PT**. Sem o scrape, teríamos cancelado R$580 de deals válidos CT achando que MYP dominava.

**Bonus quirk — apostrophe bug:** endpoint `/carta/{nome}` retorna HTTP 200 + cards vazios pra nomes com `'`. Cards como "Team Rocket's X", "N's Plan", "Lillie's X", "Morty's X" não retornam match mesmo existindo. Workaround: URL-encode `%27` ou skip via pattern.

**Por isso este scanner NÃO usa a API**, vai direto no HTML scrape per-product:
- O parser pega cada `<tr>` da seller table, lê o `flag-icon[title]` pra detectar idioma, filtra `Inglês` + `NM`
- Ground truth por listing — não tem como a API substituir isso

**Quando a API ainda é útil (em ferramenta separada):**
- Cross-reference rápido de 1 card CT contra MYP (lookup pontual em ~1s) — em `Scripts/myp_api_lookup.py`
- Pre-filtro pra batch grande (200+ deals) antes de ir pro targeted scrape detalhado

Para o nosso pipeline normal (CT scan → cross-reference MYP), o caminho é direto pro `myp_targeted_scrape.py` (combo: API só pega URL do produto + cloudscraper filtra EN-NM nas tabelas). Ground truth em ~2-5s/card.

## Limitações conhecidas

- **Truncamento de sellers**: MYP não expõe paginação per-language no rendered HTML. Cards com flag T1 indicam onde isso é provavelmente acontecendo, mas o scanner não consegue listar os sellers truncados — validação manual via perfil de sellers é necessária.
- **Tempo de scan**: ~16 produtos/min com delay 1.5s. 2.000+ produtos = ~2hr.
- **Margem bruta, não líquida**: frete + taxas + impostos não aplicados. Pra arbitragem real, descontar manualmente.
- **Reproducibilidade depende de listings ativos no momento do scan**: snapshots variam entre runs.

## Author

Matheus Chillemi
