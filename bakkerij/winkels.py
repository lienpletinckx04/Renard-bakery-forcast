"""De winkelindeling: welke filialen samen één verkooppunt vormen.

Het canonieke model draagt `filiaal_id` sinds dag één, maar het platform toont
tot nu toe één geheel. Deze module maakt de indeling een instelling van de
klant in plaats van een aanname van ons: `data/config/winkels.json` (buiten
git) zegt welke filialen bij welke winkel horen, en de contractbouw schrijft
per winkel een eigen contractmap naast het totaal. Zonder bestand verandert er
niets — één geheel, zoals vandaag. Dat is bewust: vraag 18 (registers of
vestigingen) ligt nog bij de opdrachtgever, en zodra er een tweede vestiging
komt, is dit één configregel in plaats van een verbouwing.

De prognose blijft per winkel overeind: elke winkel krijgt zijn eigen reeks,
zijn eigen backtest en zijn eigen band. Een winkel met te weinig historiek
krijgt géén prognose maar een reden (harde regel 7 en 8).

Bestandsvorm:

    {"winkels": [{"naam": "Elsene", "filialen": ["1", "2", "3"]}]}

De slug (mapnaam onder platform/contract/winkels/) wordt hier afgeleid en
getoetst: alleen [a-z0-9-], want hij wordt een pad. Een cookie of URL die een
winkel kiest, wordt altijd tegen deze lijst gehouden en nooit als pad vertrouwd.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

MAX_WINKELS = 12
NAAM_MAX = 40


@dataclass(frozen=True)
class Winkel:
    naam: str
    slug: str
    filialen: tuple[str, ...]


def slug_van(naam: str) -> str:
    """Padveilige slug: accenten weg, kleine letters, streepjes."""
    plat = unicodedata.normalize("NFKD", naam).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", plat.casefold()).strip("-")
    if not slug:
        raise ValueError(
            f'Uit de winkelnaam "{naam}" valt geen bruikbare mapnaam af te leiden.'
        )
    return slug


def parse_winkels(tekst: str) -> tuple[Winkel, ...]:
    """Van bestandsinhoud naar een getoetste indeling; elke afwijking is een
    fout met reden, want een halve indeling zou omzet stil laten verdwijnen."""
    try:
        ruw = json.loads(tekst)
    except json.JSONDecodeError as fout:
        raise ValueError(f"Het winkelbestand is geen geldige JSON: {fout}") from fout
    if not isinstance(ruw, dict) or not isinstance(ruw.get("winkels"), list):
        raise TypeError('Het winkelbestand mist het veld "winkels" (lijst).')
    if len(ruw["winkels"]) > MAX_WINKELS:
        raise ValueError(f"Meer dan {MAX_WINKELS} winkels; dat is geen indeling "
                         "meer maar een vergissing.")

    winkels: list[Winkel] = []
    slugs: set[str] = set()
    geclaimd: dict[str, str] = {}  # filiaal_id -> winkelnaam
    for rij in ruw["winkels"]:
        if not isinstance(rij, dict) or not isinstance(rij.get("naam"), str):
            raise TypeError('Elke winkel heeft een veld "naam" (tekst) nodig.')
        naam = re.sub(r"\s+", " ", rij["naam"]).strip()
        if not naam or len(naam) > NAAM_MAX:
            raise ValueError(
                f"Een winkelnaam moet 1 tot {NAAM_MAX} tekens tellen."
            )
        filialen = rij.get("filialen")
        if not isinstance(filialen, list) or not filialen:
            raise ValueError(
                f'Winkel "{naam}" heeft geen filialen; een winkel zonder '
                "filialen heeft geen data."
            )
        ids = tuple(str(f).strip() for f in filialen)
        if any(not f for f in ids):
            raise ValueError(f'Winkel "{naam}" bevat een leeg filiaal-id.')
        for f in ids:
            if f in geclaimd:
                raise ValueError(
                    f'Filiaal "{f}" staat bij "{geclaimd[f]}" én bij "{naam}"; '
                    "een filiaal hoort bij precies één winkel."
                )
            geclaimd[f] = naam
        slug = slug_van(naam)
        if slug in slugs:
            raise ValueError(
                f'Twee winkels leiden tot dezelfde mapnaam "{slug}"; '
                "geef ze duidelijker verschillende namen."
            )
        slugs.add(slug)
        winkels.append(Winkel(naam=naam, slug=slug, filialen=ids))

    return tuple(winkels)


def lees_winkels(pad: Path) -> tuple[Winkel, ...]:
    """Leeg zonder bestand — dan is er één geheel, zoals vandaag."""
    if not pad.exists():
        return ()
    return parse_winkels(pad.read_text(encoding="utf-8"))


def niet_toegewezen(filiaal_ids: set[str],
                    winkels: tuple[Winkel, ...]) -> tuple[str, ...]:
    """Filialen mét data die in geen enkele winkel staan. Die blijven in het
    totaal meetellen maar vallen buiten elke winkelweergave; de contractbouw
    meldt ze hardop in plaats van ze stil te laten verdwijnen."""
    geclaimd = {f for w in winkels for f in w.filialen}
    return tuple(sorted(filiaal_ids - geclaimd))
