"""Haalt het aantal bonnen per dag per kassa uit Odoo.

De traffic-as van het overzichtsscherm: omzet = bonnen x gemiddeld bonbedrag,
en die twee bewegen om verschillende redenen. Minder klanten is een ander
probleem dan een kleinere mand.

WAAROM DIT NIET UIT DE PRODUCT-DAGTELLING KAN. Het aantal bonnen per dag is
niet de som van `bonnen` per product-dag uit odoo_laatste_uur.py: een bon met
drie producten telt daar drie keer. De dagtelling moet als eigen distinct-
count uit de bron komen, anders wordt het bonbedrag structureel te laag en
beweegt de "traffic" mee met de assortimentsbreedte per bon in plaats van met
klanten.

Aggregeert aan de bron: alleen datum x kassa x aantal. Geen bedragen op
bonniveau, geen klantvelden — die worden nooit bevraagd.

Draaien:
    python3 scripts/odoo_bonnen.py --vanaf 2025-01-02
"""
import argparse
import csv
import datetime
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from bakkerij.sources.odoo_client import Odoo
from bakkerij.tijd import BRUSSEL, brusselse_dag

RAW = REPO / "data" / "raw"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vanaf", default="2025-01-02",
                    help="YYYY-MM-DD. Standaard 2025-01-02: het werkextract "
                         "begint 2025-01-01, maar dat is nieuwjaarsdag "
                         "(gesloten) en telt geen bonnen.")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    o = Odoo()
    print(f"Odoo {o.version} | db={o.db}\n\nBONNEN PER DAG")

    kassa_naam = {c["id"]: c["name"] for c in o.search_read("pos.config", [], ["name"])}
    domein = [("date_order", ">=", f"{args.vanaf} 00:00:00")]

    telling: Counter = Counter()
    n = 0
    for r in o.paginate("pos.order", domein, ["date_order", "config_id"], load=""):
        n += 1
        # Odoo slaat date_order op in UTC; de dag hoort bij Brussel.
        # Sinds 18 aug 2026 via bakkerij.tijd — de conversie bestaat één keer.
        datum = brusselse_dag(r["date_order"])
        telling[(datum, kassa_naam.get(r["config_id"], "?"))] += 1
    print(f"  {n:,} orders -> {len(telling):,} dag-kassa-rijen")

    if not telling:
        print("  niets gevonden")
        return

    vandaag = datetime.datetime.now(BRUSSEL).date().isoformat()
    datums = [d for d, _ in telling]
    bestand = RAW / f"{vandaag}_odoo_bonnen_{min(datums)}_{max(datums)}.csv"
    with open(bestand, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["datum", "filiaal_id", "bonnen"])
        for (datum, kassa), aantal in sorted(telling.items()):
            w.writerow([datum, kassa, aantal])
    print(f"  -> {bestand.name}")
    print("\nKlaar. data/ is gitignored. Dit bestand bevat alleen dagtellingen.")


if __name__ == "__main__":
    raise SystemExit(main())
