"""Migraties toepassen: in volgorde, één keer, en met een vangrail.

De projectregel is "migraties in de repo, geen wijzigingen met de hand". Dat
werkt alleen als er iets bijhoudt wat er al gedraaid heeft, anders is de
tweede keer draaien even spannend als de eerste.

Het bijhouden gebeurt in `public.schema_migraties`. Naast de bestandsnaam
staat daar een checksum van de inhoud, en dat is de vangrail: wie een
migratie aanpast die al toegepast is, krijgt een fout in plaats van stilte.
Zonder die controle loopt de database uit de pas met de repo op een manier
die pas maanden later opvalt, en dan weet niemand meer welke kolom er nu
eigenlijk in productie staat.

De pure functies (`checksum`, `migratiebestanden`, `plan`) raken de database
niet aan en hebben tests. Alleen `pas_toe` praat met Postgres.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

MIGRATIEMAP = Path(__file__).resolve().parents[2] / "db" / "migraties"

#: De boekhoudingstabel krijgt dezelfde afscherming als elke andere tabel in
#: public: PostgREST hangt aan de database, en zonder RLS is deze tabel met de
#: publiceerbare sleutel niet alleen leesbaar maar ook schrijfbaar. Rijen
#: wissen laat de runner alles opnieuw draaien; een rij met een verzonnen
#: checksum laat plan() permanent werpen. Er is bewust geen select-policy:
#: niemand hoeft deze tabel via PostgREST te zien.
BOEKHOUDING = """
create table if not exists public.schema_migraties (
    bestandsnaam  text        primary key,
    checksum      text        not null,
    toegepast_op  timestamptz not null default now()
);
alter table public.schema_migraties enable row level security;
alter table public.schema_migraties force row level security;
revoke all on public.schema_migraties from anon, authenticated;
"""


@dataclass(frozen=True)
class Migratie:
    """Eén migratiebestand: zijn naam, zijn inhoud, zijn vingerafdruk."""

    bestandsnaam: str
    sql: str

    @property
    def checksum(self) -> str:
        return checksum(self.sql)


def checksum(sql: str) -> str:
    """De vingerafdruk van een migratie.

    Regeleindes worden genormaliseerd en witruimte aan het eind valt weg, want
    een editor die een afsluitende newline toevoegt is geen wijziging aan het
    schema. Alles daarbinnen telt wél mee: een gewijzigde kolom moet opvallen.
    """
    genormaliseerd = sql.replace("\r\n", "\n").replace("\r", "\n").rstrip()
    return hashlib.sha256(genormaliseerd.encode("utf-8")).hexdigest()


def migratiebestanden(map_: Path | None = None) -> list[Migratie]:
    """Lees alle migraties, op naam gesorteerd.

    De volgorde is de bestandsnaam, en daarom beginnen ze met een nummer.
    Sorteren op wijzigingsdatum of op inhoud zou betekenen dat dezelfde repo
    op twee machines een andere volgorde krijgt.
    """
    map_ = map_ or MIGRATIEMAP
    if not map_.is_dir():
        raise FileNotFoundError(f"Migratiemap bestaat niet: {map_}")

    bestanden = sorted(map_.glob("*.sql"), key=lambda p: p.name)
    if not bestanden:
        raise FileNotFoundError(f"Geen migraties gevonden in {map_}")

    nummers: dict[str, str] = {}
    migraties = []
    for pad in bestanden:
        nummer = pad.name.split("_", 1)[0]
        if nummer in nummers:
            raise ValueError(
                f"Twee migraties dragen nummer {nummer}: '{nummers[nummer]}' en "
                f"'{pad.name}'. De volgorde ligt dan niet vast."
            )
        nummers[nummer] = pad.name
        migraties.append(Migratie(pad.name, pad.read_text(encoding="utf-8")))
    return migraties


def plan(
    aanwezig: list[Migratie], toegepast: dict[str, str]
) -> list[Migratie]:
    """Wat moet er nog draaien, gegeven wat er al gedraaid heeft.

    `toegepast` is bestandsnaam -> checksum, zoals het in de database staat.

    Werpt bij twee soorten afwijking, allebei stil-gevaarlijk:

      * een toegepaste migratie waarvan de inhoud gewijzigd is. De database
        draagt dan iets anders dan de repo beweert.
      * een toegepaste migratie die uit de repo verdwenen is. Dan is de
        geschiedenis niet meer na te lopen.
    """
    namen = {m.bestandsnaam for m in aanwezig}

    verdwenen = sorted(set(toegepast) - namen)
    if verdwenen:
        raise ValueError(
            "Deze migraties zijn toegepast op de database maar staan niet meer "
            f"in de repo: {', '.join(verdwenen)}. De geschiedenis klopt niet "
            "meer; zet de bestanden terug of herstel de database uit een "
            "back-up."
        )

    gewijzigd = [
        m.bestandsnaam
        for m in aanwezig
        if m.bestandsnaam in toegepast and toegepast[m.bestandsnaam] != m.checksum
    ]
    if gewijzigd:
        raise ValueError(
            "Deze migraties zijn al toegepast maar hun inhoud is daarna "
            f"gewijzigd: {', '.join(gewijzigd)}. Een toegepaste migratie pas je "
            "niet aan -- schrijf een nieuwe migratie die het verschil maakt."
        )

    return [m for m in aanwezig if m.bestandsnaam not in toegepast]


def _toegepast(verbinding) -> dict[str, str]:
    with verbinding.cursor() as cur:
        cur.execute(BOEKHOUDING)
        cur.execute("select bestandsnaam, checksum from public.schema_migraties")
        return dict(cur.fetchall())


def pas_toe(verbinding, map_: Path | None = None) -> list[str]:
    """Draai alle migraties die nog niet gedraaid hebben.

    Elke migratie krijgt zijn eigen transactie: de boeking gaat samen met de
    wijziging erin of geen van beide. Faalt migratie 3, dan staan 1 en 2 er
    gewoon en begint de volgende run bij 3.

    Geeft de namen terug van wat er toegepast is. Lege lijst betekent: alles
    stond er al, en dat is het normale geval bij de tweede run.
    """
    aanwezig = migratiebestanden(map_)
    verbinding.commit()  # de boekhoudingstabel staat los van de migraties zelf
    te_doen = plan(aanwezig, _toegepast(verbinding))
    verbinding.commit()

    gedaan = []
    for migratie in te_doen:
        with verbinding.cursor() as cur:
            cur.execute(migratie.sql)
            cur.execute(
                "insert into public.schema_migraties (bestandsnaam, checksum) "
                "values (%s, %s)",
                (migratie.bestandsnaam, migratie.checksum),
            )
        verbinding.commit()
        gedaan.append(migratie.bestandsnaam)
    return gedaan
