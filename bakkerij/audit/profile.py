"""Dag-1 dataprofiler.

Draait vóór er iets gemodelleerd wordt en beantwoordt de blokken uit
docs/data-audit.md met echte cijfers.

    python -m bakkerij.audit.profile data/raw/export.csv

Bewust ontworpen om **niets** te tonen dat klantdata is. Kolomnamen, aantallen,
percentages, datumbereiken en categorie-aantallen wel. Waarden uit de rijen
niet. Daardoor mag de output van dit script wél in een modelcontext of in een
mail aan de opdrachtgever, en de brondata niet.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from bakkerij.io_load import (
    laad,
    parse_datums,
    parse_getallen,
    raad_kanaal,
    raad_kolommen,
)

LIJN = "=" * 78
DUN = "-" * 78


def _kop(tekst: str) -> None:
    print(f"\n{LIJN}\n{tekst}\n{LIJN}")


def _sub(tekst: str) -> None:
    print(f"\n{tekst}\n{DUN}")


def _oordeel(conditie: bool | None, groen: str, amber: str, rood: str) -> str:
    if conditie is None:
        return f"  AMBER  {amber}"
    return f"  GROEN  {groen}" if conditie else f"  ROOD   {rood}"


def blok_vorm(df: pd.DataFrame, pad: Path) -> None:
    _kop(f"BLOK 0  VORM  ({pad.name})")
    print(f"  Rijen:    {len(df):,}".replace(",", "."))
    print(f"  Kolommen: {len(df.columns)}")
    grootte_mb = pad.stat().st_size / 1_048_576
    print(f"  Bestand:  {grootte_mb:.1f} MB")

    _sub("Kolommen, gevuldheid en aantal unieke waarden")
    print(f"  {'kolom':<34} {'gevuld':>8}  {'uniek':>10}")
    for kolom in df.columns:
        gevuld = df[kolom].notna().mean() * 100
        uniek = df[kolom].nunique(dropna=True)
        vlag = "  <- leeg" if gevuld < 1 else ("  <- constant" if uniek <= 1 else "")
        print(f"  {str(kolom)[:34]:<34} {gevuld:7.1f}% {uniek:10,}{vlag}".replace(",", "."))


def blok_rollen(df: pd.DataFrame) -> dict:
    _kop("BLOK B  GRANULARITEIT  (welke kolom speelt welke rol)")
    gokken = raad_kolommen(df)
    for rol, gok in gokken.items():
        if gok.kolom is None:
            print(f"  {rol:<10} NIET GEVONDEN")
            continue
        merk = "zeker" if gok.zeker else "ONZEKER, bevestigen"
        print(f"  {rol:<10} {gok.kolom!s:<34} ({merk})")
        if not gok.zeker and len(gok.kandidaten) > 1:
            alt = ", ".join(str(k) for k, _ in gok.kandidaten[1:4])
            print(f"  {'':<10} alternatieven: {alt}")

    ontbreekt = [r for r in ("datum", "product", "aantal") if gokken[r].kolom is None]
    print()
    print(_oordeel(
        not ontbreekt,
        "datum, product en aantal zijn alle drie aanwezig",
        "",
        f"ontbreekt: {', '.join(ontbreekt)}. Zonder deze drie is er geen model.",
    ))
    if gokken["filiaal"].kolom is None:
        print("  AMBER  geen filiaalkolom. Voorspelling wordt keten-breed, "
              "niet per vestiging. Uitvragen vóór dag 2.")
    if gokken["kanaal"].kolom is None:
        print("  AMBER  geen kanaalkolom. De beslislaag met marges per kanaal "
              "kan dan niet. Zie docs/data-audit.md blok F.")
    return gokken


def blok_historiek(df: pd.DataFrame, datumkolom: str | None) -> pd.Series | None:
    _kop("BLOK C  HISTORIEK")
    if datumkolom is None:
        print("  ROOD   geen datumkolom herkend, historiek niet te beoordelen.")
        return None

    datums = parse_datums(df[datumkolom])
    onparseerbaar = datums.isna().mean() * 100
    geldig = datums.dropna()
    if geldig.empty:
        print(f"  ROOD   kolom '{datumkolom}' bevat geen parseerbare datums.")
        return None

    eerste, laatste = geldig.min(), geldig.max()
    maanden = (laatste.year - eerste.year) * 12 + (laatste.month - eerste.month)
    print(f"  Kolom:         {datumkolom}")
    print(f"  Onparseerbaar: {onparseerbaar:.2f}%")
    print(f"  Bereik:        {eerste:%d-%m-%Y} tot {laatste:%d-%m-%Y}")
    print(f"  Duur:          {maanden} maanden ({(laatste - eerste).days} dagen)")
    print()
    print(_oordeel(
        maanden >= 12,
        "minstens één volledige jaarcyclus aanwezig",
        "",
        f"slechts {maanden} maanden. Kalendereffecten (Pasen, kerst, "
        f"schoolvakanties) zijn niet leerbaar. Zie docs/aannames.md A2.",
    ))
    if maanden >= 24:
        print("  GROEN  meer dan twee jaar: jaar-op-jaar-vergelijking mogelijk.")

    _sub("Volume per maand (om breuken en systeemwissels te zien)")
    per_maand = geldig.dt.to_period("M").value_counts().sort_index()
    if len(per_maand) > 0:
        piek = per_maand.max()
        for periode, aantal in per_maand.items():
            balk = "#" * int(40 * aantal / piek) if piek else ""
            print(f"  {periode}  {aantal:>8,}".replace(",", ".") + f"  {balk}")
        mediaan = per_maand.median()
        verdacht = per_maand[per_maand < mediaan * 0.4]
        if len(verdacht) > 0:
            print(f"\n  AMBER  {len(verdacht)} maand(en) met minder dan 40% van het "
                  "mediaanvolume. Systeemwissel, sluiting of onvolledige export? "
                  "Uitvragen vóór je erop traint.")
    return datums


def blok_volledigheid(datums: pd.Series | None) -> None:
    _kop("BLOK D  VOLLEDIGHEID")
    if datums is None:
        print("  overgeslagen, geen datums.")
        return

    dagen = datums.dropna().dt.normalize()
    aanwezig = pd.DatetimeIndex(sorted(dagen.unique()))
    if len(aanwezig) < 2:
        print("  ROOD   minder dan twee verschillende dagen in de data.")
        return

    volledig = pd.date_range(aanwezig.min(), aanwezig.max(), freq="D")
    ontbrekend = volledig.difference(aanwezig)
    pct = len(ontbrekend) / len(volledig) * 100
    print(f"  Kalenderdagen in bereik: {len(volledig)}")
    print(f"  Dagen met data:          {len(aanwezig)}")
    print(f"  Ontbrekende dagen:       {len(ontbrekend)} ({pct:.1f}%)")

    if len(ontbrekend) > 0:
        per_weekdag = pd.Series(ontbrekend.dayofweek).value_counts().sort_index()
        namen = ["ma", "di", "wo", "do", "vr", "za", "zo"]
        verdeling = ", ".join(f"{namen[i]}:{n}" for i, n in per_weekdag.items())
        print(f"  Verdeling per weekdag:   {verdeling}")
        dominant = per_weekdag.idxmax()
        if per_weekdag.max() > len(ontbrekend) * 0.6:
            print(f"\n  GROEN  ontbrekende dagen zitten vooral op {namen[dominant]}. "
                  "Dat is waarschijnlijk de wekelijkse sluitingsdag, geen datagat.")
            print("         BELANGRIJK: een sluitingsdag is geen nulvraag maar een "
                  "niet-meting. Nooit als nul meetrainen.")
        else:
            print("\n  AMBER  ontbrekende dagen zijn verspreid. Dat wijst eerder op "
                  "een onvolledige export dan op sluitingsdagen. Uitvragen.")
    else:
        print("\n  AMBER  geen enkele ontbrekende dag. Controleer of sluitingsdagen "
              "als nul geregistreerd worden, want dan is nul geen echte nulvraag.")


def blok_meetwaarden(df: pd.DataFrame, gokken: dict) -> None:
    _kop("BLOK D2  MEETWAARDEN")
    for rol in ("aantal", "omzet"):
        kolom = gokken[rol].kolom
        if kolom is None:
            print(f"  {rol}: geen kolom herkend.")
            continue
        waarden = parse_getallen(df[kolom])
        geldig = waarden.dropna()
        if geldig.empty:
            print(f"  {rol} ({kolom}): geen parseerbare getallen.")
            continue
        negatief = (geldig < 0).sum()
        nul = (geldig == 0).sum()
        print(f"\n  {rol} ({kolom})")
        print(f"    onparseerbaar: {waarden.isna().mean() * 100:.2f}%")
        print(f"    negatief:      {negatief:,} rijen".replace(",", "."))
        print(f"    nul:           {nul:,} rijen".replace(",", "."))
        for label, q in (("p50", 0.5), ("p90", 0.9), ("p99", 0.99), ("max", 1.0)):
            print(f"    {label}: {geldig.quantile(q):,.2f}".replace(",", "."))
        if negatief > 0:
            print("    AMBER  negatieve waarden zijn waarschijnlijk retours of "
                  "correcties. Beslis expliciet: verrekenen of uitsluiten. "
                  "Noteer in docs/beslissingen.md.")
        uitschieter = geldig.quantile(0.99) * 20
        extreem = (geldig > uitschieter).sum() if uitschieter > 0 else 0
        if extreem > 0:
            print(f"    AMBER  {extreem} waarden liggen boven twintig maal p99. "
                  "Groothandelsbestellingen of eenheidsfouten? Uitzoeken vóór "
                  "je erop traint, want ze domineren elk gemiddelde.")


def blok_dimensies(df: pd.DataFrame, gokken: dict, datums: pd.Series | None) -> None:
    _kop("BLOK B2  DIMENSIES EN DICHTHEID")
    prod = gokken["product"].kolom
    fil = gokken["filiaal"].kolom

    n_prod = df[prod].nunique() if prod else 0
    n_fil = df[fil].nunique() if fil else 1
    n_dagen = datums.dt.normalize().nunique() if datums is not None else 0
    print(f"  Producten: {n_prod:,}".replace(",", "."))
    print(f"  Filialen:  {n_fil:,}".replace(",", "."))
    print(f"  Dagen:     {n_dagen:,}".replace(",", "."))

    if n_prod and n_dagen:
        cellen = n_prod * max(n_fil, 1) * n_dagen
        dichtheid = len(df) / cellen * 100
        print(f"  Mogelijke combinaties product x filiaal x dag: {cellen:,}".replace(",", "."))
        print(f"  Dichtheid: {dichtheid:.1f}% van de cellen heeft minstens één rij")
        print()
        if dichtheid < 5:
            print("  AMBER  zeer dun. De meeste producten worden niet elke dag in "
                  "elk filiaal verkocht. Modelleer op productgroep, niet per "
                  "artikel, en leen spreiding van de groep.")
        else:
            print("  GROEN  voldoende dicht om per product te modelleren, "
                  "minstens voor de kopgroep.")

    if prod:
        _sub("Concentratie: hoeveel producten dragen het volume")
        telling = df[prod].value_counts()
        cum = telling.cumsum() / telling.sum()
        for drempel in (0.5, 0.8, 0.95):
            n = int((cum <= drempel).sum()) + 1
            print(f"  {drempel:.0%} van de rijen komt van {n} producten "
                  f"({n / len(telling):.1%} van het assortiment)")
        print("\n  Modelleer de kopgroep goed en de staart eenvoudig. De staart "
              "kost meer rekentijd dan hij aan marge oplevert.")

    if prod and datums is not None:
        _sub("Naamswijzigingen: producten die stoppen en beginnen op dezelfde dag")
        tijdelijk = pd.DataFrame({"p": df[prod], "d": datums}).dropna()
        bereik = tijdelijk.groupby("p")["d"].agg(["min", "max"])
        einden = bereik["max"].dt.normalize().value_counts()
        starts = bereik["min"].dt.normalize().value_counts()
        gedeeld = sorted(set(einden.index) & set(starts.index))
        verdacht = [
            (d, int(einden[d]), int(starts[d]))
            for d in gedeeld
            if einden[d] >= 3 and starts[d] >= 3 and d != bereik["min"].min()
        ]
        if verdacht:
            print("  Datums waarop meerdere producten stoppen én meerdere beginnen:")
            for d, e, s in verdacht[:10]:
                print(f"    {d:%d-%m-%Y}: {e} gestopt, {s} gestart")
            print("\n  AMBER  dit patroon betekent meestal hernoemde of samengevoegde "
                  "artikelcodes, niet echte productwissels. Zonder mapping ziet het "
                  "model een reeks die abrupt eindigt en een nieuwe die begint.")
        else:
            print("  GROEN  geen duidelijk patroon van massale hernoemingen.")


def blok_kanalen(df: pd.DataFrame, gokken: dict) -> None:
    _kop("BLOK F  KANALEN")
    kolom = gokken["kanaal"].kolom
    if kolom is None:
        print("  Geen kanaalkolom herkend.")
        print("\n  AMBER  zoek in andere kolommen naar Deliveroo of Too Good To Go. "
              "Als het kanaal nergens in de rij staat, kan de beslislaag niet met "
              "marges per kanaal rekenen, en dat is de scherpste hoek van dit "
              "project. Prioritair uitvragen.")
        gevonden = []
        for k in df.columns:
            monster = df[k].dropna().astype(str).head(2000).str.lower()
            if monster.str.contains("deliveroo|too good|tgtg", regex=True).any():
                gevonden.append(str(k))
        if gevonden:
            print(f"  Kanaaltermen komen wel voor in: {', '.join(gevonden)}")
        return

    genormaliseerd = df[kolom].fillna("").map(raad_kanaal)
    verdeling = genormaliseerd.value_counts(normalize=True) * 100
    print(f"  Kolom: {kolom}")
    for kanaal, pct in verdeling.items():
        print(f"    {kanaal:<12} {pct:5.1f}%")
    if "overig" in verdeling and verdeling["overig"] > 20:
        print("\n  AMBER  meer dan een vijfde valt in 'overig'. De mapping in "
              "io_load.KANAAL_HINTS moet uitgebreid worden met de echte waarden.")
    if "tgtg" in verdeling:
        print("\n  GROEN  Too Good To Go zit in de data. TGTG-volume is de beste "
              "beschikbare proxy voor overschot. Zie docs/data-audit.md blok E.")


def blok_censuur(df: pd.DataFrame) -> None:
    _kop("BLOK E  GECENSUREERDE VRAAG  (het belangrijkste blok)")
    print("  Verkocht is niet hetzelfde als gevraagd. Als een filiaal om elf uur")
    print("  uitverkocht is, meet je de rekcapaciteit en niet de vraag. Een model")
    print("  dat daarop traint, voorspelt structureel te laag en bevestigt zichzelf.")
    print()
    zoektermen = {
        "bakaantal / productie": r"gebakken|productie|bereid|geproduceerd|baked|output",
        "restaantal / derving": r"rest|over|derving|waste|verlies|afval|weggegooid|onverkocht",
        "voorraad": r"voorraad|stock|inventaris|inventory",
        "tijdstip verkoop": r"tijd|uur|time|hour|timestamp",
    }
    import re as _re
    gevonden_iets = False
    for label, patroon in zoektermen.items():
        treffers = [str(k) for k in df.columns if _re.search(patroon, str(k).lower())]
        if treffers:
            gevonden_iets = True
            print(f"  GEVONDEN  {label}: {', '.join(treffers[:5])}")
        else:
            print(f"  ontbreekt  {label}")
    print()
    if gevonden_iets:
        print("  GROEN  er is materiaal om de censuur te corrigeren. Onderzoek per")
        print("         gevonden kolom of hij echt gevuld is en over de hele periode.")
    else:
        print("  AMBER  niets van dit alles gevonden. Het model wordt dan gebouwd op")
        print("         verkoopcijfers, met een expliciete beperking in het rapport,")
        print("         plus de aanbeveling om restaantallen te gaan registreren.")
        print("         Dat advies heeft blijvende waarde en hoort niet in een")
        print("         voetnoot. Zie docs/data-audit.md blok E.")


def blok_slot() -> None:
    _kop("VOLGENDE STAPPEN")
    print("  1. Vul docs/data-audit.md in met bovenstaande cijfers.")
    print("  2. Zet elke AMBER en ROOD om in een regel in docs/vragen-aan-lien.md.")
    print("  3. Schrijf het eindoordeel in één alinea, in gewone taal.")
    print("  4. Stuur dat oordeel dezelfde dag door, ook (juist) als het rood is.")
    print()
    print("  Een ROOD op dag 1 is een goede dag. Een ROOD dat op dag 6 opduikt,")
    print("  is een verloren week die niemand betaalt.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dag-1 dataprofiler.")
    parser.add_argument("bestand", help="pad naar de export (csv, xlsx, parquet)")
    parser.add_argument("--blad", default=None, help="bladnaam bij een xlsx")
    args = parser.parse_args(argv)

    pad = Path(args.bestand)
    df = laad(pad, args.blad)

    print(f"\n{LIJN}")
    print("DATA-AUDIT  asklien-bakkerij")
    print("Deze output bevat geen rijwaarden en mag gedeeld worden.")
    print(LIJN)

    blok_vorm(df, pad)
    gokken = blok_rollen(df)
    datums = blok_historiek(df, gokken["datum"].kolom)
    blok_volledigheid(datums)
    blok_meetwaarden(df, gokken)
    blok_dimensies(df, gokken, datums)
    blok_kanalen(df, gokken)
    blok_censuur(df)
    blok_slot()
    return 0


if __name__ == "__main__":
    sys.exit(main())
