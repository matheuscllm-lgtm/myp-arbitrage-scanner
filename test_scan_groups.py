# -*- coding: utf-8 -*-
"""Trava a partição dos 6 grupos de scan (scan_groups.py) contra o mapa de
substrings do scanner. Se um set novo entrar em MYP_EDITION_SUBSTR_TO_PTCG e
não for colocado num grupo, o teste de união quebra — de propósito."""

import subprocess
import sys

from myp_arbitrage_scanner import MYP_EDITION_SUBSTR_TO_PTCG
from scan_groups import GROUPS, MAX_EDITIONS_PER_GROUP, editions_input


def _all_group_editions():
    out = []
    for spec in GROUPS.values():
        out.extend(spec["editions"])
    return out


def test_groups_cover_map_exactly():
    grouped = _all_group_editions()
    assert len(grouped) == len(set(grouped)), "edição duplicada entre grupos"
    assert set(grouped) == set(MYP_EDITION_SUBSTR_TO_PTCG), (
        "grupos != mapa: faltando %r / sobrando %r"
        % (sorted(set(MYP_EDITION_SUBSTR_TO_PTCG) - set(grouped)),
           sorted(set(grouped) - set(MYP_EDITION_SUBSTR_TO_PTCG)))
    )


def test_six_groups_within_duration_cap():
    assert sorted(GROUPS) == [1, 2, 3, 4, 5, 6]
    for g, spec in GROUPS.items():
        assert 0 < len(spec["editions"]) <= MAX_EDITIONS_PER_GROUP, (
            "G%d tem %d edições (cap %d ≈ 2h30 na rota local)"
            % (g, len(spec["editions"]), MAX_EDITIONS_PER_GROUP)
        )


def test_group1_is_the_newest_and_includes_chaos_rising():
    g1 = GROUPS[1]["editions"]
    for required in ("Chaos Rising", "Perfect Order", "Ascended Heroes",
                     "Mega Evolution"):
        assert required in g1, "%r fora do G1 (mais recente)" % (required,)


def test_editions_input_roundtrips_through_shell_eval():
    # Emula o caminho REAL do quick-scan.yml: o input chega via env
    # (EDITIONS_INPUT) e é re-parseado com `eval set --`. A string do grupo
    # tem que voltar exatamente às N edições originais — inclusive a que tem
    # apóstrofo (Champion's Path, G2), que quebraria interpolação inline.
    script = 'eval "set -- $EDITIONS_INPUT"; for a in "$@"; do printf "%s\\n" "$a"; done'
    for g, spec in GROUPS.items():
        out = subprocess.run(
            ["bash", "-c", script],
            env={"EDITIONS_INPUT": editions_input(g), "PATH": "/usr/bin:/bin"},
            capture_output=True, text=True, check=True,
        ).stdout
        parsed = out.splitlines()
        assert parsed == spec["editions"], "G%d não round-tripa no eval set --" % g


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS %s" % name)
    print("OK")
    sys.exit(0)
