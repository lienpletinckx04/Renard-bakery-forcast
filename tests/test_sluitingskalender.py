"""De sluitingskalender uit de database: uitspraken, weekregels, en de rangorde.

Aanleiding, 19 augustus 2026: de zin op het prognosescherm — "vul de
sluitingslijst aan" — vroeg een handeling die een CFO niet kan uitvoeren (een
JSON-bestand in git bewerken). Deze module draagt de databasekant van dezelfde
invoer, met drie toestanden per dag (dicht, open, onbeantwoord) en een vaste
rangorde tussen de bronnen: agenda > database > bestand.

Alle datums hieronder zijn verzonnen en liggen in 2031, ver van elke echte
meetperiode: dit zijn vormen, geen klantcijfers.
"""

import datetime as dt

import pandas as pd
import pytest

from bakkerij import sluitingsdagen as sd
from bakkerij import sluitingskalender as sk
from bakkerij.sluitingsdagen import Sluiting


def _d(iso: str) -> dt.date:
    return dt.date.fromisoformat(iso)


def _dicht(iso: str, reden: str = "Kerstmis", bron: str = "feestdag") -> sk.Uitspraak:
    return sk.Uitspraak(datum=_d(iso), toestand="dicht", reden=reden, bron=bron)


def _open(iso: str, bron: str = "feestdag") -> sk.Uitspraak:
    return sk.Uitspraak(datum=_d(iso), toestand="open", reden="", bron=bron)


def _kalender(van: str, tot: str, **kolommen) -> pd.DataFrame:
    dagen = pd.date_range(van, tot, freq="D")
    kal = pd.DataFrame({"datum": [d.date() for d in dagen],
                        "winkel_gemeten": False, "winkel_open": False})
    for naam, waarde in kolommen.items():
        kal[naam] = waarde
    return kal


# --- de dataclasses toetsen hun eigen invoer --------------------------------


def test_een_onbekende_toestand_is_een_fout_met_reden():
    """Onbekend is geen toestand maar het ontbreken van een uitspraak; wie
    "misschien" probeert op te slaan, hoort dat in gewone taal te lezen."""
    with pytest.raises(ValueError, match="Onbekend is geen toestand"):
        sk.Uitspraak(datum=_d("2031-12-25"), toestand="misschien",
                     reden="", bron="feestdag")


def test_een_onbekende_bron_is_een_fout():
    with pytest.raises(ValueError, match='De bron "agenda" bestaat niet'):
        sk.Uitspraak(datum=_d("2031-12-25"), toestand="dicht",
                     reden="", bron="agenda")


def test_een_te_lange_reden_op_een_uitspraak_wordt_geweigerd():
    """Zelfde grens als de bestandslijst (REDEN_MAX): de reden komt op een
    scherm terecht."""
    with pytest.raises(ValueError, match="langer dan 120 tekens"):
        sk.Uitspraak(datum=_d("2031-12-25"), toestand="dicht",
                     reden="x" * 121, bron="feestdag")


def test_een_weekdag_buiten_de_week_bestaat_niet():
    for weekdag in (-1, 7):
        with pytest.raises(ValueError, match="bestaat niet"):
            sk.Weekregel(weekdag=weekdag, vanaf=_d("2031-01-01"),
                         tot=None, reden="")


def test_een_regel_die_eindigt_voor_hij_begint_wordt_geweigerd():
    with pytest.raises(ValueError, match="dat is eerder"):
        sk.Weekregel(weekdag=0, vanaf=_d("2031-02-01"),
                     tot=_d("2031-01-01"), reden="")


def test_een_te_lange_reden_op_een_regel_wordt_geweigerd():
    with pytest.raises(ValueError, match="langer dan 120 tekens"):
        sk.Weekregel(weekdag=0, vanaf=_d("2031-01-01"), tot=None,
                     reden="x" * 121)


# --- uitspraken naar dagen ---------------------------------------------------


def test_dichte_dagen_geeft_datum_naar_reden_en_slaat_open_over():
    per_dag = sk.dichte_dagen((_dicht("2031-12-25"), _open("2031-01-06")))
    assert per_dag == {_d("2031-12-25"): "Kerstmis"}


def test_een_dichte_dag_zonder_reden_krijgt_er_een():
    """Zelfde terugval als de bestandslijst: leeg mag, maar dan staat er iets
    leesbaars op het scherm en geen niets."""
    per_dag = sk.dichte_dagen((_dicht("2031-12-25", reden=""),))
    assert per_dag[_d("2031-12-25")] == sd.REDEN_ONBEKEND


def test_open_dagen_geeft_alleen_de_bevestigd_open_dagen():
    uit = sk.open_dagen((_dicht("2031-12-25"), _open("2031-01-06")))
    assert uit == {_d("2031-01-06")}


# --- weekregels uitrollen ----------------------------------------------------


def test_een_regel_rolt_uit_naar_elke_juiste_weekdag_in_het_bereik():
    """3 maart 2031 is een maandag; de regel springt per week en slaat de
    andere weekdagen over."""
    regel = sk.Weekregel(weekdag=0, vanaf=_d("2031-01-01"), tot=None,
                         reden="wekelijkse rustdag")
    uit = sk.regel_dagen((regel,), _d("2031-03-01"), _d("2031-03-31"))
    assert sorted(uit) == [_d("2031-03-03"), _d("2031-03-10"),
                           _d("2031-03-17"), _d("2031-03-24"),
                           _d("2031-03-31")]
    assert set(uit.values()) == {"wekelijkse rustdag"}


def test_een_regel_zonder_reden_krijgt_de_vaste_tekst():
    regel = sk.Weekregel(weekdag=0, vanaf=_d("2031-03-01"), tot=None, reden="")
    uit = sk.regel_dagen((regel,), _d("2031-03-01"), _d("2031-03-09"))
    assert uit == {_d("2031-03-03"): sk.REDEN_REGEL}


def test_vanaf_en_tot_begrenzen_de_uitrol_binnen_de_kalender():
    """De regel geldt van 10 t/m 24 maart; de maandagen ervoor en erna in de
    kalender blijven onaangeroerd."""
    regel = sk.Weekregel(weekdag=0, vanaf=_d("2031-03-10"),
                         tot=_d("2031-03-24"), reden="")
    uit = sk.regel_dagen((regel,), _d("2031-03-01"), _d("2031-03-31"))
    assert sorted(uit) == [_d("2031-03-10"), _d("2031-03-17"), _d("2031-03-24")]


def test_tot_none_loopt_precies_tot_het_kalendereinde():
    """Dat is het hele punt van een regel: hij is nooit "op". De volgende
    bouw, met een langere kalender, rolt hem vanzelf verder."""
    regel = sk.Weekregel(weekdag=0, vanaf=_d("2031-03-01"), tot=None, reden="")
    uit = sk.regel_dagen((regel,), _d("2031-03-01"), _d("2031-12-31"))
    assert max(uit) == _d("2031-12-29")  # de laatste maandag van de kalender


def test_een_leeg_of_omgekeerd_bereik_geeft_niets():
    regel = sk.Weekregel(weekdag=0, vanaf=_d("2031-03-01"), tot=None, reden="")
    assert sk.regel_dagen((regel,), _d("2031-03-10"), _d("2031-03-01")) == {}


def test_een_decennialang_bereik_blijft_gewoon_werken():
    """Er stond hier tot 19 aug 2026 een vangrail van vijf jaar, en die liet
    de allereerste run tegen de echte kalender omvallen: de canonieke
    kalender beslaat de volle kassahistoriek (ruim zeven jaar) plus het
    prognosevenster. De kalender zelf is de begrenzing; de lus is per week en
    blijft ook over decennia goedkoop."""
    regel = sk.Weekregel(weekdag=0, vanaf=_d("2031-01-01"), tot=None, reden="")
    uit = sk.regel_dagen((regel,), _d("2031-01-01"), _d("2040-01-01"))
    assert min(uit) == _d("2031-01-06")
    assert max(uit) == _d("2039-12-26")  # de laatste maandag binnen het bereik
    assert all(dag.weekday() == 0 for dag in uit)


# --- de kalender verrijken ---------------------------------------------------


def test_verrijk_kalender_zet_dichte_uitspraken_en_regeldagen():
    kal = _kalender("2031-03-02", "2031-03-11")
    regel = sk.Weekregel(weekdag=0, vanaf=_d("2031-01-01"), tot=None,
                         reden="rustdag")
    uit = sk.verrijk_kalender(kal, (_dicht("2031-03-05", reden="Feest"),),
                              (regel,))
    per_dag = dict(zip(uit["datum"], zip(uit["gepland_dicht"],
                                         uit["gepland_dicht_reden"],
                                         strict=True), strict=True))
    assert per_dag[_d("2031-03-03")] == (True, "rustdag")   # de regel
    assert per_dag[_d("2031-03-05")] == (True, "Feest")     # de uitspraak
    assert per_dag[_d("2031-03-10")] == (True, "rustdag")
    assert per_dag[_d("2031-03-04")] == (False, "")


def test_een_uitspraak_op_een_regeldag_wint_van_de_regel():
    """"Elke maandag dicht" plus "maandag 3 maart bevestigd open" betekent dat
    3 maart open is: een uitspraak over één dag is de meest specifieke
    bewering. De maandag erna blijft gewoon dicht."""
    kal = _kalender("2031-03-02", "2031-03-11")
    regel = sk.Weekregel(weekdag=0, vanaf=_d("2031-01-01"), tot=None, reden="")
    uit = sk.verrijk_kalender(kal, (_open("2031-03-03"),), (regel,))
    per_dag = dict(zip(uit["datum"], uit["gepland_dicht"], strict=True))
    assert not per_dag[_d("2031-03-03")]
    assert per_dag[_d("2031-03-10")]
    open_ = dict(zip(uit["datum"], uit["bevestigd_open"], strict=True))
    assert open_[_d("2031-03-03")]


def test_een_open_uitspraak_zet_bevestigd_open_en_verder_niets():
    kal = _kalender("2031-01-05", "2031-01-07")
    uit = sk.verrijk_kalender(kal, (_open("2031-01-06"),), ())
    assert list(uit["bevestigd_open"]) == [False, True, False]
    assert not uit["gepland_dicht"].any()


def test_een_open_uitspraak_op_een_al_dichte_dag_wordt_niet_gezet():
    """Agenda > database: het conflict hoort de aanroeper vooraf te melden
    via agenda_conflicten, en deze laag beslecht het niet stil."""
    kal = _kalender("2031-01-05", "2031-01-07",
                    gepland_dicht=[False, True, False],
                    gepland_dicht_reden=["", "Uit de agenda", ""])
    uit = sk.verrijk_kalender(kal, (_open("2031-01-06"),), ())
    assert list(uit["gepland_dicht"]) == [False, True, False]
    assert list(uit["bevestigd_open"]) == [False, False, False]


def test_een_bestaande_reden_blijft_staan():
    """Zelfde OF-semantiek als sluitingsdagen.verrijk_kalender: wat een
    eerdere bron al zei, is specifieker dan wat deze laag toevoegt."""
    kal = _kalender("2031-01-05", "2031-01-06",
                    gepland_dicht=[True, False],
                    gepland_dicht_reden=["Uit de agenda", ""])
    uit = sk.verrijk_kalender(
        kal,
        (_dicht("2031-01-05", reden="Uit de database"),
         _dicht("2031-01-06", reden="Uit de database")),
        (),
    )
    assert list(uit["gepland_dicht"]) == [True, True]
    assert list(uit["gepland_dicht_reden"]) == ["Uit de agenda", "Uit de database"]


def test_de_kolom_bevestigd_open_bestaat_ook_zonder_uitspraken():
    """De CSV-vorm hangt niet af van de vraag of er al iets bevestigd is."""
    uit = sk.verrijk_kalender(_kalender("2031-01-05", "2031-01-06"), (), ())
    assert sk.OPEN_KOLOM in uit.columns
    assert not uit[sk.OPEN_KOLOM].any()


def test_verrijk_kalender_raakt_de_meting_niet_aan():
    """De kassa is de waarheid voor het verleden; deze laag staat ernaast."""
    kal = _kalender("2031-01-06", "2031-01-06")
    kal["winkel_gemeten"] = True
    kal["winkel_open"] = True
    uit = sk.verrijk_kalender(kal, (_dicht("2031-01-06"),), ())
    assert bool(uit["winkel_open"].iloc[0]) is True
    assert bool(uit["winkel_gemeten"].iloc[0]) is True
    assert bool(uit["gepland_dicht"].iloc[0]) is True


def test_waarheidskolommen_uit_een_csv_blijven_waar():
    """Een kalender die over schijf is gegaan, draagt tekstkolommen. "False"
    is als tekst waar, en zonder _waarheid zou elke dag dicht lijken."""
    kal = _kalender("2031-01-05", "2031-01-07",
                    gepland_dicht=["False", "True", "False"],
                    gepland_dicht_reden=["", "Uit de agenda", ""])
    kal["bevestigd_open"] = ["True", "False", "False"]
    uit = sk.verrijk_kalender(kal, (_open("2031-01-07"),), ())
    assert list(uit["gepland_dicht"]) == [False, True, False]
    assert list(uit["bevestigd_open"]) == [True, False, True]


# --- agenda_conflicten -------------------------------------------------------


def test_agenda_conflicten_meldt_de_open_dagen_die_al_dicht_stonden():
    kal = _kalender("2031-01-05", "2031-01-08",
                    gepland_dicht=[True, True, False, False])
    conflicten = sk.agenda_conflicten(
        kal, (_open("2031-01-06"), _open("2031-01-05"), _open("2031-01-07")))
    assert conflicten == (_d("2031-01-05"), _d("2031-01-06"))


def test_zonder_sluitingskolom_zijn_er_geen_conflicten():
    """Vóór de agenda draait, bestaat de kolom niet; dan valt er niets te
    melden."""
    kal = _kalender("2031-01-05", "2031-01-06")
    assert sk.agenda_conflicten(kal, (_open("2031-01-05"),)) == ()


# --- zonder_dagen: database > bestand ----------------------------------------


def test_een_dag_middenin_een_periode_splitst_haar_in_twee():
    periode = Sluiting(van=_d("2031-03-01"), tot=_d("2031-03-05"), reden="Verlof")
    uit = sk.zonder_dagen((periode,), {_d("2031-03-03")})
    assert uit == (
        Sluiting(van=_d("2031-03-01"), tot=_d("2031-03-02"), reden="Verlof"),
        Sluiting(van=_d("2031-03-04"), tot=_d("2031-03-05"), reden="Verlof"),
    )


def test_een_hele_periode_kan_wegvallen():
    periode = Sluiting(van=_d("2031-12-25"), tot=_d("2031-12-25"), reden="Kerst")
    assert sk.zonder_dagen((periode,), {_d("2031-12-25")}) == ()


def test_een_lege_verzameling_dagen_is_de_identiteit():
    """Niets te knippen betekent letterlijk dezelfde lijst terug, geen kopie
    die per ongeluk zou kunnen verschillen."""
    lijst = (Sluiting(van=_d("2031-03-01"), tot=_d("2031-03-05"), reden="X"),)
    assert sk.zonder_dagen(lijst, set()) is lijst


# --- onbekende_dagen: het per-dag-voorbehoud ---------------------------------


def test_dagen_binnen_de_dekking_zijn_beantwoord():
    dagen = [_d("2031-03-01"), _d("2031-03-02"), _d("2031-03-03")]
    uit = sk.onbekende_dagen(dagen, dekking_tot=_d("2031-03-02"),
                             beantwoord=set())
    assert uit == (_d("2031-03-03"),)


def test_een_bevestigde_dag_valt_uit_het_voorbehoud():
    """Dicht of open, allebei zijn een antwoord; wat overblijft zijn de dagen
    waarvoor de prognose "open" aanneemt zonder dat iemand dat gezegd heeft."""
    dagen = [_d("2031-03-01"), _d("2031-03-02")]
    uit = sk.onbekende_dagen(dagen, dekking_tot=None,
                             beantwoord={_d("2031-03-02")})
    assert uit == (_d("2031-03-01"),)


def test_zonder_dekking_en_zonder_antwoorden_is_elke_dag_onbekend():
    dagen = [_d("2031-03-01"), _d("2031-03-02")]
    uit = sk.onbekende_dagen(dagen, dekking_tot=None, beantwoord=set())
    assert uit == tuple(dagen)


def test_onbekende_dagen_aanvaardt_timestamps():
    """`Prognosevenster.dagen` is een DatetimeIndex, geen lijst van dates."""
    dagen = pd.DatetimeIndex(["2031-03-01", "2031-03-02"])
    uit = sk.onbekende_dagen(dagen, dekking_tot=_d("2031-03-01"),
                             beantwoord=set())
    assert uit == (_d("2031-03-02"),)


# --- feestdagkandidaten ------------------------------------------------------


def test_kerstmis_zit_in_de_komende_twaalf_maanden():
    kandidaten = sk.feestdagkandidaten(_d("2031-09-01"))
    assert (_d("2031-12-25"), "Kerstmis") in kandidaten


def test_de_naam_volgt_de_taal():
    nl = dict(sk.feestdagkandidaten(_d("2031-09-01"), taal="nl"))
    fr = dict(sk.feestdagkandidaten(_d("2031-09-01"), taal="fr"))
    assert nl[_d("2031-12-25")] == "Kerstmis"
    assert fr[_d("2031-12-25")] == "Noël"


def test_de_kandidaten_komen_gesorteerd_terug():
    kandidaten = sk.feestdagkandidaten(_d("2031-01-01"), maanden=24)
    datums = [datum for datum, _naam in kandidaten]
    assert datums == sorted(datums)
    assert len(datums) > 12  # twee jaar aan feestdagen, geen enkel jaar leeg


def test_de_grenzen_zijn_inclusief():
    """Een venster van nul maanden dat op een feestdag begint, bevat precies
    die feestdag: vanaf en tot doen allebei mee."""
    assert sk.feestdagkandidaten(_d("2031-12-25"), maanden=0) == [
        (_d("2031-12-25"), "Kerstmis")
    ]
