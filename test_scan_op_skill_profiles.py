"""Trava a partição dos 6 grupos do skill `scan-myp-op` (espelho do
test_scan_dbz_skill_profiles.py).

Fonte de verdade dupla:
  - os comandos VERBATIM do `.claude/skills/scan-myp-op/SKILL.md`;
  - o snapshot REAL do catálogo One Piece do MYP (65 edições da seção
    /onepiece), enumerado pela sonda `probe-myp-onepiece` no PR #98
    (run 31300834735, 2026-08-09).

Invariantes travados:
  1. todo termo de grupo casa ≥1 edição (termo morto = typo);
  2. a união dos grupos cobre TODAS as 65 edições (nada fica órfão);
  3. nenhuma edição é coberta por 2 grupos (re-scan duplicado proibido);
  4. as contagens "; N ed.)" declaradas nos títulos batem com a cobertura.

Se o MYP adicionar edição nova, atualize o snapshot AQUI e o grupo da era
correspondente no SKILL.md — juntos (o teste força a dupla atualização).

Run: python test_scan_op_skill_profiles.py  (ou via pytest)
"""
import re
import shlex
import sys
from pathlib import Path

if (sys.stdout.encoding or "").lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SKILL_PATH = Path(__file__).resolve().parent / ".claude" / "skills" / \
    "scan-myp-op" / "SKILL.md"

# Snapshot do catálogo (títulos LIMPOS, como o get_section_editions entrega
# após o split_edition_title — sem código/data). Sonda 2026-08-09.
ONEPIECE_EDITIONS = [
    "Set Sail Deck Set",
    "The World's Strongest Warriors",
    "Starter Deck 35: RED/BLACK Sabo",
    "Starter Deck 36: YELLOW Eustass”Captain”Kid",   # aspas curvas REAIS do site
    "Starter Deck 31: RED Monkey.D.Luffy",
    "Starter Deck 34: PURPLE Charlotte Katakuri",
    "Starter Deck 33: BLUE Kuzan",
    "Starter Deck 32: GREEN Roronoa Zoro",
    "Starter Deck EX: Luffy & Ace",
    "The Time of Battle",
    "Adventure on Kami's Island",
    "Adventure on Kami's Island Release Event Cards",
    "Extra Booster: One Piece Heroines Edition",
    "Starter Deck 29: Egghead",
    "The Azure Sea's Seven",
    "Carrying On His Will",
    "Learn Together Deck Set",
    "Premium Booster -The Best- Vol. 2",
    "Starter Deck 22: Ace & Newgate",
    "Legacy of the Master",
    "Starter Deck 28: GREEN/YELLOW Yamato",
    "Starter Deck 27: BLACK Marshall.D.Teach",
    "Starter Deck 26: PURPLE/BLACK Monkey.D.Luffy",
    "Starter Deck 25: BLUE Buggy",
    "Starter Deck 24: GREEN Jewelry Bonney",
    "Starter Deck 23: RED Shanks",
    "A Fist of Divine Speed",
    "Extra Booster: Anime 25th Collection",
    "Royal Blood",
    "Starter Deck EX: Gear 5",
    "Emperors in the New World",
    "Emperors in the New World: 2nd Anniversary Tournament Cards",
    "Revision Pack Cards",
    "Premium Booster -The Best-",
    "Starter Deck 20: YELLOW Charlotte Katakuri",
    "Starter Deck 19: BLACK Smoker",
    "Starter Deck 18: PURPLE Monkey.D.Luffy",
    "Starter Deck 17: BLUE Donquixote Doflamingo",
    "Starter Deck 16: GREEN Uta",
    "Starter Deck 15: RED Edward.Newgate",
    "Two Legends",
    "Starter Deck 14: 3D2Y",
    "500 Years In the Future",
    "Memorial Collection",
    "Ultra Deck: The Three Brothers",
    "Wings of the Captain",
    "Starter Deck 11: Uta",
    "AWAKENING OF THE NEW ERA",
    "Ultra Deck: The Three Captains",
    "Kingdoms of Intrigue",
    "Starter Deck 9: Yamato",
    "Starter Deck 8: Monkey D. Luffy",
    "Starter Deck 7: Big Mom Pirates",
    "Pillars of Strength",
    "STARTER DECK -Zoro and Sanji-",
    "Absolute Justice",
    "Paramount War",
    "One Piece Film Edition",
    "Animal Kingdom Pirates",
    "The Seven Warlords of the Sea",
    "Worst Generation",
    "Straw Hat Crew",
    "Romance Dawn",
    "Promotion Cards",
    "Gift Collection 2023",
]


def parse_skill_groups():
    """Extrai [(nº, [termos])] dos blocos de código do SKILL.md."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    groups = []
    for m in re.finditer(
            r"### Grupo (\d+)[^\n]*\n```\n(.*?)\n```", text, re.DOTALL):
        num = int(m.group(1))
        cmd = " ".join(m.group(2).split())
        toks = shlex.split(cmd)
        assert toks[0] == "--editions", f"Grupo {num}: comando não começa com --editions"
        terms = toks[1:]
        groups.append((num, terms))
    return groups


def matches(term: str, title: str) -> bool:
    """Mesma régua do filtro do scanner: substring case-insensitive."""
    return term.lower().strip() in title.lower()


def test_skill_tem_6_grupos():
    groups = parse_skill_groups()
    assert [g[0] for g in groups] == [1, 2, 3, 4, 5, 6], \
        f"grupos encontrados: {[g[0] for g in groups]}"
    for num, terms in groups:
        assert terms, f"Grupo {num}: sem termos"
        assert len(terms) == len({t.lower() for t in terms}), \
            f"Grupo {num}: termo duplicado"


def test_todo_termo_casa_alguma_edicao():
    for num, terms in parse_skill_groups():
        for t in terms:
            hit = [ti for ti in ONEPIECE_EDITIONS if matches(t, ti)]
            assert hit, (f"Grupo {num}: termo morto {t!r} não casa nenhuma "
                         f"edição (typo? edição saiu do site?)")


def test_cobertura_total_sem_sobreposicao():
    groups = parse_skill_groups()
    coverage: dict[str, list[int]] = {}
    for num, terms in groups:
        for title in ONEPIECE_EDITIONS:
            if any(matches(t, title) for t in terms):
                coverage.setdefault(title, []).append(num)
    # 1) nada órfão
    orfas = [t for t in ONEPIECE_EDITIONS if t not in coverage]
    assert not orfas, f"Edições sem grupo: {orfas}"
    # 2) nenhuma edição em 2 grupos (re-scan duplicado)
    dups = {k: v for k, v in coverage.items() if len(v) > 1}
    assert not dups, f"Edições cobertas por 2+ grupos: {dups}"
    # 3) contagem total bate com o snapshot
    assert len(coverage) == 65, len(coverage)


def test_contagens_declaradas_no_skill():
    """Os '; N ed.' dos títulos dos grupos batem com a cobertura real."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    declared = {int(n): int(c) for n, c in
                re.findall(r"### Grupo (\d+)[^\n]*?(\d+) ed\.\)", text)}
    groups = parse_skill_groups()
    for num, terms in groups:
        real = sum(1 for title in ONEPIECE_EDITIONS
                   if any(matches(t, title) for t in terms))
        assert declared.get(num) == real, \
            f"Grupo {num}: declarado {declared.get(num)} ed., real {real}"


def main() -> int:
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"  ✓ {name}")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {name}: {e}")
    print(f"{len(fns) - failed}/{len(fns)} passaram")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
