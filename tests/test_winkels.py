"""De winkelindeling: lezen, toetsen, slugs en niet-toegewezen filialen."""

import pytest

from bakkerij import winkels as wk

GELDIG = ('{"winkels": ['
          '{"naam": "Elsene", "filialen": ["1", "2", "3"]},'
          '{"naam": "Sint-Gillis", "filialen": ["4"]}]}')


def test_geldig_bestand_levert_winkels_met_slugs():
    winkels = wk.parse_winkels(GELDIG)
    assert [w.slug for w in winkels] == ["elsene", "sint-gillis"]
    assert winkels[0].filialen == ("1", "2", "3")


def test_slug_is_padveilig_ook_met_accenten():
    assert wk.slug_van("Ixelles / Élsene²") == "ixelles-elsene2"
    with pytest.raises(ValueError, match="mapnaam"):
        wk.slug_van("!!!")


def test_dubbel_filiaal_is_een_fout():
    tekst = ('{"winkels": [{"naam": "A", "filialen": ["1"]},'
             '{"naam": "B", "filialen": ["1"]}]}')
    with pytest.raises(ValueError, match="precies één winkel"):
        wk.parse_winkels(tekst)


def test_winkel_zonder_filialen_is_een_fout():
    with pytest.raises(ValueError, match="geen filialen"):
        wk.parse_winkels('{"winkels": [{"naam": "A", "filialen": []}]}')


def test_botsende_slugs_zijn_een_fout():
    tekst = ('{"winkels": [{"naam": "Elsene", "filialen": ["1"]},'
             '{"naam": "ELSENE!", "filialen": ["2"]}]}')
    with pytest.raises(ValueError, match="zelfde mapnaam"):
        wk.parse_winkels(tekst)


def test_kapotte_json_en_ontbrekend_veld_zijn_fouten():
    with pytest.raises(ValueError, match="geen geldige JSON"):
        wk.parse_winkels("{")
    with pytest.raises(TypeError, match="winkels"):
        wk.parse_winkels("{}")


def test_ontbrekend_bestand_is_leeg_geen_fout(tmp_path):
    assert wk.lees_winkels(tmp_path / "bestaat-niet.json") == ()


def test_niet_toegewezen_meldt_wat_buiten_de_indeling_valt():
    winkels = wk.parse_winkels(GELDIG)
    assert wk.niet_toegewezen({"1", "2", "3", "4", "tgtg-99"}, winkels) == (
        "tgtg-99",)
    assert wk.niet_toegewezen({"1", "4"}, winkels) == ()
