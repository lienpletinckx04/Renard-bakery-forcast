"""De schoolvakantiekalender als data: lezen, valideren, vergelijken, wachten.

De regels die hier getoetst worden zijn de beslissing van 14 augustus 2026:
verversbaar, niet zelfwijzigend. Nieuwe toekomst gaat er automatisch in;
alles wat het verleden raakt, vraagt een mens.
"""

from __future__ import annotations

import datetime

import pandas as pd
import pytest

from bakkerij import canoniek
from bakkerij import contract as ct
from bakkerij.features import vakanties as vk
from bakkerij.features.calendar import (
    SCHOOLVAKANTIES_FR,
    SCHOOLVAKANTIES_VL,
    markeer_schoolvakanties,
)
from bakkerij.tijd import BRUSSEL

VANDAAG = datetime.date(2026, 8, 14)
BIJGEWERKT = datetime.datetime(2026, 8, 14, 6, 0, tzinfo=BRUSSEL)


# --- het meegeleverde bestand -------------------------------------------------

def _einde_lopend_schooljaar(vandaag: datetime.date) -> datetime.date:
    """31 augustus van het schooljaar waarin `vandaag` valt.

    Een schooljaar loopt van 1 september tot en met 31 augustus, dus de
    zomervakantie hoort nog bij het jaar dat afloopt.
    """
    jaar = vandaag.year + 1 if vandaag.month >= 9 else vandaag.year
    return datetime.date(jaar, 8, 31)


def test_meegeleverd_bestand_is_geldig_en_dekt_de_historiek():
    data = vk.lees()  # valideert impliciet
    assert set(data["regimes"]) >= set(vk.REGIMES)
    # De verkoophistoriek begint 2019-07-04; de kalender moet daar al staan.
    for regime in vk.REGIMES:
        tabel = vk.regime_tabel(regime)
        assert min(van for (van, _) in tabel.values()) <= "2019-07-04"

    # En vooruit: minstens het lopende schooljaar volledig.
    #
    # Deze grens komt van de klok en staat sinds 19 augustus 2026 niet meer
    # vastgeschreven. Dit is met opzet de enige klokafhankelijke test in de
    # suite. Overal elders is "vandaag" gif in een test, maar hier is de klok
    # juist het onderwerp: het bestand veroudert vanzelf, de code niet. Tot
    # 19 augustus stond hier een vaste datum (VL 31 aug 2027, FR 1 mei 2027).
    # Zo'n datum meet één keer iets en daarna niets meer: vanaf september 2027
    # zou de kalender het lopende schooljaar niet meer dekken terwijl de test
    # groen bleef, want de vaste grens ligt dan in het verleden. De test hoort
    # juist rood te worden op de dag dat `scripts/vakanties_ververs.py` had
    # moeten draaien -- dat is het hele nut van deze assert.
    einde = _einde_lopend_schooljaar(datetime.datetime.now(tz=BRUSSEL).date())
    assert vk.dekking_tot(vk.regime_tabel("VL")) >= einde
    # De FWB publiceert haar kalender met minder voorsprong dan Vlaanderen.
    # Voor FR volstaat daarom dekking tot en met de lentevakantie van hetzelfde
    # schooljaar; verder vooruit eisen zou een tekortkoming van de bron als een
    # fout van dit project rapporteren.
    assert vk.dekking_tot(vk.regime_tabel("FR")) >= einde.replace(month=5, day=1)


def test_geverifieerde_periodes_zijn_niet_verschoven():
    """De handmatig geverifieerde datums van 13 aug (A20) moeten de omzetting
    naar data overleefd hebben; de bron bevestigde ze, op één na."""
    assert SCHOOLVAKANTIES_VL["kerst_2024"] == ("2024-12-23", "2025-01-05")
    assert SCHOOLVAKANTIES_VL["zomer_2026"] == ("2026-07-01", "2026-08-31")
    # De ene correctie: de FWB-rentrée valt op 24 aug 2026, niet 1 september.
    assert SCHOOLVAKANTIES_FR["zomer_2026"] == ("2026-07-04", "2026-08-23")


def test_markeer_schoolvakanties_werkt_op_de_diepe_historiek():
    dagen = pd.DataFrame({"datum": pd.date_range("2020-07-01", "2020-07-05")})
    gemarkeerd = markeer_schoolvakanties(dagen, SCHOOLVAKANTIES_VL)
    assert gemarkeerd["schoolvakantie"].all()
    assert (gemarkeerd["vakantienaam"] == "zomer_2020").all()


# --- valideren ----------------------------------------------------------------

def _bestand(vl=None, fr=None) -> dict:
    basis = [{"naam": "kerst_2025", "van": "2025-12-22", "tot": "2026-01-04"}]
    return {"regimes": {"VL": vl if vl is not None else list(basis),
                        "FR": fr if fr is not None else list(basis)}}


def test_valideer_weigert_overlap_en_onzinnige_duur():
    with pytest.raises(ValueError, match="overlapt"):
        vk.valideer(_bestand(vl=[
            {"naam": "a", "van": "2025-12-22", "tot": "2026-01-04"},
            {"naam": "b", "van": "2026-01-01", "tot": "2026-01-11"},
        ]))
    with pytest.raises(ValueError, match="duur"):
        vk.valideer(_bestand(vl=[{"naam": "kort", "van": "2026-01-01",
                                  "tot": "2026-01-02"}]))
    with pytest.raises(ValueError, match="duur"):
        vk.valideer(_bestand(vl=[{"naam": "lang", "van": "2026-01-01",
                                  "tot": "2026-06-01"}]))
    with pytest.raises(ValueError, match="tweemaal"):
        vk.valideer(_bestand(vl=[
            {"naam": "x", "van": "2025-07-01", "tot": "2025-08-31"},
            {"naam": "x", "van": "2026-07-01", "tot": "2026-08-31"},
        ]))
    with pytest.raises(ValueError, match="ontbreekt of is leeg"):
        vk.valideer({"regimes": {"VL": _bestand()["regimes"]["VL"], "FR": []}})


# --- ophalen en normaliseren ---------------------------------------------------

def _api_record(van, tot, naam="Herfstvakantie", groep="BE-NL", nr="1"):
    return {"id": nr, "startDate": van, "endDate": tot,
            "name": [{"language": "NL", "text": naam}],
            "groups": [{"code": groep, "shortName": groep[-2:]}]}


def test_haal_periodes_normaliseert_filtert_en_ontdubbelt():
    aanroepen = []

    def nep_ophaler(url):
        aanroepen.append(url)
        return [
            _api_record("2026-11-02", "2026-11-08"),
            # zelfde record nogmaals: bloknaad-duplicaat, moet wegvallen
            _api_record("2026-11-02", "2026-11-08"),
            # eendagsrecord: geen vakantieregime
            _api_record("2026-11-15", "2026-11-15", naam="Dag van de Gemeenschap"),
            # Duitstalige Gemeenschap: bewust geen kandidaat
            _api_record("2026-11-02", "2026-11-07", groep="BE-DE", nr="2"),
            # onbekend vakantietype: niet stil laten vallen
            _api_record("2027-05-03", "2027-05-09", naam="Zomerse proefvakantie",
                        groep="BE-FR", nr="3"),
        ]

    per = vk.haal_periodes(datetime.date(2026, 9, 1), datetime.date(2027, 8, 31),
                           vandaag=VANDAAG, ophaler=nep_ophaler)
    assert len(aanroepen) == 1  # venster < 3 jaar: één blok
    assert [p.naam for p in per["VL"]] == ["herfst_2026"]
    assert per["VL"][0].bron and "openholidaysapi" in per["VL"][0].bron
    assert len(per["FR"]) == 1 and "2027" in per["FR"][0].naam


def test_haal_periodes_haalt_lange_vensters_in_blokken():
    aanroepen = []

    def nep_ophaler(url):
        aanroepen.append(url)
        return []

    vk.haal_periodes(datetime.date(2019, 7, 1), datetime.date(2027, 8, 31),
                     vandaag=VANDAAG, ophaler=nep_ophaler)
    assert len(aanroepen) >= 3  # ruim acht jaar past niet in één API-verzoek


# --- vergelijken: de kern van "verversbaar, niet zelfwijzigend" ----------------

VENSTER = {"venster_van": datetime.date(2019, 7, 1),
           "venster_tot": datetime.date(2027, 12, 31)}


def _p(naam, van, tot):
    return vk.Periode(naam, van, tot)


def test_nieuwe_toekomstige_periode_gaat_automatisch():
    w = vk.vergelijk([], [_p("herfst_2026", "2026-11-02", "2026-11-08")],
                     regime="VL", vandaag=VANDAAG, **VENSTER)
    assert [x.soort for x in w] == ["nieuw"] and w[0].automatisch


def test_nieuwe_periode_in_het_verleden_vraagt_een_mens():
    w = vk.vergelijk([_p("anker", "2026-07-01", "2026-08-31")],
                     [_p("anker", "2026-07-01", "2026-08-31"),
                      _p("herfst_2024", "2024-10-28", "2024-11-03")],
                     regime="VL", vandaag=VANDAAG, **VENSTER)
    assert [x.soort for x in w] == ["nieuw"]
    assert w[0].raakt_verleden and not w[0].automatisch


def test_wijziging_die_alleen_de_toekomst_raakt_gaat_automatisch():
    # 14 aug 2026: het einde van de zomer verschuift van 31 naar 23 aug.
    # De verschoven dagen (24-31 aug) liggen allemaal ná vandaag == 14 aug...
    w = vk.vergelijk([_p("zomer_2026", "2026-07-04", "2026-08-31")],
                     [_p("zomer_2026", "2026-07-04", "2026-08-23")],
                     regime="FR", vandaag=datetime.date(2026, 8, 14), **VENSTER)
    assert [x.soort for x in w] == ["gewijzigd"] and w[0].automatisch

    # ...maar wie dezelfde wijziging in september zou binnenkrijgen, herschrijft
    # gemeten dagen, en dat is handwerk.
    w = vk.vergelijk([_p("zomer_2026", "2026-07-04", "2026-08-31")],
                     [_p("zomer_2026", "2026-07-04", "2026-08-23")],
                     regime="FR", vandaag=datetime.date(2026, 9, 15), **VENSTER)
    assert not w[0].automatisch


def test_hernoemen_is_cosmetisch_en_gaat_automatisch():
    w = vk.vergelijk([_p("toussaint_2025", "2025-10-20", "2025-11-02")],
                     [_p("herfst_2025", "2025-10-20", "2025-11-02")],
                     regime="FR", vandaag=VANDAAG, **VENSTER)
    assert [x.soort for x in w] == ["hernoemd"] and w[0].automatisch


def test_vervallen_is_altijd_handwerk_en_alleen_binnen_de_brondekking():
    oud = [_p("zomer_2019", "2019-07-01", "2019-08-31"),
           _p("kerst_2025", "2025-12-22", "2026-01-04")]
    nieuw = [_p("herfst_2025", "2025-10-27", "2025-11-02"),
             _p("paas_2026", "2026-04-06", "2026-04-19")]
    w = vk.vergelijk(oud, nieuw, regime="VL", vandaag=VANDAAG, **VENSTER)
    # kerst_2025 ligt tussen twee teruggekregen periodes en ontbreekt: dat is
    # een echte schrapping. zomer_2019 ligt vóór de aantoonbare dekking van de
    # bron (die begint hier pas eind oktober 2025): afwezigheid zegt daar
    # niets, dus niet vervallen.
    vervallen = [x for x in w if x.soort == "vervallen"]
    assert [x.oud.naam for x in vervallen] == ["kerst_2025"]
    assert not vervallen[0].automatisch


def test_lege_bron_verklaart_nooit_alles_vervallen():
    oud = [_p("kerst_2025", "2025-12-22", "2026-01-04")]
    w = vk.vergelijk(oud, [], regime="VL", vandaag=VANDAAG, **VENSTER)
    assert w == []


def test_pas_toe_respecteert_de_grens_en_forceer_heft_haar_op():
    oud = [_p("zomer_2026", "2026-07-01", "2026-08-31")]
    wijzigingen = vk.vergelijk(
        oud,
        [_p("zomer_2026", "2026-07-01", "2026-08-31"),
         _p("herfst_2024", "2024-10-28", "2024-11-03"),   # verleden: weigeren
         _p("herfst_2026", "2026-11-02", "2026-11-08")],  # toekomst: toepassen
        regime="VL", vandaag=VANDAAG, **VENSTER)

    lijst, toegepast, geweigerd = vk.pas_toe(oud, wijzigingen)
    assert [p.naam for p in lijst] == ["zomer_2026", "herfst_2026"]
    assert len(toegepast) == 1 and len(geweigerd) == 1

    lijst, toegepast, geweigerd = vk.pas_toe(oud, wijzigingen, forceer=True)
    assert [p.naam for p in lijst] == ["herfst_2024", "zomer_2026", "herfst_2026"]
    assert not geweigerd


# --- de dekkingswacht in het contract ------------------------------------------

def _venster(dagen: int = 3) -> canoniek.Prognosevenster:
    kal = pd.DataFrame({
        "datum": pd.date_range("2026-06-01", "2026-07-31", freq="D").date,
        "winkel_gemeten": False,
        "winkel_open": False,
    })
    kal.loc[kal["datum"] <= datetime.date(2026, 6, 30),
            ["winkel_gemeten", "winkel_open"]] = True
    return canoniek.prognosevenster(kal, gemeten_tot="2026-06-30",
                                    vandaag="2026-06-30", horizon=dagen)


def _blik(datums) -> pd.DataFrame:
    return pd.DataFrame({"datum": pd.DatetimeIndex(datums),
                         "verwacht": [1000.0] * len(datums),
                         "onder": [900.0] * len(datums),
                         "boven": [1100.0] * len(datums)})


def test_dekkingswacht_meldt_een_te_korte_kalender():
    venster = _venster(3)  # doeldagen begin juli 2026
    a = ct.prognose(_blik(venster.dagen), bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    baseline_naam="test", wape=0.08, venster=venster,
                    kalenderdekking=datetime.date(2026, 7, 1))
    velden = {o["veld"]: o["reden"] for o in a["onbeschikbaar"]}
    assert "prognose.kalenderdekking" in velden
    assert "make vakanties" in velden["prognose.kalenderdekking"]


def test_dekkingswacht_zwijgt_zolang_de_kalender_ver_genoeg_reikt():
    venster = _venster(3)
    a = ct.prognose(_blik(venster.dagen), bron=["odoo"], bijgewerkt_op=BIJGEWERKT,
                    baseline_naam="test", wape=0.08, venster=venster,
                    kalenderdekking=datetime.date(2027, 8, 31))
    assert "prognose.kalenderdekking" not in [o["veld"] for o in a["onbeschikbaar"]]
