"""Loopt de TGTG-dump door en schrijft twee tabellen naar data/interim.

    tgtg_dagen.csv       datum | store_id | item_id | item_naam | aantal | omzet_bruto
    tgtg_maanden.csv     maand | store_id | pakketten | omzet_bruto | bruto_per_pakket |
                         commissie_per_stuk | netto_per_pakket | commissie_totaal |
                         uitbetaling | uitbetaling_per_pakket

De eerste is de reeks waar het platform op rekent. De tweede geeft wat een
pakket netto opbrengt, en dat is het enige gemeten getal over de waarde van
een overschot dat in dit hele project bestaat.

Over `netto_per_pakket` versus `uitbetaling_per_pakket`. Het eerste is
berekend: de gemiddelde bruto verkoopprijs uit het verkoopoverzicht min de
commissie per stuk van de factuur. Het tweede komt uit het rekeningoverzicht.
Gebruik het eerste. TGTG betaalt per kwartaal uit (januari, april, juli,
oktober), dus de uitbetaling van een maand slaat niet op de pakketten van die
maand, en dat maakt `uitbetaling_per_pakket` per maand onbruikbaar. Over de
hele reeks moeten de twee wel naar elkaar toe lopen; lopen ze uiteen, dan
klopt er iets niet en is dat een reden om te kijken.

Draaien:
    python3 scripts/tgtg_extract.py
    python3 scripts/tgtg_extract.py --bron "data/raw/TGTG overzicht" --stil
"""
from __future__ import annotations

import argparse
import collections
import csv
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bakkerij.sources.tgtg_parse import (
    TgtgFormaatFout,
    id_uit_pad,
    klopt_met_maand,
    lees_namen,
    maand_uit_pad,
    parse_factuur,
    parse_rekeningoverzicht,
    parse_verkoopoverzicht,
)

RAW = REPO / "data" / "raw"
INTERIM = REPO / "data" / "interim"
CENT = Decimal("0.01")


def pdf_tekst(pad: Path) -> str:
    """pdftotext met -layout: de kolommen blijven staan waar ze staan."""
    r = subprocess.run(
        ["pdftotext", "-layout", str(pad), "-"],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        raise TgtgFormaatFout(f"pdftotext faalde: {r.stderr.strip()[:120]}")
    return r.stdout


def verzamel_namen(bron: Path) -> dict[str, str]:
    namen: dict[str, str] = {}
    for readme in bron.rglob("readme.csv"):
        namen.update(lees_namen(readme))
    return namen


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bron", default=str(RAW / "TGTG overzicht"))
    p.add_argument("--stil", action="store_true", help="alleen de eindtelling")
    args = p.parse_args()

    bron = Path(args.bron)
    if not bron.exists():
        print(f"bron niet gevonden: {bron}", file=sys.stderr)
        return 1

    namen = verzamel_namen(bron)
    INTERIM.mkdir(parents=True, exist_ok=True)

    # Ontdubbelen op documentnummer: de zeven deelexports overlappen.
    gezien: set[str] = set()
    per_dag: dict[tuple, int] = collections.defaultdict(int)
    omzet_dag: dict[tuple, Decimal] = collections.defaultdict(Decimal)
    maanden: dict[tuple, dict] = {}
    fouten: list[str] = []
    dubbel = 0

    for pad in sorted(bron.rglob("*.pdf")):
        soort = pad.name.split("-")[0]
        jm = maand_uit_pad(pad)
        if jm is None:
            fouten.append(f"{pad.name}: geen maandmap in het pad")
            continue
        jaar, maand = jm
        store = id_uit_pad(pad, "storeId") or "?"
        item = id_uit_pad(pad, "itemId") or "?"

        try:
            tekst = pdf_tekst(pad)

            if soort == "Verkoopoverzicht":
                regels = klopt_met_maand(parse_verkoopoverzicht(tekst), jaar, maand)
                for b in regels:
                    if b.documentnummer in gezien:
                        dubbel += 1
                        continue
                    gezien.add(b.documentnummer)
                    per_dag[(b.datum, store, item)] += b.aantal
                    if b.bedrag is not None:
                        omzet_dag[(b.datum, store, item)] += b.bedrag

            elif soort == "Factuur":
                f = parse_factuur(tekst)
                m = maanden.setdefault((jaar, maand, store), {})
                m["pakketten_factuur"] = f.aantal
                m["commissie_per_stuk"] = f.prijs_per_stuk
                m["commissie_totaal"] = f.totaal

            elif soort == "Rekeningoverzicht":
                uit = parse_rekeningoverzicht(tekst)
                if uit is not None:
                    m = maanden.setdefault((jaar, maand, store), {})
                    m["uitbetaling"] = uit

        except TgtgFormaatFout as e:
            fouten.append(f"{jaar}-{maand:02d} {soort}: {e}")
        except Exception as e:  # noqa: BLE001 - bewust breed, we willen door
            fouten.append(f"{jaar}-{maand:02d} {soort}: onverwacht: {type(e).__name__}: {e}")

    # --- wegschrijven -------------------------------------------------------
    dagen_pad = INTERIM / "tgtg_dagen.csv"
    with dagen_pad.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["datum", "store_id", "item_id", "item_naam", "aantal", "omzet_bruto"])
        for (datum, store, item), aantal in sorted(per_dag.items()):
            omzet = omzet_dag.get((datum, store, item))
            w.writerow([datum.isoformat(), store, item, namen.get(f"itemId {item}", ""),
                        aantal, omzet if omzet is not None else ""])

    pakketten_per_maand: dict[tuple, int] = collections.defaultdict(int)
    omzet_per_maand: dict[tuple, Decimal] = collections.defaultdict(Decimal)
    for (datum, store, item), aantal in per_dag.items():
        pakketten_per_maand[(datum.year, datum.month, store)] += aantal
        omzet_per_maand[(datum.year, datum.month, store)] += omzet_dag.get((datum, store, item), Decimal(0))

    maand_pad = INTERIM / "tgtg_maanden.csv"
    with maand_pad.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["maand", "store_id", "pakketten", "omzet_bruto", "bruto_per_pakket",
                    "commissie_per_stuk", "netto_per_pakket", "commissie_totaal",
                    "uitbetaling", "uitbetaling_per_pakket"])
        for sleutel in sorted(set(maanden) | set(pakketten_per_maand)):
            jaar, maand, store = sleutel
            m = maanden.get(sleutel, {})
            pakketten = pakketten_per_maand.get(sleutel, 0)
            omzet = omzet_per_maand.get(sleutel, Decimal(0))
            commissie = m.get("commissie_per_stuk")
            uitbetaling = m.get("uitbetaling")

            bruto_pp = (omzet / pakketten).quantize(CENT) if pakketten and omzet else None
            netto_pp = (bruto_pp - commissie) if (bruto_pp is not None and commissie is not None) else None
            uit_pp = (
                (uitbetaling / pakketten).quantize(CENT)
                if uitbetaling is not None and pakketten else None
            )
            w.writerow([
                f"{jaar}-{maand:02d}", store, pakketten,
                omzet or "", bruto_pp if bruto_pp is not None else "",
                commissie if commissie is not None else "",
                netto_pp if netto_pp is not None else "",
                m.get("commissie_totaal", ""),
                uitbetaling if uitbetaling is not None else "",
                uit_pp if uit_pp is not None else "",
            ])

    # --- rapport (uitsluitend aggregaten) -----------------------------------
    if per_dag:
        datums = [d for d, _, _ in per_dag]
        print(f"dagen met verkoop : {len(set(datums)):>6}")
        print(f"eerste / laatste  : {min(datums)}  ->  {max(datums)}")
        print(f"pakketten totaal  : {sum(per_dag.values()):>6}")
        print(f"dubbels overgeslagen: {dubbel:>4}  (overlappende deelexports)")
    print(f"maanden met cijfers: {len(maanden):>5}")
    print(f"geschreven        : {dagen_pad.relative_to(REPO)}, {maand_pad.relative_to(REPO)}")

    if fouten:
        print(f"\n{len(fouten)} document(en) niet gelezen:")
        for f_ in fouten if not args.stil else fouten[:10]:
            print(f"  - {f_}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
