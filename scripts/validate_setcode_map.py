#!/usr/bin/env python3
"""Audita o mapa `MYP_EDITION_SUBSTR_TO_PTCG` contra os metadados REAIS dos sets
no pokemontcg.io — pega mapeamento `edition→setcode` errado (a classe do bug
Black Bolt/White Flare base-086, onde o setcode aponta pro set errado e o preço
sai furado) ANTES de virar margem ilusória.

Ferramenta de AUDITORIA, isolada do scanner: **não toca** o caminho de preço
(`_real_tcg_brl`/tcgcsv/cache). Só LÊ o mapa e cruza com o `/v2/sets/{setcode}`.

Para cada `(substring de edição → setcode)` confere:
  - o setcode EXISTE no pokemontcg.io? (404 = mapa quebrado → 🚨)
  - o NOME do set bate com a substring da edição? (sem sobreposição de tokens =
    suspeita de set errado → ⚠️)
  - reporta `printedTotal`/`total` — o **set-total** é a impressão digital que a
    validação de carta usa; tê-lo à mão por setcode habilita um guard de runtime
    depois (medir antes de mudar, como manda o CLAUDE.md).

Honesto (regra dura do repo): sem rede / sem cobertura → marca e segue, **nunca
inventa**. Saída = tabela markdown (convenção de entrega), problemas primeiro.

Uso:
    python scripts/validate_setcode_map.py            # audita todos os 106
    python scripts/validate_setcode_map.py --limit 10 # smoke rápido
    POKEMONTCG_API_KEY=... python scripts/validate_setcode_map.py   # sem throttle
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

# importa o mapa do scanner (fonte única — nunca duplicar)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from myp_arbitrage_scanner import MYP_EDITION_SUBSTR_TO_PTCG  # noqa: E402

SETS_ENDPOINT = "https://api.pokemontcg.io/v2/sets/"

# palavras de série/genéricas que NÃO contam como evidência de que o nome bate
# (senão "Scarlet & Violet" casaria qualquer set SV pelo prefixo da série).
_STOPWORDS = {
    "the", "and", "of", "ex", "gx", "tcg", "pokemon", "pokémon",
    "scarlet", "violet", "sword", "shield", "sun", "moon", "xy", "black",
    "white", "diamond", "pearl", "platinum", "heartgold", "soulsilver",
    "set", "series", "expansion", "mega", "evolution",
}


def _tokens(text: str) -> set[str]:
    """Tokens significativos (alnum, len>=3, sem stopwords de série)."""
    raw = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {t for t in raw if len(t) >= 3 and t not in _STOPWORDS}


def _edition_core(substr: str) -> str:
    """Parte significativa da substring de edição: depois do último ':' / '-'
    (ex.: 'XY 5: Primal Clash' -> 'Primal Clash'; 'Prismatic Evolutions' -> idem)."""
    core = re.split(r"[:\-]", substr)[-1].strip()
    return core or substr


def classify(edition_substr: str, set_name: Optional[str],
             set_exists: bool) -> tuple[str, str]:
    """Lógica PURA (testável offline) de status do mapeamento.

    Retorna (status, motivo) com status em {'ok', 'warn', 'broken'}:
      - 'broken'  : setcode não resolve no pokemontcg.io (404/sem set).
      - 'warn'    : set existe mas o nome NÃO compartilha nenhum token
                    significativo com a substring da edição (possível set errado).
      - 'ok'      : set existe e há sobreposição de token OU um é substring do
                    outro (mapeamento plausível).
    Conservador: só marca 'warn' quando NÃO há relação nenhuma — minimiza falso
    alarme em diferenças menores de nome ("Champion's Path" vs "Champions Path").
    """
    if not set_exists or not set_name:
        return "broken", "setcode não existe no pokemontcg.io (404/sem set)"
    core = _edition_core(edition_substr)
    et, st = _tokens(core), _tokens(set_name)
    if not et or not st:
        # sem tokens significativos dos dois lados (ex.: nome só de série) →
        # não dá pra afirmar divergência; trata como ok (sem sinal de erro).
        return "ok", "sem tokens comparáveis (inconclusivo, sem sinal de erro)"
    if et & st:
        return "ok", f"tokens em comum: {sorted(et & st)}"
    nl, cl = set_name.lower(), core.lower()
    if cl in nl or nl in cl:
        return "ok", "um nome é substring do outro"
    # palavras compostas escritas com/sem espaço ("Fire Red" vs "FireRed"):
    dn = re.sub(r"[^a-z0-9]", "", nl)
    dc = re.sub(r"[^a-z0-9]", "", cl)
    if dc and (dc in dn or dn in dc):
        return "ok", "nomes equivalentes ignorando espaços/pontuação"
    return "warn", f"sem token em comum (edição~{sorted(et)} vs set~{sorted(st)})"


def fetch_set(setcode: str, api_key: Optional[str], timeout: int = 20) -> dict:
    """GET /v2/sets/{setcode}. Distingue HONESTAMENTE três casos:
      - set existe        → dict com os dados;
      - 404 (não existe)  → {}  (mapa genuinamente quebrado);
      - 429/erro de rede  → {"_skip": motivo}  (transitório, NÃO é problema de
                            mapa — re-rode, idealmente com POKEMONTCG_API_KEY).
    NUNCA inventa: throttle/erro vira 'skip' marcado, jamais 'broken'."""
    req = urllib.request.Request(
        SETS_ENDPOINT + setcode,
        headers={"User-Agent": "myp-setmap-audit",
                 "Accept": "application/json",
                 **({"X-Api-Key": api_key} if api_key else {})},
    )
    for attempt, backoff in enumerate((2, 5, 0)):  # 2 retries leves p/ 429/5xx
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return (json.loads(r.read()).get("data") or {})
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}  # set genuinamente inexistente
            if e.code in (429, 500, 502, 503) and backoff:
                time.sleep(backoff)
                continue
            return {"_skip": f"HTTP {e.code}"}
        except Exception as e:  # noqa: BLE001
            if backoff:
                time.sleep(backoff)
                continue
            return {"_skip": repr(e)}
    return {"_skip": "throttle persistente (defina POKEMONTCG_API_KEY)"}


_BADGE = {"broken": "🚨", "warn": "⚠️", "ok": "✅", "skip": "❔"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0, help="audita só os N primeiros")
    ap.add_argument("--delay", type=float, default=0.0,
                    help="pausa entre requests (sem API key, use ~0.3)")
    args = ap.parse_args()

    api_key = (os.environ.get("POKEMONTCG_API_KEY") or "").strip() or None
    items = list(MYP_EDITION_SUBSTR_TO_PTCG.items())
    if args.limit:
        items = items[: args.limit]

    rows, counts = [], {"broken": 0, "warn": 0, "ok": 0, "skip": 0}
    for i, (substr, setcode) in enumerate(items, 1):
        data = fetch_set(setcode, api_key)
        if data.get("_skip"):
            counts["skip"] += 1
            rows.append(("skip", substr, setcode, "—", "—", "—",
                         f"não auditado (transitório): {data['_skip']}"))
        else:
            exists = bool(data)
            name = data.get("name")
            status, reason = classify(substr, name, exists)
            counts[status] += 1
            rows.append((status, substr, setcode, name or "—",
                         str(data.get("printedTotal") or "—"),
                         str(data.get("total") or "—"), reason))
        print(f"\r  auditando {i}/{len(items)}…", end="", file=sys.stderr, flush=True)
        if args.delay:
            time.sleep(args.delay)
    print("", file=sys.stderr)

    # problemas primeiro (broken, warn), depois ok, depois skip
    order = {"broken": 0, "warn": 1, "ok": 2, "skip": 3}
    rows.sort(key=lambda r: (order[r[0]], r[1].lower()))

    print(f"# Auditoria do mapa edition→setcode ({len(items)} entradas)\n")
    if counts["skip"]:
        print(f"> ❔ {counts['skip']} não auditado(s) (throttle/rede — transitório, "
              f"NÃO é erro de mapa). {'Defina POKEMONTCG_API_KEY e re-rode' if not api_key else 'Re-rode'} "
              f"pra fechar a cobertura.\n")
    print(f"**{counts['broken']} 🚨 quebrados · {counts['warn']} ⚠️ suspeitos · "
          f"{counts['ok']} ✅ ok · {counts['skip']} ❔ não auditados**\n")
    print("| | Edição (substring MYP) | setcode | Set (pokemontcg.io) | printed | total | Motivo |")
    print("|---|---|---|---|---|---|---|")
    for status, substr, setcode, name, printed, total, reason in rows:
        print(f"| {_BADGE[status]} | {substr} | `{setcode}` | {name} | "
              f"{printed} | {total} | {reason} |")

    # exit != 0 só se houver problema REAL de mapa (broken/warn); skip não conta
    return 1 if (counts["broken"] or counts["warn"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
