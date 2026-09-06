> **Regra vigente de entrega:** [DELIVERY_CHAT.md](DELIVERY_CHAT.md). Resultados somente no chat, referência clicável e coleta nova por solicitação; substitui orientações antigas de entrega via GitHub ou preços reutilizados.

# price-compare-tool

Ferramenta pessoal de linha de comando que compara preços de itens entre duas
fontes públicas e gera uma planilha `.xlsx` + um resumo em markdown. Roda local
ou no GitHub Actions (matrix paralelo).

> Projeto pessoal de uso único. Publicado principalmente para usar CI gratuito.
> Documentação operacional detalhada (convenções, fluxo de execução, formato de
> entrega) fica em [`CLAUDE.md`](CLAUDE.md).

## Setup

Requer Python 3.10+ (testado em 3.12 e 3.14).

```bash
git clone https://github.com/matheuscllm-lgtm/<repo>.git
cd <repo>

python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

No Windows, exporte o encoding antes de rodar (logs usam UTF-8):

```bash
# PowerShell:
$env:PYTHONIOENCODING = "utf-8"
# Bash:
export PYTHONIOENCODING=utf-8
```

## Uso

```bash
# Execução padrão
python myp_arbitrage_scanner.py

# Escopo reduzido para teste rápido (~5 min)
python myp_arbitrage_scanner.py --max-editions 3

# Filtrar por substring de título
python myp_arbitrage_scanner.py --editions "Ascended Heroes"

# Saída customizada
python myp_arbitrage_scanner.py --editions "Prismatic" -o my_output.xlsx
```

Principais flags: `--editions <substr>...`, `--threshold <int>` (inteiro em
percent — convenção oposta à da ferramenta irmã, que usa fração), `--min-price
<float>`, `--delay <float>`, `--max-editions`, `--max-products`,
`--chunk-index` / `--chunk-total` (matrix). Detalhes completos em
[`CLAUDE.md`](CLAUDE.md).

## Testes

```bash
python -m pytest -q
```

A suíte é offline (sem rede), com fixtures sintéticas. Roda também no CI
(`.github/workflows/tests.yml`) em `ubuntu-latest`, sem secrets.

## GitHub Actions

Há workflows de execução agendada/manual (matrix job + agregação) além do
workflow de testes. Eles produzem os resultados como **artifacts** da run
(baixáveis via aba Actions ou `gh run download`), não como arquivos
commitados no repositório. Configuração e schedules em [`CLAUDE.md`](CLAUDE.md).

## Author

Matheus Chillemi

## Recuperação de falhas de coleta

HTTP 429 respeita Retry-After e espera pelo menos 60/120 segundos entre tentativas.
Falha persistente encerra como parcial (exit 2), salvando XLSX, status JSON e
checkpoint. O progresso é salvo dentro da edição, a cada dez produtos, e na
interrupção. O checkpoint identifica produtos concluídos e escopo/configuração;
retomar não duplica cartas nem pula o produto que falhou. Checkpoints antigos ou
de outro escopo são ignorados. Use `--resume` explicitamente somente para a mesma
solicitação interrompida; uma coleta nova começa com saída nova.
