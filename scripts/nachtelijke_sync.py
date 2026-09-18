"""De nachtelijke sync: Odoo -> canoniek -> Supabase, als één ketting.

    make sync            de echte run (vergt ODOO_* en SUPABASE_DB_URL)
    make sync-droog      dezelfde ketting zonder Odoo en zonder schrijven:
                         canoniek + db-laad in droge modus op de lokale data

De ketting hergebruikt de bestaande stappen en voegt er niets aan toe:

    0. migraties      scripts/db_migreer.py (idempotent; zonder werk een lege
                      run) -- zo kan een nieuwe migratie nooit een nachtelijke
                      run laten omvallen op een kolom die er nog niet is
    1. poortwachter   jongste write_date in Odoo naast de jongste geslaagde
                      run in etl_run; niets gewijzigd -> stoppen (zie
                      bakkerij/db/sync.py voor waarom dit een poortwachter is
                      en geen gedeeltelijk extract)
    2. extract        scripts/odoo_extract.py --vanaf 2025-01-01
    3. canoniek       scripts/canoniek_bouw.py
    4. laden          scripts/db_laad.py (COPY + insert-on-conflict, dus
                      idempotent: twee keer draaien is één keer draaien)
    5. contract       scripts/contract_bouw.py (beide talen)
    6. contract laden scripts/contract_laad.py -> contract_antwoord
                      (migratie 006), waar het platform met CONTRACT_BRON=db
                      leest -- zonder die vlag leest het de bestanden en is
                      deze stap onzichtbaar voor de UI

Bewust NIET in de ketting: odoo_bonnen.py en odoo_laatste_uur.py. Die voeden
fact_bonnen en fact_product_uren (kwaliteitswachters en censurering), niet de
kerncijfers, en ze herlezen anderhalf miljoen bonregels -- dat hoort een
bewuste keuze te zijn zodra de ketting echt nachtelijk draait, geen bijvangst.
Tot die keuze verversen die twee tabellen alleen met de hand (make
extract-bonnen / extract-uren); inspectiepunt 18 aug.

Elke run schrijft één rij in etl_run (bron 'nachtelijke-sync'): gestart,
geslaagd of gefaald, met de reden. Ook een gevallen poortwachter (Odoo
onbereikbaar, sleutel verlopen) laat een 'fout'-rij achter -- anders is een
uitgevallen koppeling niet te onderscheiden van een cron die nooit vuurde.
Een run die halverwege sterft laat een 'bezig'-rij achter; dat is de
dodemansknop die het platform toont.

Dit script print stapnamen en aantallen. Nooit rijen, nooit klantdata.
"""
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bakkerij.db import droge_modus
from bakkerij.db.sync import beslis_sync
from bakkerij.omgeving import laad_env

PY = sys.executable

#: De ketting, in volgorde. Elke stap is een bestaand script dat ook los
#: draait; de sync voegt alleen de volgorde en de logging toe.
STAPPEN = [
    ("extract", [PY, "scripts/odoo_extract.py", "--vanaf", "2025-01-01"]),
    ("canoniek", [PY, "scripts/canoniek_bouw.py"]),
    ("laden", [PY, "scripts/db_laad.py"]),
    ("contract", [PY, "scripts/contract_bouw.py"]),
    ("contract laden", [PY, "scripts/contract_laad.py"]),
]

DROGE_STAPPEN = [
    ("canoniek", [PY, "scripts/canoniek_bouw.py"]),
    ("laden droog", [PY, "scripts/db_laad.py"]),
    ("contract", [PY, "scripts/contract_bouw.py"]),
    ("contract laden droog", [PY, "scripts/contract_laad.py"]),
]


def _draai(naam: str, commando: list[str], omgeving: dict | None = None) -> None:
    print(f"\n=== {naam} ===", flush=True)
    uitkomst = subprocess.run(commando, cwd=REPO, env=omgeving, check=False)
    if uitkomst.returncode != 0:
        raise RuntimeError(f"stap '{naam}' faalde met code {uitkomst.returncode}")


def _jongste_wijziging() -> dt.datetime | None:
    """De jongste write_date over de kassaorders, tijdzonebewust (UTC).

    Eén record, aflopend gesorteerd: dit is de goedkoopst mogelijke vraag aan
    Odoo, en precies genoeg voor de poortwachter.
    """
    from bakkerij.sources.odoo_client import Odoo

    o = Odoo()
    rec = o.search_read("pos.order", [], ["write_date"],
                        limit=1, order="write_date desc")
    if not rec:
        return None
    ruw = str(rec[0]["write_date"])  # Odoo geeft UTC zonder aanduiding
    return dt.datetime.fromisoformat(ruw).replace(tzinfo=dt.UTC)


def _laatste_geslaagde_run(verbinding) -> dt.datetime | None:
    with verbinding.cursor() as cur:
        cur.execute(
            "select gestart_op from public.etl_run "
            "where bron = %s and status = 'goed' "
            "order by gestart_op desc limit 1",
            ("nachtelijke-sync",),
        )
        rij = cur.fetchone()
    return rij[0] if rij else None


def main() -> int:
    laad_env()
    droog = droge_modus()

    if droog:
        # De droge ketting bewijst de volgorde en de voorbereiding op de
        # lokale data, zonder Odoo en zonder database. Dit is wat er vandaag
        # al kan, in afwachting van het databasewachtwoord (S11).
        omgeving = dict(os.environ, DROOG="1")
        for naam, commando in DROGE_STAPPEN:
            _draai(naam, commando, omgeving)
        print("\nDroge sync geslaagd: de ketting staat, alleen de sleutels ontbreken.")
        return 0

    from bakkerij.db import laden
    from bakkerij.db.verbinding import dsn_uit_omgeving, verbind

    dsn = dsn_uit_omgeving()

    # Stap 0, vóór alles wat etl_run aanraakt: het schema bij. Idempotent,
    # en zonder nieuwe migratie een lege run van een seconde.
    _draai("migraties", [PY, "scripts/db_migreer.py"])

    volledig = "--volledig" in sys.argv[1:]

    with verbind(dsn) as verbinding:
        run_id = laden.start_run(verbinding, "nachtelijke-sync")
        laatste = None if volledig else _laatste_geslaagde_run(verbinding)

    # De Odoo-rondgang gebeurt búiten de databaseverbinding (verbind() zegt
    # zelf: gebruik dit kort, de pooler knipt inactieve verbindingen), maar
    # ná start_run: faalt Odoo, dan bestaat de run en kan de fout erop.
    try:
        besluit = beslis_sync(_jongste_wijziging(), laatste)
    except Exception as fout:
        _registreer_fout(dsn, run_id, f"poortwachter: {fout}")
        raise
    print(f"poortwachter: {besluit.reden}")

    if not besluit.draaien:
        with verbind(dsn) as verbinding:
            laden.eind_run(verbinding, run_id, "goed", rijen=0,
                           melding=besluit.reden)
        return 0

    # De ketting zelf loopt buiten elke verbinding: de pooler knipt inactieve
    # verbindingen en het extract duurt lang. db_laad opent zijn eigen.
    try:
        for naam, commando in STAPPEN:
            _draai(naam, commando)
    except Exception as fout:
        _registreer_fout(dsn, run_id, str(fout))
        raise

    # rijen blijft hier leeg: de teltallen per tabel staan bij bron
    # 'canoniek' en 'contract'; deze rij draagt alleen de uitkomst.
    with verbind(dsn) as verbinding:
        laden.eind_run(verbinding, run_id, "goed", melding=besluit.reden)
    print("\nSync geslaagd.")
    return 0


def _registreer_fout(dsn: str, run_id, melding: str) -> None:
    """Schrijf de foutafloop in etl_run zonder de echte fout op te eten.

    Is de database zélf het probleem (pooler weg, verbinding geknipt), dan
    zou een kale verbind() hier een nieuwe exception gooien en de
    oorspronkelijke maskeren -- het logboek toont dan een verbindingsfout
    waar de oorzaak een gevallen extractstap was. Vandaar de eigen try.
    """
    from bakkerij.db import laden
    from bakkerij.db.verbinding import verbind

    try:
        with verbind(dsn) as verbinding:
            laden.eind_run(verbinding, run_id, "fout", melding=melding)
    except Exception as log_fout:  # noqa: BLE001 -- bewust breed: de echte fout gaat vóór
        print(f"kon de fout niet registreren in etl_run: {log_fout}",
              file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
