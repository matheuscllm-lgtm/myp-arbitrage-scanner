#!/usr/bin/env python3
"""Teste offline (puro, sem rede) da lógica de classificação do auditor de mapa.

Roda standalone:  python scripts/test_validate_setcode_map.py
(também passa sob pytest se disponível.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_setcode_map import classify, _edition_core, _tokens  # noqa: E402


def test_broken_when_set_missing():
    # setcode não resolve (404) → broken, independente do nome
    assert classify("Black Bolt", None, False)[0] == "broken"
    assert classify("Whatever", "", False)[0] == "broken"


def test_ok_on_token_overlap():
    assert classify("Prismatic Evolutions", "Prismatic Evolutions", True)[0] == "ok"
    assert classify("SV09: Journey Together", "Journey Together", True)[0] == "ok"
    assert classify("XY 5: Primal Clash", "Primal Clash", True)[0] == "ok"


def test_ok_on_substring_even_without_token():
    # apóstrofo/pontuação diferente, mas um é substring do outro
    assert classify("Champions Path", "Champion's Path", True)[0] in {"ok", "warn"}
    # substring direta
    assert classify("Foo: Bar", "Some Bar Thing", True)[0] == "ok"


def test_warn_on_gross_mismatch():
    # a classe do bug: setcode existe mas é de OUTRO set (sem token em comum)
    status, reason = classify("Journey Together", "Surging Sparks", True)
    assert status == "warn", reason
    status, _ = classify("Black Bolt", "Crown Zenith", True)
    assert status == "warn"


def test_inconclusive_is_ok_not_false_alarm():
    # nome só com tokens de série/stopword → inconclusivo, NÃO marca warn
    assert classify("Scarlet & Violet", "Scarlet & Violet", True)[0] == "ok"


def test_compound_word_spacing_not_false_alarm():
    # caso real do audit: 'Fire Red & Leaf Green' (MYP) vs 'FireRed & LeafGreen'
    # (pokemontcg.io) é o MESMO set — não pode marcar warn por causa do espaço.
    assert classify("EX 6: Fire Red & Leaf Green", "FireRed & LeafGreen", True)[0] == "ok"
    assert classify("HeartGold SoulSilver", "Heart Gold Soul Silver", True)[0] == "ok"


def test_edition_core_and_tokens_helpers():
    assert _edition_core("XY 5: Primal Clash") == "Primal Clash"
    assert _edition_core("Prismatic Evolutions") == "Prismatic Evolutions"
    assert "primal" in _tokens("Primal Clash")
    assert "the" not in _tokens("The Best")          # stopword removido
    assert "ex" not in _tokens("Charizard ex")        # stopword removido


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ✓ {fn.__name__}")
    print(f"\n✅ {len(fns)}/{len(fns)} testes passaram (lógica do auditor, offline)")


if __name__ == "__main__":
    _run()
