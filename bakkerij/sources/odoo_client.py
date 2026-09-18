"""Minimale Odoo XML-RPC client. Alleen stdlib, geen extra dependency.

Credentials komen uit .env in de repo-root. Zie docs/werkafspraken.md voor de
credential-discipline: gescopete key, herkomst genoteerd, roteren bij oplevering.
"""
import os
import xmlrpc.client
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load_env():
    env = REPO / ".env"
    if not env.exists():
        raise SystemExit(f"Geen .env gevonden in {REPO}. Kopieer .env.example en vul aan.")
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


class Odoo:
    def __init__(self):
        _load_env()
        self.url = os.environ.get("ODOO_URL", "").rstrip("/")
        self.db = os.environ.get("ODOO_DB", "")
        self.key = os.environ.get("ODOO_API_KEY", "")
        self.user = os.environ.get("ODOO_USER", "")
        if not all([self.url, self.db, self.key, self.user]):
            raise SystemExit("ODOO_URL, ODOO_DB, ODOO_USER of ODOO_API_KEY ontbreekt in .env")

        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.version = common.version().get("server_version", "?")
        self.uid = common.authenticate(self.db, self.user, self.key, {})
        if not self.uid:
            raise SystemExit(
                f"Authenticatie geweigerd op database '{self.db}'.\n"
                "Meest waarschijnlijk: de databasenaam is veranderd na een rebuild "
                "(gebeurd op 7/8/2026), of de API-sleutel hangt aan een ander account."
            )
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def call(self, model, method, args, **kwargs):
        return self.models.execute_kw(self.db, self.uid, self.key, model, method, args, kwargs)

    def count(self, model, domain=None):
        return self.call(model, "search_count", [domain or []])

    def search_read(self, model, domain, fields, limit=None, offset=0, order=None, load=None):
        kw = {"fields": fields, "offset": offset}
        if limit:
            kw["limit"] = limit
        if order:
            kw["order"] = order
        if load is not None:
            # load='' laat de display_name-berekening op elke many2one weg.
            # Over 1,5 miljoen bonregels is dat het verschil tussen minuten en uren.
            # Je krijgt dan kale id's terug in plaats van [id, "naam"].
            kw["load"] = load
        return self.call(model, "search_read", [domain], **kw)

    def paginate(self, model, domain, fields, batch=5000, load=None):
        """Bladert met een sleutel, niet met een offset.

        `offset=N` laat Odoo N rijen ophalen en weggooien vóór het de volgende
        bladzijde teruggeeft. Over 1,5 miljoen bonregels wordt dat kwadratisch:
        de laatste bladzijde kost dan honderden keren zoveel als de eerste.
        Filteren op `id > laatste` gebruikt de primaire index en kost voor elke
        bladzijde evenveel.

        Voorwaarde: `id` moet niet in het domein voorkomen. Dat is hier zo.
        """
        laatste = 0
        while True:
            rijen = self.search_read(
                model,
                list(domain or []) + [("id", ">", laatste)],
                fields,
                limit=batch,
                order="id asc",
                load=load,
            )
            if not rijen:
                return
            yield from rijen
            laatste = rijen[-1]["id"]


def naam(waarde):
    """Odoo geeft many2one terug als [id, 'naam'] of False."""
    return waarde[1] if isinstance(waarde, (list, tuple)) else ""
