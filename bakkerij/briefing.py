"""De briefing bovenaan elk scherm: wat valt op, waarom, en wat is er nodig van wie.

Blok 21, en de grens eromheen staat in `docs/beslissingen.md` (14 augustus 2026,
"De briefing bovenaan elk scherm is signalering, geen productie-advies"):

    Dit is SIGNALERING. Geen productie-advies.

"Plan maandag lager" hoort hier niet, en niet omdat het onbeleefd zou zijn maar
omdat het de beslislaag is die op 12 augustus uit fase 1 geschrapt is. Zo'n zin
eerlijk maken vergt de kostenkant van te veel én te weinig bakken, en die
bestaat nog niet. Wat hier wél mag: zeggen wat er gemeten is, wat daaraan
opvalt, en wie er iets moet aanleveren of nakijken. De heropening van die grens
loopt via vraag 56.

DRIE REGELS DIE DE VORM STUREN

1. *Een punt volgt uit een meting, of het bestaat niet.* Geen enkel punt hier
   wordt gemaakt uit een gevoel over de zaak; elk punt heeft een drempel en een
   getal erachter. Levert de berekeningslaag dat getal niet, dan is er geen
   punt — geen vage waarschuwing "voor de zekerheid" (harde regel 7 in de
   geest, en harde regel 8: onbeschikbaar is een antwoord).
2. *Een bedrag mag er alleen bij als de berekeningslaag het staaft.* `bedrag` is
   de machinewaarde als string met punt-decimaal, precies zoals in
   `contract.py`; de UI maakt hem op. Er wordt hier nooit een euro
   gereconstrueerd uit een afgerond percentage.
3. *De betekenis zit in het woord, nooit in de kleur* (huisstijl). `status` is
   een machinesleutel voor sortering, `statuswoord` is wat een mens leest, in de
   taal waarin het contract gebouwd wordt.

DE MOTOR IS PUUR

Functies in, gegevens uit. Deze module leest geen bestanden, kijkt niet op de
klok en praat met niets. `vandaag` komt als argument binnen, net als in
`canoniek.prognosevenster` en `kwaliteit.stand`. Zo blijft de contractbouw de
enige plek die de wereld aanraakt, en is elk punt hier met een handvol regels
na te bouwen in een test.

ARGUMENTEN ZONDER STANDAARDWAARDE, EN DAT IS OPZET

Elke schermfunctie eist al haar argumenten, ook de argumenten die None mogen
zijn. Een briefing die stilzwijgend een punt minder toont omdat een aanroeper
iets vergat, is precies wat harde regel 8 verbiedt. Wat None betekent, staat per
argument in de docstring van de functie: soms "deze meting bestaat niet" (en dan
is dát het punt), soms "niet aangeleverd" (en dan zwijgt de briefing erover).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

from bakkerij import taal as tl
from bakkerij.berekening import Bonritme, Margebeeld, Periodecontext, Verschuiving
from bakkerij.canoniek import Meetgat, Prognosevenster, Sluitingsstand
from bakkerij.kwaliteit import BRONNEN, Bronstand, Wachter
from bakkerij.taal import t

# --- de drempels ------------------------------------------------------------
#
# Alle drempels staan hier, met de reden erbij. Een drempel die verspreid in de
# code staat, wordt bij de eerste discussie stilletjes verzet; een drempel die
# hier staat, moet iemand uitleggen. Waar een waarde gekozen is en niet
# afgeleid, staat dat er met zoveel woorden — een gekozen getal verkopen als een
# gemeten getal is precies het soort halve waarheid dat dit platform niet
# vertelt.

#: Zoveel dagen mag er niets nieuws ingeladen zijn voor de briefing erover
#: begint. GEKOZEN, niet gemeten. De nachtelijke run laadt gisteren, en de
#: bakkerij heeft sluitingsdagen: één haperende nacht boven op een sluitingsdag
#: is nog geen storing. Vanaf drie dagen kan geen enkele losse sluitingsdag het
#: nog verklaren. `kwaliteit.MAX_ONGEMETEN_DAGEN` staat op twee en meet
#: hetzelfde per bron; deze ligt er bewust één boven, zodat de briefing niet bij
#: elke hik van de bronwachter meepiept.
ACHTERSTAND_DAGEN = 3

#: Vanaf hier is het geen hapering meer maar een storing, en wordt het punt
#: 'actie'. Zeven dagen: dan is van elke weekdag er één gemist, en loopt elke
#: vergelijking op elk scherm over een venster dat een week oud is.
ACHTERSTAND_ERNSTIG_DAGEN = 7

#: Zoveel dagen moet de bakkerij aaneengesloten dicht zijn voordat de briefing
#: de sluiting meldt. GEKOZEN, en het is dezelfde afweging als
#: `sluitingsdagen.MIN_REEKS_DAGEN` (die op dezelfde waarde staat): een bakkerij
#: met een vaste sluitingsdag is elke week een of twee dagen dicht, en een punt
#: dat elke maandag verschijnt leest niemand nog. Drie aaneengesloten dagen
#: passen in geen enkel weekpatroon; dan is er iets aan de hand dat de cijfers
#: op elk scherm verklaart.
SLUITING_MIN_DAGEN = 3

#: Zoveel procent mag het gemiddelde per gemeten open dag afwijken van de
#: vorige, even lange periode voor de briefing het opmerkt. GEKOZEN. De
#: dagomzet heeft een flinke eigen spreiding — de prognose zit op 7,6% WAPE per
#: dag — maar over dertig open dagen middelt daar het meeste van uit. Onder de
#: tien procent zou dit punt bijna elke maand verschijnen, en een punt dat er
#: altijd staat leest niemand nog (dezelfde kernregel als bij de dodemansknop in
#: `kwaliteit.py`).
OMZETSCHUIF_PCT = Decimal("10.0")

#: Zo groot moet de verschuiving van één product zijn voor ze in de briefing
#: komt: twee procent van de omzet van het venster waarin ze gemeten is.
#: Relatief en niet in euro's, want een vaste eurodrempel is een uitspraak over
#: de grootte van de zaak en die hoort niet in code. GEKOZEN, maar wel in
#: verhouding tot de drempel hierboven: één product dat twee procent van de
#: vensteromzet verschuift, draagt in zijn eentje een vijfde van wat deze module
#: op het totaal een opvallende beweging noemt. Dat is zeldzaam, en dat is de
#: bedoeling — het scherm zelf toont de vijf grootste stijgers en dalers al.
PRODUCTSCHUIF_AANDEEL = Decimal("0.02")

#: Onder deze dekking meldt de briefing dat een deel van de omzet buiten de
#: marge valt, en onder de tweede drempel wordt het 'actie'. GEKOZEN. Bij een
#: dekking van 80% weegt het gewogen margepercentage nog over het overgrote
#: deel van de omzet; onder de helft zegt het meer over wie iets invulde dan
#: over de zaak.
DEKKING_DREMPEL = Decimal("80.0")
DEKKING_ERNSTIG = Decimal("50.0")

#: Zoveel dagen mag de bonnentelling ontbreken binnen het bonritmevenster voor
#: de briefing het meldt. GEKOZEN, laag gezet: elke dag zonder bonnentelling
#: valt stil uit het gemiddelde bonbedrag, en drie dagen op dertig is tien
#: procent van het venster.
BON_GAT_DAGEN = 3

#: Zoveel mag de out-of-sample gemeten banddekking onder haar doel liggen
#: voordat de briefing zegt dat de band niet houdt wat ze belooft. AFGELEID:
#: bij ruim 340 gemeten dagen is de standaardfout op een aandeel van 0,80
#: ongeveer 2 procentpunt (sqrt(0.8*0.2/340) = 0,022). Een gat dat kleiner is
#: dan de meetfout van de meting zelf, is geen bevinding.
BAND_TOLERANTIE = 0.02

#: Vanaf deze systematische afwijking (bias als fractie van de dagomzet, + is te
#: hoog) meldt de briefing dat de prognose structureel scheef staat. GEKOZEN met
#: de gemeten fout als ijkpunt: de totale afwijking is 7,6% WAPE, dus een
#: systematisch deel van 3% is bijna de helft daarvan en geen toeval meer.
BIAS_DREMPEL = 0.03

#: Zoveel punten toont een briefing hoogstens. Een handvol, want een briefing
#: waar je doorheen moet scrollen is geen briefing meer maar een tweede scherm.
#: Uitzondering: elk punt met status 'actie' blijft staan, ook boven dit
#: maximum — een punt dat om iemand vraagt, mag niet wegvallen omdat er drie
#: observaties boven staan. Wat wél kan wegvallen is een 'let_op' of een 'goed',
#: en die staan elders op hetzelfde scherm voluit (in `onbeschikbaar` of in de
#: toelichting bij het blok waar ze over gaan).
MAX_PUNTEN = 5


# --- de vorm ----------------------------------------------------------------

STATUSSEN = ("goed", "let_op", "actie")
SOORTEN = ("euro", "aantal", "verschil")
RICHTINGEN = ("op", "neer")

#: Zwaarste eerst. Alleen voor sortering; de mens leest `statuswoord`.
_RANG = {"actie": 0, "let_op": 1, "goed": 2}


def statuswoord_van(status: str) -> str:
    """Het woord dat bij een status hoort, in de taal van het contract.

    De huisstijl laat kleur geen betekenis dragen. Een statuschip is dus geen
    rood of oranje bolletje maar een woord, en dat woord komt uit de
    berekeningslaag zoals elk ander label (harde regel 4).
    """
    if status == "actie":
        return t("Actie nodig", "Action requise")
    if status == "let_op":
        return t("Let op", "À surveiller")
    return t("In orde", "En ordre")


@dataclass(frozen=True)
class BriefingPunt:
    """Eén punt: wat valt op, waarom, en wat is er nodig van wie.

    `bedrag` is een machinewaarde als string met punt-decimaal, net als overal
    in het contract — nooit een float, want een float in JSON is een
    afrondingsfout die onderweg ontstaat. Hij mag alleen gevuld zijn als de
    berekeningslaag hem staaft, en dan hoort er een `soort` bij: een getal
    zonder eenheid kan de UI niet opmaken.

    `status` is de machinesleutel ('goed', 'let_op', 'actie') waarop gesorteerd
    wordt; `statuswoord` is wat er te lezen staat. Wordt `statuswoord` niet
    meegegeven, dan volgt hij uit `status` in de taal van het moment.

    `gedeeld` zegt dat dit punt op ÉLK scherm staat, woord voor woord: het gaat
    over de versheid van de hele aanvoer en niet over dít scherm. Vandaag zijn
    dat er twee — de sluiting en de achterstand — en ze komen alle twee uit
    `_versheidspunten`, dat door alle zes de schermfuncties wordt aangeroepen.

    Toegevoegd 19 augustus 2026, en niet voor de schermen: daar hoort zo'n punt
    op elk scherm te staan, want wie op Productmix binnenkomt moet óók weten dat
    de zaak dicht is. Het is voor het RAPPORT. `/rapport` zet de gekozen
    schermen achter elkaar, en zonder dit veld openen zes opeenvolgende
    bladzijden met dezelfde alinea van 268 tekens ("De bakkerij is gesloten").
    Dat stond bovenaan `docs/open-punten.md` als de grootste tekstberg in juist
    het document dat een CFO werkelijk leest.

    "OP ELK SCHERM" IS EEN HARDE EIS EN GEEN BENADERING. Het rapport toont een
    gemerkt punt in het eerste onderdeel en verbergt het in alle volgende; dat
    is alleen veilig zolang het eerste onderdeel het punt zéker draagt. Een punt
    dat op vijf van de zes schermen staat, zou uit een rapport verdwijnen dat
    met het zesde begint. Vandaar dat een bronpunt het merk niet krijgt, hoewel
    het zich op twee schermen herhaalt — zie `_bronpunt`. Een test bewaakt de
    eis: `test_elk_gemerkt_punt_staat_op_elk_scherm`.

    Waarom een vlag in het contract en geen ontdubbeling in de presentatielaag:
    de UI kan twee alinea's wel vergelijken, maar dan besluit zíj wat hetzelfde
    is, en dat besluit hoort bij de laag die het punt maakt. Hier is het geen
    vergelijking maar een eigenschap: de functie die dit punt bouwt, weet dat
    het op elk scherm terugkomt.
    """

    kop: str
    waarom: str
    nodig: str | None = None
    bedrag: str | None = None
    soort: str | None = None
    eenheid: str | None = None
    richting: str | None = None
    status: str = "let_op"
    statuswoord: str = ""
    gedeeld: bool = False

    def __post_init__(self) -> None:
        if self.status not in STATUSSEN:
            raise ValueError(
                f"Onbekende status {self.status!r}; keuze uit {STATUSSEN}."
            )
        if self.soort is not None and self.soort not in SOORTEN:
            raise ValueError(
                f"Onbekende soort {self.soort!r}; keuze uit {SOORTEN} of None."
            )
        if self.richting is not None and self.richting not in RICHTINGEN:
            raise ValueError(
                f"Onbekende richting {self.richting!r}; keuze uit {RICHTINGEN} "
                "of None."
            )
        if self.bedrag is not None:
            if not isinstance(self.bedrag, str):
                raise TypeError(
                    "Een bedrag verlaat de berekeningslaag als string met "
                    f"punt-decimaal, niet als {type(self.bedrag).__name__}."
                )
            if self.soort is None:
                raise ValueError(
                    "Een bedrag zonder soort kan de UI niet opmaken; geef "
                    "'euro', 'aantal' of 'verschil' mee."
                )
        # Euro's en verschillen maken zichzelf leesbaar ("€ 1.234,56",
        # "+0,4%"), maar een kaal aantal op een scherm leest als een
        # notificatieteller. Vandaar: een aantal draagt zijn eenheid, en de
        # andere soorten dragen er geen — daar zou ze dubbelop zijn.
        if self.soort == "aantal" and not self.eenheid:
            raise ValueError(
                "Een aantal zonder eenheid is een kaal cijfer op het scherm; "
                "geef mee wat er geteld wordt ('dagen', 'groepen', ...)."
            )
        if self.eenheid is not None and self.soort != "aantal":
            raise ValueError(
                "Een eenheid hoort alleen bij soort 'aantal'; euro en "
                "verschil maken zichzelf leesbaar."
            )
        if not self.statuswoord:
            object.__setattr__(self, "statuswoord", statuswoord_van(self.status))


@dataclass(frozen=True)
class Briefing:
    """De punten van één scherm, plus de zin voor als er niets te melden is."""

    punten: list[BriefingPunt]
    leeg: str

    def als_dict(self) -> dict:
        """De vorm die het contract doorgeeft aan de UI."""
        return asdict(self)


@dataclass(frozen=True)
class Versheid:
    """Wat er over de versheid van de cijfers bekend is, voor elk scherm gelijk.

    `gemeten_tot` is de jongste gemeten open winkeldag, dezelfde datum die in de
    enveloppe van elk antwoord staat. `meetgat` komt uit
    `canoniek.prognosevenster(...).meetgat` en is de eerlijkste bron voor de
    achterstand: daarvan telt alleen `niet_ingeladen` mee, want dat zijn de dagen
    die niemand verklaart. Dagen waarop de winkel gemeten dicht was of vooraf
    dicht was aangekondigd, staan in hun eigen bakje en zijn geen achterstand.
    Zonder meetgat valt deze module terug op het aantal kalenderdagen sinds de
    laatste meting, en zegt dat er dan ook bij.

    `sluiting` komt uit `canoniek.prognosevenster(...).sluiting` en is de andere
    helft van datzelfde onderscheid: is de bakkerij vandaag dicht, dan lopen de
    cijfers niet achter maar houden ze gewoon op, en dat hoort er te staan in
    plaats van een alarm. None betekent "de zaak hoort vandaag open te zijn".
    """

    vandaag: dt.date
    gemeten_tot: dt.date | None
    meetgat: Meetgat | None = None
    sluiting: Sluitingsstand | None = None

    def __post_init__(self) -> None:
        # De berekeningslaag levert haar peildatum als Timestamp en de kalender
        # de hare als date. Hier één keer normaliseren, zodat geen enkele
        # rekenregel verderop een Timestamp van een date hoeft af te trekken —
        # dat is precies het soort fout dat pas op het scherm zichtbaar wordt.
        object.__setattr__(self, "vandaag", _als_date(self.vandaag))
        if self.gemeten_tot is not None:
            object.__setattr__(self, "gemeten_tot", _als_date(self.gemeten_tot))


# --- hulpjes ----------------------------------------------------------------
#
# `contract.py` heeft vergelijkbare hulpjes, maar die kunnen hier niet vandaan
# komen: het contract importeert straks deze module, en niet omgekeerd. Dit is
# bewust een kopie van drie regels en geen import die een kring maakt.


def _als_date(waarde: dt.date | dt.datetime | pd.Timestamp) -> dt.date:
    return pd.Timestamp(waarde).date()


def _datum(waarde: dt.date | dt.datetime | pd.Timestamp) -> str:
    """'7 augustus 2026' / '7 août 2026', en '1er août' waar het Frans dat vraagt.

    Via `taal.dagnummer`, net als `contract._datum_nl` en
    `sluitingsdagen._datumtekst`. Deze module schreef de dag tot 18 augustus 2026
    als kaal getal en was daarmee de enige van de drie die "1 août 2026" opleverde
    in plaats van "1er août 2026".
    """
    d = _als_date(waarde)
    return f"{tl.dagnummer(d.day)} {tl.maand_vol(d.month)} {d.year}"


def _datum_le(waarde: dt.date | dt.datetime | pd.Timestamp) -> str:
    """Dezelfde datum, maar met het Franse lidwoord: 'le 1er août 2026'.

    Het Nederlands zet er niets voor; het Frans wil "le" na "depuis" en na "est".
    Eén helper zodat die "le" niet in vijf f-strings los rondslingert.
    """
    return t(_datum(waarde), f"le {_datum(waarde)}")


def _dagen(aantal: int) -> str:
    enkel = t("dag", "jour")
    meer = t("dagen", "jours")
    return f"{aantal} {enkel}" if aantal == 1 else f"{aantal} {meer}"


def _dagen_eenheid(aantal: int) -> str:
    """De eenheid naast een geteld aantal dagen, zonder het getal zelf: dat
    staat al in `bedrag` en de UI zet de twee naast elkaar."""
    return t("dag", "jour") if aantal == 1 else t("dagen", "jours")


def _euro(waarde: Decimal | float) -> str:
    """Een bedrag als machinewaarde: '1234.56'. Twee decimalen, punt-decimaal."""
    getal = waarde if isinstance(waarde, Decimal) else Decimal(str(waarde))
    return str(getal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _procent_machine(waarde: Decimal | float) -> str:
    """Een percentage als machinewaarde: -12.4 -> '-12.4'. Neemt een PERCENTAGE.

    De naam draagt de eenheid sinds 19 augustus 2026. Daarvoor heetten deze
    functie en haar buurvrouw `_procent` en `_procent_nl` — twee namen die drie
    letters schelen terwijl hun invoer een factor 100 scheelt. Zo'n verwisseling
    geeft geen fout, alleen een cijfer dat er honderd keer naast zit en er
    normaal uitziet.
    """
    getal = waarde if isinstance(waarde, Decimal) else Decimal(str(waarde))
    return str(getal.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _procent_tekst(fractie: float) -> str:
    """Een percentage in lopende tekst: 0.078 -> '7,8 %'. Neemt een FRACTIE.

    De notatie staat op één plek, `taal.procent_tekst` — drie eigen kopieën
    toonden tot 17 augustus 2026 "7,8%" naast het "8,1 %" van de tabellen.
    Zie `_procent_machine` voor de reden dat de eenheid in de naam staat.
    """
    return tl.procent_tekst(fractie)


def _richting_van(waarde: Decimal | float) -> str | None:
    """Op, neer, of geen van beide. Richting komt uit het teken, nooit uit kleur."""
    if waarde > 0:
        return "op"
    if waarde < 0:
        return "neer"
    return None


def _wie_platform() -> str:
    return t("het platformbeheer", "l'équipe technique de la plateforme")


def _wie_beheerder() -> str:
    return t("een beheerder, op Instellingen", "un administrateur, dans Paramètres")


def _wie_bakkerij() -> str:
    return t("de bakkerij, via Lien", "la boulangerie, via Lien")


def _leegzin() -> str:
    """De zin voor een scherm zonder punten.

    Bewust bescheiden. "Alles in orde" zou een uitspraak zijn over dingen die
    deze module niet meet, en dat is dezelfde stille leugen als een leeg vak
    zonder reden (harde regel 8). Wat hier staat is wat waar is: de metingen
    achter dit scherm leverden niets op om te melden.
    """
    return t(
        "Geen signalen voor dit scherm. De metingen hierachter leverden niets "
        "op om te melden — dat is iets anders dan de garantie dat er niets aan "
        "de hand is.",
        "Aucun signal pour cet écran. Les mesures sous-jacentes n'ont rien "
        "relevé — ce qui n'est pas la garantie que tout va bien.",
    )


def _bundel(punten: Sequence[BriefingPunt]) -> Briefing:
    """Zwaarste eerst, en hoogstens een handvol.

    Sorteren is stabiel: binnen dezelfde status blijft de volgorde staan waarin
    de schermfunctie de punten heeft gemaakt, en die volgorde is de rangschikking
    naar belang. Alle 'actie'-punten overleven het maximum; zie MAX_PUNTEN voor
    waarom dat verantwoord is.
    """
    geordend = sorted(punten, key=lambda p: _RANG[p.status])
    zichtbaar = [p for p in geordend if p.status == "actie"]
    for punt in geordend:
        if punt.status != "actie" and len(zichtbaar) < MAX_PUNTEN:
            zichtbaar.append(punt)
    return Briefing(punten=zichtbaar, leeg=_leegzin())


# --- het gedeelde punt: lopen de cijfers achter? ----------------------------


def _als_gedeeld(punten: Sequence[BriefingPunt]) -> list[BriefingPunt]:
    """Merkt punten als 'dit staat woord voor woord op elk scherm'.

    Op één plek en niet bij elke constructie: de functies hieronder maken
    uitsluitend gedeelde punten, en een vlag die per `BriefingPunt(...)` gezet
    moet worden, is een vlag die de volgende keer vergeten wordt. Zie
    `BriefingPunt.gedeeld` voor waarvoor hij dient.
    """
    return [replace(p, gedeeld=True) for p in punten]


def _sluitingspunt(sluiting: Sluitingsstand, gemeten_tot: dt.date) -> BriefingPunt:
    """De bakkerij is dicht, en daarom houden de cijfers op waar ze ophouden.

    Bewust 'let_op' en niet 'goed': de lezer moet weten dat elk cijfer op dit
    scherm van vóór de sluiting komt, en dat is een voorbehoud en geen
    geruststelling. Even bewust zónder `nodig`: er is niemand die hier iets moet
    aanleveren of nakijken. Een sluiting is geen storing, en het punt dat het
    platformbeheer om een blik op de nachtelijke synchronisatie vroeg, is precies
    de fout die dit punt vervangt.
    """
    sinds = _datum_le(sluiting.dicht_sinds)
    tot = _datum(gemeten_tot)
    reden = f" ({sluiting.reden})" if sluiting.reden else ""

    if sluiting.eerste_open_dag is not None:
        open_zin = t(
            f"De eerste dag dat de zaak weer opengaat, is "
            f"{_datum(sluiting.eerste_open_dag)}.",
            f"Le premier jour de réouverture est "
            f"{_datum_le(sluiting.eerste_open_dag)}.",
        )
    else:
        open_zin = t(
            "Tot wanneer de sluiting loopt, is niet bekend: de kalender reikt "
            "niet verder dan de sluiting zelf.",
            "Jusqu'à quand la fermeture se prolonge n'est pas connu : le "
            "calendrier ne va pas au-delà de la fermeture elle-même.",
        )

    return BriefingPunt(
        kop=t("De bakkerij is gesloten", "La boulangerie est fermée"),
        waarom=t(
            f"De zaak is dicht sinds {sinds}{reden}. {open_zin} De cijfers op "
            f"dit scherm lopen tot {tot} en niet tot vandaag, omdat er sindsdien "
            "niets verkocht is: dat is geen achterstand in de inlaad.",
            f"Le commerce est fermé depuis {sinds}{reden}. {open_zin} Les "
            f"chiffres de cet écran s'arrêtent au {tot} et non à aujourd'hui, "
            "parce que rien n'a été vendu depuis : ce n'est pas un retard de "
            "chargement.",
        ),
        bedrag=str(sluiting.dagen),
        soort="aantal",
        eenheid=_dagen_eenheid(sluiting.dagen),
        status="let_op",
    )


def _versheidspunten(versheid: Versheid) -> list[BriefingPunt]:
    """Achterlopende cijfers kleuren elk getal op elk scherm, dus staat dit
    punt op elk scherm.

    Twee punten die elkaar niet uitsluiten, en dat is opzet. Een sluiting
    verklaart waarom de cijfers ophouden; ze verklaart niet waarom er dáárvoor
    open dagen ontbreken. Loopt de inlaad écht achter én is de zaak dicht, dan
    staan er twee punten en zijn ze allebei waar.
    """
    if versheid.gemeten_tot is None:
        return _als_gedeeld([
            BriefingPunt(
                kop=t(
                    "Er is geen enkele gemeten dag ingeladen",
                    "Aucun jour mesuré n'a été chargé",
                ),
                waarom=t(
                    "Zonder gemeten dag heeft geen enkel cijfer op dit scherm "
                    "een bron: er valt niets te tonen en niets te vergelijken.",
                    "Sans jour mesuré, aucun chiffre de cet écran n'a de "
                    "source : il n'y a rien à montrer ni à comparer.",
                ),
                nodig=t(
                    f"De inlaad uit de bronsystemen moet draaien — "
                    f"{_wie_platform()}.",
                    f"Le chargement depuis les systèmes sources doit tourner — "
                    f"{_wie_platform()}.",
                ),
                status="actie",
            )
        ])

    punten: list[BriefingPunt] = []
    sluiting = versheid.sluiting
    if sluiting is not None and sluiting.dagen >= SLUITING_MIN_DAGEN:
        punten.append(_sluitingspunt(sluiting, versheid.gemeten_tot))

    # ALLEEN `niet_ingeladen` IS EEN ACHTERSTAND. Dat woord stond hier tot
    # 18 augustus 2026 op `niet_gemeten`, en dat veld telde ook de dagen die de
    # kalender als gepland dicht kende. Tijdens de zomersluiting meldde dit punt
    # daardoor tien dagen achterstand en vroeg het het platformbeheer de
    # nachtelijke synchronisatie na te kijken, terwijl de bakkerij gewoon in
    # verlof was. Zie `canoniek.Meetgat` voor de drie bakjes.
    gemeten = versheid.meetgat is not None
    achterstand = (
        versheid.meetgat.niet_ingeladen
        if versheid.meetgat is not None
        else (versheid.vandaag - versheid.gemeten_tot).days
    )
    if achterstand < ACHTERSTAND_DAGEN:
        return _als_gedeeld(punten)

    laatste = _datum(versheid.gemeten_tot)
    if gemeten:
        waarom = t(
            f"De jongste gemeten open winkeldag is {laatste}. Sindsdien zijn "
            f"er {_dagen(achterstand)} die niet uit de bronsystemen zijn "
            "ingeladen en die geen enkele sluiting verklaart; over die dagen "
            "zegt geen enkel cijfer op dit scherm iets.",
            f"Le dernier jour d'ouverture mesuré est le {laatste}. Depuis, "
            f"{_dagen(achterstand)} n'ont pas été chargés depuis les systèmes "
            "sources et aucune fermeture ne les explique ; aucun chiffre de "
            "cet écran ne dit quoi que ce soit sur ces jours.",
        )
    else:
        waarom = t(
            f"De jongste gemeten open winkeldag is {laatste}, en dat is "
            f"{_dagen(achterstand)} geleden. Of daar sluitingsdagen tussen "
            "zitten, is hier niet bekend; het aantal is in kalenderdagen "
            "geteld.",
            f"Le dernier jour d'ouverture mesuré est le {laatste}, il y a "
            f"{_dagen(achterstand)}. On ignore ici si des jours de fermeture "
            "s'y trouvent ; le compte est en jours calendrier.",
        )

    ernstig = achterstand >= ACHTERSTAND_ERNSTIG_DAGEN
    punten.append(
        BriefingPunt(
            kop=t(
                "De cijfers lopen achter op vandaag",
                "Les chiffres sont en retard sur aujourd'hui",
            ),
            waarom=waarom,
            nodig=t(
                f"De nachtelijke synchronisatie moet nagekeken worden — "
                f"{_wie_platform()}.",
                f"La synchronisation nocturne doit être vérifiée — "
                f"{_wie_platform()}.",
            ),
            bedrag=str(achterstand),
            soort="aantal",
            eenheid=_dagen_eenheid(achterstand),
            status="actie" if ernstig else "let_op",
        )
    )
    return _als_gedeeld(punten)


# --- de bronnen, gedeeld door Verkoopkanalen en Instellingen ----------------

#: naam van de bron -> kanaal in het canonieke model. Afgeleid uit
#: `kwaliteit.BRONNEN`, zodat een nieuwe bron daar volstaat.
_KANAAL_PER_BRON = {bron: kanaal for kanaal, bron in BRONNEN}


def _bronnaam(stand: Bronstand) -> str:
    kanaal = _KANAAL_PER_BRON.get(stand.bron)
    return tl.kanaalnaam(kanaal) if kanaal else stand.bron


def _bronpunt(stand: Bronstand, vandaag: dt.date) -> BriefingPunt | None:
    """Eén bronstand vertaald naar een punt, of None als er niets te melden is.

    NIET `gedeeld`, en dat is een bewuste grens (19 augustus 2026). Een bronpunt
    staat vandaag woord voor woord op twéé schermen — Verkoopkanalen en
    Instellingen — en herhaalt zich dus ook in het rapport. Toch draagt het het
    merk niet: `gedeeld` betekent "staat op élk scherm", en het rapport rekent
    daarop. Het toont zo'n punt in het eerste onderdeel en verbergt het in de
    rest; staat het punt niet op het eerste onderdeel, dan verdwijnt het uit het
    hele document. Bij een bronpunt is dat precies het geval — kies een rapport
    dat met Dagoverzicht begint, en "Het kanaal Deliveroo heeft nog geen data"
    zou spoorloos zijn. Een actiepunt dat stilletjes uit een rapport valt, is
    erger dan hetzelfde punt dat er tweemaal in staat (harde regel 8).

    'vers' en 'gesloten' leveren geen punt op: dat is de bron die doet wat hij
    hoort te doen, en de briefing is geen opsomming van wat goed gaat.

    'bevroren' ook niet, en dat is een andere reden: dat kanaal wordt niet meer
    aangevuld (zie `kwaliteit.BEVROREN`). Een briefingpunt is een oproep aan
    iemand — "wat valt op, en wat is er nodig van wie" — en hier is er niemand
    aan wie iets te vragen valt. Tot wanneer de historiek loopt, staat mét de
    reden in het bronnenlijstje op Instellingen; dát is de plek voor een feit
    dat niet verandert.
    """
    naam = _bronnaam(stand)

    if stand.status == "stil":
        return BriefingPunt(
            kop=t(
                f"Er komt niets meer binnen van {naam}",
                f"Plus rien n'arrive de {naam}",
            ),
            waarom=t(
                "De kalender zegt dat de winkel open hoorde te zijn, maar er "
                "is voor die dagen geen enkele rij ingeladen. Dat is geen "
                "sluiting; dat is een bron die stilgevallen is.",
                "Le calendrier indique que la boutique aurait dû être ouverte, "
                "mais aucune ligne n'a été chargée pour ces jours. Ce n'est "
                "pas une fermeture, c'est une source à l'arrêt.",
            ),
            nodig=t(
                f"De koppeling met deze bron moet nagekeken worden — "
                f"{_wie_platform()}.",
                f"La connexion à cette source doit être vérifiée — "
                f"{_wie_platform()}.",
            ),
            status="actie",
        )

    if stand.status == "achter":
        dagen = (
            (vandaag - stand.laatste_meetdag).days
            if stand.laatste_meetdag is not None
            else None
        )
        laatste = (
            _datum(stand.laatste_meetdag)
            if stand.laatste_meetdag is not None
            else t("onbekend", "inconnue")
        )
        return BriefingPunt(
            kop=t(f"{naam} loopt achter", f"{naam} est en retard"),
            waarom=t(
                f"De jongste meting van deze bron is {laatste}. Cijfers per "
                "kanaal op dit scherm lopen daarmee niet gelijk: een kanaal "
                "dat later aanlevert, oogt kleiner dan het is.",
                f"La dernière mesure de cette source date du {laatste}. Les "
                "chiffres par canal de cet écran ne sont donc pas alignés : un "
                "canal qui livre plus tard paraît plus petit qu'il n'est.",
            ),
            nodig=t(
                f"De aanlevering van deze bron moet nagekeken worden — "
                f"{_wie_platform()}.",
                f"La livraison de cette source doit être vérifiée — "
                f"{_wie_platform()}.",
            ),
            bedrag=str(dagen) if dagen is not None else None,
            soort="aantal" if dagen is not None else None,
            eenheid=_dagen_eenheid(dagen) if dagen is not None else None,
            status="let_op",
        )

    if stand.status == "ontbreekt":
        deliveroo = stand.bron == "deliveroo"
        return BriefingPunt(
            kop=t(
                f"Het kanaal {naam} heeft nog geen data",
                f"Le canal {naam} n'a pas encore de données",
            ),
            waarom=t(
                f"Er is geen enkele rij van {naam} ingeladen. Het kanaal staat "
                "op dit scherm als onbeschikbaar met de reden erbij, en telt "
                "in geen enkel totaal mee — ook niet als nul.",
                f"Aucune ligne de {naam} n'a été chargée. Le canal figure sur "
                "cet écran comme indisponible avec la raison, et ne compte "
                "dans aucun total — pas même comme zéro.",
            ),
            nodig=(
                t(
                    f"De rapporten Items Sold en Orders uit de Deliveroo "
                    f"Partner Hub — {_wie_bakkerij()}. Het venster in de "
                    "Partner Hub schuift op: wat er nu uit valt, is later niet "
                    "meer op te halen.",
                    f"Les rapports Items Sold et Orders du Deliveroo Partner "
                    f"Hub — {_wie_bakkerij()}. La fenêtre du Partner Hub "
                    "défile : ce qui en sort maintenant ne pourra plus être "
                    "récupéré.",
                )
                if deliveroo
                else t(
                    f"De aanlevering van dit kanaal — {_wie_bakkerij()}.",
                    f"La livraison de ce canal — {_wie_bakkerij()}.",
                )
            ),
            status="actie" if deliveroo else "let_op",
        )

    return None


# --- Dagoverzicht -----------------------------------------------------------


def overzicht(
    *,
    versheid: Versheid,
    periode: Periodecontext | None,
    afwijkende: pd.DataFrame | None,
    bonritme: Bonritme | None,
) -> Briefing:
    """De briefing boven het Dagoverzicht.

    `periode` is `berekening.periodecontext(...)` over het venster dat het
    scherm toont (30 gemeten open dagen). None betekent "niet aangeleverd" en
    levert geen punt op; een `verschil_pct` van None betekent "geen
    vergelijkbaar venster", en dat staat al met reden in `onbeschikbaar`.

    `afwijkende` is de uitkomst van `berekening.afwijkende_dagen`, nieuwste
    eerst. Leeg betekent "geen uitschieters gevonden" — geen punt, want dat is
    de normale toestand.

    `bonritme` is `berekening.bonritme(...)` of None, en None betekent hier wél
    iets: er is geen bonnentelling ingeladen. Dat is een punt, want zonder die
    telling kan het scherm niet zeggen of een omzetverandering van het aantal
    klanten of van het mandje komt.
    """
    punten = _versheidspunten(versheid)
    tot = versheid.gemeten_tot

    schuif = (
        periode.verschil_pct
        if periode is not None and periode.verschil_pct is not None
        else None
    )
    if schuif is not None and abs(schuif) >= OMZETSCHUIF_PCT:
        omhoog = schuif > 0
        tot_zin = f" t/m {_datum(tot)}" if tot is not None else ""
        tot_zin_fr = f" jusqu'au {_datum(tot)}" if tot is not None else ""
        punten.append(
            BriefingPunt(
                kop=(
                    t(
                        "De omzet per open dag ligt duidelijk hoger dan de "
                        "vorige periode",
                        "Le chiffre d'affaires par jour d'ouverture est "
                        "nettement supérieur à la période précédente",
                    )
                    if omhoog
                    else t(
                        "De omzet per open dag ligt duidelijk lager dan de "
                        "vorige periode",
                        "Le chiffre d'affaires par jour d'ouverture est "
                        "nettement inférieur à la période précédente",
                    )
                ),
                waarom=t(
                    f"Gemeten over de laatste {_dagen(periode.dagen)} met "
                    f"verkoop{tot_zin}, naast de "
                    f"{_dagen(periode.vorig_dagen)} ervoor. Beide vensters "
                    "tellen even veel open dagen, dus dit is geen sluiting "
                    "die zich voordoet als vraaguitval.",
                    f"Mesuré sur les {_dagen(periode.dagen)} de vente les "
                    f"plus récents{tot_zin_fr}, face aux "
                    f"{_dagen(periode.vorig_dagen)} précédents. Les deux "
                    "fenêtres comptent autant de jours d'ouverture : ce "
                    "n'est donc pas une fermeture déguisée en baisse de la "
                    "demande.",
                ),
                bedrag=_procent_machine(schuif),
                soort="verschil",
                richting=periode.richting,
                status="let_op",
            )
        )

    if afwijkende is not None and not afwijkende.empty:
        eerste = afwijkende.iloc[0]
        datum = pd.Timestamp(eerste["datum"])
        # Via Decimal, zoals de productverschuiving verderop: dit verschil
        # eindigt als eurobedrag in de uitvoer en rekent dus niet in floats.
        verschil = Decimal(str(float(eerste["omzet"]))) - Decimal(
            str(float(eerste["verwacht_mediaan"]))
        )
        dagnaam = tl.weekdag(datum.dayofweek)
        aantal = len(afwijkende)
        punten.append(
            BriefingPunt(
                kop=(
                    t(
                        "Eén dag week sterk af van wat op die weekdag "
                        "gebruikelijk is",
                        "Un jour s'écarte fortement de l'habitude pour ce jour "
                        "de la semaine",
                    )
                    if aantal == 1
                    else t(
                        "Enkele dagen weken sterk af van wat op hun weekdag "
                        "gebruikelijk is",
                        "Quelques jours s'écartent fortement de l'habitude "
                        "pour leur jour de la semaine",
                    )
                ),
                waarom=t(
                    f"De jongste is {dagnaam} {_datum(datum)}. Het bedrag "
                    "hiernaast is het verschil met de mediaan van diezelfde "
                    "weekdag in dit venster; die afwijking is groot genoeg om "
                    "buiten de gebruikelijke spreiding van die weekdag te "
                    f"vallen. In dit venster gaat het om {_dagen(aantal)}.",
                    f"Le plus récent est le {dagnaam} {_datum(datum)}. Le "
                    "montant ci-contre est l'écart avec la médiane de ce même "
                    "jour de la semaine dans cette fenêtre ; cet écart sort de "
                    "la dispersion habituelle de ce jour. Dans cette fenêtre, "
                    f"il s'agit de {_dagen(aantal)}.",
                ),
                bedrag=_euro(verschil),
                soort="euro",
                richting=_richting_van(verschil),
                status="let_op",
            )
        )

    if bonritme is None or bonritme.bonnen_per_dag is None:
        punten.append(
            BriefingPunt(
                kop=t(
                    "Het aantal klanten is niet gemeten",
                    "Le nombre de clients n'est pas mesuré",
                ),
                waarom=(
                    t(
                        "De bonnentelling per dag is niet ingeladen. Zonder "
                        "die telling valt niet te zeggen of een omzetverandering "
                        "van het aantal klanten komt of van het gemiddelde "
                        "mandje, en dat zijn twee heel verschillende verhalen.",
                        "Le comptage quotidien des tickets n'est pas chargé. "
                        "Sans lui, impossible de dire si une variation du "
                        "chiffre d'affaires vient du nombre de clients ou du "
                        "panier moyen : ce sont deux histoires très "
                        "différentes.",
                    )
                    if bonritme is None
                    else t(
                        "Er is in dit venster geen enkele dag waarvoor zowel de "
                        "omzet als het aantal bonnen bekend is. De twee "
                        "extracties overlappen elkaar niet.",
                        "Dans cette fenêtre, aucun jour ne dispose à la fois du "
                        "chiffre d'affaires et du nombre de tickets. Les deux "
                        "extractions ne se recouvrent pas.",
                    )
                ),
                nodig=t(
                    f"De bonnentelling per dag uit Odoo — {_wie_platform()}.",
                    f"Le comptage quotidien des tickets depuis Odoo — "
                    f"{_wie_platform()}.",
                ),
                status="let_op",
            )
        )
    elif bonritme.dagen_zonder_bonnen >= BON_GAT_DAGEN:
        punten.append(
            BriefingPunt(
                kop=t(
                    "Voor een deel van de dagen ontbreekt de bonnentelling",
                    "Le comptage des tickets manque pour une partie des jours",
                ),
                waarom=t(
                    "Die dagen hebben wel omzet maar geen bonnen, en vallen "
                    "daarom uit het gemiddelde bonbedrag. Het cijfer klopt, "
                    "maar het loopt over minder dagen dan het venster suggereert.",
                    "Ces jours ont un chiffre d'affaires mais pas de tickets, "
                    "et sortent donc du panier moyen. Le chiffre est juste, "
                    "mais il porte sur moins de jours que la fenêtre ne le "
                    "laisse croire.",
                ),
                nodig=t(
                    f"De bonnenextractie moet die dagen alsnog dekken — "
                    f"{_wie_platform()}.",
                    f"L'extraction des tickets doit encore couvrir ces jours — "
                    f"{_wie_platform()}.",
                ),
                bedrag=str(bonritme.dagen_zonder_bonnen),
                soort="aantal",
                eenheid=_dagen_eenheid(bonritme.dagen_zonder_bonnen),
                status="let_op",
            )
        )

    return _bundel(punten)


# --- Verkoopkanalen ---------------------------------------------------------


def kanalen(
    *,
    versheid: Versheid,
    bronstanden: Sequence[Bronstand],
) -> Briefing:
    """De briefing boven Verkoopkanalen.

    `bronstanden` komt uit `kwaliteit.bronstanden(...)`: per bron of er nog iets
    binnenkomt. Dat is hier de bron van "een kanaal zonder data" — dezelfde
    meting die het scherm Instellingen toont, zodat de twee schermen niet elk
    hun eigen waarheid over Deliveroo vertellen. Een lege reeks levert geen
    punten op.
    """
    punten = _versheidspunten(versheid)

    for stand in bronstanden:
        punt = _bronpunt(stand, versheid.vandaag)
        if punt is not None:
            punten.append(punt)

    return _bundel(punten)


# --- Productmix -------------------------------------------------------------


def producten(*, versheid: Versheid, verschuiving: Verschuiving | None) -> Briefing:
    """De briefing boven Productmix.

    `verschuiving` is `berekening.productverschuiving(...)`: per product de
    omzet in het venster naast die in het even lange venster ervoor. None
    betekent "niet aangeleverd". Is de uitkomst niet vergelijkbaar (ongelijke
    vensters), dan is dát het punt: er staat op dit scherm geen vergelijking, en
    de reden hoort erbij.

    De grootste stijger en de grootste daler komen alleen in de briefing als ze
    minstens PRODUCTSCHUIF_AANDEEL van de vensteromzet bewegen. Zonder die
    drempel zou hier elke dag een product staan, en dan zegt het niets meer.
    """
    punten = _versheidspunten(versheid)

    if verschuiving is None:
        return _bundel(punten)

    if not verschuiving.vergelijkbaar:
        punten.append(
            BriefingPunt(
                kop=t(
                    "Er is geen vergelijking met de vorige periode",
                    "Il n'y a pas de comparaison avec la période précédente",
                ),
                waarom=t(
                    f"Het venster telt {_dagen(verschuiving.dagen)} met gemeten "
                    f"verkoop, de periode ervoor "
                    f"{_dagen(verschuiving.vorig_dagen)}. Bij ongelijke "
                    "vensters stijgt op papier bijna elk product en staan er "
                    "dalers in de tabel die niet gedaald zijn; dat is een "
                    "sluiting die zich voordoet als vraaguitval.",
                    f"La fenêtre compte {_dagen(verschuiving.dagen)} de vente "
                    f"mesurée, la période précédente "
                    f"{_dagen(verschuiving.vorig_dagen)}. Avec des fenêtres "
                    "inégales, presque tout produit monte sur le papier et le "
                    "tableau montre des baisses qui n'en sont pas : c'est une "
                    "fermeture déguisée en baisse de la demande.",
                ),
                status="let_op",
            )
        )
        return _bundel(punten)

    rijen = verschuiving.rijen
    if rijen.empty:
        return _bundel(punten)

    vensteromzet = Decimal(str(float(rijen["omzet_nu"].sum())))
    grens = vensteromzet * PRODUCTSCHUIF_AANDEEL
    if grens <= 0:
        return _bundel(punten)

    for rij, omhoog in ((rijen.iloc[0], True), (rijen.iloc[-1], False)):
        verschil = Decimal(str(float(rij["verschil"])))
        if omhoog and verschil <= 0:
            continue
        if not omhoog and verschil >= 0:
            continue
        if abs(verschil) < grens:
            continue
        naam = (
            str(rij["product_naam"])
            if pd.notna(rij["product_naam"])
            else f"Product {rij['product_id']}"
        )
        punten.append(
            BriefingPunt(
                kop=(
                    t(
                        f"{naam} trekt de omzet zichtbaar omhoog",
                        f"{naam} tire visiblement le chiffre d'affaires vers le "
                        "haut",
                    )
                    if omhoog
                    else t(
                        f"{naam} levert zichtbaar in",
                        f"{naam} recule visiblement",
                    )
                ),
                waarom=t(
                    f"Gemeten over de laatste {_dagen(verschuiving.dagen)} met "
                    f"verkoop, naast even veel dagen ervoor. Het bedrag "
                    "hiernaast is het verschil in omzet van dit ene product, en "
                    "dat is meer dan "
                    f"{_procent_tekst(float(PRODUCTSCHUIF_AANDEEL))} van de omzet "
                    "in dit venster.",
                    f"Mesuré sur les {_dagen(verschuiving.dagen)} de vente les "
                    "plus récents, face à autant de jours précédents. Le "
                    "montant ci-contre est l'écart de chiffre d'affaires de ce "
                    "seul produit, soit plus de "
                    f"{_procent_tekst(float(PRODUCTSCHUIF_AANDEEL))} du chiffre "
                    "d'affaires de la fenêtre.",
                ),
                bedrag=_euro(verschil),
                soort="euro",
                richting=_richting_van(verschil),
                status="let_op",
            )
        )

    return _bundel(punten)


# --- Margebewaking ----------------------------------------------------------


def marge(
    *,
    versheid: Versheid,
    beeld: Margebeeld | None,
    invoer_fout: str | None,
) -> Briefing:
    """De briefing boven Margebewaking.

    `beeld` is `berekening.marge_per_groep(...)`. None betekent dat er geen
    omzet is om een marge op te berekenen — een ander verhaal dan een
    ontbrekend kostenmodel, en de briefing houdt die twee uit elkaar.

    `invoer_fout` is de reden waarom een aanwezig kostenbestand genegeerd wordt,
    of None. Die tekst komt uit de invoerlaag en blijft staan zoals ze is: het
    is de foutmelding zelf, en die vertalen zou hem onvindbaar maken.
    """
    punten = _versheidspunten(versheid)

    if invoer_fout:
        punten.append(
            BriefingPunt(
                kop=t(
                    "Het ingevulde kostenbestand wordt genegeerd",
                    "Le fichier de coûts saisi est ignoré",
                ),
                waarom=t(
                    f"De invoer is niet te lezen: {invoer_fout} Zolang dat zo "
                    "is, rekent dit scherm met geen enkel ingevuld criterium — "
                    "en een marge die stil verdwijnt is erger dan geen marge.",
                    f"La saisie est illisible : {invoer_fout} Tant que c'est le "
                    "cas, cet écran ne calcule avec aucun critère saisi — et "
                    "une marge qui disparaît en silence est pire qu'une absence "
                    "de marge.",
                ),
                nodig=t(
                    f"De invoer moet hersteld worden — {_wie_beheerder()}.",
                    f"La saisie doit être corrigée — {_wie_beheerder()}.",
                ),
                status="actie",
            )
        )

    if beeld is None:
        punten.append(
            BriefingPunt(
                kop=t(
                    "Er is geen omzet om een marge op te berekenen",
                    "Il n'y a pas de chiffre d'affaires sur lequel calculer une "
                    "marge",
                ),
                waarom=t(
                    "In het venster van dit scherm is geen winkelomzet gemeten. "
                    "Een marge van nul procent zou hier een zaak tonen die "
                    "niets verdient, in plaats van een venster zonder meting.",
                    "Aucun chiffre d'affaires en magasin n'a été mesuré dans la "
                    "fenêtre de cet écran. Une marge de zéro pour cent "
                    "montrerait un commerce qui ne gagne rien, au lieu d'une "
                    "fenêtre sans mesure.",
                ),
                status="let_op",
            )
        )
        return _bundel(punten)

    if beeld.gewogen_pct is None:
        punten.append(
            BriefingPunt(
                kop=t(
                    "Niemand heeft kosten ingevuld, dus er is geen marge",
                    "Personne n'a saisi de coûts : il n'y a donc pas de marge",
                ),
                waarom=t(
                    "Het platform kan de marge niet zelf berekenen: Odoo "
                    "berekende de kostprijs op alle kassabonregels en kwam "
                    "vrijwel altijd op nul uit. Het bedrag hiernaast is de "
                    "omzet in dit venster waarover dus geen marge te zeggen "
                    "valt.",
                    "La plateforme ne peut pas calculer la marge elle-même : "
                    "Odoo a calculé le prix de revient sur toutes les lignes de "
                    "ticket et est presque toujours arrivé à zéro. Le montant "
                    "ci-contre est le chiffre d'affaires de cette fenêtre sur "
                    "lequel rien ne peut donc être dit.",
                ),
                nodig=t(
                    f"De kostencriteria per productgroep — {_wie_beheerder()}.",
                    f"Les critères de coûts par groupe de produits — "
                    f"{_wie_beheerder()}.",
                ),
                bedrag=_euro(beeld.totale_omzet),
                soort="euro",
                status="actie",
            )
        )
        return _bundel(punten)

    if beeld.dekking_pct < DEKKING_DREMPEL:
        ongedekt = beeld.totale_omzet - beeld.gedekte_omzet
        zonder = [
            str(g)
            for g in beeld.rijen.loc[beeld.rijen["marge_pct"].isna(), "groep"].head(6)
        ]
        opsomming = ", ".join(zonder)
        punten.append(
            BriefingPunt(
                kop=t(
                    "Een deel van de omzet valt buiten de marge",
                    "Une partie du chiffre d'affaires reste hors marge",
                ),
                waarom=t(
                    f"Het gewogen margepercentage weegt over "
                    f"{_procent_tekst(float(beeld.dekking_pct) / 100)} van de "
                    "omzet; de rest heeft geen ingevulde kosten. Zonder invoer "
                    f"blijven: {opsomming}. Het bedrag hiernaast is de omzet "
                    "waarover geen marge berekend is.",
                    f"Le pourcentage de marge pondéré porte sur "
                    f"{_procent_tekst(float(beeld.dekking_pct) / 100)} du chiffre "
                    "d'affaires ; le reste n'a pas de coûts saisis. Restent "
                    f"sans saisie : {opsomming}. Le montant ci-contre est le "
                    "chiffre d'affaires sans marge calculée.",
                ),
                nodig=t(
                    f"De ontbrekende kostencriteria — {_wie_beheerder()}.",
                    f"Les critères de coûts manquants — {_wie_beheerder()}.",
                ),
                bedrag=_euro(ongedekt),
                soort="euro",
                status="actie" if beeld.dekking_pct < DEKKING_ERNSTIG else "let_op",
            )
        )

    negatief = beeld.rijen[
        beeld.rijen["marge_pct"].map(lambda m: m is not None and m < 0)
    ]
    if not negatief.empty:
        namen = ", ".join(str(g) for g in negatief["groep"].head(6))
        punten.append(
            BriefingPunt(
                kop=t(
                    "Bij een of meer groepen zijn de kosten hoger dan de omzet",
                    "Pour un ou plusieurs groupes, les coûts dépassent le "
                    "chiffre d'affaires",
                ),
                waarom=t(
                    f"De ingevulde criteria tellen daar op tot meer dan honderd "
                    f"procent van de omzet: {namen}. Dat kan kloppen — een "
                    "groep kán met verlies verkopen — maar het is vaker een "
                    "tikfout, en het telt gewoon mee in het gewogen cijfer.",
                    f"Les critères saisis y dépassent cent pour cent du chiffre "
                    f"d'affaires : {namen}. Cela peut être exact — un groupe "
                    "peut vendre à perte — mais c'est plus souvent une faute de "
                    "frappe, et cela compte tel quel dans le chiffre pondéré.",
                ),
                nodig=t(
                    f"De invoer van deze groepen moet nagekeken worden — "
                    f"{_wie_beheerder()}.",
                    f"La saisie de ces groupes doit être vérifiée — "
                    f"{_wie_beheerder()}.",
                ),
                bedrag=str(len(negatief)),
                soort="aantal",
                eenheid=t("groepen", "groupes") if len(negatief) != 1
                else t("groep", "groupe"),
                status="actie",
            )
        )

    return _bundel(punten)


# --- Prognose ---------------------------------------------------------------


def prognose(
    *,
    versheid: Versheid,
    venster: Prognosevenster | None,
    bias: float | None,
    banddekking: pd.DataFrame | None,
    band_doel: float | None,
    kalenderdekking: dt.date | None,
    sluitingsdekking: dt.date | None,
    categorieen_overgeslagen: Sequence[str],
    #: De dagen die een beheerder op het scherm Sluitingsdagen bevestigd open
    #: heeft verklaard. Een bevestigde dag is beantwoord en telt niet meer als
    #: "onbekend voorbij de lijst" — het voorbehoud werkt per dag.
    bevestigde_dagen: frozenset = frozenset(),
) -> Briefing:
    """De briefing boven Prognose.

    `venster` is `canoniek.prognosevenster(...)`, dezelfde die het scherm
    gebruikt. Daaruit komt of er überhaupt dagen te voorspellen zijn, en tot
    waar het venster reikt.

    `bias` is de systematische afwijking uit de backtest, als fractie van de
    dagomzet, waarbij + betekent dat het model gemiddeld te hoog voorspelt.
    None betekent "niet gemeten": dan zwijgt de briefing erover in plaats van
    een nul te suggereren.

    `banddekking` is `backtest.rolling.dekking` met de kolommen `binnen_band`,
    `n` en `beloofd`; `band_doel` is de dekking die beloofd wordt (0,80).
    Dekt de band out-of-sample minder dan dat, dan staat dat hier — een band
    die breder oogt dan ze dekt, is precies de stille leugen die dit platform
    niet vertelt (harde regel 7).

    `kalenderdekking` en `sluitingsdekking` zijn de laatste dag waarvoor de
    schoolvakantiekalender respectievelijk de sluitingslijst gevuld is. Reikt
    het venster daar voorbij, dan voorspelt het model die dagen als gewone open
    dagen, en dat is een aanname die op het scherm hoort.

    `categorieen_overgeslagen` zijn de categorieën zonder eigen prognose omdat
    er te weinig gemeten dagen zijn om hun fout te meten (harde regel 7).
    """
    punten = _versheidspunten(versheid)
    laatste_doeldag = (
        venster.dagen.max().date()
        if venster is not None and len(venster.dagen) > 0
        else None
    )

    if venster is not None and len(venster.dagen) == 0:
        punten.append(
            BriefingPunt(
                kop=t(
                    "Er blijft geen dag over om te voorspellen",
                    "Il ne reste aucun jour à prévoir",
                ),
                waarom=t(
                    f"Vanaf {_datum(venster.start)} valt elke dag in het "
                    "venster af: gemeten en gesloten, of vooraf als gesloten "
                    "aangekondigd. Een nul zou hier een verwachte omzet van nul "
                    "euro suggereren, en dat is niet wat er aan de hand is.",
                    f"À partir du {_datum(venster.start)}, chaque jour de la "
                    "fenêtre est écarté : mesuré et fermé, ou annoncé fermé à "
                    "l'avance. Un zéro suggérerait ici un chiffre d'affaires "
                    "attendu nul, ce qui n'est pas le cas.",
                ),
                status="let_op",
            )
        )

    if kalenderdekking is not None and laatste_doeldag is not None:
        buiten = int(sum(1 for d in venster.dagen if d.date() > kalenderdekking))
        if buiten:
            punten.append(
                BriefingPunt(
                    kop=t(
                        "De vakantiekalender reikt niet tot het einde van de "
                        "prognose",
                        "Le calendrier des vacances ne couvre pas toute la "
                        "prévision",
                    ),
                    waarom=t(
                        f"De schoolvakanties zijn gevuld tot "
                        f"{_datum(kalenderdekking)}, en dit venster loopt tot "
                        f"{_datum(laatste_doeldag)}. De dagen ertussen worden "
                        "voorspeld alsof het gewone dagen zijn, zonder "
                        "vakantiecorrectie — en dat is precies de correctie die "
                        "de backtest heeft opgeleverd.",
                        f"Les vacances scolaires sont renseignées jusqu'au "
                        f"{_datum(kalenderdekking)}, et cette fenêtre va "
                        f"jusqu'au {_datum(laatste_doeldag)}. Les jours "
                        "intermédiaires sont prévus comme des jours ordinaires, "
                        "sans correction de vacances — précisément la "
                        "correction issue du backtest.",
                    ),
                    nodig=t(
                        f"De kalender moet ververst worden (`make vakanties`) — "
                        f"{_wie_platform()}.",
                        f"Le calendrier doit être actualisé (`make vakanties`) — "
                        f"{_wie_platform()}.",
                    ),
                    bedrag=str(buiten),
                    soort="aantal",
                    eenheid=_dagen_eenheid(buiten),
                    status="actie",
                )
            )

    if laatste_doeldag is not None:
        if sluitingsdekking is None and not bevestigde_dagen:
            punten.append(
                BriefingPunt(
                    kop=t(
                        "Het platform kent geen geplande sluitingen",
                        "La plateforme ne connaît aucune fermeture planifiée",
                    ),
                    waarom=t(
                        "Er is geen sluitingslijst aangeleverd en er is nog "
                        "niets bevestigd op het scherm Sluitingsdagen. Voor "
                        "elke dag in dit venster neemt de prognose daarom aan "
                        "dat de winkel open is. Dat is een aanname en geen "
                        "meting: valt er een sluiting in deze week, dan staat "
                        "er nu een verwachting op een dag dat de zaak dicht is.",
                        "Aucune liste de fermetures n'a été fournie et rien "
                        "n'a encore été confirmé sur l'écran Jours de "
                        "fermeture. Pour chaque jour de cette fenêtre, la "
                        "prévision suppose donc la boutique ouverte. C'est une "
                        "hypothèse et non une mesure : si une fermeture tombe "
                        "cette semaine, une prévision est affichée pour un "
                        "jour de fermeture.",
                    ),
                    nodig=t(
                        f"De geplande sluitingsdagen, op het scherm "
                        f"Sluitingsdagen — {_wie_bakkerij()}.",
                        f"Les jours de fermeture planifiés, sur l'écran Jours "
                        f"de fermeture — {_wie_bakkerij()}.",
                    ),
                    status="let_op",
                )
            )
        else:
            # Het voorbehoud werkt per dag: een dag telt als beantwoord
            # wanneer hij binnen het bereik van de bestandslijst valt of op
            # het scherm Sluitingsdagen bevestigd is (dicht bevestigde dagen
            # staan niet in het venster). Zelfde regel als
            # contract._kalenderreden, en bewust dezelfde telling.
            grens = sluitingsdekking or dt.date.min
            onbekend = int(sum(
                1 for d in venster.dagen
                if d.date() > grens and d.date() not in bevestigde_dagen
            ))
            if onbekend:
                punten.append(
                    BriefingPunt(
                        kop=t(
                            "Niet elke dag in dit venster heeft een "
                            "sluitingsantwoord",
                            "Certains jours de cette fenêtre n'ont pas de "
                            "réponse de fermeture",
                        ),
                        waarom=t(
                            f"Voor {onbekend} van de {len(venster.dagen)} "
                            "dagen in dit venster is geen sluiting bekend en "
                            "geen bevestiging. Voor die dagen neemt de "
                            "prognose aan dat de winkel open is; niets-weten "
                            "is hier geen sluiting.",
                            f"Pour {onbekend} des {len(venster.dagen)} jours "
                            "de cette fenêtre, aucune fermeture n'est connue "
                            "et rien n'est confirmé. Pour ces jours, la "
                            "prévision suppose la boutique ouverte ; ne rien "
                            "savoir n'est pas une fermeture.",
                        ),
                        nodig=t(
                            "Eén bevestiging per dag (open of dicht) op het "
                            f"scherm Sluitingsdagen — {_wie_bakkerij()}.",
                            "Une confirmation par jour (ouvert ou fermé) sur "
                            f"l'écran Jours de fermeture — {_wie_bakkerij()}.",
                        ),
                        bedrag=str(onbekend),
                        soort="aantal",
                        eenheid=_dagen_eenheid(onbekend),
                        status="let_op",
                    )
                )

    punten.extend(_bandpunten(banddekking, band_doel))

    if bias is not None and abs(bias) >= BIAS_DREMPEL:
        te_hoog = bias > 0
        punten.append(
            BriefingPunt(
                kop=(
                    t(
                        "De prognose ligt gemiddeld te hoog",
                        "La prévision est en moyenne trop élevée",
                    )
                    if te_hoog
                    else t(
                        "De prognose ligt gemiddeld te laag",
                        "La prévision est en moyenne trop basse",
                    )
                ),
                waarom=t(
                    "Over de hele backtest wijkt de voorspelling niet alleen af, "
                    "ze wijkt stelselmatig dezelfde kant op. Zo'n scheefstand "
                    "middelt niet weg over een week: hij telt op in het "
                    "weektotaal.",
                    "Sur l'ensemble du backtest, la prévision ne fait pas que "
                    "s'écarter : elle s'écarte systématiquement du même côté. "
                    "Un tel biais ne se compense pas sur une semaine, il "
                    "s'additionne dans le total hebdomadaire.",
                ),
                bedrag=_procent_machine(bias * 100),
                soort="verschil",
                richting=_richting_van(bias),
                status="let_op",
            )
        )

    if categorieen_overgeslagen:
        namen = ", ".join(categorieen_overgeslagen)
        punten.append(
            BriefingPunt(
                kop=t(
                    "Niet elke categorie heeft een eigen prognose",
                    "Toutes les catégories n'ont pas leur propre prévision",
                ),
                waarom=t(
                    f"Zonder eigen prognose: {namen}. Er zijn te weinig gemeten "
                    "open dagen om de fout van die categorieën betrouwbaar te "
                    "meten, en een voorspelling zonder gemeten fout is een "
                    "mening.",
                    f"Sans prévision propre : {namen}. Il y a trop peu de jours "
                    "d'ouverture mesurés pour évaluer leur erreur de façon "
                    "fiable, et une prévision sans erreur mesurée est un avis.",
                ),
                bedrag=str(len(categorieen_overgeslagen)),
                soort="aantal",
                eenheid=t("categorieën", "catégories")
                if len(categorieen_overgeslagen) != 1
                else t("categorie", "catégorie"),
                status="let_op",
            )
        )

    return _bundel(punten)


def _bandpunten(
    banddekking: pd.DataFrame | None, band_doel: float | None
) -> list[BriefingPunt]:
    """Houdt de band wat ze belooft?

    Het enige punt in deze module dat 'goed' kan zijn, en dat is met opzet: de
    band is de belofte waar dit scherm op staat of valt, en een gemeten
    bevestiging daarvan is nieuws. De rest van de briefing meldt alleen wat er
    niet klopt.
    """
    if banddekking is None or banddekking.empty or band_doel is None:
        return []
    gemeten = banddekking.dropna(subset=["binnen_band"])
    gemeten = gemeten[gemeten["n"] > 0]
    if gemeten.empty:
        return []

    laagste = float(gemeten["binnen_band"].min())
    hoogste = float(gemeten["binnen_band"].max())

    # HET OORDEEL HANGT AAN DE ZWAKSTE HORIZONSTAP, niet aan de beste. Dat was
    # tot 15 augustus 2026 andersom (`hoogste < doel - tolerantie`), en dan
    # meldde dit punt "de band houdt wat ze belooft" terwijl het in dezelfde
    # zin toegaf dat de dekking bij 69% begon op een doel van 80%. Een band
    # belooft haar dekking op élke stap; oordelen op de beste stap is de
    # zelfbevestiging waar `rolling.dekking` in haar eigen docstring voor
    # waarschuwt. Bijkomend: de zwakste stap is doorgaans de verste, en juist
    # die draagt het weektotaal.
    if laagste < band_doel - BAND_TOLERANTIE:
        elke_stap = hoogste < band_doel - BAND_TOLERANTIE
        return [
            BriefingPunt(
                kop=(
                    t("De band dekt minder dagen dan ze belooft",
                      "L'intervalle couvre moins de jours qu'annoncé")
                    if elke_stap else
                    t("De band haalt haar doel niet op elke horizonstap",
                      "L'intervalle n'atteint pas sa cible à chaque pas")
                ),
                waarom=t(
                    f"Out-of-sample nagemeten valt de werkelijkheid "
                    f"{_procent_tekst(laagste)} tot {_procent_tekst(hoogste)} van de "
                    f"dagen binnen de band, waar {_procent_tekst(band_doel)} "
                    "bedoeld is. De zwakste stap is de verste, en die draagt "
                    "het weektotaal: verderop in de week valt de werkelijkheid "
                    "vaker buiten de band dan de grafiek suggereert.",
                    f"Mesuré hors échantillon, la réalité tombe dans "
                    f"l'intervalle {_procent_tekst(laagste)} à "
                    f"{_procent_tekst(hoogste)} des jours, alors que "
                    f"{_procent_tekst(band_doel)} est visé. Le pas le plus faible "
                    "est le plus lointain, et c'est lui qui porte le total "
                    "hebdomadaire : en fin de semaine, la réalité sort de "
                    "l'intervalle plus souvent que le graphique ne le laisse "
                    "croire.",
                ),
                status="let_op",
            )
        ]

    return [
        BriefingPunt(
            kop=t(
                "De band houdt wat ze belooft",
                "L'intervalle tient sa promesse",
            ),
            waarom=t(
                f"Out-of-sample nagemeten valt de werkelijkheid "
                f"{_procent_tekst(laagste)} tot {_procent_tekst(hoogste)} van de "
                f"dagen binnen de band, op een doel van "
                f"{_procent_tekst(band_doel)}. Gemeten in dezelfde rolling-origin "
                "backtest als de prognose zelf, niet aangenomen.",
                f"Mesuré hors échantillon, la réalité tombe dans l'intervalle "
                f"{_procent_tekst(laagste)} à {_procent_tekst(hoogste)} des jours, "
                f"pour un objectif de {_procent_tekst(band_doel)}. Mesuré dans le "
                "même backtest à origine glissante que la prévision elle-même, "
                "et non supposé.",
            ),
            status="goed",
        )
    ]


# --- Instellingen -----------------------------------------------------------

#: Machinenaam van een wachter -> het label dat een mens leest (nl, fr).
#: De wachters zelf leveren alleen hun sleutel en hun eigen toelichting; die
#: toelichting is de meting en blijft staan zoals ze geschreven is.
WACHTERLABELS = {
    "dubbele_sleutels": ("Dubbele rijen", "Lignes en double"),
    "negatieve_waarden": ("Negatieve waarden", "Valeurs négatives"),
    "gat_in_de_reeks": ("Gat in de reeks", "Trou dans la série"),
    "kalenderdekking": ("Kalenderdekking", "Couverture du calendrier"),
    "drempelrand": ("Drempel open of dicht", "Seuil ouvert ou fermé"),
    "bonnen_omzetdekking": (
        "Bonnentelling naast de omzet",
        "Comptage des tickets face au chiffre d'affaires",
    ),
    "censureringsdrempel": ("Leeg-reksignaal", "Signal de rayon vide"),
}


def _wachterlabel(naam: str) -> str:
    label = WACHTERLABELS.get(naam)
    return t(*label) if label else naam


def instellingen(
    *,
    versheid: Versheid,
    bronstanden: Sequence[Bronstand],
    wachters: Sequence[Wachter],
    kostenmodel_ingevuld: bool,
) -> Briefing:
    """De briefing boven Instellingen.

    Dit scherm draagt de stand van het platform zelf, dus hier staan de
    wachters en de bronstanden voluit. `wachters` komt uit
    `kwaliteit.wachters(...)`, `bronstanden` uit `kwaliteit.bronstanden(...)`.
    Lege reeksen leveren geen punten op en ook geen groen licht: een controle
    die niet gedraaid heeft, is niet hetzelfde als een controle die slaagde.

    De toelichting van een wachter gaat mee zoals ze geschreven is. Dat is de
    meting in haar eigen woorden, en in het Franse contract blijft die tekst
    Nederlands — zichtbaar in de vertaalteller, en dat is beter dan de meting
    vervangen door een vage samenvatting die wél vertaald is.
    """
    punten = _versheidspunten(versheid)
    signalen = 0

    for wachter in wachters:
        if wachter.uitkomst == "goed":
            continue
        signalen += 1
        label = _wachterlabel(wachter.naam)
        punten.append(
            BriefingPunt(
                kop=(
                    t(
                        f"De controle {label} slaat alarm",
                        f"Le contrôle {label} déclenche une alerte",
                    )
                    if wachter.uitkomst == "fout"
                    else t(
                        f"De controle {label} vraagt aandacht",
                        f"Le contrôle {label} demande de l'attention",
                    )
                ),
                waarom=t(
                    f"De meting zelf: {wachter.toelichting}",
                    f"La mesure elle-même : {wachter.toelichting}",
                ),
                nodig=t(
                    f"De data achter deze controle moet nagekeken worden — "
                    f"{_wie_platform()}.",
                    f"Les données derrière ce contrôle doivent être vérifiées — "
                    f"{_wie_platform()}.",
                ),
                status="actie" if wachter.uitkomst == "fout" else "let_op",
            )
        )

    for stand in bronstanden:
        punt = _bronpunt(stand, versheid.vandaag)
        if punt is not None:
            signalen += 1
            punten.append(punt)

    if not kostenmodel_ingevuld:
        signalen += 1
        punten.append(
            BriefingPunt(
                kop=t(
                    "Er is nog geen kostenmodel ingevuld",
                    "Aucun modèle de coûts n'est encore saisi",
                ),
                waarom=t(
                    "Zolang er per productgroep geen kostencriteria staan, "
                    "blijft het scherm Margebewaking leeg met die reden. Het "
                    "platform kan de marge niet zelf berekenen: de kostprijs "
                    "staat in het bronsysteem vrijwel overal op nul.",
                    "Tant qu'aucun critère de coûts n'est renseigné par groupe "
                    "de produits, l'écran Suivi des marges reste vide avec "
                    "cette raison. La plateforme ne peut pas calculer la marge "
                    "elle-même : dans le système source, le prix de revient est "
                    "presque partout à zéro.",
                ),
                nodig=t(
                    f"De kostencriteria per productgroep — {_wie_beheerder()}.",
                    f"Les critères de coûts par groupe de produits — "
                    f"{_wie_beheerder()}.",
                ),
                status="actie",
            )
        )

    if signalen == 0 and (bronstanden or wachters):
        punten.append(
            BriefingPunt(
                kop=t(
                    "Alle controles slagen en elke bron levert aan",
                    "Tous les contrôles passent et chaque source livre",
                ),
                waarom=t(
                    f"{len(wachters)} controles op de data en "
                    f"{len(bronstanden)} bronnen zijn nagekeken; geen ervan "
                    "meldt iets. Dat zegt niets over cijfers die niemand "
                    "aanlevert — wat daarvan bekend is, staat per scherm bij "
                    "het cijfer zelf.",
                    f"{len(wachters)} contrôles sur les données et "
                    f"{len(bronstanden)} sources ont été vérifiés ; aucun ne "
                    "signale quoi que ce soit. Cela ne dit rien des chiffres "
                    "que personne ne livre — ce qui en est connu figure par "
                    "écran, à côté du chiffre lui-même.",
                ),
                status="goed",
            )
        )

    return _bundel(punten)
