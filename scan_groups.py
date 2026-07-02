#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_groups.py — os 6 grupos canônicos de sets do scan MYP (skill /myp-scan).

Divide as 108 substrings validadas de MYP_EDITION_SUBSTR_TO_PTCG em 6 grupos
por recência (G1 = mais novo, inclui toda a era Mega Evolution até Chaos
Rising; G6 = WotC). Cada grupo tem <= 21 edições, o teto que mantém um run
dentro de ~2h30 (~7 min/edição na rota local sequencial) — runs maiores vinham
sendo mortos por timeout sem entregar resultado (CHANGELOG v5.5).

Uso:
    python scan_groups.py --list       # tabela dos 6 grupos
    python scan_groups.py --group 1    # string pronta pro input `editions`
                                       # do quick-scan.yml (eval set -- friendly)

As substrings são cópias VERBATIM das chaves do mapa do scanner — nunca edite
um nome aqui sem conferir o mapa; o test_scan_groups.py trava união exata.
"""

import argparse
import sys

if (sys.stdout.encoding or "").lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Minutos estimados por edição na rota local sequencial (CHANGELOG v5.5:
# ~7 min/edição com delay 1.5s; com POKEMONTCG_API_KEY cai pra ~6).
MINUTES_PER_EDITION = 7

# Teto de edições por grupo: 21 × 7 min ≈ 2h27 — garante que nem a rota local
# sequencial passe de ~2h30 (o limite pedido pelo operador em 2026-07-02).
MAX_EDITIONS_PER_GROUP = 21

GROUPS = {
    1: {
        "label": "Mega Evolution + SV recente",
        "editions": [
            "Mega Evolution",
            "Mega Evolution: Phantasmal Flames",
            "Ascended Heroes",
            "Perfect Order",
            "Chaos Rising",
            "Black Bolt",
            "White Flare",
            "Scarlet & Violet: Destined Rivals",
            "SV09: Journey Together",
            "Prismatic Evolutions",
            "Surging Sparks",
            "Stellar Crown",
            "Shrouded Fable",
            "Twilight Masquerade",
            "Temporal Forces",
            "Paldean Fates",
            "Paradox Rift",
            "151",
        ],
    },
    2: {
        "label": "SV inicial + Sword & Shield",
        "editions": [
            "Obsidian Flames",
            "Paldea Evolved",
            "Crown Zenith",
            "Silver Tempest",
            "Lost Origin",
            "Pokémon GO",
            "Astral Radiance",
            "Brilliant Stars",
            "Fusion Strike",
            "Celebrations: Classic Collection",
            "Evolving Skies",
            "Sword & Shield 6: Chilling Reign",
            "Sword & Shield 5: Battle Styles",
            "Shining Fates",
            "Sword & Shield 4: Vivid Voltage",
            "Sword & Shield 3.5: Champion's Path",
            "Sword & Shield 3: Darkness Ablaze",
            "Sword & Shield 2: Rebel Clash",
        ],
    },
    3: {
        "label": "Sun & Moon + XY final",
        "editions": [
            "Sun & Moon 12: Cosmic Eclipse",
            "Sun & Moon 11.5: Hidden Fates",
            "Sun & Moon 11: Unified Minds",
            "Sun & Moon 10: Unbroken Bonds",
            "Sun & Moon 9: Team Up",
            "Sun & Moon 8: Lost Thunder",
            "Sun & Moon 7.5: Dragon Majesty",
            "Sun & Moon 7: Celestial Storm",
            "Sun & Moon 6: Forbidden Light",
            "Sun & Moon 5: Ultra Prism",
            "Sun & Moon 4: Crimson Invasion",
            "Sun & Moon 3.5: Shining Legends",
            "Sun & Moon 3: Burning Shadows",
            "Sun & Moon 2: Guardians Rising",
            "XY 12: Evolutions",
            "XY 11: Steam Siege",
            "XY 10: Fates Collide",
            "XY 8: BREAKthrough",
        ],
    },
    4: {
        "label": "XY inicial + Black & White",
        "editions": [
            "XY 7: Ancient Origins",
            "XY 6: Roaring Skies",
            "XY 5: Primal Clash",
            "XY 4: Phantom Forces",
            "XY 3: Furious Fists",
            "XY 2: Flashfire",
            "XY: Double Crisis",
            "XY: Kalos Starter Set",
            "Black & White 10: Plasma Blast",
            "Black & White 9: Plasma Freeze",
            "Black & White 8: Plasma Storm",
            "Black & White 7: Boundaries Crossed",
            "Black & White 6: Dragons Exalted",
            "Black & White 5: Dark Explorers",
            "Black & White 4: Next Destinies",
            "Black & White 3: Noble Victories",
            "Black & White 2: Emerging Powers",
            "Black & White: Dragon Vault",
        ],
    },
    5: {
        "label": "HGSS + DP/Platinum + EX tardio",
        "editions": [
            "HeartGold & SoulSilver 4: Triumphant",
            "HeartGold & SoulSilver 3: Undaunted",
            "HeartGold & SoulSilver 2: Unleashed",
            "Platinum 4: Arceus",
            "Platinum 3: Supreme Victors",
            "Diamond & Pearl 7: Stormfront",
            "Legends Awakened",
            "Majestic Dawn",
            "Great Encounters",
            "Secret Wonders",
            "Mysterious Treasures",
            "EX 16: Power Keepers",
            "EX 15: Dragon Frontiers",
            "EX 14: Crystal Guardians",
            "EX 13: Holon Phantoms",
            "EX 12: Legend Maker",
            "EX 11: Delta Species",
            "EX 10: Unseen Forces",
        ],
    },
    6: {
        "label": "EX inicial + e-Card + WotC",
        "editions": [
            "EX 9: Emerald",
            "EX 8: Deoxys",
            "EX 6: Fire Red & Leaf Green",
            "EX 5: Hidden Legends",
            "EX 4: Team Magma vs Team Aqua",
            "EX 3: Dragon",
            "EX 2: Sandstorm",
            "EX 1: Ruby & Sapphire",
            "E-Card 3: Skyridge",
            "E-Card 2: Aquapolis",
            "E-Card 1: Expedition Base Set",
            "Legendary Collection",
            "Neo Destiny",
            "Neo Revelation",
            "Neo Discovery",
            "Neo Genesis",
            "Gym Challenge",
            "Gym Heroes",
        ],
    },
}


def editions_input(group: int) -> str:
    """String pronta pro input `editions` do workflow (multi-palavra entre
    aspas duplas — o formato que o `eval set --` do quick-scan.yml re-parseia
    de volta em N argumentos)."""
    parts = []
    for ed in GROUPS[group]["editions"]:
        parts.append('"%s"' % ed if " " in ed else ed)
    return " ".join(parts)


def _fmt_duration(n_editions: int) -> str:
    mins = n_editions * MINUTES_PER_EDITION
    return "%dh%02d" % divmod(mins, 60)


def list_groups() -> str:
    lines = [
        "Grupos canônicos do scan MYP (G1 = mais novo). Estimativa = rota "
        "LOCAL sequencial a ~%d min/edição; via workflow (6 chunks) é ~6× "
        "mais rápido." % MINUTES_PER_EDITION,
        "",
    ]
    for g, spec in sorted(GROUPS.items()):
        n = len(spec["editions"])
        lines.append(
            "G%d — %s: %d edições (~%s local)"
            % (g, spec["label"], n, _fmt_duration(n))
        )
        for ed in spec["editions"]:
            lines.append("    %s" % ed)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grupos canônicos de sets do scan MYP (skill /myp-scan)"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--group", type=int, choices=sorted(GROUPS),
                      help="Imprime o input `editions` pronto pro grupo N")
    mode.add_argument("--list", action="store_true",
                      help="Lista os 6 grupos com edições e estimativa")
    args = parser.parse_args()

    if args.list:
        print(list_groups())
    else:
        print(editions_input(args.group))
    return 0


if __name__ == "__main__":
    sys.exit(main())
