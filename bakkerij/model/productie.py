"""Wat "in productie" is: één definitie, waar iedereen uit put.

WAAROM DEZE MODULE BESTAAT

Er waren drie constructies van dezelfde voorspeller. De contractbouw had er
één, het backtest-rapport leende die, en de diagnose bouwde hem met de hand na.
Nagebouwd is bijna nooit identiek, en hier was het verschil precies groot
genoeg om twee tegengestelde verdicten op te leveren over hetzelfde kenmerk:

    diagnose (nagebouwd)    heropeningscorrectie  +0,12 punt   -> adopteren
    E4 (geleend)            heropeningscorrectie  -0,002 punt  -> afwijzen

Het verschil zat niet in het model maar in de vlaggen. De diagnose leidde
"de eerste open dagen na een vakantie" af uit `reeks.index` — alleen gemeten
dagen — en `prognosekalender` uit `open_of_gepland_open` over de hele kalender,
toekomst inbegrepen. Twee constructies van dezelfde vlag, twee uitkomsten, en
geen manier om eerlijk te beslissen. Op 18 augustus 2026 is dat kenmerk daarom
twee keer aangenomen en twee keer teruggedraaid (zie `docs/beslissingen.md`).

Dezelfde val had op 14 augustus al een echte fout opgeleverd: het contract
toonde toen "met heropeningscorrectie, WAPE 7,6%" terwijl het getoonde cijfer
uit een ánder model kwam dan het gebackteste. Dat is harde regel 7 gebroken —
een voorspelling die niet uit haar eigen backtest komt.

Sinds 19 augustus 2026 is er één plaats, en dit is hem. Wie hier iets wijzigt,
wijzigt het voor de contractbouw, het backtest-rapport én de diagnose
tegelijk — en dat is precies de bedoeling: een kenmerk dat hier niet in
KENMERKEN staat, is nergens in productie.

WAT HIER NIET HOORT

Kandidaten. Een variant die gemeten wordt maar (nog) niet gekozen is, hoort in
het script dat haar meet. Deze module beschrijft alleen wat er vandaag draait.
"""

from __future__ import annotations

import pandas as pd

from bakkerij import canoniek
from bakkerij.features.calendar import (
    SCHOOLVAKANTIES_FR,
    markeer_schoolvakanties,
    overgangsdagen,
)
from bakkerij.model.verfijning import met_feestdagcorrectie, weekdag_niveau

#: De basisvoorspeller. Winnaar van de backtest van 13 augustus 2026 op beide
#: niveaus (8,2 % WAPE dagomzet, 20,1 % per product-dag; was 8,4 % en 20,2 %
#: met weekdag_gemiddelde). Belangrijker dan die marge: na een sluiting volgt
#: dit model het heropeningsniveau binnen twee weken, waar een vast venster er
#: acht nodig heeft.
BASIS = weekdag_niveau

#: De kenmerken waarmee de kalenderwikkel de basis corrigeert. Deze tuple ís de
#: definitie van "wat in productie is": staat een kenmerk hier niet in, dan
#: rekent het model er nergens mee, en dan mag geen enkel scherm het noemen.
#:
#: `schoolvakantie` staat er sinds 13 augustus (avond), op het FRANSTALIGE
#: regime. Beide regimes zijn getoetst: VL +0,19 punt totaal en 9,5 % -> 8,6 %
#: op de vakantiedagen, FR +0,41 punt en 7,8 % -> 6,0 % op de 86 geraakte
#: dagen. De lat van 0,5 punt op het TOTAAL is daarmee niet gehaald, maar het
#: harnas rekent een kenmerk dat een deelvenster raakt bewust op dat
#: deelvenster af (rolling.evalueer, alleen_dagen) — en daar wint FR ruim,
#: zonder ergens te verliezen.
#:
#: `heropening` stond hier van 14 tot 15 augustus en opnieuw op 18 augustus,
#: en is beide keren teruggedraaid. Het staat er nu niet. De volledige
#: geschiedenis staat in `docs/beslissingen.md`; wat ervan overblijft is de
#: reden dat deze module bestaat.
KENMERKEN: tuple[str, ...] = ("schoolvakantie",)

#: Zoveel open dagen na het einde van een vakantie zouden de
#: heropeningscorrectie dragen. De vlag wordt nog altijd berekend — de diagnose
#: meet ermee — maar hij staat niet in KENMERKEN en corrigeert dus niets.
HEROPENING_DAGEN = 3

#: De naam van de voorspeller op de modelkaart, in beide talen. Geen
#: moduleconstante die bij import in één taal bevriest: `voorspeller_naam()`
#: in de contractbouw kiest de taal van het moment.
VOORSPELLER_NAAM = ("weekdagmediaan, geschaald naar het niveau van de laatste "
                    "twee weken, met schoolvakantiecorrectie "
                    "(Franstalig regime)")
VOORSPELLER_NAAM_FR = ("médiane par jour de la semaine, mise à l'échelle du "
                       "niveau des deux dernières semaines, avec correction "
                       "des vacances scolaires (régime francophone)")

#: De interne naam van het model, zoals het harnas hem rapporteert.
MODELNAAM = "weekdag_niveau_vakantie_fr"


def open_of_gepland_open(kalender: pd.DataFrame) -> pd.Series:
    """Welke dagen tellen als open, verleden én toekomst.

    Exact de regel van `canoniek.prognosevenster`, en dat is geen toeval: een
    dag die daar een prognose krijgt, moet hier als open dag meetellen, anders
    rekent het model met een andere kalender dan het scherm toont.

        dicht  <=>  (gemeten EN niet open)  OF  vooraf aangekondigd dicht
        open   <=>  al de rest

    WAAROM NIET GEWOON `winkel_open`. Dat was de eerste versie, en ze was stil
    fout. `winkel_open` is alleen betekenisvol waar `winkel_gemeten` waar is —
    `canoniek.py` waarschuwt daar met zoveel woorden voor, twintig regels boven
    de functie die het misdeed. Buiten het gemeten bereik staat de kolom op
    False, dus élke toekomstige dag las als gesloten. Er was zelfs een
    `.fillna(True)` om ontbrekende dagen op te vangen, maar de kolom bevat
    nooit NaN: dode code die de indruk wekte dat het geval afgedekt was.

    Gevolg, gemeten op het contract van 15 augustus 2026: nul heropeningsdagen
    na 31 juli, dus 24, 25 en 26 augustus — de eerste drie open dagen na de
    Franstalige zomervakantie — kregen `kenmerk = None` terwijl de modelkaart
    "met heropeningscorrectie" en WAPE 7,6 % claimde. Het getoonde cijfer kwam
    uit een ánder model dan het gebackteste, en precies op de dagen waar de
    diagnose 21,0 % WAPE en een structurele −2.823 €/dag mat (harde regel 7).
    """
    gemeten = canoniek.als_bool(kalender["winkel_gemeten"])
    open_ = canoniek.als_bool(kalender["winkel_open"])
    dicht = gemeten & ~open_
    if "gepland_dicht" in kalender.columns:
        dicht = dicht | canoniek.als_bool(kalender["gepland_dicht"])
    return ~dicht


def prognosekalender(kalender: pd.DataFrame) -> pd.DataFrame:
    """De kalender zoals de voorspeller hem ziet: datum, schoolvakantie
    (FR-regime) en heropening (eerste open dagen na elke vakantie).

    Eén bouwplaats voor voorspeller, opbouw én diagnose, zodat de uitleg op het
    scherm en de meting in het rapport per constructie dezelfde vlaggen zien
    als het model.

    De heropeningskolom staat er ook al corrigeert ze niets (zie KENMERKEN).
    Weglaten zou de diagnose dwingen haar zelf af te leiden, en dan zijn we
    terug bij de twee constructies die deze module opheft.
    """
    vk = markeer_schoolvakanties(kalender[["datum"]].copy(), SCHOOLVAKANTIES_FR)
    open_dagen = pd.DatetimeIndex(
        kalender.loc[open_of_gepland_open(kalender), "datum"]
    )
    na, _ = overgangsdagen(open_dagen, SCHOOLVAKANTIES_FR, HEROPENING_DAGEN)
    vk["heropening"] = vk["datum"].isin(na)
    return vk


def wikkel(vakantiekalender: pd.DataFrame, *,
           kenmerken: tuple[str, ...] | None = None):
    """De basis, gewikkeld in de kalendercorrectie van een gegeven kalender.

    Bestaat apart van `bouw_voorspeller` voor de twee aanroepers die hun eigen
    kalender meebrengen: de scenario's (die de kalenderinvoer variëren binnen
    hetzelfde gebackteste mechanisme) en de diagnose (die dezelfde constructie
    op een variant meet). Vóór 19 augustus 2026 bouwden die twee de wikkel elk
    zelf — en dat is precies hoe een vierde constructie ontstaat.

    `kenmerken` is er alleen voor de diagnose: wie hem meegeeft, meet een
    kandidaat; wie hem weglaat, krijgt wat er vandaag draait.
    """
    gekozen = KENMERKEN if kenmerken is None else kenmerken
    return met_feestdagcorrectie(
        BASIS, vakantiekalender, kenmerken=gekozen,
        naam=MODELNAAM if gekozen == KENMERKEN else "kandidaat",
    )


def bouw_voorspeller(kalender: pd.DataFrame, *,
                     kenmerken: tuple[str, ...] | None = None):
    """De productievoorspeller: basis, gewikkeld in de kalendercorrectie.

    Gebouwd als functie omdat de correctie de kalender nodig heeft; de
    vakantieranges zelf staan als publieke, verversbare data in
    `features/schoolvakanties.json`.

    Dit is de aanroep die de contractbouw, het backtest-rapport en de diagnose
    alle drie doen. Wijkt er ooit één van af, dan is er weer meer dan één
    productievoorspeller.
    """
    return wikkel(prognosekalender(kalender), kenmerken=kenmerken)
