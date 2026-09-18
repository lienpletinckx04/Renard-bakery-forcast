"""De sluitingslijst (config/sluitingsdagen.json) van schijf naar Postgres.

    config/sluitingsdagen.json  ->  public.sluitingsdag (bron 'bestand')

Draaien:  make db-sluitingen
Droog:    DROOG=1 make db-sluitingen

WAARVOOR DIT SCRIPT BESTAAT. Eén keer, en dan hopelijk nooit meer: het draagt
de sluitingen die tot nu toe alleen in het bestand stonden over naar de
database, zodat het scherm Sluitingsdagen met een gevulde kalender begint.
Vanaf dat moment schrijft het scherm rechtstreeks naar dezelfde tabellen
(migratie 012), en is dit script alleen nog gereedschap voor een herstel.

WAAROM HET WEIGERT ALS DE DATABASE AL GEVULD IS. Het schrijfpatroon is alles
weg, dan alles erin — en "alles" is hier de invoer die een beheerder op het
scherm heeft gedaan. Dit script over een gevulde kalender heen draaien zou
bevestigde feestdagen en eigen periodes wissen omdat er op déze machine een
ouder bestand staat. Wie dat écht wil (herstel na een vergissing), zegt het
expliciet met FORCEER=1.

WAAROM HET GEEN DEEL VAN DE NACHTKETTING IS. Zelfde argument als bij
`kostenmodel_laad.py`: het bestand is een bron zolang de database er geen is;
daarna is de database de bron, en het overzetten is een bewuste handeling van
een mens.

Dit script print aantallen en datums van de zaak (openingsdagen zijn geen
klantdata), maar geen redenen: een terminal-uitvoer is geen plek waar meer
hoeft te staan dan nodig.
"""

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bakkerij import sluitingsdagen
from bakkerij.db import droge_modus, laden
from bakkerij.db import sluitingen_db as sldb
from bakkerij.db.verbinding import dsn_uit_omgeving, verbind
from bakkerij.omgeving import laad_env
from bakkerij.sluitingskalender import Uitspraak

SLUITINGEN_PAD = REPO / "config" / "sluitingsdagen.json"


def main() -> int:
    laad_env()
    droog = droge_modus()
    forceer = os.environ.get("FORCEER") == "1"

    try:
        lijst = sluitingsdagen.lees_sluitingen(SLUITINGEN_PAD)
    except (ValueError, TypeError) as fout:
        print(f"GEBLOKKEERD -- {fout}", file=sys.stderr)
        return 1

    print("=" * 64)
    print("SLUITINGSLIJST NAAR POSTGRES" + ("  (DROOG)" if droog else ""))
    print("=" * 64)

    if not lijst:
        print(f"  geen invoer gevonden ({SLUITINGEN_PAD.name} is leeg of "
              "bestaat niet).")
        print("\nEr is niets te schrijven. De database blijft zoals ze is.")
        return 0

    per_dag = sluitingsdagen.dagen_met_reden(lijst)
    uitspraken = tuple(
        Uitspraak(datum=dag, toestand="dicht", reden=reden, bron="bestand")
        for dag, reden in sorted(per_dag.items())
    )
    print(f"  periodes             : {len(lijst)}")
    print(f"  dagen (alle 'dicht') : {len(uitspraken)}")
    print(f"  bereik               : {uitspraken[0].datum} t/m "
          f"{uitspraken[-1].datum}")

    if droog:
        print("\nDROOG=1: gelezen en getoetst, er is niets geschreven en geen "
              "verbinding gelegd.")
        return 0

    try:
        dsn_uit_omgeving()
    except ValueError as fout:
        print(f"\n{fout}", file=sys.stderr)
        return 1

    with verbind() as verbinding:
        bestaand = sldb.lees(verbinding)
        if bestaand is not None and not forceer:
            print(f"\nGEBLOKKEERD -- de database draagt al een "
                  f"sluitingskalender ({len(bestaand.uitspraken)} uitspraken, "
                  f"{len(bestaand.regels)} regels, laatst bewaard door "
                  f"{bestaand.bewaard_door or '(onbekend)'}). Dit script zou "
                  "die invoer wissen. Wie dat echt wil: FORCEER=1.",
                  file=sys.stderr)
            return 1

        run_id = laden.start_run(verbinding, "sluitingen")
        try:
            aantal = sldb.schrijf(verbinding, uitspraken, (),
                                  "sluitingen_laad.py")
            verbinding.commit()
        except Exception as fout:
            verbinding.rollback()
            laden.eind_run(verbinding, run_id, "fout",
                           melding=f"{type(fout).__name__}: {fout}"[:500])
            raise
        laden.eind_run(verbinding, run_id, "goed", rijen=aantal)

    print(f"\nKlaar. {aantal} dagen geschreven, run {run_id} afgesloten als "
          "'goed'.")
    print("Draai daarna `make canoniek` en `make contract` met "
          "CONTRACT_BRON=db (of de nachtelijke sync) zodat de prognose de "
          "kalender ziet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
