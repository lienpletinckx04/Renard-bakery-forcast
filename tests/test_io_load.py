"""Tests op het schema-agnostische inladen. Pure functies, geen bestanden.

Alle data in dit bestand is verzonnen. Er staat geen enkele echte productnaam
en geen enkel echt bedrag in -- ook een test is een plek waar klantdata niet
hoort.
"""
import math

import pandas as pd
import pytest

from bakkerij.io_load import parse_getallen, raad_kanaal, raad_kolommen

# --- parse_getallen -----------------------------------------------------------
#
# De gevaarlijkste invoer is niet de onleesbare maar de dubbelzinnige: "1.234"
# is in een Europese export twaalfhonderdvierendertig, en wie het als 1,234
# leest, is stilletjes een factor duizend kwijt. Elk geval hieronder legt één
# kant van die dubbelzinnigheid vast.

GETALGEVALLEN = [
    # (invoer, verwacht) -- verwacht None betekent NaN.
    ("1.234", 1234.0),          # punt + drie cijfers zonder komma: duizendtal
    ("1.234,50", 1234.50),      # komma aanwezig: komma decimaal, punt duizend
    ("1234.50", 1234.50),       # vier cijfers voor de punt: punt is decimaal
    ("-1.234,50", -1234.50),    # minteken verandert de leesregel niet
    ("€ 12,34", 12.34),    # euroteken en spatie worden weggeschoond
    ("", None),                 # leeg is onbekend, geen nul
    ("1.234.567", 1234567.0),   # herhaalde groepen van drie: duizendtallen
    ("12.34", 12.34),           # twee cijfers na de punt: decimaal
    ("0.5", 0.5),               # geen groep van drie: decimaal
    ("1234", 1234.0),           # kaal geheel getal
    ("-1.234", -1234.0),        # negatief duizendtal zonder komma
    ("12,5", 12.5),             # komma zonder punten
    ("onzin", None),            # onparseerbaar wordt NaN, geen fout
]


@pytest.mark.parametrize("invoer, verwacht", GETALGEVALLEN)
def test_parse_getallen(invoer, verwacht):
    uit = parse_getallen(pd.Series([invoer]))
    waarde = uit.iloc[0]
    if verwacht is None:
        assert math.isnan(waarde)
    else:
        assert waarde == pytest.approx(verwacht)


def test_parse_getallen_mengt_notaties_binnen_een_kolom():
    """Een export mengt soms notaties (handmatige correcties in een xlsx).

    De leesregel geldt per waarde, niet per kolom: een komma in rij drie mag
    de lezing van rij één niet veranderen.
    """
    uit = parse_getallen(pd.Series(["1.234", "1234.50", "1.234,50"]))
    assert list(uit) == pytest.approx([1234.0, 1234.5, 1234.5])


# --- raad_kanaal --------------------------------------------------------------


@pytest.mark.parametrize("invoer, verwacht", [
    ("Winkel Centrum", "winkel"),
    ("POS kassa 2", "winkel"),
    ("Deliveroo", "deliveroo"),
    ("Too Good To Go", "tgtg"),
    ("TGTG ochtend", "tgtg"),
    ("Marktkraam", "overig"),
])
def test_raad_kanaal(invoer, verwacht):
    assert raad_kanaal(invoer) == verwacht


def test_raad_kanaal_onbekend_wordt_overig_en_niet_geraden():
    """Een onherkenbaar kanaal hoort zichtbaar in 'overig', nooit stil in
    'winkel': dat zou omzet aan het verkeerde kanaal (en de verkeerde marge)
    toewijzen."""
    assert raad_kanaal("") == "overig"
    assert raad_kanaal(None) == "overig"


# --- raad_kolommen ------------------------------------------------------------


def test_raad_kolommen_herkent_een_odoo_achtige_export():
    df = pd.DataFrame(columns=["date_order", "product_id", "qty", "price_subtotal"])
    gokken = raad_kolommen(df)
    assert gokken["datum"].kolom == "date_order"
    assert gokken["product"].kolom == "product_id"
    assert gokken["aantal"].kolom == "qty"
    assert gokken["omzet"].kolom == "price_subtotal"


def test_raad_kolommen_zonder_kandidaat_gokt_niet():
    """Raden is expliciet: geen kandidaat betekent kolom None, nooit een
    stille gok op de eerste de beste kolom."""
    df = pd.DataFrame(columns=["x", "y"])
    gokken = raad_kolommen(df)
    assert gokken["datum"].kolom is None
    assert gokken["datum"].zeker is False
