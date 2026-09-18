"""Verfijningen op de baselines. De backtest beslist, niet de smaak.

Twee kandidaten, elk gericht op een fout die de weekdagbaselines aantoonbaar
maken:

  * `weekdag_niveau` — het weekdagprofiel zit vast aan zijn venster (de
    laatste acht weken) en loopt achter wanneer het omzetniveau verschuift:
    seizoensdrift, een prijsronde, de aanloop naar of uit een vakantie. Dit
    model schaalt het profiel met het recente niveau: dezelfde weekdagvorm,
    maar op de hoogte van de laatste twee weken.

  * `met_feestdagcorrectie` — een feestdag, de dag ervoor en een brugdag
    gedragen zich anders dan hun weekdag belooft, en het weekdagprofiel kan
    dat per constructie niet zien. De factor wordt per kenmerk uit de eigen
    historiek geschat (mediaan van werkelijk/weekdagnorm op zulke dagen) en
    alleen toegepast als er genoeg waarnemingen zijn. De kenmerken volgen
    volledig uit de datum zelf, dus dit lekt geen toekomst.

Beide respecteren het contract van `baseline.py`: expliciete doeldagen,
weekdag uit de datum, nooit op positie rekenen, en de leklatcontrole van
`_controleer`.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from bakkerij.model.baseline import _controleer

Voorspeller = Callable[[pd.Series, pd.DatetimeIndex], pd.Series]

#: Het niveau en elke kalenderfactor blijven binnen deze klem. Een halve of
#: een dubbele dag is een groot effect; wat daarbuiten valt is vrijwel zeker
#: een artefact van een klein venster (een heropening, een halve meetweek) en
#: geen vraagsignaal.
KLEM = (0.5, 2.0)

#: Minder waarnemingen dan dit voor een kalenderkenmerk en de factor blijft 1.
#: Een mediaan over drie feestdagen is een anekdote.
MIN_WAARNEMINGEN = 4


def _klem(waarde: float, grenzen: tuple[float, float] = KLEM) -> float:
    return min(max(waarde, grenzen[0]), grenzen[1])


def _weekdagprofiel(historiek: pd.Series, vensters: int):
    """Weekdag -> basisverwachting: mediaan van de laatste `vensters` keer
    dezelfde weekdag, met de totale mediaan als terugval voor een weekdag
    zonder waarnemingen."""
    per_weekdag = historiek.groupby(historiek.index.dayofweek).apply(
        lambda s: s.iloc[-vensters:].median()
    )
    terugval = float(historiek.median())

    def basis(weekdag: int) -> float:
        return float(per_weekdag.get(weekdag, terugval))

    return basis


def _niveaufactor(historiek: pd.Series, basis, niveau_dagen: int) -> float:
    """De verhouding tussen de werkelijke omzet van de laatste `niveau_dagen`
    open dagen en wat het weekdagprofiel voor diezelfde dagen zegt, geklemd."""
    staart = historiek.iloc[-niveau_dagen:]
    verwacht = sum(basis(dag) for dag in staart.index.dayofweek)
    return _klem(float(staart.sum()) / verwacht) if verwacht > 0 else 1.0


def weekdag_niveau(
    historiek: pd.Series,
    doeldagen: pd.DatetimeIndex,
    *,
    vensters: int = 8,
    niveau_dagen: int = 14,
) -> pd.Series:
    """Weekdagmediaan, geschaald naar het niveau van de laatste twee weken.

    De vorm komt uit de mediaan van de laatste `vensters` keer dezelfde
    weekdag (robuust tegen uitschieters); de hoogte uit de verhouding tussen
    de werkelijke omzet van de laatste `niveau_dagen` open dagen en wat het
    profiel voor diezelfde dagen zegt. In een stabiel regime is die factor 1
    en valt dit model samen met `weekdag_mediaan`.
    """
    _controleer(historiek, doeldagen)
    if vensters < 1 or niveau_dagen < 1:
        raise ValueError("vensters en niveau_dagen moeten minstens 1 zijn.")

    basis = _weekdagprofiel(historiek, vensters)
    niveau = _niveaufactor(historiek, basis, niveau_dagen)

    waarden = [basis(dag) * niveau for dag in doeldagen.dayofweek]
    return pd.Series(waarden, index=doeldagen, name="weekdag_niveau")


def met_feestdagcorrectie(
    basis: Voorspeller,
    kalender: pd.DataFrame,
    *,
    kenmerken: tuple[str, ...],
    min_waarnemingen: int = MIN_WAARNEMINGEN,
    naam: str | None = None,
) -> Voorspeller:
    """Wikkel een voorspeller in een kalendercorrectie.

    `kenmerken` heeft met opzet geen standaardwaarde (19 augustus 2026). Tot
    dan stond hier `("feestdag", "dag_voor_feestdag", "brugdag")` en in
    `opbouw` hieronder `("schoolvakantie",)`: twee functies uit dezelfde module
    die zonder argument een ánder model opleveren, en geen van beide het model
    dat draait (`productie.KENMERKEN`). Dat is hetzelfde defect als in
    `backtest/rolling.py` (zie het commentaar bij MIN_TRAIN daar): geen enkele
    aanroeper liet het argument weg, dus het verschil deed niets — het wachtte
    op de eerste aanroep die dat wél doet, en die zou stil een ander model
    hebben gemeten dan ze dacht. Wie wikkelt, kiest nu expliciet.

    Per kenmerk wordt op de trainingsdagen de mediaan genomen van
    werkelijk / weekdagnorm; die factor vermenigvuldigt de voorspelling op
    doeldagen met datzelfde kenmerk. Valt een doeldag onder twee kenmerken
    (kan bij ketens van feestdagen), dan stapelen de factoren — dat is zeldzaam
    en de klem begrenst het product niet per ongeluk naar iets absurds omdat
    elke factor afzonderlijk geklemd is.

    `kalender` draagt een `datum`-kolom en de booleaanse kenmerkkolommen; de
    kenmerken volgen uit de datum zelf, dus de wikkel lekt geen toekomst.
    """
    aanwezig = [k for k in kenmerken if k in kalender.columns]
    vlaggen = (
        kalender.assign(datum=pd.to_datetime(kalender["datum"]))
        .set_index("datum")[aanwezig]
        .astype(bool)
    )
    modelnaam = naam or "met_feestdagcorrectie"

    def voorspeller(historiek: pd.Series, doeldagen: pd.DatetimeIndex) -> pd.Series:
        voorspeld = basis(historiek, doeldagen).copy()
        factoren = kalenderfactoren(historiek, vlaggen, aanwezig,
                                    min_waarnemingen=min_waarnemingen)
        for kenmerk, factor in factoren.items():
            doelmarkering = vlaggen[kenmerk].reindex(doeldagen, fill_value=False)
            voorspeld[doelmarkering.to_numpy()] *= factor

        return voorspeld.rename(modelnaam)

    return voorspeller


def kalenderfactoren(
    historiek: pd.Series,
    vlaggen: pd.DataFrame,
    kenmerken: list[str],
    *,
    min_waarnemingen: int = MIN_WAARNEMINGEN,
) -> dict[str, float]:
    """De geschatte factor per kalenderkenmerk, uit de eigen historiek.

    Per kenmerk de mediaan van werkelijk / weekdagnorm op de gemarkeerde
    dagen, geklemd; een kenmerk met te weinig waarnemingen krijgt géén factor
    (afwezig in het resultaat betekent: blijft 1). Dit is de rekenkern van
    `met_feestdagcorrectie`, apart benoemd zodat de opbouw op het scherm
    exact dezelfde factoren toont als de voorspeller gebruikt.
    """
    per_weekdag = historiek.groupby(historiek.index.dayofweek).median()
    norm = pd.Series(
        [float(per_weekdag.get(dag, float(historiek.median())))
         for dag in historiek.index.dayofweek],
        index=historiek.index,
    )
    verhouding = historiek / norm.replace(0.0, pd.NA)

    factoren: dict[str, float] = {}
    for kenmerk in kenmerken:
        markering = vlaggen[kenmerk].reindex(historiek.index, fill_value=False)
        waargenomen = verhouding[markering].dropna()
        if len(waargenomen) >= min_waarnemingen:
            factoren[kenmerk] = _klem(float(waargenomen.median()))
    return factoren


def opbouw(
    historiek: pd.Series,
    doeldagen: pd.DatetimeIndex,
    kalender: pd.DataFrame,
    *,
    kenmerken: tuple[str, ...],
    vensters: int = 8,
    niveau_dagen: int = 14,
    min_waarnemingen: int = MIN_WAARNEMINGEN,
) -> pd.DataFrame:
    """De opbouw van elke voorspelde dag: basis × niveau × kalenderfactoren.

    `kenmerken` heeft geen standaardwaarde, om de reden die bij
    `met_feestdagcorrectie` staat. Hier weegt die reden extra: deze functie
    levert de uitleg die de klant op het scherm leest, en een uitleg die stil
    andere kenmerken gebruikt dan de voorspelling, verklaart een getal dat er
    niet staat.

    Dit is de uitleg die een CFO mag opvragen ("waarom staat hier dit
    getal?"), berekend met exact dezelfde helpers als de productievoorspeller
    — de test legt vast dat het product van de kolommen gelijk is aan wat
    `met_feestdagcorrectie(weekdag_niveau, ...)` voorspelt, zodat de uitleg
    nooit een tweede, net iets ander model wordt.

    Kolommen: datum, basis (euro, de weekdagmediaan), niveau (factor),
    kalenderfactor (product van de actieve kenmerken, 1.0 zonder),
    kenmerk (de actieve kenmerknamen, kommagescheiden; leeg zonder),
    verwacht (euro, het product).
    """
    _controleer(historiek, doeldagen)

    basis = _weekdagprofiel(historiek, vensters)
    niveau = _niveaufactor(historiek, basis, niveau_dagen)

    aanwezig = [k for k in kenmerken if k in kalender.columns]
    vlaggen = (
        kalender.assign(datum=pd.to_datetime(kalender["datum"]))
        .set_index("datum")[aanwezig]
        .astype(bool)
    )
    factoren = kalenderfactoren(historiek, vlaggen, aanwezig,
                                min_waarnemingen=min_waarnemingen)

    rijen = []
    for dag in doeldagen:
        dagbasis = basis(dag.dayofweek)
        kalenderfactor = 1.0
        actief = []
        for kenmerk, factor in factoren.items():
            reeks_vlag = vlaggen[kenmerk].reindex([dag], fill_value=False)
            if bool(reeks_vlag.iloc[0]):
                kalenderfactor *= factor
                actief.append(kenmerk)
        rijen.append({
            "datum": dag,
            "basis": dagbasis,
            "niveau": niveau,
            "kalenderfactor": kalenderfactor,
            "kenmerk": ", ".join(actief),
            "verwacht": dagbasis * niveau * kalenderfactor,
        })
    return pd.DataFrame(rijen)
