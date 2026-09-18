"""De sluitingslijst: inlezen, toetsen, en in de kalender zetten.

Aanleiding, 14 augustus 2026: het prognosescherm zette een omzetverwachting op
een week waarin de zaak aangekondigd dicht is. De kolom om dat te voorkomen
bestond al (`gepland_dicht`, uit de agenda), maar er was geen bron die niet op
vraag 46 wachtte, en niets keek ernaar bij het kiezen van de prognosedagen.
"""

import datetime as dt
import json

import pandas as pd
import pytest

from bakkerij import sluitingsdagen as sd
from bakkerij import taal


def _json(sluitingen) -> str:
    return json.dumps({"sluitingen": sluitingen})


# --- inlezen en toetsen -----------------------------------------------------


def test_een_periode_met_van_en_tot():
    (s,) = sd.parse_sluitingen(
        _json([{"van": "2026-08-17", "tot": "2026-08-23", "reden": "Zomersluiting"}])
    )
    assert s.van == dt.date(2026, 8, 17)
    assert s.tot == dt.date(2026, 8, 23)
    assert s.reden == "Zomersluiting"
    assert s.dagen == 7


def test_tot_mag_weg_voor_een_enkele_dag():
    (s,) = sd.parse_sluitingen(_json([{"van": "2026-12-25", "reden": "Kerstmis"}]))
    assert s.van == s.tot == dt.date(2026, 12, 25)
    assert s.dagen == 1


def test_zonder_bestand_is_de_lijst_leeg(tmp_path):
    """Leeg is een geldige toestand: dan weet het platform van geen sluitingen.

    Dat is een ANDERE uitspraak dan "er zijn er geen", en `dekking_tot` maakt
    dat verschil zichtbaar voor het contract.
    """
    assert sd.lees_sluitingen(tmp_path / "bestaat-niet.json") == ()
    assert sd.dekking_tot(()) is None


def test_periodes_komen_gesorteerd_terug():
    lijst = sd.parse_sluitingen(
        _json([{"van": "2026-12-25"}, {"van": "2026-08-17", "tot": "2026-08-23"}])
    )
    assert [s.van for s in lijst] == [dt.date(2026, 8, 17), dt.date(2026, 12, 25)]


@pytest.mark.parametrize(
    ("rijen", "fragment"),
    [
        ([{"van": "17-08-2026"}], "geen geldige datum"),
        ([{"van": "2026-08-32"}], "geen geldige datum"),
        ([{"tot": "2026-08-23"}], 'zonder veld "van"'),
        ([{"van": "2026-08-23", "tot": "2026-08-17"}], "dat is eerder"),
        ([{"van": "2026-01-01", "tot": "2026-12-31"}], "meer dan de 120"),
        ([{"van": "2026-08-17", "reden": "x" * 200}], "langer dan"),
        ([{"van": 20260817}], "datum als tekst"),
        ([{"van": "2026-08-17", "reden": 5}], "moet tekst zijn"),
    ],
)
def test_elke_afwijking_is_een_fout_met_reden(rijen, fragment):
    """Streng, en met opzet.

    Een sluitingsdag die door een typefout niet meedoet, levert een
    omzetverwachting op voor een dag dat de deur dicht is. Stil corrigeren is
    hier het gevaarlijkste gedrag dat deze module kan hebben.
    """
    with pytest.raises((ValueError, TypeError), match=fragment):
        sd.parse_sluitingen(_json(rijen))


def test_overlappende_periodes_worden_geweigerd():
    with pytest.raises(ValueError, match="overlappen"):
        sd.parse_sluitingen(
            _json([
                {"van": "2026-08-17", "tot": "2026-08-23", "reden": "Zomer"},
                {"van": "2026-08-20", "tot": "2026-08-25", "reden": "Verbouwing"},
            ])
        )


def test_aansluitende_periodes_mogen_wel():
    """23 en 24 augustus raken elkaar maar overlappen niet."""
    lijst = sd.parse_sluitingen(
        _json([
            {"van": "2026-08-17", "tot": "2026-08-23"},
            {"van": "2026-08-24", "tot": "2026-08-25"},
        ])
    )
    assert len(lijst) == 2


def test_geen_geldige_json():
    with pytest.raises(ValueError, match="geen geldige JSON"):
        sd.parse_sluitingen("{dit is geen json")


def test_ontbrekend_hoofdveld():
    with pytest.raises(TypeError, match='mist het veld "sluitingen"'):
        sd.parse_sluitingen('{"dagen": []}')


def test_te_veel_periodes():
    with pytest.raises(ValueError, match="geen sluitingskalender meer"):
        sd.parse_sluitingen(
            _json([{"van": f"20{j:02d}-01-01"} for j in range(30, 30 + 401)])
        )


# --- naar dagen en naar de kalender -----------------------------------------


def test_dagen_met_reden_ontvouwt_de_periode():
    per_dag = sd.dagen_met_reden(
        sd.parse_sluitingen(
            _json([{"van": "2026-08-17", "tot": "2026-08-19", "reden": "Zomer"}])
        )
    )
    assert per_dag == {
        dt.date(2026, 8, 17): "Zomer",
        dt.date(2026, 8, 18): "Zomer",
        dt.date(2026, 8, 19): "Zomer",
    }


def test_een_sluiting_zonder_reden_krijgt_er_een():
    """Leeg mag, maar dan staat er iets leesbaars op het scherm en geen niets."""
    per_dag = sd.dagen_met_reden(sd.parse_sluitingen(_json([{"van": "2026-08-17"}])))
    assert per_dag[dt.date(2026, 8, 17)] == sd.REDEN_ONBEKEND


def test_dekking_tot_is_de_laatste_dag_in_de_lijst():
    lijst = sd.parse_sluitingen(
        _json([{"van": "2026-08-17", "tot": "2026-08-23"}, {"van": "2026-12-25"}])
    )
    assert sd.dekking_tot(lijst) == dt.date(2026, 12, 25)


def _kalender(datums, *, gemeten=False, open_=False) -> pd.DataFrame:
    return pd.DataFrame([
        {"datum": dt.date.fromisoformat(d), "winkel_gemeten": gemeten,
         "winkel_open": open_}
        for d in datums
    ])


def test_verrijk_kalender_zet_de_kolommen():
    kal = _kalender(["2026-08-16", "2026-08-17", "2026-08-18"])
    lijst = sd.parse_sluitingen(
        _json([{"van": "2026-08-17", "tot": "2026-08-18", "reden": "Zomer"}])
    )
    uit = sd.verrijk_kalender(kal, lijst)
    assert list(uit["gepland_dicht"]) == [False, True, True]
    assert list(uit["gepland_dicht_reden"]) == ["", "Zomer", "Zomer"]


def test_verrijk_kalender_zonder_lijst_verandert_niets():
    kal = _kalender(["2026-08-16"])
    assert sd.verrijk_kalender(kal, ()) is kal


def test_verrijk_kalender_raakt_de_meting_niet_aan():
    """De kassa is de waarheid voor het verleden; deze laag staat ernaast."""
    kal = _kalender(["2026-08-17"], gemeten=True, open_=True)
    uit = sd.verrijk_kalender(
        kal, sd.parse_sluitingen(_json([{"van": "2026-08-17", "reden": "Zomer"}]))
    )
    assert bool(uit["winkel_open"].iloc[0]) is True
    assert bool(uit["winkel_gemeten"].iloc[0]) is True
    assert bool(uit["gepland_dicht"].iloc[0]) is True


def test_verrijk_kalender_bovenop_de_agenda_is_een_of():
    """Twee bronnen die dicht zeggen, is geen conflict.

    En een reden die de agenda al gaf, blijft staan: die komt van de bakkerij
    zelf en is specifieker dan wat wij in een configbestand typen.
    """
    kal = _kalender(["2026-08-17", "2026-08-18"])
    kal["gepland_dicht"] = [True, False]
    kal["gepland_dicht_reden"] = ["Uit de agenda", ""]

    uit = sd.verrijk_kalender(
        kal,
        sd.parse_sluitingen(
            _json([{"van": "2026-08-17", "tot": "2026-08-18", "reden": "Uit de lijst"}])
        ),
    )
    assert list(uit["gepland_dicht"]) == [True, True]
    assert list(uit["gepland_dicht_reden"]) == ["Uit de agenda", "Uit de lijst"]


# --- de controle tegen de meting -------------------------------------------


def test_afwijking_als_de_lijst_dicht_zegt_en_de_kassa_verkocht():
    kal = _kalender(["2026-08-17"], gemeten=True, open_=True)
    uit = sd.afwijkingen(
        kal, sd.parse_sluitingen(_json([{"van": "2026-08-17", "reden": "Zomer"}]))
    )
    assert len(uit) == 1
    assert uit["reden"].iloc[0] == "Zomer"


def test_geen_afwijking_buiten_het_gemeten_bereik():
    """Over de toekomst kan de lijst niet met de meting in strijd zijn."""
    kal = _kalender(["2026-08-17"], gemeten=False, open_=False)
    uit = sd.afwijkingen(
        kal, sd.parse_sluitingen(_json([{"van": "2026-08-17", "reden": "Zomer"}]))
    )
    assert uit.empty


def test_geen_afwijking_als_beide_dicht_zeggen():
    kal = _kalender(["2026-08-17"], gemeten=True, open_=False)
    uit = sd.afwijkingen(
        kal, sd.parse_sluitingen(_json([{"van": "2026-08-17", "reden": "Zomer"}]))
    )
    assert uit.empty


# --- de wacht op een sluiting die misschien doorloopt ----------------------
#
# Alle data hieronder is verzonnen en staat in 2031, ver van elke echte
# meetperiode: dit zijn vormen, geen klantcijfers.


def _reeks(van: str, tot: str) -> list[dt.date]:
    a, b = dt.date.fromisoformat(van), dt.date.fromisoformat(tot)
    return [a + dt.timedelta(days=i) for i in range((b - a).days + 1)]


def _wachtkalender(*, van="2031-02-01", tot="2031-04-30",
                   gemeten_tot="2031-03-07", gesloten=(), gepland=()):
    """Een verzonnen kalender: gemeten t/m `gemeten_tot` en open, behalve wat
    in `gesloten` staat. `gepland` zet `gepland_dicht`. Beide zijn lijsten van
    (van, tot)-paren, inclusief."""
    dicht = {d for a, b in gesloten for d in _reeks(a, b)}
    aangekondigd = {d for a, b in gepland for d in _reeks(a, b)}
    grens = dt.date.fromisoformat(gemeten_tot)
    rijen = []
    for datum in _reeks(van, tot):
        gemeten = datum <= grens
        rijen.append({
            "datum": datum,
            "winkel_gemeten": gemeten,
            "winkel_open": gemeten and datum not in dicht,
            "gepland_dicht": datum in aangekondigd,
            "gepland_dicht_reden": "Verzonnen sluiting" if datum in aangekondigd
                                   else "",
        })
    return pd.DataFrame(rijen)


#: De prognosedagen zoals `prognosevenster` ze zou opleveren: de aangekondigde
#: week is er al uit gezeefd, de twee dagen ervoor niet -- want niemand heeft
#: ooit gezegd dat die dicht waren.
VENSTER = _reeks("2031-03-15", "2031-03-16") + _reeks("2031-03-24", "2031-03-28")


def test_de_reeks_zonder_einde_geeft_een_signaal():
    """Het geval van 15 augustus 2026, in verzonnen data.

    De meting eindigt in een gesloten week, de lijst kent alleen de week
    daarna, en tussen die twee staan prognosedagen met een omzetverwachting.
    """
    kal = _wachtkalender(gesloten=[("2031-03-01", "2031-03-07")],
                         gepland=[("2031-03-17", "2031-03-23")])
    signaal = sd.lopende_sluiting(kal, VENSTER)

    assert signaal is not None
    assert signaal.reeks_van == dt.date(2031, 3, 1)
    assert signaal.reeks_tot == dt.date(2031, 3, 7)
    assert signaal.reeks_dagen == 7
    assert signaal.lijst_eindigde_op is None
    assert signaal.onverklaard_van == dt.date(2031, 3, 8)
    assert signaal.onverklaard_tot == dt.date(2031, 3, 16)
    assert signaal.onverklaarde_dagen == 9
    assert signaal.dagen_in_venster == (dt.date(2031, 3, 15), dt.date(2031, 3, 16))
    assert signaal.aantal_in_venster == 2


def test_de_melding_zegt_wat_hoeveel_en_van_wie():
    kal = _wachtkalender(gesloten=[("2031-03-01", "2031-03-07")],
                         gepland=[("2031-03-17", "2031-03-23")])
    tekst = sd.lopende_sluiting(kal, VENSTER).melding()

    assert "1 maart 2031 t/m 7 maart 2031" in tekst   # wat er gemeten is
    assert "De sluitingslijst kent die sluiting niet" in tekst
    assert "2 dagen van dit venster" in tekst          # hoeveel het er zijn
    assert "15 maart 2031 t/m 16 maart 2031" in tekst  # en welke
    assert "vul de sluitingslijst aan" in tekst        # wat er nodig is
    assert "alleen de bakkerij weet" in tekst          # en van wie


def test_de_melding_bestaat_in_het_frans():
    kal = _wachtkalender(gesloten=[("2031-03-01", "2031-03-07")],
                         gepland=[("2031-03-17", "2031-03-23")])
    with taal.in_taal("fr"):
        tekst = sd.lopende_sluiting(kal, VENSTER).melding()
    assert "liste des fermetures" in tekst
    assert "2 jours de cette fenêtre" in tekst
    # De eerste van de maand is in het Frans een rangtelwoord: "1er mars".
    assert "du 1er mars 2031 au 7 mars 2031" in tekst


def test_de_melding_loopt_ook_met_een_enkele_dag():
    """Eén dag is het scherpste geval, niet het zeldzaamste."""
    kal = _wachtkalender(gesloten=[("2031-03-05", "2031-03-07")],
                         gepland=[("2031-03-09", "2031-03-23")])
    signaal = sd.lopende_sluiting(kal, [dt.date(2031, 3, 8)])
    assert signaal.aantal_in_venster == 1
    assert "daar valt 1 dag van dit venster in" in signaal.melding()
    assert "voor die dag een omzetverwachting" in signaal.melding()
    with taal.in_taal("fr"):
        tekst = signaal.melding()
    assert "1 jour de cette fenêtre s'y situe" in tekst
    assert "ce jour affiche" in tekst


def test_geen_signaal_als_de_laatste_gemeten_dag_open_was():
    """De zaak was open toen we voor het laatst keken; dan is er geen sluiting
    die kan doorlopen."""
    kal = _wachtkalender(gesloten=[("2031-03-01", "2031-03-06")])
    assert sd.lopende_sluiting(kal, VENSTER) is None


def test_een_korte_gesloten_staart_is_een_weekpatroon_en_zwijgt():
    """Twee gesloten dagen aan het einde van de meting is zondag plus maandag.

    Zou de wacht daar afgaan, dan gaat ze elke week af en leest niemand haar
    nog -- inclusief de ene keer dat het wél een verlofweek is.
    """
    kal = _wachtkalender(gesloten=[("2031-03-06", "2031-03-07")])
    assert sd.lopende_sluiting(kal, VENSTER) is None

    # Met een lagere drempel ziet dezelfde wacht hem wél: de drempel is een
    # keuze en geen eigenschap van de reeks.
    assert sd.lopende_sluiting(kal, VENSTER, minimum_reeks=2) is not None


def test_geen_signaal_als_de_sluiting_aangekondigd_doorloopt():
    """De lijst is compleet: de sluiting heeft een aangekondigd einde."""
    kal = _wachtkalender(gesloten=[("2031-03-01", "2031-03-07")],
                         gepland=[("2031-03-01", "2031-03-23")])
    assert sd.lopende_sluiting(kal, VENSTER) is None


def test_geen_signaal_als_de_lijst_de_sluiting_precies_beeindigt():
    """De lijst kent deze sluiting en laat haar eindigen op de laatste gemeten
    dag. Dat einde komt van de bakkerij of van de beheerder, en dat geloven we;
    wat daarna niet gemeten is, is een meetgat en niet deze sluiting."""
    kal = _wachtkalender(gesloten=[("2031-03-01", "2031-03-07")],
                         gepland=[("2031-03-01", "2031-03-07")])
    assert sd.lopende_sluiting(kal, VENSTER) is None


def test_signaal_als_de_lijst_eerder_eindigt_dan_de_kassa():
    """De lijst zegt tot 5 maart, de kassa mat nog dicht op 6 en 7 maart. Dan
    loopt de lijst aantoonbaar achter, en dat staat in de melding."""
    kal = _wachtkalender(gesloten=[("2031-03-01", "2031-03-07")],
                         gepland=[("2031-03-01", "2031-03-05")])
    signaal = sd.lopende_sluiting(kal, VENSTER)
    assert signaal is not None
    assert signaal.lijst_eindigde_op == dt.date(2031, 3, 5)
    assert "eindigen op 5 maart 2031" in signaal.melding()


def test_geen_signaal_zonder_prognosedagen_in_het_gat():
    """Het gat ligt volledig achter de aangekondigde sluiting: het scherm toont
    voor die dagen geen cijfer, dus valt er niets te melden."""
    kal = _wachtkalender(gesloten=[("2031-03-01", "2031-03-07")],
                         gepland=[("2031-03-08", "2031-03-23")])
    assert sd.lopende_sluiting(kal, VENSTER) is None
    assert sd.lopende_sluiting(kal, []) is None


def test_zonder_sluitingskolom_gaat_de_wacht_gewoon_af():
    """Geen lijst en geen agenda betekent dat niets de sluiting verklaart. Dat
    is de scherpste vorm van dit signaal, niet een reden om te zwijgen."""
    kal = _wachtkalender(gesloten=[("2031-03-01", "2031-03-07")])
    kal = kal.drop(columns=["gepland_dicht", "gepland_dicht_reden"])
    signaal = sd.lopende_sluiting(kal, VENSTER)
    assert signaal is not None
    assert signaal.onverklaard_tot == dt.date(2031, 3, 28)


def test_zonder_meting_zwijgt_de_wacht():
    kal = _wachtkalender(gesloten=[("2031-03-01", "2031-03-07")])
    assert sd.lopende_sluiting(kal.drop(columns=["winkel_gemeten"]), VENSTER) is None
    kal["winkel_gemeten"] = False
    assert sd.lopende_sluiting(kal, VENSTER) is None


def test_waarheidskolommen_uit_een_csv_zetten_de_wacht_niet_uit():
    """Een kalender die over schijf is gegaan, kan tekstkolommen hebben. Zou
    de wacht daarop stilvallen, dan verdwijnt ze precies waar ze moet werken."""
    kal = _wachtkalender(gesloten=[("2031-03-01", "2031-03-07")],
                         gepland=[("2031-03-17", "2031-03-23")])
    for kolom in ("winkel_gemeten", "winkel_open", "gepland_dicht"):
        kal[kolom] = kal[kolom].map(lambda w: "True" if w else "False")
    signaal = sd.lopende_sluiting(kal, VENSTER)
    assert signaal is not None
    assert signaal.dagen_in_venster == (dt.date(2031, 3, 15), dt.date(2031, 3, 16))


def test_prognosedagen_mogen_timestamps_zijn():
    """`Prognosevenster.dagen` is een DatetimeIndex, geen lijst van dates."""
    kal = _wachtkalender(gesloten=[("2031-03-01", "2031-03-07")],
                         gepland=[("2031-03-17", "2031-03-23")])
    signaal = sd.lopende_sluiting(kal, pd.DatetimeIndex(VENSTER, name="datum"))
    assert signaal is not None
    assert signaal.aantal_in_venster == 2


def test_een_onmogelijke_drempel_is_een_fout():
    kal = _wachtkalender(gesloten=[("2031-03-01", "2031-03-07")])
    with pytest.raises(ValueError, match="minstens 1 dag"):
        sd.lopende_sluiting(kal, VENSTER, minimum_reeks=0)
