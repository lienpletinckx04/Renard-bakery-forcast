"""Het canonieke model naar Postgres schrijven.

Deze laag rekent niet. Ze neemt de tabellen die `bakkerij/canoniek.py`
produceert, zet ze om naar de vorm die het schema verwacht, en schrijft ze
weg. Elke aggregatie hoort in de berekeningslaag thuis -- staat ze hier, dan
bestaat ze niet voor een export en niet voor de app van fase 2.

HET SCHRIJFPATROON

`COPY` naar een tijdelijke tabel, dan één `insert ... on conflict` binnen
dezelfde transactie (stack.md). Alles of niets.

Waarom niet gewoon rij voor rij invoegen: 221.375 rijen over een
pooler-verbinding met een netwerkrondgang per rij duurt uren, en een run die
halverwege sterft laat de tabel in een halve staat achter. Waarom niet
`truncate` gevolgd door `insert`: dan is er een moment waarop de tabel leeg
is, en als de run daarna faalt, staat het platform zonder cijfers. Met
`on conflict do update` blijft de oude inhoud staan tot de nieuwe erover
heen gaat, en dat gebeurt in één transactie.

WAT ER NOOIT IN GAAT

Geen `partner_id`, geen klantnaam, geen adres, geen bonnotitie. De extractie
vraagt die velden nooit op, en `controleer_kolommen` weigert een DataFrame
dat ze toch draagt -- een vangrail voor het geval een bron ooit meer levert
dan gevraagd.
"""

from __future__ import annotations

import io
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

# Stammen die nergens in een kolomnaam mogen voorkomen, ongeacht wat de bron
# levert. Stammen en geen exacte namen: een lijst van exacte namen liet
# `customer_note` en `partner_street` door -- precies de vormen waarin een
# Odoo-bron klantvelden aanlevert.
#
# Bewust `btw_nummer` en niet het kale `btw`: de kernkolom `omzet_excl_btw`
# bevat die drie letters ook, en de vangrail mag de omzet zelf niet weigeren.
# Het Engelstalige btw-nummerveld (`vat`) staat er wel kaal in.
VERBODEN_STAMMEN = (
    "partner", "klant", "customer", "adres", "address", "street", "city",
    "zip", "postcode", "note", "notitie", "email", "mail", "telefoon",
    "phone", "mobile", "vat", "btw_nummer", "btwnummer",
)


def controleer_kolommen(df: pd.DataFrame, waar: str) -> None:
    """Weiger een DataFrame dat een klantveld draagt.

    Dit is geen theoretische controle. De Odoo-extractie vraagt de verboden
    velden niet op, maar een toekomstige wijziging aan een bron kan er stil
    een kolom bij zetten, en dan schuift die door tot in de gehoste database.
    Harde regel 3 is dan al gebroken voor iemand het merkt.
    """
    gevonden = sorted({
        str(k).lower() for k in df.columns
        if any(stam in str(k).lower() for stam in VERBODEN_STAMMEN)
    })
    if gevonden:
        raise ValueError(
            f"{waar}: deze kolommen mogen de database niet in: "
            f"{gevonden}. Zie harde regel 3 in CLAUDE.md -- er gaat "
            f"alleen geaggregeerde productverkoop naar de gehoste database."
        )


def naar_decimaal(waarden: pd.Series, plaatsen: str = "0.01") -> pd.Series:
    """Zet een kolom om naar Decimal met een vast aantal decimalen.

    De canonieke CSV's dragen floats -- dat is voor pandas onvermijdelijk. De
    database draagt `numeric`. Precies hier gebeurt de afronding, één keer en
    zichtbaar, in plaats van impliciet ergens in het stuurprogramma.

    ROUND_HALF_UP en niet Python's standaard ROUND_HALF_EVEN: bankiersafronding
    is statistisch netter maar wijkt af van wat een boekhouder narekent, en de
    cijfers op dit platform worden nagerekend.
    """
    kwantum = Decimal(plaatsen)
    return waarden.map(
        lambda w: Decimal(str(w)).quantize(kwantum, rounding=ROUND_HALF_UP)
    )


# Wat er in `dim_product` staat voor een product dat in de bron nooit een naam
# draagt. Deze tekst komt op het scherm, dus hij is voor een lezer geschreven
# en niet voor een ontwikkelaar.
NAAM_ONTBREEKT = "(naam ontbreekt in de bron)"


def kies_productnaam(verkopen: pd.DataFrame) -> pd.DataFrame:
    """Eén naam per product_id, voor `dim_product`.

    Een product kan in de bron onder meerdere schrijfwijzen voorkomen: een
    hernoeming in Odoo verandert de naam vanaf dat moment, maar de oude rijen
    houden de oude. Welke wint?

    De JONGSTE naam, dat wil zeggen de naam op de laatste datum waarop het
    product verkocht is. Dat is de naam die de bakker vandaag gebruikt, en het
    scherm toont het assortiment van vandaag. Bij een gelijke stand (twee
    namen op dezelfde laatste dag) wint de alfabetisch eerste, puur zodat de
    uitkomst niet afhangt van de rijvolgorde in het bestand -- een tabel die
    bij elke run anders is, is niet reproduceerbaar.

    EEN PRODUCT ZONDER NAAM VERDWIJNT NIET

    Gemeten op 13 augustus 2026: vier product_id's dragen in het hele extract
    nergens een naam, samen 28 rijen en EUR 400,91 (0,006% van de omzet).

    Die krijgen `NAAM_ONTBREEKT` als naam en blijven dus in de tabel staan.
    Ze eruit laten vallen zou hun omzet uit `fact_verkoop` moeten schrappen om
    de refereert-naar-beperking te halen, en dan sluiten de kanaaltotalen niet
    meer aan op de bron. Een verschil van vierhonderd euro dat niemand kan
    verklaren, kost meer vertrouwen dan een product dat eerlijk zegt dat zijn
    naam ontbreekt -- dat is harde regel 8, toegepast op een dimensie.
    """
    if verkopen.empty:
        return pd.DataFrame(columns=["product_id", "product_naam"])

    nodig = {"product_id", "product_naam", "datum"}
    ontbreekt = nodig - set(verkopen.columns)
    if ontbreekt:
        raise ValueError(f"kies_productnaam mist kolommen: {sorted(ontbreekt)}")

    alle = verkopen[["product_id", "product_naam", "datum"]].dropna(
        subset=["product_id"]
    )
    met_naam = alle.dropna(subset=["product_naam"])
    gesorteerd = met_naam.sort_values(
        ["product_id", "datum", "product_naam"], ascending=[True, False, True]
    )
    uit = gesorteerd.drop_duplicates("product_id", keep="first")[
        ["product_id", "product_naam"]
    ]

    naamloos = sorted(set(alle["product_id"]) - set(uit["product_id"]))
    if naamloos:
        uit = pd.concat(
            [uit, pd.DataFrame({"product_id": naamloos,
                                "product_naam": NAAM_ONTBREEKT})],
            ignore_index=True,
        )

    return uit.reset_index(drop=True)


def ontdubbel(df: pd.DataFrame, sleutel: list[str], sommeer: list[str]) -> tuple[pd.DataFrame, int]:
    """Tel rijen met dezelfde sleutel bij elkaar op.

    Geeft de ontdubbelde tabel terug plus het aantal rijen dat verdwenen is.

    Dit is geen voorzorg maar noodzaak. `insert ... on conflict do update`
    kán een rij niet twee keer in hetzelfde statement raken: Postgres werpt
    dan "ON CONFLICT DO UPDATE command cannot affect row a second time" en de
    hele laadrun valt om. En zou je dat omzeilen door per rij te schrijven,
    dan wint stilzwijgend de laatste en is de omzet van de andere weg.

    Optellen is de juiste behandeling en geen keuze uit gemak: twee rijen met
    dezelfde datum, hetzelfde filiaal, hetzelfde product en hetzelfde kanaal
    zijn twee stukken van dezelfde verkoop, geen tegenstrijdige metingen.

    Het aantal verdwenen rijen wordt teruggegeven zodat de aanroeper het kan
    melden. Stilzwijgend ontdubbelen is precies zo erg als het probleem.
    """
    ontbreekt = (set(sleutel) | set(sommeer)) - set(df.columns)
    if ontbreekt:
        raise ValueError(f"ontdubbel mist kolommen: {sorted(ontbreekt)}")

    if df.empty:
        return df, 0

    voor = len(df)
    uit = df.groupby(sleutel, as_index=False, sort=False, dropna=False)[sommeer].sum()
    return uit, voor - len(uit)


def onbekende_verwijzingen(
    feiten: pd.DataFrame, kolom: str, toegestaan: pd.Series
) -> list:
    """Welke waarden in `kolom` bestaan niet in de dimensie.

    De feitentabellen dragen refereert-naar-beperkingen op `dim_kalender` en
    `dim_product`. Loopt een aanvullend extract (bonnen, uren) verder door dan
    het verkoopextract, dan bestaat er een datum die de kalender niet kent, en
    dan valt de hele transactie om op een Postgres-foutmelding die de rij niet
    noemt.

    Beter is het om vóór het schrijven te weten wélke waarden ontbreken, zodat
    de melding zegt wat er aan de hand is in plaats van dat er iets misging.
    """
    if feiten.empty:
        return []
    bekend = set(toegestaan)
    return sorted({w for w in feiten[kolom] if w not in bekend})


def upsert_sql(tabel: str, kolommen: list[str], sleutel: list[str]) -> str:
    """Bouw het `insert ... select ... on conflict`-statement.

    Pure functie, en daarom te toetsen zonder database. Dat is de moeite waard
    omdat een fout hier stil is: vergeet je de `do update`, dan doet de tweede
    run niets en blijven de cijfers op de stand van gisteren staan zonder dat
    er iets faalt.
    """
    if not kolommen:
        raise ValueError("upsert_sql zonder kolommen")
    ontbreekt = set(sleutel) - set(kolommen)
    if ontbreekt:
        raise ValueError(
            f"sleutelkolommen staan niet in de kolomlijst: {sorted(ontbreekt)}"
        )

    velden = ", ".join(kolommen)
    conflict = ", ".join(sleutel)
    bij_te_werken = [k for k in kolommen if k not in sleutel]

    if bij_te_werken:
        zetten = ", ".join(f"{k} = excluded.{k}" for k in bij_te_werken)
        actie = f"do update set {zetten}"
    else:
        # Een tabel die alleen uit sleutelkolommen bestaat, heeft niets bij te
        # werken. `do nothing` is dan correct en `do update set` is een
        # syntaxfout.
        actie = "do nothing"

    return (
        f"insert into public.{tabel} ({velden})\n"
        f"select {velden} from tijdelijk_{tabel}\n"
        f"on conflict ({conflict}) {actie}"
    )


# De tekenreeks waarmee een echte NULL over de COPY gaat.
#
# Waarom niet de lege string, zoals hier tot 18 aug 2026 stond: Postgres leest
# in CSV-modus een ONGEQUOTE leeg veld als de null-string. Stond die op '',
# dan werd elke lege tekst een NULL -- en `dim_kalender.feestdagnaam` is
# `not null default ''` (001_dimensies.sql). Een DEFAULT grijpt niet in bij een
# expliciete NULL, en `create table ... (like ...)` neemt NOT NULL altijd mee,
# dus de tijdelijke tabel weigerde de rij. Gemeten op 18 aug 2026 tegen een
# echte Postgres 17: `null value in column "feestdagnaam" ... violates not-null
# constraint`, COPY-regel 1 van de eerste tabel. De hele laadstap kwam nooit
# verder dan de kalender, en geen enkele droge run kon dat zien.
#
# Met een sentinel blijft leeg gewoon leeg, en betekent alleen een echte NaN
# NULL. `\N` is de conventie die Postgres in zijn eigen tekstformaat gebruikt.
NULL_SENTINEL = "\\N"


def _naar_csv_buffer(df: pd.DataFrame, kolommen: list[str]) -> io.StringIO:
    # De sentinel mag niet als échte waarde in de data staan, anders leest
    # Postgres hem als NULL. In CSV-modus geldt de null-string alleen voor
    # ongequote velden, dus dit raakt alleen kale `\N`-cellen -- maar een
    # stilzwijgend NULL geworden productnaam is precies het soort fout waar
    # deze laag voor bestaat.
    # Geen dtype-controle vooraf: pandas 3 geeft tekstkolommen een eigen
    # `str`-dtype in plaats van `object`, en een filter op `== object` sloeg
    # daardoor precies de kolommen over die het moest bewaken (gemeten
    # 18 aug 2026 -- de wacht stond er, en deed niets). Een vergelijking met
    # een string is op een numerieke kolom gewoon overal onwaar, dus de
    # controle mag onvoorwaardelijk.
    for kolom in kolommen:
        if (df[kolom] == NULL_SENTINEL).any():
            raise ValueError(
                f"Kolom '{kolom}' bevat de letterlijke waarde {NULL_SENTINEL!r}, "
                "die bij het schrijven als NULL gelezen zou worden."
            )

    buffer = io.StringIO()
    df[kolommen].to_csv(buffer, index=False, header=False, na_rep=NULL_SENTINEL)
    buffer.seek(0)
    return buffer


def schrijf(
    verbinding,
    tabel: str,
    df: pd.DataFrame,
    kolommen: list[str],
    sleutel: list[str],
) -> int:
    """Schrijf een DataFrame weg. Alles of niets.

    Geeft het aantal weggeschreven rijen terug. Commit gebeurt hier niet: de
    aanroeper bepaalt de transactiegrens, zodat meerdere tabellen samen kunnen
    slagen of falen.
    """
    controleer_kolommen(df, f"tabel {tabel}")

    ontbreekt = set(kolommen) - set(df.columns)
    if ontbreekt:
        raise ValueError(f"{tabel}: DataFrame mist kolommen {sorted(ontbreekt)}")

    if df.empty:
        return 0

    tijdelijk = f"tijdelijk_{tabel}"
    with verbinding.cursor() as cur:
        # `on commit drop` ruimt zichzelf op, ook als er iets misgaat.
        cur.execute(
            f"create temporary table {tijdelijk} "
            f"(like public.{tabel} including defaults) on commit drop"
        )
        velden = ", ".join(kolommen)
        with cur.copy(
            f"copy {tijdelijk} ({velden}) from stdin "
            f"with (format csv, null '{NULL_SENTINEL}')"
        ) as kopie:
            kopie.write(_naar_csv_buffer(df, kolommen).read())

        cur.execute(upsert_sql(tabel, kolommen, sleutel))
        # `cur.rowcount` en niet `len(df)`: dit getal gaat naar de
        # etl_run-boekhouding, en die hoort te melden wat de database heeft
        # aangenomen -- niet wat wij hebben aangeboden. Bij `do nothing`
        # (fact_kanaalkost) lopen die twee uiteen, en dat verschil is
        # informatie, geen ruis.
        return cur.rowcount


# --- de dodemansknop --------------------------------------------------------
#
# `etl_run` werkt alleen als hij aan het BEGIN geschreven wordt en aan het
# eind afgesloten. Een run die halverwege sterft laat dan een rij achter met
# status 'bezig', en dát is het signaal. Zou je de rij pas aan het eind
# wegschrijven, dan is een gestorven run niet te onderscheiden van een cron
# die nooit gevuurd heeft -- en dat is precies het onderscheid waar een
# dodemansknop voor bestaat.


def start_run(verbinding, bron: str) -> int:
    """Open een run en geef zijn id terug. Commit meteen.

    De commit is essentieel: valt het proces daarna om, dan moet die rij er
    staan. Een 'bezig'-rij die in een teruggedraaide transactie zat, bestaat
    voor niemand.
    """
    with verbinding.cursor() as cur:
        cur.execute(
            "insert into public.etl_run (bron, status) values (%s, 'bezig') "
            "returning id",
            (bron,),
        )
        run_id = cur.fetchone()[0]
    verbinding.commit()
    return run_id


def eind_run(
    verbinding, run_id: int, status: str, rijen: int | None = None,
    melding: str | None = None,
) -> None:
    """Sluit een run af als 'goed' of 'fout'.

    `melding` gaat naar een kolom die elke ingelogde gebruiker kan lezen. Daar
    hoort dus een foutmelding in en nooit een datarij -- zie het commentaar bij
    de kolom in 003_etl_run.sql.
    """
    if status not in ("goed", "fout"):
        raise ValueError(f"status moet 'goed' of 'fout' zijn, niet {status!r}")
    with verbinding.cursor() as cur:
        cur.execute(
            "update public.etl_run set status = %s, geeindigd_op = now(), "
            "rijen = %s, melding = %s where id = %s",
            (status, rijen, melding, run_id),
        )
    verbinding.commit()
