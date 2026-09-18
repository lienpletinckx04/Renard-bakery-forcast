"""Bouwt het canonieke datamodel uit de bronextracten.

Leest het jongste Odoo-werkextract (data/raw) en de TGTG-dagen en -maanden
(data/interim), en schrijft:

    data/interim/canoniek_verkopen.csv   datum | filiaal_id | product_id |
                                         product_naam | kanaal | aantal |
                                         omzet_excl_btw
    data/interim/canoniek_kalender.csv   kalender + winkel_gemeten + winkel_open

Deliveroo is als kanaal gedefinieerd maar leeg; het script toont dat expliciet
als onbeschikbaar met reden, conform harde regel 8. De keuzes (alle drie de
kassa's, netto TGTG-omzet, sluitingsdag = geen meting) staan in
bakkerij/canoniek.py, niet hier.

TWEE PLEKKEN WAAR TGTG VANDAAN KAN KOMEN (19 aug 2026)

Normaal de bestanden in data/interim. Ontbreken die én staat CONTRACT_BRON op
`db`, dan komt het kanaal uit de database terug — zie `haal_tgtg` hieronder en
`bakkerij/db/bevroren.py` voor het waarom. Dat is wat de nachtelijke ketting op
een GitHub-runner mogelijk maakt: daar bestaat data/interim niet, want die map
is gitignored.

Draaien:  make canoniek
"""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pandas as pd

from bakkerij import canoniek, sluitingsdagen, sluitingskalender
from bakkerij.db import contract_bron, droge_modus
from bakkerij.omgeving import laad_env

# Als `agenda_afwijkingen`, niet kaal: sluitingsdagen.afwijkingen bestaat ook,
# wordt hieronder gekwalificeerd aangeroepen, en twee gelijknamige functies in
# één bestand waarvan één onzichtbaar is in de aanroep, is vragen om de
# verkeerde (audit 18 aug).
from bakkerij.sources.agenda import afwijkingen as agenda_afwijkingen
from bakkerij.sources.agenda import lees_ics, verrijk_kalender

RAW = REPO / "data" / "raw"
INTERIM = REPO / "data" / "interim"
REPORTS = REPO / "reports"

#: De sluitingsdagen die de bakkerij vooraf weet. IN GIT, anders dan de rest
#: van de beheerinvoer, en sinds 19 aug 2026 in `config/` in plaats van
#: `data/config/`.
#:
#: `data/` is gitignored omdat daar klantdata staat. Deze lijst bevat er geen —
#: het zijn de dagen dat de zaak dicht is, geen transacties en geen personen —
#: en zolang ze daar tóch stond, kon de nachtelijke synchronisatie op een
#: GitHub-runner niet slagen: zonder deze lijst verdwijnt `gepland_dicht` uit
#: de kalender, en dan meldt het platform een geplande sluiting als
#: achterstand. Precies de fout die op 19 augustus gerepareerd is, langs de
#: achterdeur weer binnen.
SLUITINGEN_PAD = REPO / "config" / "sluitingsdagen.json"

# De opgehaalde agenda (make agenda schrijft dit bestand). Bewust een bestand
# en geen netwerkcall: de canoniekbouw blijft offline en deterministisch, de
# ophaalstap is een aparte, expliciete handeling.
AGENDA_PAD = RAW / "agenda.ics"


def verwerk_agenda(kal: pd.DataFrame) -> pd.DataFrame:
    """Verrijk de kalender met de agenda, als die er ligt (blok 17, restant).

    Zonder agenda.ics verandert er exact niets — dat is de normale toestand
    zolang vraag 46 openstaat. Mét een bruikbare agenda komen de geplande
    kolommen naast de meting te staan (verrijk_kalender raakt winkel_open en
    winkel_gemeten niet aan) en gaat het afwijkingsrapport naar reports/:
    twee onafhankelijke bronnen die over dezelfde sluitingsdagen moeten
    overeenkomen. De redenen uit de agenda blijven buiten het rapport — een
    reden kan een persoonlijk gegeven zijn; de datums en soorten volstaan.
    """
    if not AGENDA_PAD.exists():
        return kal
    agenda = lees_ics(AGENDA_PAD.read_text(encoding="utf-8"))
    if not agenda.bruikbaar:
        print(f"agenda.ics aanwezig maar onbruikbaar: {agenda.reden_onbruikbaar}")
        return kal

    verrijkt = verrijk_kalender(kal, agenda)
    # agenda_afwijkingen() verrijkt zelf; die krijgt dus de kale kalender.
    verschillen = agenda_afwijkingen(kal, agenda)
    REPORTS.mkdir(parents=True, exist_ok=True)
    regels = ["# Agenda naast meting: afwijkingen", ""]
    if verschillen.empty:
        regels.append("Geen afwijkingen: de agenda en de gemeten open dagen "
                      "zijn het binnen het meetbereik eens.")
    else:
        regels.append("| Datum | Gemeten open | Gepland dicht | Soort |")
        regels.append("|---|---|---|---|")
        for rij in verschillen.itertuples():
            regels.append(
                f"| {rij.datum} | {'ja' if rij.winkel_open else 'nee'} | "
                f"{'ja' if rij.gepland_dicht else 'nee'} | {rij.soort} |"
            )
    # Ook het rapport valt onder DROOG: "zonder schrijven" is zonder schrijven.
    if droge_modus():
        print(f"DROOG: agenda-afwijkingen ({len(verschillen)}) niet geschreven")
    else:
        (REPORTS / "agenda-afwijkingen.md").write_text(
            "\n".join(regels) + "\n", encoding="utf-8"
        )
    print(f"agenda: kalender verrijkt ({len(agenda.dagen)} agendadagen), "
          f"{len(verschillen)} afwijkingen -> reports/agenda-afwijkingen.md")
    return verrijkt


def _sluitingen_uit_database():
    """De sluitingskalender uit Postgres, voor de gehoste route.

    Faalt luid en niet stil: op de route waar de database de invoer draagt
    (CONTRACT_BRON=db), betekent "de database gaf geen antwoord" dat de
    bevestigde sluitingen van de beheerder uit de kalender zouden vallen — en
    dan voorspelt het platform omzet op elke dag die het scherm dicht noemt.
    De melding draagt alleen de typenaam; SUPABASE_DB_URL bevat het
    wachtwoord en een driver-fout kan de DSN citeren (zelfde voorzichtigheid
    als kostenrijen_uit_db in contract_bouw.py).
    """
    from bakkerij.db import sluitingen_db
    from bakkerij.db.verbinding import verbind

    try:
        with verbind() as verbinding:
            return sluitingen_db.lees(verbinding)
    except Exception as fout:
        raise SystemExit(
            "sluitingskalender: de database gaf geen antwoord "
            f"({type(fout).__name__}). Onder CONTRACT_BRON=db is de database "
            "de bron van de bevestigde sluitingen; zonder die kalender zou "
            "deze bouw omzet voorspellen op dagen die de beheerder dicht "
            "heeft verklaard. Controleer SUPABASE_DB_URL en migratie 011."
        ) from fout


def verwerk_sluitingen(kal: pd.DataFrame) -> pd.DataFrame:
    """Zet de vooraf bekende sluitingen in de kalender (14 aug 2026).

    Sinds de sluitingskalender (migratie 011) zijn er twee bronnen naast de
    agenda, met een vaste rangorde: **agenda > database > bestand**. De
    agenda komt van de bakkerij zelf en draait eerder (verwerk_agenda); de
    database draagt de uitspraken van de beheerder via het scherm
    Sluitingsdagen; het bestand (config/sluitingsdagen.json) is de oudste
    bron en blijft staan als eenmalige invoer en historisch record.

    De rangorde is geen theorie maar drie concrete regels:
      * een dag die de agenda dicht noemt, blijft dicht, ook als de database
        hem bevestigd open noemt — het conflict wordt gemeld;
      * een bevestigd-open dag uit de database knipt een dicht-dag uit de
        bestandslijst weg (sluitingskalender.zonder_dagen);
      * binnen de database wint de uitspraak van de weekregel.

    Onder CONTRACT_BRON=bestand (een werkplek zonder database) doet alleen
    het bestand mee, zoals voorheen; de kolom `bevestigd_open` komt er dan
    leeg bij, zodat de CSV-vorm op beide routes gelijk is.

    Een fout in het bestand is hier fataal en wordt niet weggeslikt. Een
    sluitingsdag die door een typefout niet meedoet, levert een omzetprognose
    op voor een dag dat de deur dicht is, en dat is precies wat deze laag moet
    voorkomen.
    """
    try:
        lijst = sluitingsdagen.lees_sluitingen(SLUITINGEN_PAD)
    except (ValueError, TypeError) as fout:
        raise SystemExit(
            f"sluitingsdagen.json deugt niet: {fout}\n"
            f"Bestand: {SLUITINGEN_PAD}"
        ) from fout

    if not lijst:
        # Op de gehoste route is een ontbrekende lijst geen "we weten geen
        # sluitingen" maar "er is iets weg dat in git hoort te staan". Het
        # verschil is niet academisch: zonder deze lijst verdwijnt
        # `gepland_dicht` uit de kalender, en dan meldt het platform tijdens de
        # zomersluiting weer een ACHTERSTAND in plaats van een sluiting --
        # precies de fout die op 19 aug 2026 gerepareerd is. De krimpwacht op
        # het contract ziet dat niet: dezelfde sleutels, dezelfde bronnen,
        # alleen een ander verhaal. Dus stopt de bouw hier, luid.
        if contract_bron() == "db":
            raise SystemExit(
                "sluitingsdagen: de lijst ontbreekt terwijl CONTRACT_BRON=db. "
                "Sinds 19 aug 2026 staat ze in git, dus op de gehoste route "
                "betekent 'weg' dat iemand haar verwijderd heeft -- en dan "
                "meldt het platform een geplande sluiting als achterstand.\n"
                f"Verwacht: {SLUITINGEN_PAD}"
            )
        print("sluitingsdagen: geen lijst (config/sluitingsdagen.json "
              "bestaat niet); toekomstige sluitingen zijn onbekend")

    stand = _sluitingen_uit_database() if contract_bron() == "db" else None
    uitspraken = stand.uitspraken if stand else ()
    regels = stand.regels if stand else ()

    # Agenda > database: een bevestigd-open dag die de agenda dicht noemt,
    # wordt niet gezet. Melden, niet stil beslechten — en alleen de datum,
    # nooit de reden: stdout is het Actions-logboek.
    conflicten = sluitingskalender.agenda_conflicten(kal, uitspraken)
    if conflicten:
        print(f"  LET OP: {len(conflicten)} bevestigd-open dag(en) die een "
              "eerdere bron dicht noemt; die bron gaat voor:")
        for dag in conflicten:
            print(f"    {dag}")

    kal = sluitingskalender.verrijk_kalender(kal, uitspraken, regels)
    if stand is not None:
        dicht = sluitingskalender.dichte_dagen(uitspraken)
        open_ = sluitingskalender.open_dagen(uitspraken)
        print(f"sluitingskalender (database): {len(uitspraken)} uitspraken "
              f"({len(dicht)} dicht, {len(open_)} bevestigd open), "
              f"{len(regels)} weekregel(s), bewaard door "
              f"{stand.bewaard_door or '(onbekend)'}")
    elif contract_bron() == "db":
        print("sluitingskalender (database): nog leeg — er is nog niets "
              "bevestigd op het scherm Sluitingsdagen")

    if not lijst:
        return kal

    # Database > bestand: bevestigd-open dagen uit de bestandslijst knippen.
    effectief = sluitingskalender.zonder_dagen(
        lijst, sluitingskalender.open_dagen(uitspraken))
    geknipt = (len(sluitingsdagen.dagen_met_reden(lijst))
               - len(sluitingsdagen.dagen_met_reden(effectief)))
    if geknipt:
        print(f"  {geknipt} dag(en) uit de bestandslijst geknipt: in de "
              "database bevestigd open, en de database gaat voor het bestand")

    verrijkt = sluitingsdagen.verrijk_kalender(kal, effectief)
    verschillen = sluitingsdagen.afwijkingen(kal, effectief)
    dagen = len(sluitingsdagen.dagen_met_reden(effectief))
    tot = sluitingsdagen.dekking_tot(lijst)
    print(f"sluitingsdagen (bestand): {len(effectief)} periodes, {dagen} "
          f"dagen, lijst reikt tot {tot}")
    if not verschillen.empty:
        print(f"  LET OP: {len(verschillen)} dag(en) staan in de lijst als "
              "gesloten terwijl de kassa verkocht. De meting blijft de "
              "waarheid; controleer de lijst.")
        for rij in verschillen.itertuples():
            # Alleen de datum, nooit de reden: stdout is het Actions-logboek,
            # en een reden kan een persoonlijk gegeven zijn (zie verwerk_agenda).
            print(f"    {rij.datum}")
    return verrijkt


def laatste(patroon: str, map_: Path) -> Path:
    treffers = sorted(map_.glob(patroon))
    if not treffers:
        raise SystemExit(f"Geen bestand gevonden voor {patroon} in {map_}")
    return treffers[-1]


def _schrijf_csv(df, pad) -> None:
    """Atomair: eerst een tijdelijk bestand, dan os.replace. `make contract`
    kan tegelijk draaien en mag nooit een afgekapte CSV lezen.

    Onder DROOG wordt er niets geschreven. Tot 18 aug 2026 negeerde dit
    script de vlag, terwijl `make sync-droog` "zonder schrijven" beloofde:
    een droge proef op een productiemachine overschreef dan stil de laatste
    goede bouw. De hele bouw en alle controles draaien wél — alleen de
    laatste stap, het wegschrijven, valt weg.
    """
    if droge_modus():
        print(f"DROOG: {len(df):,} rijen niet geschreven naar {pad.name}")
        return
    tmp = pad.with_name(pad.name + ".tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, pad)


#: De TGTG-bestanden die de canoniekbouw normaal leest. Buiten git, zoals alle
#: data: de bronbestanden zijn pdf's met klantdata erin (harde regel 2).
TGTG_BESTANDEN = ("tgtg_dagen.csv", "tgtg_maanden.csv")


def _tgtg_uit_bestanden() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Het gewone pad: de verwerkte TGTG-bestanden zijn de bron."""
    dagen = pd.read_csv(INTERIM / "tgtg_dagen.csv")
    maanden = pd.read_csv(INTERIM / "tgtg_maanden.csv")
    return (canoniek.tgtg_naar_canoniek(dagen, maanden),
            canoniek.kanaalkost_tgtg(dagen, maanden))


def _tgtg_uit_database() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Het runnerpad: het bevroren kanaal komt uit de bewaarplaats terug.

    Zie `bakkerij/db/bevroren.py` voor waarom dit mag en wanneer. Kort: TGTG
    krijgt sinds 17 augustus geen nieuwe aanvoer meer, dus wat in de database
    staat ís de historiek. Hier wordt niets herberekend — ook de commissiewig
    komt terug zoals hij erin ging, want die twee keer afleiden zou betekenen
    dat de commissieregel op twee plaatsen staat.
    """
    from bakkerij.db.bevroren import lees_kanaalkost, lees_verkopen
    from bakkerij.db.verbinding import verbind

    with verbind() as verbinding:
        return (lees_verkopen(verbinding, "tgtg"),
                lees_kanaalkost(verbinding, "tgtg"))


def haal_tgtg() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Het TGTG-kanaal, uit de bestanden of anders uit de database.

    De bestanden gaan vóór, altijd: zij zijn de bron en de database is er maar
    de bewaarplaats van. Ontbreken ze, dan hangt het ervan af waar deze bouw
    draait. Op een runner (CONTRACT_BRON=db) is de database het antwoord; op
    een werkplek is het ontbreken van de bestanden gewoon een fout, en dan is
    de oude melding nog steeds de juiste.
    """
    ontbreekt = [n for n in TGTG_BESTANDEN if not (INTERIM / n).exists()]
    if not ontbreekt:
        return _tgtg_uit_bestanden()

    if contract_bron() != "db":
        raise SystemExit(
            f"{', '.join(ontbreekt)} ontbreekt. Draai eerst: make tgtg. "
            "(Draait dit op een runner zonder data/interim/, zet dan "
            "CONTRACT_BRON=db; dan komt het bevroren TGTG-kanaal uit de "
            "database.)"
        )

    print(f"TGTG: {', '.join(ontbreekt)} ontbreekt, het kanaal komt uit de "
          "database (bevroren historiek, zie bakkerij/db/bevroren.py)")
    tgtg, kanaalkost = _tgtg_uit_database()
    print(f"TGTG: {len(tgtg):,} verkoopregels terug, "
          f"{tgtg['datum'].min()} t/m {tgtg['datum'].max()}, "
          f"{len(kanaalkost)} maanden kanaalkost")
    return tgtg, kanaalkost


def main() -> int:
    # Nodig vóór haal_tgtg(): het databasepad leest CONTRACT_BRON en de
    # verbindingsstring uit de omgeving, en op een werkplek staan die in .env.
    laad_env()
    winkel_pad = laatste("*_odoo_verkopen_*.csv", RAW)
    tgtg, kanaalkost = haal_tgtg()

    winkel = canoniek.laad_winkel(winkel_pad)
    verkopen = canoniek.bouw_verkopen(winkel, tgtg)
    kal = canoniek.bouw_kalender(verkopen)
    kal = verwerk_agenda(kal)
    kal = verwerk_sluitingen(kal)

    _schrijf_csv(verkopen, INTERIM / "canoniek_verkopen.csv")
    _schrijf_csv(kal, INTERIM / "canoniek_kalender.csv")
    _schrijf_csv(kanaalkost, INTERIM / "canoniek_kanaalkost.csv")

    # De twee jongere extracties zijn optioneel: zonder bonnen geen traffic-as
    # en zonder uren geen uitverkoopsignaal, maar de rest van het model draait.
    # Ontbreken wordt gemeld, niet verzwegen (harde regel 8).
    aanvullend = {
        "bonnen": ("*_odoo_bonnen_*.csv", canoniek.laad_bonnen, "canoniek_bonnen.csv"),
        "uren": ("*_odoo_laatste_uur_*.csv", canoniek.laad_uren, "canoniek_uren.csv"),
    }
    aanvullend_status = {}
    for naam, (patroon, lader, uit) in aanvullend.items():
        treffers = sorted(RAW.glob(patroon))
        if treffers:
            frame = lader(treffers[-1])
            _schrijf_csv(frame, INTERIM / uit)
            aanvullend_status[naam] = f"{len(frame):,} rijen -> {uit} (bron {treffers[-1].name})"
        else:
            aanvullend_status[naam] = f"ONBESCHIKBAAR: geen {patroon} in data/raw"

    print("=" * 64)
    print("CANONIEK DATAMODEL")
    print("=" * 64)
    print(f"bron winkel : {winkel_pad.name}")
    print(f"verkopen    : {len(verkopen):,} rijen -> canoniek_verkopen.csv")
    for s in canoniek.kanaalstatus(verkopen):
        if s["beschikbaar"]:
            print(f"  {s['kanaal']:<10} {s['van']} -> {s['tot']}")
        else:
            print(f"  {s['kanaal']:<10} ONBESCHIKBAAR: {s['reden']}")

    gemeten = kal[kal["winkel_gemeten"]]
    dicht = int((~gemeten["winkel_open"]).sum())
    for naam, status in aanvullend_status.items():
        print(f"{naam:<12}: {status}")
    print(f"kalender    : {len(kal):,} dagen -> canoniek_kalender.csv")
    print(f"  gemeten bereik winkel: {len(gemeten):,} dagen, "
          f"waarvan {dicht} zonder kassaverkoop (= gesloten, geen nulomzet)")
    print(f"  feestdagen in het bereik: {int(kal['feestdag'].sum())}")
    print("\nKlaar. data/ is gitignored. Controleer met: make check-data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
