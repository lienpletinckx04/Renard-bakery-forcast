"""Sluitingsdagen die de bakkerij vooraf weet, als invoer voor de prognose.

WAAROM DEZE MODULE BESTAAT, EN WAAROM ZE NIET DE EERSTE POGING IS

`sources/agenda.py` beschrijft het probleem al precies: "de prognose heeft de
sluitingen van de komende maanden nodig, en die staan in geen enkele dataset.
De historiek meten we zelf, maar de toekomst kan alleen de bakkerij weten."
Die module leest daarvoor een iCal-feed en zet de kolom `gepland_dicht`.

Twee dingen ontbraken, en samen leverden ze op 14 augustus 2026 een omzet-
projectie voor een week waarin de zaak dicht is:

  1. De feed wacht op vraag 46. Zolang de klant geen agenda-link geeft, is
     `gepland_dicht` overal False en weet het platform van geen enkele
     toekomstige sluiting.
  2. En zelfs mét feed werd de kolom nergens gebruikt om te beslissen welke
     dagen een prognose krijgen. `canoniek.prognosevenster` sloeg alleen dagen
     over die *gemeten én dicht* waren -- en een toekomstige dag is per
     definitie niet gemeten. De kolom bestond, niemand keek ernaar.

Deze module lost (1) op met een tweede bron die niet op de klant wacht: een
configbestand dat wij of de beheerder bijhoudt, in dezelfde kolommen als de
agenda. `canoniek.prognosevenster` lost (2) op.

EEN BRON MEER, GEEN BEGRIP MEER. De uitkomst is bewust dezelfde kolom
`gepland_dicht` met dezelfde `gepland_dicht_reden`. Er is één begrip "gepland
dicht" met twee mogelijke bronnen, niet twee soorten sluiting. Wie later de
agenda aansluit, hoeft niets aan de prognose te veranderen.

DE MEETING BLIJFT DE WAARHEID. Net als de agenda raakt deze laag `winkel_open`
en `winkel_gemeten` nooit aan. Voor een dag die gemeten is, is de kassa de
bron; een configregel over het verleden is daar hoogstens een controle, en
`afwijkingen()` rapporteert dat zonder iets te muteren. Alleen voorbij het
gemeten bereik is deze lijst de enige bron die er is.

Bestandsvorm (`config/sluitingsdagen.json`, sinds 19 aug 2026 IN git —
het zijn openingsdagen, geen klantdata, en de nachtelijke run op een runner
heeft ze nodig):

    {"sluitingen": [
      {"van": "2026-08-17", "tot": "2026-08-23", "reden": "Zomersluiting"},
      {"van": "2026-12-25", "reden": "Kerstmis"}
    ]}

`tot` mag weg voor één dag. `reden` mag weg, maar dan staat er op het scherm
"gepland gesloten" zonder uitleg -- en een sluiting zonder reden is precies
het soort cijfer waar een CFO naar terugvraagt. Vul hem in.

EN DAN DE VRAAG DIE DE LIJST ZELF NIET KAN BEANTWOORDEN

Een lijst die je met de hand bijhoudt, is onvolledig tot iemand hem aanvult, en
een onvolledige lijst ziet er van binnenuit precies uit als een volledige. Op
15 augustus 2026 stond er een omzetverwachting op twee dagen waarop de zaak in
verlof was: de zeef van 14 augustus werkte, maar de lijst die hem voedt kende
alleen de week erna. Dezelfde fout op het scherm, via een andere weg.

`lopende_sluiting()` is de wacht daarop. Ze verzint niets en snijdt niets weg
-- dat zou het platform een sluitingskalender laten bedenken, en dat is op
14 augustus uitdrukkelijk afgewezen. Ze meldt alleen wat ze ziet: de meting
eindigt in een gesloten reeks, de lijst verklaart die reeks niet, en achter dat
gat staan prognosedagen. Het platform weet dan niet of de zaak open is -- maar
het weet wel dát het dat niet weet, en harde regel 8 zegt dat het dat hardop
hoort te zeggen.
"""

from __future__ import annotations

import datetime as dt
import itertools
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from bakkerij.taal import dagnummer, maand_vol, t

#: Meer dan dit in één periode is geen sluiting meer maar een vergissing --
#: een bakkerij die vier maanden dicht is, heeft een ander probleem dan een
#: prognose. Dezelfde gedachte als MAX_WINKELS in winkels.py.
MAX_DAGEN_PER_PERIODE = 120

#: Ruim boven elk realistisch aantal (feestdagen + sluitingsweken over meerdere
#: jaren), en laag genoeg om een geplakt bestand met duizenden regels te weigeren.
MAX_PERIODES = 400

REDEN_MAX = 120

#: De naam van de kolommen die deze module vult. Gelijk aan die van de agenda,
#: bewust: zie de moduledocstring.
KOLOM = "gepland_dicht"
REDENKOLOM = "gepland_dicht_reden"

#: Wat er op het scherm staat als iemand een sluiting invoert zonder reden.
REDEN_ONBEKEND = "gepland gesloten"


@dataclass(frozen=True)
class Sluiting:
    """Eén aangekondigde periode. `tot` is inclusief."""

    van: dt.date
    tot: dt.date
    reden: str

    @property
    def dagen(self) -> int:
        return (self.tot - self.van).days + 1


def _datum(waarde, veld: str) -> dt.date:
    """Van JSON-waarde naar `date`, met een leesbare fout in plaats van een
    ValueError uit de standaardbibliotheek."""
    if not isinstance(waarde, str):
        raise TypeError(
            f'Het veld "{veld}" moet een datum als tekst zijn (JJJJ-MM-DD), '
            f"niet {type(waarde).__name__}."
        )
    try:
        return dt.date.fromisoformat(waarde.strip())
    except ValueError as fout:
        raise ValueError(
            f'"{waarde}" is geen geldige datum in het veld "{veld}". '
            "De vorm is JJJJ-MM-DD, bijvoorbeeld 2026-08-17."
        ) from fout


def parse_sluitingen(tekst: str) -> tuple[Sluiting, ...]:
    """Van bestandsinhoud naar een getoetste lijst.

    Elke afwijking is een fout met reden en geen stille correctie. Dat is hier
    strenger dan gebruikelijk en met opzet: een sluitingsdag die door een
    typefout niet meedoet, levert een omzetverwachting op voor een dag dat de
    deur dicht is -- precies het cijfer dat deze module moet voorkomen.
    """
    try:
        ruw = json.loads(tekst)
    except json.JSONDecodeError as fout:
        raise ValueError(
            f"Het sluitingsbestand is geen geldige JSON: {fout}"
        ) from fout

    if not isinstance(ruw, dict) or not isinstance(ruw.get("sluitingen"), list):
        raise TypeError(
            'Het sluitingsbestand mist het veld "sluitingen" (lijst).'
        )
    if len(ruw["sluitingen"]) > MAX_PERIODES:
        raise ValueError(
            f"Meer dan {MAX_PERIODES} sluitingsperiodes; dat is geen "
            "sluitingskalender meer maar een vergissing."
        )

    sluitingen: list[Sluiting] = []
    for rij in ruw["sluitingen"]:
        if not isinstance(rij, dict):
            raise TypeError(
                "Elke sluiting is een object met minstens een veld \"van\"."
            )
        if "van" not in rij:
            raise ValueError('Een sluiting zonder veld "van" zegt niets.')

        van = _datum(rij["van"], "van")
        tot = _datum(rij["tot"], "tot") if rij.get("tot") is not None else van

        if tot < van:
            raise ValueError(
                f'De sluiting van {van} loopt tot {tot}, en dat is eerder. '
                'Wissel "van" en "tot" om.'
            )
        periode = (tot - van).days + 1
        if periode > MAX_DAGEN_PER_PERIODE:
            raise ValueError(
                f"De sluiting van {van} tot {tot} duurt {periode} dagen, meer "
                f"dan de {MAX_DAGEN_PER_PERIODE} die deze lijst aanvaardt. "
                "Controleer of er geen jaartal verkeerd staat."
            )

        reden_ruw = rij.get("reden", "")
        if not isinstance(reden_ruw, str):
            raise TypeError(
                f"De reden bij de sluiting van {van} moet tekst zijn."
            )
        reden = re.sub(r"\s+", " ", reden_ruw).strip()
        if len(reden) > REDEN_MAX:
            raise ValueError(
                f"De reden bij de sluiting van {van} is langer dan "
                f"{REDEN_MAX} tekens; ze komt op een scherm terecht."
            )

        sluitingen.append(Sluiting(van=van, tot=tot, reden=reden))

    geordend = tuple(sorted(sluitingen, key=lambda s: (s.van, s.tot)))
    for vorige, volgende in itertools.pairwise(geordend):
        if volgende.van <= vorige.tot:
            raise ValueError(
                f"De periodes {vorige.van}..{vorige.tot} en "
                f"{volgende.van}..{volgende.tot} overlappen. Voeg ze samen; "
                "twee redenen voor dezelfde dag is er één te veel."
            )
    return geordend


def lees_sluitingen(pad: Path) -> tuple[Sluiting, ...]:
    """Leeg zonder bestand. Dan weet het platform van geen sluitingen, en dat
    is een andere uitspraak dan "er zijn er geen" -- zie `dekking_tot`."""
    if not pad.exists():
        return ()
    return parse_sluitingen(pad.read_text(encoding="utf-8"))


def dagen_met_reden(sluitingen: tuple[Sluiting, ...]) -> dict[dt.date, str]:
    """datum -> reden, één rij per gesloten dag. Eén keer opbouwen, vaak
    bevragen -- dezelfde vorm als `_status_per_dag` in canoniek.py."""
    uit: dict[dt.date, str] = {}
    for s in sluitingen:
        dag = s.van
        while dag <= s.tot:
            uit[dag] = s.reden or REDEN_ONBEKEND
            dag += dt.timedelta(days=1)
    return uit


def dekking_tot(sluitingen: tuple[Sluiting, ...]) -> dt.date | None:
    """De laatste dag waarover deze lijst iets beweert, of None.

    Dezelfde rol als `Agenda.tot`: voorbij deze datum betekent "geen sluiting
    in de lijst" niet "open", maar "onbekend". De prognose mag dat verschil
    niet wegpoetsen, en `contract.prognose` zegt het op het scherm.

    Let op wat dit NIET is: een garantie dat elke dag tot hier gecontroleerd
    is. Het is de laatste dag die iemand heeft ingevoerd. Verder reikt de
    kennis van deze lijst niet, en dus reikt de bewering niet verder.
    """
    return max((s.tot for s in sluitingen), default=None)


def verrijk_kalender(kalender: pd.DataFrame,
                     sluitingen: tuple[Sluiting, ...]) -> pd.DataFrame:
    """Zet `gepland_dicht` en `gepland_dicht_reden` uit de configlijst.

    Werkt samen met `agenda.verrijk_kalender` in willekeurige volgorde: bestaat
    de kolom al, dan wordt er een OF op gedaan en blijft een bestaande reden
    staan waar deze lijst er geen heeft. Twee bronnen die "dicht" zeggen, is
    geen conflict; twee bronnen die iets anders zeggen, is een afwijking en
    die hoort in `afwijkingen()`, niet in een stille keuze.

    Raakt `winkel_open` en `winkel_gemeten` niet aan. Zie de moduledocstring.
    """
    if not sluitingen:
        return kalender

    per_dag = dagen_met_reden(sluitingen)
    uit = kalender.copy()
    datums = uit["datum"].map(lambda d: pd.Timestamp(d).date())

    uit_lijst = datums.map(per_dag.__contains__)
    redenen = datums.map(lambda d: per_dag.get(d, ""))

    if KOLOM in uit.columns:
        # `_waarheid` en niet `.astype(bool)`: dit is letterlijk de aanroep waar
        # de docstring van `_waarheid` voor waarschuwt. Een bestaande
        # `gepland_dicht`-kolom die als object binnenkomt (één NaN uit de CSV
        # volstaat) zou hier elke dag als gepland-dicht markeren.
        uit[KOLOM] = _waarheid(uit[KOLOM].fillna(False)) | uit_lijst
    else:
        uit[KOLOM] = uit_lijst

    if REDENKOLOM in uit.columns:
        bestaand = uit[REDENKOLOM].fillna("")
        uit[REDENKOLOM] = bestaand.where(bestaand != "", redenen)
    else:
        uit[REDENKOLOM] = redenen

    return uit


def afwijkingen(kalender: pd.DataFrame,
                sluitingen: tuple[Sluiting, ...]) -> pd.DataFrame:
    """Waar zijn de meting en deze lijst het oneens, binnen het gemeten bereik?

    Muteert niets, en dat is het punt. De tegenhanger van `agenda.afwijkingen`,
    maar bewust maar half zo streng: alleen "lijst zegt dicht, de kassa
    verkocht" wordt gemeld. De omgekeerde richting — kassa dicht, lijst zwijgt —
    die de agendacontrole wél meldt, is hier geen afwijking maar de normale
    toestand: deze lijst is met de hand bijgehouden en per ontwerp onvolledig
    (zie de moduledocstring), dus een gesloten dag die er niet in staat, bewijst
    niets. Het gat dat daardoor overblijft — een sluiting die doorloopt zonder
    dat de lijst het weet — wordt niet hier maar door `lopende_sluiting()`
    bewaakt. Zegt de lijst dicht terwijl de kassa verkocht, dan is één van de
    twee fout en wil je dat weten vóór je erop rekent.
    """
    kolommen = ["datum", "winkel_open", "reden", "soort"]
    if not sluitingen or "winkel_gemeten" not in kalender.columns:
        return pd.DataFrame(columns=kolommen)

    per_dag = dagen_met_reden(sluitingen)
    # Beide kolommen via `_waarheid`: als kale mask respectievelijk
    # `.astype(bool)` zou een object-kolom deze wacht stil laten uitvallen —
    # ofwel geen enkele dag als gemeten zien, ofwel elke dag als open. Zie de
    # docstring van `_waarheid`.
    gemeten = kalender[_waarheid(kalender["winkel_gemeten"])].copy()
    if gemeten.empty:
        return pd.DataFrame(columns=kolommen)

    datums = gemeten["datum"].map(lambda d: pd.Timestamp(d).date())
    in_lijst = datums.map(per_dag.__contains__)
    open_volgens_kassa = _waarheid(gemeten["winkel_open"])

    soort = pd.Series("", index=gemeten.index, dtype=object)
    soort[open_volgens_kassa & in_lijst] = "lijst zegt dicht, de kassa verkocht"

    uit = gemeten.loc[soort != "", ["datum", "winkel_open"]].copy()
    uit["reden"] = datums[soort != ""].map(lambda d: per_dag.get(d, ""))
    uit["soort"] = soort[soort != ""]
    return uit.reset_index(drop=True)[kolommen]


# --- de wacht op een sluiting die misschien doorloopt -----------------------
#
# `afwijkingen()` hierboven toetst de lijst aan de meting binnen het gemeten
# bereik. Deze wacht toetst het omgekeerde en veel gevaarlijker geval: de lijst
# zegt niets waar de meting ophoudt. Dat levert geen tegenspraak op die je kunt
# zien -- het levert stilte op, en stilte leest als "open".


#: Korter dan dit is een gesloten staart geen sluiting maar een weekpatroon.
#:
#: Een bakkerij met een vaste sluitingsdag heeft geregeld een laatste gemeten
#: dag die dicht is, en soms twee op een rij: zondag plus maandag dicht is in
#: Belgische bakkerijen een gewoon patroon. Drie aaneengesloten gesloten dagen
#: aan het einde van de meting passen in geen enkel weekpatroon; dan is er iets
#: anders aan de hand. Onder deze drempel zwijgt de wacht, want een melding die
#: elke week afgaat, leest niemand nog -- en dan mist ze de ene keer dat ze
#: ertoe doet.
MIN_REEKS_DAGEN = 3


def _als_datum(waarde) -> dt.date:
    """Elke datumvorm (date, Timestamp, string) naar één `date`.

    Een tweeling van `canoniek._als_datum`, en met opzet geen import daarvan:
    de canoniekbouw gebruikt deze module, niet andersom, en die richting houden
    we vrij. Eén regel dubbel is dat waard.
    """
    return pd.Timestamp(waarde).date()


def _waarheid(reeks: pd.Series) -> pd.Series:
    """Een waarheidskolom naar echte booleans, ook als ze uit een CSV komt.

    Zelfde val als in `canoniek.als_bool`, en hier stiller: `astype(bool)` maakt
    van de string "False" een True, en dan zou deze wacht elke dag als gesloten
    zien -- of, met de kolom andersom gelezen, nooit meer afgaan. Een wachter die
    door een dtype uitvalt, meldt niets en niemand merkt het.
    """
    if reeks.dtype == bool:
        return reeks

    def waar(w) -> bool:
        if isinstance(w, str):
            return w.strip().lower() in ("true", "1", "ja", "waar")
        if pd.isna(w):
            return False
        return bool(w)

    return reeks.map(waar).astype(bool)


def _dagstatus(kalender: pd.DataFrame) -> dict[dt.date, tuple[bool, bool]]:
    """datum -> (winkel_gemeten, winkel_open). Leeg als de kolommen ontbreken."""
    nodig = {"datum", "winkel_gemeten", "winkel_open"}
    if not nodig <= set(kalender.columns):
        return {}
    gemeten = _waarheid(kalender["winkel_gemeten"])
    open_ = _waarheid(kalender["winkel_open"])
    return {
        _als_datum(datum): (bool(g), bool(o))
        for datum, g, o in zip(kalender["datum"], gemeten, open_, strict=True)
    }


def _aangekondigd(kalender: pd.DataFrame) -> set[dt.date]:
    """De dagen die vooraf als gesloten aangekondigd zijn.

    Uit de kalenderkolom en niet uit de `Sluiting`-lijst, en dat is een keuze:
    `gepland_dicht` draagt beide bronnen (deze configlijst én de iCal-agenda),
    en de vraag "verklaart iemand deze sluiting?" gaat over beide. Wie later de
    agenda aansluit, hoeft aan deze wacht niets te veranderen.
    """
    if "gepland_dicht" not in kalender.columns or "datum" not in kalender.columns:
        return set()
    dicht = _waarheid(kalender["gepland_dicht"])
    return {
        _als_datum(datum)
        for datum, v in zip(kalender["datum"], dicht, strict=True)
        if v
    }


def _datumtekst(datum: dt.date) -> str:
    """'31 juli 2026' / '31 juillet 2026', en '1er août' waar het Frans dat
    vraagt. Zelfde vorm als `contract._datum_nl`."""
    return f"{dagnummer(datum.day)} {maand_vol(datum.month)} {datum.year}"


def _dagen(aantal: int) -> str:
    enkel, meer = t("dag", "jour"), t("dagen", "jours")
    return f"{aantal} {enkel if aantal == 1 else meer}"


def _bereik(van: dt.date, tot: dt.date) -> str:
    """'1 t/m 7 maart' of één losse dag. Het Frans draagt zijn voorzetsel mee
    ("du ... au ...", "le ..."), zodat de zinnen eromheen in beide talen lopen."""
    if van == tot:
        return t(_datumtekst(van), f"le {_datumtekst(van)}")
    return t(f"{_datumtekst(van)} t/m {_datumtekst(tot)}",
             f"du {_datumtekst(van)} au {_datumtekst(tot)}")


@dataclass(frozen=True)
class LopendeSluiting:
    """Een gemeten sluiting zonder bekend einde, met prognosedagen erachter.

    Wat deze uitspraak wél is: de meting eindigt in een aaneengesloten reeks
    gesloten dagen, geen enkele bron verklaart die reeks, en in het gat dat
    daarop volgt staan dagen waarvoor het scherm een omzet verwacht.

    Wat ze NIET is: een bewering dat die dagen gesloten zijn. Dat weet het
    platform niet, en het gaat het niet invullen -- zie de beslissing van
    14 augustus 2026. Dit is een signaal, en het venster blijft ongemoeid.
    """

    #: De aaneengesloten gemeten gesloten reeks aan het einde van de meting.
    reeks_van: dt.date
    reeks_tot: dt.date
    reeks_dagen: int
    #: De laatste dag van deze sluiting die iemand aangekondigd had, als de
    #: lijst de reeks gedeeltelijk kent en hem te vroeg laat eindigen. None als
    #: de lijst deze sluiting helemaal niet kent -- dat is het gewone geval.
    lijst_eindigde_op: dt.date | None
    #: Het gat: vanaf de dag na de reeks tot aan de eerstvolgende aangekondigde
    #: sluitingsdag, of tot het einde van het prognosevenster.
    onverklaard_van: dt.date
    onverklaard_tot: dt.date
    onverklaarde_dagen: int
    #: De prognosedagen die in dat gat vallen: precies de dagen waarvoor het
    #: scherm nu een cijfer toont dat op een gesloten dag kan slaan.
    dagen_in_venster: tuple[dt.date, ...]

    @property
    def aantal_in_venster(self) -> int:
        return len(self.dagen_in_venster)

    def melding(self) -> str:
        """De tekst voor het scherm, in de ingestelde taal.

        Vier dingen, in deze volgorde, want dat is de volgorde waarin een lezer
        ze nodig heeft: wat er gemeten is, wat de lijst erover zegt, hoeveel
        dagen van dit venster eraan hangen, en wie het kan oplossen.
        """
        if self.lijst_eindigde_op is None:
            lijst = t(
                "De sluitingslijst kent die sluiting niet.",
                "La liste des fermetures ignore cette fermeture.",
            )
        else:
            eind = _datumtekst(self.lijst_eindigde_op)
            lijst = t(
                f"De sluitingslijst laat die sluiting eindigen op {eind}, maar "
                "de kassa mat daarna nog gesloten dagen.",
                f"La liste des fermetures fait finir cette fermeture le {eind}, "
                "mais la caisse a encore mesuré des jours fermés ensuite.",
            )

        reeks = _bereik(self.reeks_van, self.reeks_tot)
        gat = _bereik(self.onverklaard_van, self.onverklaard_tot)
        venster = _bereik(self.dagen_in_venster[0], self.dagen_in_venster[-1])

        # Eén dag is het scherpste geval en niet het zeldzaamste: precies dan
        # moet de zin nog lopen.
        een = self.aantal_in_venster == 1
        valt, die_dagen = ("valt", "die dag") if een else ("vallen", "die dagen")
        situe = "situe" if een else "situent"
        ce_jour, affiche = (("ce jour", "affiche") if een
                            else ("ces jours", "affichent"))

        return t(
            f"De laatste gemeten dagen vóór deze prognose waren gesloten: "
            f"{reeks} ({_dagen(self.reeks_dagen)}). {lijst} Over {gat} "
            f"({_dagen(self.onverklaarde_dagen)}) zegt geen enkele bron iets, "
            f"en daar {valt} {_dagen(self.aantal_in_venster)} van dit venster "
            f"in ({venster}). Loopt de sluiting door, dan staat er voor "
            f"{die_dagen} een omzetverwachting op een dag dat de deur dicht "
            "is. Het platform verzint geen sluitingskalender en laat "
            f"{die_dagen} dus staan; alleen de bakkerij weet of ze open was. "
            "Laat het bevestigen en vul de sluitingslijst aan, dan volgt de "
            "prognose vanzelf.",
            f"Les derniers jours mesurés avant cette prévision étaient fermés : "
            f"{reeks} ({_dagen(self.reeks_dagen)}). {lijst} Aucune source ne "
            f"dit rien {gat} ({_dagen(self.onverklaarde_dagen)}), et "
            f"{_dagen(self.aantal_in_venster)} de cette fenêtre s'y {situe} "
            f"({venster}). Si la fermeture se prolonge, {ce_jour} {affiche} un "
            "chiffre d'affaires attendu alors que la porte est close. La "
            "plateforme n'invente pas de calendrier de fermetures et laisse "
            f"donc {ce_jour} en place ; seule la boulangerie sait si elle "
            "était ouverte. Faites-le confirmer et complétez la liste des "
            "fermetures : la prévision suivra.",
        )


def lopende_sluiting(kalender: pd.DataFrame, prognosedagen, *,
                     minimum_reeks: int = MIN_REEKS_DAGEN
                     ) -> LopendeSluiting | None:
    """Loopt de sluiting waarin de meting eindigt, misschien door in het venster?

    De redenering, in vier stappen die elk apart kunnen afbreken:

      1. Eindigt de meting in een gesloten reeks van minstens `minimum_reeks`
         dagen? Zo niet: de zaak was open toen we voor het laatst keken, en er
         is niets aan de hand.
      2. Verklaart iemand die reeks? Staat de laatste gemeten dag of de dag
         erna in `gepland_dicht`, dan kent een bron deze sluiting en heeft ze
         er een einde aan gegeven. Dat einde geloven we -- het komt van de
         bakkerij of van de beheerder, en niet van ons.
      3. Hoe ver reikt het gat? Vanaf de dag na de reeks vooruit tot de
         eerstvolgende aangekondigde sluitingsdag. Daar begint immers weer een
         verhaal dat iemand kent; wat daarachter ligt hangt niet meer aan deze
         reeks.
      4. Staan er prognosedagen in dat gat? Zo niet, dan toont het scherm geen
         cijfer dat op een gesloten dag kan slaan, en zwijgt de wacht.

    `kalender` is de canonieke kalender ná verrijking met de sluitingen (en, als
    hij er is, de agenda): `winkel_gemeten`, `winkel_open` en `gepland_dicht`.
    `prognosedagen` is `Prognosevenster.dagen` -- de dagen die werkelijk een
    cijfer krijgen, dus zonder de dagen die de zeef al heeft overgeslagen.

    Geeft None als er niets te melden valt. Muteert niets, en dat is het punt:
    dagen uit het venster gooien op een vermoeden zou het platform een
    sluitingskalender laten verzinnen, en dat is precies wat het niet doet.
    """
    if minimum_reeks < 1:
        raise ValueError("minimum_reeks is minstens 1 dag")

    dagen = sorted({_als_datum(d) for d in prognosedagen})
    if not dagen:
        return None

    status = _dagstatus(kalender)
    gemeten_dagen = [d for d, (gemeten, _) in status.items() if gemeten]
    if not gemeten_dagen:
        return None

    # 1. De gesloten staart van de meting.
    laatste = max(gemeten_dagen)
    if status[laatste][1]:
        return None
    reeks_van = laatste
    while True:
        vorige = reeks_van - dt.timedelta(days=1)
        gemeten, open_ = status.get(vorige, (False, False))
        if not gemeten or open_:
            break
        reeks_van = vorige
    reeks_dagen = (laatste - reeks_van).days + 1
    if reeks_dagen < minimum_reeks:
        return None

    # 2. Verklaart een bron deze sluiting?
    aangekondigd = _aangekondigd(kalender)
    onverklaard_van = laatste + dt.timedelta(days=1)
    if laatste in aangekondigd or onverklaard_van in aangekondigd:
        return None

    # Kende de lijst het begin van deze reeks wel, dan is ze niet onbekend maar
    # te vroeg beëindigd -- een ander verhaal, en een scherpere aanwijzing dat
    # de lijst achterloopt.
    in_reeks = [d for d in aangekondigd if reeks_van <= d <= laatste]
    lijst_eindigde_op = max(in_reeks) if in_reeks else None

    # 3. Hoe ver reikt het gat?
    onverklaard_tot = dagen[-1]
    dag = onverklaard_van
    while dag <= dagen[-1]:
        if dag in aangekondigd:
            onverklaard_tot = dag - dt.timedelta(days=1)
            break
        dag += dt.timedelta(days=1)
    if onverklaard_tot < onverklaard_van:
        return None

    # 4. Welke prognosedagen hangen eraan?
    in_venster = tuple(d for d in dagen if onverklaard_van <= d <= onverklaard_tot)
    if not in_venster:
        return None

    return LopendeSluiting(
        reeks_van=reeks_van,
        reeks_tot=laatste,
        reeks_dagen=reeks_dagen,
        lijst_eindigde_op=lijst_eindigde_op,
        onverklaard_van=onverklaard_van,
        onverklaard_tot=onverklaard_tot,
        onverklaarde_dagen=(onverklaard_tot - onverklaard_van).days + 1,
        dagen_in_venster=in_venster,
    )
