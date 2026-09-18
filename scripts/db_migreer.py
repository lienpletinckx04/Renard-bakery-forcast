"""Pas de migraties toe op de database uit SUPABASE_DB_URL.

De projectregel is "migraties in de repo, geen wijzigingen met de hand". Dit
script is de enige manier waarop het schema verandert, en het is idempotent:
tweede keer draaien is een lege run, geen tweede keer schema.

Draaien:  make db-migreer
Droog:    make db-migreer DROOG=1     (toont alleen wat er zou draaien)

Dit script print geen verbindingsstring en geen wachtwoord, ook niet bij een
fout. Het print namen van migraties en aantallen, meer niet.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bakkerij.db import droge_modus
from bakkerij.db import migratie as m
from bakkerij.db.verbinding import dsn_uit_omgeving, verbind

# Woonde tot 18 aug 2026 hier als functie; drie andere scripts importeerden
# hem uit dít script, waardoor een hernoeming de nachtketen stil zou breken.
from bakkerij.omgeving import laad_env


def main() -> int:
    laad_env()

    aanwezig = m.migratiebestanden()
    print(f"Migraties in de repo: {len(aanwezig)}")
    for migratie in aanwezig:
        print(f"  {migratie.bestandsnaam}  ({migratie.checksum[:12]})")

    if droge_modus():
        print("\nDROOG=1: er is niets toegepast en er is geen verbinding gelegd.")
        return 0

    try:
        dsn_uit_omgeving()
    except ValueError as fout:
        print(f"\n{fout}", file=sys.stderr)
        return 1

    print()
    with verbind() as verbinding:
        gedaan = m.pas_toe(verbinding)

    if gedaan:
        print(f"Toegepast ({len(gedaan)}):")
        for naam in gedaan:
            print(f"  {naam}")
    else:
        print("Niets te doen: alle migraties stonden er al.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
