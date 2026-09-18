"""Tests voor de briefing bovenaan elk scherm (blok 21).

Wat hier vooral bewaakt wordt, en het zijn niet toevallig de drie dingen die
een briefing kunnen laten ontsporen:

  * **de grens.** Signalering, geen productie-advies. Er staat een test die op
    elk gegenereerd punt van alle zes de schermen zoekt naar de werkwoorden
    waarmee advies begint ("plan", "bak", "verhoog"). Die grens is een
    beslissing van 14 augustus 2026 en geen smaakkwestie; ze hoort dus in een
    test en niet alleen in een docstring;
  * **de vorm.** `bedrag` is een string met punt-decimaal of niets, `status` is
    een machinesleutel, `statuswoord` is het woord dat een mens leest, en er
    staat nooit een opgemaakt bedrag in de lopende tekst — dat maakt de UI;
  * **de stilte.** Een punt verschijnt alleen als een meting het staaft. Onder
    de drempel is er geen punt, en zonder meting is er geen geruststelling: de
    leeg-zin belooft niets over wat niet gemeten is (harde regel 8).
"""

import datetime as dt
from decimal import Decimal

import pandas as pd
import pytest

from bakkerij import briefing as bf
from bakkerij import taal as tl
from bakkerij.berekening import Bonritme, Margebeeld, Periodecontext, Verschuiving
from bakkerij.canoniek import Meetgat, Prognosevenster, Sluitingsstand
from bakkerij.kwaliteit import Bronstand, Wachter

VANDAAG = dt.date(2026, 8, 15)
GEMETEN_TOT = dt.date(2026, 8, 14)


def _versheid(**kw) -> bf.Versheid:
    """Een verse toestand: gisteren gemeten, geen gat. Zo gaan de tests over
    het punt dat ze bedoelen en niet over de achterstand."""
    kw.setdefault("vandaag", VANDAAG)
    kw.setdefault("gemeten_tot", GEMETEN_TOT)
    return bf.Versheid(**kw)


def _meetgat(niet_ingeladen: int, gemeten_gesloten: int = 0,
             gepland_dicht: int = 0) -> Meetgat:
    dagen = niet_ingeladen + gemeten_gesloten + gepland_dicht
    van = VANDAAG - dt.timedelta(days=dagen)
    return Meetgat(van=van, tot=VANDAAG - dt.timedelta(days=1), dagen=dagen,
                   gemeten_gesloten=gemeten_gesloten,
                   gepland_dicht=gepland_dicht,
                   niet_ingeladen=niet_ingeladen)


# De echte toestand van 18 augustus 2026, want dat is de melding die deze tests
# bewaken: laatste open dag 31 juli, dicht sinds 1 augustus, weer open op
# 24 augustus. Als losse constanten, zodat de datums in de asserts en de datums
# in de fixture dezelfde zijn en niemand ze twee keer hoeft uit te rekenen.
SLUITING_VANDAAG = dt.date(2026, 8, 18)
SLUITING_GEMETEN_TOT = dt.date(2026, 7, 31)
SLUITING_DAGEN = 18
SLUITING_OPEN = dt.date(2026, 8, 24)


def _sluiting(dagen: int = SLUITING_DAGEN, *,
              reden: str = "Jaarlijkse sluiting",
              eerste_open_dag: dt.date | None = SLUITING_OPEN
              ) -> Sluitingsstand:
    """Een sluiting die op SLUITING_VANDAAG nog loopt, `dagen` dagen oud."""
    return Sluitingsstand(
        dicht_sinds=SLUITING_VANDAAG - dt.timedelta(days=dagen - 1),
        dagen=dagen, reden=reden, eerste_open_dag=eerste_open_dag,
    )


def _periode(verschil_pct: Decimal | None, richting: str | None = None,
             dagen: int = 30) -> Periodecontext:
    return Periodecontext(
        totaal=Decimal("30000.00"), gemiddelde=Decimal("1000.00"),
        beste_datum=pd.Timestamp("2026-08-08"), beste_omzet=Decimal("1800.00"),
        verschil_pct=verschil_pct, richting=richting,
        dagen=dagen, vorig_dagen=dagen,
    )


def _afwijkende(rijen) -> pd.DataFrame:
    """rijen: (datum, omzet, verwacht_mediaan). Nieuwste eerst, zoals de
    berekeningslaag ze levert."""
    return pd.DataFrame(
        [{"datum": pd.Timestamp(d), "omzet": o, "verwacht_mediaan": m,
          "z": 4.0} for d, o, m in rijen]
    )


def _bonritme(dagen_zonder_bonnen: int = 0) -> Bonritme:
    """Een bonritme dat er gewoon is. De ontbindingstermen doen hier niet mee:
    de briefing kijkt alleen of de telling bestaat en of ze dagen mist."""
    return Bonritme(
        bonnen_per_dag=Decimal(300), gemiddeld_bonbedrag=Decimal("8.00"),
        verschil=None, bonneneffect=None, bonbedrag_effect=None,
        kruisterm=None, dagen=30, vorig_dagen=30,
        dagen_zonder_bonnen=dagen_zonder_bonnen,
    )


def _verschuiving(rijen, dagen: int = 30, vorig_dagen: int = 30) -> Verschuiving:
    """rijen: (product_id, naam, omzet_nu, omzet_vorig), aflopend op verschil."""
    frame = pd.DataFrame(
        [{"product_id": p, "product_naam": n, "omzet_nu": nu,
          "omzet_vorig": vorig, "verschil": nu - vorig,
          "verschil_pct": None, "nieuw": vorig == 0}
         for p, n, nu, vorig in rijen]
    )
    return Verschuiving(rijen=frame, dagen=dagen, vorig_dagen=vorig_dagen)


def _margebeeld(groepen, *, gewogen: Decimal | None, dekking: Decimal,
                totaal: Decimal, gedekt: Decimal) -> Margebeeld:
    """groepen: (naam, omzet, marge_pct of None)."""
    rijen = pd.DataFrame(
        [{"groep": g, "omzet": o, "aandeel_pct": Decimal("10.0"),
          "marge_pct": m, "marge_eur": None if m is None else Decimal("1.00"),
          "opbouw": []}
         for g, o, m in groepen]
    )
    return Margebeeld(
        rijen=rijen, per_criterium=pd.DataFrame(), totale_omzet=totaal,
        gedekte_omzet=gedekt, marge_eur=Decimal("100.00"), gewogen_pct=gewogen,
        dekking_pct=dekking, dagen=30,
    )


def _venster(dagen: list[str], start: str = "2026-08-15") -> Prognosevenster:
    return Prognosevenster(
        gemeten_tot=GEMETEN_TOT, vandaag=VANDAAG,
        start=dt.date.fromisoformat(start),
        dagen=pd.DatetimeIndex([pd.Timestamp(d) for d in dagen]),
        overgeslagen=(), buiten_kalender=(), meetgat=None,
    )


def _banddekking(waarden: list[float], beloofd: float = 0.80) -> pd.DataFrame:
    return pd.DataFrame(
        [{"stap": i + 1, "n": 40, "binnen_band": w, "beloofd": beloofd}
         for i, w in enumerate(waarden)]
    )


def _alle_briefings() -> list[bf.Briefing]:
    """Van elk scherm een briefing met zoveel mogelijk punten tegelijk.

    Voor de tests die over de vorm gaan en niet over één punt: die moeten over
    alle teksten lopen die deze module kan produceren, anders bewaken ze het
    ene punt dat toevallig getest wordt.
    """
    versheid = _versheid(meetgat=_meetgat(9))
    return [
        bf.overzicht(
            versheid=versheid,
            periode=_periode(Decimal("-14.2"), "neer"),
            afwijkende=_afwijkende([("2026-08-08", 2400.0, 1100.0)]),
            bonritme=None,
        ),
        bf.kanalen(
            versheid=versheid,
            bronstanden=[
                Bronstand("odoo-kassa", GEMETEN_TOT, 100, "stil", "toel"),
                Bronstand("tgtg", dt.date(2026, 6, 1), 10, "achter", "toel"),
                Bronstand("deliveroo", None, 0, "ontbreekt", "toel"),
            ],
            tgtg_kost_bekend=False,
        ),
        bf.producten(
            versheid=versheid,
            verschuiving=_verschuiving([
                ("p1", "Pistolet", 3000.0, 1000.0),
                ("p2", "Boule", 500.0, 2000.0),
            ]),
        ),
        bf.marge(
            versheid=versheid,
            beeld=_margebeeld(
                [("Brood", 5000.0, Decimal("40.0")),
                 ("Patisserie", 5000.0, Decimal("-3.0")),
                 ("Dranken", 5000.0, None)],
                gewogen=Decimal("38.0"), dekking=Decimal("45.0"),
                totaal=Decimal("15000.00"), gedekt=Decimal("6750.00"),
            ),
            invoer_fout="de kolom pct ontbreekt.",
        ),
        bf.prognose(
            versheid=versheid,
            venster=_venster(["2026-08-15", "2026-08-16", "2026-08-17"]),
            bias=-0.05,
            banddekking=_banddekking([0.62, 0.71]),
            band_doel=0.80,
            kalenderdekking=dt.date(2026, 8, 16),
            sluitingsdekking=dt.date(2026, 8, 16),
            categorieen_overgeslagen=["Dranken"],
        ),
        bf.instellingen(
            versheid=versheid,
            bronstanden=[Bronstand("deliveroo", None, 0, "ontbreekt", "toel")],
            wachters=[Wachter("dubbele_sleutels", "fout", "3 dubbele rijen."),
                      Wachter("drempelrand", "let_op", "2 grensdagen.")],
            kostenmodel_ingevuld=False,
        ),
    ]


# --- de vorm ----------------------------------------------------------------


def test_statuswoord_volgt_de_status_en_de_taal():
    """De betekenis zit in het woord, niet in de kleur (huisstijl)."""
    punt = bf.BriefingPunt(kop="k", waarom="w", status="actie")
    assert punt.status == "actie"
    assert punt.statuswoord == "Actie nodig"
    with tl.in_taal("fr"):
        assert bf.BriefingPunt(kop="k", waarom="w",
                               status="actie").statuswoord == "Action requise"
        assert bf.BriefingPunt(kop="k", waarom="w",
                               status="goed").statuswoord == "En ordre"


def test_een_bedrag_is_een_string_met_punt_decimaal():
    for briefing in _alle_briefings():
        for punt in briefing.punten:
            if punt.bedrag is None:
                continue
            assert isinstance(punt.bedrag, str)
            assert "," not in punt.bedrag
            float(punt.bedrag)  # machinewaarde, dus leesbaar als getal


def test_een_bedrag_zonder_soort_wordt_geweigerd():
    """De UI maakt het bedrag op, en kan dat niet zonder eenheid."""
    with pytest.raises(ValueError, match="soort"):
        bf.BriefingPunt(kop="k", waarom="w", bedrag="12.00")


def test_een_aantal_zonder_eenheid_wordt_geweigerd():
    """Een kaal aantal op het scherm leest als een notificatieteller; euro en
    verschil maken zichzelf leesbaar en dragen er juist geen."""
    with pytest.raises(ValueError, match="eenheid"):
        bf.BriefingPunt(kop="k", waarom="w", bedrag="9", soort="aantal")
    with pytest.raises(ValueError, match="eenheid"):
        bf.BriefingPunt(kop="k", waarom="w", bedrag="12.00", soort="euro",
                        eenheid="dagen")


def test_elk_aantal_in_de_briefings_draagt_zijn_eenheid():
    for briefing in _alle_briefings():
        for punt in briefing.punten:
            if punt.soort == "aantal":
                assert punt.eenheid, punt.kop


def test_een_float_als_bedrag_wordt_geweigerd():
    """Een float in JSON is een afrondingsfout die niemand kan navertellen."""
    with pytest.raises(TypeError, match="string"):
        bf.BriefingPunt(kop="k", waarom="w", bedrag=12.0, soort="euro")


def test_een_onbekende_status_is_een_fout():
    with pytest.raises(ValueError, match="Onbekende status"):
        bf.BriefingPunt(kop="k", waarom="w", status="rood")


def test_geen_opgemaakt_bedrag_in_de_lopende_tekst():
    """Bedragen horen in `bedrag`, niet in de zin. Anders maakt de UI het ene
    getal op en het andere niet, op dezelfde regel."""
    for briefing in _alle_briefings():
        for punt in briefing.punten:
            for tekst in (punt.kop, punt.waarom, punt.nodig or ""):
                assert "€" not in tekst


def test_de_kop_is_een_zin_zonder_cijferopmaak():
    for briefing in _alle_briefings():
        for punt in briefing.punten:
            assert punt.kop
            assert not punt.kop.endswith(".")
            assert "%" not in punt.kop


def test_als_dict_levert_de_vorm_die_het_contract_doorgeeft():
    briefing = bf.overzicht(versheid=_versheid(), periode=None,
                            afwijkende=None, bonritme=_bonritme())
    d = briefing.als_dict()
    assert set(d) == {"punten", "leeg"}
    assert d["punten"] == []
    assert d["leeg"]


# --- de grens: signalering, geen advies -------------------------------------

#: Woorden waarmee productie-advies begint. De beslissing van 14 augustus 2026
#: houdt die buiten fase 1; heropening loopt via vraag 56.
VERBODEN = ("plan ", "bak ", "bakken", "verhoog", "verlaag", "minder bakken",
            "meer bakken", "aanbevol", "advies", "adviseer", "raden wij",
            "zou je moeten", "conseill", "recommand")


def test_geen_enkel_punt_geeft_productie_advies():
    for briefing in _alle_briefings():
        for punt in briefing.punten:
            tekst = f"{punt.kop} {punt.waarom} {punt.nodig or ''}".lower()
            for woord in VERBODEN:
                assert woord not in tekst, f"advies in de briefing: {woord!r}"


def test_de_leegzin_belooft_niets_wat_niet_gemeten_is():
    """Zonder metingen is er geen groen licht, alleen stilte met die uitleg."""
    briefing = bf.overzicht(versheid=_versheid(), periode=None,
                            afwijkende=None, bonritme=_bonritme())
    assert briefing.punten == []
    assert "garantie" in briefing.leeg


# --- volgorde en maximum ----------------------------------------------------


def test_zwaarste_eerst():
    briefing = bf.instellingen(
        versheid=_versheid(),
        bronstanden=[],
        wachters=[Wachter("drempelrand", "let_op", "iets"),
                  Wachter("dubbele_sleutels", "fout", "iets anders")],
        kostenmodel_ingevuld=True,
    )
    statussen = [p.status for p in briefing.punten]
    assert statussen == sorted(statussen, key=bf._RANG.__getitem__)
    assert statussen[0] == "actie"


def test_actiepunten_overleven_het_maximum():
    """Een punt dat om iemand vraagt, mag niet wegvallen omdat er observaties
    boven staan."""
    wachters = [Wachter(f"controle_{i}", "fout", "iets") for i in range(8)]
    briefing = bf.instellingen(versheid=_versheid(), bronstanden=[],
                               wachters=wachters, kostenmodel_ingevuld=True)
    assert len(briefing.punten) == 8
    assert all(p.status == "actie" for p in briefing.punten)


def test_de_zachtere_punten_worden_afgekapt_op_het_maximum():
    wachters = [Wachter(f"controle_{i}", "let_op", "iets") for i in range(9)]
    briefing = bf.instellingen(versheid=_versheid(), bronstanden=[],
                               wachters=wachters, kostenmodel_ingevuld=True)
    assert len(briefing.punten) == bf.MAX_PUNTEN


# --- de versheid, gedeeld door elk scherm -----------------------------------


def test_onder_de_drempel_is_er_geen_punt():
    briefing = bf.overzicht(
        versheid=_versheid(meetgat=_meetgat(bf.ACHTERSTAND_DAGEN - 1)),
        periode=None, afwijkende=None, bonritme=_bonritme(),
    )
    assert briefing.punten == []


def test_een_gesloten_zondag_is_geen_achterstand():
    """Het meetgat telt alleen wat niet ingeladen is. Een winkel die dicht was,
    is geen bron die stilviel."""
    briefing = bf.overzicht(
        versheid=_versheid(meetgat=_meetgat(niet_ingeladen=0,
                                            gemeten_gesloten=5)),
        periode=None, afwijkende=None, bonritme=_bonritme(),
    )
    assert briefing.punten == []


def test_zonder_meetgat_telt_de_briefing_kalenderdagen_en_zegt_dat():
    briefing = bf.overzicht(
        versheid=bf.Versheid(vandaag=VANDAAG,
                             gemeten_tot=dt.date(2026, 8, 10)),
        periode=None, afwijkende=None, bonritme=None,
    )
    achter = [p for p in briefing.punten if p.bedrag == "5"]
    assert len(achter) == 1
    assert "kalenderdagen" in achter[0].waarom


def test_een_timestamp_mag_ook_als_datum_binnenkomen():
    """De peildatum van de berekeningslaag is een Timestamp, de kalender levert
    een date. Beide moeten werken zonder dat de aanroeper eraan denkt."""
    versheid = bf.Versheid(vandaag=pd.Timestamp("2026-08-15"),
                           gemeten_tot=pd.Timestamp("2026-08-10"))
    assert versheid.vandaag == VANDAAG
    briefing = bf.overzicht(versheid=versheid, periode=None, afwijkende=None,
                            bonritme=_bonritme())
    assert briefing.punten[0].bedrag == "5"


def test_een_lange_achterstand_wordt_actie():
    briefing = bf.overzicht(
        versheid=_versheid(meetgat=_meetgat(bf.ACHTERSTAND_ERNSTIG_DAGEN)),
        periode=None, afwijkende=None, bonritme=None,
    )
    punt = briefing.punten[0]
    assert punt.status == "actie"
    assert punt.bedrag == str(bf.ACHTERSTAND_ERNSTIG_DAGEN)
    assert punt.soort == "aantal"
    assert punt.nodig


def test_zonder_gemeten_dag_is_alles_geblokkeerd():
    briefing = bf.overzicht(
        versheid=bf.Versheid(vandaag=VANDAAG, gemeten_tot=None),
        periode=_periode(Decimal("-20.0"), "neer"), afwijkende=None,
        bonritme=None,
    )
    assert briefing.punten[0].status == "actie"
    assert briefing.punten[0].bedrag is None


# --- de sluiting tegenover de achterstand -----------------------------------
#
# De fout van 18 augustus 2026, aan de briefingkant: tijdens de zomersluiting
# meldde het openingsscherm tien dagen achterstand en vroeg het het
# platformbeheer de nachtelijke synchronisatie na te kijken, terwijl elk van die
# tien dagen als `gepland_dicht` in de kalender stond. Een externe lezer
# concludeerde eruit dat het platform verouderde cijfers toonde. Deze tests
# leggen beide kanten vast: een sluiting is geen achterstand, en een echt gat
# blijft er wel een.


def _gedeelde_punten(**kw) -> list:
    """De punten die elk scherm deelt, los van de rest van een scherm.

    Via `overzicht` en niet via `_versheidspunten` zelf: het gaat erom wat er
    werkelijk op een scherm belandt, en `_bundel` zit daartussen.
    """
    kw.setdefault("vandaag", SLUITING_VANDAAG)
    kw.setdefault("gemeten_tot", SLUITING_GEMETEN_TOT)
    return bf.overzicht(versheid=bf.Versheid(**kw), periode=None,
                        afwijkende=None, bonritme=_bonritme()).punten


def test_een_sluitingsperiode_levert_geen_achterstandsmelding_op():
    """De hele situatie van 18 augustus: zeventien dagen gat, geen dag ervan
    onverklaard, en de zaak is vandaag nog dicht."""
    punten = _gedeelde_punten(
        meetgat=_meetgat(niet_ingeladen=0, gemeten_gesloten=7, gepland_dicht=10),
        sluiting=_sluiting(),
    )
    koppen = [p.kop for p in punten]
    assert "De cijfers lopen achter op vandaag" not in koppen
    assert not any(p.nodig and "synchronisatie" in p.nodig for p in punten)


def test_tijdens_een_sluiting_zegt_de_briefing_wat_er_aan_de_hand_is():
    punten = _gedeelde_punten(
        meetgat=_meetgat(niet_ingeladen=0, gemeten_gesloten=7, gepland_dicht=10),
        sluiting=_sluiting(),
    )
    assert len(punten) == 1
    punt = punten[0]
    assert punt.kop == "De bakkerij is gesloten"
    # De drie dingen die de lezer nodig heeft: sinds wanneer, tot wanneer, en
    # waarom de cijfers ophouden waar ze ophouden.
    assert "1 augustus 2026" in punt.waarom
    assert "24 augustus 2026" in punt.waarom
    assert "31 juli 2026" in punt.waarom
    assert "Jaarlijkse sluiting" in punt.waarom
    # Signalering en geen alarm: niemand hoeft iets na te kijken.
    assert punt.status == "let_op"
    assert punt.nodig is None
    assert (punt.bedrag, punt.soort, punt.eenheid) == (
        str(SLUITING_DAGEN), "aantal", "dagen",
    )


def test_een_sluiting_zonder_bekend_einde_verzint_geen_openingsdag():
    punten = _gedeelde_punten(
        meetgat=_meetgat(niet_ingeladen=0, gepland_dicht=5),
        sluiting=_sluiting(6, eerste_open_dag=None),
    )
    assert len(punten) == 1
    assert "niet bekend" in punten[0].waarom


def test_een_korte_sluiting_haalt_de_briefing_niet():
    """Een bakkerij met een vaste sluitingsdag is elke week een dag dicht; een
    punt dat elke maandag verschijnt, leest niemand nog."""
    punten = _gedeelde_punten(
        meetgat=_meetgat(niet_ingeladen=0, gepland_dicht=1),
        sluiting=_sluiting(bf.SLUITING_MIN_DAGEN - 1),
    )
    assert punten == []


def test_een_echt_gat_in_open_dagen_blijft_een_achterstand():
    """Geen sluiting in zicht, dagen die niemand verklaart: dan hoort het punt er
    te staan, met de vraag aan het platformbeheer erbij."""
    punten = _gedeelde_punten(meetgat=_meetgat(niet_ingeladen=4))
    assert len(punten) == 1
    punt = punten[0]
    assert punt.kop == "De cijfers lopen achter op vandaag"
    assert punt.bedrag == "4"
    assert "synchronisatie" in punt.nodig


def test_een_sluiting_dekt_een_achterstand_van_ervoor_niet_toe():
    """De twee punten sluiten elkaar niet uit. Zijn er open dagen die niemand
    verklaart én is de zaak nu dicht, dan staan er twee punten."""
    punten = _gedeelde_punten(
        meetgat=_meetgat(niet_ingeladen=bf.ACHTERSTAND_ERNSTIG_DAGEN,
                         gepland_dicht=10),
        sluiting=_sluiting(10),
    )
    koppen = [p.kop for p in punten]
    assert "De bakkerij is gesloten" in koppen
    assert "De cijfers lopen achter op vandaag" in koppen


def test_de_achterstandsmelding_zegt_dat_geen_sluiting_de_dagen_verklaart():
    """Het woord dat het onderscheid draagt, staat in de tekst zelf: wie dit punt
    leest, moet weten dat het niet over sluitingsdagen gaat."""
    punt = _gedeelde_punten(meetgat=_meetgat(niet_ingeladen=4))[0]
    assert "geen enkele sluiting verklaart" in punt.waarom


def test_de_franse_sluitingsmelding_draagt_dezelfde_datums():
    with tl.in_taal("fr"):
        punten = _gedeelde_punten(
            meetgat=_meetgat(niet_ingeladen=0, gepland_dicht=10,
                             gemeten_gesloten=7),
            sluiting=_sluiting(),
        )
    assert len(punten) == 1
    punt = punten[0]
    assert punt.kop == "La boulangerie est fermée"
    # Het Frans schrijft de eerste van de maand als rangtelwoord.
    assert "le 1er août 2026" in punt.waarom
    assert "24 août 2026" in punt.waarom
    assert "31 juillet 2026" in punt.waarom


# --- Dagoverzicht -----------------------------------------------------------


def test_een_omzetschuif_binnen_de_bandbreedte_zwijgt():
    briefing = bf.overzicht(
        versheid=_versheid(),
        periode=_periode(bf.OMZETSCHUIF_PCT - Decimal("0.1"), "neer"),
        afwijkende=None, bonritme=_bonritme(),
    )
    assert briefing.punten == []


def test_een_omzetschuif_erbuiten_draagt_het_percentage_als_machinewaarde():
    briefing = bf.overzicht(
        versheid=_versheid(), periode=_periode(Decimal("-14.2"), "neer"),
        afwijkende=None, bonritme=_bonritme(),
    )
    punt = briefing.punten[0]
    assert punt.bedrag == "-14.2"
    assert punt.soort == "verschil"
    assert punt.richting == "neer"
    assert punt.nodig is None  # signalering; er is niets nodig van niemand


def test_zonder_vergelijkbaar_venster_is_er_geen_omzetpunt():
    """Een ontbrekende vergelijking staat met reden in `onbeschikbaar`; de
    briefing verzint er geen punt bij."""
    briefing = bf.overzicht(
        versheid=_versheid(), periode=_periode(None), afwijkende=None,
        bonritme=_bonritme(),
    )
    assert briefing.punten == []


def test_een_afwijkende_dag_draagt_het_verschil_in_euro():
    briefing = bf.overzicht(
        versheid=_versheid(), periode=None,
        afwijkende=_afwijkende([("2026-08-08", 2400.0, 1100.0),
                                ("2026-07-04", 200.0, 1100.0)]),
        bonritme=_bonritme(),
    )
    punt = briefing.punten[0]
    assert punt.bedrag == "1300.00"
    assert punt.soort == "euro"
    assert punt.richting == "op"
    assert "zaterdag 8 augustus 2026" in punt.waarom  # de jongste, niet de ergste


def test_zonder_bonnentelling_staat_dat_in_de_briefing():
    briefing = bf.overzicht(versheid=_versheid(), periode=None,
                            afwijkende=None, bonritme=None)
    punt = briefing.punten[0]
    assert punt.status == "let_op"
    assert punt.nodig
    assert punt.bedrag is None


def test_gaten_in_de_bonnentelling_worden_geteld():
    briefing = bf.overzicht(
        versheid=_versheid(), periode=None, afwijkende=None,
        bonritme=_bonritme(bf.BON_GAT_DAGEN),
    )
    punt = briefing.punten[0]
    assert punt.bedrag == str(bf.BON_GAT_DAGEN)
    assert punt.soort == "aantal"


# --- Verkoopkanalen ---------------------------------------------------------


def test_een_kanaal_zonder_data_vraagt_om_iemand():
    briefing = bf.kanalen(
        versheid=_versheid(),
        bronstanden=[Bronstand("deliveroo", None, 0, "ontbreekt", "toel")],
        tgtg_kost_bekend=True,
    )
    punt = briefing.punten[0]
    assert punt.status == "actie"
    assert "Deliveroo" in punt.kop
    assert "Partner Hub" in punt.nodig


def test_een_verse_bron_levert_geen_punt():
    """De briefing is geen opsomming van wat goed gaat."""
    briefing = bf.kanalen(
        versheid=_versheid(),
        bronstanden=[Bronstand("odoo-kassa", GEMETEN_TOT, 100, "vers", "toel"),
                     Bronstand("tgtg", GEMETEN_TOT, 10, "gesloten", "toel")],
        tgtg_kost_bekend=True,
    )
    assert briefing.punten == []


def test_een_achterlopende_bron_telt_de_dagen_sinds_de_laatste_meting():
    briefing = bf.kanalen(
        versheid=_versheid(),
        bronstanden=[Bronstand("tgtg", dt.date(2026, 6, 1), 10, "achter", "x")],
        tgtg_kost_bekend=True,
    )
    punt = briefing.punten[0]
    assert punt.bedrag == str((VANDAAG - dt.date(2026, 6, 1)).days)
    assert punt.soort == "aantal"
    assert punt.status == "let_op"


def test_zonder_kanaalkost_is_de_commissie_een_punt():
    briefing = bf.kanalen(versheid=_versheid(), bronstanden=[],
                          tgtg_kost_bekend=False)
    assert len(briefing.punten) == 1
    assert briefing.punten[0].bedrag is None


# --- Productmix -------------------------------------------------------------


def test_een_daler_boven_de_drempel_komt_in_de_briefing():
    """De stijger blijft hier onder de drempel en de daler niet; alleen de
    daler hoort in de briefing."""
    briefing = bf.producten(
        versheid=_versheid(),
        verschuiving=_verschuiving([("p1", "Pistolet", 1000.0, 995.0),
                                    ("p2", "Boule", 500.0, 2000.0)]),
    )
    assert len(briefing.punten) == 1
    punt = briefing.punten[0]
    assert "Boule" in punt.kop
    assert punt.bedrag == "-1500.00"
    assert punt.richting == "neer"


def test_een_stijger_en_een_daler_kunnen_allebei():
    briefing = bf.producten(
        versheid=_versheid(),
        verschuiving=_verschuiving([("p1", "Pistolet", 3000.0, 1000.0),
                                    ("p2", "Boule", 500.0, 2000.0)]),
    )
    assert [p.richting for p in briefing.punten] == ["op", "neer"]
    assert [p.bedrag for p in briefing.punten] == ["2000.00", "-1500.00"]


def test_een_beweging_onder_de_drempel_zwijgt():
    """Twee procent van de vensteromzet; daaronder is het ruis."""
    briefing = bf.producten(
        versheid=_versheid(),
        verschuiving=_verschuiving([("p1", "Pistolet", 10000.0, 9990.0),
                                    ("p2", "Boule", 10000.0, 10010.0)]),
    )
    assert briefing.punten == []


def test_zonder_vergelijkbare_vensters_is_dat_zelf_het_punt():
    briefing = bf.producten(
        versheid=_versheid(),
        verschuiving=_verschuiving([("p1", "Pistolet", 1000.0, 0.0)],
                                   dagen=30, vorig_dagen=22),
    )
    assert len(briefing.punten) == 1
    assert "22" in briefing.punten[0].waarom
    assert briefing.punten[0].bedrag is None


# --- Margebewaking ----------------------------------------------------------


def test_zonder_kostenmodel_is_de_hele_omzet_zonder_marge():
    briefing = bf.marge(
        versheid=_versheid(),
        beeld=_margebeeld([("Brood", 5000.0, None)], gewogen=None,
                          dekking=Decimal("0.0"), totaal=Decimal("15000.00"),
                          gedekt=Decimal("0.00")),
        invoer_fout=None,
    )
    punt = briefing.punten[0]
    assert punt.status == "actie"
    assert punt.bedrag == "15000.00"
    assert punt.soort == "euro"
    assert "Instellingen" in punt.nodig


def test_een_lage_dekking_draagt_de_ongedekte_omzet():
    briefing = bf.marge(
        versheid=_versheid(),
        beeld=_margebeeld(
            [("Brood", 5000.0, Decimal("40.0")), ("Dranken", 5000.0, None)],
            gewogen=Decimal("40.0"), dekking=Decimal("60.0"),
            totaal=Decimal("10000.00"), gedekt=Decimal("6000.00")),
        invoer_fout=None,
    )
    punt = briefing.punten[0]
    assert punt.bedrag == "4000.00"
    assert punt.status == "let_op"
    assert "Dranken" in punt.waarom


def test_een_dekking_onder_de_helft_wordt_actie():
    briefing = bf.marge(
        versheid=_versheid(),
        beeld=_margebeeld([("Brood", 5000.0, Decimal("40.0"))],
                          gewogen=Decimal("40.0"), dekking=Decimal("30.0"),
                          totaal=Decimal("10000.00"), gedekt=Decimal("3000.00")),
        invoer_fout=None,
    )
    assert briefing.punten[0].status == "actie"


def test_een_volledige_dekking_zwijgt():
    briefing = bf.marge(
        versheid=_versheid(),
        beeld=_margebeeld([("Brood", 5000.0, Decimal("40.0"))],
                          gewogen=Decimal("40.0"), dekking=Decimal("100.0"),
                          totaal=Decimal("5000.00"), gedekt=Decimal("5000.00")),
        invoer_fout=None,
    )
    assert briefing.punten == []


def test_kosten_boven_de_omzet_worden_gemeld_maar_niet_gecorrigeerd():
    briefing = bf.marge(
        versheid=_versheid(),
        beeld=_margebeeld([("Patisserie", 5000.0, Decimal("-3.0"))],
                          gewogen=Decimal("-3.0"), dekking=Decimal("100.0"),
                          totaal=Decimal("5000.00"), gedekt=Decimal("5000.00")),
        invoer_fout=None,
    )
    punt = briefing.punten[0]
    assert punt.status == "actie"
    assert punt.bedrag == "1"
    assert "Patisserie" in punt.waarom


def test_een_onleesbaar_kostenbestand_is_actie_met_de_foutmelding_erin():
    briefing = bf.marge(
        versheid=_versheid(), beeld=None,
        invoer_fout="de kolom pct ontbreekt.",
    )
    assert briefing.punten[0].status == "actie"
    assert "de kolom pct ontbreekt." in briefing.punten[0].waarom


# --- Prognose ---------------------------------------------------------------


def _prognose(**kw) -> bf.Briefing:
    kw.setdefault("versheid", _versheid())
    kw.setdefault("venster", _venster(["2026-08-15", "2026-08-16"]))
    kw.setdefault("bias", 0.0)
    kw.setdefault("banddekking", None)
    kw.setdefault("band_doel", None)
    kw.setdefault("kalenderdekking", None)
    kw.setdefault("sluitingsdekking", dt.date(2026, 12, 31))
    kw.setdefault("categorieen_overgeslagen", [])
    return bf.prognose(**kw)


def test_een_band_die_haar_doel_niet_haalt_is_een_punt():
    briefing = _prognose(banddekking=_banddekking([0.56, 0.74]), band_doel=0.80)
    punt = briefing.punten[0]
    assert punt.status == "let_op"
    assert "56,0 %" in punt.waarom
    assert punt.bedrag is None  # de dekking is geen bedrag


def test_een_band_die_haar_doel_haalt_is_het_enige_goede_nieuws():
    briefing = _prognose(banddekking=_banddekking([0.79, 0.85]), band_doel=0.80)
    assert [p.status for p in briefing.punten] == ["goed"]


def test_een_band_die_maar_op_sommige_stappen_haalt_is_geen_goed_nieuws():
    """Het oordeel hangt aan de ZWAKSTE horizonstap, niet aan de beste.

    Dit is de echte stand van 15 augustus 2026: 69% tot 82% op een doel van
    80%. De vorige versie keek naar `hoogste` en meldde "de band houdt wat ze
    belooft", terwijl ze in dezelfde zin toegaf dat de dekking bij 69% begon —
    en terwijl de toelichting op hetzelfde scherm het tegenovergestelde zei.
    Een band belooft haar dekking op elke stap.
    """
    briefing = _prognose(banddekking=_banddekking([0.69, 0.82]), band_doel=0.80)
    punt = briefing.punten[0]
    assert punt.status == "let_op"
    assert "69,0 %" in punt.waarom and "82,0 %" in punt.waarom
    assert "niet op elke horizonstap" in punt.kop


def test_een_gat_binnen_de_meetfout_is_geen_bevinding():
    """0,79 tegen een doel van 0,80 is kleiner dan de standaardfout van de
    meting zelf."""
    briefing = _prognose(banddekking=_banddekking([0.79]), band_doel=0.80)
    assert briefing.punten[0].status == "goed"


def test_een_kalender_die_niet_tot_het_einde_reikt_is_actie():
    briefing = _prognose(
        venster=_venster(["2026-08-15", "2026-08-16", "2026-08-17"]),
        kalenderdekking=dt.date(2026, 8, 15),
    )
    punt = briefing.punten[0]
    assert punt.status == "actie"
    assert punt.bedrag == "2"
    assert punt.soort == "aantal"
    assert "make vakanties" in punt.nodig


def test_een_kalender_die_ver_genoeg_reikt_zwijgt():
    briefing = _prognose(kalenderdekking=dt.date(2027, 8, 31))
    assert briefing.punten == []


def test_zonder_sluitingslijst_staat_de_aanname_in_de_briefing():
    briefing = _prognose(sluitingsdekking=None)
    punt = briefing.punten[0]
    assert punt.status == "let_op"
    assert "Lien" in punt.nodig


def test_een_sluitingslijst_die_te_kort_reikt_telt_de_onbekende_dagen():
    briefing = _prognose(
        venster=_venster(["2026-08-15", "2026-08-16", "2026-08-17"]),
        sluitingsdekking=dt.date(2026, 8, 16),
    )
    assert briefing.punten[0].bedrag == "1"


def test_een_systematische_scheefstand_wordt_gemeld():
    briefing = _prognose(bias=-0.06)
    punt = briefing.punten[0]
    assert punt.bedrag == "-6.0"
    assert punt.soort == "verschil"
    assert punt.richting == "neer"


def test_een_kleine_bias_zwijgt():
    briefing = _prognose(bias=bf.BIAS_DREMPEL / 2)
    assert briefing.punten == []


def test_een_ongemeten_bias_levert_geen_nul_op():
    briefing = _prognose(bias=None)
    assert briefing.punten == []


def test_een_leeg_venster_meldt_dat_er_niets_te_voorspellen_valt():
    briefing = _prognose(venster=_venster([]))
    assert len(briefing.punten) == 1
    assert briefing.punten[0].bedrag is None


def test_overgeslagen_categorieen_worden_geteld():
    briefing = _prognose(categorieen_overgeslagen=["Dranken", "Traiteur"])
    punt = briefing.punten[0]
    assert punt.bedrag == "2"
    assert "Traiteur" in punt.waarom


# --- Instellingen -----------------------------------------------------------


def test_een_wachter_die_alarm_slaat_draagt_zijn_eigen_meting():
    briefing = bf.instellingen(
        versheid=_versheid(), bronstanden=[],
        wachters=[Wachter("dubbele_sleutels", "fout",
                          "3 rijen komen twee keer voor.")],
        kostenmodel_ingevuld=True,
    )
    punt = briefing.punten[0]
    assert punt.status == "actie"
    assert "Dubbele rijen" in punt.kop
    assert "3 rijen komen twee keer voor." in punt.waarom


def test_alles_groen_levert_een_bevestiging_op():
    briefing = bf.instellingen(
        versheid=_versheid(),
        bronstanden=[Bronstand("odoo-kassa", GEMETEN_TOT, 100, "vers", "x")],
        wachters=[Wachter("drempelrand", "goed", "niets gevonden.")],
        kostenmodel_ingevuld=True,
    )
    assert [p.status for p in briefing.punten] == ["goed"]


def test_zonder_controles_is_er_geen_groen_licht():
    """Een controle die niet gedraaid heeft, is niet hetzelfde als een controle
    die slaagde."""
    briefing = bf.instellingen(versheid=_versheid(), bronstanden=[],
                               wachters=[], kostenmodel_ingevuld=True)
    assert briefing.punten == []


def test_een_ontbrekend_kostenmodel_wijst_naar_de_beheerder():
    briefing = bf.instellingen(versheid=_versheid(), bronstanden=[],
                               wachters=[], kostenmodel_ingevuld=False)
    punt = briefing.punten[0]
    assert punt.status == "actie"
    assert "Instellingen" in punt.nodig


# --- de aansluiting op de echte berekeningslaag -----------------------------


def test_de_motor_draait_op_wat_de_berekeningslaag_echt_levert():
    """De fixtures hierboven bouwen hun frames met de hand, en dan is een
    hernoemde kolom in `berekening.py` pas in de browser te zien. Deze test
    voedt de briefing met de echte uitkomsten van de echte functies."""
    from bakkerij import berekening as bk

    datums = pd.date_range("2026-04-01", "2026-08-14", freq="D")
    verkopen = pd.DataFrame([
        {"datum": d, "filiaal_id": "Kassa 1", "product_id": p,
         "product_naam": naam, "kanaal": "winkel", "aantal": 10.0,
         "omzet_excl_btw": basis + (300.0 if i % 37 == 0 and p == "p1" else 0.0)}
        for i, d in enumerate(datums)
        for p, naam, basis in (("p1", "Pistolet", 900.0), ("p2", "Boule", 200.0))
    ])
    kalender = pd.DataFrame({"datum": datums, "winkel_gemeten": True,
                             "winkel_open": True})

    open_verkopen = bk.open_verkopen(verkopen, kalender)
    dagtotalen = bk.dagtotalen(open_verkopen)
    tot = bk.peildatum(open_verkopen, "winkel")

    briefing = bf.overzicht(
        versheid=_versheid(),
        periode=bk.periodecontext(dagtotalen, tot, dagen=30),
        afwijkende=bk.afwijkende_dagen(dagtotalen, tot),
        bonritme=_bonritme(),
    )
    assert isinstance(briefing.als_dict(), dict)

    productbriefing = bf.producten(
        versheid=_versheid(),
        verschuiving=bk.productverschuiving(open_verkopen, tot, dagen=30),
    )
    assert isinstance(productbriefing.als_dict(), dict)


# --- de tweede taal ---------------------------------------------------------


def test_geen_enkele_tekst_valt_terug_op_het_nederlands():
    """De teller in `taal.py` vangt elke `t(...)` zonder Franse variant. Er
    staan al 63 onvertaalde teksten open; daar horen deze niet bij."""
    tl.ONVERTAALD.clear()
    with tl.in_taal("fr"):
        _alle_briefings()
    assert tl.ONVERTAALD == set()


def test_de_franse_briefing_draagt_dezelfde_cijfers():
    nl = _alle_briefings()
    tl.ONVERTAALD.clear()
    with tl.in_taal("fr"):
        fr = _alle_briefings()
    for briefing_nl, briefing_fr in zip(nl, fr, strict=True):
        assert [p.bedrag for p in briefing_nl.punten] == \
               [p.bedrag for p in briefing_fr.punten]
        assert [p.status for p in briefing_nl.punten] == \
               [p.status for p in briefing_fr.punten]
        for punt_nl, punt_fr in zip(briefing_nl.punten, briefing_fr.punten,
                                    strict=True):
            assert punt_nl.statuswoord != punt_fr.statuswoord


# --- het gedeelde punt ------------------------------------------------------
#
# Zie `BriefingPunt.gedeeld`. Het gaat om het rapport: dat zet de schermen
# achter elkaar, en zonder dit merk openen zes bladzijden met dezelfde alinea.


def test_elk_gemerkt_punt_staat_op_elk_scherm():
    """De eis waar het rapport op rekent, en de gevaarlijkste kant ervan.

    Het rapport toont een gemerkt punt in het eerste onderdeel en verbergt het
    in alle volgende. Dat is alleen veilig als élk scherm het punt draagt: een
    punt op vijf van de zes schermen verdwijnt uit een rapport dat met het
    zesde begint — een actiepunt dat stilletjes uit een document valt.

    Deze test kijkt naar de uitkomst en niet naar de functies die het merk
    vandaag zetten; een nieuw gemerkt punt op één scherm valt hier om.
    """
    briefings = _alle_briefings()
    gemerkt: dict[tuple[str, str], int] = {}
    for briefing in briefings:
        for punt in briefing.punten:
            if punt.gedeeld:
                sleutel = (punt.kop, punt.waarom)
                gemerkt[sleutel] = gemerkt.get(sleutel, 0) + 1

    assert gemerkt, "geen enkel punt is gemerkt; dan doet het rapport niets"
    for (kop, _waarom), n in gemerkt.items():
        assert n == len(briefings), (
            f"{kop!r} is als gedeeld gemerkt maar staat op {n} van de "
            f"{len(briefings)} schermen; in het rapport zou hij kunnen "
            "verdwijnen in plaats van één keer te verschijnen"
        )


def test_een_punt_op_twee_schermen_wordt_niet_gemerkt():
    """De andere kant van dezelfde grens: liever tweemaal dan nul keer.

    Het bronpunt over Deliveroo staat op Verkoopkanalen en op Instellingen, en
    herhaalt zich dus in een volledig rapport. Het krijgt het merk toch niet:
    een rapport dat met Dagoverzicht begint, zou het anders helemaal kwijt zijn.
    """
    per_tekst: dict[tuple[str, str], list[bool]] = {}
    for briefing in _alle_briefings():
        for punt in briefing.punten:
            per_tekst.setdefault((punt.kop, punt.waarom), []).append(punt.gedeeld)

    tweemaal = [k for k, v in per_tekst.items() if len(v) == 2]
    assert tweemaal, "de fixture bevat geen punt op precies twee schermen"
    for sleutel in tweemaal:
        assert not any(per_tekst[sleutel]), sleutel[0]


def test_een_scherm_eigen_punt_is_niet_gedeeld():
    """Het omgekeerde, want een merk op alles is hetzelfde als geen merk.

    Zonder deze kant zou `_als_gedeeld` op elk punt zetten de test hierboven
    even groen laten — en in het rapport zou dan de hele briefing van vijf van
    de zes schermen wegvallen.
    """
    eigen = [
        punt
        for briefing in _alle_briefings()
        for punt in briefing.punten
        if not punt.gedeeld
    ]
    assert eigen, "geen enkel punt is schermeigen; dan verdwijnt er te veel"
    koppen = {p.kop for p in eigen}
    # Drie voorbeelden die per definitie over één scherm gaan.
    assert any("marge" in k.lower() for k in koppen), koppen
    assert any("band" in k.lower() for k in koppen), koppen


def test_het_sluitingspunt_is_op_elk_scherm_hetzelfde_en_gemerkt():
    """Het punt uit `docs/open-punten.md`: 268 tekens, zesmaal in één rapport."""
    versheid = _versheid(
        sluiting=Sluitingsstand(
            dicht_sinds=dt.date(2026, 8, 1), dagen=14,
            reden="zomersluiting", eerste_open_dag=dt.date(2026, 8, 24),
        ),
    )
    briefing = bf.overzicht(
        versheid=versheid, periode=None, afwijkende=None, bonritme=None,
    )
    sluitingspunten = [p for p in briefing.punten if "gesloten" in p.kop.lower()]
    assert len(sluitingspunten) == 1
    assert sluitingspunten[0].gedeeld is True


def test_het_merk_overleeft_de_serialisatie_naar_het_contract():
    """`als_dict` is wat de UI leest; een veld dat daar wegvalt, bestaat niet."""
    briefing = bf.overzicht(
        versheid=_versheid(meetgat=_meetgat(9)),
        periode=None, afwijkende=None, bonritme=None,
    )
    d = briefing.als_dict()
    assert d["punten"], "geen punten om te toetsen"
    assert all("gedeeld" in p for p in d["punten"])
    assert any(p["gedeeld"] for p in d["punten"])
