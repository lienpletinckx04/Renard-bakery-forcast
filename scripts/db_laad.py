"""Het canonieke model naar Postgres schrijven.

    data/interim/canoniek_*.csv  ->  Supabase

Draaien:  make db-laad
Droog:    make db-laad DROOG=1

De droge modus doet alles behalve schrijven: ze leest de CSV's, bereidt elke
tabel voor, ontdubbelt, en controleert de verwijzingen naar de dimensies.
Daarmee is de hele voorbereiding te toetsen zonder database en zonder
sleutel -- en dat is precies wat je wil, want de fouten die hier ontstaan
(een dubbele sleutel, een datum die de kalender niet kent) hebben niets met
de verbinding te maken.

VOLGORDE

dim_kalender en dim_product eerst, dan pas de feiten. De feitentabellen
verwijzen ernaar, en Postgres weigert een feit waarvan de dimensie ontbreekt.

Dit script print aantallen, kolomnamen en datumbereiken. Nooit rijen.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pandas as pd

from bakkerij import canoniek
from bakkerij.db import droge_modus, laden
from bakkerij.db.verbinding import dsn_uit_omgeving, verbind
from bakkerij.omgeving import laad_env

INTERIM = REPO / "data" / "interim"

KALENDER_KOLOMMEN = [
    "datum", "weekdag", "weekdagnaam", "is_weekend", "feestdag", "feestdagnaam",
    "dag_voor_feestdag", "dag_na_feestdag", "brugdag", "maand", "weeknr",
    "dag_van_jaar", "winkel_gemeten", "winkel_open",
]


def _datum(serie: pd.Series) -> pd.Series:
    return pd.to_datetime(serie).dt.date


def bereid_kalender(kal: pd.DataFrame) -> pd.DataFrame:
    df = kal.copy()
    # De kolomcontrole vóór het aanraken van een kolom, en niet erna. Stond
    # `fillna("feestdagnaam")` hierboven, dan gaf een kalender zonder die kolom
    # een kale KeyError in plaats van de bedoelde "draai eerst make canoniek".
    ontbreekt = set(KALENDER_KOLOMMEN) - set(df.columns)
    if ontbreekt:
        raise SystemExit(
            f"canoniek_kalender.csv mist kolommen {sorted(ontbreekt)}. "
            "Draai eerst: make canoniek"
        )
    df["datum"] = _datum(df["datum"])
    # Lege tekst en geen NULL: de kolom is `not null default ''` in migratie
    # 001. Zie NULL_SENTINEL in bakkerij/db/laden.py voor waarom dat verschil
    # de hele laadstap ooit stopzette.
    df["feestdagnaam"] = df["feestdagnaam"].fillna("")
    return df[KALENDER_KOLOMMEN]


def bereid_verkoop(verkopen: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    df = verkopen.copy()
    df["datum"] = _datum(df["datum"])
    sleutel = ["datum", "kanaal", "filiaal_id", "product_id"]
    df, dubbel = laden.ontdubbel(df, sleutel, ["aantal", "omzet_excl_btw"])
    df["omzet_excl_btw"] = laden.naar_decimaal(df["omzet_excl_btw"])
    return df[sleutel + ["aantal", "omzet_excl_btw"]], dubbel


def bereid_bonnen(bonnen: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    df = bonnen.copy()
    df["datum"] = _datum(df["datum"])
    df, dubbel = laden.ontdubbel(df, ["datum", "filiaal_id"], ["bonnen"])
    df["bonnen"] = df["bonnen"].astype(int)
    return df[["datum", "filiaal_id", "bonnen"]], dubbel


def bereid_uren(uren: pd.DataFrame) -> pd.DataFrame:
    df = uren.copy()
    df["datum"] = _datum(df["datum"])
    # Hier NIET ontdubbelen met een som: een uur optellen is onzin. De bron
    # levert één rij per product per dag; twee rijen zou een bronfout zijn en
    # die hoort luidruchtig te falen op de primaire sleutel.
    for kolom in ("eerste_uur", "laatste_uur"):
        df[kolom] = laden.naar_decimaal(df[kolom])
    df["bonnen"] = df["bonnen"].astype(int)
    return df[["datum", "product_id", "eerste_uur", "laatste_uur", "bonnen"]]


def bereid_kanaalkost(kk: pd.DataFrame) -> pd.DataFrame:
    df = kk.copy()
    for kolom, plaatsen in (
        ("stuks", "0.001"), ("bruto_per_stuk", "0.0001"),
        ("commissie_per_stuk", "0.0001"), ("inhouding_pct", "0.0001"),
    ):
        df[kolom] = laden.naar_decimaal(df[kolom], plaatsen)
    return df[["kanaal", "maand", "stuks", "bruto_per_stuk",
               "commissie_per_stuk", "inhouding_pct"]]


def _lees(naam: str, verplicht: bool = True) -> pd.DataFrame | None:
    pad = INTERIM / naam
    if not pad.exists():
        if verplicht:
            raise SystemExit(f"{naam} ontbreekt. Draai eerst: make canoniek")
        return None
    # Dezelfde mapping als elke andere lezer van de canonieke CSV. Stond hier
    # als eigen kopie; twee lijsten die hetzelfde moeten zeggen, lopen uiteen.
    return pd.read_csv(pad, dtype=canoniek.CANONIEK_DTYPES)


def main() -> int:
    laad_env()
    droog = droge_modus()

    verkopen_ruw = _lees("canoniek_verkopen.csv")
    kalender_ruw = _lees("canoniek_kalender.csv")
    kanaalkost_ruw = _lees("canoniek_kanaalkost.csv", verplicht=False)
    bonnen_ruw = _lees("canoniek_bonnen.csv", verplicht=False)
    uren_ruw = _lees("canoniek_uren.csv", verplicht=False)

    kalender = bereid_kalender(kalender_ruw)
    producten = laden.kies_productnaam(verkopen_ruw)
    verkoop, verkoop_dubbel = bereid_verkoop(verkopen_ruw)

    print("=" * 64)
    print("LADEN NAAR POSTGRES" + ("  (DROOG)" if droog else ""))
    print("=" * 64)
    print(f"dim_kalender      {len(kalender):>8,} rijen  "
          f"{kalender['datum'].min()} t/m {kalender['datum'].max()}")
    print(f"dim_product       {len(producten):>8,} rijen")
    print(f"fact_verkoop      {len(verkoop):>8,} rijen  "
          f"{verkoop['datum'].min()} t/m {verkoop['datum'].max()}")
    if verkoop_dubbel:
        print(f"                  {verkoop_dubbel:,} dubbele sleutels opgeteld")

    # De verwijzingscontrole vóór het schrijven. Zonder deze stap valt de
    # transactie om op een Postgres-melding die de rij niet noemt.
    tabellen: list[tuple[str, pd.DataFrame, list[str], list[str]]] = [
        ("dim_kalender", kalender, KALENDER_KOLOMMEN, ["datum"]),
        ("dim_product", producten, ["product_id", "product_naam"], ["product_id"]),
        ("fact_verkoop", verkoop,
         ["datum", "kanaal", "filiaal_id", "product_id", "aantal", "omzet_excl_btw"],
         ["datum", "kanaal", "filiaal_id", "product_id"]),
    ]

    if bonnen_ruw is not None:
        bonnen, bonnen_dubbel = bereid_bonnen(bonnen_ruw)
        print(f"fact_bonnen       {len(bonnen):>8,} rijen"
              + (f"  ({bonnen_dubbel:,} opgeteld)" if bonnen_dubbel else ""))
        tabellen.append(("fact_bonnen", bonnen,
                         ["datum", "filiaal_id", "bonnen"], ["datum", "filiaal_id"]))
    else:
        print("fact_bonnen       ONBESCHIKBAAR: canoniek_bonnen.csv ontbreekt")

    if uren_ruw is not None:
        uren = bereid_uren(uren_ruw)
        print(f"fact_product_uren {len(uren):>8,} rijen")
        tabellen.append(("fact_product_uren", uren,
                         ["datum", "product_id", "eerste_uur", "laatste_uur", "bonnen"],
                         ["datum", "product_id"]))
    else:
        print("fact_product_uren ONBESCHIKBAAR: canoniek_uren.csv ontbreekt")

    if kanaalkost_ruw is not None and not kanaalkost_ruw.empty:
        kanaalkost = bereid_kanaalkost(kanaalkost_ruw)
        print(f"fact_kanaalkost   {len(kanaalkost):>8,} rijen")
        tabellen.append(("fact_kanaalkost", kanaalkost,
                         ["kanaal", "maand", "stuks", "bruto_per_stuk",
                          "commissie_per_stuk", "inhouding_pct"],
                         ["kanaal", "maand"]))
    else:
        print("fact_kanaalkost   ONBESCHIKBAAR: canoniek_kanaalkost.csv ontbreekt")

    fouten = []
    for naam, df, _, _ in tabellen:
        if "datum" in df.columns and naam != "dim_kalender":
            weg = laden.onbekende_verwijzingen(df, "datum", kalender["datum"])
            if weg:
                fouten.append(
                    f"{naam}: {len(weg)} datum(s) staan niet in dim_kalender, "
                    f"eerste {weg[0]}, laatste {weg[-1]}"
                )
        if "product_id" in df.columns and naam != "dim_product":
            weg = laden.onbekende_verwijzingen(df, "product_id", producten["product_id"])
            if weg:
                fouten.append(
                    f"{naam}: {len(weg)} product_id(s) staan niet in dim_product"
                )

    if fouten:
        print("\nGEBLOKKEERD -- de verwijzingen kloppen niet:")
        for f in fouten:
            print(f"  {f}")
        print("\nEr is niets geschreven. Draai `make canoniek` opnieuw, zodat "
              "de kalender het volledige bereik van alle extracten dekt.")
        return 1

    print("\nVerwijzingen: in orde.")

    if droog:
        print("\nDROOG=1: er is niets geschreven en geen verbinding gelegd.")
        return 0

    try:
        dsn_uit_omgeving()
    except ValueError as fout:
        print(f"\n{fout}", file=sys.stderr)
        return 1

    with verbind() as verbinding:
        run_id = laden.start_run(verbinding, "canoniek")
        try:
            totaal = 0
            # Eén commit ná alle tabellen: de docstring belooft alles-of-niets,
            # en een commit per tabel liet een halve lading achter wanneer een
            # latere tabel omviel (audit 14 aug).
            for naam, df, kolommen, sleutel in tabellen:
                totaal += laden.schrijf(verbinding, naam, df, kolommen, sleutel)
                print(f"  {naam:<18} geschreven")
            verbinding.commit()
        except Exception as fout:
            # Eerst de mislukte transactie terugdraaien: in een 'aborted'
            # transactie weigert Postgres élk statement, dus ook de
            # foutregistratie zelf zou anders omvallen.
            verbinding.rollback()
            # De melding is leesbaar voor elke ingelogde gebruiker, dus alleen
            # het type en de tekst van de fout -- nooit een rij uit de data.
            laden.eind_run(verbinding, run_id, "fout",
                           melding=f"{type(fout).__name__}: {fout}"[:500])
            raise
        laden.eind_run(verbinding, run_id, "goed", rijen=totaal)

    print(f"\nKlaar. {totaal:,} rijen weggeschreven, run {run_id} afgesloten als 'goed'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
