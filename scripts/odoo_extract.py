"""Haalt de verkoophistoriek uit Odoo en schrijft ze naar het canonieke datamodel.

Aggregeert AAN DE BRON: product x datum x kassa. Er wordt geen enkel
persoonsgegeven opgehaald. Klantvelden (partner_id, customer_note, naam,
adres) worden bewust nooit bevraagd, niet gefilterd achteraf. Daardoor is
er geen AVG-vraag te beantwoorden in plaats van een AVG-vraag die goed
beantwoord is.

Output volgt CLAUDE.md:
    verkopen: datum | filiaal_id | product_id | kanaal | aantal | omzet_excl_btw

Draaien:
    python3 scripts/odoo_extract.py                 # alles
    python3 scripts/odoo_extract.py --vanaf 2025-01-01
"""
import argparse
import csv
import datetime
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from bakkerij.sources.odoo_client import Odoo, naam
from bakkerij.tijd import BRUSSEL, brusselse_dag

RAW = REPO / "data" / "raw"

# Odoo geeft datumlabels terug in de serverlocale. Nederlands hier.
MAAND = {"jan": 1, "feb": 2, "mrt": 3, "apr": 4, "mei": 5, "jun": 6,
         "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12}

# Dezelfde afronding als bakkerij/db/laden.py: half-up, want de cijfers op
# dit platform worden nagerekend door een boekhouder, niet door een
# statisticus. round() zou bankiersafronding zijn.
CENT = Decimal("0.01")
MILLI = Decimal("0.001")


def dagsleutel(waarde):
    """'19 sep. 2024' of '2024-09-19 21:14:03' (UTC) -> Belgische date.

    De ISO-vorm is een UTC-moment (zo levert Odoo ze) en gaat via
    bakkerij.tijd naar de Brusselse dag. Tot 18 augustus 2026 werd hier de
    UTC-datum afgeknipt, waardoor de kernfeiten in de zomer een andere
    kalender volgden dan de bonnen- en urenextracten, die wél converteerden.
    De labelvorm is al een dag en heeft geen conversie nodig.
    """
    s = str(waarde)
    if "-" in s[:10]:
        return brusselse_dag(s)
    d, m, y = s.replace(".", "").split()
    return datetime.date(int(y), MAAND[m[:3].lower()], int(d))


def extract_pos(o, vanaf):
    """Kassaverkopen. Kanaal is per definitie 'winkel': Odoo kent hier geen ander."""
    domein = [("date_order", ">=", f"{vanaf} 00:00:00")] if vanaf else []

    # Dimensies apart ophalen: drie kassa's en een paar honderd producten. Daarna
    # kunnen alle grote reads met load='' draaien, zonder display_name-berekening.
    kassa_naam = {c["id"]: c["name"] for c in o.search_read("pos.config", [], ["name"])}
    product_naam = {p["id"]: p["name"] for p in o.paginate("product.product", [], ["name"])}

    print("  orders inlezen...")
    orders = {}
    for r in o.paginate("pos.order", domein, ["date_order", "config_id"], load=""):
        orders[r["id"]] = (dagsleutel(r["date_order"]), kassa_naam.get(r["config_id"], "?"))
    print(f"  {len(orders):,} orders")

    if not orders:
        return []

    # Filteren via een puntpad op de order, NIET met een lijst van 678.000 id's:
    # dat domein zou bij elke bladzijde opnieuw over de lijn gaan.
    lijn_domein = [("order_id.date_order", ">=", f"{vanaf} 00:00:00")] if vanaf else []

    print("  bonregels inlezen...")
    agg = defaultdict(lambda: [0.0, 0.0])
    n = 0
    for line in o.paginate("pos.order.line", lijn_domein,
                           ["order_id", "product_id", "qty", "price_subtotal"], load=""):
        n += 1
        ref = orders.get(line["order_id"])
        if not ref or not line.get("product_id"):
            continue
        datum, kassa = ref
        pid = line["product_id"]
        sleutel = (datum, kassa, pid, product_naam.get(pid, ""), "winkel")
        agg[sleutel][0] += line.get("qty") or 0
        agg[sleutel][1] += line.get("price_subtotal") or 0
        if n % 100000 == 0:
            print(f"    {n:,} regels", flush=True)
    print(f"  {n:,} bonregels -> {len(agg):,} geaggregeerde rijen")
    return sorted(agg.items())


def extract_producten(o):
    """Productdimensie. Geen persoonsgegevens, wel de sleutel tot marges en groepen."""
    rijen = []
    for p in o.paginate("product.product", [], ["name", "categ_id", "list_price", "standard_price", "active"]):
        rijen.append({
            "product_id": p["id"],
            "naam": p["name"],
            "categorie": naam(p["categ_id"]),
            "verkoopprijs": p.get("list_price") or 0,
            "kostprijs": p.get("standard_price") or 0,
            "actief": p.get("active", True),
        })
    return rijen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vanaf", default=None,
                    help="YYYY-MM-DD. Tip: 2025-01-01, want sep-dec 2024 is "
                         "implementatie-ruis (11 bonnen). Zie docs/data-audit.md blok C.")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    o = Odoo()
    print(f"Odoo {o.version} | db={o.db}\n")
    vandaag = datetime.datetime.now(BRUSSEL).date().isoformat()

    print("VERKOPEN")
    rijen = extract_pos(o, args.vanaf)
    if not rijen:
        # Nul orders is geen lege dag maar een kapotte bron: verkeerde
        # --vanaf, een ingetrokken leesrecht, een lege preprod. Zonder deze
        # exit pakte canoniek_bouw stilzwijgend het extract van gisteren en
        # meldde de ketting 'goed' op oude data.
        print("GEBLOKKEERD -- het extract leverde nul orders op; "
              "er is niets geschreven.", file=sys.stderr)
        return 1
    datums = [k[0] for k, _ in rijen]
    bestand = RAW / f"{vandaag}_odoo_verkopen_{min(datums)}_{max(datums)}.csv"
    with open(bestand, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["datum", "filiaal_id", "product_id", "product_naam",
                    "kanaal", "aantal", "omzet_excl_btw"])
        for (datum, kassa, pid, pnaam, kanaal), (qty, omzet) in rijen:
            w.writerow([datum, kassa, pid, pnaam, kanaal,
                        Decimal(str(qty)).quantize(MILLI, rounding=ROUND_HALF_UP),
                        Decimal(str(omzet)).quantize(CENT, rounding=ROUND_HALF_UP)])
    print(f"  -> {bestand.name}")

    print("\nPRODUCTEN")
    prods = extract_producten(o)
    bestand = RAW / f"{vandaag}_odoo_producten.csv"
    with open(bestand, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(prods[0]))
        w.writeheader()
        w.writerows(prods)
    met_kost = sum(1 for p in prods if p["kostprijs"] > 0)
    print(f"  {len(prods)} producten, {met_kost} met kostprijs ({100*met_kost/len(prods):.0f}%)")
    print(f"  -> {bestand.name}")

    print("\nKlaar. data/ is gitignored. Controleer met: make check-data")
    print("LET OP: filiaal_id bevat de KASSA, niet noodzakelijk de vestiging.")
    print("Zie docs/aannames.md A11 - dit moet bevestigd worden voor het datamodel vastligt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
