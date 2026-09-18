"""Meet of uitverkoop zichtbaar is in het laatste verkoopuur (O8/O11).

Wat de kassa meet is verkoop, niet vraag. Als de croissants om 10u op zijn,
telt de kassa de rek en niet de klant. Deze module beantwoordt de vraag of
dat patroon meetbaar is, met het laatste verkoopuur per product per dag als
signaal (extractie: scripts/odoo_laatste_uur.py).

Een dag telt pas als censureringssignaal wanneer DRIE dingen samenvallen:

  1. het product had die dag genoeg bonnen (`min_bonnen`). Een traag product
     met vier bonnen per dag heeft zijn laatste bon uren vóór sluitingstijd,
     ook met volle rekken — schaarse aankopen zijn geen leeg rek. De eerste
     versie van deze meting miste dit filter en rapporteerde 54% "censurering";
     dat was grotendeels deze vertekening.
  2. de laatste bon viel minstens `drempel` uren vóór de laatste bon van de
     hele winkel DIE DAG. De winkel sluit niet elke dag even laat (zondag!);
     meten tegen een vaste sluittijd zou elke korte dag als uitverkoop lezen.
     De eerste versie rapporteerde 97% op zondag — dat was de korte zondag,
     geen leeg rek.
  3. de laatste bon lag minstens `drempel` uren onder het eigen p90-referentie-
     uur van het product: het uur dat het haalt op drukke dagen waarop het
     aanbod strekt. Dit filtert producten die uit gewoonte 's ochtends
     verkopen.

Blinde vlek, erkend en niet weg te meten: een product dat ÁLTIJD vroeg op is,
heeft een vroege referentie en wordt nooit gevlagd. De meting is dus een
ondergrens. De bovengrens (alles wat vroeg stopt t.o.v. de winkel, zonder
filter 3) wordt apart gerapporteerd, en de waarheid ligt ertussen.

Alle functies zijn puur: DataFrames in, DataFrames of scalars uit. Geen I/O.
"""
from __future__ import annotations

import pandas as pd

#: Uren onder de referentie voordat een product-dag "vroeg op" heet.
#: Twee uur, niet één: kassadrukte golft, en één uur zonder bon voor een
#: gemiddeld product is ruis, geen leeg rek.
DREMPEL_UREN = 2

#: Minder bonnen dan dit op een dag en de dag telt niet mee: de laatste bon
#: van een schaars gekocht product zegt niets over het rek. Tien bonnen die
#: allemaal >= 2 uur voor sluit vallen terwijl de winkel doordraait, is wél
#: een signaal.
MIN_BONNEN = 10

#: Minder gewogen dagen dan dit en een product krijgt geen referentie: een
#: p90 op een handvol dagen is een gok.
MIN_DAGEN = 30

#: De referentie is p90, niet max: de max is één uitschieter (een feestdag
#: met verlengde opening), p90 is wat het product gewoonlijk haalt als het
#: aanbod strekt.
REFERENTIE_KWANTIEL = 0.90

KOLOMMEN = ["datum", "product_id", "eerste_uur", "laatste_uur", "bonnen"]

SIGNAAL_KOLOMMEN = ["datum", "product_id", "gewogen", "bovengrens",
                    "gecensureerd", "referentie_uur"]


def sluitproxy_per_dag(uren: pd.DataFrame) -> pd.Series:
    """datum -> laatste verkoopuur van de hele winkel die dag.

    De echte sluitingstijd staat nergens in de data; de laatste bon van de
    dag is de beste proxy. Op een dag waarop de hele winkel om 13u zijn
    laatste bon had (zondag), schuift de lat mee — dat is precies de
    bedoeling.
    """
    return uren.groupby("datum")["laatste_uur"].max()


def referentie_uur(
    uren: pd.DataFrame, *, min_bonnen: int = MIN_BONNEN, min_dagen: int = MIN_DAGEN
) -> pd.Series:
    """product_id -> p90 van het laatste verkoopuur op dagen met genoeg bonnen.

    Alleen drukke dagen tellen: de referentie moet zeggen "tot hoe laat haalt
    dit product als het aanbod strekt", en dat is niet te zien op een dag met
    drie bonnen. Producten met minder dan `min_dagen` zulke dagen krijgen
    geen referentie.
    """
    druk = uren[uren["bonnen"] >= min_bonnen]
    per_product = druk.groupby("product_id")["laatste_uur"]
    genoeg = per_product.count() >= min_dagen
    p90 = per_product.quantile(REFERENTIE_KWANTIEL)
    return p90[genoeg[p90.index]]


def signaal_per_dag(
    uren: pd.DataFrame,
    *,
    open_dagen: set | None = None,
    drempel: int = DREMPEL_UREN,
    min_bonnen: int = MIN_BONNEN,
    min_dagen: int = MIN_DAGEN,
) -> pd.DataFrame:
    """Per product-dag: woog deze dag mee, en wees hij op een leeg rek?

    Dit is de kern van `meet`, apart gezet omdat er twee lezers van zijn.
    `meet` telt dit op per product. De wachter `censureringsdrempel` in
    bakkerij/kwaliteit.py legt twee periodes uit dezelfde uitkomst naast
    elkaar, en die mag `meet` niet twee keer aanroepen: de referentie-uren
    worden berekend over het bereik dat je meegeeft, dus een aanroep per
    periode verschuift de lat mee met de verandering die de wachter juist
    moet zien.

    `open_dagen`: alleen deze datums tellen mee (de kalenderlaag weet welke
    dagen de winkel echt open was). None = alle datums in `uren`.

    Uit: één rij per rij in de invoer, met
      gewogen         de dag had >= min_bonnen bonnen voor dit product
      bovengrens      gewogen én >= drempel uren vóór de winkelsluiting van
                      die dag (gewoonte telt mee)
      gecensureerd    óók >= drempel onder het eigen referentie-uur
      referentie_uur  de p90 van dit product (NaN zonder referentie; dan is
                      `gecensureerd` altijd False en zegt hij niets)
    """
    ontbreekt = set(KOLOMMEN) - set(uren.columns)
    if ontbreekt:
        raise ValueError(f"uren mist kolommen: {sorted(ontbreekt)}")

    df = uren if open_dagen is None else uren[uren["datum"].isin(open_dagen)]
    if df.empty:
        return pd.DataFrame(columns=SIGNAAL_KOLOMMEN)

    sluit = df["datum"].map(sluitproxy_per_dag(df))
    referentie = referentie_uur(df, min_bonnen=min_bonnen, min_dagen=min_dagen)
    eigen = df["product_id"].map(referentie)

    druk = df["bonnen"] >= min_bonnen
    vroeg_vs_winkel = (sluit - df["laatste_uur"]) >= drempel
    vroeg_vs_eigen = (eigen - df["laatste_uur"]) >= drempel  # NaN-referentie -> False

    return pd.DataFrame(
        {
            "datum": df["datum"],
            "product_id": df["product_id"],
            "gewogen": druk,
            "bovengrens": druk & vroeg_vs_winkel,
            "gecensureerd": druk & vroeg_vs_winkel & vroeg_vs_eigen,
            "referentie_uur": eigen,
        }
    )[SIGNAAL_KOLOMMEN].reset_index(drop=True)


def meet(
    uren: pd.DataFrame,
    *,
    open_dagen: set | None = None,
    drempel: int = DREMPEL_UREN,
    min_bonnen: int = MIN_BONNEN,
    min_dagen: int = MIN_DAGEN,
) -> pd.DataFrame:
    """Per product: hoe vaak wees het laatste verkoopuur op een leeg rek.

    `open_dagen`: alleen deze datums tellen mee (de kalenderlaag weet welke
    dagen de winkel echt open was). None = alle datums in `uren`.

    Uit: DataFrame met index product_id en kolommen
      dagen            verkoopdagen binnen open_dagen (alle, ook rustige)
      dagen_gewogen    dagen met >= min_bonnen bonnen; alleen die kunnen vlaggen
      referentie_uur   p90 van het laatste uur op drukke dagen (NaN onder
                       min_dagen drukke dagen)
      bovengrens       aandeel gewogen dagen >= drempel uren vóór de
                       winkelsluiting van die dag (gewoonte telt mee)
      gecensureerd     aandeel gewogen dagen dat óók >= drempel onder de eigen
                       referentie lag (NaN zonder referentie) — de ondergrens
    """
    per_dag = signaal_per_dag(uren, open_dagen=open_dagen, drempel=drempel,
                              min_bonnen=min_bonnen, min_dagen=min_dagen)
    kolommen = ["dagen", "dagen_gewogen", "referentie_uur", "bovengrens", "gecensureerd"]
    if per_dag.empty:
        return pd.DataFrame(columns=kolommen)

    per_product = per_dag.groupby("product_id").agg(
        dagen=("gewogen", "size"),
        dagen_gewogen=("gewogen", "sum"),
        bovengrens=("bovengrens", "sum"),
        gecensureerd=("gecensureerd", "sum"),
        # Het referentie-uur is per product constant; max() haalt het eruit en
        # laat NaN staan waar het product er geen heeft.
        referentie_uur=("referentie_uur", "max"),
    )
    gewogen = per_product["dagen_gewogen"]
    per_product["bovengrens"] = per_product["bovengrens"] / gewogen
    per_product["gecensureerd"] = per_product["gecensureerd"] / gewogen
    zonder_ref = per_product["referentie_uur"].isna()
    per_product.loc[zonder_ref, "gecensureerd"] = float("nan")
    return per_product[kolommen]


def samenvatting(meting: pd.DataFrame, *, structureel_vanaf: float = 0.20) -> dict:
    """De cijfers voor het rapport, als scalars. Geen rij-data.

    `structureel_vanaf`: een product heet structureel gecensureerd als het op
    minstens dit aandeel van zijn gewogen dagen een leeg-reksignaal gaf.
    Aandelen zijn gewogen naar dagen_gewogen: een product dat elke dag
    meetbaar is, weegt zwaarder dan een dat één keer per week piekt.
    """
    met_referentie = meting.dropna(subset=["gecensureerd"])
    gewogen = met_referentie["dagen_gewogen"].sum()
    alle_gewogen = meting["dagen_gewogen"].sum()
    return {
        "producten": len(meting),
        "producten_met_referentie": len(met_referentie),
        "productdagen": int(meting["dagen"].sum()),
        "productdagen_gewogen": int(alle_gewogen),
        "aandeel_bovengrens": float(
            (meting["bovengrens"] * meting["dagen_gewogen"]).sum() / alle_gewogen
        )
        if alle_gewogen
        else float("nan"),
        "aandeel_gecensureerd": float(
            (met_referentie["gecensureerd"] * met_referentie["dagen_gewogen"]).sum() / gewogen
        )
        if gewogen
        else float("nan"),
        "structureel_gecensureerde_producten": int(
            (met_referentie["gecensureerd"] >= structureel_vanaf).sum()
        ),
    }
