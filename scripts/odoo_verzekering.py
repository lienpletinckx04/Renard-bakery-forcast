"""Het verzekeringsextract: de volledige Odoo-verkoophistoriek, op bonregelniveau.

Dit is geen werkbestand maar een archief. Als de API-toegang wegvalt — sleutel
ingetrokken, preprod herbouwd, licentie verlopen — dan is met dit extract niets
verloren: elke bon, elke regel, elke betaling, plus de dimensietabellen om ze
te lezen. Daarom GEEN aggregatie en geen filter op de datum.

Wat er bewust NIET in zit: persoonsgegevens. partner_id, customer_note, namen
en adressen worden nooit bevraagd — niet opgehaald en weggegooid, maar nooit
opgehaald. Zie scripts/odoo_extract.py voor dezelfde redenering.

Output: één parquet-bestand per model in data/raw/verzekering/<datum>/.
Parquet omdat het kolomtypes vastlegt en een derde van de CSV-grootte kost;
zstd-compressie omdat dit archief is, geen werkverkeer.

Draaien:
    .venv/bin/python scripts/odoo_verzekering.py     # of: make verzekering
"""
import datetime
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from bakkerij.sources.odoo_client import Odoo

DOEL = REPO / "data" / "raw" / "verzekering"

# De projecttijdzone, niet die van de machine: de mapnaam van het archief moet
# de Belgische dag zijn waarop het getrokken is. Zie CLAUDE.md.
# Sinds 18 aug 2026 uit bakkerij.tijd: de zone bestaat één keer.
from bakkerij.tijd import BRUSSEL as TIJDZONE

# Per model: de velden die we bewaren. Geen klantvelden, nergens.
# Bij load='' komen many2one-velden terug als kaal id (of False bij leeg).
MODELLEN = [
    # (model, velden, extra domein)
    ("pos.order",
     ["date_order", "config_id", "amount_total", "amount_tax",
      "amount_paid", "state", "session_id"], []),
    ("pos.order.line",
     ["order_id", "product_id", "qty", "price_unit", "discount",
      "price_subtotal", "price_subtotal_incl"], []),
    ("pos.payment",
     ["pos_order_id", "amount", "payment_method_id", "payment_date"], []),
    # Dimensies. Let op: een leeg domein verbergt gearchiveerde records,
    # dus 'active in [True, False]' om ook geschrapte producten te bewaren.
    ("product.product",
     ["name", "categ_id", "list_price", "standard_price", "active", "barcode"],
     [("active", "in", [True, False])]),
    ("product.category", ["name", "parent_id"], []),
    ("pos.config", ["name"], []),
    ("pos.payment.method", ["name"], []),
]


def schoon(waarde):
    """Odoo geeft False terug voor lege velden, ongeacht het type."""
    return None if waarde is False else waarde


def extract_model(o, model, velden, domein, map_):
    print(f"{model}")
    kolommen = {"id": []}
    for v in velden:
        kolommen[v] = []
    n = 0
    for rij in o.paginate(model, domein, velden, load=""):
        n += 1
        kolommen["id"].append(rij["id"])
        for v in velden:
            kolommen[v].append(schoon(rij.get(v)))
        if n % 100000 == 0:
            print(f"    {n:,} rijen", flush=True)

    tabel = pa.table(kolommen)
    bestand = map_ / f"{model.replace('.', '_')}.parquet"
    pq.write_table(tabel, bestand, compression="zstd")
    mb = bestand.stat().st_size / 1e6
    print(f"    {n:,} rijen -> {bestand.name} ({mb:.1f} MB)")
    return n


def main():
    o = Odoo()
    print(f"Odoo {o.version} | db={o.db}")
    map_ = DOEL / datetime.datetime.now(TIJDZONE).date().isoformat()
    map_.mkdir(parents=True, exist_ok=True)
    print(f"doel: {map_.relative_to(REPO)}\n")

    totalen = {}
    for model, velden, domein in MODELLEN:
        totalen[model] = extract_model(o, model, velden, domein, map_)

    print("\nKlaar. data/ is gitignored; controleer met: make check-data")
    for model, n in totalen.items():
        print(f"  {model:<22} {n:>12,}")


if __name__ == "__main__":
    main()
