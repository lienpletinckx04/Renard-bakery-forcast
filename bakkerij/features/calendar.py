"""Kalenderkenmerken. Bij een bakkerij is de kalender het sterkste signaal.

Wat hier expliciet ingaat, hoeft het model niet zelf te ontdekken. Dat is het
hele argument om geen zwaar model te gebruiken op een kort dataveld: zet de
bekende structuur erin en er blijft weinig te leren over.
"""

from __future__ import annotations

import datetime as dt

import holidays
import pandas as pd

from bakkerij.features import vakanties

WEEKDAGNAMEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag",
                "zaterdag", "zondag"]


def _belgische_feestdagen(jaren: list[int]) -> dict[dt.date, str]:
    # Geen vangnet meer rond deze aanroep. Tot 18 augustus 2026 ving een brede
    # except álles, en dan bouwde de kalender stil verder zonder één feestdag —
    # ook als alleen de `language`-kwarg was gewijzigd. holidays staat vast in
    # requirements.txt, dus falen hier is een kapotte omgeving en hoort luid.
    return dict(holidays.Belgium(years=jaren, language="nl"))


def kalender(start: str | dt.date, eind: str | dt.date) -> pd.DataFrame:
    """Bouw de kalendertabel voor het hele bereik.

    Kolommen: datum, weekdag, is_weekend, feestdag, feestdagnaam,
    dag_voor_feestdag, dag_na_feestdag, brugdag, maand, weeknr, dag_van_jaar.
    """
    dagen = pd.date_range(start, eind, freq="D")
    # De buurjaren gaan mee: dag_voor/dag_na kijken één dag buiten het bereik,
    # en de randdag van een jaargrens heeft zijn buurfeestdag anders niet
    # (31 december is de dag vóór Nieuwjaar, ook als het bereik daar stopt).
    jaren = sorted({j for d in dagen for j in (d.year - 1, d.year, d.year + 1)})
    feestdagen = _belgische_feestdagen(jaren)
    feestdata = set(feestdagen)

    df = pd.DataFrame({"datum": dagen})
    df["weekdag"] = df["datum"].dt.dayofweek
    df["weekdagnaam"] = df["weekdag"].map(lambda i: WEEKDAGNAMEN[i])
    df["is_weekend"] = df["weekdag"] >= 5
    df["feestdag"] = df["datum"].dt.date.map(lambda d: d in feestdata)
    df["feestdagnaam"] = df["datum"].dt.date.map(lambda d: feestdagen.get(d, ""))
    # Op datumrekenkunde en niet met shift(): shift is positiegebaseerd en dus
    # alleen correct op een aaneengesloten dagreeks. Die eis verviel hier op
    # 18 augustus 2026, zodat een latere wijziging aan `dagen` hem niet stil
    # kan breken.
    een_dag = dt.timedelta(days=1)
    df["dag_voor_feestdag"] = df["datum"].dt.date.map(
        lambda d: d + een_dag in feestdata)
    df["dag_na_feestdag"] = df["datum"].dt.date.map(
        lambda d: d - een_dag in feestdata)

    # Brugdag: werkdag die klem zit tussen een feestdag en een weekend. Andere
    # winkelpatronen dan een gewone werkdag, en makkelijk te missen.
    df["brugdag"] = (
        ~df["feestdag"]
        & ~df["is_weekend"]
        & (
            (df["weekdag"].eq(0) & df["dag_voor_feestdag"])
            | (df["weekdag"].eq(4) & df["dag_na_feestdag"])
        )
    )

    df["maand"] = df["datum"].dt.month
    df["weeknr"] = df["datum"].dt.isocalendar().week.astype(int)
    df["dag_van_jaar"] = df["datum"].dt.dayofyear
    return df


# Schoolvakanties zijn niet in `holidays` gevat en verschuiven per jaar. Ze
# hebben een groot effect op een bakkerij: andere ochtendspits, andere
# weekendpiek. Sinds de hervorming van 2022 lopen de twee gemeenschappen
# bovendien niet meer gelijk — in Elsene leven beide regimes door elkaar, en
# wélk regime het koopgedrag stuurt is open punt O10 (vraag 47). Daarom
# allebei, elk empirisch te toetsen in de backtest.
#
# Sinds 14 augustus 2026 zijn de periodes data in plaats van code: ze staan in
# `schoolvakanties.json` naast deze module (publieke data, in de repo, dekking
# 2019 tot en met minstens schooljaar 2026-27) en worden bijgewerkt door
# `scripts/vakanties_ververs.py` — verversbaar, niet zelfwijzigend: nieuwe
# toekomstige periodes gaan er automatisch in, wijzigingen die het verleden
# raken vragen een expliciete `--forceer`. Zie bakkerij/features/vakanties.py.
SCHOOLVAKANTIES_VL: dict[str, tuple[str, str]] = vakanties.regime_tabel("VL")
SCHOOLVAKANTIES_FR: dict[str, tuple[str, str]] = vakanties.regime_tabel("FR")

# Het alias `SCHOOLVAKANTIES` (= VL) is op 18 augustus 2026 verwijderd: het
# was het stille default van `markeer_schoolvakanties` en koos daarmee een
# kant in open punt O10, terwijl de backtest empirisch FR aanwijst. Wie
# markeert, kiest nu zelf en zichtbaar een regime.


def overgangsdagen(
    open_dagen: pd.DatetimeIndex,
    periodes: dict[str, tuple[str, str]],
    n: int = 3,
) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    """(na, voor): de eerste `n` open dagen ná elke vakantieperiode en de
    laatste `n` open dagen ervóór.

    Open dagen zijn dagen waarop de winkel werkelijk open is (of gepland
    open, voor de toekomst); kalenderdagen in een sluitingsweek tellen niet
    mee. De kenmerken volgen volledig uit de datum en de publieke
    vakantietabel, dus dit lekt geen toekomst. De ná-dagen dragen sinds
    14 augustus 2026 de heropeningscorrectie in de productievoorspeller:
    de diagnose (blok 23) mat daar de zwakste plek van het model (21% WAPE,
    structureel te laag), en de correctie won haar deelvenster in de
    backtest zonder elders te schaden.
    """
    idx = pd.DatetimeIndex(sorted(open_dagen))
    na: set[pd.Timestamp] = set()
    voor: set[pd.Timestamp] = set()
    for van, tot in periodes.values():
        na.update(idx[idx > pd.Timestamp(tot)][:n])
        voor.update(idx[idx < pd.Timestamp(van)][-n:])
    return pd.DatetimeIndex(sorted(na)), pd.DatetimeIndex(sorted(voor))


def markeer_schoolvakanties(
    df: pd.DataFrame,
    vakanties: dict[str, tuple[str, str]],
) -> pd.DataFrame:
    """Voeg de kolom `schoolvakantie` toe volgens het gekozen regime.

    Het regime is sinds 18 augustus 2026 verplicht (voorheen viel het stil
    terug op VL): welk regime het koopgedrag stuurt is open punt O10, en zo'n
    open punt beantwoord je niet met een default.
    """
    bereik = vakanties
    df = df.copy()
    df["schoolvakantie"] = False
    df["vakantienaam"] = ""
    for naam, (van, tot) in bereik.items():
        masker = (df["datum"] >= pd.Timestamp(van)) & (df["datum"] <= pd.Timestamp(tot))
        df.loc[masker, "schoolvakantie"] = True
        df.loc[masker, "vakantienaam"] = naam
    return df
