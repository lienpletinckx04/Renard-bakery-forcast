"""Leest de TGTG-documentendump uit en zet ze om naar tabellen.

Too Good To Go heeft geen publieke API. Wat de bakker kan aanleveren is een
dump van het partnerportaal: per maand per winkel drie pdf's.

    Verkoopoverzicht   een regel per bestelling: datum, bestelnr, docnr, aantal
    Factuur            de commissie die TGTG aanrekent, met aantal en prijs per stuk
    Rekeningoverzicht  het maandsaldo. Negatief bedrag = uitbetaling aan de bakker

Waarom dit meer werk is dan het lijkt: de dump beslaat zeven jaar en bestaat uit
zeven deelexports die elkaar overlappen. Dezelfde maand komt dus meermaals voor.
Ontdubbelen gebeurt op documentnummer, niet op bestand.

Alles hier is een pure functie op tekst. Het inlezen van de pdf zelf staat in
`scripts/tgtg_extract.py`, zodat dit met vaste teksten te testen is en er geen
klantbestand in de tests hoeft te staan.
"""
from __future__ import annotations

import csv
import datetime
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

# Over zeven jaar gebruikt TGTG drie datumnotaties, alle drie met de dag eerst:
#   2024 en later : 1/05/2024      2021 : 1/09/21      2020 en eerder : 01-06-2020
# De maandmap waarin het document staat is de controle, zie `klopt_met_maand`.
_DATUM = re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})")

# Een regel uit het verkoopoverzicht heeft vier of vijf kolommen:
#   datum | bestelnummer | documentnummer | aantal [| verkoopprijs]
# De vijfde staat er niet in elk bouwjaar. Daarom wordt er op kolommen gesplitst
# en niet op één vast patroon: dat overleeft een formaatwissel, en waar het dat
# niet doet, valt het luid om via `TgtgFormaatFout`.
_KOLOMSCHEIDING = re.compile(r"\s{2,}")

# "€ 1.234,56", "-€ 12,34", "9,99 €" (oudere documenten) of kaal "999,99" (facturen
# van vóór 2023). Het euroteken staat dus vóór of achter, of helemaal nergens.
_BEDRAG = re.compile(r"(-?)\s*(?:€\s*)?(\d[\d.]*,\d{2})\s*(?:€)?")


class TgtgFormaatFout(ValueError):
    """De pdf ziet er anders uit dan verwacht.

    Dit is met opzet een fout en geen stille nul: zeven jaar documenten van
    dezelfde leverancier veranderen ergens onderweg van vorm, en een parser die
    dat niet merkt levert een lege maand op die niemand opvalt.
    """


@dataclass(frozen=True)
class Bestelling:
    datum: datetime.date
    bestelnummer: str
    documentnummer: str
    aantal: int
    bedrag: Decimal | None = None
    """Verkoopprijs van de bestelling. Staat niet in elk bouwjaar van het document."""


@dataclass(frozen=True)
class Factuurregel:
    """Wat TGTG aanrekent. `prijs_per_stuk` is de commissie per pakket."""

    aantal: int
    prijs_per_stuk: Decimal
    netto: Decimal | None
    totaal: Decimal | None


def lees_bedrag(tekst: str) -> Decimal | None:
    """'€ 1.234,56' -> Decimal('1234.56'). Negatief blijft negatief."""
    m = _BEDRAG.search(tekst)
    if not m:
        return None
    teken, getal = m.groups()
    waarde = Decimal(getal.replace(".", "").replace(",", "."))
    return -waarde if teken == "-" else waarde


def lees_datum(tekst: str) -> datetime.date | None:
    m = _DATUM.search(tekst)
    if not m:
        return None
    dag, maand, jaar = (int(g) for g in m.groups())
    if jaar < 100:  # '21' -> 2021. TGTG bestaat niet sinds 1921.
        jaar += 2000
    if not (1 <= maand <= 12 and 1 <= dag <= 31):
        return None
    try:
        return datetime.date(jaar, maand, dag)
    except ValueError:  # 31 februari en dergelijke
        return None


def parse_verkoopoverzicht(tekst: str) -> list[Bestelling]:
    """Haalt de bestellingen uit de tekst van een Verkoopoverzicht-pdf."""
    # In de oudste documenten staan de letters van de kopregel uit elkaar
    # getrokken: "A an tal een h ed en". Spaties weghalen vóór de controle.
    if "aantaleenheden" not in tekst.replace(" ", "").lower():
        raise TgtgFormaatFout("kopregel 'Aantal eenheden' niet gevonden")

    bestellingen: list[Bestelling] = []
    for regel in tekst.splitlines():
        kolommen = _KOLOMSCHEIDING.split(regel.strip())
        if len(kolommen) < 4:
            continue
        datum = lees_datum(kolommen[0])
        if datum is None:
            continue
        if not kolommen[3].strip().isdigit():
            continue
        bestellingen.append(
            Bestelling(
                datum=datum,
                bestelnummer=kolommen[1].strip(),
                documentnummer=kolommen[2].strip(),
                aantal=int(kolommen[3].strip()),
                bedrag=lees_bedrag(kolommen[4]) if len(kolommen) > 4 else None,
            )
        )

    if not bestellingen:
        raise TgtgFormaatFout("geen enkele bestelregel herkend")
    return bestellingen


_GELDBEDRAG = re.compile(r"-?\d[\d.]*,\d{2}")


def parse_factuur(tekst: str) -> Factuurregel:
    """Haalt aantal en commissie per stuk uit een Factuur-pdf.

    De artikelregel heet door de jaren heen 'Servicekosten',
    'Reserveringsvergoedingen' of 'Verkochte pakketten'. Op de naam afgaan is
    daarom fragiel. Wat wél constant is: de regel begint met een aantal en
    eindigt op twee bedragen, de prijs per stuk en het totaal.
    """
    regels = tekst.splitlines()
    aantal = None
    prijs = None
    for regel in regels:
        m = re.match(r"^\s*(\d+)\s+\D", regel)
        if not m:
            continue
        bedragen = _GELDBEDRAG.findall(regel)
        if len(bedragen) < 2:
            continue
        aantal = int(m.group(1))
        prijs = lees_bedrag(bedragen[0])
        break
    if aantal is None or prijs is None:
        raise TgtgFormaatFout("artikelregel met aantal en twee bedragen niet gevonden")

    return Factuurregel(
        aantal=aantal,
        prijs_per_stuk=prijs,
        netto=_bedrag_na_label(regels, "Netto bedrag"),
        totaal=_bedrag_na_label(regels, "Totale kosten"),
    )


def parse_rekeningoverzicht(tekst: str) -> Decimal | None:
    """Het maandtotaal. Negatief = wat TGTG aan de bakker uitbetaalt.

    Geeft de uitbetaling terug als positief getal, of None als de regel
    ontbreekt. Positief saldo (bakker is nog iets verschuldigd) geeft 0.
    """
    regels = tekst.splitlines()
    totaal = _bedrag_na_label(regels, "Totaal (negatief getal")
    if totaal is None:
        return None
    return -totaal if totaal < 0 else Decimal("0.00")


def _bedrag_na_label(regels: list[str], label: str) -> Decimal | None:
    """Bedrag op de labelregel zelf, of op een van de twee regels erna.

    Met -layout staat het bedrag soms op dezelfde regel als het label en soms
    net erna, afhankelijk van de kolombreedte in dat bouwjaar van het document.
    """
    for i, regel in enumerate(regels):
        if label in regel:
            for kandidaat in regels[i : i + 3]:
                bedrag = lees_bedrag(kandidaat)
                if bedrag is not None:
                    return bedrag
    return None


def klopt_met_maand(bestellingen: list[Bestelling], jaar: int, maand: int) -> list[Bestelling]:
    """Controleert de datums tegen de maandmap waarin het document stond.

    Dit vangt het enige echt gevaarlijke leesfout af: dag en maand omgewisseld.
    05/03 en 03/05 zijn allebei geldige datums en geen enkele parser ziet het
    verschil, behalve door te vergelijken met de map waarin het bestand staat.
    """
    fout = [b for b in bestellingen if (b.datum.year, b.datum.month) != (jaar, maand)]
    if fout:
        voorbeeld = fout[0].datum.isoformat()
        raise TgtgFormaatFout(
            f"{len(fout)} van {len(bestellingen)} datums vallen buiten {jaar}-{maand:02d} "
            f"(eerste: {voorbeeld}). Mogelijk dag/maand omgewisseld."
        )
    return bestellingen


def lees_namen(readme: Path) -> dict[str, str]:
    """readme.csv koppelt itemId en storeId aan een naam."""
    namen: dict[str, str] = {}
    with readme.open(encoding="utf-8-sig", newline="") as f:
        for rij in csv.DictReader(f):
            if rij.get("id") and rij.get("name"):
                namen[rij["id"].strip()] = rij["name"].strip()
    return namen


def maand_uit_pad(pad: Path) -> tuple[int, int] | None:
    """Vindt de YYYY-MM-map in het pad van een document."""
    for deel in pad.parts:
        m = re.fullmatch(r"(\d{4})-(\d{2})", deel)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def id_uit_pad(pad: Path, soort: str) -> str | None:
    """Vindt 'itemId 8191' of 'storeId 8113' in het pad en geeft het nummer."""
    for deel in pad.parts:
        m = re.fullmatch(rf"{soort}\s+(\d+)", deel)
        if m:
            return m.group(1)
    return None
