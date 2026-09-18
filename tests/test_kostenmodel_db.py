"""De databasevorm van het kostenmodel: rijen in, rijen uit, en de heenweg.

Alles hier is puur en raakt geen database. De echte Postgres-kant (de
schrijffunctie van migratie 009, de rechten van service_role, alles-of-niets)
staat in tests/test_db_echt.py -- die vergt een server, deze niet.

De rode draad: er mag GEEN tweede vorm en GEEN tweede validatie ontstaan. Een
model uit de database moet exact dezelfde controles doorstaan als een model uit
een bestand, anders lopen de twee routes uiteen op precies het scherm dat over
geld gaat.
"""

import datetime as dt
import json
from decimal import Decimal

import pytest

from bakkerij import kostenmodel as km
from bakkerij.db import contract_bron
from bakkerij.db import kostenmodel_db as kmdb

DOOR = "lien@asklien.ai"
OP = dt.datetime(2026, 8, 18, 22, 30, tzinfo=dt.UTC)

MODEL = km.Kostenmodel(
    criteria=(
        km.Criterium("Grondstoffen", "Foodcost."),
        km.Criterium("Verlies en verspilling", ""),
    ),
    waarden={
        "Brood": {"Grondstoffen": Decimal("30.50"),
                  "Verlies en verspilling": Decimal(2)},
        "Patisserie": {"Grondstoffen": Decimal("37.5")},
    },
    ingevuld_door=DOOR,
    ingevuld_op="2026-08-18T22:30:00+00:00",
)


# --- de heenweg: model -> rijen ---------------------------------------------


def test_criteriumrijen_beginnen_bij_een_en_houden_de_volgorde():
    """De volgorde is de kolomvolgorde op het scherm, dus ze hoort bewaard te
    blijven -- en de nummering moet gelijk lopen met `with ordinality` in
    migratie 009, anders staan de kolommen anders na een laadrun dan na een
    formulieropslag."""
    rijen = kmdb.criteriumrijen(MODEL, DOOR)
    assert [(naam, nummer) for naam, _o, nummer, _d in rijen] == [
        ("Grondstoffen", 1),
        ("Verlies en verspilling", 2),
    ]
    assert all(door == DOOR for *_rest, door in rijen)


def test_waarderijen_dragen_decimals_en_nooit_floats():
    """De kolom is numeric(5, 2). Een kost van 30,5% die als float rondreist, is
    op het scherm een keer 30,499..."""
    rijen = kmdb.waarderijen(MODEL, DOOR)
    for _groep, _criterium, pct, _door in rijen:
        assert isinstance(pct, Decimal), f"{pct!r} is geen Decimal"
    assert ("Brood", "Grondstoffen", Decimal("30.50"), DOOR) in rijen


def test_waarderijen_hebben_een_vaste_volgorde():
    """Een lijst die per run verschilt, is niet reproduceerbaar. Groep
    alfabetisch, criterium in de volgorde van het model zelf."""
    eerst = [(g, c) for g, c, _p, _d in kmdb.waarderijen(MODEL, DOOR)]
    assert eerst == [
        ("Brood", "Grondstoffen"),
        ("Brood", "Verlies en verspilling"),
        ("Patisserie", "Grondstoffen"),
    ]


# --- de terugweg: rijen -> model --------------------------------------------


def _rijen(model=MODEL):
    criteria = [(naam, omschrijving, DOOR, OP)
                for naam, omschrijving, _nr, _d in kmdb.criteriumrijen(model, DOOR)]
    waarden = [(groep, criterium, pct)
               for groep, criterium, pct, _d in kmdb.waarderijen(model, DOOR)]
    return criteria, waarden


def test_rondgang_verandert_geen_cijfer():
    """Model -> rijen -> model, en er hoort niets te verschuiven. Dit is de test
    die uitsluit dat de databaseroute een ander getal toont dan de bestandsroute
    bij dezelfde invoer."""
    terug = kmdb.model_uit_rijen(*_rijen())
    assert terug is not None
    assert [c.naam for c in terug.criteria] == [c.naam for c in MODEL.criteria]
    assert [c.omschrijving for c in terug.criteria] == [
        c.omschrijving for c in MODEL.criteria]
    assert terug.waarden == MODEL.waarden
    assert terug.ingevuld_door == DOOR
    assert terug.ingevuld_op == OP.isoformat()


def test_lege_tabellen_betekenen_nog_niets_ingevuld_en_geen_fout():
    """Dezelfde beginstand als een ontbrekend kostenmodel.json: None, geen
    exception. Het margescherm zegt dan eerlijk dat er geen kosten zijn."""
    assert kmdb.model_uit_rijen([], []) is None


def test_criteria_zonder_waarden_blijven_een_model():
    """Een beheerder die het menu samenstelt maar nog niets invult, heeft wél
    iets bewaard -- precies zoals een v2-bestand met lege waarden."""
    model = kmdb.model_uit_rijen([("Grondstoffen", "", DOOR, OP)], [])
    assert model is not None
    assert [c.naam for c in model.criteria] == ["Grondstoffen"]
    assert model.waarden == {}


def test_een_kost_voor_een_onbekend_criterium_valt_luid_om():
    """Kan in de database niet gebeuren (migratie 005 legt een refereert-naar
    vast), maar de lezer mag er niet op vertrouwen: dan zou een losgeraakte rij
    stil van het scherm vallen."""
    with pytest.raises(ValueError, match="onbekende criterium"):
        kmdb.model_uit_rijen(
            [("Grondstoffen", "", DOOR, OP)],
            [("Brood", "Spoken", Decimal(5))],
        )


def test_een_percentage_buiten_bereik_valt_luid_om():
    with pytest.raises(ValueError, match="buiten het bereik"):
        kmdb.model_uit_rijen(
            [("Grondstoffen", "", DOOR, OP)],
            [("Brood", "Grondstoffen", Decimal(150))],
        )


def test_de_lezer_gebruikt_dezelfde_validatie_als_het_bestand():
    """Meer dan MAX_CRITERIA criteria is in een bestand een fout, en dus ook in
    de database. Zou hier een eigen reeks controles staan, dan zou de strengste
    afhangen van welke route je toevallig neemt."""
    veel = [(f"C{i}", "", DOOR, OP) for i in range(km.MAX_CRITERIA + 1)]
    with pytest.raises(ValueError, match="hoogstens"):
        kmdb.model_uit_rijen(veel, [])


def test_ontbrekende_bewaargegevens_worden_leeg_en_geen_fout():
    """Een handmatig ingevoegde rij zonder tijdstip mag het model niet slopen."""
    model = kmdb.model_uit_rijen([("Grondstoffen", None, "", None)], [])
    assert model is not None
    assert model.ingevuld_door == ""
    assert model.ingevuld_op == ""


# --- de bestandsvorm als enige vorm -----------------------------------------


def test_naar_boom_is_de_omkering_van_de_parser():
    """`toets` en de databaseschrijver rusten hierop: het model terug in de
    bestandsvorm moet door de parser komen zonder één cijfer te verschuiven."""
    opnieuw = km.parse_kostenmodel(json.dumps(km.naar_boom(MODEL)))
    assert opnieuw.waarden == MODEL.waarden
    assert [c.naam for c in opnieuw.criteria] == [c.naam for c in MODEL.criteria]


def test_naar_boom_schrijft_percentages_als_string():
    """Een JSON-getal zou onderweg door een float gaan; de parser weigert er
    daarom een, en `naar_boom` levert er dus geen."""
    boom = km.naar_boom(MODEL)
    assert boom["waarden"]["Brood"]["Grondstoffen"] == "30.50"
    assert boom["versie"] == 2


def test_toets_weigert_een_model_dat_de_parser_niet_zou_overleven():
    """Een `Kostenmodel` kan ook buiten de parser om ontstaan. Dan gelden de
    regels onverkort -- anders is de validatie te omzeilen door het model zelf
    samen te stellen."""
    stuk = km.Kostenmodel(
        criteria=(km.Criterium("Grondstoffen", ""),),
        waarden={"Brood": {"Onbekend": Decimal(5)}},
    )
    with pytest.raises(ValueError, match="onbekende criterium"):
        km.toets(stuk)


def test_schrijf_zonder_naam_weigert_voor_er_iets_gewist_is():
    """bewaard_door is `not null` in migratie 005 omdat elke wijziging aan de
    cijferbasis de naam draagt van wie hem deed. Deze controle staat vóór de
    verbinding, zodat een naamloze poging nooit een delete kan uitlokken."""
    with pytest.raises(ValueError, match="bewaard_door"):
        kmdb.schrijf(None, MODEL, "   ")


# --- welke bron de omgeving aanwijst ----------------------------------------


def test_zonder_vlag_leest_de_bouw_de_bestanden():
    """Het belangrijkste gedrag is negatief: zonder CONTRACT_BRON verandert er
    niets aan de bestaande route. Dezelfde garantie als de TS-tegenhanger in
    platform/tests/contract-bron.test.ts."""
    assert contract_bron({}) == "bestand"
    assert contract_bron({"CONTRACT_BRON": ""}) == "bestand"
    assert contract_bron({"CONTRACT_BRON": "bestand"}) == "bestand"


def test_met_de_vlag_op_db_wisselt_de_bron():
    assert contract_bron({"CONTRACT_BRON": "db"}) == "db"
    assert contract_bron({"CONTRACT_BRON": " db "}) == "db"


def test_een_onbekende_waarde_werpt_in_plaats_van_stil_terug_te_vallen():
    """Stil terugvallen zou een verkeerd gezette vlag verzwijgen als een
    werkende run -- en op een runner zonder data/config/ is dat het verschil
    tussen een volledig en een verarmd contract."""
    with pytest.raises(ValueError, match="CONTRACT_BRON=postgres is onbekend"):
        contract_bron({"CONTRACT_BRON": "postgres"})
