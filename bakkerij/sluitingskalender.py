"""De sluitingskalender uit de database: uitspraken per dag en weekregels.

WAAROM DEZE MODULE NAAST `sluitingsdagen.py` BESTAAT

`sluitingsdagen.py` leest een bestand in git, en dat bestand heeft één
fundamentele beperking die geen code oplost: het is een JSON-bestand in een
git-repository, en de zin op het prognosescherm — "vul de sluitingslijst aan
en de prognose volgt" — vroeg daarmee een handeling die een CFO per definitie
niet kan uitvoeren. Deze module is de databasekant van dezelfde invoer
(migratie 011 draagt de tabellen, 012 de schrijffunctie voor PostgREST),
zodat het scherm Sluitingsdagen die handeling wél kan aanbieden. Het bestand
blijft bestaan als eenmalige invoer en als historisch record; zie
docs/sluitingskalender-ontwerp.md.

DRIE TOESTANDEN, NIET TWEE

Een dag is bevestigd dicht, bevestigd open, of onbeantwoord — en dat laatste
is een derde toestand, geen open (harde regel 8: onbekend is niet hetzelfde
als open). "Bevestigd open" is echte informatie: bij Renard is 6 januari
(galette) een van de drukste dagen van het jaar, en dat moet iemand kunnen
zeggen zonder dat het platform de feestdag als sluiting behandelt. Een
bevestigd-open dag wordt gewoon voorspeld; wat verdwijnt is het voorbehoud
"geen sluiting bekend" voor die dag.

DE RANGORDE VAN DE BRONNEN: AGENDA > DATABASE > BESTAND

Drie bronnen kunnen iets over dezelfde dag zeggen. De agenda (iCal, vraag 46)
komt van de bakkerij zelf en gaat voor; de database komt van de beheerder via
het scherm; het bestand is de oudste en wijkt voor beide. Concreet betekent
dat twee dingen:

  * een dag die de agenda dicht noemt, blijft dicht, óók als de database hem
    bevestigd open noemt — dat conflict wordt gemeld, niet stil beslecht
    (`agenda_conflicten`);
  * een dag die de database bevestigd open noemt, haalt een dicht-dag uit
    het bestand weg (`zonder_dagen`) — de beheerder heeft hem later en
    bewuster ingevoerd dan de lijst.

Binnen de database zelf wint de uitspraak van de regel: "elke maandag dicht"
plus "maandag 6 januari bevestigd open" betekent dat 6 januari open is. Een
uitspraak gaat over één dag en is daarmee de meest specifieke bewering.

NET ALS `sluitingsdagen.py`: DE METING BLIJFT DE WAARHEID. Deze module raakt
`winkel_open` en `winkel_gemeten` nooit aan. De uitkomst is dezelfde kolom
`gepland_dicht` met dezelfde `gepland_dicht_reden` — één begrip "gepland
dicht", nu met drie mogelijke bronnen — plus één nieuwe kolom
`bevestigd_open` die alleen het voorbehoud stuurt en nooit het venster.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import holidays
import pandas as pd

from bakkerij import sluitingsdagen
from bakkerij.sluitingsdagen import REDEN_MAX, Sluiting

#: De twee toestanden die een rij in de tabel kan dragen. "Onbekend" staat er
#: bewust niet in: een dag zonder rij ís de derde toestand, en een expliciete
#: rij "onbekend" zou dezelfde informatie dubbel opslaan (migratie 011 zegt
#: hetzelfde).
TOESTANDEN = ("dicht", "open")

#: Waar een uitspraak vandaan komt: een bevestigde feestdagkandidaat, een
#: eigen periode (jaarlijkse sluiting, verbouwing), of de eenmalige overname
#: uit config/sluitingsdagen.json.
BRONNEN = ("feestdag", "periode", "bestand")

#: De nieuwe kalenderkolom. Alleen waar voor dagen die een beheerder
#: uitdrukkelijk open heeft verklaard; stuurt het voorbehoud op het
#: prognosescherm en verder niets.
OPEN_KOLOM = "bevestigd_open"

#: De reden op het scherm voor een dag die door een weekregel dicht is en
#: waar de regel zelf geen reden draagt. Nederlands, zoals elke reden in deze
#: keten: de invoer van de beheerder is taalvrij en wordt niet vertaald.
REDEN_REGEL = "vaste sluitingsdag"

@dataclass(frozen=True)
class Uitspraak:
    """Eén uitspraak van de beheerder over één dag."""

    datum: dt.date
    toestand: str
    reden: str
    bron: str

    def __post_init__(self) -> None:
        if self.toestand not in TOESTANDEN:
            raise ValueError(
                f'De toestand "{self.toestand}" bestaat niet; het is een van '
                f"{TOESTANDEN}. Onbekend is geen toestand maar het ontbreken "
                "van een uitspraak."
            )
        if self.bron not in BRONNEN:
            raise ValueError(
                f'De bron "{self.bron}" bestaat niet; het is een van {BRONNEN}.'
            )
        if len(self.reden) > REDEN_MAX:
            raise ValueError(
                f"De reden bij {self.datum} is langer dan {REDEN_MAX} tekens; "
                "ze komt op een scherm terecht."
            )


@dataclass(frozen=True)
class Weekregel:
    """Een vaste wekelijkse sluitingsdag: "elke maandag dicht, vanaf X".

    `tot` mag None zijn en betekent dan "tot nader order" — precies het stuk
    dat losse datums niet kunnen: die lopen per definitie een keer af.
    `weekdag` telt zoals overal in dit project: 0 is maandag, 6 is zondag.
    """

    weekdag: int
    vanaf: dt.date
    tot: dt.date | None
    reden: str

    def __post_init__(self) -> None:
        if not 0 <= self.weekdag <= 6:
            raise ValueError(
                f"weekdag {self.weekdag} bestaat niet; 0 (maandag) tot en "
                "met 6 (zondag)."
            )
        if self.tot is not None and self.tot < self.vanaf:
            raise ValueError(
                f"De regel vanaf {self.vanaf} eindigt op {self.tot}, en dat "
                "is eerder. Wissel de datums om."
            )
        if len(self.reden) > REDEN_MAX:
            raise ValueError(
                f"De reden bij de regel vanaf {self.vanaf} is langer dan "
                f"{REDEN_MAX} tekens; ze komt op een scherm terecht."
            )


def dichte_dagen(uitspraken: tuple[Uitspraak, ...]) -> dict[dt.date, str]:
    """datum -> reden voor elke bevestigd-dichte dag. Zelfde vorm als
    `sluitingsdagen.dagen_met_reden`, en met dezelfde terugval voor een
    lege reden."""
    return {
        u.datum: u.reden or sluitingsdagen.REDEN_ONBEKEND
        for u in uitspraken
        if u.toestand == "dicht"
    }


def open_dagen(uitspraken: tuple[Uitspraak, ...]) -> set[dt.date]:
    """De dagen die de beheerder uitdrukkelijk open heeft verklaard."""
    return {u.datum for u in uitspraken if u.toestand == "open"}


def regel_dagen(regels: tuple[Weekregel, ...],
                van: dt.date, tot: dt.date) -> dict[dt.date, str]:
    """De weekregels uitgerold naar losse dichte dagen binnen [van, tot].

    De kalender begrenst het bereik; een regel zonder einddatum rolt dus
    precies zo ver uit als de kalender reikt, en de volgende bouw rolt hem
    vanzelf verder. Dat is het hele punt van een regel: hij is nooit "op".

    Bewust geen eigen vangrail op de omvang van het bereik: de canonieke
    kalender is de aanroeper en die beslaat de volle kassahistoriek plus het
    prognosevenster (op 19 aug 2026 al ruim zeven jaar). Een grens hier zou
    de bouw laten omvallen op precies de data waarvoor hij bestaat — dat is
    op 19 augustus 2026 één keer echt gebeurd, bij de eerste run tegen de
    volledige kalender. De lus is per week, dus ook decennia blijven goedkoop.
    """
    if tot < van:
        return {}
    uit: dict[dt.date, str] = {}
    for regel in regels:
        dag = max(van, regel.vanaf)
        # Naar de eerstvolgende juiste weekdag springen in plaats van dag
        # voor dag proberen: een regel over vijf jaar kalender blijft dan
        # een handvol stappen per week.
        dag += dt.timedelta(days=(regel.weekdag - dag.weekday()) % 7)
        einde = min(tot, regel.tot) if regel.tot is not None else tot
        while dag <= einde:
            uit.setdefault(dag, regel.reden or REDEN_REGEL)
            dag += dt.timedelta(days=7)
    return uit


def agenda_conflicten(kalender: pd.DataFrame,
                      uitspraken: tuple[Uitspraak, ...]) -> tuple[dt.date, ...]:
    """De bevestigd-open dagen die een eerdere bron al dicht had verklaard.

    Aan te roepen VÓÓR `verrijk_kalender`, op de kalender zoals hij dan
    staat: alles wat daar al `gepland_dicht` is, komt van de agenda (die
    eerder draait) en gaat voor. Het conflict wordt gemeld en de open-dag
    wordt niet gezet — twee bronnen die elkaar tegenspreken is iets wat een
    mens moet zien, geen keuze die deze laag stil maakt.
    """
    if sluitingsdagen.KOLOM not in kalender.columns:
        return ()
    dicht = {
        pd.Timestamp(datum).date()
        for datum, v in zip(
            kalender["datum"],
            _waarheid(kalender[sluitingsdagen.KOLOM]),
            strict=True,
        )
        if v
    }
    return tuple(sorted(open_dagen(uitspraken) & dicht))


def verrijk_kalender(kalender: pd.DataFrame,
                     uitspraken: tuple[Uitspraak, ...],
                     regels: tuple[Weekregel, ...]) -> pd.DataFrame:
    """Zet de databasekant in de kalender: `gepland_dicht` erbij voor dichte
    uitspraken en regeldagen, `bevestigd_open` voor open uitspraken.

    Dezelfde OF-semantiek als `sluitingsdagen.verrijk_kalender`: een
    bestaande dicht-markering blijft staan, een bestaande reden gaat voor.
    De regel wijkt voor de uitspraak (een uitspraak over één dag is
    specifieker), en een open-uitspraak wijkt voor een dag die al dicht
    stond — dat conflict hoort de aanroeper vooraf te melden via
    `agenda_conflicten`.

    Raakt `winkel_open` en `winkel_gemeten` niet aan. De kolom
    `bevestigd_open` komt er ook zonder uitspraken, zodat de CSV-vorm niet
    afhangt van de vraag of er al iets bevestigd is.
    """
    uit = kalender.copy()
    datums = uit["datum"].map(lambda d: pd.Timestamp(d).date())

    beantwoord = {u.datum for u in uitspraken}
    dicht = dichte_dagen(uitspraken)
    if not uit.empty:
        for dag, reden in regel_dagen(regels, datums.min(), datums.max()).items():
            if dag not in beantwoord:
                dicht[dag] = reden

    dicht_lijst = datums.map(dicht.__contains__)
    redenen = datums.map(lambda d: dicht.get(d, ""))

    if sluitingsdagen.KOLOM in uit.columns:
        al_dicht = _waarheid(uit[sluitingsdagen.KOLOM].fillna(False))
        uit[sluitingsdagen.KOLOM] = al_dicht | dicht_lijst
    else:
        al_dicht = pd.Series(False, index=uit.index)
        uit[sluitingsdagen.KOLOM] = dicht_lijst

    if sluitingsdagen.REDENKOLOM in uit.columns:
        bestaand = uit[sluitingsdagen.REDENKOLOM].fillna("")
        uit[sluitingsdagen.REDENKOLOM] = bestaand.where(bestaand != "", redenen)
    else:
        uit[sluitingsdagen.REDENKOLOM] = redenen

    open_ = open_dagen(uitspraken)
    open_lijst = datums.map(open_.__contains__) & ~al_dicht & ~dicht_lijst
    if OPEN_KOLOM in uit.columns:
        uit[OPEN_KOLOM] = _waarheid(uit[OPEN_KOLOM].fillna(False)) | open_lijst
    else:
        uit[OPEN_KOLOM] = open_lijst

    return uit


def zonder_dagen(sluitingen: tuple[Sluiting, ...],
                 dagen: set[dt.date]) -> tuple[Sluiting, ...]:
    """De bestandslijst met de gegeven dagen eruit geknipt.

    Voor de rangorde database > bestand: een dag die de beheerder bevestigd
    open heeft verklaard, mag niet alsnog dicht worden gezet door een oudere
    periode uit config/sluitingsdagen.json. Een periode waar een dag uit
    wegvalt, splitst in twee kortere periodes met dezelfde reden; de
    dekkingsvraag verandert niet, want `dekking_tot` hoort op de
    óngefilterde lijst te draaien — wat de lijst beweerde, blijft beweerd,
    ook waar een nieuwere bron er overheen gaat.
    """
    if not dagen:
        return sluitingen
    uit: list[Sluiting] = []
    for s in sluitingen:
        begin: dt.date | None = None
        dag = s.van
        while dag <= s.tot:
            if dag in dagen:
                if begin is not None:
                    uit.append(Sluiting(van=begin, tot=dag - dt.timedelta(days=1),
                                        reden=s.reden))
                    begin = None
            elif begin is None:
                begin = dag
            dag += dt.timedelta(days=1)
        if begin is not None:
            uit.append(Sluiting(van=begin, tot=s.tot, reden=s.reden))
    return tuple(uit)


def onbekende_dagen(dagen, *,
                    dekking_tot: dt.date | None,
                    beantwoord: set[dt.date]) -> tuple[dt.date, ...]:
    """De prognosedagen waarover geen enkele bron een uitspraak doet.

    Dit is het per-dag-voorbehoud dat het venstervoorbehoud vervangt: een dag
    is bekend als hij binnen het bereik van de bestandslijst valt (tot en met
    `dekking_tot` heeft iemand de lijst ingevuld) óf als er een uitspraak in
    de database over bestaat — dicht of open, allebei zijn een antwoord.
    Dichte dagen staan sowieso niet in `dagen` (de zeef sloeg ze al over);
    wat hier terugkomt zijn de dagen waarvoor de prognose "open" aanneemt
    zonder dat iemand dat gezegd heeft.
    """
    grens = dekking_tot or dt.date.min
    return tuple(
        d for d in (pd.Timestamp(dag).date() for dag in dagen)
        if d > grens and d not in beantwoord
    )


def feestdagkandidaten(vanaf: dt.date, maanden: int = 12,
                       taal: str = "nl") -> list[tuple[dt.date, str]]:
    """De Belgische feestdagen in de komende `maanden`, als (datum, naam).

    De kandidatenlijst voor het scherm: het platform weet de feestdagen al
    (de `holidays`-bibliotheek levert elk jaar, onbeperkt vooruit), dus het
    scherm hoeft geen lege datumkiezer te zijn maar een bevestigingslijst —
    twee klikken per rij, één keer per jaar. Een lege datumkiezer is een
    klus, en klussen gebeuren niet.
    """
    tot = vanaf + dt.timedelta(days=maanden * 31)
    jaren = sorted({vanaf.year, tot.year})
    feest = holidays.Belgium(years=jaren, language=taal)
    return sorted(
        (datum, naam) for datum, naam in feest.items() if vanaf <= datum <= tot
    )


def _waarheid(reeks: pd.Series) -> pd.Series:
    """Zelfde CSV-veilige boolconversie als `sluitingsdagen._waarheid`, en
    bewust een doorverwijzing en geen kopie: één definitie van waarheid."""
    return sluitingsdagen._waarheid(reeks)
