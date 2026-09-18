"""Tests op de verbindingscontrole.

Deze tests raken geen database aan en dragen geen wachtwoord. Dat is met
opzet: de drie valkuilen uit stack.md zijn vormfouten, en een vormfout hoort
gevonden te worden zonder dat er een Supabase-project hoeft te bestaan.
"""
import pytest

from bakkerij.db.verbinding import controleer_dsn, normaliseer_dsn

GOED = (
    "postgresql://postgres.abcdefghijklm:geheim"
    "@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require"
)


def test_een_goede_dsn_heeft_geen_bezwaren():
    assert controleer_dsn(GOED) == []


def test_leeg_wijst_naar_env():
    bezwaren = controleer_dsn("")
    assert len(bezwaren) == 1
    assert "SUPABASE_DB_URL" in bezwaren[0]


def test_ipv6_only_hostnaam_wordt_gevangen():
    """De valkuil die de nachtelijke run stilletjes sloopt.

    `db.<ref>.supabase.co` is IPv6-only en GitHub Actions-runners hebben
    onbetrouwbare IPv6-uitgang. Het symptoom is 'network is unreachable', wat
    naar een firewall wijst en niet naar een hostnaam.
    """
    dsn = (
        "postgresql://postgres:geheim"
        "@db.abcdefghijklm.supabase.co:5432/postgres?sslmode=require"
    )
    bezwaren = controleer_dsn(dsn)
    assert any("IPv6" in b for b in bezwaren)
    assert any("pooler" in b for b in bezwaren)


def test_transaction_mode_poort_wordt_gevangen():
    """6543 kent geen prepared statements en botst met psycopg3 en COPY."""
    bezwaren = controleer_dsn(GOED.replace(":5432", ":6543"))
    assert any("6543" in b and "5432" in b for b in bezwaren)


def test_ontbrekende_poort_wordt_gevangen():
    dsn = (
        "postgresql://postgres.abcdefghijklm:geheim"
        "@aws-0-eu-central-1.pooler.supabase.com/postgres?sslmode=require"
    )
    assert any("geen poort" in b for b in controleer_dsn(dsn))


def test_pooler_eist_gebruiker_met_projectverwijzing():
    """`postgres` in plaats van `postgres.<ref>` geeft een authenticatiefout.

    En dan ga je het wachtwoord opnieuw zetten, want daar wijst de melding
    naartoe. Vandaar dat dit bij naam genoemd wordt.
    """
    dsn = GOED.replace("postgres.abcdefghijklm:", "postgres:")
    assert any("postgres.<project-ref>" in b for b in controleer_dsn(dsn))


def test_zonder_sslmode_een_bezwaar():
    assert any("sslmode" in b for b in controleer_dsn(GOED.replace("?sslmode=require", "")))


@pytest.mark.parametrize("modus", ["require", "verify-ca", "verify-full"])
def test_strengere_sslmodi_zijn_ook_goed(modus):
    dsn = GOED.replace("sslmode=require", f"sslmode={modus}")
    assert not any("sslmode" in b for b in controleer_dsn(dsn))


def test_verkeerd_schema_wordt_gevangen():
    assert any("postgresql" in b for b in controleer_dsn(GOED.replace("postgresql://", "mysql://")))


def test_meerdere_fouten_worden_allemaal_gemeld():
    """Niet stoppen bij de eerste.

    Wie drie dingen fout heeft, wil dat in één keer horen en niet in drie
    ronden van proberen.
    """
    slecht = "postgresql://postgres:geheim@db.abcdefghijklm.supabase.co:6543/postgres"
    bezwaren = controleer_dsn(slecht)
    assert len(bezwaren) >= 3


def test_de_plaatshouder_uit_het_dashboard_wordt_bij_naam_genoemd():
    """Gemeten op 14 augustus 2026, bij het opzetten van de echte database.

    Supabase geeft de connection string met `[YOUR-PASSWORD]` erin. Wie hem
    plakt en het wachtwoord vergeet, kreeg tot vandaag geen bezwaar maar een
    traceback uit urlparse: de blokhaken lezen als een IPv6-netloc, en de
    ValueError praat over 'does not appear to be an IPv4 or IPv6 address'.
    Dat wijst naar een adresprobleem dat er niet is.
    """
    dsn = (
        "postgresql://postgres.abcdefghijklm:[YOUR-PASSWORD]"
        "@aws-0-eu-north-1.pooler.supabase.com:5432/postgres?sslmode=require"
    )
    bezwaren = controleer_dsn(dsn)
    assert any("YOUR-PASSWORD" in b for b in bezwaren)


def test_een_onontleedbare_string_werpt_niet_maar_meldt():
    """`controleer_dsn` is een pure functie: ze geeft bezwaren, ze crasht niet.

    De hele reden dat deze module bestaat, is dat de foutmeldingen rond deze
    verbinding naar het verkeerde probleem wijzen. Een traceback is daarvan
    het ergste geval.
    """
    for rommel in ("postgresql://postgres:pw@[niet-echt]:5432/postgres", "://", "http://["):
        bezwaren = controleer_dsn(rommel)
        assert bezwaren, f"geen bezwaar voor {rommel!r}"
        assert all(isinstance(b, str) for b in bezwaren)


def test_de_dsn_zelf_staat_nooit_in_een_bezwaar():
    """Een foutmelding met het wachtwoord erin is een gelekt wachtwoord.

    Foutmeldingen belanden in CI-logs, in issues en in chatberichten.
    """
    slecht = "postgresql://postgres:HEELGEHEIM@db.x.supabase.co:6543/postgres"
    for bezwaar in controleer_dsn(slecht):
        assert "HEELGEHEIM" not in bezwaar


# --- normalisatie: wat het dashboard levert, moet gewoon werken -------------


def test_de_gekopieerde_pooler_uri_krijgt_sslmode_erbij():
    """Wat de knop "Copy" in Supabase geeft, draagt geen sslmode.

    Dat was de enige reden waarom een verder correcte opzet afketste, en het
    kostte een beheerder een avond. De eis blijft (controleer_dsn toetst er
    nog steeds op), alleen wordt ze nu ingevuld in plaats van afgedwongen.
    """
    uit_dashboard = (
        "postgresql://postgres.abcdefghijklm:geheim"
        "@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"
    )
    assert controleer_dsn(uit_dashboard), "zonder sslmode hoort er een bezwaar"
    assert controleer_dsn(normaliseer_dsn(uit_dashboard)) == []


def test_een_bestaande_sslmode_blijft_staan():
    """verify-full is strenger dan require; die keuze is niet aan ons."""
    strenger = GOED.replace("sslmode=require", "sslmode=verify-full")
    assert normaliseer_dsn(strenger) == strenger


def test_een_andere_queryparameter_blijft_behouden():
    met_extra = GOED.replace("?sslmode=require", "?application_name=bakkerij")
    genormaliseerd = normaliseer_dsn(met_extra)
    assert "application_name=bakkerij" in genormaliseerd
    assert controleer_dsn(genormaliseerd) == []


def test_regeleindes_en_spaties_van_het_plakken_verdwijnen():
    """Een secret-veld plakt graag een regeleinde achter de waarde."""
    assert normaliseer_dsn(f"  {GOED}\n") == GOED


def test_normaliseren_verzint_geen_poort_of_host():
    """Die twee dragen een keuze en horen zichtbaar te blijven, niet geraden."""
    zonder_poort = (
        "postgresql://postgres.abcdefghijklm:geheim"
        "@aws-0-eu-central-1.pooler.supabase.com/postgres"
    )
    assert controleer_dsn(normaliseer_dsn(zonder_poort)), "poort blijft een bezwaar"
