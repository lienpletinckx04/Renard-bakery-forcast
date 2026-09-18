"""De databasesuite die een échte Postgres nodig heeft.

Alles hier is op 18 augustus 2026 geschreven naar aanleiding van de eerste keer
dat de databasetrack tegen een draaiende server liep. Elke test hieronder komt
overeen met een fout die die dag gevonden is, en die geen enkele bestaande test
kón vinden -- omdat je er een SQL-parser voor nodig hebt.

OPZETTEN, LOKAAL

    brew install postgresql@17 && pg_ctl -D /opt/homebrew/var/postgresql@17 start
    createdb bakkerij_test
    psql -d bakkerij_test -c "create role anon nologin;
                              create role authenticated nologin;
                              create role service_role nologin bypassrls;"
    TEST_DB_URL=postgresql://$USER@localhost:5432/bakkerij_test \\
        .venv/bin/python -m pytest tests/test_db_echt.py

De drie rollen zijn geen franje: Supabase maakt ze zelf aan en de migraties
verwijzen ernaar. Zonder die rollen valt migratie 001 al om met
`role "anon" does not exist` -- de eerste fout van die dag.

Zonder TEST_DB_URL slaat deze suite zichzelf over.
"""
import datetime as dt
import json
from decimal import Decimal

import pandas as pd
import pytest

from bakkerij import kostenmodel as km
from bakkerij.db import contract_rijen as cr
from bakkerij.db import kostenmodel_db as kmdb
from bakkerij.db import laden, sluitingen_db
from bakkerij.db import migratie as m
from bakkerij.sluitingskalender import Uitspraak, Weekregel

# Alle kolommen van dim_kalender (migratie 001), in schemavolgorde.
KALENDER_KOLOMMEN = [
    "datum", "weekdag", "weekdagnaam", "is_weekend", "feestdag",
    "feestdagnaam", "dag_voor_feestdag", "dag_na_feestdag", "brugdag",
    "maand", "weeknr", "dag_van_jaar", "winkel_gemeten", "winkel_open",
]


def _kalenderrij(datum: str, feestdagnaam: str) -> pd.DataFrame:
    return pd.DataFrame([{
        "datum": pd.Timestamp(datum).date(),
        "weekdag": 3, "weekdagnaam": "donderdag",
        "is_weekend": False, "feestdag": bool(feestdagnaam),
        "feestdagnaam": feestdagnaam,
        "dag_voor_feestdag": False, "dag_na_feestdag": False, "brugdag": False,
        "maand": 7, "weeknr": 27, "dag_van_jaar": 185,
        "winkel_gemeten": True, "winkel_open": True,
    }])


def _leeg(verbinding, tabel: str) -> None:
    """Maak één feitentabel leeg binnen de lopende transactie.

    Een testdatabase die ooit een echte `make db-laad` heeft gezien, staat vol.
    Een test die dan telt hoeveel rijen er terugkomen, meet die vulling en niet
    zichzelf. De rollback aan het eind van de test zet alles terug.
    """
    with verbinding.cursor() as cur:
        cur.execute(f"delete from public.{tabel}")


def test_alle_migraties_draaien_en_zijn_idempotent(echte_db):
    """Tweede keer draaien is een lege run, geen tweede keer schema."""
    m.pas_toe(echte_db)
    assert m.pas_toe(echte_db) == [], "een tweede run paste opnieuw iets toe"


def test_lege_tekst_blijft_leeg_en_wordt_geen_null(echte_db):
    """DE regressietest van 18 augustus 2026.

    `dim_kalender.feestdagnaam` is `not null default ''`. De COPY bood lege
    tekst aan als de null-string, en Postgres weigerde de rij:

        null value in column "feestdagnaam" of relation
        "tijdelijk_dim_kalender" violates not-null constraint

    Dat was COPY-regel 1 van de eerste tabel, dus `make db-laad` kwam nooit
    verder dan de kalender -- en de droge modus kon het per constructie niet
    zien, want die stopt vóór het schrijven. Zie NULL_SENTINEL in
    bakkerij/db/laden.py.
    """
    m.pas_toe(echte_db)
    datum = "2019-07-04"
    laden.schrijf(echte_db, "dim_kalender", _kalenderrij(datum, ""),
                  KALENDER_KOLOMMEN, ["datum"])

    with echte_db.cursor() as cur:
        cur.execute("select feestdagnaam from public.dim_kalender where datum = %s",
                    (datum,))
        gevonden = cur.fetchone()

    assert gevonden is not None, "de rij is niet geschreven"
    assert gevonden[0] == "", f"lege tekst werd {gevonden[0]!r} in plaats van ''"
    echte_db.rollback()


def test_een_echte_feestdagnaam_overleeft_de_copy_ook(echte_db):
    """De sentinel mag de gewone weg niet stukmaken."""
    m.pas_toe(echte_db)
    datum = "2019-07-21"
    laden.schrijf(echte_db, "dim_kalender", _kalenderrij(datum, "Nationale feestdag"),
                  KALENDER_KOLOMMEN, ["datum"])

    with echte_db.cursor() as cur:
        cur.execute("select feestdagnaam from public.dim_kalender where datum = %s",
                    (datum,))
        gevonden = cur.fetchone()

    assert gevonden is not None and gevonden[0] == "Nationale feestdag"
    echte_db.rollback()


def test_de_sentinel_als_echte_waarde_wordt_geweigerd(echte_db):
    """Een cel die letterlijk `\\N` draagt zou als NULL gelezen worden."""
    m.pas_toe(echte_db)
    with pytest.raises(ValueError, match=r"letterlijke waarde"):
        laden.schrijf(echte_db, "dim_kalender",
                      _kalenderrij("2019-07-25", laden.NULL_SENTINEL),
                      KALENDER_KOLOMMEN, ["datum"])
    echte_db.rollback()


def _model(*criteria: str, waarden: dict | None = None) -> km.Kostenmodel:
    return km.Kostenmodel(
        criteria=tuple(km.Criterium(naam, "") for naam in criteria),
        waarden=waarden or {},
    )


def test_kostenmodel_schrijven_en_teruglezen(echte_db):
    """De rondgang over een echte Postgres: model -> tabellen -> model.

    Dit is de kant die geen enkele pure test kan zien. `numeric(5, 2)` rondt af,
    `bewaard_op` komt van de database, en de volgorde komt uit een `order by` --
    drie dingen die alleen een server werkelijk doet.
    """
    m.pas_toe(echte_db)
    model = _model(
        "Grondstoffen", "Verlies en verspilling",
        waarden={
            "Brood": {"Grondstoffen": Decimal("30.50"),
                      "Verlies en verspilling": Decimal(2)},
            "Patisserie": {"Grondstoffen": Decimal("37.5")},
        },
    )
    aantal = kmdb.schrijf(echte_db, model, "test@example.com")
    assert aantal == 3

    terug = kmdb.lees(echte_db)
    assert terug is not None
    assert [c.naam for c in terug.criteria] == [
        "Grondstoffen", "Verlies en verspilling"]
    assert terug.waarden == model.waarden
    assert terug.ingevuld_door == "test@example.com"
    # bewaard_op komt van de database (default now()), dus er staat er één.
    assert terug.ingevuld_op != ""
    echte_db.rollback()


def test_kostenmodel_schrijven_is_alles_of_niets(echte_db):
    """Een tweede opslag die halverwege valt, mag de eerste niet slopen.

    Zonder deze test is de vorm "alles weg, dan alles erin" een belofte op
    papier: hij faalt pas zichtbaar op de dag dat er echt iets misgaat, en dan
    staat er een leeg kostenmodel waar niemand om vroeg.
    """
    m.pas_toe(echte_db)
    kmdb.schrijf(echte_db, _model(
        "Grondstoffen", waarden={"Brood": {"Grondstoffen": Decimal(30)}},
    ), "eerste")
    echte_db.commit()

    # Een percentage buiten 0-100 laat de check-clausule van migratie 005 vallen.
    # Het model komt niet door `km.toets` heen, dus valt het vóór het eerste
    # delete -- precies de bedoeling.
    with pytest.raises(ValueError, match="buiten het bereik"):
        kmdb.schrijf(echte_db, km.Kostenmodel(
            criteria=(km.Criterium("Verlies", ""),),
            waarden={"Brood": {"Verlies": Decimal(150)}},
        ), "tweede")

    behouden = kmdb.lees(echte_db)
    assert behouden is not None
    assert [c.naam for c in behouden.criteria] == ["Grondstoffen"]
    assert behouden.waarden == {"Brood": {"Grondstoffen": Decimal(30)}}

    # Opruimen: deze test heeft bewust gecommit om te bewijzen dat de eerste
    # opslag echt vast stond.
    with echte_db.cursor() as cur:
        cur.execute(kmdb.VERWIJDER_WAARDEN_SQL)
        cur.execute(kmdb.VERWIJDER_CRITERIA_SQL)
    echte_db.commit()


def test_de_rpc_van_migratie_009_bewaart_in_een_transactie(echte_db):
    """De schrijfroute van de gehoste omgeving.

    Het platform op Vercel heeft geen Postgres-verbinding en schrijft via
    PostgREST; daar is één verzoek één transactie. Deze functie is dus de enige
    manier waarop twee tabellen samen kunnen slagen of falen -- en dit is de
    enige test die dat kan bewijzen, want de vorm zit in SQL en niet in Python.
    """
    m.pas_toe(echte_db)
    boom = {
        "versie": 2,
        "criteria": [{"naam": "Grondstoffen", "omschrijving": "foodcost"},
                     {"naam": "Verlies  en verspilling"}],
        "waarden": {"Brood": {"Grondstoffen": "30.50",
                              "Verlies en verspilling": "2"}},
    }
    with echte_db.cursor() as cur:
        cur.execute("select public.bewaar_kostenmodel(%s::jsonb, %s)",
                    (json.dumps(boom), "lien@asklien.ai"))
        assert cur.fetchone()[0] == 2

    # Dubbele witruimte in een criteriumnaam wordt weggewerkt, net als in
    # bakkerij/kostenmodel.py en platform/lib/kostenmodel.ts -- anders zou de
    # waarde onder "Verlies en verspilling" geen criterium meer vinden.
    gelezen = kmdb.lees(echte_db)
    assert gelezen is not None
    assert [c.naam for c in gelezen.criteria] == [
        "Grondstoffen", "Verlies en verspilling"]
    assert gelezen.waarden["Brood"]["Grondstoffen"] == Decimal("30.50")
    assert gelezen.ingevuld_door == "lien@asklien.ai"
    echte_db.rollback()


def test_de_rpc_laat_het_oude_model_staan_als_de_nieuwe_niet_deugt(echte_db):
    """Alles of niets, ook over PostgREST.

    Zonder deze eigenschap zou een afgewezen opslag de bestaande kosten wissen:
    de functie begint met een delete, en een half uitgevoerde functie zou de
    beheerder met een leeg margescherm achterlaten na een poging die zichtbaar
    mislukte.
    """
    m.pas_toe(echte_db)
    with echte_db.cursor() as cur:
        cur.execute(
            "select public.bewaar_kostenmodel(%s::jsonb, %s)",
            (json.dumps({"criteria": [{"naam": "Grondstoffen"}],
                         "waarden": {"Brood": {"Grondstoffen": "30"}}}), "een"),
        )
        cur.execute("savepoint voor_de_fout")
        with pytest.raises(Exception, match="kosten_waarde_pct_check"):
            cur.execute(
                "select public.bewaar_kostenmodel(%s::jsonb, %s)",
                (json.dumps({"criteria": [{"naam": "Verlies"}],
                             "waarden": {"Brood": {"Verlies": "150"}}}), "twee"),
            )
        cur.execute("rollback to savepoint voor_de_fout")

    behouden = kmdb.lees(echte_db)
    assert behouden is not None
    assert [c.naam for c in behouden.criteria] == ["Grondstoffen"]
    echte_db.rollback()


def test_de_rpc_weigert_een_opslag_zonder_naam(echte_db):
    """`bewaard_door` is `not null` omdat elke wijziging aan de cijferbasis de
    naam draagt van wie hem deed. Een lege string zou die kolom halen en de
    bedoeling missen."""
    m.pas_toe(echte_db)
    with echte_db.cursor() as cur, pytest.raises(Exception, match='"door" is leeg'):
        cur.execute("select public.bewaar_kostenmodel(%s::jsonb, %s)",
                    (json.dumps({"criteria": [], "waarden": {}}), "   "))
    echte_db.rollback()


def test_service_role_mag_de_rpc_maar_niet_de_tabellen(echte_db):
    """De rol waarmee het platform schrijft, mag precies één ding.

    Migratie 008 zei het scherp: "SELECT EN NIETS MEER -- wie er ooit
    schrijfrechten aan toevoegt, moet zich eerst afvragen waarom de schrijfroute
    niet meer volstaat." Migratie 009 is dat antwoord, en dit is de test die
    vastlegt dat het antwoord smal blijft: de functie mag, de tabellen niet.
    """
    m.pas_toe(echte_db)
    with echte_db.cursor() as cur:
        cur.execute("select rolname from pg_roles where rolname = 'service_role'")
        if cur.fetchone() is None:
            pytest.skip("rol service_role bestaat niet in deze testdatabase")

        cur.execute("set local role service_role")
        cur.execute("select public.bewaar_kostenmodel(%s::jsonb, %s)",
                    (json.dumps({"criteria": [{"naam": "Grondstoffen"}],
                                 "waarden": {"Brood": {"Grondstoffen": "30"}}}),
                     "svc"))
        assert cur.fetchone()[0] == 1

        cur.execute("savepoint voor_de_fout")
        with pytest.raises(Exception, match="permission denied"):
            cur.execute("insert into public.kosten_criterium "
                        "(naam, bewaard_door) values ('Rechtstreeks', 'svc')")
        cur.execute("rollback to savepoint voor_de_fout")
    echte_db.rollback()


def test_anon_mag_de_rpc_niet_aanroepen(echte_db):
    """`anon` is de publiceerbare sleutel, en die zit in elke JavaScript-bundel.
    Een `security definer`-functie krijgt van Postgres standaard uitvoerrecht
    voor PUBLIC; zonder de revoke in migratie 009 kon iedere bezoeker het
    kostenmodel overschrijven."""
    m.pas_toe(echte_db)
    with echte_db.cursor() as cur:
        cur.execute("select rolname from pg_roles where rolname = 'anon'")
        if cur.fetchone() is None:
            pytest.skip("rol anon bestaat niet in deze testdatabase")
        cur.execute("set local role anon")
        with pytest.raises(Exception, match="permission denied for function"):
            cur.execute("select public.bewaar_kostenmodel(%s::jsonb, %s)",
                        (json.dumps({"criteria": [], "waarden": {}}), "anon"))
    echte_db.rollback()


def test_service_role_mag_het_contract_lezen(echte_db):
    """De rol waarmee het platform leest, moet er ook echt in kunnen.

    `service_role` draagt BYPASSRLS, maar dat zegt niets over tabelrechten.
    Tot migratie 008 kreeg die rol nergens een grant, en werkte het alleen op
    Supabase -- via default privileges die in geen enkel bestand van deze repo
    staan. Op een kale Postgres gaf dezelfde code `permission denied for table
    contract_antwoord`, en onder CONTRACT_BRON=db is dat élk scherm.
    """
    m.pas_toe(echte_db)
    with echte_db.cursor() as cur:
        cur.execute("select rolname from pg_roles where rolname = 'service_role'")
        if cur.fetchone() is None:
            pytest.skip("rol service_role bestaat niet in deze testdatabase")

        cur.execute("set local role service_role")
        cur.execute("select count(*) from public.contract_antwoord")
        assert cur.fetchone() is not None
    echte_db.rollback()


def test_de_krimpwacht_leest_de_rijkdom_uit_echte_jsonb(echte_db):
    """`BESTAANDE_RIJKDOM_SQL` bevraagt jsonb met `->`, en die query is nooit
    door een parser gegaan tot deze test bestond.

    Wat hier bewezen wordt is de hele keten van de tweede wacht: de twee velden
    komen er als Python-lijsten uit (niet als tekst), `rijkdom_uit_velden`
    maakt er dezelfde samenvatting van als `rijkdom_uit_json` op de bestanden,
    en een antwoord dat een bron verliest wordt herkend. Faalt de vertaling
    jsonb -> Python, dan leest de wacht overal lege verzamelingen en meldt ze
    nooit iets -- een wacht die stil goedkeurt is erger dan geen wacht.
    """
    m.pas_toe(echte_db)
    antwoord = {
        "versie": 1,
        "bron": ["deliveroo", "winkel"],
        "onbeschikbaar": [{"veld": "marge_per_groep", "reden": "geen kosten"}],
        "data": {},
    }
    with echte_db.cursor() as cur:
        # Binnen de transactie, net als de echte schrijfroute: alles weg,
        # alles erin. De rollback aan het eind zet de tabel terug.
        cur.execute(cr.VERWIJDER_SQL)
        cur.execute(cr.INVOEG_SQL, ("kanalen", "nl", "", json.dumps(antwoord)))
        cur.execute(cr.BESTAANDE_RIJKDOM_SQL)
        bestaand = {
            (s, t, w): cr.rijkdom_uit_velden(bron, onb)
            for s, t, w, bron, onb in cur.fetchall()
        }

    sleutel = ("kanalen", "nl", "")
    assert bestaand[sleutel] == cr.rijkdom_uit_json(json.dumps(antwoord))
    assert bestaand[sleutel].bronnen == frozenset({"deliveroo", "winkel"})

    # En de wacht slaat aan op precies het runner-scenario: dezelfde sleutel,
    # Deliveroo eruit.
    zonder_deliveroo = dict(antwoord, bron=["winkel"])
    armer = cr.verarming(
        bestaand, {sleutel: cr.rijkdom_uit_json(json.dumps(zonder_deliveroo))}
    )
    assert [v.verloren_bronnen for v in armer] == [frozenset({"deliveroo"})]
    echte_db.rollback()


# --- de dodemansknop: migratie 010 ------------------------------------------

def _sync_stand(verbinding, runs):
    """Zet `etl_run` op een verzonnen stand en lees het oordeel terug.

    `runs` is een lijst (status, uren_geleden). De tabel gaat eerst leeg: deze
    tests meten de drempels, niet wat er toevallig in de testdatabase stond.
    """
    with verbinding.cursor() as cur:
        cur.execute("delete from public.etl_run")
        for status, uren in runs:
            cur.execute(
                "insert into public.etl_run "
                "(bron, status, gestart_op, geeindigd_op) values "
                "('nachtelijke-sync', %s, now() - make_interval(hours => %s), "
                " case when %s = 'bezig' then null "
                "      else now() - make_interval(hours => %s) end)",
                (status, uren, status, uren),
            )
        cur.execute("select geval, oordeel from public.sync_stand")
        return cur.fetchone()


def test_zonder_enige_run_zegt_de_stand_dat_ook(echte_db):
    """Nul rijen mag geen nul rijen worden: "er heeft nog nooit een sync
    gedraaid" is zelf een antwoord dat op het scherm hoort, en een leeg
    resultaat is in de UI niet te onderscheiden van een kapotte verbinding."""
    m.pas_toe(echte_db)
    assert _sync_stand(echte_db, []) == ("nooit", "let_op")
    echte_db.rollback()


def test_een_verse_run_is_goed(echte_db):
    m.pas_toe(echte_db)
    assert _sync_stand(echte_db, [("goed", 2)]) == ("vers", "goed")
    echte_db.rollback()


def test_een_overgeslagen_nacht_is_nog_geen_alarm(echte_db):
    """De planner van GitHub Actions is best effort. Eén gemiste nacht mag
    geen alarm zijn, anders staat het scherm vaker rood dan terecht."""
    m.pas_toe(echte_db)
    assert _sync_stand(echte_db, [("goed", 30)]) == ("vers", "goed")
    assert _sync_stand(echte_db, [("goed", 40)]) == ("achter", "let_op")
    echte_db.rollback()


def test_drie_nachten_stil_is_fout(echte_db):
    m.pas_toe(echte_db)
    assert _sync_stand(echte_db, [("goed", 24 * 4)]) == ("oud", "fout")
    echte_db.rollback()


def test_een_gefaalde_run_is_meteen_fout(echte_db):
    """Ook wanneer de vorige nacht wél slaagde: een gevallen sync hoort
    dezelfde ochtend op het scherm te staan, niet pas na drie dagen."""
    m.pas_toe(echte_db)
    assert _sync_stand(echte_db, [("goed", 26), ("fout", 2)]) == ("gefaald", "fout")
    echte_db.rollback()


def test_een_lopende_run_is_geen_storing(echte_db):
    m.pas_toe(echte_db)
    assert _sync_stand(echte_db, [("bezig", 0)]) == ("loopt", "goed")
    echte_db.rollback()


def test_een_run_die_begon_en_nooit_afmaakte_is_fout(echte_db):
    """DE reden dat etl_run zijn rij aan het BEGIN schrijft (zie 003). De job
    heeft een timeout van 90 minuten, dus na drie uur loopt hij niet meer."""
    m.pas_toe(echte_db)
    assert _sync_stand(echte_db, [("bezig", 5)]) == ("gestrand", "fout")
    echte_db.rollback()


def test_de_stand_kijkt_alleen_naar_de_nachtelijke_sync(echte_db):
    """`contract` en `canoniek` schrijven hun eigen etl_run-rijen. Die zijn
    stappen binnen een run en zeggen niets over of de ketting nog leeft."""
    m.pas_toe(echte_db)
    with echte_db.cursor() as cur:
        cur.execute("delete from public.etl_run")
        cur.execute(
            "insert into public.etl_run (bron, status, geeindigd_op) "
            "values ('contract', 'goed', now())"
        )
        cur.execute("select geval, oordeel from public.sync_stand")
        assert cur.fetchone() == ("nooit", "let_op")
    echte_db.rollback()


# --- de sluitingskalender: migratie 011/012 ----------------------------------


def _kalenderdocument() -> dict:
    """Het document zoals het scherm Sluitingsdagen het aanbiedt: twee
    uitspraken en één weekregel. De dubbele witruimte is opzet."""
    return {
        "dagen": [
            {"datum": "2026-12-25", "toestand": "dicht",
             "reden": "Kerstmis  op  vrijdag", "bron": "feestdag"},
            {"datum": "2027-01-06", "toestand": "open", "reden": "",
             "bron": "feestdag"},
        ],
        "regels": [
            {"weekdag": 0, "vanaf": "2026-09-01", "tot": None,
             "reden": "vaste rustdag"},
        ],
    }


def test_de_rpc_van_migratie_012_bewaart_in_een_transactie(echte_db):
    """De schrijfroute van de gehoste omgeving, derde toepassing van de keten.

    Het platform op Vercel schrijft via PostgREST, en daar is één verzoek één
    transactie. Deze functie is de enige manier waarop de twee
    sluitingstabellen samen kunnen slagen of falen -- en dit is de enige test
    die dat kan bewijzen, want de vorm zit in SQL en niet in Python.
    """
    m.pas_toe(echte_db)
    with echte_db.cursor() as cur:
        cur.execute("select public.bewaar_sluitingskalender(%s::jsonb, %s)",
                    (json.dumps(_kalenderdocument()), "lien@asklien.ai"))
        assert cur.fetchone()[0] == 3

    stand = sluitingen_db.lees(echte_db)
    assert stand is not None
    assert [u.datum for u in stand.uitspraken] == [
        dt.date(2026, 12, 25), dt.date(2027, 1, 6)]
    # Dubbele witruimte in een reden wordt weggewerkt, net als in de rpc van
    # het kostenmodel: de reden komt letterlijk op het scherm.
    assert stand.uitspraken[0].reden == "Kerstmis op vrijdag"
    assert stand.uitspraken[1].toestand == "open"
    (regel,) = stand.regels
    assert (regel.weekdag, regel.tot, regel.reden) == (0, None, "vaste rustdag")
    assert stand.bewaard_door == "lien@asklien.ai"
    assert stand.bewaard_op != ""
    echte_db.rollback()


def test_de_rpc_laat_de_oude_kalender_staan_als_de_nieuwe_niet_deugt(echte_db):
    """Alles of niets, ook over PostgREST.

    De functie begint met een delete; een half uitgevoerde aanroep zou de
    kalender leeg achterlaten, en dan voorspelt het platform omzet op elke
    dag die de beheerder dicht heeft verklaard.
    """
    m.pas_toe(echte_db)
    with echte_db.cursor() as cur:
        cur.execute("select public.bewaar_sluitingskalender(%s::jsonb, %s)",
                    (json.dumps(_kalenderdocument()), "een"))
        cur.execute("savepoint voor_de_fout")
        # "misschien" haalt de check van migratie 011 niet: onbekend is geen
        # toestand maar het ontbreken van een uitspraak.
        fout = {"dagen": [{"datum": "2026-12-25", "toestand": "misschien",
                           "reden": "", "bron": "feestdag"}], "regels": []}
        with pytest.raises(Exception, match="sluitingsdag_toestand_check"):
            cur.execute(
                "select public.bewaar_sluitingskalender(%s::jsonb, %s)",
                (json.dumps(fout), "twee"))
        cur.execute("rollback to savepoint voor_de_fout")

    behouden = sluitingen_db.lees(echte_db)
    assert behouden is not None
    assert len(behouden.uitspraken) == 2
    assert len(behouden.regels) == 1
    assert behouden.bewaard_door == "een"
    echte_db.rollback()


def test_de_sluitings_rpc_weigert_een_opslag_zonder_naam(echte_db):
    """Wie schrijft, tekent -- zelfde regel als bewaar_kostenmodel."""
    m.pas_toe(echte_db)
    with echte_db.cursor() as cur, pytest.raises(Exception, match='"door" is leeg'):
        cur.execute("select public.bewaar_sluitingskalender(%s::jsonb, %s)",
                    (json.dumps({"dagen": [], "regels": []}), "   "))
    echte_db.rollback()


def test_de_sluitings_rpc_weigert_dubbele_datums_in_mensentaal(echte_db):
    """De primaire sleutel zou dit ook weigeren, maar in de taal van een
    constraint; de functie zegt het in gewone taal, en vóór het delete."""
    m.pas_toe(echte_db)
    dubbel = {
        "dagen": [
            {"datum": "2026-12-25", "toestand": "dicht", "reden": "",
             "bron": "feestdag"},
            {"datum": "2026-12-25", "toestand": "open", "reden": "",
             "bron": "feestdag"},
        ],
        "regels": [],
    }
    with echte_db.cursor() as cur, \
            pytest.raises(Exception, match="één uitspraak per dag"):
        cur.execute("select public.bewaar_sluitingskalender(%s::jsonb, %s)",
                    (json.dumps(dubbel), "test"))
    echte_db.rollback()


def test_service_role_mag_de_sluitings_rpc_maar_niet_de_tabellen(echte_db):
    """Zelfde smalle afspraak als bij het kostenmodel: de rol waarmee het
    platform schrijft, mag de functie en niets rechtstreeks op de tabel."""
    m.pas_toe(echte_db)
    with echte_db.cursor() as cur:
        cur.execute("select rolname from pg_roles where rolname = 'service_role'")
        if cur.fetchone() is None:
            pytest.skip("rol service_role bestaat niet in deze testdatabase")

        cur.execute("set local role service_role")
        cur.execute("select public.bewaar_sluitingskalender(%s::jsonb, %s)",
                    (json.dumps(_kalenderdocument()), "svc"))
        assert cur.fetchone()[0] == 3

        cur.execute("savepoint voor_de_fout")
        with pytest.raises(Exception, match="permission denied"):
            cur.execute("insert into public.sluitingsdag "
                        "(datum, toestand, reden, bron, bewaard_door) "
                        "values ('2031-01-06', 'open', '', 'feestdag', 'svc')")
        cur.execute("rollback to savepoint voor_de_fout")
    echte_db.rollback()


def test_anon_mag_de_sluitings_rpc_niet_aanroepen(echte_db):
    """`anon` is de publiceerbare sleutel, en die zit in elke
    JavaScript-bundel. Zonder de revoke in migratie 012 kon iedere bezoeker
    de sluitingskalender overschrijven."""
    m.pas_toe(echte_db)
    with echte_db.cursor() as cur:
        cur.execute("select rolname from pg_roles where rolname = 'anon'")
        if cur.fetchone() is None:
            pytest.skip("rol anon bestaat niet in deze testdatabase")
        cur.execute("set local role anon")
        with pytest.raises(Exception, match="permission denied for function"):
            cur.execute(
                "select public.bewaar_sluitingskalender(%s::jsonb, %s)",
                (json.dumps({"dagen": [], "regels": []}), "anon"))
    echte_db.rollback()


def test_sluitingskalender_schrijven_en_teruglezen(echte_db):
    """De rondgang over een echte Postgres, aan de Python-kant van de keten:
    het eenmalige laadscript (make db-sluitingen) schrijft, de canoniekbouw
    leest. Als die reis een veld verandert, verschuift een uitspraak van de
    beheerder zonder dat iemand het ziet."""
    m.pas_toe(echte_db)
    uitspraken = (
        Uitspraak(datum=dt.date(2026, 12, 25), toestand="dicht",
                  reden="Kerstmis", bron="bestand"),
        Uitspraak(datum=dt.date(2027, 1, 6), toestand="open", reden="",
                  bron="feestdag"),
    )
    regels = (Weekregel(weekdag=0, vanaf=dt.date(2026, 9, 1), tot=None,
                        reden="vaste rustdag"),)

    aantal = sluitingen_db.schrijf(echte_db, uitspraken, regels,
                                   "test@example.com")
    assert aantal == 3

    terug = sluitingen_db.lees(echte_db)
    assert terug is not None
    assert terug.uitspraken == uitspraken
    assert terug.regels == regels
    assert terug.bewaard_door == "test@example.com"
    # bewaard_op komt van de database (default now()), dus er staat er één.
    assert terug.bewaard_op != ""
    echte_db.rollback()
