"""Ververs de schoolvakantiekalender vanaf de OpenHolidays-API.

Verversbaar, niet zelfwijzigend (beslissing 14 augustus 2026):

  * nieuwe periodes in de toekomst gaan er automatisch in, gelogd;
  * hernoemingen zijn cosmetisch en gaan automatisch (het model kijkt naar de
    vlag, niet naar de naam);
  * elke wijziging die het verleden raakt — en dus de trainingskenmerken en
    het getoonde trackrecord verandert — wordt geweigerd zonder `--forceer`;
  * een geschrapte periode ("vervallen") is altijd handwerk.

Zonder wijzigingen is dit een lege run: het bestand blijft byte-voor-byte
ongemoeid, zodat een nachtelijke aanroep geen ruis maakt. Een netwerk- of
bronfout stopt alléén dit script; de contractbouw draait door op het bestand
dat er ligt, en de dekkingswacht in het prognosecontract meldt het eerlijk
wanneer de kalender te kort wordt (harde regel 8).

Gebruik:  python scripts/vakanties_ververs.py [--droog] [--forceer]
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bakkerij.features import vakanties as vk
from bakkerij.tijd import BRUSSEL

#: De historiek begint op 4 juli 2019; verder terug vragen heeft geen zin.
DATA_START = dt.date(2019, 7, 1)

#: Hoe ver vooruit we vragen. De gemeenschappen publiceren één à twee
#: schooljaren vooruit; wat er nog niet is, komt bij een latere run vanzelf.
VOORUIT_DAGEN = 550


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--droog", action="store_true",
                        help="toon wat er zou gebeuren, schrijf niets")
    parser.add_argument("--forceer", action="store_true",
                        help="pas ook wijzigingen toe die het verleden raken")
    args = parser.parse_args()

    vandaag = dt.datetime.now(tz=BRUSSEL).date()
    venster_van = DATA_START
    venster_tot = vandaag + dt.timedelta(days=VOORUIT_DAGEN)

    data = vk.lees()
    try:
        nieuw = vk.haal_periodes(venster_van, venster_tot, vandaag=vandaag)
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as fout:
        print(f"Ophalen mislukt, bestand ongemoeid: {fout}")
        return 1

    alles_toegepast: list[vk.Wijziging] = []
    alles_geweigerd: list[vk.Wijziging] = []
    nieuwe_regimes: dict[str, list[dict]] = {}
    for regime in vk.REGIMES:
        oud = vk.uit_json(data["regimes"][regime])
        wijzigingen = vk.vergelijk(oud, nieuw[regime], regime=regime,
                                   vandaag=vandaag, venster_van=venster_van,
                                   venster_tot=venster_tot)
        lijst, toegepast, geweigerd = vk.pas_toe(oud, wijzigingen,
                                                 forceer=args.forceer)
        nieuwe_regimes[regime] = vk.naar_json(lijst)
        alles_toegepast += toegepast
        alles_geweigerd += geweigerd

    if not alles_toegepast and not alles_geweigerd:
        print(f"Geen wijzigingen; de kalender loopt gelijk met de bron "
              f"(gecontroleerd {vandaag.isoformat()}). Bestand ongemoeid.")
        return 0

    for w in alles_toegepast:
        print(("zou toepassen:  " if args.droog else "toegepast:  ")
              + w.omschrijving())
    for w in alles_geweigerd:
        print("GEWEIGERD (raakt het verleden, gebruik --forceer): "
              + w.omschrijving())

    if args.droog:
        print("Droge run, niets geschreven.")
        return 0

    if alles_toegepast:
        data["regimes"] = nieuwe_regimes
        data["ververst_op"] = vandaag.isoformat()
        vk.schrijf(data)
        print(f"Geschreven: {vk.VAKANTIES_PAD.relative_to(REPO)}. "
              "Draai `make contract` zodat de prognose de nieuwe kalender ziet.")

    if alles_geweigerd:
        print("WAARSCHUWING: er liggen bronwijzigingen aan het verleden te "
              "wachten. Bekijk ze, en pas ze bewust toe met --forceer; daarna "
              "verschuiven backtest en trackrecord, en dat hoort dan in het "
              "dagboek.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
