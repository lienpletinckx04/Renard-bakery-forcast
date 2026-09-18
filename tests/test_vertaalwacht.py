"""Tests voor de vertaalwacht van de contractbouw.

Deze tests bestaan omdat de wacht op 17 augustus 2026 groen was terwijl het
Franse productmixscherm "KOMT VAN", "29 producten" en "overige 8 producten"
toonde. De teller zei "26, allemaal productnamen" en had twee mazen:

1. Er werd maar een handvol velden gelezen. Kolomkoppen (lijstitems),
   drempels, tabelwaarden en het complete briefingproza (kop, waarom, nodig)
   vielen buiten de telling.
2. Alles van drie woorden of minder werd als "zal wel een productnaam zijn"
   opzijgelegd. "komt van" is twee woorden en geen productnaam.

De wacht leest nu elke mensleesbare tekst en de uitzonderingen zijn expliciet
(bronvelden, productnaam-paden, merknamen) in plaats van een lengteheuristiek.
Elke maas hieronder is eerst als falende test geschreven tegen de oude wacht.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from contract_bouw import (
    _hoort_gelijk,
    _leesbare_teksten,
    _veldnaam,
    vergelijk_talen,
)


def test_veldnaam_kijkt_door_lijstindexen_heen():
    assert _veldnaam("data.concentratie.kolommen.1") == "kolommen"
    assert _veldnaam("data.top.0.naam") == "naam"
    assert _veldnaam("briefing.punten.2.waarom") == "waarom"


def test_leesbare_teksten_dragen_hun_volledige_pad():
    """Zonder volledig pad kan de bron-uitzondering alleen op veldnaam werken:
    dan is een productnaam in `data.top` niet te onderscheiden van een
    reeksnaam in een grafiek, die óók `naam` heet en wél vertaald hoort."""
    boom = {"data": {"top": [{"naam": "Pistolet"}]}}
    (pad,) = _leesbare_teksten(boom)
    assert pad.split("#")[0] == "data.top.0.naam"


def test_kolomkoppen_in_een_lijst_tellen_mee():
    """De maas van 17 augustus 2026: het laatste padstuk van een lijstitem is
    zijn index, en die stond in geen enkele veldenlijst."""
    boom = {"data": {"concentratie": {"kolommen": ["komt van"]}}}
    assert "komt van" in _leesbare_teksten(boom).values()


def test_briefingproza_telt_mee():
    boom = {"briefing": {"punten": [
        {"kop": "Meetgat", "waarom": "De extractie loopt achter.",
         "nodig": "Extract draaien.", "status": "let_op",
         "statuswoord": "Let op"}], "leeg": "Niets te melden."}}
    teksten = set(_leesbare_teksten(boom).values())
    assert {"Meetgat", "De extractie loopt achter.", "Extract draaien.",
            "Let op", "Niets te melden."} <= teksten
    # de machinesleutel niet: die is geen tekst voor een mens
    assert "let_op" not in teksten


def test_wachternamen_zijn_machinesleutels_en_tellen_niet_mee():
    boom = {"data": {"wachters": [
        {"naam": "dubbele_sleutels", "uitkomst": "goed",
         "toelichting": "Geen dubbele rijen gevonden."}]}}
    teksten = set(_leesbare_teksten(boom).values())
    assert "dubbele_sleutels" not in teksten
    assert "Geen dubbele rijen gevonden." in teksten


def test_de_gevonden_lekken_worden_nu_werk():
    """De drie vondsten van de visuele steekproef, exact zoals ze in het
    contract staan: alle drie korter dan vier woorden, geen van drieën een
    productnaam. De oude lengteheuristiek legde ze alle drie opzij."""
    nl = {"producten": {"data": {
        "concentratie": {
            "kolommen": ["Dit deel van de omzet", "komt van",
                         "van het assortiment"],
            "rijen": [{"label": "29 producten"}],
        },
        "groepen_detail": [{"rest": {"label": "overige 8 producten"}}],
    }}}
    werk, hoort_zo = vergelijk_talen(nl, nl)
    assert set(werk) == {"Dit deel van de omzet", "komt van",
                         "van het assortiment", "29 producten",
                         "overige 8 producten"}
    assert not hoort_zo


def test_productnamen_op_hun_eigen_plek_horen_gelijk_te_zijn():
    nl = {"producten": {"data": {
        "top": [{"naam": "Pistolet blanc"}],
        "groepen_detail": [{"producten": [{"naam": "Boule de Berlin"}]}],
        "verschuiving": {"stijgers": [{"naam": "Baguette"}], "dalers": []},
    }}}
    werk, hoort_zo = vergelijk_talen(nl, nl)
    assert not werk
    assert hoort_zo == {"Pistolet blanc", "Boule de Berlin", "Baguette"}


def test_een_identieke_reeksnaam_is_wel_werk():
    """`naam` is alleen bron op de productnaam-paden. Een grafiekreeks heet
    ook `naam`, en die hoort vertaald te zijn."""
    nl = {"overzicht": {"data": {"grafiek": {"reeksen": [
        {"naam": "Omzet 30 dagen"}]}}}}
    werk, _ = vergelijk_talen(nl, nl)
    assert werk == ["Omzet 30 dagen"]


def test_merknamen_en_aslabels_horen_gelijk():
    nl = {"kanalen": {"data": {
        "grafiek": {"reeksen": [{
            "naam": "Deliveroo",
            "punten": [{"x": "nov 25", "y": 1.0}],
        }]},
    }}}
    werk, hoort_zo = vergelijk_talen(nl, nl)
    assert not werk
    assert hoort_zo == {"Deliveroo", "nov 25"}


def test_vertaalde_teksten_zijn_geen_werk():
    nl = {"producten": {"data": {"concentratie": {"kolommen": ["komt van"]}}}}
    fr = {"producten": {"data": {"concentratie": {"kolommen": ["provient de"]}}}}
    werk, hoort_zo = vergelijk_talen(nl, fr)
    assert not werk and not hoort_zo


def test_hoort_gelijk_is_expliciet_geen_lengteheuristiek():
    # kort en toch werk
    assert not _hoort_gelijk("data.concentratie.kolommen.1#0", "komt van")
    # lang en toch bron: een productnaam mag zo lang zijn als de bakkerij wil
    assert _hoort_gelijk("data.top.3.naam#7",
                         "Bag of vanilla waffles extra groot")
