"""Tests op de migratieplanner en op de echte migraties in de repo.

Ook deze draaien zonder database. Wat hier getoetst wordt is de vangrail: dat
een gewijzigde of verdwenen migratie een fout geeft in plaats van stilte.
"""
import pytest

from bakkerij.db.migratie import (
    MIGRATIEMAP,
    Migratie,
    checksum,
    migratiebestanden,
    plan,
)


def _m(naam: str, sql: str = "select 1") -> Migratie:
    return Migratie(naam, sql)


def _zonder_commentaar(sql: str) -> str:
    """Alleen de uitvoerbare SQL.

    De migraties leggen in commentaar uit waarom ze bepaalde dingen NIET doen
    ("geld in numeric, nooit in double precision"). Een test die op de ruwe
    tekst zoekt, valt over die uitleg -- en dan wordt de vangrail uitgezet
    omdat hij vals alarm geeft, wat erger is dan geen vangrail.
    """
    return "\n".join(
        regel.split("--", 1)[0] for regel in sql.splitlines()
    ).lower()


# --- checksum ---------------------------------------------------------------


def test_checksum_negeert_afsluitende_witruimte():
    """Een editor die een newline toevoegt, wijzigt het schema niet."""
    assert checksum("select 1") == checksum("select 1\n\n  ")


def test_checksum_negeert_regeleindes():
    assert checksum("a\nb") == checksum("a\r\nb")


def test_checksum_ziet_een_echte_wijziging():
    assert checksum("select 1") != checksum("select 2")


def test_checksum_ziet_witruimte_binnenin():
    """Binnenin telt witruimte wel mee: `not null` is niet `notnull`."""
    assert checksum("a b") != checksum("ab")


# --- plan -------------------------------------------------------------------


def test_lege_database_krijgt_alles():
    aanwezig = [_m("001_a.sql"), _m("002_b.sql")]
    assert [m.bestandsnaam for m in plan(aanwezig, {})] == ["001_a.sql", "002_b.sql"]


def test_alles_toegepast_geeft_lege_lijst():
    aanwezig = [_m("001_a.sql")]
    toegepast = {"001_a.sql": aanwezig[0].checksum}
    assert plan(aanwezig, toegepast) == []


def test_alleen_het_nieuwe_wordt_gepland():
    aanwezig = [_m("001_a.sql"), _m("002_b.sql", "select 2")]
    toegepast = {"001_a.sql": aanwezig[0].checksum}
    assert [m.bestandsnaam for m in plan(aanwezig, toegepast)] == ["002_b.sql"]


def test_gewijzigde_toegepaste_migratie_werpt():
    """De belangrijkste vangrail.

    Zonder deze controle draagt de database iets anders dan de repo beweert,
    en dat valt pas maanden later op.
    """
    aanwezig = [_m("001_a.sql", "select 2")]
    with pytest.raises(ValueError, match="inhoud is daarna"):
        plan(aanwezig, {"001_a.sql": checksum("select 1")})


def test_verdwenen_toegepaste_migratie_werpt():
    with pytest.raises(ValueError, match="niet meer in de repo"):
        plan([_m("002_b.sql")], {"001_a.sql": "abc"})


# --- de echte migraties in de repo -----------------------------------------


def test_de_repo_heeft_migraties_en_ze_zijn_leesbaar():
    migraties = migratiebestanden()
    assert migraties, "geen migraties gevonden"
    assert all(m.sql.strip() for m in migraties)


def test_migratienummers_zijn_uniek_en_oplopend():
    namen = [m.bestandsnaam for m in migratiebestanden()]
    nummers = [n.split("_", 1)[0] for n in namen]
    assert nummers == sorted(nummers)
    assert len(set(nummers)) == len(nummers)


def test_dubbel_nummer_werpt(tmp_path):
    (tmp_path / "001_een.sql").write_text("select 1")
    (tmp_path / "001_twee.sql").write_text("select 2")
    with pytest.raises(ValueError, match="nummer 001"):
        migratiebestanden(tmp_path)


def test_lege_map_werpt(tmp_path):
    with pytest.raises(FileNotFoundError):
        migratiebestanden(tmp_path)


def test_elke_tabel_krijgt_rls_in_dezelfde_migratie():
    """Harde eis, geen stijlkwestie.

    In Supabase hangt PostgREST aan de database. Een tabel zonder RLS is
    leesbaar voor iedereen met de publiceerbare sleutel, en die sleutel staat
    per definitie in de JavaScript-bundel. RLS "in een latere migratie" is
    daarmee een venster waarin de omzet van de klant publiek staat.

    De revoke geldt sinds 18 augustus 2026 óók voor authenticated: de
    default privileges van Supabase geven die rol schrijfrechten, en dan is
    RLS de enige laag in plaats van één van twee. De grant select erna geeft
    terug wat wél mag.
    """
    gezien = set()
    for migratie in migratiebestanden():
        sql = migratie.sql.lower()
        tabellen = {
            regel.split("public.")[1].split()[0].rstrip("(")
            for regel in sql.splitlines()
            if "create table" in regel and "public." in regel
        }
        gezien |= tabellen
        for tabel in tabellen:
            assert f"alter table public.{tabel} enable row level security" in sql, (
                f"{migratie.bestandsnaam}: tabel {tabel} krijgt geen RLS"
            )
            assert f"revoke all on public.{tabel} from anon, authenticated" in sql, (
                f"{migratie.bestandsnaam}: tabel {tabel} houdt rechten voor "
                f"anon of authenticated buiten RLS om"
            )

    # De test mag niet stilletjes nul tabellen nakijken en dan groen zijn.
    assert len(gezien) >= 6, f"maar {len(gezien)} tabellen gevonden: {sorted(gezien)}"


def test_de_boekhoudingstabel_krijgt_dezelfde_afscherming():
    """schema_migraties viel tot 18 augustus 2026 buiten de RLS-eis.

    De redenering was "er staat geen klantdata in", maar het argument voor
    RLS is breder: PostgREST hangt aan de database, en een tabel zonder RLS
    is met de publiceerbare sleutel ook schrijfbaar. Rijen wissen laat de
    runner alle migraties opnieuw draaien; een verzonnen checksum laat plan()
    permanent werpen.
    """
    from bakkerij.db.migratie import BOEKHOUDING

    sql = BOEKHOUDING.lower()
    assert "enable row level security" in sql
    assert "force row level security" in sql
    assert "revoke all on public.schema_migraties from anon, authenticated" in sql


def test_elke_policy_is_herhaalbaar():
    """Vóór elke create policy staat een drop policy if exists.

    Postgres kent geen `create policy if not exists`. Via de runner maakt dat
    niet uit (elke migratie draait precies één keer), maar wie een migratie
    ooit met de hand in de SQL-editor plakt, valt anders over een policy die
    al bestaat -- met een foutmelding die nergens naar wijst.
    """
    for migratie in migratiebestanden():
        sql = migratie.sql.lower()
        for blok in sql.split("create policy")[1:]:
            naam = blok.split('"')[1] if '"' in blok else None
            if naam is None:
                continue
            assert f'drop policy if exists "{naam}"' in sql, (
                f"{migratie.bestandsnaam}: policy '{naam}' heeft geen "
                f"drop-vooraf en is dus niet herhaalbaar"
            )


def test_elke_policy_noemt_expliciet_to():
    """Zonder `TO` wordt een policy ook voor anonieme bezoekers geëvalueerd.

    Dat is de eerste van de drie details in stack.md die er echt toe doen, en
    het is precies het soort fout dat je niet ziet door ernaar te kijken: de
    policy staat er, hij is leesbaar, en hij doet iets anders dan je denkt.
    """
    rollen = (" to authenticated", " to service_role", " to authenticator")
    gezien = 0
    for migratie in migratiebestanden():
        sql = migratie.sql.lower()
        for blok in sql.split("create policy")[1:]:
            gezien += 1
            kop = blok.split(";", 1)[0]
            assert any(rol in kop for rol in rollen), (
                f"{migratie.bestandsnaam}: policy zonder expliciete TO -- "
                f"die geldt dan óók voor anonieme bezoekers"
            )

    assert gezien >= 6, f"maar {gezien} policies gevonden"


def test_de_migraties_worden_niet_door_gitignore_geslikt():
    """De vangrail onder "migraties in de repo, geen wijzigingen met de hand".

    `.gitignore` bevat `*.sql` om datadumps buiten te houden, en dat ving op
    13 augustus 2026 ook `db/migraties/` op. Gevolg als dat onopgemerkt bleef:
    de migratielaag wordt gecommit zónder haar migraties. Wie de repo daarna
    kloont krijgt een runner die op FileNotFoundError valt, en een database
    die niemand meer kan herbouwen uit de bron.

    Het is precies het soort fout dat geen enkele test vindt die alleen naar
    Python kijkt, want lokaal werkt alles.
    """
    import shutil
    import subprocess

    if not shutil.which("git"):
        pytest.skip("git niet beschikbaar")

    repo = MIGRATIEMAP.parents[1]
    if not (repo / ".git").exists():
        pytest.skip("geen git-repo")

    paden = [str(MIGRATIEMAP / m.bestandsnaam) for m in migratiebestanden()]
    uitkomst = subprocess.run(
        ["git", "check-ignore", *paden],
        cwd=repo, capture_output=True, text=True, check=False,
    )
    # Exitcode 1 betekent: geen enkel pad wordt genegeerd. Dat is wat we willen.
    assert uitkomst.returncode == 1, (
        "Deze migraties worden door .gitignore genegeerd en komen dus nooit in "
        f"de repo:\n{uitkomst.stdout}"
    )


def test_geen_float_voor_geld_in_het_schema():
    """Geld in numeric, nooit in een drijvendekommagetal.

    De invarianten in de berekeningslaag eisen dat ontbindingen tot op de cent
    optellen. Een `double precision` in de opslag maakt dat onhaalbaar.
    """
    verboden = ("double precision", "float4", "float8", " real ")
    for migratie in migratiebestanden():
        sql = _zonder_commentaar(migratie.sql)
        for woord in verboden:
            assert woord not in sql, f"{migratie.bestandsnaam} gebruikt {woord.strip()}"


def test_geen_klantveld_in_het_schema():
    """Harde regel 3: geen partner_id, klantnaam, adres of bonnotitie.

    Deze test is een vangrail tegen een toekomstige migratie, niet tegen de
    huidige. Wie ooit "even" een klantveld toevoegt, loopt hier tegenaan.
    """
    verboden = ("partner_id", "klantnaam", "customer_name", "adres", "bonnotitie")
    for migratie in migratiebestanden():
        # Het woord mag wél in een toelichting staan die uitlegt dat het er
        # juist NIET in komt -- en dat staat er ook. Alleen de uitvoerbare SQL
        # telt.
        for regel in _zonder_commentaar(migratie.sql).splitlines():
            for veld in verboden:
                assert not regel.strip().startswith(veld), (
                    f"{migratie.bestandsnaam} definieert kolom {veld}"
                )
