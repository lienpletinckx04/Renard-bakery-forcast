"""Beslislaag: van vraagverdeling naar bakaantal.

Dit is de kern van het project. De voorspelling is de tussenstap, dit is het
product. Zie docs/model-ontwerp.md.

Het krantenverkopersprobleem: als een gemiste verkoop meer kost dan een
onverkocht stuk, bak je bewust boven de mediaan. Het optimale percentiel is

    q* = Cu / (Cu + Co)

met Cu de kost van te weinig (gederfde marge) en Co de kost van te veel
(productiekost min restwaarde). Too Good To Go verhoogt de restwaarde, verlaagt
daarmee Co, en verschuift q* omhoog. Het optimum ligt dus niet op nul
verspilling, en dat is precies de inzicht dat de klant zelf niet heeft.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Economie:
    """De economie van één product in één filiaal.

    Alle bedragen in euro per stuk, exclusief btw.
    """

    verkoopprijs: float
    productiekost: float
    restwaarde: float = 0.0
    kanaalcommissie: float = 0.0

    def __post_init__(self) -> None:
        if self.verkoopprijs < 0 or self.productiekost < 0:
            raise ValueError("Prijzen en kosten kunnen niet negatief zijn.")
        if self.restwaarde > self.productiekost:
            raise ValueError(
                "Restwaarde boven productiekost betekent dat overproductie winst "
                "oplevert. Controleer de cijfers voor je hierop bakt."
            )
        if not 0 <= self.kanaalcommissie < 1:
            raise ValueError("Kanaalcommissie is een fractie tussen 0 en 1.")

    @property
    def kost_te_weinig(self) -> float:
        """Gederfde nettomarge op een stuk dat je had kunnen verkopen."""
        netto = self.verkoopprijs * (1 - self.kanaalcommissie)
        return max(netto - self.productiekost, 0.0)

    @property
    def kost_te_veel(self) -> float:
        """Netto verlies op een stuk dat blijft liggen."""
        return max(self.productiekost - self.restwaarde, 0.0)

    @property
    def kritiek_percentiel(self) -> float:
        """Het percentiel van de vraagverdeling waarop je moet bakken."""
        cu, co = self.kost_te_weinig, self.kost_te_veel
        if cu + co == 0:
            return 0.5
        return cu / (cu + co)


def bakaantal(
    kwantielen: dict[float, float],
    economie: Economie,
    *,
    minimum: int = 0,
    veelvoud: int = 1,
) -> int:
    """Zet een vraagverdeling om in een concreet bakaantal.

    kwantielen: {0.5: 38.0, 0.75: 45.0, 0.9: 52.0, ...} uit de modellaag.
    minimum:    ondergrens voor toonbankpresentatie. Een leeg rek verkoopt ook
                de rest niet. Dit is een businessregel, geen modelregel.
    veelvoud:   een oven bakt in platen, niet in stuks. Rond af naar boven.
    """
    if not kwantielen:
        raise ValueError("Geen kwantielen meegegeven.")

    doel = economie.kritiek_percentiel
    aantal = _interpoleer(kwantielen, doel)
    aantal = max(aantal, float(minimum))
    if veelvoud > 1:
        aantal = math.ceil(aantal / veelvoud) * veelvoud
    return round(aantal)


def _interpoleer(kwantielen: dict[float, float], doel: float) -> float:
    """Lineaire interpolatie tussen de twee dichtstbijzijnde kwantielen."""
    punten = sorted(kwantielen.items())
    if doel <= punten[0][0]:
        return punten[0][1]
    if doel >= punten[-1][0]:
        return punten[-1][1]
    for (q1, v1), (q2, v2) in itertools.pairwise(punten):
        if q1 <= doel <= q2:
            if q2 == q1:
                return v1
            gewicht = (doel - q1) / (q2 - q1)
            return v1 + gewicht * (v2 - v1)
    return punten[-1][1]


def kost_van_beslissing(gebakken: int, werkelijke_vraag: float, economie: Economie) -> float:
    """Wat heeft deze beslissing achteraf gekost, in euro.

    Dit is de maat waarop de backtest afrekent. Niet MAPE: die straft fouten op
    kleine producten onevenredig en zegt niets over marge.
    """
    if gebakken >= werkelijke_vraag:
        over = gebakken - werkelijke_vraag
        return over * economie.kost_te_veel
    tekort = werkelijke_vraag - gebakken
    return tekort * economie.kost_te_weinig
