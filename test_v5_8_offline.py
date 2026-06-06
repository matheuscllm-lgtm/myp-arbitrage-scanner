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
    MYPScraper,
    generate_xlsx,
    tcg_search_url,
    tcg_direct_url,
    myp_edition_to_ptcg_setcode,
    TCG_SUSPECT_RATIO_THRESHOLD,
    OVERSIZED_TITLE_RE,
    OVERSIZED_FOIL_RE,
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
        single_en_seller_risk=True,  # MYP-LOW-a 2026-05-30: coerência com scanner real (en_nm_sellers=1 < min default 2)
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
    Verifica nas 5 sheets de cards (não na Summary).

    v5.8.9 (2026-05-29): TCG link agora pode ser DIRETO (pokemontcg.io
    redirect) quando MYP edition mapeada + collector# in-range. Quando não,
    cai no fallback de busca (tcgplayer.com/search). Asserção genérica
    "tcgplayer.com in target" cobre ambos (search) E (product redirect
    final) — domínio pokemontcg.io é checado no test_tcg_direct_url.
    """
    clean = make_clean_deal()       # entra em Deals + All + Top50
    border = make_borderline_deal() # entra em Deals + All + Top50
    jirachi = make_jirachi()        # suspect → TCG Suspect sheet
    trunc = CardData(
        name="Psyduck (053/198)",
        edition="Scarlet & Violet",   # NÃO mapeado → fallback search
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
    # v5.8.9: card cuja edition É mapeada → hyperlink DIRETO pokemontcg.io.
    # Tef = Temporal Forces → sv5. Salamence ex (187/159) é oversized →
    # fallback DEVE acontecer (oversized_collector_risk=True).
    direct = CardData(
        name="Iron Hands ex (070/162)",
        edition="Temporal Forces",
        product_url="https://mypcards.com/pokemon/produto/12345/iron-hands-ex",
        myp_lowest_en_nm=120.0,
        tcg_player_price=240.0,
        myp_last_sale_brl=220.0,
        margin_pct=1.00,
        margin_brl=120.0,
        en_nm_sellers=5,
        last_updated="2026-05-29 12:00",
    )
    cards = [clean, border, jirachi, trunc, direct]

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
            # TCG price cell: número preservado + hyperlink TCG.
            # v5.8.9: aceita ambos os esquemas — direct (pokemontcg.io
            # redirect → tcgplayer.com/product/<id>) ou fallback search
            # (tcgplayer.com/search). Assertions específicas por caso
            # estão no bloco abaixo.
            if tcg_cell.value is not None:
                assert isinstance(tcg_cell.value, (int, float)), \
                    f"{sname} r{r}: valor TCG não numérico: {tcg_cell.value!r}"
                assert tcg_cell.hyperlink is not None, \
                    f"{sname} r{r}: TCG price sem hyperlink"
                target = tcg_cell.hyperlink.target
                ok = ("tcgplayer.com" in target
                      or "prices.pokemontcg.io/tcgplayer/" in target)
                assert ok, f"{sname} r{r}: hyperlink TCG errado: {target}"
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

    # v5.8.9: Iron Hands ex (Temporal Forces, 070/162, in-range) → DIRECT link
    # `prices.pokemontcg.io/tcgplayer/sv5-70`. Psyduck (Scarlet & Violet — não
    # mapeado) → fallback `tcgplayer.com/search`.
    direct_link = None
    psyduck_link = None
    for r in range(2, ws_all.max_row + 1):
        nv = ws_all.cell(row=r, column=name_col).value
        tcg_cell = ws_all.cell(row=r, column=hdr.index("TCG Player (R$)") + 1)
        if not nv or not tcg_cell.hyperlink:
            continue
        if "Iron Hands" in str(nv):
            direct_link = tcg_cell.hyperlink.target
        elif "Psyduck" in str(nv):
            psyduck_link = tcg_cell.hyperlink.target
    assert direct_link is not None, "Iron Hands sumiu de All EN Cards"
    assert direct_link == "https://prices.pokemontcg.io/tcgplayer/sv5-70", \
        f"Iron Hands não pegou direct link: {direct_link!r}"
    assert psyduck_link is not None, "Psyduck sumiu de All EN Cards"
    assert "tcgplayer.com/search" in psyduck_link, \
        f"Psyduck (Scarlet & Violet, unmapped) não caiu no fallback: {psyduck_link!r}"

    Path(out).unlink()
    print(f"  Hyperlinks de preço OK em {len(card_sheets)} sheets ({checked} células checadas) ✓")
    print(f"  Direct link (sv5-70) e fallback (search) confirmados ✓")
    return True


def test_myp_edition_to_setcode():
    """v5.8.9: mapeamento MYP edition → pokemontcg.io setcode.

    Cobre forma bilingual concat (MYP cola PT+EN) — substrings EN do mapa
    casam mesmo dentro da concat. Cobre longest-substring win (evita "Mega
    Evolution" overriding "Ascended Heroes").
    """
    # Direct match
    assert myp_edition_to_ptcg_setcode("Temporal Forces") == "sv5"
    assert myp_edition_to_ptcg_setcode("Stellar Crown") == "sv7"
    # Bilingual concat (MYP common form)
    assert myp_edition_to_ptcg_setcode(
        "Espada e Escudo 7: Céus em EvoluçãoSword & Shield 7: Evolving Skies"
    ) == "swsh7"
    assert myp_edition_to_ptcg_setcode(
        "Escarlate e Violeta: Amigos de JornadaSV09: Journey Together"
    ) == "sv9"
    # Longest-substring win: "Ascended Heroes" (mapped to me2pt5) beats
    # "Mega Evolution" (mapped to me1) when both substrings present.
    assert myp_edition_to_ptcg_setcode("ME: Ascended Heroes") == "me2pt5"
    # Case-insensitive
    assert myp_edition_to_ptcg_setcode("STELLAR CROWN") == "sv7"
    # Unmapped (vintage / promo / SV base / Black Bolt etc) → None
    assert myp_edition_to_ptcg_setcode("Diamond & Pearl") is None
    assert myp_edition_to_ptcg_setcode("Scarlet & Violet") is None
    assert myp_edition_to_ptcg_setcode("Sun & Moon Promos") is None
    assert myp_edition_to_ptcg_setcode("Black & White 9: Plasma Freeze") is None
    # Edge cases
    assert myp_edition_to_ptcg_setcode("") is None
    assert myp_edition_to_ptcg_setcode(None) is None
    print(f"  Mapeamento edition→setcode: 11 casos OK ✓")
    return True


def test_tcg_direct_url():
    """v5.8.9: monta URL DIRETA via redirect pokemontcg.io.

    Forma: prices.pokemontcg.io/tcgplayer/{setcode}-{num}. Strip leading
    zeros (verificado contra Link TCG do CT handoff: base6-13 não base6-013).
    None em todos os casos onde caller deve cair no fallback.
    """
    # In-range, edition mapeada → direct
    u = tcg_direct_url("Iron Hands ex (070/162)", "Temporal Forces")
    assert u == "https://prices.pokemontcg.io/tcgplayer/sv5-70", f"got {u!r}"
    # Leading zeros stripped (base6-13 style)
    u = tcg_direct_url("Some Card (013/110)", "Evolving Skies")
    assert u == "https://prices.pokemontcg.io/tcgplayer/swsh7-13", f"got {u!r}"
    # Bilingual concat edition
    u = tcg_direct_url(
        "Regidrago V (184/195)",
        "Espada e Escudo 12: Tempestade PrateadaSword & Shield 12: Silver Tempest",
    )
    assert u == "https://prices.pokemontcg.io/tcgplayer/swsh12-184", f"got {u!r}"
    # Oversized (numerator > set_size) → None, caller fallback
    # (Mega Feraligatr ex 274/217 — confirmado 404 em pokemontcg.io 2026-05-29)
    u = tcg_direct_url("Mega Feraligatr ex (274/217)", "ME: Ascended Heroes",
                       oversized_collector_risk=True)
    assert u is None, f"oversized deve cair no fallback: {u!r}"
    # Edition não mapeada → None
    u = tcg_direct_url("Charizard (004/102)", "Base Set")
    assert u is None
    u = tcg_direct_url("Random (053/198)", "Scarlet & Violet")
    assert u is None  # SV base NÃO está no mapa
    # Sem (NNN/MMM) parseável → None (promo PR-SM_SM161 style)
    u = tcg_direct_url("Jirachi PR-SM SM161", "Sol & Lua Promos")
    assert u is None
    # Edge: nome vazio
    u = tcg_direct_url("", "Temporal Forces")
    assert u is None
    print(f"  tcg_direct_url: 8 casos OK ✓")
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


# ── v5.9 (2026-06-03): marketplace pagination fix (truncation root cause) ──
def _seller_row(lang_title, qual, price_brl, foil="Normal"):
    """Uma <tr> de seller no formato MYP (flag-icon + células dedicadas)."""
    return (
        f'<tr>'
        f'<td><span class="flag-icon" title="{lang_title}"></span></td>'
        f'<td class="estoque-lista-qualidadenome">{qual}</td>'
        f'<td class="estoque-lista-nomeenfoil">{foil}</td>'
        f'<td>R$ {price_brl}</td>'
        f'</tr>'
    )


def _marketplace_container(rows_html, pagination_html=""):
    """Container #lista-anuncio-demais-vendedores (tabela marketplace + paginação)."""
    return (
        f'<div id="lista-anuncio-demais-vendedores">'
        f'<table class="table-striped table-bordered"><tbody>{rows_html}</tbody></table>'
        f'{pagination_html}'
        f'</div>'
    )


def _make_psyduck_page1():
    """Página 1: lojistas tem EN-NM mais caro (R$498); marketplace cheia de
    PT/JP baratos (0 EN visível) com paginação até a página 3 — réplica fiel
    do caso Psyduck 226/217 documentado no HANDOFF-TRUNCATION-2026-06-03 §2."""
    # Tabela lojistas: 2 EN-NM (498, 520) → lowest EN page-1 = 498 (inflado).
    lojistas = (
        '<table class="table-striped table-bordered"><tbody>'
        + _seller_row("Inglês", "NM - Quase nova", "498,00")
        + _seller_row("Inglês", "NM - Quase nova", "520,00")
        + '</tbody></table>'
    )
    # Marketplace page 1: 16 rows PT/JP NM, todas R$180–245 (< 498), 0 EN.
    mkt_rows = ""
    for i in range(16):
        price = 180 + i * 4  # 180..240
        lang = "Português" if i % 2 == 0 else "Japonês"
        mkt_rows += _seller_row(lang, "NM - Quase nova", f"{price},00")
    pagination = (
        '<ul class="pagination">'
        '<a href="?estoque-outros-page=2">2</a>'
        '<a href="?estoque-outros-page=3">3</a>'
        '</ul>'
    )
    marketplace = _marketplace_container(mkt_rows, pagination)
    return (
        '<html><body>'
        '<h1>Psyduck (053/198)</h1>'
        '<span class="estat-tcg">TCG Player: R$ 557,40</span>'
        f'{lojistas}{marketplace}'
        '</body></html>'
    )


def _make_psyduck_page2():
    """Página 2 marketplace: 3 EN-NM, a mais barata R$398 (o TRUE lowest)."""
    rows = (
        _seller_row("Inglês", "NM - Quase nova", "398,00")
        + _seller_row("Inglês", "NM - Quase nova", "410,00")
        + _seller_row("Português", "NM - Quase nova", "405,00")
    )
    return f'<html><body>{_marketplace_container(rows)}</body></html>'


def _make_psyduck_page3():
    """Página 3 marketplace: EN-NM mais caros (450, 650) — não muda o min."""
    rows = (
        _seller_row("Inglês", "NM - Quase nova", "450,00")
        + _seller_row("Inglês", "NM - Quase nova", "650,00")
    )
    return f'<html><body>{_marketplace_container(rows)}</body></html>'


def test_marketplace_pagination():
    """v5.9: scrape_product segue ?estoque-outros-page=N e acha o EN-NM oculto.

    Caso Psyduck: page 1 reportaria R$498,70 (tabela lojistas) porque a
    marketplace está cheia de PT/JP e os EN-NM caem na página 2. Com o fix,
    lowest EN-NM = R$398 (página 2), margem vs TCG R$557,40 = +40%, e
    truncation_risk é RESOLVIDO (False) porque a paginação foi seguida com
    sucesso. Sem rede: monkeypatch de _get serve fixtures por URL.
    """
    from myp_arbitrage_scanner import MYPScraper

    pages = {
        "https://mypcards.com/pokemon/produto/310463/psyduck": _make_psyduck_page1(),
        "https://mypcards.com/pokemon/produto/310463/psyduck?estoque-outros-page=2": _make_psyduck_page2(),
        "https://mypcards.com/pokemon/produto/310463/psyduck?estoque-outros-page=3": _make_psyduck_page3(),
    }
    fetched = []

    sc = MYPScraper(delay=0.0)

    def fake_get(url, save_debug=False):
        fetched.append(url)
        html = pages.get(url)
        return BeautifulSoup(html, "lxml") if html is not None else None

    sc._get = fake_get
    base = "https://mypcards.com/pokemon/produto/310463/psyduck"
    card = sc.scrape_product(base, "Scarlet & Violet")

    assert card is not None, "BUG: Psyduck retornou None (não deveria ser skipado)"
    # O CORAÇÃO DO FIX: lowest EN-NM = 398, não 498.
    assert card.myp_lowest_en_nm == 398.0, \
        f"BUG truncation: lowest EN-NM={card.myp_lowest_en_nm} (esperado 398.0 da pág 2)"
    # Margem vira deal real ≥25% (+40%).
    assert abs(card.margin_pct - 0.4005) < 0.01, \
        f"margem={card.margin_pct} (esperado ~0.40 / +40%)"
    # Paginação seguida com sucesso → risco resolvido.
    assert card.en_truncation_risk is False, \
        "truncation_risk deveria ser resolvido (paginação seguiu sem falha)"
    # Páginas 2 e 3 foram realmente buscadas.
    assert sc._stats["seller_pages_followed"] == 2, \
        f"esperado 2 páginas seguidas, got {sc._stats['seller_pages_followed']}"
    assert sc._stats["seller_page_fetch_failures"] == 0
    # EN sellers = lojistas(2) + pág2(2 EN) + pág3(2 EN) = 6.
    assert card.en_nm_sellers == 6, f"en_nm_sellers={card.en_nm_sellers} (esperado 6)"
    print(f"  Psyduck lowest EN-NM = R${card.myp_lowest_en_nm} "
          f"(margem +{card.margin_pct*100:.0f}%), {sc._stats['seller_pages_followed']} págs seguidas ✓")
    return True


def test_pagination_gate_skips_untruncated():
    """v5.9: produto SEM sinal de truncation NÃO pagina (controle de custo).

    Página 1 com EN-NM visível e barato → gate não dispara → nenhum fetch de
    ?estoque-outros-page mesmo que a paginação exista no HTML."""
    from myp_arbitrage_scanner import MYPScraper

    # Marketplace com EN-NM barato visível na página 1 (R$120) + paginação.
    mkt_rows = (
        _seller_row("Inglês", "NM - Quase nova", "120,00")
        + _seller_row("Português", "NM - Quase nova", "130,00")
    )
    pagination = '<ul class="pagination"><a href="?estoque-outros-page=2">2</a></ul>'
    html = (
        '<html><body><h1>Cheap Card (010/100)</h1>'
        '<span class="estat-tcg">TCG Player: R$ 300,00</span>'
        + _marketplace_container(mkt_rows, pagination)
        + '</body></html>'
    )
    fetched = []
    sc = MYPScraper(delay=0.0)

    def fake_get(url, save_debug=False):
        fetched.append(url)
        return BeautifulSoup(html, "lxml")

    sc._get = fake_get
    card = sc.scrape_product("https://mypcards.com/pokemon/produto/1/cheap", "x")
    assert card is not None
    assert card.myp_lowest_en_nm == 120.0
    # NENHUMA página extra buscada — só a página 1.
    assert sc._stats["seller_pages_followed"] == 0, \
        f"gate falhou: paginou produto não-truncado ({sc._stats['seller_pages_followed']} págs)"
    assert all("estoque-outros-page" not in u for u in fetched), \
        f"buscou página extra indevidamente: {fetched}"
    print(f"  Produto não-truncado: 0 páginas extras (truncation gate OK) ✓")
    return True


def test_pagination_cost_gate_low_tcg():
    """v5.9.1: produto TRUNCADO mas com TCG < min_price NÃO pagina (cost gate).

    Mesmo padrão de truncation do Psyduck (marketplace pág 1 cheia de PT/JP
    baratos, 0 EN, paginação disponível) MAS com TCG R$50 < min_price R$80.
    Como o card nunca pode virar deal, paginar pra resolver truncation é puro
    desperdício — o cost gate pula a paginação e conta pagination_skipped_low_tcg.
    Contraste com test_marketplace_pagination (TCG R$557 ⟹ ainda pagina)."""
    from myp_arbitrage_scanner import MYPScraper

    # Lojistas: 2 EN-NM (90, 95) ⟹ lowest EN visível pág-1 = 90 (≥ min_price).
    lojistas = (
        '<table class="table-striped table-bordered"><tbody>'
        + _seller_row("Inglês", "NM - Quase nova", "90,00")
        + _seller_row("Inglês", "NM - Quase nova", "95,00")
        + '</tbody></table>'
    )
    # Marketplace pág 1: 16 PT/JP baratos (40..70 < 90, 0 EN) ⟹ truncation gate
    # DISPARA. O cost gate é que deve barrar a paginação (TCG baixo).
    mkt_rows = ""
    for i in range(16):
        price = 40 + i * 2
        lang = "Português" if i % 2 == 0 else "Japonês"
        mkt_rows += _seller_row(lang, "NM - Quase nova", f"{price},00")
    pagination = '<ul class="pagination"><a href="?estoque-outros-page=2">2</a></ul>'
    html = (
        '<html><body><h1>Cheap Truncated (010/100)</h1>'
        '<span class="estat-tcg">TCG Player: R$ 50,00</span>'
        + lojistas
        + _marketplace_container(mkt_rows, pagination)
        + '</body></html>'
    )
    fetched = []
    # min_price pinado em 80 (não depende do default global, que virou R$50
    # no #20): card com TCG R$50 fica abaixo do piso ⟹ cost gate deve pular.
    sc = MYPScraper(delay=0.0, min_price=80.0)

    def fake_get(url, save_debug=False):
        fetched.append(url)
        return BeautifulSoup(html, "lxml")

    sc._get = fake_get
    card = sc.scrape_product("https://mypcards.com/pokemon/produto/2/cheaptrunc", "x")

    assert card is not None, "card não deveria ser None (EN visível R$90 ≥ min_price)"
    # O cost gate pulou a paginação APESAR do sinal de truncation.
    assert sc._stats["seller_pages_followed"] == 0, \
        f"cost gate falhou: paginou card TCG<min ({sc._stats['seller_pages_followed']} págs)"
    assert sc._stats["pagination_skipped_low_tcg"] == 1, \
        f"pagination_skipped_low_tcg={sc._stats['pagination_skipped_low_tcg']} (esperado 1)"
    assert all("estoque-outros-page" not in u for u in fetched), \
        f"buscou página extra indevidamente: {fetched}"
    print(f"  Truncado + TCG R$50 < R$80: 0 págs, gate contou 1 (cost gate v5.9.1) ✓")
    return True


def test_parse_brl_formats():
    """v5.8.10: _parse_brl — BR canonical, US-decimal leak, milhares, edge cases.

    Regressão do bug v5.8.2 ('30.00' lido como 3000.0). É a função mais
    propensa a erro do parser e não tinha cobertura direta.
    """
    f = MYPScraper._parse_brl
    cases = [
        ("R$ 1.900,00", 1900.0),      # BR canonical
        ("R$ 30,00", 30.0),           # BR só vírgula
        ("R$ 30.00", 30.0),           # US-decimal leak (bug v5.8.2)
        ("R$ 1,500.00", 1500.0),      # US milhares + decimal
        ("R$ 30.000", 30000.0),       # BR milhares (sufixo 3 dígitos)
        ("R$ 1.500.000", 1500000.0),  # BR milhares (multi-ponto)
        ("1234.56", 1234.56),         # US decimal sem prefixo
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
    """v5.8.10: _last_brl extrai o ÚLTIMO R$ (caso multi-preço '.estat-tcg')."""
    f = MYPScraper._last_brl
    assert f("Last R$ 26,00 | Avg R$ 30,00") == 30.0, "deve pegar o último valor"
    assert f("R$ 99,90") == 99.9
    assert f("sem preço aqui") is None
    assert f("") is None
    assert f(None) is None
    print(f"  _last_brl: extração do último valor OK ✓")
    return True


def test_oversized_regex():
    """v5.8.10: filtros Jumbo/oversized — title (2ª camada) + foil (1ª camada)."""
    assert OVERSIZED_TITLE_RE.search("Pikachu Jumbo (SWSH039)")
    assert OVERSIZED_TITLE_RE.search("Charizard Oversized Promo")
    assert OVERSIZED_TITLE_RE.search("Mewtwo Box Topper")
    assert not OVERSIZED_TITLE_RE.search("Charizard ex 234/091"), "standard não deve casar"
    assert OVERSIZED_FOIL_RE.search("Jumbo")
    assert not OVERSIZED_FOIL_RE.search("Holo")
    print(f"  oversized/jumbo regex OK ✓")
    return True


def main():
    tests = [
        ("threshold constant", test_threshold_constant),
        ("Jirachi ratio math", test_jirachi_ratio_math),
        ("parse_brl BR/US formats (v5.8.10)", test_parse_brl_formats),
        ("_last_brl extraction (v5.8.10)", test_last_brl),
        ("oversized/jumbo regex (v5.8.10)", test_oversized_regex),
        ("XLSX end-to-end", test_xlsx_end_to_end),
        ("tcg_search_url (v5.8.8)", test_tcg_search_url),
        ("price cell hyperlinks (v5.8.8/v5.8.9)", test_price_cell_hyperlinks),
        ("myp_edition_to_ptcg_setcode (v5.8.9)", test_myp_edition_to_setcode),
        ("tcg_direct_url (v5.8.9)", test_tcg_direct_url),
        ("marketplace pagination (v5.9)", test_marketplace_pagination),
        ("pagination truncation gate (v5.9)", test_pagination_gate_skips_untruncated),
        ("pagination cost gate TCG<min (v5.9.1)", test_pagination_cost_gate_low_tcg),
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
    print(f"✅ Todos os {len(tests)} testes passaram — fixes v5.8 + v5.9 OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
