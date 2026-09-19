"""Tests voor het canonieke datamodel.

Alle fixtures zijn verzonnen. Geen enkele rij komt uit klantdata: deze tests
moeten kunnen draaien (en in de repo staan) zonder dat er ook maar iets van de
eindklant meereist.
"""
import datetime
from decimal import Decimal

import pandas as pd
import pytest

from bakkerij import canoniek
from bakkerij.sources.deliveroo_parse import Orderregel


def _winkel(rijen) -> pd.DataFrame:
    """rijen: (datum, filiaal, product_id, naam, aantal, omzet)."""
    return pd.DataFrame(
        [{"datum": datetime.date.fromisoformat(d), "filiaal_id": f,
          "product_id": p, "product_naam": n, "kanaal": "winkel",
          "aantal": a, "omzet_excl_btw": o}
         for d, f, p, n, a, o in rijen]
    )


def _deliveroo(rijen) -> pd.DataFrame:
    """rijen: (datum, filiaal, product_id, naam, aantal, omzet). Zelfde vorm
    als `_winkel`, maar op het kanaal deliveroo, voor tests die een tweede
    kanaal naast winkel nodig hebben."""
    return pd.DataFrame(
        [{"datum": datetime.date.fromisoformat(d), "filiaal_id": f,
          "product_id": p, "product_naam": n, "kanaal": "deliveroo",
          "aantal": a, "omzet_excl_btw": o}
         for d, f, p, n, a, o in rijen]
    )


# --- samenvoegen -----------------------------------------------------------

def test_bouw_verkopen_sorteert_en_bewaakt_kanalen():
    winkel = _winkel([("2024-03-06", "Kassa 1", "10", "Brood", 3, 9.0)])
    deliveroo = _deliveroo([("2024-03-05", "1", "7001", "Bestelling", 1, 4.30)])
    uit = canoniek.bouw_verkopen(winkel, deliveroo)
    assert list(uit.columns) == canoniek.KOLOMMEN
    assert list(uit["datum"]) == [datetime.date(2024, 3, 5),
                                  datetime.date(2024, 3, 6)]


def test_bouw_verkopen_weigert_onbekend_kanaal():
    fout = _winkel([("2024-03-06", "Kassa 1", "10", "Brood", 3, 9.0)])
    fout["kanaal"] = "ubereats"
    with pytest.raises(ValueError, match="ubereats"):
        canoniek.bouw_verkopen(fout)


def test_kanaalstatus_toont_deliveroo_als_onbeschikbaar_met_reden():
    winkel = _winkel([("2024-03-06", "Kassa 1", "10", "Brood", 3, 9.0)])
    status = {s["kanaal"]: s for s in canoniek.kanaalstatus(winkel)}
    assert status["winkel"]["beschikbaar"] is True
    assert status["deliveroo"]["beschikbaar"] is False
    assert "Partner Hub" in status["deliveroo"]["reden"]


# --- kalender: dicht is geen nul -------------------------------------------

def test_kalender_sluitingsdag_binnen_bereik_is_dicht_niet_nul():
    winkel = _winkel([
        ("2024-03-04", "Kassa 1", "10", "Brood", 3, 9.0),
        ("2024-03-06", "Kassa 1", "10", "Brood", 2, 6.0),
    ])
    kal = canoniek.bouw_kalender(winkel).set_index("datum")
    dicht = kal.loc[datetime.date(2024, 3, 5)]
    assert bool(dicht["winkel_gemeten"]) is True
    assert bool(dicht["winkel_open"]) is False
    # En de verkooptabel zelf bevat voor die dag géén rij (geen nulomzet).
    assert datetime.date(2024, 3, 5) not in set(winkel["datum"])


def test_kalender_buiten_gemeten_bereik_weten_we_niets():
    # Deliveroo loopt langer terug dan het Odoo-extract: die vroege dagen zijn
    # voor de winkel niet gemeten, dus ook niet 'dicht'.
    winkel = _winkel([("2024-03-04", "Kassa 1", "10", "Brood", 3, 9.0)])
    deliveroo = _deliveroo([("2024-02-01", "1", "7001", "Bestelling", 1, 5.99)])
    kal = canoniek.bouw_kalender(canoniek.bouw_verkopen(winkel, deliveroo))
    kal = kal.set_index("datum")
    vroeg = kal.loc[datetime.date(2024, 2, 1)]
    assert bool(vroeg["winkel_gemeten"]) is False


# --- kalender: een losse bon maakt van een sluitingsdag geen openingsdag ----
#
# Gemeten op 12 augustus 2026: vijf dagen binnen het gemeten bereik hadden 1 tot
# 6 bonregels en € 0,03 tot € 54,18 omzet, allemaal middenin een sluitings-
# periode. De oude regel ("minstens één kassaverkoop") noemde die dagen open.

MAANDAGEN_2024 = ["2024-01-01", "2024-01-08", "2024-01-15", "2024-01-22",
                  "2024-01-29", "2024-02-05", "2024-02-12", "2024-02-19",
                  "2024-02-26", "2024-03-04"]


def _maandagen(omzetten) -> pd.DataFrame:
    """Eén rij per maandag, met de opgegeven dagomzet. Zoveel maandagen als
    er omzetten zijn, zodat de mediaan per weekdag betekenis heeft."""
    return _winkel([(d, "Kassa 1", "10", "Brood", 1, o)
                    for d, o in zip(MAANDAGEN_2024, omzetten)])


def test_kalender_sluitingsdag_met_losse_bon_is_toch_dicht():
    # Negen normale maandagen en één met € 0,50: dat is een sluitingsdag waar
    # één bon op is aangeslagen, niet een dag met bijna geen vraag naar brood.
    winkel = _maandagen([1000.0] * 9 + [0.50])
    kal = canoniek.bouw_kalender(winkel).set_index("datum")
    stille = kal.loc[datetime.date(2024, 3, 4)]
    assert bool(stille["winkel_gemeten"]) is True
    assert bool(stille["winkel_open"]) is False
    # De negen andere maandagen blijven onaangeroerd open.
    assert bool(kal.loc[datetime.date(2024, 1, 8), "winkel_open"]) is True


def test_kalender_laat_een_lage_maar_echte_dag_open():
    # 70% van de mediaan is een slappe maandag, geen sluiting. De gemeten
    # scheiding is ruim: echte dagen zaten op >= 0,67, sluitingsdagen <= 0,004.
    winkel = _maandagen([1000.0] * 9 + [700.0])
    kal = canoniek.bouw_kalender(winkel).set_index("datum")
    assert bool(kal.loc[datetime.date(2024, 3, 4), "winkel_open"]) is True


def test_drempel_valt_weg_bij_te_weinig_dagen_per_weekdag():
    # Vier maandagen is geen mediaan. Dan geldt weer 'er was verkoop', want een
    # drempel op vier waarnemingen zou dagen wegsnijden op basis van ruis.
    winkel = _maandagen([1000.0, 1000.0, 1000.0, 0.50])
    kal = canoniek.bouw_kalender(winkel).set_index("datum")
    assert bool(kal.loc[datetime.date(2024, 1, 22), "winkel_open"]) is True


def test_alleen_open_dagen_snijdt_de_losse_bon_weg_maar_spaart_deliveroo():
    winkel = _maandagen([1000.0] * 9 + [0.50])
    # Deliveroo verkoopt op een dag dat de winkel dicht is: dat blijft staan,
    # want een winkelsluiting zegt niets over het Deliveroo-kanaal.
    deliveroo = _deliveroo([("2024-03-04", "1", "7001", "Bestelling", 1, 5.99)])
    verkopen = canoniek.bouw_verkopen(winkel, deliveroo)
    kal = canoniek.bouw_kalender(verkopen)
    uit = canoniek.alleen_open_dagen(verkopen, kal)

    winkelrijen = uit[uit["kanaal"] == "winkel"]
    assert len(winkelrijen) == 9
    assert datetime.date(2024, 3, 4) not in set(winkelrijen["datum"])
    assert len(uit[uit["kanaal"] == "deliveroo"]) == 1
    # En de feitentabel zelf is niet aangetast: de bon van € 0,50 staat er nog.
    assert len(verkopen[verkopen["kanaal"] == "winkel"]) == 10


def test_uiteenlopende_datumtypes_falen_luid_in_plaats_van_stil():
    """De gevaarlijkste vorm van deze functie is niet een fout maar een leegte.

    `pd.Timestamp` erft van `datetime.date` maar hasht anders, dus een set van
    `date` vindt nooit een `Timestamp`. Loopt de ene kant als het ene type
    binnen en de andere als het andere, dan matcht er níéts en verdwijnt het
    volledige kanaal winkel — zonder foutmelding, met tabellen die gewoon
    kloppen en alleen leeg zijn.
    """
    winkel = _maandagen([1000.0] * 3)
    kal = canoniek.bouw_kalender(winkel)
    # De kalender op Timestamp zetten terwijl de verkopen `date` dragen.
    scheef = kal.copy()
    scheef["datum"] = pd.to_datetime(scheef["datum"])

    with pytest.raises(TypeError, match="Datumtypes lopen uiteen"):
        canoniek.alleen_open_dagen(winkel, scheef)


def test_kalender_kent_belgische_feestdagen():
    winkel = _winkel([
        ("2024-12-20", "Kassa 1", "10", "Brood", 3, 9.0),
        ("2024-12-27", "Kassa 1", "10", "Brood", 2, 6.0),
    ])
    kal = canoniek.bouw_kalender(winkel).set_index("datum")
    assert bool(kal.loc[datetime.date(2024, 12, 25), "feestdag"]) is True


# --- kalender: overloop voorbij de laatste meting ---------------------------

def test_kalender_loopt_door_voorbij_de_laatste_meting():
    """Zonder overloop bestaat er geen kalenderrij voor een toekomstige dag, en
    kan de prognose niet nagaan of de winkel dan open is."""
    winkel = _winkel([("2024-03-04", "Kassa 1", "10", "Brood", 3, 9.0)])
    kal = canoniek.bouw_kalender(winkel, vooruit=10).set_index("datum")

    assert kal.index.max() == datetime.date(2024, 3, 14)
    later = kal.loc[datetime.date(2024, 3, 14)]
    # Niet gemeten, dus ook niet 'dicht' — maar de datumkenmerken zijn gevuld.
    assert bool(later["winkel_gemeten"]) is False
    assert bool(later["winkel_open"]) is False
    assert later["weekdagnaam"] == "donderdag"
    # En de standaard laat de kalender ruim vooruit lopen.
    standaard = canoniek.bouw_kalender(winkel)
    assert len(standaard) == 1 + canoniek.VOORUIT_DAGEN


def test_kalender_zonder_overloop_stopt_op_de_laatste_meting():
    winkel = _winkel([("2024-03-04", "Kassa 1", "10", "Brood", 3, 9.0)])
    kal = canoniek.bouw_kalender(winkel, vooruit=0)
    assert list(kal["datum"]) == [datetime.date(2024, 3, 4)]


# --- de horizonregel van de prognose ---------------------------------------

def _kalender_met(rijen) -> pd.DataFrame:
    """Een minimale kalender: (datum, winkel_gemeten, winkel_open)."""
    return pd.DataFrame(
        [{"datum": datetime.date.fromisoformat(d), "winkel_gemeten": g,
          "winkel_open": o}
         for d, g, o in rijen]
    )


def test_prognosevenster_slaat_gemeten_gesloten_dagen_over_maar_niet_de_toekomst():
    """De kern van bevinding 1, in één test.

    De kalender bevat drie soorten dagen: gemeten en open, gemeten en gesloten
    (een sluitingsperiode), en niet gemeten (de toekomst). Alleen de tweede soort
    mag wegvallen. Filteren op alleen `winkel_open` zou ook de derde soort
    wegsnijden — en dat is precies de valkuil, want dan blijft er niets over.
    """
    kal = _kalender_met(
        # gemeten en open t/m 20 mei
        [(f"2026-05-{d:02d}", True, True) for d in range(18, 21)]
        # gemeten sluiting: 21 t/m 24 mei
        + [(f"2026-05-{d:02d}", True, False) for d in range(21, 25)]
        # voorbij het gemeten bereik: onbekend
        + [(f"2026-05-{d:02d}", False, False) for d in range(25, 32)]
    )
    venster = canoniek.prognosevenster(
        kal, gemeten_tot="2026-05-20", vandaag="2026-05-20", horizon=3,
    )

    # Start op 21 mei (de dag na de meting), maar 21 t/m 24 mei zijn gesloten:
    # de drie dagen die overblijven zijn 25, 26 en 27 mei.
    assert venster.start == datetime.date(2026, 5, 21)
    assert [d.date() for d in venster.dagen] == [
        datetime.date(2026, 5, 25), datetime.date(2026, 5, 26),
        datetime.date(2026, 5, 27),
    ]
    assert venster.overgeslagen == tuple(
        datetime.date(2026, 5, d) for d in range(21, 25)
    )
    assert venster.buiten_kalender == ()
    assert venster.meetgat is None


def test_prognosevenster_begint_nooit_in_het_verleden():
    """Het startpunt: max(laatste meting + 1, vandaag).

    Loopt het extract achter, dan mag het scherm geen week voorspellen die al
    voorbij is. Het gat tussen de twee wordt geteld naar oorzaak.
    """
    kal = _kalender_met(
        [("2026-07-31", True, True)]
        + [(f"2026-08-{d:02d}", True, False) for d in range(1, 8)]   # zomersluiting
        + [(f"2026-08-{d:02d}", False, False) for d in range(8, 21)]  # niet gemeten
    )
    venster = canoniek.prognosevenster(
        kal, gemeten_tot="2026-07-31", vandaag="2026-08-12", horizon=7,
    )

    assert venster.start == datetime.date(2026, 8, 12)
    assert [d.date() for d in venster.dagen] == [
        datetime.date(2026, 8, d) for d in range(12, 19)
    ]
    # De zomersluiting ligt vóór het startpunt en wordt dus niet 'overgeslagen'
    # maar gemeld als meetgat: 1 t/m 11 augustus, waarvan zeven gemeten gesloten.
    assert venster.overgeslagen == ()
    gat = venster.meetgat
    assert (gat.van, gat.tot, gat.dagen) == (
        datetime.date(2026, 8, 1), datetime.date(2026, 8, 11), 11,
    )
    assert (gat.gemeten_gesloten, gat.gepland_dicht, gat.niet_ingeladen) == (
        7, 0, 4,
    )


def test_prognosevenster_meldt_dagen_zonder_kalenderrij():
    """Loopt de kalender niet ver genoeg door, dan zijn die dagen onbekend en
    gaan ze mee — maar het venster zegt van hoeveel dagen dat geldt."""
    kal = _kalender_met([("2026-05-20", True, True)])
    venster = canoniek.prognosevenster(
        kal, gemeten_tot="2026-05-20", vandaag="2026-05-20", horizon=2,
    )
    assert len(venster.dagen) == 2
    assert venster.buiten_kalender == (datetime.date(2026, 5, 21),
                                       datetime.date(2026, 5, 22))


def test_prognosevenster_zonder_gat_als_de_meting_van_gisteren_is():
    kal = _kalender_met([("2026-05-20", True, True), ("2026-05-21", False, False)])
    venster = canoniek.prognosevenster(
        kal, gemeten_tot="2026-05-20", vandaag="2026-05-21", horizon=1,
    )
    assert venster.meetgat is None
    assert venster.start == datetime.date(2026, 5, 21)


def test_prognosevenster_op_echte_kalender_uit_bouw_kalender():
    """Dezelfde regel, nu op de kalender zoals het platform hem écht bouwt.

    Dit is de productiesituatie van augustus 2026: negen weken normale verkoop,
    daarna een sluitingsperiode waarop toch een losse bon is aangeslagen. Die
    dagen liggen binnen het gemeten bereik (er staat een bonregel) en zijn door
    DREMPEL_OPEN als gesloten gemarkeerd, dus het gemeten bereik loopt door ná de
    laatste open dag. Precies daar sloeg de oude pd.date_range de mist in.
    """
    normaal = pd.date_range("2026-03-23", "2026-05-24", freq="D")   # negen weken
    winkel = _winkel(
        [(d.date().isoformat(), "Kassa 1", "10", "Brood", 1, 1000.0)
         for d in normaal]
        + [(f"2026-05-{d}", "Kassa 1", "10", "Brood", 1, 0.50) for d in (25, 26, 27)]
    )
    kal = canoniek.bouw_kalender(winkel).set_index("datum")
    assert bool(kal.loc[datetime.date(2026, 5, 25), "winkel_gemeten"]) is True
    assert bool(kal.loc[datetime.date(2026, 5, 25), "winkel_open"]) is False

    venster = canoniek.prognosevenster(
        kal.reset_index(), gemeten_tot="2026-05-24", vandaag="2026-05-24", horizon=3,
    )
    # 25 t/m 27 mei zijn gemeten en gesloten: die vallen weg. De prognose gaat
    # over 28 t/m 30 mei, dagen die de kalender dank zij de overloop wél kent.
    assert venster.overgeslagen == (datetime.date(2026, 5, 25),
                                    datetime.date(2026, 5, 26),
                                    datetime.date(2026, 5, 27))
    assert [d.date() for d in venster.dagen] == [
        datetime.date(2026, 5, 28), datetime.date(2026, 5, 29),
        datetime.date(2026, 5, 30),
    ]
    assert venster.buiten_kalender == ()


def test_prognosevenster_weigert_een_negatieve_horizon():
    kal = _kalender_met([("2026-05-20", True, True)])
    with pytest.raises(ValueError, match="horizon"):
        canoniek.prognosevenster(kal, gemeten_tot="2026-05-20",
                                 vandaag="2026-05-20", horizon=-1)


# --- het meetgat en de sluitingsstand ---------------------------------------
#
# De aanleiding staat in `canoniek.Meetgat`: tijdens de zomersluiting van 2026
# telde het meetgat elke ongemeten dag als achterstand, ook de dagen waarvan de
# kalender wist dat de bakkerij dicht was. Deze twee groepjes tests leggen het
# onderscheid vast, want het is het verschil tussen "de synchronisatie hapert"
# en "er was niets te verkopen".


def _zomersluiting() -> pd.DataFrame:
    """De gemeten toestand van 18 augustus 2026, in de vorm van de echte kalender.

    Laatste open dag 31 juli; 1 t/m 7 augustus gemeten en gesloten (er stond een
    losse bon op, dus binnen het gemeten bereik en door DREMPEL_OPEN dicht);
    8 t/m 23 augustus niet gemeten. Alle sluitingsdagen zijn vooraf aangekondigd.
    Vanaf 24 augustus is de zaak weer open.
    """
    dicht = {datetime.date(2026, 8, d) for d in range(1, 24)}
    rijen = []
    for d in pd.date_range("2026-07-25", "2026-09-05", freq="D"):
        dag = d.date()
        gemeten = dag <= datetime.date(2026, 8, 7)
        rijen.append({
            "datum": dag,
            "winkel_gemeten": gemeten,
            "winkel_open": gemeten and dag not in dicht,
            "gepland_dicht": dag in dicht,
            "gepland_dicht_reden": "Jaarlijkse sluiting" if dag in dicht else "",
        })
    return pd.DataFrame(rijen)


def test_meetgat_rekent_een_aangekondigde_sluiting_niet_als_achterstand():
    """De fout van 18 augustus 2026, in één test.

    1 t/m 17 augustus zit in het gat: zeven dagen gemeten en gesloten, tien
    dagen niet gemeten. Die tien staan alle tien als `gepland_dicht` in de
    kalender, dus er is geen enkele dag achterstand.
    """
    venster = canoniek.prognosevenster(
        _zomersluiting(), gemeten_tot="2026-07-31", vandaag="2026-08-18",
        horizon=7,
    )
    gat = venster.meetgat
    assert (gat.van, gat.tot, gat.dagen) == (
        datetime.date(2026, 8, 1), datetime.date(2026, 8, 17), 17,
    )
    assert gat.gemeten_gesloten == 7
    assert gat.gepland_dicht == 10
    assert gat.niet_ingeladen == 0


def test_meetgat_telt_een_onverklaarde_dag_wel_als_achterstand():
    """Dezelfde sluiting, maar de lijst kent 15 t/m 17 augustus niet. Drie dagen
    die niemand verklaart zijn dan wél achterstand — en de andere veertien niet."""
    kal = _zomersluiting()
    vergeten = kal["datum"].map(
        lambda d: datetime.date(2026, 8, 15) <= d <= datetime.date(2026, 8, 17)
    )
    kal.loc[vergeten, "gepland_dicht"] = False
    kal.loc[vergeten, "gepland_dicht_reden"] = ""

    gat = canoniek.prognosevenster(
        kal, gemeten_tot="2026-07-31", vandaag="2026-08-18", horizon=7,
    ).meetgat
    assert (gat.gemeten_gesloten, gat.gepland_dicht, gat.niet_ingeladen) == (
        7, 7, 3,
    )


def test_de_meting_gaat_voor_op_de_aankondiging_in_het_meetgat():
    """Een dag die gemeten is en dicht bleek, telt als gemeten — ook als er een
    sluiting voor aangekondigd stond. Zelfde voorrang als in prognosevenster."""
    gat = canoniek.prognosevenster(
        _zomersluiting(), gemeten_tot="2026-07-31", vandaag="2026-08-08",
        horizon=7,
    ).meetgat
    # 1 t/m 7 augustus: alle zeven gemeten én aangekondigd, en ze staan één keer
    # in het bakje van de meting.
    assert gat.dagen == 7
    assert (gat.gemeten_gesloten, gat.gepland_dicht, gat.niet_ingeladen) == (
        7, 0, 0,
    )


def test_sluitingsstand_wijst_het_begin_en_de_eerste_open_dag_aan():
    stand = canoniek.sluitingsstand(_zomersluiting(), vandaag="2026-08-18")
    assert stand is not None
    assert stand.dicht_sinds == datetime.date(2026, 8, 1)
    assert stand.dagen == 18
    assert stand.reden == "Jaarlijkse sluiting"
    assert stand.eerste_open_dag == datetime.date(2026, 8, 24)


def test_sluitingsstand_zwijgt_op_een_dag_dat_de_zaak_open_hoort_te_zijn():
    """24 augustus is de eerste open dag; dan is er geen sluiting om te melden."""
    assert canoniek.sluitingsstand(_zomersluiting(), vandaag="2026-08-24") is None


def test_sluitingsstand_verzint_geen_openingsdag_voorbij_de_kalender():
    """Loopt de kalender niet verder dan de sluiting, dan is de eerste open dag
    onbekend — en onbekend is iets anders dan morgen (harde regel 8)."""
    kal = _zomersluiting()
    kal = kal[kal["datum"] <= datetime.date(2026, 8, 20)]
    stand = canoniek.sluitingsstand(kal, vandaag="2026-08-18")
    assert stand is not None
    assert stand.dicht_sinds == datetime.date(2026, 8, 1)
    assert stand.eerste_open_dag is None


def test_sluitingsstand_zonder_kolom_gepland_dicht_kijkt_alleen_naar_de_meting():
    """Zonder sluitingskennis blijft alleen de gemeten sluiting over, en de dagen
    erna zijn onbekend en dus geen sluiting."""
    kal = _kalender_met(
        [(f"2026-08-{d:02d}", True, True) for d in (5, 6)]
        + [(f"2026-08-{d:02d}", True, False) for d in (7, 8, 9)]
        + [(f"2026-08-{d:02d}", False, False) for d in (10, 11)]
    )
    stand = canoniek.sluitingsstand(kal, vandaag="2026-08-09")
    assert stand is not None
    assert (stand.dicht_sinds, stand.dagen, stand.reden) == (
        datetime.date(2026, 8, 7), 3, "",
    )
    assert stand.eerste_open_dag == datetime.date(2026, 8, 10)
    # Eén dag later valt vandaag buiten het gemeten bereik: niets weten is geen
    # sluiting, dus er is geen sluitingsstand.
    assert canoniek.sluitingsstand(kal, vandaag="2026-08-10") is None


# --- laad_bonnen en laad_uren ------------------------------------------------

def test_laad_bonnen_leest_en_controleert_de_kolommen(tmp_path):
    pad = tmp_path / "bonnen.csv"
    pad.write_text("datum,filiaal_id,bonnen\n2026-03-01,Kassa 1,412\n")
    df = canoniek.laad_bonnen(pad)
    assert list(df.columns) == canoniek.BONNEN_KOLOMMEN
    assert df.loc[0, "datum"] == datetime.date(2026, 3, 1)
    assert df.loc[0, "bonnen"] == 412


def test_laad_bonnen_weigert_een_onvolledig_bestand(tmp_path):
    pad = tmp_path / "bonnen.csv"
    pad.write_text("datum,bonnen\n2026-03-01,412\n")
    with pytest.raises(ValueError, match="mist kolommen"):
        canoniek.laad_bonnen(pad)


def test_laad_uren_leest_en_controleert_de_kolommen(tmp_path):
    pad = tmp_path / "uren.csv"
    pad.write_text(
        "datum,product_id,eerste_uur,laatste_uur,bonnen\n2026-03-01,7,7,16,25\n"
    )
    df = canoniek.laad_uren(pad)
    assert list(df.columns) == canoniek.UREN_KOLOMMEN
    assert df.loc[0, "laatste_uur"] == 16


def test_laad_uren_weigert_een_onvolledig_bestand(tmp_path):
    pad = tmp_path / "uren.csv"
    pad.write_text("datum,product_id\n2026-03-01,7\n")
    with pytest.raises(ValueError, match="mist kolommen"):
        canoniek.laad_uren(pad)


# --- geplande sluitingen in het prognosevenster (14 augustus 2026) -----------
#
# De fout die deze tests vastpinnen: de horizonregel sloeg alleen dagen over die
# GEMETEN én dicht waren, en een toekomstige dag is per definitie niet gemeten.
# Gevolg op het scherm: een omzetverwachting voor een week waarin de zaak
# aangekondigd dicht is. De kolom `gepland_dicht` bestond al (uit de agenda);
# niets keek ernaar.


def _kalender_met_sluiting(rijen):
    """(datum, gemeten, open, gepland_dicht, reden) -> kalender."""
    return pd.DataFrame([
        {"datum": datetime.date.fromisoformat(datum), "winkel_gemeten": gemeten,
         "winkel_open": open_, "gepland_dicht": dicht,
         "gepland_dicht_reden": reden}
        for datum, gemeten, open_, dicht, reden in rijen
    ])


def test_prognosevenster_slaat_aangekondigde_sluitingen_over():
    """De week van 17 augustus is dicht; de prognose schuift naar erna."""
    kal = _kalender_met_sluiting(
        [(f"2026-08-{d:02d}", True, True, False, "") for d in range(10, 15)]
        + [(f"2026-08-{d:02d}", False, False, True, "Zomersluiting")
           for d in range(17, 24)]
        + [(f"2026-08-{d:02d}", False, False, False, "") for d in range(24, 29)]
    )
    venster = canoniek.prognosevenster(
        kal, gemeten_tot="2026-08-14", vandaag="2026-08-17", horizon=3,
    )

    gekozen = [d.date() for d in venster.dagen]
    assert gekozen == [datetime.date(2026, 8, 24), datetime.date(2026, 8, 25),
                       datetime.date(2026, 8, 26)]
    assert len(venster.gepland_gesloten) == 7
    assert venster.gepland_gesloten[0] == (datetime.date(2026, 8, 17),
                                           "Zomersluiting")
    # Een aangekondigde sluiting is een ander verhaal dan een gemeten sluiting
    # en hoort dus niet in dezelfde lijst.
    assert venster.overgeslagen == ()


def test_de_meting_gaat_voor_op_de_aankondiging():
    """Stond er een sluiting gepland en verkocht de kassa toch, dan is de dag open.

    Die tegenspraak hoort in `afwijkingen()` en niet in een stille keuze hier.
    """
    kal = _kalender_met_sluiting([
        ("2026-08-10", True, True, False, ""),
        ("2026-08-11", True, True, True, "Zou dicht zijn"),
        ("2026-08-12", False, False, False, ""),
    ])
    venster = canoniek.prognosevenster(
        kal, gemeten_tot="2026-08-10", vandaag="2026-08-10", horizon=2,
    )
    gekozen = [d.date() for d in venster.dagen]
    assert datetime.date(2026, 8, 11) in gekozen
    assert venster.gepland_gesloten == ()


def test_zonder_de_kolom_verandert_er_niets():
    """Geen agenda en geen lijst: het oude gedrag, ongewijzigd."""
    kal = _kalender_met(
        [(f"2026-08-{d:02d}", True, True) for d in range(10, 15)]
        + [(f"2026-08-{d:02d}", False, False) for d in range(15, 22)]
    )
    venster = canoniek.prognosevenster(
        kal, gemeten_tot="2026-08-14", vandaag="2026-08-14", horizon=3,
    )
    assert len(venster.dagen) == 3
    assert venster.gepland_gesloten == ()


def test_een_boolkolom_uit_een_csv_wordt_niet_verkeerd_gelezen():
    """`astype(bool)` op de string "False" geeft True, en dat is een stille ramp.

    De kalender gaat via canoniek_kalender.csv. Eén NaN of één handmatige
    aanpassing maakt er een object-kolom van, en dan zou elke dag als gesloten
    gelden en verdween de hele prognose zonder foutmelding.
    """
    kal = _kalender_met(
        [(f"2026-08-{d:02d}", True, True) for d in range(10, 15)]
        + [(f"2026-08-{d:02d}", False, False) for d in range(15, 22)]
    )
    kal["gepland_dicht"] = "False"          # zoals een CSV hem kan teruggeven
    kal["gepland_dicht_reden"] = ""
    venster = canoniek.prognosevenster(
        kal, gemeten_tot="2026-08-14", vandaag="2026-08-14", horizon=3,
    )
    assert len(venster.dagen) == 3
    assert venster.gepland_gesloten == ()


def test_winkel_open_en_gemeten_uit_een_csv_worden_niet_verkeerd_gelezen():
    """Dezelfde val als hierboven, maar op de twee kolommen die alles dragen.

    `gepland_dicht` was op 14 aug 2026 al afgeschermd; `winkel_open` en
    `winkel_gemeten` niet, terwijl juist zij onder de hele berekeningslaag
    liggen: de openingsfilter van `alleen_open_dagen`, en de dict van
    `_status_per_dag` die de bronwachters, de censureringsdrempel, de
    sluitingsstand en het prognosevenster voedt. Kwamen ze ooit als
    object-kolom binnen — één NaN of één handmatige regel in
    canoniek_kalender.csv volstaat — dan is `"False"` een niet-lege string en
    telt élke dag als open. Sinds 19 aug 2026 lopen beide door `als_bool`.

    De test kiest bewust strings die het mis zouden laten gaan: zonder de
    vangrail zijn de vier gesloten dagen hieronder allemaal "open".
    """
    rijen = (
        [(f"2026-05-{d:02d}", "True", "True") for d in range(18, 21)]
        + [(f"2026-05-{d:02d}", "True", "False") for d in range(21, 25)]
    )
    kal = _kalender_met(rijen)
    # Anders meet de test niets. Welk niet-bool dtype pandas er precies van
    # maakt (object, of sinds pandas 3 een StringDtype) doet er niet toe: het
    # gaat erom dát het geen bool is, want dan slaat `als_bool` niet over.
    assert kal["winkel_open"].dtype != bool
    assert kal["winkel_gemeten"].dtype != bool

    # 1. De openingsfilter: de vier gesloten dagen horen eruit te vallen.
    verkopen = pd.DataFrame(
        [{"datum": datetime.date.fromisoformat(d), "filiaal_id": "1",
          "product_id": "7", "product_naam": "Brood", "kanaal": "winkel",
          "aantal": 5.0, "omzet_excl_btw": 100.0}
         for d, _, _ in rijen]
    )
    over = canoniek.alleen_open_dagen(verkopen, kal)
    assert sorted(over["datum"].unique()) == [
        datetime.date(2026, 5, 18),
        datetime.date(2026, 5, 19),
        datetime.date(2026, 5, 20),
    ]

    # 2. De statusdict, via de sluitingsstand: op 24 mei loopt de zaak sinds
    #    21 mei dicht. Zonder de vangrail is er geen enkele gesloten dag en
    #    zwijgt deze functie — precies het stille gat waar het om gaat.
    stand = canoniek.sluitingsstand(kal, vandaag="2026-05-24")
    assert stand is not None
    assert stand.dicht_sinds == datetime.date(2026, 5, 21)
    assert stand.dagen == 4


def test_een_sluiting_zonder_kalenderrij_valt_niet_ook_in_buiten_kalender():
    """Overgeslagen is overgeslagen; hij is niet 'als onbekend meegenomen'."""
    kal = _kalender_met_sluiting(
        [(f"2026-08-{d:02d}", True, True, False, "") for d in range(10, 15)]
        + [("2026-08-15", False, False, True, "Feestdag")]
    )
    venster = canoniek.prognosevenster(
        kal, gemeten_tot="2026-08-14", vandaag="2026-08-14", horizon=2,
    )
    assert datetime.date(2026, 8, 15) not in venster.buiten_kalender
    assert venster.gepland_gesloten == ((datetime.date(2026, 8, 15), "Feestdag"),)


# --- Deliveroo -------------------------------------------------------------
#
# De Orders-export draagt per bestelling een datum, een vestiging, een
# subtotaal en een commissie. Wat hier getest wordt is de omzetting naar de
# canonieke vorm en naar de kanaalkost, niet het lezen zelf (dat staat in
# test_deliveroo_parse.py).



def _order(datum, store, nr, subtotaal, commissie) -> Orderregel:
    return Orderregel(datum=datetime.date.fromisoformat(datum), store_id=store,
                      order_id=nr, subtotaal=Decimal(subtotaal),
                      commissie=Decimal(commissie),
                      btw_op_commissie=Decimal(0))


def test_orders_naar_canoniek_telt_per_dag_per_vestiging_en_neemt_netto():
    """Twee bestellingen op één dag in Elsene, één in Ukkel: twee rijen, het
    aantal is het aantal bestellingen, de omzet is subtotaal min commissie."""
    regels = [
        _order("2026-09-01", "Renard Bakery Ixelles", "1", "20.00", "4.00"),
        _order("2026-09-01", "Renard Bakery Ixelles", "2", "30.00", "6.00"),
        _order("2026-09-01", "Renard Bakery Uccle", "1", "10.00", "2.00"),
    ]
    uit = canoniek.orders_naar_canoniek(regels)
    assert list(uit.columns) == canoniek.KOLOMMEN
    assert len(uit) == 2
    elsene = uit[uit["filiaal_id"] == "Renard Bakery Ixelles"].iloc[0]
    assert elsene["kanaal"] == "deliveroo"
    assert elsene["product_id"] == canoniek.DELIVEROO_PRODUCT_ID
    assert elsene["aantal"] == 2.0
    assert elsene["omzet_excl_btw"] == 40.00  # 50 bruto - 10 commissie
    ukkel = uit[uit["filiaal_id"] == "Renard Bakery Uccle"].iloc[0]
    assert ukkel["omzet_excl_btw"] == 8.00


def test_orders_naar_canoniek_past_in_bouw_verkopen_naast_winkel():
    winkel = _winkel([("2026-09-01", "Ixelles Kassa 1", "10", "Brood", 3, 9.0)])
    deliveroo = canoniek.orders_naar_canoniek(
        [_order("2026-09-01", "Renard Bakery Ixelles", "1", "20.00", "4.00")])
    uit = canoniek.bouw_verkopen(winkel, deliveroo)
    assert set(uit["kanaal"]) == {"winkel", "deliveroo"}
    status = {s["kanaal"]: s for s in canoniek.kanaalstatus(uit)}
    assert status["deliveroo"]["beschikbaar"] is True


def test_kanaalkost_deliveroo_is_een_gemeten_gemiddelde_per_maand():
    """Twee maanden. September: 50 bruto en 10 commissie over twee
    bestellingen; per stuk 25 en 5, inhouding 0,2. Oktober: één bestelling."""
    regels = [
        _order("2026-09-01", "Renard Bakery Ixelles", "1", "20.00", "4.00"),
        _order("2026-09-15", "Renard Bakery Ixelles", "2", "30.00", "6.00"),
        _order("2026-10-02", "Renard Bakery Uccle", "1", "10.00", "2.50"),
    ]
    uit = canoniek.kanaalkost_deliveroo(regels).set_index("maand")
    assert list(uit.index) == ["2026-09", "2026-10"]
    assert uit.loc["2026-09", "stuks"] == 2.0
    assert uit.loc["2026-09", "bruto_per_stuk"] == 25.0
    assert uit.loc["2026-09", "commissie_per_stuk"] == 5.0
    assert uit.loc["2026-09", "inhouding_pct"] == 0.2
    assert uit.loc["2026-10", "inhouding_pct"] == 0.25
    assert set(uit["kanaal"]) == {"deliveroo"}


def test_laad_deliveroo_orders_ontdubbelt_over_bestanden_heen(tmp_path):
    """Twee downloads die elkaar overlappen dragen dezelfde bestelling; die
    telt één keer. De sleutel is (datum, vestiging, nummer), dus hetzelfde
    nummer bij een andere vestiging is een andere bestelling."""
    kop = ("Naam restaurant,Bestelnummer,Bestelstatus,Datum ingediend,"
           "Tijdstip ingediend,Bezorgdatum,Tijdstip bezorging,Subtotaal,"
           "Deliveroo-commissie,Btw op Deliveroo-commissie\n")
    a = kop + ("Renard Bakery Ixelles,7,Afgerond,2026-09-01,10:00:00,"
               "2026-09-01,10:30:00,20.00,4.00,0.84\n")
    b = kop + ("Renard Bakery Ixelles,7,Afgerond,2026-09-01,10:00:00,"
               "2026-09-01,10:30:00,20.00,4.00,0.84\n"
               "Renard Bakery Uccle,7,Afgerond,2026-09-01,11:00:00,"
               "2026-09-01,11:30:00,10.00,2.00,0.42\n")
    (tmp_path / "a.csv").write_text(a, encoding="utf-8")
    (tmp_path / "b.csv").write_text(b, encoding="utf-8")
    regels = canoniek.laad_deliveroo_orders([tmp_path / "a.csv",
                                             tmp_path / "b.csv"])
    assert len(regels) == 2
    assert {r.store_id for r in regels} == {"Renard Bakery Ixelles",
                                            "Renard Bakery Uccle"}


def test_zonder_orders_is_deliveroo_leeg_en_de_kanaalkost_ook():
    assert canoniek.orders_naar_canoniek([]).empty
    assert canoniek.kanaalkost_deliveroo([]).empty


def test_laad_deliveroo_orders_leest_ook_een_gecomprimeerde_export(tmp_path):
    """De postbus draagt bytes; een export van een halve megabyte gaat er
    gecomprimeerd in. De extensie beslist, de inhoud is dezelfde tekst."""
    import gzip
    kop = ("Naam restaurant,Bestelnummer,Bestelstatus,Datum ingediend,"
           "Tijdstip ingediend,Bezorgdatum,Tijdstip bezorging,Subtotaal,"
           "Deliveroo-commissie,Btw op Deliveroo-commissie\n")
    rij = ("Renard Bakery Uccle,9,Afgerond,2026-09-01,10:00:00,"
           "2026-09-01,10:30:00,12.00,2.40,0.50\n")
    pad = tmp_path / "000001_rs-orders-report_x.csv.gz"
    with gzip.open(pad, "wt", encoding="utf-8") as fh:
        fh.write(kop + rij)
    regels = canoniek.laad_deliveroo_orders([pad])
    assert len(regels) == 1 and regels[0].store_id == "Renard Bakery Uccle"
