"""Voert de censureringsmeting (O8) uit op het laatste-verkoopuur-extract.

Print UITSLUITEND aggregaten: aantallen, percentages, verdelingen. Geen
productnamen, geen rijen, geen dagen. De uitkomst is de bevinding die in het
backtest-rapport (E4) hoort: ligt de censurering tussen verwaarloosbaar en
structureel, en voor hoeveel van de omzet?

Draaien (na scripts/odoo_laatste_uur.py):
    .venv/bin/python scripts/censurering_meting.py
"""
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from bakkerij import canoniek
from bakkerij import censurering as cz

RAW = REPO / "data" / "raw"
INTERIM = REPO / "data" / "interim"


def nieuwste(patroon: str) -> Path:
    kandidaten = sorted(RAW.glob(patroon))
    if not kandidaten:
        raise SystemExit(f"Geen bestand voor {patroon}. Draai eerst de extractie.")
    return kandidaten[-1]


def main():
    pad = nieuwste("*_odoo_laatste_uur_*.csv")
    uren = pd.read_csv(pad, parse_dates=["datum"])
    uren["datum"] = uren["datum"].dt.date

    kalender = pd.read_csv(INTERIM / "canoniek_kalender.csv", parse_dates=["datum"])
    kalender["datum"] = kalender["datum"].dt.date
    open_dagen = set(kalender.loc[kalender["winkel_open"], "datum"])

    meting = cz.meet(uren, open_dagen=open_dagen)
    s = cz.samenvatting(meting)

    print(f"CENSURERINGSMETING op {pad.name}")
    print(f"  open dagen in de kalender       : {len(open_dagen):,}")
    print(f"  producten in de meting          : {s['producten']:,}")
    print(f"  ... met eigen referentie        : {s['producten_met_referentie']:,}")
    print(f"  product-dagen                   : {s['productdagen']:,}")
    print(f"  ... gewogen (>= {cz.MIN_BONNEN} bonnen)      : {s['productdagen_gewogen']:,}")
    print()
    print("  BOVENGRENS  vroeg t.o.v. winkelsluit die dag   "
          f": {s['aandeel_bovengrens']:.1%} van de gewogen dagen")
    print("  ONDERGRENS  én vroeg t.o.v. eigen p90          "
          f": {s['aandeel_gecensureerd']:.1%} van de gewogen dagen")
    print(f"  structureel gecensureerd (>=20% van de dagen)  "
          f": {s['structureel_gecensureerde_producten']:,} producten")

    # Hoeveel van de omzet zit bij de structureel gecensureerde producten?
    # Join op productniveau (aggregaat), niet op rij-niveau.
    met_ref = meting.dropna(subset=["gecensureerd"])
    structureel = set(met_ref[met_ref["gecensureerd"] >= 0.20].index)
    verkopen = pd.read_csv(INTERIM / "canoniek_verkopen.csv",
                           dtype=canoniek.CANONIEK_DTYPES)
    winkel = verkopen[verkopen["kanaal"] == "winkel"]
    omzet_per_product = winkel.groupby("product_id")["omzet_excl_btw"].sum()
    totaal = omzet_per_product.sum()
    aandeel = omzet_per_product[omzet_per_product.index.isin(structureel)].sum() / totaal
    print(f"  omzetaandeel van die producten                 : {aandeel:.1%}")

    # Verdeling van de ondergrens, zodat de staart zichtbaar is.
    print("\n  verdeling gecensureerd-aandeel over producten met referentie:")
    randen = [0, 0.05, 0.10, 0.20, 0.35, 0.50, 1.0]
    labels = ["0-5%", "5-10%", "10-20%", "20-35%", "35-50%", ">50%"]
    telling = pd.cut(met_ref["gecensureerd"], randen, labels=labels,
                     include_lowest=True).value_counts().sort_index()
    for label, n in telling.items():
        print(f"    {label:>7}: {n:4d} producten")

    # Het weekdagpatroon: censurering die vooral op zaterdag optreedt is een
    # ander verhaal (en een andere bijbestelling) dan door de week. Zelfde
    # signaal als hierboven, uit dezelfde functie — een tweede implementatie
    # zou hier stilzwijgend uit de pas gaan lopen met `meet`.
    df = cz.signaal_per_dag(uren, open_dagen=open_dagen)
    df["weekdag"] = pd.to_datetime(df["datum"].astype(str)).dt.dayofweek
    namen = ["ma", "di", "wo", "do", "vr", "za", "zo"]
    per_dag = df[df["gewogen"]].groupby("weekdag")["gecensureerd"].mean()
    print("\n  gecensureerd-aandeel per weekdag (gewogen dagen):")
    for wd, aandeel_wd in per_dag.items():
        print(f"    {namen[int(wd)]}: {aandeel_wd:.1%}")


if __name__ == "__main__":
    raise SystemExit(main())
