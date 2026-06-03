# Re-validação dos cards truncados — fix v5.9 (ME: Ascended Heroes)

*Gerado 2026-06-03 ~18:25 UTC — scrape ao vivo com o fix de paginação da tabela
marketplace ([PR #13](https://github.com/matheuscllm-lgtm/myp-arbitrage-scanner/pull/13)).
Supersede a análise de "janela de incerteza"
([`manual-2026-06-03-truncation-window.md`](manual-2026-06-03-truncation-window.md)),
que só conseguia estimar o "melhor caso" — aqui são os **números reais**.*

## Como foi medido

Os 7 cards flagados foram re-scrapados numa **única sessão sequencial**
(`delay=2.5s`, single cloudscraper — CloudFlare). Pra cada um o scanner seguiu a
paginação `?estoque-outros-page=N` da tabela marketplace e recalculou o lowest
EN-NM sobre **todas** as páginas antes do `min()`. **0 falhas de fetch**; todos
resolveram com `en_truncation_risk = False`.

## Resultado

| Card | Antes (teto, só pág 1) | **EN-NM real** | TCG | **Margem real** | Págs extras | Veredito vs 25% |
|---|---:|---:|---:|---:|:---:|:---:|
| Psyduck (226/217) | R$498,70 (+12%) | **R$398,00** | R$557,40 | **+40%** | +2 | 🟢 deal real |
| Mega Dragonite ex (271/217) | R$300 (+0%) | **R$200,00** | R$300,15 | **+50%** | +3 | 🟢 deal real |
| Mega Gengar ex (269/217) | R$400 (+12%) | **R$290,00** | R$446,00 | **+54%** | +2 | 🟢 deal real |
| Tangela da Érica (218/217) | R$130 (+4%) | **R$105,00** | R$135,50 | **+29%** | +1 | 🟢 deal real |
| Mewtwo ex da Equipe Rocket (281/217) | R$2400 (−6%) | R$2399,97 | R$2263,50 | −6% | +1 | ⚪ não-deal (confirmado) |
| Grimmsnarl ex da Marine (287/217) | R$550 (−25%) | R$500,00 | R$412,75 | −17% | +1 | ⚪ negativo |
| Fezandipiti ex (288/217) | R$560 (−36%) | R$550,00 | R$360,10 | −35% | +1 | ⚪ negativo |

## Leitura

- **4 dos 7 cards cruzaram o threshold de 25%** que o scanner antigo perdia por
  completo (Psyduck +40%, Mega Dragonite +50%, Mega Gengar +54%, Tangela +29%).
  O EN-NM mais barato estava em página 2+ da marketplace, escondido atrás de
  listings PT/JP.
- **Mewtwo TR**: o gate paginou, mas **não** havia EN-NM mais barato oculto — o
  R$2400 era real. O fix confirma corretamente que **não** é deal (evita falso
  positivo tanto quanto recupera falso negativo).
- **Grimmsnarl / Fezandipiti** (BAIXA na análise antiga): melhoraram um pouco
  mas seguem com margem negativa → corretamente fora.
- A "janela / upside potencial" da análise antiga era o **melhor caso** (EN-NM
  no piso). O real ficou entre o teto antigo e esse piso — exatamente o esperado.
  Não é mais estimativa: o scanner resolve sozinho.

## ⚠️ Caveats (dados pra decisão do operador — não são recomendações de compra)

1. **Todos os 6 (além do Psyduck) são oversized-collector#** (271>217, 269>217,
   etc.) → variantes SIR/special-art da Ascended Heroes. O scanner já os marca
   `oversized_collector_risk=True` → caem em **🚨 Validate Manually**, e o link
   TCG é busca por nome (não direto). Antes de qualquer ação: confirmar
   visualmente **variante + condição NM + idioma EN** do listing mais barato.
2. Mewtwo / Grimmsnarl / Fezandipiti também dispararam o aviso **SIR/HR
   misclassificado** (`rarity='Comum'` mas TCG alto) — esperado nessa faixa,
   reforça a triagem manual.
3. Margem usa o modelo padrão do scanner (custo = preço × 1.06, frete 0). FX e
   spread não entram aqui.

## Produtos resolvidos nesta sessão

| Card | Product URL |
|---|---|
| Psyduck (226/217) | https://mypcards.com/pokemon/produto/310463/psyduck |
| Mega Dragonite ex (271/217) | https://mypcards.com/pokemon/produto/310508/mega-dragonite-ex |
| Mega Gengar ex (269/217) | https://mypcards.com/pokemon/produto/310506/mega-gengar-ex |
| Mewtwo ex da Equipe Rocket (281/217) | https://mypcards.com/pokemon/produto/310518/mewtwo-ex-da-equipe-rocket |
| Tangela da Érica (218/217) | https://mypcards.com/pokemon/produto/310455/tangela-da-erica |
| Grimmsnarl ex da Marine (287/217) | https://mypcards.com/pokemon/produto/310524/grimmsnarl-ex-da-marine |
| Fezandipiti ex (288/217) | https://mypcards.com/pokemon/produto/310525/fezandipiti-ex |
