"""
Offline regression test for v5.8 fix (Jirachi PR-SM_SM161 case).

Sem rede / sem CloudFlare. Exercita a lógica determinística com fixtures
sintéticas: TCG suspect filter + language-by-condition detection + XLSX
end-to-end surfacing.

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
    generate_xlsx,
    tcg_search_url,
    TCG_SUSPECT_RATIO_THRESHOLD,
)

# NOTE (v5.8.8, 2026-05-29): PT_CONDITION_MARKERS / EN_CONDITION_MARKERS foram
# REMOVIDOS do scanner no commit a4d2111 (a detecção de idioma migrou de
# "substring na linha" pra leitura da célula dedicada td.estoque-lista-
# qualidadenome). O test_v5_8_offline.py importava esses símbolos e estava
# QUEBRADO em ImportError desde então (pré-existente, não introduzido aqui).
# Os dois testes que dependiam deles (language markers disjoint + H1 language
# logic) foram removidos por testarem lógica que não existe mais.


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


def test_tcg_search_url():
    """v5.8.8: URL de busca TCGplayer remove o sufixo (NNN/MMM) e codifica."""
    u = tcg_search_url("Rayquaza VMAX (111/203)")
    assert u is not None
    assert "tcgplayer.com" in u, f"domínio errado: {u}"
    assert "Rayquaza" in u and "111" not in u, f"sufixo não removido: {u}"
    # apóstrofo e espaço codificados
    u2 = tcg_search_url("Team Aqua's Kyogre (003/95)")
    assert "Kyogre" in u2 and "%27" in u2, f"encoding falhou: {u2}"
    # promo sem (NNN/MMM) standard
    u3 = tcg_search_url("Pikachu (PR-SM SM229)")
    assert u3 is not None and "Pikachu" in u3 and "SM229" not in u3, f"promo: {u3}"
    # nome vazio → None (não gera link de busca vazio)
    assert tcg_search_url("") is None
    assert tcg_search_url(None) is None
    print(f"  tcg_search_url: 6 casos OK ✓")
    return True


def test_price_cell_hyperlinks():
    """v5.8.8: célula MYP EN NM linka pro produto MYP, TCG Player pra busca
    TCGplayer. Valor (número) preservado, hyperlink + fonte azul/sublinhada.
    Verifica nas 5 sheets de cards (não na Summary)."""
    clean = make_clean_deal()       # entra em Deals + All + Top50
    border = make_borderline_deal() # entra em Deals + All + Top50
    jirachi = make_jirachi()        # suspect → TCG Suspect sheet
    trunc = CardData(
        name="Psyduck (053/198)",
        edition="Scarlet & Violet",
        product_url="https://mypcards.com/pokemon/produto/99999/psyduck",
        myp_lowest_en_nm=300.0,
        tcg_player_price=400.0,
        myp_last_sale_brl=380.0,
        margin_pct=0.30,
        margin_brl=100.0,
        en_nm_sellers=3,
        en_truncation_risk=True,     # → Validate Manually
        last_updated="2026-05-29 12:00",
    )
    cards = [clean, border, jirachi, trunc]

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        out = f.name
    generate_xlsx(cards, out, threshold=0.25)
    wb = load_workbook(out)

    card_sheets = [
        "🔥 Deals", "All EN Cards", "🏆 Top 50 Margin",
        "🚨 Validate Manually", "🚨 TCG Suspect",
    ]
    checked = 0
    for sname in card_sheets:
        assert sname in wb.sheetnames, f"sheet ausente: {sname}"
        ws = wb[sname]
        hdr = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        myp_col = hdr.index("MYP EN NM (R$)") + 1
        tcg_col = hdr.index("TCG Player (R$)") + 1
        rows_seen = 0
        for r in range(2, ws.max_row + 1):
            myp_cell = ws.cell(row=r, column=myp_col)
            tcg_cell = ws.cell(row=r, column=tcg_col)
            if myp_cell.value is None and tcg_cell.value is None:
                continue
            rows_seen += 1
            # MYP price cell: número preservado + hyperlink mypcards
            if myp_cell.value is not None:
                assert isinstance(myp_cell.value, (int, float)), \
                    f"{sname} r{r}: valor MYP não numérico: {myp_cell.value!r}"
                assert myp_cell.hyperlink is not None, \
                    f"{sname} r{r}: MYP price sem hyperlink"
                assert "mypcards.com" in myp_cell.hyperlink.target, \
                    f"{sname} r{r}: hyperlink MYP errado: {myp_cell.hyperlink.target}"
                assert myp_cell.font.underline == "single", \
                    f"{sname} r{r}: MYP price sem underline"
            # TCG price cell: número preservado + hyperlink tcgplayer
            if tcg_cell.value is not None:
                assert isinstance(tcg_cell.value, (int, float)), \
                    f"{sname} r{r}: valor TCG não numérico: {tcg_cell.value!r}"
                assert tcg_cell.hyperlink is not None, \
                    f"{sname} r{r}: TCG price sem hyperlink"
                assert "tcgplayer.com" in tcg_cell.hyperlink.target, \
                    f"{sname} r{r}: hyperlink TCG errado: {tcg_cell.hyperlink.target}"
        assert rows_seen >= 1, f"{sname}: nenhuma row de card pra checar"
        checked += rows_seen

    # Card Name e URL NÃO devem ser quebrados: URL ainda string http, Card Name
    # ainda o (NNN/MMM) intacto.
    ws_all = wb["All EN Cards"]
    hdr = [c.value for c in next(ws_all.iter_rows(min_row=1, max_row=1))]
    name_col = hdr.index("Card Name") + 1
    url_col = hdr.index("URL") + 1
    # Localiza o Psyduck (053/198): tem o token (NNN/MMM) que NÃO pode quebrar.
    psyduck_name = None
    for r in range(2, ws_all.max_row + 1):
        nv = ws_all.cell(row=r, column=name_col).value
        uv = ws_all.cell(row=r, column=url_col).value
        # URL não pode ter sido quebrada em nenhuma row
        assert uv is None or str(uv).startswith("http"), f"URL quebrada r{r}: {uv!r}"
        if nv and "Psyduck" in str(nv):
            psyduck_name = nv
    assert psyduck_name == "Psyduck (053/198)", \
        f"Card Name (NNN/MMM) quebrado/alterado: {psyduck_name!r}"

    Path(out).unlink()
    print(f"  Hyperlinks de preço OK em {len(card_sheets)} sheets ({checked} células checadas) ✓")
    return True


def test_threshold_constant():
    """Threshold 10x é o que documentação especifica."""
    assert TCG_SUSPECT_RATIO_THRESHOLD == 10.0, f"Threshold mudou: {TCG_SUSPECT_RATIO_THRESHOLD}"
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
        ("Jirachi ratio math", test_jirachi_ratio_math),
        ("XLSX end-to-end", test_xlsx_end_to_end),
        ("tcg_search_url (v5.8.8)", test_tcg_search_url),
        ("price cell hyperlinks (v5.8.8)", test_price_cell_hyperlinks),
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
    print(f"✅ Todos os {len(tests)} testes passaram — fix v5.8 OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
