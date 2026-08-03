"""Trava a partição dos 6 grupos do skill `scan-myp-dbz` (espelho do
tests/test_scan_skill_profiles.py do card-trader-scanner).

Fonte de verdade dupla:
  - os comandos VERBATIM do `.claude/skills/scan-myp-dbz/SKILL.md`;
  - o snapshot REAL do catálogo DBZ do MYP (123 edições: 35 dbsfusion + 88
    dbsmasters), enumerado pela sonda `probe-myp-dragonball` no PR #95
    (runs 30781111250/30781617752, 2026-08-03).

Invariantes travados:
  1. todo termo de grupo casa ≥1 edição da SUA seção (termo morto = typo);
  2. a união dos grupos cobre TODAS as 123 edições (nada fica órfão);
  3. nenhuma edição é coberta por 2 grupos (re-scan duplicado proibido);
  4. cada grupo declara exatamente uma seção válida.

Se o MYP adicionar edição nova, atualize o snapshot AQUI e o grupo da era
correspondente no SKILL.md — juntos (o teste força a dupla atualização).

Run: python test_scan_dbz_skill_profiles.py  (ou via pytest)
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
    "scan-myp-dbz" / "SKILL.md"

# Snapshot do catálogo (títulos LIMPOS, como o get_section_editions entrega
# após o split_edition_title — sem código/data). Sonda 2026-08-03.
DBSFUSION_EDITIONS = [
    "Brightness of Hope", "Story Booster 01", "Cross Force",
    "Cross Force Release Event Cards", "Dual Evolution Release Event Cards",
    "Starter Deck EX: The Beat of Ki",
    "Starter Deck EX: The Phase of Evolution", "Saiyan's Pride",
    "Manga Booster 02", "Wish For Shenron", "Manga Booster 01",
    "Starter Deck 10: Giblet", "Starter Deck 9: Shallot", "Rivals Clash",
    "Starter Deck 8: Vegeta (Mini) Super Saiyan 3", "New Adventure",
    "Ultra Limit", "Raging Roar Alternate Art Reprints",
    "Ultra Limit Release Event Cards", "Starter Deck 7: Vegeta (Mini)",
    "Starter Deck 6: Son Goku (Mini)", "Raging Roar",
    "Starter Deck 5: Bardock", "Blazing Aura",
    "Blazing Aura Release Event Cards", "Awakened Pulse Pre-Release Cards",
    "Awakened Pulse", "Starter Deck 4: Frieza", "Starter Deck 3: Broly",
    "Starter Deck 2: Vegeta", "Starter Deck 1: Son Goku",
    "Tournament and Championship Promos",
    "Fusion World Promotion Cards and Packs", "Fusion World Energy Markers",
    "Dual Evolution",
]

DBSMASTERS_EDITIONS = [
    "Prismatic Clash", "Beyond Generations", "Perfect Combination",
    "Perfect Combination Pre-Release Cards",
    "Expansion Deck Box Set 23: Premium Anniversary Box 2023",
    "Critical Blow", "Critical Blow Pre-Release Cards", "Wild Resurgence",
    "Proud Warrior", "Ultimate Squad", "Realm of the Gods", "Mythic Booster",
    "Saiyan Showdown", "Cross Spirits", "Universe 18 Namekian Boost",
    "Universe 17 Saiyan Boost", "Supreme Rivalry", "Vicious Rejuvenation",
    "Universe 15 Battle Enhanced", "Universe 14 Battle Advanced",
    "Giant Force", "Vermilion Bloodline", "Divine Multiverse",
    "Instinct Surpassed", "Universal Onslaught", "Namekian Surge",
    "Saiyan Surge", "Promotion Cards", "Malicious Machinations",
    "Universe 6 Assailants", "Saiyan Legacy", "Assault of the Saiyans",
    "Special Anniversary Box", "Unity Of Saiyans", "Unity Of Destruction",
    "Rising Broly", "Destroyer Kings", "Clash Of Fates",
    "Shenron’S Advent",           # apóstrofo curvo REAL do site
    "Miraculous Revival", "World Martial Arts Tournament", "Ultimate Box",
    "Colossal Warfare", "The Tournament Of Power", "Cross Worlds",
    "Union Force", "Galactic Battle", "Mighty Heroes",
    "Dark Demon’S Villains",      # idem
    "The Awakening", "The Extreme Evolution", "The Dark Invasion",
    "The Guardian Of Namekians", "The Crimson Saiyan", "Resurrected Fusion",
    "Zenkai Sereis Power Absorbed",    # typo REAL do site — não corrigir
    "Ultimate Deck 2023", "5th Anniversary Set Premium Edition",
    "5th Anniversary Set", "Ultimate Deck 2022", "Z-Series Pack Wave 2",
    "ZENKAI Series Fighter's Ambition", "Ultimate Awakened Power",
    "Zenkai Series Dawn of The Z-Legends",
    "Zenkai Starter Deck Yellow Transformation",
    "Zenkai Starter Deck Green Fusion", "Zenkai Starter Deck Blue Future",
    "Zenkai Starter Deck Red Rage", "CollectorsSelection Vol.2",
    "CollectorsSelection Vol.1", "Theme Selection History of Vegeta",
    "Theme Selection History of Son Goku", "Darkness Reborn",
    "Pride of the Saiyans", "Battle Evolution Booster",
    "Special Anniversary Box 2020", "Universe 7 Unison",
    "Universe 11 Unison", "The Ultimate Life Form", "Spirit of Potara",
    "Clan Collusion", "Saiyan Wonder", "Rise of the Unison Warrior",
    "Fusion Hero", "Forsaken Warrior", "Android Duality", "Dragon Brawl",
    "Parasitic Overlord",
]

CATALOG = {"dbsfusion": DBSFUSION_EDITIONS, "dbsmasters": DBSMASTERS_EDITIONS}


def parse_skill_groups():
    """Extrai [(nº, seção, [termos])] dos blocos de código do SKILL.md."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    groups = []
    for m in re.finditer(
            r"### Grupo (\d+)[^\n]*\n```\n(.*?)\n```", text, re.DOTALL):
        num = int(m.group(1))
        cmd = " ".join(m.group(2).split())
        toks = shlex.split(cmd)
        assert toks[0] == "--sections", f"Grupo {num}: comando não começa com --sections"
        section = toks[1]
        assert toks[2] == "--editions", f"Grupo {num}: faltou --editions"
        terms = toks[3:]
        groups.append((num, section, terms))
    return groups


def matches(term: str, title: str) -> bool:
    """Mesma régua do filtro do scanner: substring case-insensitive."""
    return term.lower().strip() in title.lower()


def test_skill_tem_6_grupos_com_secoes_validas():
    groups = parse_skill_groups()
    assert [g[0] for g in groups] == [1, 2, 3, 4, 5, 6], \
        f"grupos encontrados: {[g[0] for g in groups]}"
    for num, section, terms in groups:
        assert section in CATALOG, f"Grupo {num}: seção inválida {section!r}"
        assert terms, f"Grupo {num}: sem termos"
        assert len(terms) == len({t.lower() for t in terms}), \
            f"Grupo {num}: termo duplicado"


def test_todo_termo_casa_alguma_edicao():
    for num, section, terms in parse_skill_groups():
        titles = CATALOG[section]
        for t in terms:
            hit = [ti for ti in titles if matches(t, ti)]
            assert hit, (f"Grupo {num}: termo morto {t!r} não casa nenhuma "
                         f"edição de {section} (typo? edição saiu do site?)")


def test_cobertura_total_sem_sobreposicao():
    groups = parse_skill_groups()
    coverage: dict[tuple, list[int]] = {}
    for num, section, terms in groups:
        for title in CATALOG[section]:
            if any(matches(t, title) for t in terms):
                coverage.setdefault((section, title), []).append(num)
    # 1) nada órfão
    orfas = [(s, t) for s in CATALOG for t in CATALOG[s]
             if (s, t) not in coverage]
    assert not orfas, f"Edições sem grupo: {orfas}"
    # 2) nenhuma edição em 2 grupos (re-scan duplicado)
    dups = {k: v for k, v in coverage.items() if len(v) > 1}
    assert not dups, f"Edições cobertas por 2+ grupos: {dups}"
    # 3) contagem total bate com o snapshot (35 + 88)
    assert len(coverage) == 123, len(coverage)


def test_contagens_declaradas_no_skill():
    """Os '; N ed.' dos títulos dos grupos batem com a cobertura real."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    declared = {int(n): int(c) for n, c in
                re.findall(r"### Grupo (\d+)[^\n]*?(\d+) ed\.\)", text)}
    groups = parse_skill_groups()
    for num, section, terms in groups:
        real = sum(1 for title in CATALOG[section]
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
