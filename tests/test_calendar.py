"""Tests voor de kalenderkenmerken (features/calendar.py).

Geschreven op 18 augustus 2026, toen het stille vangnet rond `holidays`
verdween: sindsdien is een kalender zonder feestdagen een kapotte omgeving in
plaats van een stil gat, en horen de vlaggen zelf een test te hebben. De
schoolvakantiekant van dezelfde module wordt in test_vakanties.py getest.
"""

import pandas as pd

from bakkerij.features.calendar import kalender


def _rij(df: pd.DataFrame, datum: str) -> pd.Series:
    rij = df[df["datum"] == pd.Timestamp(datum)]
    assert len(rij) == 1, f"{datum} hoort precies één keer in de kalender te staan"
    return rij.iloc[0]


def test_kerstmis_is_een_feestdag_met_naam():
    df = kalender("2025-12-01", "2025-12-31")
    kerst = _rij(df, "2025-12-25")
    assert bool(kerst["feestdag"]) is True
    assert kerst["feestdagnaam"] != ""
    gewone = _rij(df, "2025-12-02")
    assert bool(gewone["feestdag"]) is False
    assert gewone["feestdagnaam"] == ""


def test_dag_voor_en_dag_na_feestdag_om_kerstmis_heen():
    df = kalender("2025-12-01", "2025-12-31")
    assert bool(_rij(df, "2025-12-24")["dag_voor_feestdag"]) is True
    assert bool(_rij(df, "2025-12-26")["dag_na_feestdag"]) is True
    assert bool(_rij(df, "2025-12-22")["dag_voor_feestdag"]) is False
    assert bool(_rij(df, "2025-12-22")["dag_na_feestdag"]) is False


def test_brugdag_vrijdag_na_hemelvaart():
    # Hemelvaart 2025 valt op donderdag 29 mei; vrijdag 30 mei zit klem
    # tussen de feestdag en het weekend.
    df = kalender("2025-05-01", "2025-06-15")
    assert bool(_rij(df, "2025-05-29")["feestdag"]) is True
    assert bool(_rij(df, "2025-05-30")["brugdag"]) is True
    # Een gewone vrijdag is geen brugdag.
    assert bool(_rij(df, "2025-05-16")["brugdag"]) is False


def test_brugdag_maandag_voor_een_dinsdagfeestdag():
    # Wapenstilstand 2025 valt op dinsdag 11 november: maandag 10 november
    # zit klem tussen het weekend en de feestdag.
    df = kalender("2025-11-01", "2025-11-30")
    assert bool(_rij(df, "2025-11-11")["feestdag"]) is True
    assert bool(_rij(df, "2025-11-10")["brugdag"]) is True
    # De feestdag zelf is geen brugdag.
    assert bool(_rij(df, "2025-11-11")["brugdag"]) is False


def test_weeknr_is_de_isoweek_ook_over_de_jaargrens():
    df = kalender("2025-12-20", "2026-01-10")
    assert int(_rij(df, "2025-12-25")["weeknr"]) == 52
    # Maandag 29 december 2025 hoort al bij ISO-week 1 van 2026.
    assert int(_rij(df, "2025-12-29")["weeknr"]) == 1
    assert int(_rij(df, "2026-01-01")["weeknr"]) == 1


def test_de_randdag_ziet_zijn_buurfeestdag_buiten_het_bereik():
    # Tot 18 augustus 2026 kwamen de vlaggen uit shift() en was de rand van
    # het bereik blind voor een feestdag er net buiten: 31 december is de dag
    # vóór Nieuwjaar, ook als het bereik op 31 december stopt.
    df = kalender("2025-12-01", "2025-12-31")
    assert bool(_rij(df, "2025-12-31")["dag_voor_feestdag"]) is True
    df2 = kalender("2026-01-02", "2026-01-31")
    assert bool(_rij(df2, "2026-01-02")["dag_na_feestdag"]) is True
