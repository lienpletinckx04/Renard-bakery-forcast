"""Maakt de postbus leeg: wat het platform opgeladen kreeg, hier ophalen.

WAAROM DIT SCRIPT BESTAAT

Sinds 28 augustus 2026 kan een beheerder op het scherm `/deliveroo` een export
opladen. Die belandt in `bron_upload` (migratie 015) en blijft daar staan: het
platform ontleedt niets, want het kent de vorm van een Deliveroo-export niet en
hoort die ook niet te kennen. Zonder dit script is de postbus een brievenbus
die niemand leegt.

DRIE HANDELINGEN, EN ZE ZIJN MET OPZET GESCHEIDEN

    overzicht  (standaard)  wat ligt er, wat wacht er. Schrijft niets.
    --haal                  de wachtende bestanden naar de schijf, zodat een
                            mens of een parser ze lokaal kan bekijken. Vinkt
                            NIETS af: ophalen is geen verwerken.
    --verwerk               de bestanden door de lezer halen en de uitkomst
                            terugschrijven.

Dat `--haal` niets afvinkt, is de belangrijkste van de drie regels. Wie een
bestand ophaalt om ernaar te kijken, heeft het niet verwerkt, en een postbus
die leegloopt zodra iemand meekijkt verliest werk dat niemand mist.

WAT ER VANDAAG GEBEURT ALS JE `--verwerk` DRAAIT

Niets, en dat is de juiste uitkomst. Er is nog geen lezer geregistreerd, omdat
`parse_items_sold` en `parse_orders` bewust wachten op een echte export (zie
`docs/plan-deliveroo-parser.md`). De wachtende bestanden blijven staan met de
uitkomst `nog-niet-leesbaar`. Ze worden niet als mislukt afgevinkt: dat zou
iets zeggen over het bestand, terwijl het iets zegt over ons.

WAT DIT NIET DOET

Het schrijft niets naar `data/interim` en het raakt het canonieke model niet
aan. Zodra een lezer bestaat, is die verantwoordelijk voor wat er met de
inhoud gebeurt; dit script is het transport en de boekhouding eromheen. De lus
zelf staat in `bakkerij/db/uploads.py`, waar ze getest kan worden.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bakkerij.db import droge_modus, laden
from bakkerij.db import uploads as up
from bakkerij.db.verbinding import verbind
from bakkerij.omgeving import laad_env

#: Waar `--haal` de bestanden neerzet. Bewust NIET in de mappenconventie
#: `data/raw/Deliveroo/<vanaf>_<tot>/`: die draagt het bereik van de download in
#: de mapnaam, en dat bereik weet de postbus niet. Wie een opgehaald bestand in
#: die keten wil, geeft het zelf de juiste map -- dan is dat een bewuste
#: handeling en geen gok van een script.
POSTBUSMAP = Path("data/raw/postbus")

#: bron -> functie die de bytes leest. LEEG, en dat is de huidige stand.
#:
#: Hier komt `deliveroo` te staan op de dag dat `parse_items_sold` en
#: `parse_orders` gevuld zijn. De functie krijgt de bytes en de `Upload` en
#: geeft terug hoeveel regels ze gelezen heeft. Werpt ze `NotImplementedError`,
#: dan blijft de rij in de wachtrij; werpt ze iets anders, dan is het bestand
#: stuk en wordt de rij afgevinkt als mislukt.
LEZERS: dict = {}


def toon_overzicht(verbinding, bron: str) -> int:
    """Wat er in de postbus ligt. Schrijft niets en faalt nergens op."""
    alles = up.lees_alles(verbinding, bron)
    wachtend = [u for u in alles if not u.verwerkt]

    print(f"postbus '{bron}': {len(alles)} oplading(en), "
          f"{len(wachtend)} wachtend")
    if not alles:
        print("  Er is nog niets opgeladen. Het scherm staat op /deliveroo.")
        return 0

    for u in alles:
        if not u.verwerkt:
            stand = "wacht"
        elif u.verwerkt_status == up.GELUKT:
            stand = "gelukt"
        else:
            stand = "MISLUKT"
        maat = f"{u.bytes / 1024:.0f} kB"
        print(f"  [{u.upload_id:>5}] {stand:<8} {u.geladen_op:%Y-%m-%d %H:%M}  "
              f"{maat:>8}  {u.bestandsnaam}")
        if u.verwerkt_status == up.MISLUKT and u.verwerkt_reden:
            print(f"          reden: {u.verwerkt_reden}")
    return len(wachtend)


def haal_op(verbinding, bron: str, droog: bool) -> int:
    """Schrijft de wachtende bestanden naar de schijf. Vinkt niets af."""
    wachtend = up.lees_onverwerkt(verbinding, bron)
    if not wachtend:
        print(f"postbus '{bron}': niets wachtend, er is niets op te halen.")
        return 0

    doel = POSTBUSMAP / bron
    if not droog:
        doel.mkdir(parents=True, exist_ok=True)

    for u in wachtend:
        pad = doel / up.veilige_naam(u.bestandsnaam, u.upload_id)
        if droog:
            print(f"  DROOG: zou {u.bytes} bytes schrijven naar {pad}")
            continue
        inhoud = up.lees_inhoud(verbinding, u.upload_id)
        tijdelijk = pad.with_name(pad.name + ".tmp")
        tijdelijk.write_bytes(inhoud)
        tijdelijk.replace(pad)
        print(f"  {pad}  ({len(inhoud)} bytes)")

    if not droog:
        print(f"\n{len(wachtend)} bestand(en) opgehaald. Er is NIETS "
              "afgevinkt: ophalen is geen\nverwerken, en de wachtrij hoort te "
              "blijven staan tot een lezer haar leest.")
    return len(wachtend)


def toon_verwerking(uitkomsten) -> dict:
    """Drukt af wat `verwerk_wachtrij` teruggaf en telt de uitkomsten."""
    telling = {up.GELUKT: 0, up.MISLUKT: 0, up.NOG_NIET_LEESBAAR: 0}
    for upload, uitkomst in uitkomsten:
        telling[uitkomst] += 1
        print(f"  [{upload.upload_id:>5}] {uitkomst:<18} {upload.bestandsnaam}")

    if telling[up.NOG_NIET_LEESBAAR]:
        print(f"\n{telling[up.NOG_NIET_LEESBAAR]} bestand(en) blijven in de "
              "wachtrij staan: voor die bron is er\nnog geen lezer. Dat is "
              "geen fout van het bestand en wordt dus niet als\nmislukt "
              "genoteerd. Zie docs/plan-deliveroo-parser.md.")
    return telling


def main(argv: list[str] | None = None) -> int:
    ontleder = argparse.ArgumentParser(
        description="Maakt de postbus met opgeladen bronbestanden leeg.",
    )
    ontleder.add_argument(
        "--bron", default="deliveroo", choices=up.BRONNEN,
        help="van welk platform de opladingen komen (standaard: deliveroo)",
    )
    ontleder.add_argument(
        "--haal", action="store_true",
        help="schrijf de wachtende bestanden naar data/raw/postbus/, "
             "zonder ze af te vinken",
    )
    ontleder.add_argument(
        "--verwerk", action="store_true",
        help="haal de wachtende bestanden door de lezer en vink ze af",
    )
    argumenten = ontleder.parse_args(argv)

    laad_env()
    droog = droge_modus()

    with verbind() as verbinding:
        if not (argumenten.haal or argumenten.verwerk):
            toon_overzicht(verbinding, argumenten.bron)
            return 0

        run_id = None if droog else laden.start_run(verbinding, up.ETL_BRON)
        geteld = 0
        try:
            if argumenten.haal:
                geteld += haal_op(verbinding, argumenten.bron, droog)
            if argumenten.verwerk:
                if droog:
                    for u in up.lees_onverwerkt(verbinding, argumenten.bron):
                        print(f"  DROOG: zou oplading {u.upload_id} "
                              f"({u.bestandsnaam}) verwerken")
                else:
                    telling = toon_verwerking(up.verwerk_wachtrij(
                        verbinding, argumenten.bron, LEZERS))
                    geteld += telling[up.GELUKT]
                    if telling[up.MISLUKT]:
                        laden.eind_run(
                            verbinding, run_id, "fout", geteld,
                            f"{telling[up.MISLUKT]} bestand(en) mislukt; "
                            "zie bron_upload.verwerkt_reden",
                        )
                        return 1
        except Exception as fout:
            # Eerst boekhouden, dan doorgooien: een run die sterft zonder
            # afgesloten etl_run-rij is niet te onderscheiden van een run die
            # nooit gestart is, en dat is precies wat die tabel moet zeggen.
            if run_id is not None:
                laden.eind_run(verbinding, run_id, "fout", geteld,
                               f"{type(fout).__name__}: {fout}")
            raise

        if run_id is not None:
            laden.eind_run(verbinding, run_id, "goed", geteld)
    return 0


if __name__ == "__main__":
    sys.exit(main())
