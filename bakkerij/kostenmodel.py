"""Het kostenmodel: kostencriteria per productgroep, beheerd door de klant.

Dit is versie 2 van de marge-invoer. Versie 1 (`bakkerij.marges`) vroeg één
brutomarge per productgroep; dit model bouwt diezelfde brutomarge op uit
kostencriteria die de beheerder zelf samenstelt — toevoegen, hernoemen,
verwijderen — naar het foodcost-denken uit de sector: grondstoffen, verlies en
verspilling, basisingrediënten. De brutomarge per groep is dan 100 min de som
van de ingevulde criteria. Dat rekenwerk staat in `berekening.marge_per_groep`;
deze module leest, toetst en niets meer.

Dezelfde regelset als v1:

  * De invoer leeft in `data/config/kostenmodel.json`, buiten git — het zijn
    bedrijfsgegevens van de eindklant. Migratie 005 draagt de databasevorm.
  * Percentages zijn strings in het bestand en `Decimal` daarbuiten.
  * Een kapot bestand is een fout met een reden, geen leeg resultaat.
  * Een bestaand `marges.json` (v1) gaat niet verloren: zonder v2-bestand wordt
    het gelezen als één criterium "Totale kost" met waarde 100 − brutomarge.
    Dat is een herschrijving van dezelfde invoer, geen nieuw cijfer.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from bakkerij import marges as v1
from bakkerij.taal import t

# Dezelfde grenzen als de v1-lezer, sinds 18 augustus 2026 uit één bron: een
# percentage is in beide vormen hetzelfde ding. Uit marges en niet andersom,
# want deze module importeert marges al (van_marges) — de andere richting is
# een importcykel.
PCT_MIN = v1.PCT_MIN
PCT_MAX = v1.PCT_MAX
MAX_CRITERIA = 12
NAAM_MAX = 60

# De naam waaronder een v1-brutomarge als kost binnenkomt (100 − marge).
# NL/FR als los paar en niet via t(): module-constanten bevriezen bij import
# op de standaardtaal; wie de naam gebruikt, kiest op dat moment de taal.
V1_CRITERIUM = "Totale kost"
V1_CRITERIUM_FR = "Coût total"

@dataclass(frozen=True)
class Criterium:
    naam: str
    omschrijving: str = ""


def standaard_criteria() -> tuple[Criterium, ...]:
    """Suggesties voor een leeg formulier, naar de foodcost-opbouw die in de
    sector gangbaar is. Dit zijn etiketten, geen cijfers: er hangt geen waarde
    aan tot een beheerder er een invult, en de beheerder mag ze schrappen of
    hernoemen.

    Een functie en geen constante: deze etiketten zijn de enige criterianamen
    die van óns komen (al het andere is invoer van de beheerder en blijft
    letterlijk staan), dus alleen deze volgen de ingestelde taal — en die
    staat pas vast op het moment van gebruik, niet bij import.
    """
    return (
        Criterium(t("Grondstoffen", "Matières premières"),
                  t("Inkoopkost van de ingrediënten (foodcost), als "
                    "percentage van de omzet van de groep.",
                    "Coût d'achat des ingrédients (food cost), en pourcentage "
                    "du chiffre d'affaires du groupe.")),
        Criterium(t("Verlies en verspilling", "Pertes et gaspillage"),
                  t("Bederf, snijverlies, fouten en onverkochte stuks.",
                    "Denrées avariées, chutes de découpe, erreurs et "
                    "invendus.")),
        Criterium(t("Basisingrediënten", "Ingrédients de base"),
                  t("Wat je gebruikt maar nooit per product rekent: bloem op "
                    "de werkbank, olie, zout. In de sector rekent men hier "
                    "1 à 2 %.",
                    "Ce qu'on utilise sans jamais le compter par produit : la "
                    "farine sur le plan de travail, l'huile, le sel. Le "
                    "secteur compte ici 1 à 2 %.")),
    )


@dataclass(frozen=True)
class Kostenmodel:
    """Wat de beheerder heeft samengesteld: de criteria (het menu) en per
    productgroep de ingevulde percentages per criterium."""

    criteria: tuple[Criterium, ...]
    waarden: dict[str, dict[str, Decimal]]  # groep -> criteriumnaam -> pct
    ingevuld_door: str = ""
    ingevuld_op: str = ""  # ISO 8601, zoals het formulier het wegschreef


def _pct(naam: str, criterium: str, waarde: object) -> Decimal:
    """Eén percentage, met dezelfde strengheid als v1: string, getal, 0-100."""
    if not isinstance(waarde, str):
        raise TypeError(t(
            f'De kost "{criterium}" van "{naam}" moet een string zijn met '
            f'punt-decimaal (bv. "30.5"), geen {type(waarde).__name__}.',
            f'Le coût "{criterium}" de "{naam}" doit être une chaîne avec un '
            f'point décimal (p. ex. "30.5"), pas {type(waarde).__name__}.',
        ))
    try:
        pct = Decimal(waarde)
    except InvalidOperation as fout:
        raise ValueError(t(
            f'De kost "{criterium}" van "{naam}" ({waarde!r}) is geen getal.',
            f'Le coût "{criterium}" de "{naam}" ({waarde!r}) n\'est pas un '
            f"nombre.",
        )) from fout
    if not PCT_MIN <= pct <= PCT_MAX:
        raise ValueError(t(
            f'De kost "{criterium}" van "{naam}" is {pct} %, '
            f"buiten het bereik 0-100.",
            f'Le coût "{criterium}" de "{naam}" est de {pct} %, '
            f"hors de la plage 0-100.",
        ))
    return pct


def parse_kostenmodel(tekst: str) -> Kostenmodel:
    """Van bestandsinhoud naar een getoetst model. Elke afwijking is een
    ValueError of TypeError met de reden in gewone taal."""
    try:
        ruw = json.loads(tekst)
    except json.JSONDecodeError as fout:
        raise ValueError(t(
            f"Het kostenmodel is geen geldige JSON: {fout}",
            f"Le modèle de coûts n'est pas un JSON valide : {fout}",
        )) from fout
    if not isinstance(ruw, dict) or not isinstance(ruw.get("criteria"), list):
        raise TypeError(t(
            'Het kostenmodel mist het veld "criteria" (lijst van criteria).',
            'Le modèle de coûts n\'a pas le champ "criteria" (liste de '
            "critères).",
        ))
    if not isinstance(ruw.get("waarden"), dict):
        raise TypeError(t(
            'Het kostenmodel mist het veld "waarden" '
            "(groep -> criterium -> percentage).",
            'Le modèle de coûts n\'a pas le champ "waarden" '
            "(groupe -> critère -> pourcentage).",
        ))

    criteria: list[Criterium] = []
    gezien: set[str] = set()
    for rij in ruw["criteria"]:
        if not isinstance(rij, dict) or not isinstance(rij.get("naam"), str):
            raise TypeError(t(
                'Elk criterium heeft een veld "naam" (tekst) nodig.',
                'Chaque critère doit avoir un champ "naam" (texte).',
            ))
        naam = re.sub(r"\s+", " ", rij["naam"]).strip()
        if not naam:
            raise ValueError(t(
                "Een criterium zonder naam kan geen kost dragen.",
                "Un critère sans nom ne peut pas porter de coût.",
            ))
        if len(naam) > NAAM_MAX:
            raise ValueError(t(
                f'De criteriumnaam "{naam[:20]}…" is langer dan {NAAM_MAX} '
                f"tekens.",
                f'Le nom de critère "{naam[:20]}…" dépasse {NAAM_MAX} '
                f"caractères.",
            ))
        if naam.casefold() in gezien:
            raise ValueError(t(
                f'Het criterium "{naam}" staat er twee keer in.',
                f'Le critère "{naam}" y figure deux fois.',
            ))
        gezien.add(naam.casefold())
        criteria.append(Criterium(naam, str(rij.get("omschrijving", "")).strip()))
    if len(criteria) > MAX_CRITERIA:
        raise ValueError(t(
            f"{len(criteria)} criteria; het kostenmodel draagt er hoogstens "
            f"{MAX_CRITERIA}. Voeg samen wat bij elkaar hoort.",
            f"{len(criteria)} critères ; le modèle de coûts en porte au plus "
            f"{MAX_CRITERIA}. Regroupez ce qui va ensemble.",
        ))

    bekend = {c.naam for c in criteria}
    waarden: dict[str, dict[str, Decimal]] = {}
    for groep, per_criterium in ruw["waarden"].items():
        naam = str(groep).strip()
        if not naam:
            raise ValueError(t(
                "Een productgroep zonder naam kan geen kosten dragen.",
                "Un groupe de produits sans nom ne peut pas porter de coûts.",
            ))
        if not isinstance(per_criterium, dict):
            raise TypeError(t(
                f'De waarden van "{naam}" moeten een object zijn '
                "(criterium -> percentage).",
                f'Les valeurs de "{naam}" doivent être un objet '
                "(critère -> pourcentage).",
            ))
        rij: dict[str, Decimal] = {}
        for criterium, waarde in per_criterium.items():
            if criterium not in bekend:
                raise ValueError(t(
                    f'"{naam}" draagt een kost voor het onbekende criterium '
                    f'"{criterium}"; dat staat niet in de criterialijst.',
                    f'"{naam}" porte un coût pour le critère inconnu '
                    f'"{criterium}" ; il ne figure pas dans la liste des '
                    f"critères.",
                ))
            rij[criterium] = _pct(naam, criterium, waarde)
        if rij:
            waarden[naam] = rij

    return Kostenmodel(
        criteria=tuple(criteria),
        waarden=waarden,
        ingevuld_door=str(ruw.get("ingevuld_door", "")),
        ingevuld_op=str(ruw.get("ingevuld_op", "")),
    )


def naar_boom(model: Kostenmodel) -> dict:
    """Het model terug in de vorm waarin het bestand het draagt.

    Percentages worden weer strings met punt-decimaal, precies zoals
    `parse_kostenmodel` ze verwacht: `Decimal("30.50")` wordt `"30.50"` en niet
    `30.5`. Zo is deze functie de exacte omkering van de parser, en kan alles
    wat het model ergens anders heen moet brengen (de database, een export) die
    ene vorm hergebruiken in plaats van er een tweede naast te zetten.
    """
    return {
        "versie": 2,
        "ingevuld_door": model.ingevuld_door,
        "ingevuld_op": model.ingevuld_op,
        "criteria": [
            {"naam": c.naam, "omschrijving": c.omschrijving}
            for c in model.criteria
        ],
        "waarden": {
            groep: {criterium: str(pct) for criterium, pct in per_criterium.items()}
            for groep, per_criterium in model.waarden.items()
        },
    }


def toets(model: Kostenmodel) -> Kostenmodel:
    """Dezelfde strengheid als `parse_kostenmodel`, op een al gebouwd model.

    Een `Kostenmodel` kan ook buiten de parser om ontstaan -- uit databaserijen,
    uit een testfixture, uit code die het zelf samenstelt. Dan gelden de regels
    onverkort: hoogstens MAX_CRITERIA criteria, geen dubbele of naamloze namen,
    percentages tussen 0 en 100, en geen kost voor een criterium dat niet in de
    lijst staat.

    Bewust via `naar_boom` + `parse_kostenmodel` en niet als een tweede reeks
    controles: twee validaties naast elkaar lopen uit elkaar zodra iemand er één
    aanpast, en dan is de strengste toevallig de eerste die je aanroept.
    """
    return parse_kostenmodel(json.dumps(naar_boom(model)))


def van_marges(invoer: v1.MargeInvoer) -> Kostenmodel:
    """v1 -> v2 zonder informatieverlies: een brutomarge van 55% wordt het
    criterium "Totale kost" met 45%. Zelfde cijfer, andere schrijfwijze.

    De criteriumnaam is de enige die niet van de beheerder komt maar van deze
    herschrijving zelf, en volgt daarom — anders dan opgeslagen namen — de
    ingestelde taal.
    """
    naam = t(V1_CRITERIUM, V1_CRITERIUM_FR)
    return Kostenmodel(
        criteria=(Criterium(
            naam,
            t("Overgenomen uit de eerdere brutomarge-invoer (100 − marge).",
              "Repris de l'ancienne saisie de marge brute (100 − marge)."),
        ),),
        waarden={
            groep: {naam: PCT_MAX - marge}
            for groep, marge in invoer.per_groep.items()
        },
        ingevuld_door=invoer.ingevuld_door,
        ingevuld_op=invoer.ingevuld_op,
    )


def lees_kostenmodel(pad: Path, v1_pad: Path | None = None) -> Kostenmodel | None:
    """None wanneer er niets is ingevuld — de normale beginstand, geen fout.
    Een v2-bestand wint; zonder v2 telt een v1-`marges.json` via `van_marges`.
    Een bestand dat er wél is maar niet deugt, geeft ValueError/TypeError."""
    if pad.exists():
        return parse_kostenmodel(pad.read_text(encoding="utf-8"))
    if v1_pad is not None and v1_pad.exists():
        oud = v1.lees_marges(v1_pad)
        if oud is not None and oud.per_groep:
            return van_marges(oud)
    return None
