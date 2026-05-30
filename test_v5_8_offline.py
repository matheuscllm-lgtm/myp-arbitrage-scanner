"""
Offline regression tests do scanner (sem rede / sem CloudFlare).

Exercita a lógica determinística com fixtures sintéticas:
  - _parse_brl: parsing BR/US de preço (regressão bug v5.8.2)
  - _last_brl: extração do último R$ em texto multi-preço
  - oversized/jumbo regex
  - TCG suspect filter + XLSX end-to-end surfacing (caso Jirachi PR-SM_SM161)

Run: python test_v5_8_offline.py
Exit 0 = todos asserts passam, 1 = regressão.
"""
import sys
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
from openpyxl import load_workbook

from myp_arbitrage_scanner import (
    CardData,
    MYPScraper,
    generate_xlsx,
    TCG_SUSPECT_RATIO_THRESHOLD,
    OVERSIZED_TITLE_RE,
    OVERSIZED_FOIL_RE,
)


def make_jirachi():
    """Reproduz o caso real: TCG declarado 75x última venda."""
    return CardData(
        name="Jirachi PR-SM SM161",
        edition="Sol & Lua Promos",
        rarity="Holo Rara",
        product_url="https://mypcards.com/pokemon/sol-lua-promos/jirachi-sm161",
        myp_lowest_en_nm=99.99,
        tcg_player_price=1499.00,
        myp_last_sale_brl=19.99,
        tcg_suspect=True,
        margin_pct=14.0,
        margin_brl=1399.01,
        en_nm_sellers=1,
        last_updated="2026-05-16 19:30",
    )


def make_clean_deal():
    """Deal legítimo: ratio TCG/last_sale dentro do normal (1.1x)."""
    return CardData(
        name="Charizard ex Holo",
        edition="Surging Sparks",
        rarity="Special Illustration",
        product_url="https://mypcards.com/pokemon/surging-sparks/charizard-ex",
        myp_lowest_en_nm=80.00,
        tcg_player_price=200.00,
        myp_last_sale_brl=180.00,
        tcg_suspect=False,
        margin_pct=1.5,
        margin_brl=120.00,
        en_nm_sellers=4,
        last_updated="2026-05-16 19:30",
    )


def make_borderline_deal():
    """Ratio 9.5x — abaixo do threshold 10x, NÃO deve ser suspect."""
    return CardData(
        name="Mew V Alt Art",
        edition="Surging Sparks",
        rarity="Ultra Rara",
        product_url="https://mypcards.com/pokemon/x/mew-v",
        myp_lowest_en_nm=50.00,
        tcg_player_price=950.00,
        myp_last_sale_brl=100.00,
        tcg_suspect=False,
        margin_pct=18.0,
        margin_brl=900.00,
        en_nm_sellers=2,
        last_updated="2026-05-16 19:30",
    )


def find_card_in_sheet(ws, name_substring):
    """Procura linha onde col A contém substring."""
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] and name_substring.lower() in str(row[0]).lower():
            return row
    return None


def test_xlsx_end_to_end():
    """H2 + surfacing: Jirachi NÃO em 🔥 Deals, ESTÁ em 🚨 TCG Suspect."""
    jirachi = make_jirachi()
    clean = make_clean_deal()
    borderline = make_borderline_deal()
    cards = [jirachi, clean, borderline]

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        out = f.name
    generate_xlsx(cards, out, threshold=0.25)

    wb = load_workbook(out)
    print(f"  Sheets: {wb.sheetnames}")

    # Assert 1: 🚨 TCG Suspect existe
    assert "🚨 TCG Suspect" in wb.sheetnames, "Sheet '🚨 TCG Suspect' ausente"

    # Assert 2: Jirachi NÃO em Deals
    ws_deals = wb["🔥 Deals"]
    jirachi_row = find_card_in_sheet(ws_deals, "Jirachi")
    assert jirachi_row is None, f"BUG: Jirachi vazou para 🔥 Deals: {jirachi_row}"

    # Assert 3: Jirachi ESTÁ em Suspect
    ws_susp = wb["🚨 TCG Suspect"]
    jirachi_susp = find_card_in_sheet(ws_susp, "Jirachi")
    assert jirachi_susp is not None, "BUG: Jirachi não apareceu em 🚨 TCG Suspect"
    print(f"  Jirachi row em Suspect: name={jirachi_susp[0]!r}, last_sale={jirachi_susp[5]}")

    # Assert 4: clean deal está em Deals
    clean_row = find_card_in_sheet(ws_deals, "Charizard")
    # margin 1.5 (150%) >> threshold 0.25 → entra
    # (margin_pct é Decimal 1.5 = 150% no current code)
    # Borderline 18 (1800%) também entra
    # Actually let me check — threshold 0.25 = 25%. clean margin_pct=1.5 means 150%.
    assert clean_row is not None, "Clean deal sumiu de 🔥 Deals"
    print(f"  Clean deal em Deals: name={clean_row[0]!r}, margin={clean_row[6]}")

    # Assert 5: borderline (ratio 9.5x, abaixo do 10x) NÃO é suspect
    border_susp = find_card_in_sheet(ws_susp, "Mew")
    assert border_susp is None, f"FALSO POSITIVO: borderline 9.5x foi marcado como suspect: {border_susp}"
    border_deal = find_card_in_sheet(ws_deals, "Mew")
    assert border_deal is not None, "Borderline sumiu de Deals (não deveria — não é suspect)"

    # Assert 6: Summary tem TCG Suspects count
    ws_sum = wb["Summary"]
    summary_text = []
    for row in ws_sum.iter_rows(values_only=True):
        summary_text.append([str(c) if c else "" for c in row])
    flat = "\n".join("|".join(r) for r in summary_text)
    assert "TCG Suspects" in flat, "Summary não menciona TCG Suspects"
    assert "Deals Found (clean)" in flat, "Summary não menciona 'Deals Found (clean)'"
    print(f"  Summary contém TCG Suspects ✓")

    # Cleanup
    Path(out).unlink()
    return True


def test_threshold_constant():
    """Threshold 10x é o que documentação especifica."""
    assert TCG_SUSPECT_RATIO_THRESHOLD == 10.0, f"Threshold mudou: {TCG_SUSPECT_RATIO_THRESHOLD}"
    return True


def test_parse_brl_formats():
    """_parse_brl: BR canonical, US-decimal leak, milhares e edge cases.

    Regressão do bug v5.8.2 ('30.00' lido como 3000.0). Esta é a função mais
    propensa a erro do parser e antes tinha ZERO cobertura direta.
    """
    f = MYPScraper._parse_brl
    cases = [
        ("R$ 1.900,00", 1900.0),      # BR canonical (ponto-milhar, vírgula-decimal)
        ("R$ 30,00", 30.0),           # BR só vírgula
        ("R$ 30.00", 30.0),           # US-decimal leak (bug v5.8.2)
        ("R$ 1,500.00", 1500.0),      # US milhares + decimal
        ("R$ 30.000", 30000.0),       # BR milhares (sufixo 3 dígitos)
        ("R$ 1.500.000", 1500000.0),  # BR milhares (multi-ponto)
        ("1234.56", 1234.56),         # US decimal sem prefixo R$
        ("R$ 0,00", None),            # zero → None (guard val > 0)
        ("", None),
        ("   ", None),
        (None, None),                 # guard v5.8.4 (não-str)
        ("sem preço", None),
    ]
    for text, expected in cases:
        got = f(text)
        assert got == expected, f"_parse_brl({text!r}) = {got}, esperado {expected}"
    print(f"  _parse_brl: {len(cases)} casos OK ✓")
    return True


def test_last_brl():
    """_last_brl extrai o ÚLTIMO R$ (caso multi-preço '.estat-tcg')."""
    f = MYPScraper._last_brl
    assert f("Last R$ 26,00 | Avg R$ 30,00") == 30.0, "deve pegar o último valor"
    assert f("R$ 99,90") == 99.9
    assert f("sem preço aqui") is None
    assert f("") is None
    assert f(None) is None
    print(f"  _last_brl: extração do último valor OK ✓")
    return True


def test_oversized_regex():
    """Filtros Jumbo/oversized: title (2ª camada) + foil (1ª camada)."""
    assert OVERSIZED_TITLE_RE.search("Pikachu Jumbo (SWSH039)")
    assert OVERSIZED_TITLE_RE.search("Charizard Oversized Promo")
    assert OVERSIZED_TITLE_RE.search("Mewtwo Box Topper")
    assert not OVERSIZED_TITLE_RE.search("Charizard ex 234/091"), "standard não deve casar"
    assert OVERSIZED_FOIL_RE.search("Jumbo")
    assert not OVERSIZED_FOIL_RE.search("Holo")
    print(f"  oversized/jumbo regex OK ✓")
    return True


def test_jirachi_ratio_math():
    """Sanity: ratio 1499/19.99 ≈ 75 deve disparar threshold 10."""
    ratio = 1499.00 / 19.99
    assert ratio > TCG_SUSPECT_RATIO_THRESHOLD, f"Caso Jirachi não dispara: {ratio:.1f}x"
    print(f"  Jirachi ratio = {ratio:.1f}x ✓")
    return True


def main():
    tests = [
        ("threshold constant", test_threshold_constant),
        ("parse_brl BR/US formats", test_parse_brl_formats),
        ("_last_brl extraction", test_last_brl),
        ("oversized/jumbo regex", test_oversized_regex),
        ("Jirachi ratio math", test_jirachi_ratio_math),
        ("XLSX end-to-end", test_xlsx_end_to_end),
    ]
    failed = 0
    for name, fn in tests:
        print(f"\n[TEST] {name}")
        try:
            fn()
            print(f"  ✓ PASS")
        except AssertionError as e:
            print(f"  ✗ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'═' * 50}")
    if failed:
        print(f"❌ {failed}/{len(tests)} testes falharam")
        sys.exit(1)
    print(f"✅ Todos os {len(tests)} testes passaram — scanner OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
