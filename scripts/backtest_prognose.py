"""Draait de baselines door het backtest-harnas, op de canonieke data.

Dit is de lat. Alles wat later "het model" heet, moet hier langs en moet deze
cijfers materieel verslaan; haalt het dat niet, dan gaat dát in het rapport
(harde regel 7: een voorspelling zonder backtest is een mening).

Twee niveaus, want de prognose belooft beide:

    dagomzet   de totale winkelomzet per dag
    product    per product per dag, voor de kernproducten

Alleen open dagen doen mee. Een gesloten dag is geen nulverkoop en er is niets
op te voorspellen; zie DREMPEL_OPEN in bakkerij/canoniek.py.

Draaien:  make backtest
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pandas as pd

from bakkerij import canoniek
from bakkerij.backtest.rolling import HORIZON, MIN_TRAIN, STAP, evalueer, vergelijk
from bakkerij.model.baseline import ALLE_BASELINES
from bakkerij.model.verfijning import met_feestdagcorrectie, weekdag_niveau

INTERIM = REPO / "data" / "interim"
RAPPORTEN = REPO / "reports"

# Een product moet op minstens dit aandeel van de open dagen verkocht zijn
# voordat we er een dagvoorspelling voor doen. Zie de beslissing van 12 aug:
# bij een product met een aanbodpatroon is een lege dag geen nulvraag, en de
# 103 kernproducten dekken 84,1% van alle verkochte stuks.
KERN_DEKKING = 0.95

# MIN_TRAIN/STAP/HORIZON komen sinds 18 aug 2026 uit het harnas zelf
# (bakkerij/backtest/rolling.py): één bron voor scherm én rapporten.


def laad() -> tuple[pd.DataFrame, pd.DatetimeIndex, pd.DataFrame]:
    for nodig in ("canoniek_verkopen.csv", "canoniek_kalender.csv"):
        if not (INTERIM / nodig).exists():
            raise SystemExit(f"data/interim/{nodig} ontbreekt. Draai eerst: make canoniek")
    verkopen = pd.read_csv(INTERIM / "canoniek_verkopen.csv", parse_dates=["datum"],
                           dtype=canoniek.CANONIEK_DTYPES)
    kalender = pd.read_csv(INTERIM / "canoniek_kalender.csv", parse_dates=["datum"])
    open_dagen = pd.DatetimeIndex(
        sorted(kalender.loc[kalender["winkel_open"], "datum"])
    )
    winkel = verkopen[
        (verkopen["kanaal"] == "winkel") & verkopen["datum"].isin(set(open_dagen))
    ]
    return winkel, open_dagen, kalender


def kandidaten(kalender: pd.DataFrame) -> dict:
    """Baselines plus de verfijningen van model/verfijning.py, één woordenboek.

    De feestdagcorrectie is een factory omdat het harnas de signatuur
    (historiek, doeldagen) verwacht; de kalender wordt hier gebonden. De
    kenmerken volgen uit de datum zelf, dus dit lekt geen toekomst.

    De drie feestdagkenmerken staan er sinds 19 augustus 2026 met zoveel
    woorden. Dit was de enige aanroeper die op de standaardwaarde van
    `met_feestdagcorrectie` leunde; die standaard is weg omdat hij per functie
    verschilde. De opgeschreven kenmerken zijn exact wat de standaard gaf, dus
    deze kandidaat meet hetzelfde als voorheen.
    """
    return {
        **ALLE_BASELINES,
        "weekdag_niveau": weekdag_niveau,
        "niveau_feestdag": met_feestdagcorrectie(
            weekdag_niveau, kalender,
            kenmerken=("feestdag", "dag_voor_feestdag", "brugdag"),
            naam="niveau_feestdag",
        ),
    }


def dagomzet(winkel: pd.DataFrame) -> pd.Series:
    return winkel.groupby("datum")["omzet_excl_btw"].sum().sort_index()


def kernproducten(winkel: pd.DataFrame, n_open: int) -> list:
    per_product = winkel.groupby("product_id")["datum"].nunique()
    return sorted(per_product[per_product >= KERN_DEKKING * n_open].index)


def backtest_dagomzet(reeks: pd.Series, modellen: dict) -> list:
    return [
        evalueer(reeks, fn, naam=naam, min_train=MIN_TRAIN, stap=STAP, horizon=HORIZON)
        for naam, fn in modellen.items()
    ]


def backtest_producten(winkel: pd.DataFrame, producten: list,
                       modellen: dict) -> pd.DataFrame:
    """Per baseline de gewogen afwijking over alle kernproducten samen.

    Gewogen op werkelijke stuks, niet als gemiddelde van percentages: een klein
    product mag het cijfer niet even zwaar bepalen als een broodlijn.
    """
    stuks = (
        winkel.groupby(["product_id", "datum"])["aantal"].sum().sort_index()
    )
    opgeteld = {naam: [0.0, 0.0, 0] for naam in modellen}
    overgeslagen = 0

    for pid in producten:
        reeks = stuks.loc[pid]
        if len(reeks) < MIN_TRAIN + HORIZON:
            overgeslagen += 1
            continue
        for naam, fn in modellen.items():
            r = evalueer(reeks, fn, naam=naam, min_train=MIN_TRAIN,
                         stap=STAP, horizon=HORIZON)
            opgeteld[naam][0] += r.som_absolute_fout
            opgeteld[naam][1] += r.som_werkelijk
            opgeteld[naam][2] += r.n_dagen

    if overgeslagen:
        print(f"  ({overgeslagen} kernproducten overgeslagen: te korte reeks)")

    rijen = [
        {
            "baseline": naam,
            "wape": (fout / werkelijk) if werkelijk else 0.0,
            "mae_stuks": fout / n if n else 0.0,
            "n_beslissingen": n,
        }
        for naam, (fout, werkelijk, n) in opgeteld.items()
    ]
    return pd.DataFrame(rijen).sort_values("wape").reset_index(drop=True)


def main() -> int:
    winkel, open_dagen, kalender = laad()
    reeks = dagomzet(winkel)
    kern = kernproducten(winkel, len(open_dagen))
    modellen = kandidaten(kalender)

    print("=" * 92)
    print("BACKTEST PROGNOSE — rolling origin, alleen open dagen")
    print("=" * 92)
    print(f"open dagen        : {len(open_dagen)}  "
          f"({open_dagen[0].date()} -> {open_dagen[-1].date()})")
    print(f"gem. dagomzet     : EUR {reeks.mean():,.0f}")
    print(f"kernproducten     : {len(kern)} van {winkel['product_id'].nunique()} "
          f"(>= {KERN_DEKKING:.0%} van de open dagen)")
    print(f"opzet             : train >= {MIN_TRAIN} open dagen, "
          f"horizon {HORIZON} open dagen, stap {STAP}")

    print("\n--- 1. DAGOMZET WINKEL (euro's) ---")
    resultaten = backtest_dagomzet(reeks, modellen)
    print(vergelijk(resultaten))

    print("\n--- 2. PER PRODUCT PER DAG (stuks, gewogen over de kernproducten) ---")
    per_product = backtest_producten(winkel, kern, modellen)
    for _, r in per_product.iterrows():
        print(f"  {r['baseline']:<22} WAPE {r['wape']:>6.1%}  "
              f"MAE {r['mae_stuks']:>6.1f} stuks  n={int(r['n_beslissingen']):,}")

    RAPPORTEN.mkdir(exist_ok=True)
    uit = RAPPORTEN / "backtest_baselines.csv"
    pd.DataFrame([
        {"niveau": "dagomzet", "baseline": r.naam, "wape": r.wape,
         "mae": r.mae_euro, "bias": r.bias_euro, "n": r.n_dagen}
        for r in resultaten
    ] + [
        {"niveau": "product", "baseline": r["baseline"], "wape": r["wape"],
         "mae": r["mae_stuks"], "bias": None, "n": r["n_beslissingen"]}
        for _, r in per_product.iterrows()
    ]).to_csv(uit, index=False)

    print(f"\nWeggeschreven: {uit.relative_to(REPO)}")
    print("Dit is de lat. Een model dat deze cijfers niet materieel verslaat, "
          "voegt niets toe\nen dat hoort zo in het rapport (harde regel 7).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
