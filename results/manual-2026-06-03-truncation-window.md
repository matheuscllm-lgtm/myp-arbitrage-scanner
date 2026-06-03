# Janela de incerteza — EN truncation (ME: Ascended Heroes)

*Gerado 2026-06-03 17:27 UTC — sem scrape adicional, a partir da resolução per-card de 2026-06-03.*

## Metodologia

O MYP renderiza no máx. ~20 listings por tabela (lojistas + marketplace), ordenadas por preço **across-idiomas** e cortadas server-side. Quando uma tabela enche de listings PT/JP, um EN-NM mais barato pode ficar numa 'página' que não existe no HTML nem na API (verificado: API oficial não expõe listings; servidor ignora `?idioma=`).

Para cada card flagado defino a **janela oculta**:

- **Teto** = menor EN-NM **visível** hoje (o que o scanner reporta).
- **Piso** = maior preço **visível** numa tabela CHEIA (20 rows) com **0 EN** cujo topo ainda está **abaixo** do EN atual. Abaixo desse piso é onde um EN-NM oculto poderia existir sem contradizer o que vemos.
- **Upside potencial** = margem vs TCG **se** existir um EN-NM no piso.
- **Largura da janela** = teto − piso. Janela estreita ⇒ pouco a ganhar mesmo no melhor caso; janela larga + upside alto ⇒ vale abrir os perfis.

> ⚠️ A janela é o **melhor caso**, não uma previsão. Confirma o upside **só** se um seller realmente tiver EN-NM perto do piso — exige checagem manual de perfil.

## Cards flagados — janela quantificada

| Card | EN atual (teto) | TCG | Margem atual | Piso oculto | Largura janela | Upside potencial | Vale validar? |
|---|---:|---:|---:|---:|---:|---:|:---:|
| Psyduck (226/217) | R$499 | R$557 | +12% | R$245 | R$254 (51%) | **até ~128%** | ALTA |
| Mega Dragonite ex (271/217) | R$300 | R$300 | +0% | R$135 | R$165 (55%) | **até ~122%** | ALTA |
| Mega Gengar ex (269/217) | R$400 | R$446 | +12% | R$250 | R$150 (38%) | **até ~78%** | ALTA |
| Mewtwo ex da Equipe Rocket (281/217) | R$2400 | R$2264 | -6% | R$1500 | R$900 (37%) | **até ~51%** | ALTA |
| Tangela da Érica (218/217) | R$130 | R$136 | +4% | R$90 | R$40 (31%) | **até ~51%** | ALTA |
| Grimmsnarl ex da Marine (287/217) | R$550 | R$413 | -25% | R$425 | R$125 (23%) | **até ~-3%** | BAIXA |
| Fezandipiti ex (288/217) | R$560 | R$360 | -36% | R$500 | R$60 (11%) | **até ~-28%** | BAIXA |

## Priorização

**🔴 ALTA prioridade** (janela larga + upside grande — abrir perfis dos sellers PT/JP da tabela cheia):
- Psyduck (226/217) — atual +12%, pode chegar a ~128% se houver EN-NM ~R$245. [link](https://mypcards.com/pokemon/produto/310463/psyduck)
- Mega Dragonite ex (271/217) — atual +0%, pode chegar a ~122% se houver EN-NM ~R$135. [link](https://mypcards.com/pokemon/produto/310508/mega-dragonite-ex)
- Mega Gengar ex (269/217) — atual +12%, pode chegar a ~78% se houver EN-NM ~R$250. [link](https://mypcards.com/pokemon/produto/310506/mega-gengar-ex)
- Mewtwo ex da Equipe Rocket (281/217) — atual -6%, pode chegar a ~51% se houver EN-NM ~R$1500. [link](https://mypcards.com/pokemon/produto/310518/mewtwo-ex-da-equipe-rocket)
- Tangela da Érica (218/217) — atual +4%, pode chegar a ~51% se houver EN-NM ~R$90. [link](https://mypcards.com/pokemon/produto/310455/tangela-da-erica)

**⚪ BAIXA** (mesmo no melhor caso, pouco a ganhar — pode pular):
- Grimmsnarl ex da Marine (287/217) — teto ~-3%
- Fezandipiti ex (288/217) — teto ~-28%

## Como validar (passo manual restante)

1. Abrir o link do card → tabela 'marketplace' (a cheia, com 0 EN).
2. Para cada seller PT/JP com preço perto/abaixo do piso, abrir o perfil do seller.
3. Procurar o **mesmo card em EN-NM** no estoque dele (o MYP trunca a *exibição* no produto, mas o estoque do seller é navegável no perfil).
4. Se achar EN-NM ≤ piso → deal real; recalcular margem vs TCG.

*Único passo não-automatizável hoje: o MYP não expõe o estoque per-idioma do seller por API. Tudo acima da linha foi quantificado automaticamente.*