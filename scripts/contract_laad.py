"""De gebouwde contractantwoorden naar Postgres schrijven.

    platform/contract/**.json  ->  public.contract_antwoord (migratie 006)

Draaien:  make db-contract
Droog:    make db-contract-droog

Dit is de laatste stap van de nachtelijke ketting: na de contractbouw gaan
de antwoorden — bit voor bit dezelfde JSON als de bestanden — naar de tabel
waar het platform ze met CONTRACT_BRON=db leest. Zonder die vlag leest het
platform de bestanden en doet deze tabel niets; dat is de garantie waarop
alle voorbereiding tot S11 rust.

De droge modus leest en valideert de volledige boom (beide talen, alle
winkels) en telt wat er geschreven zou worden, zonder verbinding en zonder
sleutel. Precies de fouten die niets met de verbinding te maken hebben — een
ontbrekend scherm, kapotte JSON, een winkelmap buiten de index — vallen daar
al om.

Het schrijven is één transactie: alles weg, alles erin (zie het commentaar
bij VERWIJDER_SQL in bakkerij/db/contract_rijen.py — een verdwenen winkel
moet ook uit de database verdwijnen). Elke run schrijft een rij in etl_run
(bron 'contract'), dezelfde dodemansknop als de rest van de ketting.

Dit script print aantallen per taal. Nooit inhoud, nooit klantdata.
"""

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bakkerij.db import contract_rijen, droge_modus, laden
from bakkerij.db.verbinding import dsn_uit_omgeving, verbind
from bakkerij.omgeving import laad_env

CONTRACT = REPO / "platform" / "contract"

#: Ontsnapping voor de krimpwacht hieronder, voor beide helften: verdwenen
#: sleutels én armer geworden antwoorden. Bewust een omgevingsvariabele en geen
#: vlag in de Makefile: krimp hoort een bewuste, eenmalige handeling van een
#: mens te zijn, en niet iets dat in een make-doel kan inslijten.
KRIMP_TOEGESTAAN = os.environ.get("CONTRACT_KRIMP_OK") == "1"

#: Hoeveel gevallen de melding voluit noemt. Daarboven volgt "+n meer": een
#: gefaalde run met veertien identieke regels leest niemand uit.
MAXIMUM_GETOOND = 5


def _kort(regels: list[str]) -> str:
    """Een leesbare opsomming, zonder inhoud.

    Alleen scherm, taal, winkelslug, kanaalnaam en veldnaam -- machinewaarden
    uit het contract, geen klantdata. De JSON zelf komt hier nooit in.
    """
    getoond = ", ".join(regels[:MAXIMUM_GETOOND])
    rest = len(regels) - MAXIMUM_GETOOND
    return getoond + (f", +{rest} meer" if rest > 0 else "")


def _sleutels_kort(sleutels: set[tuple[str, str, str]]) -> str:
    return _kort([
        f"{scherm}/{taal}" + (f"/{winkel}" if winkel else "")
        for scherm, taal, winkel in sorted(sleutels)
    ])


def main() -> int:
    laad_env()
    droog = droge_modus()

    try:
        rijen = contract_rijen.verzamel(CONTRACT)
    except (FileNotFoundError, ValueError, TypeError) as fout:
        print(f"GEBLOKKEERD -- {fout}", file=sys.stderr)
        return 1

    print("=" * 64)
    print("CONTRACT NAAR POSTGRES" + ("  (DROOG)" if droog else ""))
    print("=" * 64)
    for taal in sorted({r.taal for r in rijen}):
        deel = [r for r in rijen if r.taal == taal]
        winkels = sorted({r.winkel for r in deel if r.winkel})
        print(f"  taal {taal}: {len(deel):>3} antwoorden"
              + (f", {len(winkels)} winkel(s)" if winkels else ""))
    print(f"  totaal {len(rijen)} rijen voor contract_antwoord")

    # Wat de wacht straks weegt, hardop -- óók droog. Een bouwer die hier
    # 'winkel' ziet staan waar 'deliveroo, winkel' hoort, weet vóór het
    # schrijven dat zijn omgeving een bron mist; anders leert hij het pas van
    # een geweigerde nachtrun.
    rijkdommen = [contract_rijen.rijkdom_uit_json(r.antwoord) for r in rijen]
    bronnen = sorted({b for r in rijkdommen for b in r.bronnen})
    mist = sorted({v for r in rijkdommen for v in r.ontbrekende_invoer})
    print(f"  bronnen in de antwoorden: {', '.join(bronnen) or 'geen'}")
    if mist:
        print(f"  invoer die ontbreekt: {', '.join(mist)}")

    if droog:
        print("\nDROOG=1: gelezen en gevalideerd, er is niets geschreven "
              "en geen verbinding gelegd.")
        return 0

    try:
        dsn_uit_omgeving()
    except ValueError as fout:
        print(f"\n{fout}", file=sys.stderr)
        return 1

    with verbind() as verbinding:
        run_id = laden.start_run(verbinding, "contract")
        try:
            with verbinding.cursor() as cur:
                # De krimpwacht, vóór het verwijderen. Zie
                # contract_rijen.ontbrekende_sleutels en .verarming voor het
                # waarom: een runner zonder data/config/ bouwt een verarmd
                # contract en schrijft dat anders met succes over het goede
                # heen. Twee helften, want een verarmde bouw kan even goed
                # álle sleutels leveren met minder erin.
                cur.execute(contract_rijen.BESTAANDE_RIJKDOM_SQL)
                bestaand_rijk = {
                    (s, t, w): contract_rijen.rijkdom_uit_velden(bron, onb)
                    for s, t, w, bron, onb in cur.fetchall()
                }
                nieuw_rijk = {
                    (r.scherm, r.taal, r.winkel):
                        contract_rijen.rijkdom_uit_json(r.antwoord)
                    for r in rijen
                }

                verdwijnt = contract_rijen.ontbrekende_sleutels(
                    set(bestaand_rijk), set(nieuw_rijk)
                )
                armer = contract_rijen.verarming(bestaand_rijk, nieuw_rijk)

                if (verdwijnt or armer) and not KRIMP_TOEGESTAAN:
                    verbinding.rollback()
                    delen = []
                    if verdwijnt:
                        delen.append(
                            f"{len(verdwijnt)} antwoord(en) zouden verdwijnen "
                            f"({_sleutels_kort(verdwijnt)})"
                        )
                    if armer:
                        delen.append(
                            f"{len(armer)} antwoord(en) worden armer "
                            f"({_kort([v.beschrijf() for v in armer])})"
                        )
                    melding = "; ".join(delen) + ". Geweigerd."
                    laden.eind_run(verbinding, run_id, "fout", melding=melding[:500])
                    print(f"\nGEBLOKKEERD -- {melding}\n\n"
                          "Dit is de wacht tegen een verarmde bouw: een omgeving "
                          "zonder data/config/ bouwt minder schermen, of "
                          "dezelfde schermen met een kanaal of het kostenmodel "
                          "eruit -- en dat zou hier het volledige contract "
                          "vervangen.\n"
                          "Klopt de krimp wel (een winkel is echt uit de "
                          "indeling gehaald, een kanaal is echt gestopt), draai "
                          "dan met CONTRACT_KRIMP_OK=1.",
                          file=sys.stderr)
                    return 1

                cur.execute(contract_rijen.VERWIJDER_SQL)
                cur.executemany(
                    contract_rijen.INVOEG_SQL,
                    [(r.scherm, r.taal, r.winkel, r.antwoord) for r in rijen],
                )
            verbinding.commit()
        except Exception as fout:
            verbinding.rollback()
            # Leesbaar voor elke ingelogde gebruiker: alleen het type en de
            # tekst van de fout, nooit een rij uit het contract.
            laden.eind_run(verbinding, run_id, "fout",
                           melding=f"{type(fout).__name__}: {fout}"[:500])
            raise
        laden.eind_run(verbinding, run_id, "goed", rijen=len(rijen))

    print(f"\nKlaar. {len(rijen)} antwoorden geschreven, "
          f"run {run_id} afgesloten als 'goed'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
