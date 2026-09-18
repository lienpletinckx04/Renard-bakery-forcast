"""Tests voor de marge-invoer (bakkerij/marges.py).

Het kernrisico: dit is de enige invoer die niet uit een bronsysteem komt maar
uit een formulier. Een kapot bestand dat stil als "geen marges" gelezen wordt,
laat een ingevulde marge verdwijnen zonder dat iemand het merkt — elke
afwijking moet dus een fout met een reden zijn, en alleen een ontbrekend
bestand is een normale beginstand.
"""
from decimal import Decimal

import pytest

from bakkerij import marges as mg


def test_geldig_bestand_levert_decimals():
    invoer = mg.parse_marges(
        '{"ingevuld_door": "kwinten", "ingevuld_op": "2026-08-13T10:00:00",'
        ' "marges": {"Brood": "55", "Koffiekoeken": "62.5"}}'
    )
    assert invoer.per_groep == {"Brood": Decimal(55),
                                "Koffiekoeken": Decimal("62.5")}
    assert invoer.ingevuld_door == "kwinten"


def test_ontbrekend_bestand_is_none_geen_fout(tmp_path):
    assert mg.lees_marges(tmp_path / "bestaat-niet.json") is None


def test_bestaand_bestand_wordt_gelezen(tmp_path):
    pad = tmp_path / "marges.json"
    pad.write_text('{"marges": {"Brood": "40"}}', encoding="utf-8")
    invoer = mg.lees_marges(pad)
    assert invoer is not None
    assert invoer.per_groep["Brood"] == Decimal(40)


def test_kapotte_json_is_een_fout_met_reden():
    with pytest.raises(ValueError, match="geen geldige JSON"):
        mg.parse_marges("{dit is geen json")


def test_marges_veld_moet_bestaan():
    with pytest.raises(TypeError, match='"marges"'):
        mg.parse_marges('{"iets_anders": {}}')


def test_percentage_buiten_bereik_is_een_fout():
    with pytest.raises(ValueError, match="buiten het bereik"):
        mg.parse_marges('{"marges": {"Brood": "101"}}')
    with pytest.raises(ValueError, match="buiten het bereik"):
        mg.parse_marges('{"marges": {"Brood": "-1"}}')


def test_percentage_moet_string_met_punt_zijn():
    """Een JSON-getal is verleidelijk maar verboden: 62.5 als float is op een
    dag 62.499...; het contract kent bedragen en percentages alleen als string."""
    with pytest.raises(TypeError, match="string"):
        mg.parse_marges('{"marges": {"Brood": 62.5}}')


def test_komma_decimaal_is_een_fout_geen_stille_nul():
    with pytest.raises(ValueError, match="geen getal"):
        mg.parse_marges('{"marges": {"Brood": "62,5"}}')


def test_groep_zonder_naam_is_een_fout():
    with pytest.raises(ValueError, match="zonder naam"):
        mg.parse_marges('{"marges": {"  ": "10"}}')
