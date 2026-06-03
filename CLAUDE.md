# CLAUDE.md — instruções para agentes (Claude Code) neste repo

> Objetivo: "rodar o MYP scanner" tem **um caminho só**. Siga este arquivo e
> evite re-descobrir coisas que já estão resolvidas no código.

## Este é o repo canônico

`matheuscllm-lgtm/myp-arbitrage-scanner` é a **fonte de verdade única** do MYP
scanner (extraído do antigo monorepo `tcg-arbitrage-scanners` em 2026-05-13).
Se você encontrar um `myp_arbitrage_scanner.py` em qualquer outro lugar
(`tcg-arbitrage-scanners`, `Scripts/`, cópia em Drive/Obsidian), é **STALE
pré-extração** — não rode. Confira o cabeçalho: `Versão: v5.9` (ou superior).

## Setup (env novo)

```bash
pip install -r requirements.txt   # cloudscraper, bs4, lxml, openpyxl, brotli
export PYTHONIOENCODING=utf-8      # Windows PowerShell: $env:PYTHONIOENCODING="utf-8"
```
`brotli` é **obrigatório**: a Cloudflare serve `Content-Encoding: br`; sem ele o
HTML volta cru e o parser acha 0 edições silenciosamente.

## ⚠️ Cloudflare — NÃO perca tempo testando fingerprint

A Cloudflare bloqueia o fingerprint **chrome** do cloudscraper (HTTP **403**).
**Não** "valide" o acesso com um `cloudscraper.create_scraper()` puro — ele vai
dar 403 e te levar a uma falsa pista de bloqueio. O scanner **já resolve isso**:
usa `browser={"browser":"firefox","platform":"windows"}` por padrão (env
`MYP_CLOUDSCRAPER_BROWSER`, default `firefox`), que retorna **200**. Apenas rode
o scanner.

## Rodar

```bash
python myp_arbitrage_scanner.py --editions "Ascended Heroes" \
  --threshold 25 --min-price 80 --delay 1.5 \
  -o results/<set>_<stamp>.xlsx
```

- `--editions` = **substring** do título da edição MYP (ex.: `"Ascended Heroes"`
  casa `"ME: Ascended Heroes"`; `Mega` casa todos os ME0x). Não são aliases.
- `--threshold` é **percent integer** (`25` = 25%; valor <1.0 auto-converte com
  warning). Convenção oposta à do CardTrader scanner (lá é fração).
- Scan é **lento por design** (`--delay` × centenas de produtos × N edições →
  pode passar de 1h em scan largo). Para runs longos, rode detached/background.
- Single-session sequencial. **Não paralelize fetches no mesmo IP** (a v5.9 segue
  paginação `?estoque-outros-page=N` da tabela marketplace; 2 sessões no mesmo IP
  = 403 CF).

## Saída e commit

- Outputs vão pra `results/`. **O `.xlsx` é gitignored de propósito** (`*.xlsx`).
  O que entra no repo é um **resumo markdown** (`results/<scope>-<data>.md`), no
  padrão de `daily-*.md` / `manual-*.md`.
- Workflow = **branch + PR** (não dê push direto em `main`; ele é gateado).

## Não confundir

Existe um scanner irmão de **CardTrader** (repo `card-trader-scanner`, usa
`.venv`, `--max-expansions`, threshold **fracionário**). É outro projeto.
