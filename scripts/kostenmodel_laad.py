"""De beheerinvoer (het kostenmodel) van schijf naar Postgres schrijven.

    data/config/kostenmodel.json  ->  public.kosten_criterium + kosten_waarde
    (of, zonder v2-bestand, het oude data/config/marges.json)

Draaien:  make db-kostenmodel
Droog:    DROOG=1 make db-kostenmodel

WAARVOOR DIT SCRIPT BESTAAT. Eén keer, en dan hopelijk nooit meer: het draagt de
invoer die de beheerder tot nu toe lokaal invulde over naar de database, zodat de
gehoste omgeving en de nachtelijke runner haar ook zien. Vanaf dat moment
schrijft het formulier op Instellingen rechtstreeks naar dezelfde tabellen
(migratie 009), en is dit script alleen nog gereedschap voor een herstel uit een
bestandsback-up.

WAAROM HET GEEN DEEL VAN DE NACHTKETTING IS. Dan zou de nachtrun elke keer het
bestand van de bouwmachine over de invoer van het formulier heen schrijven, en is
de laatste die opsloeg niet degene die je terugleest. Het bestand is een bron
zolang de database er geen is; daarna is de database de bron. Eén bron van
waarheid, en het overzetten is een bewuste handeling van een mens.

Dit script print aantallen. Nooit percentages, nooit groepsnamen -- niet omdat ze
klantdata zijn (dat zijn ze niet), maar omdat een terminal-uitvoer geen plek is
waar bedrijfscijfers hoeven te staan.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bakkerij import kostenmodel as km
from bakkerij.db import droge_modus, laden
from bakkerij.db import kostenmodel_db as kmdb
from bakkerij.db.verbinding import dsn_uit_omgeving, verbind
from bakkerij.omgeving import laad_env

KOSTEN_PAD = REPO / "data" / "config" / "kostenmodel.json"
MARGES_PAD = REPO / "data" / "config" / "marges.json"


def main() -> int:
    laad_env()
    droog = droge_modus()

    try:
        model = km.lees_kostenmodel(KOSTEN_PAD, MARGES_PAD)
    except (ValueError, TypeError) as fout:
        print(f"GEBLOKKEERD -- {fout}", file=sys.stderr)
        return 1

    print("=" * 64)
    print("KOSTENMODEL NAAR POSTGRES" + ("  (DROOG)" if droog else ""))
    print("=" * 64)

    if model is None:
        # Geen invoer is geen fout, maar het is ook geen reden om de tabellen te
        # legen: dan zou dit script de invoer van het formulier wissen omdat er
        # op déze machine geen bestand staat. Precies de verarmde-bouw-val die
        # contract_rijen.ontbrekende_sleutels beschrijft.
        print(f"  geen invoer gevonden ({KOSTEN_PAD.name} noch "
              f"{MARGES_PAD.name} bestaat).")
        print("\nEr is niets te schrijven. De database blijft zoals ze is.")
        return 0

    print(f"  criteria             : {len(model.criteria)}")
    print(f"  groepen met kosten   : {len(model.waarden)}")
    print(f"  ingevulde kosten     : "
          f"{sum(len(rij) for rij in model.waarden.values())}")
    print(f"  ingevuld door        : "
          f"{model.ingevuld_door or '(niet vastgelegd)'}")

    if droog:
        print("\nDROOG=1: gelezen en getoetst, er is niets geschreven en geen "
              "verbinding gelegd.")
        return 0

    try:
        dsn_uit_omgeving()
    except ValueError as fout:
        print(f"\n{fout}", file=sys.stderr)
        return 1

    # `ingevuld_door` uit het bestand is de beheerder die het formulier gebruikte;
    # zonder naam valt het terug op dit script, zodat bewaard_door nooit liegt
    # over wie de invoer heeft aangeleverd.
    door = model.ingevuld_door.strip() or "kostenmodel_laad.py"

    with verbind() as verbinding:
        run_id = laden.start_run(verbinding, "kostenmodel")
        try:
            aantal = kmdb.schrijf(verbinding, model, door)
            verbinding.commit()
        except Exception as fout:
            verbinding.rollback()
            laden.eind_run(verbinding, run_id, "fout",
                           melding=f"{type(fout).__name__}: {fout}"[:500])
            raise
        laden.eind_run(verbinding, run_id, "goed", rijen=aantal)

    print(f"\nKlaar. {len(model.criteria)} criteria en {aantal} kosten "
          f"geschreven, run {run_id} afgesloten als 'goed'.")
    print("Draai daarna `make contract` met CONTRACT_BRON=db (of de nachtelijke "
          "sync) om het margescherm te herrekenen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
