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

## Encoding

No Windows, exportar `PYTHONIOENCODING=utf-8` antes de invocar — o scanner emite emojis no log que falham com `cp1252` default.

```powershell
$env:PYTHONIOENCODING = "utf-8"
py myp_arbitrage_scanner.py --editions "Ascended Heroes"
```

## Limitações conhecidas

- **Truncamento de sellers**: MYP não expõe paginação per-language no rendered HTML. Cards com flag T1 indicam onde isso é provavelmente acontecendo, mas o scanner não consegue listar os sellers truncados — validação manual via perfil de sellers é necessária.
- **Tempo de scan**: ~16 produtos/min com delay 1.5s. 2.000+ produtos = ~2hr.
- **Margem bruta, não líquida**: frete + taxas + impostos não aplicados. Pra arbitragem real, descontar manualmente.
- **Reproducibilidade depende de listings ativos no momento do scan**: snapshots variam entre runs.

## Author

Matheus Chillemi
