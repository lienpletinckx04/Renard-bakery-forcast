"""Haalt de agenda van de bakkerij op en zegt wat erin staat.

Dit is de handmatige kant van het agendaspoor (vraag 46). Draaien:

    python3 scripts/agenda_ophalen.py            # of: make agenda
    python3 scripts/agenda_ophalen.py --detail   # ook de dagen zelf
    python3 scripts/agenda_ophalen.py --streng   # exitcode 1 bij een kapotte feed
    python3 scripts/agenda_ophalen.py --bestand data/raw/agenda.ics

TWEE DINGEN OVER DE EXITCODE. Standaard is het antwoord altijd 0, ook als de
feed onbereikbaar is of niet ingesteld — een agenda die er niet is, mag de
nachtelijke keten niet omleggen. Wie het wél als een fout wil zien (een monitor
bijvoorbeeld), draait met `--streng`; dan geeft alleen een ingestelde maar
onbruikbare feed exitcode 1, en een niet-ingestelde feed nog steeds 0.

OVER WAT ER GEPRINT WORDT. Een reden in een agenda kan een persoonlijk gegeven
zijn ("DICHT: begrafenis"). Standaard toont dit script daarom tellingen, het
datumbereik en de waarschuwingen — die laatste zijn nodig om de agenda te
kunnen repareren. De dagen met hun redenen komen er alleen bij met `--detail`.
De opgehaalde .ics gaat naar data/raw/ en die map is gitignored.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bakkerij.sources.agenda import KENMERKEN, Agenda, lees_ics
from bakkerij.sources.agenda_ophaal import (
    SLEUTEL,
    haal_agenda_en_tekst,
    kort_adres,
    lees_instelling,
)

BEWAARPAD = REPO / "data" / "raw" / "agenda.ics"


def uit_bestand(pad: Path) -> Agenda:
    """Dezelfde laag, maar op een .ics die iemand doorgestuurd heeft.

    Bestaat omdat een klant die geen link kan delen wel een export kan mailen,
    en omdat je het spoor zo kunt narekenen zonder netwerk.
    """
    try:
        tekst = pad.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Agenda(bruikbaar=False, reden_onbruikbaar=f"Geen bestand op {pad}")
    except (OSError, UnicodeDecodeError) as fout:
        return Agenda(bruikbaar=False,
                      reden_onbruikbaar=f"{pad} is niet te lezen: {type(fout).__name__}")
    return lees_ics(tekst)


def toon(agenda: Agenda, detail: bool) -> None:
    if not agenda.bruikbaar:
        print(f"onbruikbaar       : {agenda.reden_onbruikbaar}")
    if agenda.van and agenda.tot:
        print(f"bereik            : {agenda.van}  ->  {agenda.tot}")
    print(f"dagen met kenmerk : {len(agenda.dagen):>5}")

    per_kenmerk = Counter(d.kenmerk for d in agenda.dagen)
    for kolom in KENMERKEN.values():
        print(f"  {kolom:<16}: {per_kenmerk.get(kolom, 0):>5} dagen")

    if agenda.waarschuwingen:
        print(f"\n{len(agenda.waarschuwingen)} waarschuwing(en) — dit is wat de "
              "agenda niet gelezen kreeg:")
        for w in agenda.waarschuwingen:
            print(f"  - {w}")

    if detail and agenda.dagen:
        print("\ndagen:")
        for d in agenda.dagen:
            print(f"  {d.datum}  {d.kenmerk:<16} {d.reden}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bestand", help="lees een lokale .ics in plaats van de feed")
    p.add_argument("--detail", action="store_true", help="ook de dagen en de redenen")
    p.add_argument("--streng", action="store_true",
                   help="exitcode 1 als een ingestelde feed onbruikbaar is")
    p.add_argument("--niet-bewaren", action="store_true",
                   help="schrijf de opgehaalde .ics niet naar data/raw/")
    args = p.parse_args()

    if args.bestand:
        print(f"bron              : {args.bestand}")
        agenda = uit_bestand(Path(args.bestand))
        toon(agenda, args.detail)
        return 1 if (args.streng and not agenda.bruikbaar) else 0

    instelling = lees_instelling()
    if not instelling.ingesteld:
        # Geen configuratie is hier geen fout maar de normale toestand zolang
        # vraag 46 openstaat. De laag doet niets en zegt dat ook.
        print(f"{SLEUTEL} is niet ingesteld ({instelling.herkomst}).")
        print("De agendalaag doet niets: geen kolommen, geen aannames, geen "
              "verschil in de cijfers.")
        return 0

    print(f"bron              : {kort_adres(instelling.url)}  ({instelling.herkomst})")
    agenda, ruw = haal_agenda_en_tekst(instelling)
    toon(agenda, args.detail)

    if ruw and not args.niet_bewaren:
        # De opgehaalde feed blijft staan zoals hij binnenkwam: dat is het enige
        # bewijsstuk als de klant morgen vraagt waarom een dag dicht stond.
        # data/raw is gitignored, dus dit gaat de repo nooit in.
        BEWAARPAD.parent.mkdir(parents=True, exist_ok=True)
        BEWAARPAD.write_text(ruw, encoding="utf-8")
        print(f"\ngeschreven        : {BEWAARPAD.relative_to(REPO)}")

    return 1 if (args.streng and not agenda.bruikbaar) else 0


if __name__ == "__main__":
    raise SystemExit(main())
