"""De kostenmodel-invoer van de contractbouw: welke bron, en in welke vorm.

Twee dingen liggen hier vast, en ze zijn allebei op 18 augustus 2026 gemeten
in plaats van bedacht:

1. `kosten_waarden` geeft een DICT terug en niet het model. Stond hier
   `kosten_model or {}`, dan viel de hele contractbouw om zodra er echt kosten
   waren ingevuld -- in beide talen, met een AttributeError diep in de
   berekeningslaag. Geen enkele test kon dat zien omdat er nog nooit een
   kostenmodel bestond (marges.json draagt nul groepen).

2. `kostenmodel_voor_taal` kiest ÉÉN bron. De database wanneer het platform
   daaruit leest, anders de bestanden. Niet beide, en nooit stil terugvallen van
   de een op de ander: twee kostenmodellen die kunnen uiteenlopen, is precies de
   toestand waarin het margescherm cijfers toont uit invoer die niemand heeft
   ingevuld.
"""

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from contract_bouw import kosten_waarden, kostenmodel_voor_taal

from bakkerij import kostenmodel as km
from bakkerij.db import kostenmodel_db as kmdb

MODEL = km.Kostenmodel(
    criteria=(km.Criterium("Grondstoffen", ""),),
    waarden={"Brood": {"Grondstoffen": Decimal("30.00")}},
)


def test_kosten_waarden_levert_de_dict_die_de_berekening_verwacht():
    """DE regressietest van 18 augustus 2026: het model zelf doorgeven gaf
    'Kostenmodel' object has no attribute 'get'."""
    assert kosten_waarden(MODEL) == {"Brood": {"Grondstoffen": Decimal("30.00")}}
    assert isinstance(kosten_waarden(MODEL), dict)


def test_kosten_waarden_van_niets_is_een_lege_dict():
    """Geen invoer is de normale beginstand; de berekening hoort dan gewoon geen
    marge te vinden, niet om te vallen."""
    assert kosten_waarden(None) == {}


def test_de_bestandsroute_blijft_de_bestandsroute():
    """Zonder CONTRACT_BRON=db verandert er niets: geen databaserij komt eraan te
    pas, ook niet als er rijen zouden klaarliggen."""
    model, fout = kostenmodel_voor_taal("bestand", None, None)
    # Er staat geen kostenmodel.json in de repo (data/ is gitignored), dus dit is
    # de echte beginstand: niets ingevuld, en dat is geen fout.
    assert fout is None
    assert model is None or isinstance(model, km.Kostenmodel)


def test_de_databaseroute_bouwt_het_model_uit_de_rijen():
    rijen = (
        [("Grondstoffen", "", "lien", None)],
        [("Brood", "Grondstoffen", Decimal("30.00"))],
    )
    model, fout = kostenmodel_voor_taal("db", rijen, None)
    assert fout is None
    assert model is not None
    assert kosten_waarden(model) == {"Brood": {"Grondstoffen": Decimal("30.00")}}


def test_lege_databasetabellen_zijn_geen_fout():
    model, fout = kostenmodel_voor_taal("db", ([], []), None)
    assert model is None
    assert fout is None


def test_een_onleesbare_database_geeft_een_reden_en_geen_model():
    """Harde regel 8: het margescherm zegt dat het cijfer onbeschikbaar is en
    waarom, in plaats van te schatten of te zwijgen. En de reden noemt de
    databasefout NIET bij naam -- die staat in de bouwuitvoer, want een
    verbindingsfout hoort niet op een scherm dat ook een lezer opent."""
    model, fout = kostenmodel_voor_taal("db", None, "OperationalError")
    assert model is None
    assert fout is not None
    assert "database" in fout.lower()
    assert "OperationalError" not in fout


def test_een_kapot_model_in_de_database_geeft_een_reden_en_stopt_de_bouw_niet():
    """Vijf schermen niet bouwen omdat één invoer niet deugt, is slechter dan het
    margescherm eerlijk op onbeschikbaar zetten."""
    rijen = ([("Grondstoffen", "", "lien", None)],
             [("Brood", "Grondstoffen", Decimal(150))])
    model, fout = kostenmodel_voor_taal("db", rijen, None)
    assert model is None
    assert fout is not None and "buiten het bereik" in fout


def test_de_twee_routes_geven_bij_dezelfde_invoer_hetzelfde_model():
    """De kern van "één bron van waarheid": welke route je ook neemt, hetzelfde
    cijfer. Zou de databaseroute anders normaliseren dan de bestandsroute, dan
    verandert de marge op het moment dat de vlag omgaat."""
    uit_bestand = km.parse_kostenmodel(
        '{"criteria": [{"naam": "Grondstoffen"}], '
        '"waarden": {"Brood": {"Grondstoffen": "30.00"}}}'
    )
    uit_db = kmdb.model_uit_rijen(
        [("Grondstoffen", "", "lien", None)],
        [("Brood", "Grondstoffen", Decimal("30.00"))],
    )
    assert uit_db is not None
    assert uit_db.waarden == uit_bestand.waarden
    assert [c.naam for c in uit_db.criteria] == [
        c.naam for c in uit_bestand.criteria]


def test_een_onbekende_bron_valt_niet_stil_terug():
    """De bron komt van `bakkerij.db.contract_bron`, die al werpt bij een
    onbekende waarde. Mocht er ooit iets anders binnenkomen, dan hoort deze
    functie niet stilzwijgend de bestanden te kiezen."""
    with pytest.raises(ValueError, match="onbekende bron"):
        kostenmodel_voor_taal("elders", None, None)
