"""Prognose per productcategorie (blok 15b, kandidaat a).

Zes categorieën dragen ~80% van de omzet; per product blijft de fout op ~20%
WAPE steken, maar per categorie middelen de productfouten uit. Dit is de laag
tussen dag en product: bruikbaar om te zien wélke hoek van het assortiment de
verwachte week draagt, zonder de belofte van een productprognose die de data
niet waarmaakt.

Twee regels uit het harnas gelden onverkort:

  * Geen prognose zonder backtest (harde regel 7): elke categorie krijgt haar
    eigen gemeten WAPE en haar eigen band uit haar eigen residuen. Een
    categorie met te weinig historiek doet niet mee en staat met die reden in
    het contract, niet stilzwijgend op nul.
  * De som van de categorieën is een tweede kandidaat voor de dagprognose en
    wordt als zodanig door hetzelfde harnas gehaald (`som_van_categorieen`).
    Of de som de directe dagprognose vervangt, beslist de meting — niet de
    esthetiek van "consistent optellen".
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from bakkerij import taal as tl
from bakkerij.backtest.rolling import Voorspeller, band_per_stap, evalueer, per_horizon

#: Minder gemeten open dagen dan dit en een categorie doet niet mee: het
#: harnas kan er geen betrouwbare fout op meten (zelfde orde als min_train).
MIN_HISTORIEK = 180


@dataclass(frozen=True)
class Categorieprognose:
    """Eén categorie: haar venstervoorspelling met gemeten fout en band."""

    categorie: str
    aandeel_pct: float  # aandeel in de kanaalomzet over de gehele historiek
    wape: float
    band: pd.DataFrame  # datum | verwacht | onder | boven
    weektotaal: float  # som van de puntvoorspellingen over het venster


def categorie_reeksen(
    open_verkopen_df: pd.DataFrame,
    groepen: pd.Series,
    *,
    top_n: int = 6,
    kanaal: str = "winkel",
) -> list[tuple[str, pd.Series, float]]:
    """Dagomzet per categorie: de `top_n` zwaarste apart, de rest als
    "Overige categorieën" gebundeld zodat de som de dagomzet blijft.

    Uit: (categorie, dagreeks, aandeel_pct) — zwaarste eerst.
    """
    deel = open_verkopen_df[open_verkopen_df["kanaal"] == kanaal].copy()
    if deel.empty:
        return []
    # t() en niet een constante: deze functie draait binnen de taallus van de
    # contractbouw, en de twee labels hier zijn de enige teksten van deze
    # module die een lezer ziet. Ze vielen buiten de teller (korte teksten).
    deel["groep"] = (deel["product_id"].astype(str).map(groepen)
                     .fillna(tl.t("Overige", "Autres")))
    totaal = float(deel["omzet_excl_btw"].sum())
    per_groep = (
        deel.groupby("groep")["omzet_excl_btw"].sum().sort_values(ascending=False)
    )
    kop = list(per_groep.head(top_n).index)
    deel["categorie"] = deel["groep"].where(
        deel["groep"].isin(kop),
        tl.t("Overige categorieën", "Autres catégories"),
    )

    uit: list[tuple[str, pd.Series, float]] = []
    for naam, groep_df in deel.groupby("categorie"):
        reeks = (
            groep_df.groupby("datum")["omzet_excl_btw"].sum().sort_index()
        )
        aandeel = 100.0 * float(groep_df["omzet_excl_btw"].sum()) / totaal
        uit.append((str(naam), reeks, aandeel))
    uit.sort(key=lambda x: x[2], reverse=True)
    return uit


def som_van_categorieen(
    reeksen: list[tuple[str, pd.Series, float]], basis: Voorspeller
) -> Voorspeller:
    """De som van de categorieprognoses als dagvoorspeller, voor het harnas.

    Elke categoriereeks wordt op datum afgekapt op het einde van de training —
    dezelfde grens als de dagreeks, dus er lekt geen toekomst. Een categorie
    zonder waarnemingen vóór die grens telt niet mee (haar bijdrage is dan ook
    in de werkelijkheid nul of bijna nul).
    """

    def voorspeller(historiek: pd.Series, doeldagen: pd.DatetimeIndex) -> pd.Series:
        grens = historiek.index.max()
        totaal = pd.Series(0.0, index=doeldagen)
        for _, reeks, _ in reeksen:
            deel = reeks[reeks.index <= grens]
            if len(deel) < 14:  # minder dan twee weken: geen weekdagvorm
                continue
            totaal = totaal + basis(deel, doeldagen)
        return totaal.rename("som_categorieen")

    return voorspeller


def categorie_prognoses(
    reeksen: list[tuple[str, pd.Series, float]],
    basis: Voorspeller,
    doeldagen: pd.DatetimeIndex,
    *,
    min_train: int = MIN_HISTORIEK,
    stap: int = 7,
    horizon: int = 7,
    onder: float = 0.10,
    boven: float = 0.90,
) -> tuple[list[Categorieprognose], list[str]]:
    """Per categorie een gemeten prognose; categorieën met te weinig
    historiek komen terug als tweede lijst en horen in `onbeschikbaar`."""
    prognoses: list[Categorieprognose] = []
    overgeslagen: list[str] = []
    for naam, reeks, aandeel in reeksen:
        if len(reeks) < min_train + horizon:
            overgeslagen.append(naam)
            continue
        resultaat = evalueer(reeks, basis, naam=naam, min_train=min_train,
                             stap=stap, horizon=horizon)
        stappen = per_horizon(reeks, basis, onder=onder, boven=boven,
                              min_train=min_train, stap=stap, horizon=horizon)
        punt = basis(reeks, doeldagen)
        band = band_per_stap(punt, stappen)
        prognoses.append(Categorieprognose(
            categorie=naam,
            aandeel_pct=aandeel,
            wape=resultaat.wape,
            band=band,
            weektotaal=float(punt.sum()),
        ))
    return prognoses, overgeslagen
