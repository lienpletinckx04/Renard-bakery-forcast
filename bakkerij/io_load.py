"""Schema-agnostisch inladen van klantexports.

We weten op voorhand niet hoe de Odoo-export eruitziet. Deze module laadt wat er
komt en raadt welke kolom welke rol speelt, zodat de audit kan draaien vóór er
ook maar iets over het schema afgesproken is.

Raden is expliciet: elke gok komt met een score en wordt getoond, nooit stil
toegepast. Een verkeerd geraden kolom die stil doorwerkt, is duurder dan een
kolom die je zelf moet aanwijzen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# Rolnaam -> patronen die in een kolomnaam kunnen voorkomen (NL, FR, EN, Odoo).
ROLPATRONEN: dict[str, list[str]] = {
    "datum": [
        r"date", r"datum", r"dag", r"day", r"invoice_date", r"order_date",
        r"date_order", r"periode", r"tijdstip", r"timestamp",
    ],
    "filiaal": [
        r"filiaal", r"vestiging", r"winkel", r"shop", r"store", r"branch",
        r"warehouse", r"magasin", r"pos_config", r"point_of_sale", r"locatie",
        r"location", r"site",
    ],
    "product": [
        r"product", r"artikel", r"article", r"item", r"sku", r"referentie",
        r"reference", r"default_code", r"omschrijving", r"description",
    ],
    "aantal": [
        r"aantal", r"qty", r"quantity", r"hoeveelheid", r"stuks", r"units",
        r"product_uom_qty", r"qte",
    ],
    "omzet": [
        r"omzet", r"bedrag", r"amount", r"total", r"revenue", r"price_subtotal",
        r"prijs", r"price", r"turnover", r"montant",
    ],
    "kanaal": [
        r"kanaal", r"channel", r"verkoopkanaal", r"sales_channel", r"bron",
        r"source", r"platform", r"type_verkoop",
    ],
}

KANAAL_HINTS = {
    "winkel": [r"winkel", r"shop", r"pos", r"toonbank", r"store", r"kassa"],
    "deliveroo": [r"deliveroo", r"delivery", r"levering"],
}


@dataclass
class Kolomgok:
    rol: str
    kolom: str | None
    score: float
    kandidaten: list[tuple[str, float]] = field(default_factory=list)

    @property
    def zeker(self) -> bool:
        """Eén duidelijke winnaar met voldoende voorsprong."""
        if self.kolom is None or self.score < 0.5:
            return False
        if len(self.kandidaten) < 2:
            return True
        return self.kandidaten[0][1] - self.kandidaten[1][1] >= 0.25


def laad(pad: str | Path, blad: str | int | None = None) -> pd.DataFrame:
    """Laad csv, tsv, xlsx of parquet. Alles als string, we casten pas bewust.

    Alles als string inlezen is bewust: pandas raadt anders types en maakt van
    een artikelcode `00123` het getal 123, en van een Europese `1.234,50` iets
    onherkenbaars. Liever traag en juist.
    """
    pad = Path(pad)
    if not pad.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {pad}")

    suffix = pad.suffix.lower()
    if suffix in {".csv", ".tsv", ".txt"}:
        sep = "\t" if suffix == ".tsv" else None
        return pd.read_csv(
            pad, sep=sep, engine="python", dtype=str,
            keep_default_na=False, na_values=[""],
        )
    if suffix == ".xls":
        # pandas heeft voor het oude .xls-formaat `xlrd` nodig en dat staat
        # bewust niet in requirements: de ImportError uit pandas' binnenwerk
        # zei niets. Eén export opnieuw opslaan als .xlsx is sneller dan een
        # dependency dragen voor een formaat dat sinds 2007 vervangen is.
        raise ValueError(
            f"{pad.name}: het oude .xls-formaat wordt niet gelezen; "
            "sla de export op als .xlsx en probeer opnieuw."
        )
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(pad, sheet_name=blad or 0, dtype=str)
    if suffix == ".parquet":
        return pd.read_parquet(pad)
    raise ValueError(f"Onbekend formaat: {suffix}")


def _score_kolom(kolomnaam: str, patronen: list[str]) -> float:
    naam = kolomnaam.lower().strip()
    genormaliseerd = re.sub(r"[^a-z0-9]+", "_", naam)
    beste = 0.0
    for patroon in patronen:
        if re.fullmatch(patroon, genormaliseerd):
            beste = max(beste, 1.0)
        elif re.search(patroon, genormaliseerd):
            beste = max(beste, 0.7)
    return beste


def raad_kolommen(df: pd.DataFrame) -> dict[str, Kolomgok]:
    """Raad per rol welke kolom hem invult. Toont altijd de alternatieven."""
    gokken: dict[str, Kolomgok] = {}
    for rol, patronen in ROLPATRONEN.items():
        scores = [(k, _score_kolom(str(k), patronen)) for k in df.columns]
        scores = sorted([s for s in scores if s[1] > 0], key=lambda x: -x[1])
        if scores:
            gokken[rol] = Kolomgok(rol, scores[0][0], scores[0][1], scores[:4])
        else:
            gokken[rol] = Kolomgok(rol, None, 0.0, [])
    return gokken


def parse_datums(reeks: pd.Series) -> pd.Series:
    """Parseer datums, dagen-eerst (Europees). Onparseerbaar wordt NaT."""
    return pd.to_datetime(reeks, errors="coerce", dayfirst=True, format="mixed")


def parse_getallen(reeks: pd.Series) -> pd.Series:
    """Parseer getallen met Europese notatie.

    `1.234,50` en `1234.50` moeten allebei 1234.5 opleveren. De regel: als er
    een komma in zit, is de komma het decimaalteken en zijn punten duizendtallen.

    Zonder komma is een punt meestal het decimaalteken -- behalve als het hele
    getal het duizendtalpatroon volgt (groepjes van exact drie cijfers achter
    elke punt: `1.234`, `1.234.567`). Een Europese export die `1.234` schrijft,
    bedoelt twaalfhonderdvierendertig; dat als 1,234 lezen scheelt stilletjes
    een factor duizend. `1234.50` matcht het patroon niet (vier cijfers vóór de
    punt, twee erachter) en houdt zijn punt als decimaalteken.
    """
    schoon = (
        reeks.astype(str)
        .str.replace(r"[^\d,.\-]", "", regex=True)
        .str.strip()
    )
    heeft_komma = schoon.str.contains(",", na=False)
    schoon = schoon.where(
        ~heeft_komma,
        schoon.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
    )
    duizendtal = ~heeft_komma & schoon.str.fullmatch(r"-?\d{1,3}(\.\d{3})+", na=False)
    schoon = schoon.where(
        ~duizendtal,
        schoon.str.replace(".", "", regex=False),
    )
    return pd.to_numeric(schoon, errors="coerce")


def raad_kanaal(waarde: str) -> str:
    """Map een vrije kanaalwaarde naar het canonieke kanaal."""
    tekst = str(waarde).lower()
    for kanaal, patronen in KANAAL_HINTS.items():
        if any(re.search(p, tekst) for p in patronen):
            return kanaal
    return "overig"
