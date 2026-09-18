"""De v1-marge-invoer: één brutomarge per productgroep, uit een formulier.

Sinds 14 augustus 2026 is dit de oude vorm. Het kostenmodel
(bakkerij.kostenmodel) bouwt de brutomarge op uit kostencriteria en neemt een
bestaand marges.json zonder informatieverlies over (100 − marge wordt het
criterium "Totale kost"). Deze module blijft bestaan als lezer van die oude
bestanden; nieuwe invoer schrijft het formulier als kostenmodel.json.

De regelset van toen geldt onverkort:

  * Percentages zijn strings in het bestand en `Decimal` daarbuiten. Een marge
    van 62,5% die als float rondreist, is op het scherm een keer 62,499...
  * Een kapot bestand is een fout met een reden, geen leeg resultaat. Het
    margescherm toont die reden dan letterlijk (harde regel 8); stil terugvallen
    op "geen marges" zou een ingevulde marge laten verdwijnen zonder dat iemand
    het merkt.

Wat hier bewust NIET gebeurt: rekenen. Omzet maal marge staat in
`berekening.marge_per_groep`; deze module leest, toetst en niets meer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

PCT_MIN = Decimal(0)
PCT_MAX = Decimal(100)


@dataclass(frozen=True)
class MargeInvoer:
    """Wat de beheerder heeft ingevuld: groep -> brutomarge als percentage."""

    per_groep: dict[str, Decimal]
    ingevuld_door: str
    ingevuld_op: str  # ISO 8601, zoals het formulier het wegschreef


def parse_marges(tekst: str) -> MargeInvoer:
    """Van de bestandsinhoud naar een getoetste invoer. Puur, en streng:
    elke afwijking is een ValueError met de reden in gewone taal.

    De foutmeldingen hieronder zijn eentalig Nederlands, en dat blijft zo
    (18 augustus 2026): dit is het v1-legacy-leespad, alleen nog bereikt via
    `kostenmodel.lees_kostenmodel` wanneer er wél een oud marges.json en géén
    kostenmodel.json is. De v2-fouten in kostenmodel.py zijn tweetalig; wie
    hier tweetaligheid nodig heeft, migreert het bestand in plaats van dit
    pad uit te bouwen."""
    try:
        ruw = json.loads(tekst)
    except json.JSONDecodeError as fout:
        raise ValueError(f"Het margebestand is geen geldige JSON: {fout}") from fout
    if not isinstance(ruw, dict) or not isinstance(ruw.get("marges"), dict):
        raise TypeError(
            'Het margebestand mist het veld "marges" (groep -> percentage).'
        )

    per_groep: dict[str, Decimal] = {}
    for groep, waarde in ruw["marges"].items():
        naam = str(groep).strip()
        if not naam:
            raise ValueError("Een productgroep zonder naam kan geen marge dragen.")
        if not isinstance(waarde, str):
            raise TypeError(
                f'De marge van "{naam}" moet een string zijn met punt-decimaal '
                f'(bv. "62.5"), geen {type(waarde).__name__}.'
            )
        try:
            pct = Decimal(waarde)
        except InvalidOperation as fout:
            raise ValueError(
                f'De marge van "{naam}" ({waarde!r}) is geen getal.'
            ) from fout
        if not PCT_MIN <= pct <= PCT_MAX:
            raise ValueError(
                f'De marge van "{naam}" is {pct}%, buiten het bereik 0-100.'
            )
        per_groep[naam] = pct

    return MargeInvoer(
        per_groep=per_groep,
        ingevuld_door=str(ruw.get("ingevuld_door", "")),
        ingevuld_op=str(ruw.get("ingevuld_op", "")),
    )


def lees_marges(pad: Path) -> MargeInvoer | None:
    """None wanneer het bestand er niet is — dat is de normale beginstand,
    geen fout. Een bestand dat er wél is maar niet deugt, geeft ValueError."""
    if not pad.exists():
        return None
    return parse_marges(pad.read_text(encoding="utf-8"))
