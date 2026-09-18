"""Dag-1 data-audit tegen Odoo. Beantwoordt docs/data-audit.md blok A t/m G.

Leest alleen aggregaten. Er komt geen enkele klantrij op schijf of in een
LLM-context: enkel tellingen, datumbereiken en groepsstatistiek.

Draaien:  make odoo-audit
"""
import sys
import xmlrpc.client
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bakkerij.sources.odoo_client import Odoo, naam

# De projecttijdzone. Odoo geeft datumlabels zonder zone terug; die horen bij de
# Belgische dag, niet bij de tijdzone van de machine waarop dit script draait.
# Sinds 18 aug 2026 uit bakkerij.tijd: de zone bestaat één keer.
from bakkerij.tijd import BRUSSEL as TIJDZONE

# Wat er bij een Odoo-aanroep mis kan gaan buiten onze schuld: de server weigert
# (Fault, dus geen rechten of een onbekend model of veld), de HTTP-laag hapert
# (ProtocolError), of de verbinding valt weg (OSError). Alles daarbuiten is een
# fout in dit script zelf en moet doorslaan in plaats van als "niet toegankelijk"
# op het scherm te belanden: een audit die zijn eigen bugs wegslikt, liegt.
ODOO_FOUT = (xmlrpc.client.Fault, xmlrpc.client.ProtocolError, OSError)


def kop(titel):
    print(f"\n{'=' * 72}\n{titel}\n{'=' * 72}")


def veilig(fn, fallback="niet toegankelijk"):
    """Voert een Odoo-aanroep uit en geeft bij een serverweigering een leesbare
    reden terug in plaats van de waarde. Vangt uitsluitend fouten van de
    koppeling; een programmeerfout slaat door."""
    try:
        return fn()
    except ODOO_FOUT as exc:
        return f"{fallback} ({str(exc)[:70]})"


def datum_uit_label(label):
    """Een read_group-daglabel van Odoo naar een `date`, of None als geen enkel
    formaat past.

    Odoo geeft dat label in de taal en de notatie van de server: '19 sep. 2024',
    '19/09/2024' of '2024-09-19'. De tijdzone wordt expliciet op Europe/Brussels
    gezet vóór het afkappen naar een dag; een label zonder zone is anders naïef,
    en dan hangt de uitkomst af van de machine in plaats van van de bakkerij.
    """
    for formaat in ("%d %b %Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(label, formaat).replace(tzinfo=TIJDZONE).date()
        except ValueError:
            continue
    return None


o = Odoo()
kop("BLOK A - TOEGANG")
print(f"Odoo-versie      {o.version}")
print(f"Database         {o.db}")
print(f"Uid              {o.uid}")

MODELLEN = [
    ("pos.order", "date_order", "kassa-orders"),
    ("pos.order.line", None, "kassa-bonregels"),
    ("sale.order", "date_order", "verkooporders"),
    ("sale.order.line", None, "verkooporderregels"),
    ("account.move", "invoice_date", "facturen"),
    ("product.product", None, "producten"),
    ("product.category", None, "productcategorieen"),
    ("pos.config", None, "kassa's"),
    ("stock.warehouse", None, "magazijnen"),
    ("res.company", None, "vennootschappen"),
    ("stock.move", "date", "voorraadbewegingen"),
    ("stock.scrap", "date_done", "afval/scrap"),
    ("mrp.production", "date_finished", "productieorders"),
    ("resource.calendar", None, "werk-/openingskalenders"),
]

print(f"\n{'model':24} {'records':>10}   bereik")
print("-" * 72)
beschikbaar = {}
for model, datumveld, label in MODELLEN:
    try:
        n = o.count(model)
    except ODOO_FOUT as exc:
        # Meestal een rechtenfout, maar niet altijd: een model dat in deze
        # Odoo-versie niet bestaat geeft dezelfde Fault. Daarom de reden erbij
        # in plaats van "geen rechten" als conclusie.
        print(f"{label:24} {'onleesbaar':>10}   {str(exc)[:44]}")
        continue
    beschikbaar[model] = n
    bereik = ""
    if n and datumveld:
        try:
            a = o.search_read(model, [], [datumveld], limit=1, order=f"{datumveld} asc")
            b = o.search_read(model, [], [datumveld], limit=1, order=f"{datumveld} desc")
            bereik = f"{str(a[0][datumveld])[:10]}  ->  {str(b[0][datumveld])[:10]}"
        except ODOO_FOUT as exc:
            bereik = f"datumveld onleesbaar ({str(exc)[:40]})"
        except (IndexError, KeyError):
            # Er zijn records geteld, maar het datumveld komt niet terug. Bij
            # Odoo gebeurt dat als het veld op dit model anders heet.
            bereik = f"veld '{datumveld}' bestaat niet op dit model"
    print(f"{label:24} {n:>10,}   {bereik}")

# --- welk model draagt de omzet ---------------------------------------------
POS = beschikbaar.get("pos.order", 0)
SALE = beschikbaar.get("sale.order", 0)
BRON = "pos.order" if POS >= SALE else "sale.order"
BRONLIJN = "pos.order.line" if BRON == "pos.order" else "sale.order.line"
QTY = "qty" if BRON == "pos.order" else "product_uom_qty"
print(f"\nDominante verkoopbron: {BRON} ({max(POS, SALE):,} orders)")

kop("BLOK B - GRANULARITEIT")
if beschikbaar.get(BRONLIJN):
    # fields_get leest het schema en raakt geen enkel record aan. Een
    # search_read met lege veldenlijst gaf hier ALLE velden van een echte rij
    # terug -- partner_id en notities incluis, en dat schendt harde regel 1.
    beschrijving = o.call(BRONLIJN, "fields_get", [], {"attributes": ["string", "type"]})
    velden = sorted(beschrijving)
    print(f"Velden op {BRONLIJN} ({len(velden)}):")
    print("  " + ", ".join(velden))
    for kandidaat in ["product_id", "qty", "product_uom_qty", "price_subtotal_incl",
                      "price_subtotal", "order_id", "discount"]:
        if kandidaat in velden:
            print(f"  aanwezig: {kandidaat}")
print("\nFilialen / kassa's:")
for m, v in [("pos.config", "name"), ("stock.warehouse", "name"), ("res.company", "name")]:
    if beschikbaar.get(m):
        rijen = veilig(lambda m=m, v=v: o.search_read(m, [], [v], limit=30))
        if isinstance(rijen, list):
            print(f"  {m:20} {len(rijen)}: " + ", ".join(r[v] for r in rijen[:12]))

kop("BLOK C+D - HISTORIEK EN VOLLEDIGHEID")
# Alleen de aanroep zit in de try. Het uitrekenwerk erna staat er bewust buiten:
# een fout in onze eigen telling mag niet als "read_group mislukt" op het scherm
# eindigen, want dan zoekt de volgende lezer bij Odoo naar een bug van ons.
try:
    per_dag = o.call(BRON, "read_group", [[], ["amount_total"], ["date_order:day"]], lazy=False)
except ODOO_FOUT as exc:
    per_dag = None
    print(f"read_group op {BRON} mislukt: {exc}")

if per_dag is not None:
    reeks = {}
    for r in per_dag:
        sleutel = r.get("date_order:day")
        if sleutel:
            reeks[sleutel] = (r["__count"], r.get("amount_total") or 0)
    print(f"Dagen met minstens 1 order: {len(reeks):,}")
    datums = sorted(d for d in (datum_uit_label(k) for k in reeks) if d)
    if datums:
        eerste, laatste = datums[0], datums[-1]
        span = (laatste - eerste).days + 1
        print(f"Eerste dag       {eerste}")
        print(f"Laatste dag      {laatste}")
        print(f"Kalenderspan     {span} dagen  (~{span / 30.4:.1f} maanden)")
        print(f"Dekking          {len(datums)}/{span} = {100 * len(datums) / span:.1f}% van de dagen heeft omzet")
        ontbrekend = span - len(datums)
        print(f"Dagen zonder ENIGE order: {ontbrekend}")
        weekdagen = Counter(d.strftime("%a") for d in datums)
        print("Orders per weekdag (aantal dagen met omzet):")
        for dag in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            print(f"  {dag}  {weekdagen.get(dag, 0):>5}")
        per_maand = Counter(d.strftime("%Y-%m") for d in datums)
        print(f"\nMaanden met data: {len(per_maand)}")
        for maand in sorted(per_maand)[-18:]:
            bar = "#" * min(31, per_maand[maand])
            print(f"  {maand}  {per_maand[maand]:>3} dagen  {bar}")
    elif reeks:
        print("Geen enkel daglabel was te lezen; de serverlocale geeft een "
              "onbekend datumformaat terug.")

kop("BLOK B/D - PRODUCTEN EN AFWIJKINGEN")
try:
    per_product = o.call(BRONLIJN, "read_group", [[], [QTY], ["product_id"]], lazy=False)
except ODOO_FOUT as exc:
    per_product = None
    print(f"read_group op {BRONLIJN} mislukt: {exc}")

if per_product is not None:
    print(f"Unieke producten met verkoop: {len(per_product):,}")
    gesorteerd = sorted(per_product, key=lambda r: -(r.get(QTY) or 0))
    print("\nTop 15 op volume:")
    for r in gesorteerd[:15]:
        print(f"  {naam(r['product_id'])[:46]:46} {r.get(QTY) or 0:>12,.0f}")
    negatief = [r for r in per_product if (r.get(QTY) or 0) < 0]
    print(f"\nProducten met netto NEGATIEF volume (retour/correctie): {len(negatief)}")
    staart = [r for r in per_product if 0 < (r.get(QTY) or 0) < 10]
    print(f"Producten met minder dan 10 stuks totaal (ruis/hernoemd): {len(staart)}")

kop("BLOK E - GECENSUREERDE VRAAG (aanbod en rest)")
for model, wat in [("mrp.production", "gebakken hoeveelheid"),
                   ("stock.scrap", "weggegooide hoeveelheid"),
                   ("stock.move", "voorraadbeweging")]:
    n = beschikbaar.get(model, 0)
    oordeel = "BESCHIKBAAR" if n else "AFWEZIG"
    print(f"{wat:32} {model:20} {n:>10,}  {oordeel}")
print("\nAls beide bovenste AFWEZIG zijn: verkoop is de enige proxy voor vraag,")
print("en uitverkoop-censurering wordt een expliciete beperking in het eindrapport.")

kop("BLOK F - MARGES")
try:
    p = o.search_read("product.product", [], ["standard_price", "list_price"], limit=500)
except ODOO_FOUT as exc:
    p = None
    print(f"kostprijzen niet leesbaar: {exc}")

if p is not None:
    met_kost = sum(1 for r in p if (r.get("standard_price") or 0) > 0)
    print(f"Producten in steekproef: {len(p)}")
    print(f"Met kostprijs ingevuld (standard_price > 0): {met_kost} ({100*met_kost/max(len(p),1):.0f}%)")
    print("Zonder kostprijs kan de beslislaag niet met echte marges rekenen;")
    print("dan wordt een marge per productgroep de aanname (docs/aannames.md).")

kop("BLOK G - KALENDER EN KANAAL")
print("Kanaalherkenning: zoek een veld dat winkel/Deliveroo/TGTG onderscheidt.")
try:
    # fields_get in plaats van een record lezen: het schema volstaat om
    # kandidaat-velden te vinden, en zo raakt dit blok nooit een echte bon aan
    # (harde regel 1). Werkt bovendien ook op een model zonder records.
    beschrijving = o.call(BRON, "fields_get", [], {"attributes": ["string", "type"]})
except ODOO_FOUT as exc:
    # Niet stil overslaan: als dit blok leeg blijft, moet op het scherm staan
    # waarom. Anders leest een lege uitkomst als "er is geen kanaalveld",
    # terwijl het antwoord in werkelijkheid nooit opgevraagd is.
    print(f"  Kandidaat-velden niet op te vragen op {BRON}: {str(exc)[:70]}")
else:
    kandidaten = [v for v in sorted(beschrijving) if any(
        t in v.lower() for t in ["channel", "kanaal", "source", "type", "config", "team", "route", "partner_id"])]
    print("  Kandidaat-velden op " + BRON + ": " + (", ".join(kandidaten) or "geen"))

print("\nKlaar. Vul docs/data-audit.md met deze cijfers en geef per blok een oordeel.")
