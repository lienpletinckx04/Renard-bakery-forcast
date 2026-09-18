"""De agenda van de bakkerij als optionele kalenderbron (iCal).

Waarvoor dit bestaat: de prognose heeft de sluitingen van de komende maanden
nodig, en die staan in geen enkele dataset. De historiek meten we zelf (zie
`DREMPEL_OPEN` in canoniek.py), maar de toekomst kan alleen de bakkerij weten.
Het voorstel aan de klant is één agenda met een geheime iCal-link, die de
nachtelijke job uitleest (vraag 46).

DRIE REGELS DIE DEZE LAAG ONSCHADELIJK MAKEN

1. *Optioneel.* Geen feed betekent geen kolommen en geen aannames. `AGENDA_ICS_URL`
   niet ingevuld -> deze module wordt niet aangeroepen en de kalender is exact
   dezelfde als zonder. Besluit de klant het niet te gebruiken, dan blijft er
   niets van achter en is er niets om op te ruimen.

2. *De agenda overschrijft nooit een meting.* Voor dagen die gemeten zijn is de
   kassa de waarheid; de agenda is daar alleen een controle. `afwijkingen()`
   rapporteert waar de twee het oneens zijn, en muteert niets. Alleen voorbij het
   gemeten bereik is de agenda de enige bron.

3. *Half begrepen is niet begrepen.* Wat deze parser niet zeker weet, meldt hij
   en gebruikt hij niet: een herhalende reeks (RRULE), een titel zonder bekend
   voorvoegsel, een event met een uur in plaats van een hele dag. Stilzwijgend
   negeren is precies hoe een kalender foute data gaat produceren.

Geen nieuwe dependency: de parser leest de handvol iCal-velden die we afgesproken
hebben. Blijkt RRULE later toch nodig, dan komt `icalendar` erbij — maar niet
voor een spoor dat nog bevestigd moet worden.

TIJDZONE. Een hele-dag-event draagt geen tijdzone en is dus meteen een datum.
Een event met een uur draagt er wel een, en iCal zet dat uur in de praktijk vaak
in UTC (`...T060000Z`) of met een `TZID`-parameter. Zo'n uur wordt eerst naar
Europe/Brussels gezet en pas daarna tot een datum teruggebracht: een event dat
om 23:30 UTC begint, valt hier de dag erna.

Het ophalen van de feed staat bewust in een apart bestand (`agenda_ophaal.py`),
zodat alles hier zonder netwerk te lezen en te testen is.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd

# De projecttijdzone komt sinds 18 augustus 2026 uit bakkerij/tijd.py in
# plaats van een eigen ZoneInfo; ZoneInfo blijft hier alleen geïmporteerd om
# een TZID-parameter uit de feed op te zoeken.
from bakkerij.tijd import BRUSSEL, UTC

# De titelconventie uit vraag 46. Het voorvoegsel bepaalt de kolom; de rest van
# de titel is de reden, en die mag de UI letterlijk tonen.
KENMERKEN: dict[str, str] = {
    "DICHT": "gepland_dicht",
    "ANDERE UREN": "andere_uren",
    "PROMO": "promotie",
    "EVENT": "evenement",
}

KOLOMMEN = tuple(KENMERKEN.values())
REDENKOLOMMEN = tuple(f"{k}_reden" for k in KOLOMMEN)


@dataclass
class Agendadag:
    datum: dt.date
    kenmerk: str
    reden: str


@dataclass
class Agenda:
    """Het resultaat van één keer inlezen. Ook een mislukking is een resultaat.

    `tot` is de belangrijkste waarde in dit object: tot die datum reikt de kennis
    van de bakkerij. Daarna weet niemand of de zaak open is, en dat is wat het
    platform moet zeggen in plaats van te gokken.
    """

    dagen: list[Agendadag] = field(default_factory=list)
    van: dt.date | None = None
    tot: dt.date | None = None
    waarschuwingen: list[str] = field(default_factory=list)
    bruikbaar: bool = True
    reden_onbruikbaar: str = ""


def _ontvouw(tekst: str) -> list[str]:
    """iCal breekt lange regels af en laat ze doorlopen met een spatie of tab."""
    regels: list[str] = []
    for ruwe in tekst.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if ruwe[:1] in (" ", "\t") and regels:
            regels[-1] += ruwe[1:]
        else:
            regels.append(ruwe)
    return regels


def _ontsnap(tekst: str) -> str:
    r"""iCal ontsnapt komma, puntkomma, backslash en regeleinde in een tekstwaarde.

    Google schrijft `SUMMARY:DICHT: zomersluiting\, winkel en atelier`. Die
    backslash is opmaak van het formaat en geen leesteken van de bakker; hij
    hoort niet op een scherm. Een regeleinde wordt een spatie: een reden is bij
    ons één regel.
    """
    uit: list[str] = []
    ontsnapt = False
    for teken in tekst:
        if ontsnapt:
            uit.append(" " if teken in "nN" else teken)
            ontsnapt = False
        elif teken == "\\":
            ontsnapt = True
        else:
            uit.append(teken)
    return "".join(uit)


def _param(naam: str, sleutel: str) -> str:
    """Haal 'Europe/Brussels' uit 'DTSTART;TZID=Europe/Brussels'."""
    for stuk in naam.split(";")[1:]:
        links, _, rechts = stuk.partition("=")
        if links.strip().upper() == sleutel:
            return rechts.strip().strip('"')
    return ""


def _kale_datum(kern: str) -> dt.date | None:
    try:
        return dt.date(int(kern[:4]), int(kern[4:6]), int(kern[6:8]))
    except ValueError:
        return None


def _datum(waarde: str, tzid: str = "") -> tuple[dt.date | None, bool, str]:
    """(datum in Brusselse tijd, is_heledag, melding).

    Drie vormen komen voor: `20260801` (hele dag, geen tijdzone),
    `20260801T060000Z` (UTC) en `20260801T060000` met een `TZID`-parameter of
    zonder — dat laatste is 'zwevende' tijd en betekent lokaal bij wie de agenda
    bijhoudt. Een uur wordt eerst naar Europe/Brussels gezet en pas dan tot zijn
    datum teruggebracht, want anders valt een event van 23:30 UTC op de
    verkeerde dag.
    """
    kern = waarde.strip()
    if re.fullmatch(r"\d{8}", kern):
        return _kale_datum(kern), True, ""

    gesplitst = re.fullmatch(r"(\d{8})T(\d{2})(\d{2})(\d{2})(Z?)", kern)
    if gesplitst is None:
        return None, False, ""
    dag = _kale_datum(gesplitst.group(1))
    if dag is None:
        return None, False, ""
    try:
        klok = dt.time(int(gesplitst.group(2)), int(gesplitst.group(3)),
                       int(gesplitst.group(4)))
    except ValueError:
        return None, False, ""

    melding = ""
    if gesplitst.group(5) == "Z":
        zone = UTC
    elif tzid:
        try:
            zone = ZoneInfo(tzid)
        except (ZoneInfoNotFoundError, ValueError):
            # Onbekende zone: de datum kan hooguit een dag mis zijn, net als bij
            # een uur-event. Melden en lezen is hier beter dan weggooien, maar
            # stilzwijgend is het niet.
            zone, melding = BRUSSEL, (
                f"Onbekende tijdzone {tzid!r}: het uur is gelezen als Brusselse tijd")
    else:
        zone = BRUSSEL

    lokaal = dt.datetime.combine(dag, klok, tzinfo=zone).astimezone(BRUSSEL)
    return lokaal.date(), False, melding


def _kenmerk_van_titel(titel: str) -> tuple[str | None, str]:
    """Splits 'DICHT: zomersluiting' in ('gepland_dicht', 'zomersluiting')."""
    for voorvoegsel, kolom in KENMERKEN.items():
        if titel.upper().startswith(voorvoegsel):
            rest = titel[len(voorvoegsel):].lstrip(": ").strip()
            return kolom, rest
    return None, titel.strip()


def lees_ics(tekst: str) -> Agenda:
    """Lees een iCal-tekst naar dagen met een kenmerk.

    Werkt op tekst en niet op een URL, zodat dit te testen is zonder netwerk en
    zonder ooit een echte agenda nodig te hebben.
    """
    agenda = Agenda()
    if "BEGIN:VEVENT" not in tekst:
        agenda.bruikbaar = False
        agenda.reden_onbruikbaar = "Het opgehaalde bestand bevat geen enkel agenda-item"
        return agenda

    per_datum: dict[tuple[dt.date, str], str] = {}
    gezien: set[dt.date] = set()

    for blok in tekst.split("BEGIN:VEVENT")[1:]:
        blok = blok.split("END:VEVENT")[0]
        titel = ""
        start = eind = None
        heledag_start = heledag_eind = True
        herhaalt = False
        tijdmeldingen: list[str] = []

        for regel in _ontvouw(blok):
            naam, _, waarde = regel.partition(":")
            veld = naam.split(";")[0].upper()
            if veld == "SUMMARY":
                titel = _ontsnap(waarde).strip()
            elif veld == "DTSTART":
                start, heledag_start, melding = _datum(waarde, _param(naam, "TZID"))
                tijdmeldingen += [melding] if melding else []
            elif veld == "DTEND":
                eind, heledag_eind, melding = _datum(waarde, _param(naam, "TZID"))
                tijdmeldingen += [melding] if melding else []
            elif veld == "RRULE":
                herhaalt = True

        if start is None:
            agenda.waarschuwingen.append(
                f"Item overgeslagen: geen leesbare begindatum (titel: {titel!r})")
            continue
        if herhaalt:
            agenda.waarschuwingen.append(
                f"Item overgeslagen: herhalende reeks wordt niet gelezen "
                f"({titel!r}, vanaf {start}). Zet de dagen los in de agenda.")
            continue
        if not heledag_start:
            agenda.waarschuwingen.append(
                f"Item met een uur in plaats van een hele dag: gelezen als de "
                f"hele dag {start} in Brusselse tijd ({titel!r})")
        for melding in tijdmeldingen:
            agenda.waarschuwingen.append(f"{melding} ({titel!r}, {start})")

        kenmerk, reden = _kenmerk_van_titel(titel)
        if kenmerk is None:
            agenda.waarschuwingen.append(
                f"Item overgeslagen: titel begint niet met "
                f"{'/'.join(KENMERKEN)} ({titel!r}, {start})")
            continue

        # DTEND is bij een hele-dag-event exclusief: 1 t/m 15 aug staat er als
        # DTSTART 0801 en DTEND 0816. Ontbreekt DTEND, dan is het één dag. Bij
        # een event met een uur is DTEND het einduur zelf en dus niet exclusief;
        # een dag aftrekken zou daar de laatste dag opeten.
        if eind is None:
            laatste = start
        elif heledag_eind:
            laatste = max(eind - dt.timedelta(days=1), start)
        else:
            laatste = max(eind, start)

        dag = start
        while dag <= laatste:
            per_datum.setdefault((dag, kenmerk), reden)
            gezien.add(dag)
            dag += dt.timedelta(days=1)

    agenda.dagen = [Agendadag(datum=d, kenmerk=k, reden=r)
                    for (d, k), r in sorted(per_datum.items())]
    if gezien:
        agenda.van, agenda.tot = min(gezien), max(gezien)
    return agenda


def _naar_frame(agenda: Agenda) -> pd.DataFrame:
    """Één rij per datum, één kolom per kenmerk, plus de reden ernaast.

    Sinds 18 augustus 2026 privé: alleen `verrijk_kalender` gebruikt dit, en
    een publieke naam zonder externe aanroepers nodigt uit tot een tweede pad
    langs de kalender heen.
    """
    kolommen = ["datum", *KOLOMMEN, *REDENKOLOMMEN]
    if not agenda.dagen:
        return pd.DataFrame(columns=kolommen)

    rijen: dict[dt.date, dict] = {}
    for d in agenda.dagen:
        rij = rijen.setdefault(d.datum, {"datum": d.datum})
        rij[d.kenmerk] = True
        rij[f"{d.kenmerk}_reden"] = d.reden

    df = pd.DataFrame(sorted(rijen.values(), key=lambda r: r["datum"]))
    # Een kenmerk dat in deze agenda niet voorkomt, krijgt toch zijn kolom: het
    # frame heeft altijd dezelfde vorm, zodat de consument niet hoeft te weten
    # wat er die maand in de agenda stond.
    for kolom in KOLOMMEN:
        df[kolom] = df[kolom].fillna(False).astype(bool) if kolom in df else False
    for kolom in REDENKOLOMMEN:
        df[kolom] = df[kolom].fillna("") if kolom in df else ""
    return df[kolommen]


def verrijk_kalender(kalender: pd.DataFrame, agenda: Agenda) -> pd.DataFrame:
    """Voeg de agendakolommen toe. Zonder bruikbare agenda: ongewijzigd terug.

    Wat deze functie NIET doet: `winkel_open` of `winkel_gemeten` aanraken. Die
    komen uit de meting en de meting blijft de waarheid. De agendakolommen staan
    ernaast, zodat elke consument zelf kan kiezen — en zodat het weghalen van dit
    spoor een kolomverwijdering is en geen herberekening.
    """
    if not agenda.bruikbaar or not agenda.dagen:
        return kalender

    frame = _naar_frame(agenda)
    uit = kalender.merge(frame, on="datum", how="left")
    for kolom in KOLOMMEN:
        uit[kolom] = uit[kolom].fillna(False).astype(bool)
    for kolom in REDENKOLOMMEN:
        uit[kolom] = uit[kolom].fillna("")
    return uit


def afwijkingen(kalender: pd.DataFrame, agenda: Agenda) -> pd.DataFrame:
    """Waar zijn de meting en de agenda het oneens, binnen het gemeten bereik?

    Dit muteert niets en het is de reden dat de agenda waarde heeft ook als we
    hem niet gebruiken om te rekenen: twee onafhankelijke bronnen die over
    dezelfde 54 sluitingsdagen moeten overeenkomen, is een controle die één
    gemeten drempel niet kan geven.
    """
    leeg = pd.DataFrame(columns=["datum", "winkel_open", "gepland_dicht", "reden", "soort"])
    if not agenda.bruikbaar or not agenda.dagen:
        return leeg

    verrijkt = verrijk_kalender(kalender, agenda)
    gemeten = verrijkt[verrijkt["winkel_gemeten"]].copy()
    if gemeten.empty:
        return leeg

    dicht_volgens_agenda = gemeten["gepland_dicht"]
    open_volgens_kassa = gemeten["winkel_open"]

    soort = pd.Series("", index=gemeten.index, dtype=object)
    soort[open_volgens_kassa & dicht_volgens_agenda] = (
        "agenda zegt dicht, de kassa verkocht")
    soort[~open_volgens_kassa & ~dicht_volgens_agenda] = (
        "kassa zegt dicht, de agenda niet")

    uit = gemeten.loc[soort != "", ["datum", "winkel_open", "gepland_dicht",
                                    "gepland_dicht_reden"]].copy()
    uit = uit.rename(columns={"gepland_dicht_reden": "reden"})
    uit["soort"] = soort[soort != ""]
    return uit.reset_index(drop=True)


def prognose_grens(agenda: Agenda, gemeten_tot: dt.date) -> tuple[dt.date, str]:
    """Tot welke datum mag de prognose iets beweren, en waarom niet verder.

    Harde regel 8, toegepast op een input die er nog niet is. Zonder agenda
    reikt de prognose niet voorbij de meting, en dat wordt gezegd in plaats
    van gegokt.
    """
    if not agenda.bruikbaar:
        return gemeten_tot, (
            f"Geen bruikbare agenda ({agenda.reden_onbruikbaar}); "
            "geplande sluitingen na de laatste meting zijn onbekend")
    if agenda.tot is None:
        return gemeten_tot, (
            "De agenda is leeg; geplande sluitingen na de laatste meting zijn onbekend")
    if agenda.tot <= gemeten_tot:
        return gemeten_tot, (
            f"De agenda reikt tot {agenda.tot} en dus niet voorbij de laatste meting")
    return agenda.tot, (
        f"De agenda reikt tot {agenda.tot}; daarna is niet bekend of de zaak open is")
