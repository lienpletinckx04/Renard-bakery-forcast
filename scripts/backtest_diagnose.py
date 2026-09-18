"""WAPE-diagnose (blok 23): waar woont de fout van de productieprognose?

De productieprognose staat op circa 7,8 % WAPE dagomzet. Voordat er verbeterd
wordt, moet duidelijk zijn wáár die fout zit: welke weekdagen, welke
horizonstappen, feestdagen of gewone dagen, binnen of buiten de schoolvakantie,
welk seizoen. Dit script rekent de productievoorspeller — identiek herbouwd uit
dezelfde bouwstenen als scripts/contract_bouw.py — out-of-sample af met het
bestaande harnas en schrijft de uitsplitsing naar een rapport.

Daarnaast meet het verbeteringskandidaten, telkens naast de productievoorspeller
op dezelfde dagen. Ronde 1: per-feestdag-factoren en een vakantie-
overgangscorrectie. Ronde 2 (gericht op de zwakke plekken uit ronde 1): een
asymmetrische ná-vakantiecorrectie, een vakantiebewust niveauvenster en een
galette-seizoenscorrectie (vroege januari), plus de combinatie van wat zijn
deelvenster wint zonder het totaal te schaden. Er wordt hier NIETS in productie
geadopteerd: dat is een aparte beslissing, met de E4-lat uit
docs/beslissingen.md (een kandidaat is interessant als hij zijn deelvenster
duidelijk wint zonder het totaal te schaden).

De uitvoer bevat uitsluitend aggregaten en dagtotalen (datum + omzetbedrag)
en gaat naar reports/ — dat is gitignored, want ook geaggregeerde foutbedragen
dragen de schaal van de omzet van de eindklant.

Draaien:  make diagnose   (na make canoniek)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pandas as pd

from bakkerij import berekening as bk
from bakkerij import canoniek
from bakkerij import contract as ct
from bakkerij.backtest.rolling import (
    HORIZON,
    MIN_TRAIN,
    STAP,
    evalueer,
    per_horizon,
    trackrecord,
)
from bakkerij.features.calendar import (
    SCHOOLVAKANTIES_FR,
    WEEKDAGNAMEN,
    markeer_schoolvakanties,
    overgangsdagen,
)
from bakkerij.features.calendar import (
    kalender as bouw_kalender,
)
from bakkerij.model.baseline import _controleer
from bakkerij.model.productie import (
    BASIS,
    HEROPENING_DAGEN,
    bouw_voorspeller,
    open_of_gepland_open,
)
from bakkerij.model.verfijning import (
    Voorspeller,
    _klem,
    met_feestdagcorrectie,
)

INTERIM = REPO / "data" / "interim"
UIT = REPO / "reports" / "backtest_diagnose.md"

# Dezelfde harnasinstellingen als de contractbouw: sinds 18 aug 2026 per
# constructie, want beide importeren ze uit het harnas zelf.

#: Een feestdagnaam krijgt in kandidaat (a) alleen een eigen kolom als hij
#: minstens zo vaak in de gemeten historiek voorkomt; de wikkel zelf houdt
#: daarbovenop zijn eigen min_waarnemingen-drempel per trainingsvenster aan.
MIN_FEESTDAG_VOORKOMENS = 4

#: Hoeveel open dagen rond een vakantiegrens als overgangsdag tellen. Uit
#: productie.py en niet opnieuw opgeschreven: dit is hetzelfde getal als de
#: heropeningsvlag gebruikt, en twee constanten voor één begrip is precies hoe
#: twee constructies ontstaan.
OVERGANG_DAGEN = HEROPENING_DAGEN

MAANDNAMEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli",
              "augustus", "september", "oktober", "november", "december"]


# --- pure hulpfuncties (getest in tests/test_backtest_diagnose.py) -----------

def foutmaten(verwacht: pd.Series, werkelijk: pd.Series) -> dict:
    """n, WAPE en bias (€/dag) van een verzameling voorspelling-werkelijk-paren.

    Dezelfde definities als het harnas: WAPE is de som van de absolute fouten
    gedeeld door de som van de werkelijke omzet, bias is de gemiddelde
    ondertekende fout per dag (positief = te hoog voorspeld).
    """
    fout = verwacht.to_numpy(dtype=float) - werkelijk.to_numpy(dtype=float)
    som_werkelijk = float(werkelijk.sum())
    n = len(fout)
    return {
        "n": n,
        "wape": float(abs(fout).sum()) / som_werkelijk if som_werkelijk else 0.0,
        "bias": float(fout.sum()) / n if n else 0.0,
        "som_abs_fout": float(abs(fout).sum()),
    }


# `overgangsdagen` is op 14 augustus naar bakkerij/features/calendar.py
# verhuisd: sinds de adoptie van de heropeningscorrectie gebruikt de
# productievoorspeller exact dezelfde vlaglogica als deze meting, en één
# implementatie kan niet drijven. De import hierboven houdt de naam hier
# beschikbaar voor de tests en de rest van dit script.


def vakantiebewust_niveau(
    vakantiestatus: pd.Series,
    *,
    vensters: int = 8,
    niveau_dagen: int = 14,
) -> Voorspeller:
    """Variant B (ronde 2): weekdag_niveau met een vakantiebewust niveauvenster.

    De kern van de ná-vakantiefout uit ronde 1: het 14-daagse niveauvenster van
    `weekdag_niveau` sleept het vakantieregime de heropening in. Hier wordt de
    niveaufactor daarom berekend over de jongste `niveau_dagen` open dagen met
    DEZELFDE vakantiestatus als de doeldag: een doeldag buiten de vakantie
    krijgt het niveau van de jongste 14 niet-vakantiedagen, een doeldag erin
    dat van de jongste 14 vakantiedagen. Zijn er geen `niveau_dagen` dagen met
    die status, dan valt de factor terug op het gewone venster — exact wat
    `weekdag_niveau` zou doen. De weekdagvorm is identiek aan `weekdag_niveau`.

    `vakantiestatus` is een booleaanse reeks op datum (het FR-regime). De
    status volgt volledig uit de publieke kalender, dus dit lekt geen toekomst.
    """
    status = vakantiestatus.astype(bool)

    def voorspeller(historiek: pd.Series, doeldagen: pd.DatetimeIndex) -> pd.Series:
        _controleer(historiek, doeldagen)
        per_weekdag = historiek.groupby(historiek.index.dayofweek).apply(
            lambda s: s.iloc[-vensters:].median()
        )
        terugval = float(historiek.median())

        def basis(weekdag: int) -> float:
            return float(per_weekdag.get(weekdag, terugval))

        def niveau_over(staart: pd.Series) -> float:
            verwacht = sum(basis(dag) for dag in staart.index.dayofweek)
            return _klem(float(staart.sum()) / verwacht) if verwacht > 0 else 1.0

        algemeen = niveau_over(historiek.iloc[-niveau_dagen:])
        hist_status = status.reindex(historiek.index, fill_value=False).to_numpy()
        niveau_bij = {}
        for s in (False, True):
            deel = historiek[hist_status == s]
            niveau_bij[s] = (niveau_over(deel.iloc[-niveau_dagen:])
                             if len(deel) >= niveau_dagen else algemeen)

        doel_status = status.reindex(doeldagen, fill_value=False).to_numpy()
        waarden = [basis(dag) * niveau_bij[bool(s)]
                   for dag, s in zip(doeldagen.dayofweek, doel_status,
                                     strict=True)]
        return pd.Series(waarden, index=doeldagen,
                         name="weekdag_niveau_vakantiebewust")

    return voorspeller


# --- opmaak -------------------------------------------------------------------

def _pct(x: float) -> str:
    return f"{x * 100:.1f}".replace(".", ",") + " %"


def _eur(x: float, *, teken: bool = False) -> str:
    vorm = "+,.0f" if teken else ",.0f"
    return f"{x:{vorm}}".replace(",", ".")


def _punt(x: float) -> str:
    """Een WAPE-verschil in procentpunten, Nederlands geschreven (+0,42)."""
    return f"{x:+.2f}".replace(".", ",")


def _rij(label: str, m: dict) -> str:
    return f"| {label} | {m['n']} | {_pct(m['wape'])} | {_eur(m['bias'], teken=True)} |"


def _groepstabel(frame: pd.DataFrame, labels_en_maskers: list[tuple[str, pd.Series]],
                 kop: str) -> list[str]:
    """Eén markdown-tabel: per (label, masker) de foutmaten over dat deel."""
    r = [f"| {kop} | n | WAPE | Bias €/dag |", "|---|---:|---:|---:|"]
    for label, masker in labels_en_maskers:
        deel = frame[masker]
        if deel.empty:
            r.append(f"| {label} | 0 | — | — |")
            continue
        r.append(_rij(label, foutmaten(deel["verwacht"], deel["werkelijk"])))
    return r


# --- de productievoorspeller ------------------------------------------------
#
# Tot 19 augustus 2026 stond hier een eigen, "identiek herbouwde" kopie van de
# constructie uit scripts/contract_bouw.py. Ze was niet identiek, en het
# verschil was niet academisch: de ná-vakantiedagen kwamen hier uit
# `reeks.index` (alleen gemeten dagen) en in productie uit
# `open_of_gepland_open` (de hele kalender). Twee constructies van dezelfde
# vlag, en dus twee tegengestelde verdicten over de heropeningscorrectie —
# +0,12 punt hier, -0,002 in E4. Zie de kop van bakkerij/model/productie.py.
#
# Nu leent dit script de constructie, net als het backtest-rapport. Een
# kandidaat blijft hier staan; wat productie ís, staat daar.


def _schrijf(pad: Path, tekst: str) -> None:
    """Atomair wegschrijven: eerst een tijdelijk bestand, dan os.replace —
    hetzelfde patroon als de contract-JSON's, en om dezelfde reden."""
    pad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pad.with_name(pad.name + ".tmp")
    tmp.write_text(tekst, encoding="utf-8")
    os.replace(tmp, pad)


# --- het rapport ---------------------------------------------------------------

def main() -> int:
    verkopen_pad = INTERIM / "canoniek_verkopen.csv"
    if not verkopen_pad.exists():
        print("Geen canonieke data gevonden. Draai eerst: make canoniek")
        return 1
    verkopen = pd.read_csv(verkopen_pad, parse_dates=["datum"],
                           dtype=canoniek.CANONIEK_DTYPES)
    kalender = pd.read_csv(INTERIM / "canoniek_kalender.csv", parse_dates=["datum"])

    # Dezelfde dagreeks als de contractbouw: open dagen, kanaal winkel.
    open_v = bk.open_verkopen(verkopen, kalender)
    totalen = bk.dagtotalen(open_v)
    reeks = (totalen[totalen["kanaal"] == "winkel"]
             .set_index("datum")["omzet"].sort_index())

    voorspeller = bouw_voorspeller(kalender)

    # De kalendercontext wordt hier vers opgebouwd uit features.calendar, zodat
    # het rapport niet afhangt van welke kolommen de canonieke kalender toevallig
    # draagt. Zelfde feestdagenbron, zelfde vakantietabel als de voorspeller.
    context = bouw_kalender(reeks.index.min().date(), reeks.index.max().date())
    context = markeer_schoolvakanties(context, SCHOOLVAKANTIES_FR)

    # 1. Het totaal, zoals de contractbouw het meet.
    resultaat = evalueer(reeks, voorspeller, naam="productie",
                         min_train=MIN_TRAIN, stap=STAP, horizon=HORIZON)

    # Elke out-of-sample dag precies één keer, zoals productie hem getoond zou
    # hebben; dagen=10**6 betekent: álle dagen, niet alleen de laatste maand.
    track = trackrecord(reeks, voorspeller, dagen=10**6,
                        min_train=MIN_TRAIN, horizon=HORIZON)
    frame = track.merge(context, on="datum", how="left")
    frame["schoolvakantie"] = frame["schoolvakantie"].fillna(False)

    # Uit dezelfde bron als de productievoorspeller: de open dagen volgens
    # `open_of_gepland_open`, niet de gemeten dagen uit `reeks.index`. Dat
    # verschil was tot 19 aug 2026 de reden dat dit script en E4 elkaar
    # tegenspraken over de heropeningscorrectie.
    open_dagen = pd.DatetimeIndex(
        kalender.loc[open_of_gepland_open(kalender), "datum"]
    )
    na_dagen, voor_dagen = overgangsdagen(
        open_dagen, SCHOOLVAKANTIES_FR, OVERGANG_DAGEN
    )
    overgang = na_dagen.union(voor_dagen)

    r: list[str] = []
    r.append("# WAPE-diagnose van de productieprognose (blok 23)")
    r.append("")
    r.append(f"*Gebouwd {ct.nu().date().isoformat()}. Rolling-origin backtest "
             f"met het harnas uit `bakkerij/backtest/rolling.py`: min. "
             f"{MIN_TRAIN} trainingsdagen, stap {STAP}, horizon {HORIZON} open "
             "dagen; elke dag hieronder is precies één keer out-of-sample "
             "voorspeld, 1 tot 7 open dagen vooruit. Voorspeller: "
             "weekdagmediaan geschaald naar het niveau van de laatste twee "
             "weken, met schoolvakantiecorrectie (Franstalig regime) — "
             "identiek aan productie. Afgerekend in euro's omzetafwijking "
             "(WAPE), bias positief = te hoog voorspeld.*")
    r.append("")
    r.append(f"- Venster: {track['datum'].min().date()} t/m "
             f"{track['datum'].max().date()}, {len(track)} out-of-sample dagen.")
    r.append(f"- Totaal: WAPE {_pct(resultaat.wape)}, bias "
             f"{_eur(resultaat.bias_euro, teken=True)} €/dag "
             f"(n={resultaat.n_dagen}).")
    r.append("")

    # 2. per weekdag
    r.append("## 1. Per weekdag")
    r.append("")
    r += _groepstabel(frame, [
        (naam, frame["weekdag"] == i) for i, naam in enumerate(WEEKDAGNAMEN)
        if (frame["weekdag"] == i).any()
    ], "Weekdag")
    r.append("")

    # 3. per horizonstap
    r.append("## 2. Per horizonstap")
    r.append("")
    stappen = per_horizon(reeks, voorspeller, min_train=MIN_TRAIN,
                          stap=STAP, horizon=HORIZON)
    r.append("| Stap (open dagen vooruit) | n | WAPE | Bias €/dag |")
    r.append("|---:|---:|---:|---:|")
    for rij in stappen.itertuples():
        r.append(f"| {rij.stap} | {rij.n} | {_pct(rij.wape)} | "
                 f"{_eur(rij.bias, teken=True)} |")
    r.append("")

    # 4. feestdagen
    r.append("## 3. Feestdagen")
    r.append("")
    r += _groepstabel(frame, [
        ("feestdag", frame["feestdag"].astype(bool)),
        ("geen feestdag", ~frame["feestdag"].astype(bool)),
        ("dag vóór een feestdag", frame["dag_voor_feestdag"].astype(bool)),
        ("brugdag", frame["brugdag"].astype(bool)),
    ], "Groep")
    r.append("")
    namen_telling = (frame[frame["feestdag"].astype(bool)]
                     .groupby("feestdagnaam").size().sort_values(ascending=False))
    per_naam = [(str(naam), frame["feestdagnaam"] == naam)
                for naam, aantal in namen_telling.items() if aantal >= 3]
    if per_naam:
        r += _groepstabel(frame, per_naam, "Feestdag (n ≥ 3)")
    else:
        r.append("Geen enkele feestdagnaam komt drie of meer keer voor in het "
                 "out-of-sample venster; een tabel per naam zou anekdotes "
                 "tonen en blijft daarom achterwege.")
    r.append("")

    # 5. schoolvakanties (FR) en de overgangsdagen
    r.append("## 4. Schoolvakanties (Franstalig regime)")
    r.append("")
    in_vak = frame["schoolvakantie"].astype(bool)
    r += _groepstabel(frame, [
        ("binnen vakantie", in_vak),
        ("buiten vakantie", ~in_vak),
        (f"eerste {OVERGANG_DAGEN} open dagen ná een vakantie",
         frame["datum"].isin(na_dagen)),
        (f"laatste {OVERGANG_DAGEN} open dagen vóór een vakantie",
         frame["datum"].isin(voor_dagen)),
    ], "Groep")
    r.append("")

    # 6. seizoen
    r.append("## 5. Per maand (gepoold over jaren)")
    r.append("")
    r += _groepstabel(frame, [
        (naam, frame["maand"] == m) for m, naam in enumerate(MAANDNAMEN, start=1)
        if (frame["maand"] == m).any()
    ], "Maand")
    r.append("")

    # 7. top-20 missers (dagtotalen: toegestane aggregaten)
    r.append("## 6. De twintig grootste absolute missers")
    r.append("")
    r.append("| Datum | Voorspeld € | Werkelijk € | Fout € | Context |")
    r.append("|---|---:|---:|---:|---|")
    frame["abs_fout"] = (frame["verwacht"] - frame["werkelijk"]).abs()
    for rij in frame.nlargest(20, "abs_fout").itertuples():
        delen = [WEEKDAGNAMEN[int(rij.weekdag)]]
        if rij.feestdagnaam:
            delen.append(f"feestdag: {rij.feestdagnaam}")
        if getattr(rij, "dag_voor_feestdag", False):
            delen.append("dag vóór een feestdag")
        if getattr(rij, "brugdag", False):
            delen.append("brugdag")
        if rij.vakantienaam:
            delen.append(f"vakantie: {rij.vakantienaam}")
        r.append(f"| {rij.datum.date()} | {_eur(rij.verwacht)} | "
                 f"{_eur(rij.werkelijk)} | "
                 f"{_eur(rij.verwacht - rij.werkelijk, teken=True)} | "
                 f"{', '.join(delen)} |")
    r.append("")

    # 8. kandidaten
    r.append("## 7. Kandidaten, gemeten")
    r.append("")
    r.append("Beide kandidaten zijn een extra `met_feestdagcorrectie`-wikkel "
             "bovenop de ongewijzigde productievoorspeller, door hetzelfde "
             "harnas gehaald, en telkens naast productie op dezelfde dagen "
             "afgerekend. Hier wordt niets geadopteerd; de lat is het "
             "E4-precedent uit `docs/beslissingen.md`: een kandidaat is "
             "interessant als hij zijn deelvenster duidelijk wint zonder het "
             "totaal te schaden.")
    r.append("")

    # (a) per-feestdag-factoren
    open_context = context[context["datum"].isin(reeks.index)]
    voorkomens = (open_context[open_context["feestdag"]]
                  .groupby("feestdagnaam").size())
    fd_namen = sorted(str(n) for n, c in voorkomens.items()
                      if c >= MIN_FEESTDAG_VOORKOMENS and n)
    fd_kal = context[["datum"]].copy()
    for naam in fd_namen:
        fd_kal[naam] = (context["feestdagnaam"] == naam).to_numpy()
    kandidaat_a = met_feestdagcorrectie(voorspeller, fd_kal,
                                        kenmerken=tuple(fd_namen),
                                        naam="productie_plus_per_feestdag")
    feestdagen = pd.DatetimeIndex(
        open_context.loc[open_context["feestdag"], "datum"])

    if fd_namen:
        r.append(f"### a. Per-feestdag-factoren ({len(fd_namen)} namen met "
                 f"≥ {MIN_FEESTDAG_VOORKOMENS} voorkomens in de historiek: "
                 f"{', '.join(fd_namen)})")
        r.append("")
    else:
        maximum = int(voorkomens.max()) if len(voorkomens) else 0
        r.append("### a. Per-feestdag-factoren")
        r.append("")
        r.append(f"Geen enkele feestdagnaam haalt "
                 f"{MIN_FEESTDAG_VOORKOMENS} voorkomens op de gemeten open "
                 f"dagen (maximum: {maximum}). De kandidaat kan dus geen "
                 "enkele per-naam-factor schatten en valt samen met "
                 "productie; de meting hieronder bevestigt dat. "
                 "Per-feestdag-factoren vragen méér jaren historiek dan er "
                 "nu ligt — dezelfde grens waarop de generieke "
                 "feestdagcorrectie eerder is afgewezen.")
        r.append("")
    _, regels = _kandidaattabel(reeks, voorspeller, kandidaat_a,
                                [("totaal", None),
                                 ("alleen feestdagen", feestdagen)])
    r += regels
    r.append("")

    # (b) vakantie-overgangscorrectie
    ov_kal = pd.DataFrame({"datum": context["datum"]})
    ov_kal["na_vakantie"] = context["datum"].isin(na_dagen).to_numpy()
    ov_kal["voor_vakantie"] = context["datum"].isin(voor_dagen).to_numpy()
    kandidaat_b = met_feestdagcorrectie(
        voorspeller, ov_kal, kenmerken=("na_vakantie", "voor_vakantie"),
        naam="productie_plus_overgang")

    r.append(f"### b. Vakantie-overgangscorrectie (eerste {OVERGANG_DAGEN} "
             f"open dagen ná en laatste {OVERGANG_DAGEN} vóór elke "
             "FR-vakantie)")
    r.append("")
    _, regels = _kandidaattabel(reeks, voorspeller, kandidaat_b,
                                [("totaal", None),
                                 ("alleen overgangsdagen", overgang)])
    r += regels
    r.append("")

    # 9. ronde 2: drie gerichte varianten plus de combinatie van de winnaars
    regels2, stdout2 = _ronde2(reeks, kalender, voorspeller, na_dagen)
    r += regels2

    # 10. slot
    r.append("## 9. Waar de fout woont")
    r.append("")
    r += _slotsectie(frame, stappen, na_dagen, voor_dagen, resultaat.wape)
    r.append("")

    _schrijf(UIT, "\n".join(r) + "\n")
    omvang = f"{UIT.stat().st_size:,}".replace(",", ".")
    print(f"Diagnose geschreven: {UIT.relative_to(REPO)} "
          f"({omvang} bytes, gitignored)")
    print(f"  venster {track['datum'].min().date()} t/m "
          f"{track['datum'].max().date()}, {len(track)} out-of-sample dagen, "
          f"WAPE {resultaat.wape:.1%}, bias {resultaat.bias_euro:+.0f} EUR/dag")
    for regel in stdout2:
        print(f"  {regel}")
    return 0


#: "Het totaal niet schaden" is met tolerantie: een kandidaat die maar een
#: handvol dagen raakt, beweegt het totaal binnen de meetruis. Meer dan dit
#: aantal procentpunten slechter op een venster telt als schade.
TOLERANTIE_PUNT = 0.05


def _kandidaattabel(reeks: pd.Series, productie, kandidaat,
                    vensters: list[tuple[str, pd.DatetimeIndex | None]],
                    ) -> tuple[list, list[str]]:
    """Productie naast kandidaat, per venster (None = het totaal).

    Geeft (metingen, markdown-regels) terug; metingen is een lijst
    (vensternaam, Resultaat productie, Resultaat kandidaat) in de volgorde
    van `vensters`.
    """
    metingen = []
    for venster_naam, alleen in vensters:
        p = evalueer(reeks, productie, min_train=MIN_TRAIN, stap=STAP,
                     horizon=HORIZON, alleen_dagen=alleen)
        k = evalueer(reeks, kandidaat, min_train=MIN_TRAIN, stap=STAP,
                     horizon=HORIZON, alleen_dagen=alleen)
        metingen.append((venster_naam, p, k))
    r = [("| Venster | n | WAPE productie | WAPE kandidaat "
          "| Bias productie | Bias kandidaat |"),
         "|---|---:|---:|---:|---:|---:|"]
    for venster_naam, p, k in metingen:
        r.append(f"| {venster_naam} | {p.n_dagen} | {_pct(p.wape)} | "
                 f"{_pct(k.wape)} | {_eur(p.bias_euro, teken=True)} | "
                 f"{_eur(k.bias_euro, teken=True)} |")
    deltas = [f"{naam} {_punt((p.wape - k.wape) * 100)} punt"
              for naam, p, k in metingen]
    r.append("")
    r.append("Verschil in WAPE (positief = de kandidaat wint): "
             + "; ".join(deltas) + ".")
    return metingen, r


#: Onder dit aantal dagen mag een NIET-primair venster geen veto uitspreken.
#
#: Toegevoegd 18 aug 2026, nadat de januari-splitsing van variant A het
#: mechanische oordeel omklapte op -0,08 procentpunt over DRIE dagen met 46 %
#: WAPE. Dat is geen schade maar ruis: op drie dagen waarvan er één 18.840 euro
#: mis is, betekent een tiende procentpunt niets. Een venster dat te dun is om
#: een winst te bewijzen, is ook te dun om een veto te dragen — en anders
#: straft het meetinstrument je voor het toevoegen van een venster.
#:
#: Het primaire venster is nooit vrijgesteld: dáár moet de winst juist blijken,
#: en als dat venster te dun is, is de hele kandidaat te dun.
MIN_VENSTER_DAGEN = 5


def _wint(metingen: list, primair: int = 1,
          tolerantie: float = TOLERANTIE_PUNT) -> bool:
    """Wint de kandidaat zijn primaire deelvenster zonder een van de andere
    vensters (het totaal voorop) meer dan `tolerantie` procentpunt te schaden?
    Dit is het E4-precedent, mechanisch toegepast; de adoptiebeslissing zelf
    blijft mensenwerk.

    Vensters met minder dan `MIN_VENSTER_DAGEN` dagen tellen mee in het rapport
    maar spreken geen veto uit; zie MIN_VENSTER_DAGEN voor waarom.
    """
    deltas = [(p.wape - k.wape) * 100 for _, p, k in metingen]
    if deltas[primair] <= 0:
        return False
    return all(
        d >= -tolerantie
        for i, (d, (_, p, _k)) in enumerate(zip(deltas, metingen, strict=True))
        if i != primair and p.n_dagen >= MIN_VENSTER_DAGEN
    )


#: De grootste misser van ronde 1: Driekoningen 2026, het galette-seizoen.
GALETTE_DAG = pd.Timestamp("2026-01-06")


def _dag_uit_trackrecord(reeks: pd.Series, model,
                         datum: pd.Timestamp) -> tuple[float, float] | None:
    """(verwacht, werkelijk) op één datum, out-of-sample voorspeld zoals
    productie hem getoond zou hebben; None als de dag niet in het venster ligt.
    Eén datum plus een dagtotaal is een toegestaan aggregaat."""
    tr = trackrecord(reeks, model, dagen=10**6, min_train=MIN_TRAIN,
                     horizon=HORIZON)
    rij = tr[tr["datum"] == datum]
    if rij.empty:
        return None
    return float(rij["verwacht"].iloc[0]), float(rij["werkelijk"].iloc[0])


def _galette_regel(reeks: pd.Series, model, naam: str) -> str:
    paar = _dag_uit_trackrecord(reeks, model, GALETTE_DAG)
    if paar is None:
        return (f"De dag {GALETTE_DAG.date()} ligt niet in het "
                "out-of-sample venster.")
    verwacht, werkelijk = paar
    return (f"Op {GALETTE_DAG.date()} voorspelt {naam} {_eur(verwacht)} € bij "
            f"werkelijk {_eur(werkelijk)} € "
            f"(fout {_eur(verwacht - werkelijk, teken=True)} €).")


def _ronde2(reeks: pd.Series, kalender: pd.DataFrame, voorspeller,
            na_dagen: pd.DatetimeIndex) -> tuple[list[str], list[str]]:
    """Ronde 2: drie gerichte varianten op de zwakke plekken uit ronde 1,
    plus de combinatie van de varianten die hun deelvenster winnen zonder
    het totaal te schaden. Geeft (rapportregels, stdout-regels) terug."""
    vakantiekalender = markeer_schoolvakanties(
        kalender[["datum"]].copy(), SCHOOLVAKANTIES_FR)
    status = vakantiekalender.set_index("datum")["schoolvakantie"].astype(bool)
    vakantiedagen = pd.DatetimeIndex(
        vakantiekalender.loc[vakantiekalender["schoolvakantie"], "datum"])
    jan26 = reeks.index[(reeks.index.year == 2026) & (reeks.index.month == 1)]
    vroege_jan26 = jan26[jan26.day <= 15]
    na_venster = (f"eerste {OVERGANG_DAGEN} open dagen ná een vakantie",
                  na_dagen)

    # De ná-dagen gesplitst op januari, en dat is geen willekeurige snede.
    #
    # Gemeten op 18 aug 2026: de kerstvakantie eindigt elk jaar begin januari,
    # dus "de eerste drie open dagen ná een vakantie" ZIJN elk jaar de
    # galette-dagen rond Driekoningen (2025-01-06/07/08 en 2026-01-05/06/07).
    # Niet door een verkeerde vlag zoals op 14 augustus -- de vlaglogica is
    # sindsdien gerepareerd -- maar omdat die dagen werkelijk samenvallen.
    #
    # Daarmee kan één ná-vakantiefactor twee dingen tegelijk zijn: een
    # heropeningseffect, of een galette-seizoenseffect dat vervolgens óók
    # afgevuurd wordt op de heropeningen in november, maart, mei en augustus,
    # waar geen galette bestaat. Op het gemiddelde van vijftien dagen is dat
    # onderscheid onzichtbaar, en juist daarop is deze correctie op
    # 14 augustus aangenomen en een dag later teruggedraaid.
    #
    # Deze twee vensters maken het onderscheid zichtbaar in plaats van
    # bespreekbaar. Let op de aantallen: januari draagt er maar drie van de
    # vijftien, dus dit wijst een richting aan en bewijst geen wet.
    na_januari = na_dagen[na_dagen.month == 1]
    na_rest = na_dagen[na_dagen.month != 1]
    na_vensters = [
        na_venster,
        ("waarvan in januari (galette-dagen)", na_januari),
        ("waarvan buiten januari (echte heropeningen)", na_rest),
    ]

    r: list[str] = []
    uit: list[str] = []
    r.append("## 8. Ronde 2: drie gerichte varianten op de zwakke plekken")
    r.append("")
    r.append("Zelfde protocol als ronde 1: hetzelfde harnas, telkens naast "
             "de ongewijzigde productievoorspeller op dezelfde dagen. Het "
             "winstcriterium (E4-precedent): het primaire deelvenster winnen "
             f"zonder een van de andere gemeten vensters meer dan "
             f"{_punt(TOLERANTIE_PUNT)[1:]} procentpunt WAPE te schaden. "
             f"Vensters met minder dan {MIN_VENSTER_DAGEN} dagen staan wél in "
             "de tabel maar spreken geen veto uit: te dun voor een winst is "
             "ook te dun voor een afwijzing. Ook hier wordt niets "
             "geadopteerd.")
    r.append("")

    # A: asymmetrisch, alleen ná de vakantie (ronde 1 mat voor+na samen; de
    # bias zat vrijwel volledig ná).
    a_kal = pd.DataFrame({"datum": kalender["datum"]})
    a_kal["na_vakantie"] = kalender["datum"].isin(na_dagen).to_numpy()
    variant_a = met_feestdagcorrectie(voorspeller, a_kal,
                                      kenmerken=("na_vakantie",),
                                      naam="productie_plus_na_vakantie")
    r.append("### A. Alleen ná-vakantie (asymmetrisch)")
    r.append("")
    r.append(f"Eén kenmerk `na_vakantie` (de eerste {OVERGANG_DAGEN} open "
             "dagen na het einde van een FR-vakantie) als extra wikkel "
             "bovenop productie. Primair deelvenster: die ná-dagen.")
    r.append("")
    met_a, regels = _kandidaattabel(reeks, voorspeller, variant_a,
                                    [("totaal", None), *na_vensters])
    r += regels
    r.append("")

    # B: vakantiebewust niveauvenster, met de productwikkel eromheen.
    basis_b = vakantiebewust_niveau(status)
    variant_b = met_feestdagcorrectie(basis_b, vakantiekalender,
                                      kenmerken=("schoolvakantie",),
                                      naam="niveau_vakantiebewust_fr")
    r.append("### B. Vakantiebewust niveauvenster")
    r.append("")
    r.append("De niveaufactor van `weekdag_niveau` wordt berekend over de "
             "jongste 14 open dagen met dezelfde vakantiestatus als de "
             "doeldag (terugval op het gewone venster als die er niet zijn), "
             "met daaromheen de bestaande FR-schoolvakantiecorrectie zoals "
             "productie. Primair deelvenster: de ná-vakantiedagen; alle "
             "vakantiedagen worden meegemeten als wachter (de correctie mag "
             "niet kapotgaan).")
    r.append("")
    met_b, regels = _kandidaattabel(reeks, voorspeller, variant_b,
                                    [("totaal", None), na_venster,
                                     ("alle vakantiedagen", vakantiedagen)])
    r += regels
    r.append("")

    # C: het galette-seizoen. Januari 2025 zit in de training, januari 2026
    # out-of-sample, dus dit is eerlijk te backtesten.
    c_kal = pd.DataFrame({"datum": kalender["datum"]})
    c_kal["vroege_januari"] = ((kalender["datum"].dt.month == 1)
                               & (kalender["datum"].dt.day <= 15)).to_numpy()
    variant_c = met_feestdagcorrectie(voorspeller, c_kal,
                                      kenmerken=("vroege_januari",),
                                      naam="productie_plus_vroege_januari")
    r.append("### C. Galette-seizoen (vroege januari, 1 t/m 15)")
    r.append("")
    r.append("Eén kenmerk `vroege_januari` als extra wikkel bovenop "
             "productie. Primair deelvenster: januari 2026 (alle "
             "out-of-sample dagen van die maand).")
    r.append("")
    met_c, regels = _kandidaattabel(reeks, voorspeller, variant_c,
                                    [("totaal", None),
                                     ("januari 2026", jan26),
                                     ("1 t/m 15 januari 2026", vroege_jan26)])
    r += regels
    r.append("")
    r.append(_galette_regel(reeks, voorspeller, "productie"))
    r.append(_galette_regel(reeks, variant_c, "variant C"))
    r.append("")

    for naam, metingen in (("A", met_a), ("B", met_b), ("C", met_c)):
        deltas = "; ".join(f"{v} {_punt((p.wape - k.wape) * 100)} pt"
                           for v, p, k in metingen)
        uit.append(f"ronde 2, variant {naam}: {deltas}"
                   f" -> {'wint' if _wint(metingen) else 'wint niet'}")

    # De combinatie van wat zijn deelvenster wint zonder het totaal te schaden.
    wint_a, wint_b, wint_c = _wint(met_a), _wint(met_b), _wint(met_c)
    winnaars = [n for n, w in (("A", wint_a), ("B", wint_b), ("C", wint_c))
                if w]
    r.append("### Combinatie van de winnaars")
    r.append("")
    if not winnaars:
        r.append("Geen enkele variant wint zijn deelvenster zonder elders te "
                 "schaden; er is geen combinatie te meten.")
        r.append("")
        uit.append("ronde 2, combinatie: geen winnaars")
        return r, uit

    delen = []
    # De productiebasis, uit productie.py: wisselt die ooit, dan wisselt
    # de combinatie hier mee in plaats van stil op de oude te blijven.
    combo_basis = BASIS
    if wint_b:
        combo_basis = basis_b
        delen.append("het vakantiebewuste niveauvenster (B)")
    combo = met_feestdagcorrectie(combo_basis, vakantiekalender,
                                  kenmerken=("schoolvakantie",),
                                  naam="combinatie_basis")
    combo_kal = pd.DataFrame({"datum": kalender["datum"]})
    extra = []
    if wint_a:
        combo_kal["na_vakantie"] = a_kal["na_vakantie"].to_numpy()
        extra.append("na_vakantie")
        delen.append("de ná-vakantiecorrectie (A)")
    if wint_c:
        combo_kal["vroege_januari"] = c_kal["vroege_januari"].to_numpy()
        extra.append("vroege_januari")
        delen.append("de vroege-januaricorrectie (C)")
    if extra:
        combo = met_feestdagcorrectie(combo, combo_kal,
                                      kenmerken=tuple(extra),
                                      naam="combinatie")
    r.append(f"Winnaars volgens het criterium: {', '.join(winnaars)}. De "
             f"combinatie is {' + '.join(delen)}, met de bestaande "
             "FR-schoolvakantiecorrectie zoals productie.")
    r.append("")
    met_combo, regels = _kandidaattabel(
        reeks, voorspeller, combo,
        [("totaal", None), na_venster,
         ("alle vakantiedagen", vakantiedagen),
         ("januari 2026", jan26),
         ("1 t/m 15 januari 2026", vroege_jan26)])
    r += regels
    r.append("")
    if wint_c:
        r.append(_galette_regel(reeks, combo, "de combinatie"))
        r.append("")
    deltas = "; ".join(f"{v} {_punt((p.wape - k.wape) * 100)} pt"
                       for v, p, k in met_combo)
    uit.append(f"ronde 2, combinatie ({'+'.join(winnaars)}): {deltas}")
    return r, uit


def _slotsectie(frame: pd.DataFrame, stappen: pd.DataFrame,
                na_dagen: pd.DatetimeIndex, voor_dagen: pd.DatetimeIndex,
                totaal_wape: float) -> list[str]:
    """Drie tot vijf patronen in gewone zinnen, rechtstreeks uit de metingen."""
    zinnen: list[str] = []
    totaal_abs = float((frame["verwacht"] - frame["werkelijk"]).abs().sum())

    def m(masker: pd.Series) -> dict:
        deel = frame[masker]
        uit = foutmaten(deel["verwacht"], deel["werkelijk"])
        uit["aandeel"] = uit["som_abs_fout"] / totaal_abs if totaal_abs else 0.0
        return uit

    # feestdagen tegenover gewone dagen
    feest = m(frame["feestdag"].astype(bool))
    gewoon = m(~frame["feestdag"].astype(bool))
    if feest["n"]:
        zinnen.append(
            f"Feestdagen zijn de duurste dagen per stuk: WAPE {_pct(feest['wape'])} "
            f"tegen {_pct(gewoon['wape'])} op gewone dagen, met een bias van "
            f"{_eur(feest['bias'], teken=True)} €/dag. Met {feest['n']} dagen dragen "
            f"ze {_pct(feest['aandeel'])} van de totale absolute fout.")

    # weekdagspreiding
    per_dag = [(naam, m(frame["weekdag"] == i))
               for i, naam in enumerate(WEEKDAGNAMEN)
               if (frame["weekdag"] == i).any()]
    slechtste = max(per_dag, key=lambda x: x[1]["wape"])
    beste = min(per_dag, key=lambda x: x[1]["wape"])
    zinnen.append(
        f"Tussen de weekdagen loopt de fout van {_pct(beste[1]['wape'])} "
        f"({beste[0]}) tot {_pct(slechtste[1]['wape'])} ({slechtste[0]}); "
        f"de {slechtste[0]} draagt {_pct(slechtste[1]['aandeel'])} van de "
        "totale absolute fout.")

    # vakantieovergangen
    na = m(frame["datum"].isin(na_dagen))
    voor = m(frame["datum"].isin(voor_dagen))
    binnen = m(frame["schoolvakantie"].astype(bool))
    buiten = m(~frame["schoolvakantie"].astype(bool))
    if na["n"] or voor["n"]:
        zinnen.append(
            f"De vakantiecorrectie doet zijn werk binnen de vakantie "
            f"({_pct(binnen['wape'])} tegen {_pct(buiten['wape'])} erbuiten), "
            f"maar de randen blijven lastig: {_pct(na['wape'])} op de eerste "
            f"{OVERGANG_DAGEN} open dagen ná een vakantie (bias "
            f"{_eur(na['bias'], teken=True)}) en {_pct(voor['wape'])} op de "
            f"laatste {OVERGANG_DAGEN} ervóór (bias "
            f"{_eur(voor['bias'], teken=True)}).")

    # seizoen
    per_maand = [(mnd, naam, m(frame["maand"] == mnd))
                 for mnd, naam in enumerate(MAANDNAMEN, start=1)
                 if (frame["maand"] == mnd).any()]
    ergste_mnd, ergste_naam, ergste = max(per_maand, key=lambda x: x[2]["wape"])
    _, beste_naam, beste_m = min(per_maand, key=lambda x: x[2]["wape"])
    top20 = frame.assign(
        _af=(frame["verwacht"] - frame["werkelijk"]).abs()).nlargest(20, "_af")
    in_ergste = int((top20["maand"] == ergste_mnd).sum())
    zinnen.append(
        f"Het seizoen spreidt van {_pct(beste_m['wape'])} in "
        f"{beste_naam} tot {_pct(ergste['wape'])} in "
        f"{ergste_naam} — de maand {ergste_naam} alleen draagt "
        f"{_pct(ergste['aandeel'])} van de totale absolute fout en herbergt "
        f"{in_ergste} van de twintig grootste missers.")

    # horizon
    if len(stappen) >= 2:
        s1 = stappen.iloc[0]
        s_laatste = stappen.iloc[-1]
        zinnen.append(
            f"De horizon kost weinig: stap 1 staat op {_pct(s1['wape'])} en "
            f"stap {int(s_laatste['stap'])} op {_pct(s_laatste['wape'])} — "
            "de fout zit dus vooral in de dagen zelf (kalender en niveau), "
            "niet in hoe ver vooruit gekeken wordt."
            if abs(s_laatste["wape"] - s1["wape"]) < 0.02 else
            f"De fout groeit met de horizon: van {_pct(s1['wape'])} op stap 1 "
            f"naar {_pct(s_laatste['wape'])} op stap {int(s_laatste['stap'])} — "
            "het niveau-anker van twee weken veroudert merkbaar binnen één "
            "voorspelweek.")

    return [f"- {zin}" for zin in zinnen[:5]]


if __name__ == "__main__":
    sys.exit(main())
