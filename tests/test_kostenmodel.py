"""Het kostenmodel: lezen, toetsen, en de v1-overname. Geen rekenwerk hier —
dat zit in berekening.marge_per_groep en wordt in test_berekening getoetst."""

from decimal import Decimal
from textwrap import dedent

import pytest

from bakkerij import kostenmodel as km

GELDIG = dedent("""
    {
      "ingevuld_door": "test",
      "ingevuld_op": "2026-08-14T10:00:00+02:00",
      "criteria": [
        {"naam": "Grondstoffen", "omschrijving": "Foodcost."},
        {"naam": "Verlies en verspilling"}
      ],
      "waarden": {
        "Brood": {"Grondstoffen": "30", "Verlies en verspilling": "5"},
        "Patisserie": {"Grondstoffen": "37.5"}
      }
    }
""")


def test_geldig_bestand_levert_decimals_en_volgorde():
    model = km.parse_kostenmodel(GELDIG)
    assert [c.naam for c in model.criteria] == [
        "Grondstoffen", "Verlies en verspilling"]
    assert model.waarden["Brood"]["Verlies en verspilling"] == Decimal(5)
    assert model.waarden["Patisserie"]["Grondstoffen"] == Decimal("37.5")
    assert isinstance(model.waarden["Brood"]["Grondstoffen"], Decimal)


def test_kapotte_json_is_een_fout_met_reden():
    with pytest.raises(ValueError, match="geen geldige JSON"):
        km.parse_kostenmodel("{niet json")


def test_criteria_en_waarden_velden_moeten_bestaan():
    with pytest.raises(TypeError, match="criteria"):
        km.parse_kostenmodel('{"waarden": {}}')
    with pytest.raises(TypeError, match="waarden"):
        km.parse_kostenmodel('{"criteria": []}')


def test_dubbele_criteriumnaam_is_een_fout_ook_met_andere_kast():
    tekst = ('{"criteria": [{"naam": "Verlies"}, {"naam": "verlies"}], '
             '"waarden": {}}')
    with pytest.raises(ValueError, match="twee keer"):
        km.parse_kostenmodel(tekst)


def test_waarde_voor_onbekend_criterium_is_een_fout():
    tekst = ('{"criteria": [{"naam": "Grondstoffen"}], '
             '"waarden": {"Brood": {"Verpakking": "3"}}}')
    with pytest.raises(ValueError, match="onbekende criterium"):
        km.parse_kostenmodel(tekst)


def test_percentage_buiten_bereik_of_geen_string_is_een_fout():
    basis = '{"criteria": [{"naam": "G"}], "waarden": {"Brood": {"G": %s}}}'
    with pytest.raises(ValueError, match="buiten het bereik"):
        km.parse_kostenmodel(basis % '"101"')
    with pytest.raises(TypeError, match="string"):
        km.parse_kostenmodel(basis % "30")


def test_te_veel_criteria_is_een_fout():
    namen = ", ".join(f'{{"naam": "C{i}"}}' for i in range(km.MAX_CRITERIA + 1))
    with pytest.raises(ValueError, match="hoogstens"):
        km.parse_kostenmodel(f'{{"criteria": [{namen}], "waarden": {{}}}}')


def test_ontbrekend_bestand_is_none_geen_fout(tmp_path):
    assert km.lees_kostenmodel(tmp_path / "bestaat-niet.json") is None


def test_v2_wint_van_v1(tmp_path):
    (tmp_path / "kostenmodel.json").write_text(GELDIG, encoding="utf-8")
    (tmp_path / "marges.json").write_text(
        '{"marges": {"Brood": "60"}}', encoding="utf-8")
    model = km.lees_kostenmodel(tmp_path / "kostenmodel.json",
                                tmp_path / "marges.json")
    assert model.waarden["Brood"]["Grondstoffen"] == Decimal(30)


def test_v1_wordt_zonder_informatieverlies_overgenomen(tmp_path):
    """Een eerdere brutomarge van 62,5% wordt het criterium 'Totale kost'
    met 37,5% — zelfde cijfer, andere schrijfwijze, niets verzonnen."""
    (tmp_path / "marges.json").write_text(
        '{"ingevuld_door": "k", "marges": {"Brood": "62.5"}}', encoding="utf-8")
    model = km.lees_kostenmodel(tmp_path / "kostenmodel.json",
                                tmp_path / "marges.json")
    assert model.criteria[0].naam == km.V1_CRITERIUM
    assert model.waarden["Brood"][km.V1_CRITERIUM] == Decimal("37.5")
    assert model.ingevuld_door == "k"


def test_lege_v1_invoer_blijft_none(tmp_path):
    (tmp_path / "marges.json").write_text('{"marges": {}}', encoding="utf-8")
    assert km.lees_kostenmodel(tmp_path / "kostenmodel.json",
                               tmp_path / "marges.json") is None


def test_de_v1_migratie_en_de_fouten_volgen_de_ingestelde_taal(tmp_path):
    """De naam van het v1-criterium en de parse-fouten komen van óns en volgen
    dus de taal; wat een beheerder zelf opslaat, blijft letterlijk staan."""
    from bakkerij import taal as tl

    (tmp_path / "marges.json").write_text(
        '{"marges": {"Brood": "62.5"}}', encoding="utf-8")
    with tl.in_taal("fr"):
        model = km.lees_kostenmodel(tmp_path / "kostenmodel.json",
                                    tmp_path / "marges.json")
        assert model.criteria[0].naam == km.V1_CRITERIUM_FR
        assert model.waarden["Brood"][km.V1_CRITERIUM_FR] == Decimal("37.5")

        with pytest.raises(ValueError, match="JSON valide"):
            km.parse_kostenmodel("dit is geen json")

    # En terug in het Nederlands blijft het Nederlands (geen bevroren staat).
    with pytest.raises(ValueError, match="geen geldige JSON"):
        km.parse_kostenmodel("dit is geen json")


def test_de_suggestiecriteria_volgen_de_taal_zonder_te_bevriezen():
    from bakkerij import taal as tl

    namen_nl = [c.naam for c in km.standaard_criteria()]
    with tl.in_taal("fr"):
        namen_fr = [c.naam for c in km.standaard_criteria()]
    assert "Grondstoffen" in namen_nl
    assert "Matières premières" in namen_fr
    assert len(namen_nl) == len(namen_fr)
    assert namen_nl != namen_fr
