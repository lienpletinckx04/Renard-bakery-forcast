"""Tests voor de Belgische getalopmaak (bakkerij/opmaak.py).

Deze drie tests stonden tot 18 augustus 2026 in `tests/test_rapport_pdf.py`, bij
de WeasyPrint-bouwer van het CFO-rapport. Die bouwer is opgeheven — het rapport
is een weergave in het platform geworden, met `platform/lib/format.ts` als
opmaaklaag — maar de omzetting zelf is nog in gebruik in scripts die zelf een
tabel afdrukken, en dus blijft ze bewaakt.

Het kernrisico is onveranderd: dit moet een *lexicale* omzetting blijven. Zodra
hier iets gaat afronden of met floats rekenen, staat er op een tabel een ander
bedrag dan in het contract.
"""
from bakkerij import opmaak


def test_euro_nl_is_lexicaal_belgisch():
    assert opmaak.euro_nl("1234.56") == "€ 1.234,56"
    assert opmaak.euro_nl("-31590.12") == "€ −31.590,12"  # echte minus
    assert opmaak.euro_nl("7") == "€ 7"


def test_pct_en_aantal_nl():
    assert opmaak.pct_nl("12.3") == "12,3 %"
    assert opmaak.pct_nl("-4.2") == "−4,2 %"
    assert opmaak.aantal_nl("24960") == "24.960"


def test_de_cijfers_zelf_blijven_onaangeroerd():
    """Geen afronding, geen herberekening: elk cijfer uit de invoer komt terug."""
    for ruw in ("0.005", "999999.99", "1000000", "0"):
        uit = opmaak.euro_nl(ruw)
        assert "".join(c for c in uit if c.isdigit()) == ruw.replace(".", "")
