"""Inventariseert de Deliveroo-downloads en zegt wat er nog ontbreekt.

De parser is nog niet gebouwd (zie `docs/plan-deliveroo-parser.md` voor de
vervolglijst en `docs/beslissingen.md`, 25 aug 2026, voor het waarom). Dit script bestaat nu al om twee redenen,
en beide zijn de wachttijd waard:

1. HET LEGT DE MAPPENCONVENTIE VAST IN CODE. Zonder dat is de conventie een
   regel in een document, en documenten worden niet gelezen door wie om
   middernacht een map aanmaakt. Wat dit script niet herkent, wordt straks ook
   niet gelezen -- en dat weet je dan nú.

2. HET MEET DE DEKKING VAN DE HISTORIEK. Twaalf maanden komen in blokken van
   maximaal negentig dagen, dus minstens vier downloads. Een blok dat iemand
   vergeet is een gat dat niemand ziet: de reeks loopt gewoon door, met een
   stille leegte erin. En dit is het enige gat in dit project dat niet meer te
   dichten is -- het venster in Partner Hub schuift elke dag op, en wat eruit
   valt is permanent weg.

Wat het NIET doet: iets naar data/interim schrijven. Een leeg
`deliveroo_dagen.csv` zou de canoniekbouw laten denken dat het kanaal bestaat
en op nul staat, terwijl het kanaal hoort te melden dat het onbeschikbaar is
met reden (harde regel 8). Zolang de parser er niet is, is niets schrijven het
juiste antwoord.

WAAR DE BESTANDEN HEEN MOETEN. Eén submap per download uit Partner Hub, en de
mapnaam draagt het bereik dat je in het portaal gekozen hebt:

    data/raw/Deliveroo/2025-08-25_2025-11-22/items-sold.csv
    data/raw/Deliveroo/2025-08-25_2025-11-22/orders.csv

De bestandsnaam die het portaal meegeeft mag blijven staan, zolang `items` of
`orders` erin voorkomt. Het bereik in de mapnaam is geen administratie maar de
controle op dag/maand-omwisseling (zie `klopt_met_bereik`), en zonder die map
wordt een export niet gelezen.

DIT SCRIPT FAALT NOOIT OP DE TOESTAND VAN DE DATA. Een ontbrekende bron levert
exitcode 0 met een melding, geen fout. Dat is dezelfde regel als
`BEKEND_AFWEZIG` in `bakkerij/kwaliteit.py`: van een bron waarvan we wéten dat
ze er nog niet is, is "ontbreekt" geen alarm maar een toestand, en een alarm
dat permanent afgaat is geen alarm. Een niet-nul exitcode zou dit doel bovendien
onbruikbaar maken in elke keten waar het ooit in komt te staan.

Draaien:
    python3 scripts/deliveroo_extract.py
    python3 scripts/deliveroo_extract.py --bron data/raw/Deliveroo
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bakkerij.sources.deliveroo_parse import (
    BRONMAP,
    NOG_NIET_GEBOUWD,
    DeliverooFormaatFout,
    bereik_uit_pad,
    gaten_in_dekking,
)

RAW = REPO / "data" / "raw"

#: Twaalf maanden is wat Partner Hub teruggeeft. Minder dekking dan dit is
#: geen fout maar wel een melding: het verschil is niet meer op te halen.
VENSTER_DAGEN = 365


def soort(naam: str) -> str | None:
    """Welk rapport dit is, aan de bestandsnaam. Niet aan de kolommen: die
    kennen we nog niet, en dit script leest de inhoud bewust niet."""
    klein = naam.lower()
    if "item" in klein:
        return "items-sold"
    if "order" in klein:
        return "orders"
    return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bron", default=str(RAW / BRONMAP))
    args = p.parse_args()

    bron = Path(args.bron)
    print("=" * 64)
    print("DELIVEROO -- inventaris van de downloads")
    print("=" * 64)

    if not bron.exists():
        print(f"bron bestaat niet: {bron.relative_to(REPO)}")
        print()
        print("Nog niets aangeleverd. Wat er moet gebeuren, in deze volgorde:")
        print("  1. Partner Hub -> Reports, één bereik van drie dagen, beide")
        print("     rapporttypes. Dat is de probe: hij beslist of Items Sold")
        print("     per dag uitsplitst en of de twee een order-sleutel delen.")
        print("  2. Daarna de volle twaalf maanden, vier blokken van 90 dagen.")
        print(f"  3. Per download een map: {bron.relative_to(REPO)}/"
              "JJJJ-MM-DD_JJJJ-MM-DD/")
        return 0

    bereiken: list[tuple[datetime.date, datetime.date]] = []
    losse: list[Path] = []
    onbekend: list[Path] = []
    per_bereik: dict[tuple, set[str]] = {}

    for pad in sorted(bron.rglob("*.csv")):
        try:
            bereik = bereik_uit_pad(pad)
        except DeliverooFormaatFout as fout:
            print(f"  MAPNAAM DEUGT NIET: {pad.name} -- {fout}")
            continue
        if bereik is None:
            losse.append(pad)
            continue
        s = soort(pad.name)
        if s is None:
            onbekend.append(pad)
            continue
        if bereik not in per_bereik:
            per_bereik[bereik] = set()
            bereiken.append(bereik)
        per_bereik[bereik].add(s)

    if not per_bereik and not losse:
        print(f"map bestaat, maar er staat geen enkele CSV in: "
              f"{bron.relative_to(REPO)}")
        return 0

    print(f"downloads gevonden: {len(per_bereik)}")
    for bereik in sorted(per_bereik):
        van, tot = bereik
        types = per_bereik[bereik]
        dagen = (tot - van).days + 1
        mist = {"items-sold", "orders"} - types
        staat = "compleet" if not mist else f"MIST: {', '.join(sorted(mist))}"
        print(f"  {van} .. {tot}  ({dagen:>3} dagen)  {staat}")

    if losse:
        print(f"\n{len(losse)} bestand(en) zonder bereikmap -- worden NIET "
              "gelezen:")
        for pad in losse[:10]:
            print(f"  - {pad.relative_to(bron)}")
        print("  Zet elke download in een map JJJJ-MM-DD_JJJJ-MM-DD.")

    if onbekend:
        print(f"\n{len(onbekend)} bestand(en) waarvan het rapporttype niet uit "
              "de naam blijkt:")
        for pad in onbekend[:10]:
            print(f"  - {pad.relative_to(bron)}")
        print("  Verwacht 'items' of 'orders' in de bestandsnaam.")

    if bereiken:
        gaten = gaten_in_dekking(bereiken)
        vroegste = min(v for v, _ in bereiken)
        laatste = max(t for _, t in bereiken)
        gedekt = (laatste - vroegste).days + 1
        print(f"\ndekking: {vroegste} .. {laatste} ({gedekt} dagen)")
        if gaten:
            print(f"  {len(gaten)} GAT(EN) in de reeks:")
            for van, tot in gaten:
                print(f"    {van} .. {tot}  ({(tot - van).days + 1} dagen)")
            print("  Deze dagen zitten in geen enkele download. Haal ze op "
                  "zolang ze nog binnen het venster van twaalf maanden vallen.")
        if gedekt < VENSTER_DAGEN:
            print(f"  Dekking is {VENSTER_DAGEN - gedekt} dagen korter dan de "
                  "twaalf maanden die Partner Hub teruggeeft. Wat daarbuiten "
                  "valt, is niet meer op te halen.")

    print()
    print(NOG_NIET_GEBOUWD)
    print()
    print("Er is niets naar data/interim geschreven, en dat is opzet: een leeg "
          "kanaal\nop nul is erger dan een kanaal dat zegt dat het "
          "onbeschikbaar is (harde regel 8).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
