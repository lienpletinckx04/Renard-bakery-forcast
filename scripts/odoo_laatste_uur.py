"""Haalt het eerste en laatste verkoopuur per product per dag uit Odoo (O11).

Dit is de meting achter de censureringsvraag (O8, open-punten.md §5): een
product dat structureel uren vóór sluitingstijd zijn laatste bon heeft, was
uitverkocht — en dan meet de kassa de rek, niet de vraag. Zonder dit veld is
die vraag niet te beantwoorden; deliverables.md A2 eist het daarom.

Aggregeert AAN DE BRON, zoals odoo_extract.py: per product x datum blijven
alleen het eerste uur, het laatste uur en het aantal bonnen over. Geen
partner_id, geen klantnaam, geen bonnotitie — die velden worden nooit
bevraagd.

Tijdzone: Odoo slaat date_order op in UTC. Voor een dagsleutel maakt dat
zelden uit (een bakkerij verkoopt niet rond middernacht), voor een UUR is de
conversie naar Europe/Brussels het verschil tussen 15u en 17u. Hier wordt dus
wél geconverteerd, anders meet de censureringsanalyse een winkel die twee uur
te vroeg dichtgaat.

Draaien:
    python3 scripts/odoo_laatste_uur.py --vanaf 2025-01-02
"""
import argparse
import csv
import datetime
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from bakkerij.sources.odoo_client import Odoo

# Sinds 18 aug 2026 uit bakkerij.tijd: dit script herbouwde de conversie met
# de hand, zonder het fromisoformat-vangnet van de module.
from bakkerij.tijd import BRUSSEL, brussels_moment

RAW = REPO / "data" / "raw"


def extract_uren(o: Odoo, vanaf: str | None):
    """Per (datum, product): eerste uur, laatste uur, aantal bonnen."""
    domein = [("date_order", ">=", f"{vanaf} 00:00:00")] if vanaf else []

    print("  orders inlezen...")
    orders: dict[int, tuple[datetime.date, int]] = {}
    for r in o.paginate("pos.order", domein, ["date_order"], load=""):
        m = brussels_moment(r["date_order"])
        orders[r["id"]] = (m.date(), m.hour)
    print(f"  {len(orders):,} orders")
    if not orders:
        return []

    lijn_domein = [("order_id.date_order", ">=", f"{vanaf} 00:00:00")] if vanaf else []

    print("  bonregels inlezen...")
    # sleutel -> [eerste_uur, laatste_uur, set van order-id's]
    agg: dict[tuple, list] = defaultdict(lambda: [24, -1, set()])
    n = 0
    for line in o.paginate("pos.order.line", lijn_domein, ["order_id", "product_id"], load=""):
        n += 1
        ref = orders.get(line["order_id"])
        if not ref or not line.get("product_id"):
            continue
        datum, uur = ref
        cel = agg[(datum, line["product_id"])]
        cel[0] = min(cel[0], uur)
        cel[1] = max(cel[1], uur)
        cel[2].add(line["order_id"])
        if n % 100000 == 0:
            print(f"    {n:,} regels", flush=True)
    print(f"  {n:,} bonregels -> {len(agg):,} product-dagen")
    return sorted((k, (v[0], v[1], len(v[2]))) for k, v in agg.items())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vanaf", default="2025-01-02",
                    help="YYYY-MM-DD. Standaard 2025-01-02: het werkextract begint 2025-01-01, maar dat is nieuwjaarsdag (gesloten) en telt geen uren.")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    o = Odoo()
    print(f"Odoo {o.version} | db={o.db}\n\nLAATSTE VERKOOPUUR (O11)")
    rijen = extract_uren(o, args.vanaf)
    if not rijen:
        print("  niets gevonden")
        return

    vandaag = datetime.datetime.now(BRUSSEL).date().isoformat()
    datums = [k[0] for k, _ in rijen]
    bestand = RAW / f"{vandaag}_odoo_laatste_uur_{min(datums)}_{max(datums)}.csv"
    with open(bestand, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["datum", "product_id", "eerste_uur", "laatste_uur", "bonnen"])
        for (datum, pid), (eerste, laatste, bonnen) in rijen:
            w.writerow([datum, pid, eerste, laatste, bonnen])
    print(f"  -> {bestand.name}")
    print("\nKlaar. data/ is gitignored. Dit bestand bevat alleen aggregaten per product per dag.")


if __name__ == "__main__":
    raise SystemExit(main())
