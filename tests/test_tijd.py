"""bakkerij/tijd.py: de conversie van Odoo-momenten (UTC) naar Belgische dagen.

De randgevallen hieronder zijn precies de gevallen waarin de oude, foute
lezing (UTC-datum afknippen) een ándere dag opleverde: een avondmoment vlak
voor middernacht UTC. Alle waarden verzonnen; geen klantdata.
"""
import datetime as dt

from bakkerij.tijd import BRUSSEL, brussels_moment, brusselse_dag


def test_zomeravond_utc_wordt_de_volgende_belgische_dag():
    # 30 juni 22:30 UTC = 1 juli 00:30 in Brussel (CEST, UTC+2).
    assert brusselse_dag("2025-06-30 22:30:00") == dt.date(2025, 7, 1)


def test_winteravond_utc_wordt_de_volgende_belgische_dag():
    # 15 januari 23:30 UTC = 16 januari 00:30 in Brussel (CET, UTC+1).
    assert brusselse_dag("2025-01-15 23:30:00") == dt.date(2025, 1, 16)


def test_middag_blijft_dezelfde_dag():
    assert brusselse_dag("2025-06-30 12:00:00") == dt.date(2025, 6, 30)


def test_winteravond_voor_de_grens_blijft_dezelfde_dag():
    # 22:30 UTC in de winter is 23:30 in Brussel: nog dezelfde dag.
    assert brusselse_dag("2025-01-15 22:30:00") == dt.date(2025, 1, 15)


def test_moment_is_tijdzonebewust_en_brussels():
    moment = brussels_moment("2025-06-30 22:30:00")
    assert moment.tzinfo is not None
    assert moment.utcoffset() == dt.timedelta(hours=2)
    assert moment.tzinfo == BRUSSEL or str(moment.tzinfo) == "Europe/Brussels"


def test_reeds_tijdzonebewuste_waarde_wordt_gerespecteerd():
    # Een waarde die al een zone draagt wordt niet nog eens verschoven:
    # 23:30 Brussels blijft 30 juni, terwijl 23:30 UTC 1 juli zou worden.
    al_brussels = dt.datetime(2025, 6, 30, 23, 30, tzinfo=BRUSSEL)
    assert brusselse_dag(al_brussels.isoformat()) == dt.date(2025, 6, 30)
    assert brusselse_dag("2025-06-30 23:30:00") == dt.date(2025, 7, 1)


def test_microseconden_worden_genegeerd():
    assert brusselse_dag("2025-03-30 01:30:00.123456") == dt.date(2025, 3, 30)
