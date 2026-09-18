"""Scenario's op de prognose (blok 22): dezelfde motor, een andere kalender.

Een scenario is GEEN vrije schuif. "Prijs +5%" of een factor met de hand
verzetten is een mening op een scherm dat vertrouwen moet verdienen (harde
regel 7, en het afgewezen auditvoorstel van 14 aug). Wat wél mag: dezelfde
gebackteste voorspeller een andere kalenderínvoer geven — toon deze week
alsof het vakantie is, alsof het geen vakantie is, of zonder de
vakantiecorrectie. Elke variant is dan een uitkomst van het gemeten
mechanisme, en de echte prognose blijft het anker.

Dit staat klaar in afwachting van vraag 55 (bouwen in fase 1 of fase 2?):
de contractbouw rekent de varianten alleen met PROGNOSE_SCENARIOS=1 in de
omgeving, en de UI toont ze hoe dan ook niet. Voorbereiden mag, tonen niet.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from bakkerij.backtest.rolling import Voorspeller

#: De kolom die de varianten verzetten. Bewust alleen deze: het is het enige
#: kalenderkenmerk waarvan het effect gebacktest in de voorspeller zit.
KENMERK = "schoolvakantie"


@dataclass(frozen=True)
class Scenario:
    """Eén variant: de sleutel is machinetaal, de tekst komt uit de bouw."""

    sleutel: str
    dagen: pd.Series  # index = doeldagen, waarden = verwachte dagomzet
    weektotaal: float


def _met_kenmerk(
    prognosekal: pd.DataFrame, doeldagen: pd.DatetimeIndex, waarde: bool,
) -> pd.DataFrame:
    kal = prognosekal.copy()
    doel = kal["datum"].isin(doeldagen)
    kal.loc[doel, KENMERK] = waarde
    return kal


def scenario_prognoses(
    reeks: pd.Series,
    doeldagen: pd.DatetimeIndex,
    prognosekal: pd.DataFrame,
    *,
    basis: Voorspeller,
    maak_voorspeller: Callable[[pd.DataFrame], Voorspeller],
) -> list[Scenario]:
    """De drie kalendervarianten naast het anker.

    `basis` is de voorspeller zónder kalenderwikkel; `maak_voorspeller` bouwt
    de productievoorspeller uit een (aangepaste) prognosekalender. De functie
    verandert niets aan haar invoer en niets aan het anker: wie haar niet
    aanroept, krijgt exact hetzelfde contract als voorheen.
    """
    varianten = [
        ("als_vakantieweek", maak_voorspeller(
            _met_kenmerk(prognosekal, doeldagen, True))),
        ("zonder_vakantie", maak_voorspeller(
            _met_kenmerk(prognosekal, doeldagen, False))),
        ("zonder_correctie", basis),
    ]
    uit = []
    for sleutel, voorspeller in varianten:
        dagen = voorspeller(reeks, doeldagen)
        uit.append(Scenario(
            sleutel=sleutel,
            dagen=dagen,
            weektotaal=float(dagen.sum()),
        ))
    return uit
