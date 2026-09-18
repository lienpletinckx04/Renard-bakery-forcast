"""Baselines. Bouwen vóór het model, niet erna.

Als het uiteindelijke model deze niet materieel verslaat op de backtest, is dat
het eerlijke resultaat en gaat het zo in het rapport. Voor een bakkerij is
"dezelfde weekdag, laatst gemeten" verrassend sterk, en dat is de baseline die
verslagen moet worden.

WAAROM DEZE MODULE OP DATUMS WERKT EN NIET OP POSITIES

De eerste versie voorspelde `horizon` stappen vooruit en pakte de laatste zeven
rijen van de reeks. Dat is correct zolang de reeks aaneensluitend is, en de
verkoopreeks van deze bakkerij is dat niet: 54 van de 583 gemeten dagen was de
zaak dicht, in blokken van acht dagen (paassluiting), ruim drie weken (zomer) en
losse feestdagen. Vrijwel geen van die blokken is een veelvoud van zeven.

Gemeten op 12 augustus 2026 met een sluiting van drie dagen: drie van de zeven
voorspellingen landden op de verkeerde weekdag. Maandag kreeg de waarde van een
vrijdag (130 tegen 100), dinsdag die van een zaterdag (160 tegen 95 — 68% te
hoog). Positioneel rekenen op een reeks met gaten schuift de weekdag op, en het
weekpatroon is bij een bakkerij nu net het sterkste signaal dat er is.

Daarom neemt elke baseline hier een **expliciete lijst doeldagen** en leidt hij
de weekdag af uit de datum zelf. Er wordt nergens in deze module op positie
gerekend. De beller bepaalt welke dagen voorspeld worden — en die laat de
sluitingsdagen eruit, want op een dag dat de zaak dicht is, is er niets te
voorspellen.
"""

from __future__ import annotations

import pandas as pd


def _controleer(historiek: pd.Series, doeldagen: pd.DatetimeIndex) -> None:
    if not isinstance(historiek.index, pd.DatetimeIndex):
        raise TypeError("De historiek moet een DatetimeIndex hebben.")
    if not isinstance(doeldagen, pd.DatetimeIndex):
        raise TypeError("doeldagen moet een DatetimeIndex zijn.")
    if historiek.empty:
        raise ValueError("Een lege historiek levert geen baseline op.")
    if not historiek.index.is_monotonic_increasing:
        raise ValueError("De historiek moet op datum gesorteerd zijn.")
    if len(doeldagen) and doeldagen.min() <= historiek.index.max():
        raise ValueError(
            "Een doeldag ligt niet ná de historiek. Dat lekt de toekomst: "
            f"laatste historiekdag {historiek.index.max().date()}, "
            f"eerste doeldag {doeldagen.min().date()}."
        )


def naive(historiek: pd.Series, doeldagen: pd.DatetimeIndex) -> pd.Series:
    """Elke dag is als de laatst gemeten dag.

    De zwakste baseline, en juist daarom nuttig: wat hier niet van wegblijft,
    voegt niets toe.
    """
    _controleer(historiek, doeldagen)
    return pd.Series(float(historiek.iloc[-1]), index=doeldagen, name="naive")


def seizoen_naive(historiek: pd.Series, doeldagen: pd.DatetimeIndex) -> pd.Series:
    """Dezelfde weekdag, laatst gemeten.

    Dit is de baseline om te verslaan. Ze vangt het weekdagpatroon volledig, en
    doordat ze per doeldag de weekdag uit de datum haalt, blijft ze correct over
    een sluitingsperiode heen — ongeacht hoe lang die duurde.
    """
    _controleer(historiek, doeldagen)
    laatste_per_weekdag = (
        historiek.groupby(historiek.index.dayofweek).last()
    )
    terugval = float(historiek.median())
    waarden = [
        float(laatste_per_weekdag.get(dag, terugval)) for dag in doeldagen.dayofweek
    ]
    return pd.Series(waarden, index=doeldagen, name="seizoen_naive")


def weekdag_gemiddelde(
    historiek: pd.Series, doeldagen: pd.DatetimeIndex, *, vensters: int = 4
) -> pd.Series:
    """Gemiddelde van de laatste N keer dezelfde weekdag.

    Robuuster dan `seizoen_naive` tegen één toevallig gekke week, trager in het
    oppikken van een echte trendbreuk. Welke van de twee wint, beslist de
    backtest en niet de smaak.
    """
    return _weekdag_samenvatting(
        historiek, doeldagen, vensters=vensters, hoe="mean",
        naam="weekdag_gemiddelde",
    )


def weekdag_mediaan(
    historiek: pd.Series, doeldagen: pd.DatetimeIndex, *, vensters: int = 8
) -> pd.Series:
    """Mediaan van de laatste N keer dezelfde weekdag.

    Toegevoegd omdat deze data uitschieters kent die geen vraagsignaal zijn: een
    feestdag vóór een sluiting, een dag met een groepsbestelling. Een mediaan
    over een langer venster trekt zich daar niets van aan. Of dat hier wint,
    zegt de backtest.
    """
    return _weekdag_samenvatting(
        historiek, doeldagen, vensters=vensters, hoe="median",
        naam="weekdag_mediaan",
    )


def _weekdag_samenvatting(
    historiek: pd.Series,
    doeldagen: pd.DatetimeIndex,
    *,
    vensters: int,
    hoe: str,
    naam: str,
) -> pd.Series:
    _controleer(historiek, doeldagen)
    if vensters < 1:
        raise ValueError("vensters moet minstens 1 zijn.")

    per_weekdag = historiek.groupby(historiek.index.dayofweek).apply(
        lambda s: getattr(s.iloc[-vensters:], hoe)()
    )
    # Zonder enige waarneming voor een weekdag: de mediaan van de hele
    # historiek. Een noodgreep, geen voorspelling — maar een stille NaN zou
    # de backtest breken en een stille nul zou liegen.
    terugval = float(historiek.median())
    waarden = [float(per_weekdag.get(dag, terugval)) for dag in doeldagen.dayofweek]
    return pd.Series(waarden, index=doeldagen, name=naam)


ALLE_BASELINES = {
    "naive": naive,
    "seizoen_naive": seizoen_naive,
    "weekdag_gemiddelde": weekdag_gemiddelde,
    "weekdag_mediaan": weekdag_mediaan,
}
