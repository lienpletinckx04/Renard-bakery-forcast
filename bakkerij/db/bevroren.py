"""Een bevroren kanaal teruglezen uit de database, in canonieke vorm.

WAAROM DIT BESTAAT

De nachtelijke sync draait op een GitHub-runner, en die krijgt precies wat er
in git staat plus wat hij zelf uit Odoo haalt. Het winkelkanaal komt uit Odoo
en is dus elke nacht compleet. TGTG niet: dat kanaal komt uit 250 pdf's die tot
`data/interim/tgtg_dagen.csv` verwerkt zijn, en die map is gitignored omdat er
klantdata in de bronbestanden zit (harde regel 2). Op de runner bestaat ze niet.

Tot 19 augustus 2026 stopte `canoniek_bouw.py` daarop met een duidelijke fout
("tgtg_dagen.csv ontbreekt"). Dat is eerlijk maar niet werkbaar: het betekent
dat de nachtelijke ketting op geen enkele runner kan slagen, en dus dat de
cron niet aan kan.

Er is een uitweg, en die is er alleen omdat dit kanaal BEVROREN is. Blok 9 (de
ingestmailbox) is op 17 augustus geschrapt op vraag van de opdrachtgever, dus
er komt geen nieuwe TGTG-aanvoer meer: de historiek loopt tot juli 2026 en
blijft daar staan. Wat bevroren is, hoeft niet elke nacht opnieuw uit de bron
gebouwd te worden — het staat al in `fact_verkoop`, geaggregeerd, precies zoals
harde regel 3 het toestaat. De database is voor dit kanaal de bewaarplaats
geworden.

WAT DIT NIET IS

Geen tweede waarheid. Zolang de TGTG-bestanden bestaan, blijven zij de bron en
raakt deze module niets aan; `canoniek_bouw.py` valt hier alleen op terug als
ze er niet zijn. En geen berekening: wat eruit komt is bit voor bit wat er in
ging, alleen weer als DataFrame. Zou hier ook maar één cijfer opnieuw berekend
worden, dan bestond de commissieafleiding op twee plaatsen.

WAT ER GEBEURT ALS DIT MISLUKT

Niets stils. Levert de database geen rijen voor het kanaal, dan werpt deze
module; en zou ze onverhoopt tóch minder leveren dan er stond, dan weigert de
krimpwacht in `scripts/contract_laad.py` het armere contract (zie
`contract_rijen.verarming`). Twee wachten op dezelfde fout, want dit is precies
het pad waarop niemand meekijkt.
"""

from __future__ import annotations

import pandas as pd

from bakkerij.canoniek import KANALEN, KOLOMMEN

#: De canonieke verkoopregels van één kanaal, met de productnaam erbij.
#: `dim_product` draagt die naam; `fact_verkoop` kent alleen het id.
VERKOPEN_SQL = """
select v.datum, v.filiaal_id, v.product_id, p.product_naam,
       v.kanaal, v.aantal, v.omzet_excl_btw
  from public.fact_verkoop v
  join public.dim_product p on p.product_id = v.product_id
 where v.kanaal = %s
 order by v.datum, v.filiaal_id, v.product_id
"""

#: De kanaalwig per maand: bruto, commissie, inhouding.
KANAALKOST_SQL = """
select kanaal, maand, stuks, bruto_per_stuk, commissie_per_stuk, inhouding_pct
  from public.fact_kanaalkost
 where kanaal = %s
 order by maand
"""

#: De kolommen die als getal terug moeten, niet als Decimal. De canonieke CSV
#: draagt floats -- dat is voor pandas onvermijdelijk (zie `bakkerij/db/laden.py`)
#: -- en een kolom die half Decimal en half float is, wordt bij het samenvoegen
#: van de kanalen een objectkolom die verderop stil anders rekent.
VERKOPEN_GETALLEN = ("aantal", "omzet_excl_btw")
KANAALKOST_GETALLEN = ("stuks", "bruto_per_stuk", "commissie_per_stuk",
                       "inhouding_pct")


def _naar_frame(rijen, kolommen: list[str], getallen) -> pd.DataFrame:
    df = pd.DataFrame(rijen, columns=kolommen)
    for kolom in getallen:
        df[kolom] = df[kolom].astype(float)
    return df


def lees_verkopen(verbinding, kanaal: str) -> pd.DataFrame:
    """De canonieke verkoopregels van één kanaal, zoals ze erin gingen.

    Werpt wanneer het kanaal geen enkele rij oplevert. Dat is opzet: deze
    functie wordt alleen aangeroepen omdat de bronbestanden ontbraken, en een
    leeg antwoord betekent dan dat het kanaal nergens meer bestaat. Stil een
    leeg frame teruggeven zou de bouw laten slagen met een kanaal minder.
    """
    if kanaal not in KANALEN:
        raise ValueError(f"onbekend kanaal {kanaal!r} (keuze: {list(KANALEN)})")

    with verbinding.cursor() as cur:
        cur.execute(VERKOPEN_SQL, (kanaal,))
        rijen = cur.fetchall()

    if not rijen:
        raise ValueError(
            f"de database draagt geen enkele verkoopregel voor kanaal "
            f"{kanaal!r}. De bronbestanden ontbreken én de bewaarplaats is "
            f"leeg; er is dus niets om dit kanaal mee te bouwen."
        )

    df = _naar_frame(rijen, KOLOMMEN, VERKOPEN_GETALLEN)
    df["datum"] = pd.to_datetime(df["datum"]).dt.date
    return df[KOLOMMEN]


def lees_kanaalkost(verbinding, kanaal: str) -> pd.DataFrame:
    """De kanaalwig per maand. Leeg mag hier wél.

    Anders dan bij de verkopen is een leeg antwoord hier geen alarm: een kanaal
    zonder commissie heeft geen wig, en het kanaalscherm toont die dan als
    onbeschikbaar met reden in plaats van als nul.
    """
    kolommen = ["kanaal", "maand", "stuks", "bruto_per_stuk",
                "commissie_per_stuk", "inhouding_pct"]
    with verbinding.cursor() as cur:
        cur.execute(KANAALKOST_SQL, (kanaal,))
        rijen = cur.fetchall()
    return _naar_frame(rijen, kolommen, KANAALKOST_GETALLEN)
