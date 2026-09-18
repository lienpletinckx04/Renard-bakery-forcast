"""Eén .env-lezer voor alle scripts.

`python-dotenv` verdient zich hier niet: dit zijn regels van de vorm
SLEUTEL=waarde en meer hebben we niet nodig. Bestaande omgevingsvariabelen
winnen, zodat een CI-secret niet door een achtergebleven .env overschreven
wordt.

Waarom dit een bakkerij-module is en geen scriptfunctie: tot 18 aug 2026
woonde `laad_env` in scripts/db_migreer.py en trokken drie andere scripts
hem daaruit (`from scripts.db_migreer import ...`) — dat werkte alleen via
namespace-packages plus de sys.path-regel bovenaan elk script, en wie
db_migreer hernoemde brak stil de hele nachtketen. De twee lezers in
bakkerij/sources/ (odoo_client, agenda_ophaal) blijven bewust apart: die
hebben andere semantiek (een ontbrekende .env is daar fataal) en zeggen
dat zelf in hun kop.
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def laad_env(pad: Path | None = None) -> None:
    """Lees .env in de repowortel; een ontbrekend bestand is geen fout."""
    pad = pad or (REPO / ".env")
    if not pad.exists():
        return
    for regel in pad.read_text(encoding="utf-8").splitlines():
        regel = regel.strip()
        if not regel or regel.startswith("#") or "=" not in regel:
            continue
        sleutel, waarde = regel.split("=", 1)
        os.environ.setdefault(sleutel.strip(), waarde.strip())
