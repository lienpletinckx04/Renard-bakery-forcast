"""Tests voor de agendalaag (iCal).

Alle iCal-tekst hieronder is verzonnen. Er is nooit een echte agenda van de
eindklant nodig om deze laag te bouwen of te testen, en dat is opzet: het spoor
moet volledig te ontwikkelen zijn vóór iemand een link deelt.
"""
import datetime

import pandas as pd

from bakkerij.sources import agenda as ag


def _ics(*events: str) -> str:
    binnen = "\n".join(f"BEGIN:VEVENT\n{e}\nEND:VEVENT" for e in events)
    return f"BEGIN:VCALENDAR\nVERSION:2.0\n{binnen}\nEND:VCALENDAR\n"


def _kalender(datums, gemeten=True, open_=True) -> pd.DataFrame:
    return pd.DataFrame({
        "datum": [datetime.date.fromisoformat(d) for d in datums],
        "winkel_gemeten": gemeten,
        "winkel_open": open_,
    })


# --- lezen ------------------------------------------------------------------

def test_heledag_reeks_wordt_uitgeklapt_met_exclusief_einde():
    # 1 t/m 15 augustus staat in iCal als DTEND 16 augustus.
    a = ag.lees_ics(_ics(
        "SUMMARY:DICHT: zomersluiting\n"
        "DTSTART;VALUE=DATE:20260801\nDTEND;VALUE=DATE:20260816"))
    assert a.bruikbaar
    assert len(a.dagen) == 15
    assert a.van == datetime.date(2026, 8, 1)
    assert a.tot == datetime.date(2026, 8, 15)
    assert {d.kenmerk for d in a.dagen} == {"gepland_dicht"}
    assert a.dagen[0].reden == "zomersluiting"


def test_event_zonder_einddatum_is_een_dag():
    a = ag.lees_ics(_ics("SUMMARY:DICHT: begrafenis\nDTSTART;VALUE=DATE:20260914"))
    assert [d.datum for d in a.dagen] == [datetime.date(2026, 9, 14)]


def test_alle_vier_de_voorvoegsels_worden_herkend():
    a = ag.lees_ics(_ics(
        "SUMMARY:DICHT: verlof\nDTSTART;VALUE=DATE:20260901",
        "SUMMARY:ANDERE UREN: 7-12\nDTSTART;VALUE=DATE:20260902",
        "SUMMARY:PROMO: 3 voor 2\nDTSTART;VALUE=DATE:20260903",
        "SUMMARY:EVENT: braderie\nDTSTART;VALUE=DATE:20260904"))
    assert {d.kenmerk for d in a.dagen} == set(ag.KOLOMMEN)
    assert a.waarschuwingen == []


# --- wat de parser bewust niet doet -----------------------------------------

def test_herhalende_reeks_wordt_gemeld_en_niet_gelezen():
    # Half begrepen is niet begrepen: een RRULE stil negeren zou betekenen dat
    # een wekelijkse sluiting één keer meetelt en daarna nooit meer.
    a = ag.lees_ics(_ics(
        "SUMMARY:DICHT: elke maandag\n"
        "DTSTART;VALUE=DATE:20260907\nRRULE:FREQ=WEEKLY;BYDAY=MO"))
    assert a.dagen == []
    assert any("herhalende reeks" in w for w in a.waarschuwingen)


def test_titel_zonder_bekend_voorvoegsel_wordt_gemeld_en_genegeerd():
    a = ag.lees_ics(_ics("SUMMARY:tandarts\nDTSTART;VALUE=DATE:20260910"))
    assert a.dagen == []
    assert any("voorvoegsel" in w or "begint niet met" in w for w in a.waarschuwingen)


def test_event_met_een_uur_wordt_gelezen_maar_gemeld():
    a = ag.lees_ics(_ics("SUMMARY:DICHT: stroompanne\nDTSTART:20260911T060000Z"))
    assert [d.datum for d in a.dagen] == [datetime.date(2026, 9, 11)]
    assert any("hele dag" in w for w in a.waarschuwingen)


def test_bestand_zonder_events_is_onbruikbaar_met_reden():
    a = ag.lees_ics("dit is geen agenda")
    assert a.bruikbaar is False
    assert a.reden_onbruikbaar
    assert a.dagen == []


def test_lange_titel_over_twee_regels_wordt_samengevoegd():
    # iCal vouwt regels langer dan 75 tekens; de tweede regel begint met een spatie.
    a = ag.lees_ics(_ics(
        "SUMMARY:DICHT: jaarlijkse sluiting wegens\n  onderhoud van de oven\n"
        "DTSTART;VALUE=DATE:20261005"))
    assert a.dagen[0].reden == "jaarlijkse sluiting wegens onderhoud van de oven"


# --- tijdzone ---------------------------------------------------------------

def test_utc_avonduur_valt_op_de_brusselse_dag_erna():
    # 23:30 UTC is 01:30 in Brussel, en dat is de dag erna. Wie de Z negeert,
    # zet dit item op de verkeerde dag.
    a = ag.lees_ics(_ics("SUMMARY:DICHT: stroompanne\nDTSTART:20261115T233000Z"))
    assert [d.datum for d in a.dagen] == [datetime.date(2026, 11, 16)]


def test_utc_ochtenduur_blijft_op_dezelfde_dag():
    a = ag.lees_ics(_ics("SUMMARY:DICHT: stroompanne\nDTSTART:20261115T060000Z"))
    assert [d.datum for d in a.dagen] == [datetime.date(2026, 11, 15)]


def test_een_andere_tijdzone_wordt_naar_brussel_gerekend():
    # 20:00 in New York is 02:00 in Brussel, de dag erna.
    a = ag.lees_ics(_ics(
        "SUMMARY:EVENT: iets\nDTSTART;TZID=America/New_York:20260910T200000"))
    assert [d.datum for d in a.dagen] == [datetime.date(2026, 9, 11)]


def test_onbekende_tijdzone_wordt_gemeld_en_als_brusselse_tijd_gelezen():
    a = ag.lees_ics(_ics(
        "SUMMARY:DICHT: verlof\nDTSTART;TZID=Mars/Olympus:20260910T200000"))
    assert [d.datum for d in a.dagen] == [datetime.date(2026, 9, 10)]
    assert any("Onbekende tijdzone" in w for w in a.waarschuwingen)


def test_een_hele_dag_draagt_geen_tijdzone_en_verschuift_dus_niet():
    a = ag.lees_ics(_ics("SUMMARY:DICHT: verlof\nDTSTART;VALUE=DATE:20261115"))
    assert [d.datum for d in a.dagen] == [datetime.date(2026, 11, 15)]
    assert a.waarschuwingen == []


def test_bij_een_event_met_een_uur_is_dtend_niet_exclusief():
    # Een hele-dag-event eindigt exclusief, een event met een uur niet. Een dag
    # aftrekken zou hier 12 november opeten.
    a = ag.lees_ics(_ics(
        "SUMMARY:DICHT: werken\n"
        "DTSTART;TZID=Europe/Brussels:20261110T070000\n"
        "DTEND;TZID=Europe/Brussels:20261112T180000"))
    assert [d.datum for d in a.dagen] == [
        datetime.date(2026, 11, d) for d in (10, 11, 12)]


def test_de_ontsnapping_van_ical_verdwijnt_uit_de_reden():
    a = ag.lees_ics(_ics(
        r"SUMMARY:DICHT: zomersluiting\, winkel\; atelier\nen bureau" "\n"
        "DTSTART;VALUE=DATE:20260801"))
    assert a.dagen[0].reden == "zomersluiting, winkel; atelier en bureau"


# --- de laag vervuilt niets -------------------------------------------------

def test_zonder_agenda_blijft_de_kalender_letterlijk_gelijk():
    kal = _kalender(["2026-09-01", "2026-09-02"])
    leeg = ag.Agenda(bruikbaar=False, reden_onbruikbaar="geen feed ingesteld")
    uit = ag.verrijk_kalender(kal, leeg)
    pd.testing.assert_frame_equal(uit, kal)


def test_verrijken_raakt_de_meting_niet_aan():
    kal = _kalender(["2026-09-01", "2026-09-02"], open_=True)
    a = ag.lees_ics(_ics("SUMMARY:DICHT: verlof\nDTSTART;VALUE=DATE:20260902"))
    uit = ag.verrijk_kalender(kal, a).set_index("datum")
    # De agenda zegt dicht, de meting zegt open. De meting blijft staan.
    assert bool(uit.loc[datetime.date(2026, 9, 2), "winkel_open"]) is True
    assert bool(uit.loc[datetime.date(2026, 9, 2), "gepland_dicht"]) is True
    assert bool(uit.loc[datetime.date(2026, 9, 1), "gepland_dicht"]) is False
    assert uit.loc[datetime.date(2026, 9, 1), "gepland_dicht_reden"] == ""


def test_afwijkingen_meldt_beide_richtingen_en_muteert_niets():
    kal = pd.DataFrame({
        "datum": [datetime.date(2026, 9, d) for d in (1, 2, 3)],
        "winkel_gemeten": True,
        # 1: open en niet in de agenda   -> geen afwijking
        # 2: open maar agenda zegt dicht -> afwijking
        # 3: dicht en agenda zegt niets  -> afwijking
        "winkel_open": [True, True, False],
    })
    a = ag.lees_ics(_ics("SUMMARY:DICHT: verlof\nDTSTART;VALUE=DATE:20260902"))
    uit = ag.afwijkingen(kal, a)
    assert len(uit) == 2
    assert set(uit["datum"]) == {datetime.date(2026, 9, 2), datetime.date(2026, 9, 3)}
    assert kal.shape == (3, 3)  # onaangeroerd


def test_afwijkingen_zonder_agenda_is_leeg_en_niet_stuk():
    kal = _kalender(["2026-09-01"])
    uit = ag.afwijkingen(kal, ag.Agenda(bruikbaar=False))
    assert uit.empty


# --- de grens van de prognose -------------------------------------------

def test_zonder_agenda_reikt_de_prognose_niet_voorbij_de_meting():
    grens, reden = ag.prognose_grens(
        ag.Agenda(bruikbaar=False, reden_onbruikbaar="geen feed ingesteld"),
        datetime.date(2026, 8, 7))
    assert grens == datetime.date(2026, 8, 7)
    assert "geen feed ingesteld" in reden


def test_agenda_die_verder_reikt_schuift_de_grens_op():
    a = ag.lees_ics(_ics(
        "SUMMARY:DICHT: zomersluiting\n"
        "DTSTART;VALUE=DATE:20261201\nDTEND;VALUE=DATE:20261203"))
    grens, reden = ag.prognose_grens(a, datetime.date(2026, 8, 7))
    assert grens == datetime.date(2026, 12, 2)
    assert "2026-12-02" in reden


def test_agenda_die_niet_verder_reikt_schuift_niets_op():
    a = ag.lees_ics(_ics("SUMMARY:DICHT: oud\nDTSTART;VALUE=DATE:20250401"))
    grens, reden = ag.prognose_grens(a, datetime.date(2026, 8, 7))
    assert grens == datetime.date(2026, 8, 7)
    assert "niet voorbij de laatste meting" in reden
