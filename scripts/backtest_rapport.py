"""Het backtest-rapport (deliverable E4): wat de prognose kan, gemeten.

Eén document dat alles draagt wat er over de prognose beweerd wordt, met de
meting ernaast — inclusief wat er getoetst en afgewezen is. Aanvaarding van de
prognose hangt niet af van de vraag of ze goed genoeg is naar de smaak van de
eindklant: als de data een grens stelt, is het eerlijke rapport dat dat
aantoont de geleverde waarde (scope.md, aanvaardingsclausule).

De uitvoer bevat uitsluitend aggregaten (percentages, foutbedragen) en gaat
naar reports/ — dat is gitignored, want ook geaggregeerde foutbedragen dragen
de schaal van de omzet van de eindklant.

Draaien:  make backtest-rapport   (na make canoniek)
"""
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
    KALIBRATIE_KANDIDATEN,
    MIN_TRAIN,
    STAP,
    dekking,
    evalueer,
    kalibreer_kwantielen,
    per_horizon,
)
from bakkerij.features.calendar import (
    SCHOOLVAKANTIES_FR,
    SCHOOLVAKANTIES_VL,
    markeer_schoolvakanties,
)
from bakkerij.model.baseline import ALLE_BASELINES
from bakkerij.model.categorie import (
    categorie_prognoses,
    categorie_reeksen,
    som_van_categorieen,
)
from bakkerij.model.productie import KENMERKEN, bouw_voorspeller
from bakkerij.model.verfijning import met_feestdagcorrectie, weekdag_niveau

INTERIM = REPO / "data" / "interim"
RAW = REPO / "data" / "raw"
UIT = REPO / "reports" / "backtest-rapport.md"

# MIN_TRAIN/STAP/HORIZON komen sinds 18 aug 2026 uit het harnas zelf.


def _pct(x: float) -> str:
    return f"{x * 100:.1f}".replace(".", ",") + " %"


def main() -> int:
    for nodig in ("canoniek_verkopen.csv", "canoniek_kalender.csv"):
        if not (INTERIM / nodig).exists():
            raise SystemExit(f"data/interim/{nodig} ontbreekt. Draai eerst: make canoniek")
    verkopen = pd.read_csv(INTERIM / "canoniek_verkopen.csv", parse_dates=["datum"],
                           dtype=canoniek.CANONIEK_DTYPES)
    kalender = pd.read_csv(INTERIM / "canoniek_kalender.csv", parse_dates=["datum"])
    open_v = bk.open_verkopen(verkopen, kalender)
    totalen = bk.dagtotalen(open_v)
    reeks = (totalen[totalen["kanaal"] == "winkel"]
             .set_index("datum")["omzet"].sort_index())

    treffers = sorted(RAW.glob("*_odoo_producten.csv"))
    groepen = (pd.read_csv(treffers[-1], dtype={"product_id": str})
               .set_index("product_id")["categorie"]
               if treffers else pd.Series(dtype=str))

    r: list[str] = []
    r.append("# Backtest-rapport (E4)")
    r.append("")
    r.append(f"*Gebouwd {ct.nu().date().isoformat()}. Rolling-origin backtest, "
             f"min. {MIN_TRAIN} trainingsdagen, stap {STAP}, horizon {HORIZON} "
             f"open dagen. Gemeten open winkeldagen: {len(reeks)}, "
             f"{reeks.index.min().date()} t/m {reeks.index.max().date()}. "
             "Afgerekend in euro's omzetafwijking (WAPE), nooit in MAPE.*")
    r.append("")

    # 1. baselines en kandidaten op dagomzet
    r.append("## 1. De lat en de kandidaten (dagomzet winkel)")
    r.append("")
    r.append("| Model | WAPE | Gem. fout €/dag | Bias €/dag |")
    r.append("|---|---:|---:|---:|")
    kandidaten: list[tuple[str, object]] = list(ALLE_BASELINES.items())
    kandidaten.append(("weekdag_niveau", weekdag_niveau))
    vl_kal = markeer_schoolvakanties(kalender[["datum"]].copy(), SCHOOLVAKANTIES_VL)
    fr_kal = markeer_schoolvakanties(kalender[["datum"]].copy(), SCHOOLVAKANTIES_FR)
    kandidaten.append(("niveau + vakantie VL", met_feestdagcorrectie(
        weekdag_niveau, vl_kal, kenmerken=("schoolvakantie",), naam="vl")))
    kandidaten.append(("niveau + vakantie FR", met_feestdagcorrectie(
        weekdag_niveau, fr_kal, kenmerken=("schoolvakantie",), naam="fr")))
    # De échte productievoorspeller, geleend en niet nagebouwd. Dat is bewust:
    # op 18 aug 2026 noemde dit rapport een halve dag het verkéérde model "in
    # productie" — de heropeningscorrectie was net geadopteerd en deze lijst
    # wist dat niet. Een tweede definitie van "wat productie is" drijft altijd
    # weg van de eerste.
    #
    # Sinds 19 aug 2026 komt hij uit `bakkerij/model/productie.py` en niet meer
    # uit `scripts/contract_bouw.py`. Dat was de laatste schuld van deze regel:
    # zolang de definitie in een script stond, kon een tweede script haar niet
    # lenen zonder sys.path-kunstgrepen — en dan bouwt het haar na.
    productie = bouw_voorspeller(kalender)
    # Het label leest zichzelf uit KENMERKEN. Een met de hand getypte naam
    # stond op 18 aug 2026 binnen één uur twee keer verkeerd in dit rapport,
    # eerst zonder en toen mét een correctie die er niet (meer) in zat.
    productie_label = ("niveau + " + " + ".join(KENMERKEN)
                       + " FR (in productie)")
    kandidaten.append((productie_label, productie))
    cat_reeksen = categorie_reeksen(open_v, groepen, top_n=6)
    kandidaten.append(("som van 7 categorieprognoses",
                       som_van_categorieen(cat_reeksen, weekdag_niveau)))

    uitkomsten = {}
    for naam, model in kandidaten:
        res = evalueer(reeks, model, naam=naam, min_train=MIN_TRAIN,
                       stap=STAP, horizon=HORIZON)
        uitkomsten[naam] = res
        mae = f"{res.mae_euro:,.0f}".replace(",", ".")
        bias = f"{res.bias_euro:+,.0f}".replace(",", ".")
        r.append(f"| {naam} | {_pct(res.wape)} | {mae} | {bias} |")
    r.append("")
    r.append("**Getoetst en afgewezen:** de feestdagcorrectie (11,7 % tegen "
             "10,7 % WAPE op de geraakte dagen — te weinig feestdagen in de "
             "historiek), het Vlaamse vakantieregime (kleiner effect dan het "
             "Franstalige, zie §3) en de som van categorieën als dagmodel "
             "(0,42 punt beter, onder de vooraf gestelde lat van 0,5 punt).")
    r.append("")

    # 2. fout per horizonstap + bandkalibratie, op de voorspeller die
    # werkelijk draait (hierboven gebouwd, inclusief heropeningscorrectie).
    r.append("## 2. Fout per horizonstap en de gekalibreerde band")
    r.append("")
    kal = kalibreer_kwantielen(reeks, productie, doel=0.80,
                               min_train=MIN_TRAIN, stap=STAP, horizon=HORIZON)
    stappen = per_horizon(reeks, productie, onder=kal.onder, boven=kal.boven,
                          min_train=MIN_TRAIN, stap=STAP, horizon=HORIZON)
    r.append("| Stap (open dagen vooruit) | n | WAPE | Bias €/dag |")
    r.append("|---:|---:|---:|---:|")
    for rij in stappen.itertuples():
        bias = f"{rij.bias:+,.0f}".replace(",", ".")
        r.append(f"| {rij.stap} | {rij.n} | {_pct(rij.wape)} | {bias} |")
    r.append("")
    r.append("| Kwantielkandidaat | Out-of-sample gedekt (gewogen) |")
    r.append("|---|---:|")
    for onder, boven in KALIBRATIE_KANDIDATEN:
        meting = dekking(reeks, productie, onder=onder, boven=boven,
                         min_train=MIN_TRAIN, stap=STAP, horizon=HORIZON)
        b = meting.dropna(subset=["binnen_band"])
        b = b[b["n"] > 0]
        gewogen = (float((b["binnen_band"] * b["n"]).sum() / b["n"].sum())
                   if not b.empty else float("nan"))
        merk = " ← gekozen" if (onder, boven) == (kal.onder, kal.boven) else ""
        paar = f"{onder * 100:g}–{boven * 100:g}".replace(".", ",")
        r.append(f"| {paar} | {_pct(gewogen)}{merk} |")
    r.append("")
    r.append(f"Doel: {_pct(kal.doel)} dekking. De kalibratie kiest de smalste "
             "kandidaat die het doel (min tolerantie van 5 punt) haalt; de "
             "gemeten dekking staat ook letterlijk in het contract en dus op "
             "het scherm.")
    r.append("")

    # 3. schoolvakantieregimes op de geraakte dagen
    r.append("## 3. Schoolvakanties: twee regimes, op de geraakte dagen afgerekend")
    r.append("")
    r.append("| Regime | Vakantiedagen (n) | WAPE basis | WAPE met correctie | Totaal-effect |")
    r.append("|---|---:|---:|---:|---:|")
    basis_res = uitkomsten["weekdag_niveau"]
    # Hier bewust de vakantie-alleen-varianten: dit is de vergelijking van twee
    # REGIMES, en die is alleen eerlijk als de rest van het model gelijk blijft.
    for naam, kal_df, model_naam in (("Vlaams", vl_kal, "niveau + vakantie VL"),
                                     ("Franstalig", fr_kal,
                                      "niveau + vakantie FR")):
        vak_dagen = pd.DatetimeIndex(kal_df.loc[kal_df["schoolvakantie"], "datum"])
        model = met_feestdagcorrectie(weekdag_niveau, kal_df,
                                      kenmerken=("schoolvakantie",), naam=naam)
        alleen_basis = evalueer(reeks, weekdag_niveau, min_train=MIN_TRAIN,
                                stap=STAP, horizon=HORIZON, alleen_dagen=vak_dagen)
        alleen_model = evalueer(reeks, model, min_train=MIN_TRAIN,
                                stap=STAP, horizon=HORIZON, alleen_dagen=vak_dagen)
        totaal_effect = (basis_res.wape - uitkomsten[model_naam].wape) * 100
        r.append(f"| {naam} | {alleen_model.n_dagen} | {_pct(alleen_basis.wape)} "
                 f"| {_pct(alleen_model.wape)} | {totaal_effect:+.2f} pt |")
    r.append("")
    r.append("Het Franstalige regime draait sinds 13 augustus 2026 in de "
             "prognose. Dit is tevens een empirische bevinding voor vraag 47 "
             "(O10): het koopgedrag van deze bakkerij volgt het Franstalige "
             "vakantieregime, niet het Vlaamse.")
    r.append("")

    # 4. per categorie
    r.append("## 4. Prognose per categorie")
    r.append("")
    # De doeldagen doen er voor dit rapport niet toe (alleen de WAPE telt),
    # maar de leklat eist dat ze ná de historiek liggen — terecht.
    doeldagen = pd.date_range(reeks.index.max() + pd.Timedelta(days=1),
                              periods=HORIZON, freq="D")
    prognoses, overgeslagen = categorie_prognoses(
        cat_reeksen, productie, doeldagen,
        onder=kal.onder, boven=kal.boven, horizon=HORIZON)
    r.append("| Categorie | Aandeel omzet | WAPE |")
    r.append("|---|---:|---:|")
    for p in prognoses:
        aandeel = f"{p.aandeel_pct:.1f}".replace(".", ",")
        r.append(f"| {p.categorie} | {aandeel} % | {_pct(p.wape)} |")
    if overgeslagen:
        r.append("")
        r.append(f"Zonder eigen prognose (te weinig historiek): "
                 f"{', '.join(overgeslagen)}.")
    r.append("")

    # 5. censurering
    r.append("## 5. De grens van elke voorspelling hier: gecensureerde vraag")
    r.append("")
    r.append("Het model voorspelt **verkoop**, niet **vraag**. De meting van "
             "O8 (12–13 augustus 2026, `make censurering`): 33 % van de "
             "gewogen product-dagen draagt een leeg-reksignaal en 98 producten "
             "met samen 66 % van de omzet zijn structureel gecensureerd — wat "
             "uitverkocht raakt, had méér kunnen verkopen. De dagomzetprognose "
             "hierboven erft die ondergrens: ze voorspelt wat er onder het "
             "huidige aanbod verkocht wordt. De correctie uit "
             "`docs/model-ontwerp.md` §3 hoort bij een productprognose, en die "
             "staat bewust niet in productie (20,1 % WAPE per product-dag is "
             "gemeten, maar zonder marges is er geen beslissing die erop kan "
             "bouwen). De wachter `censureringsdrempel` bewaakt intussen of "
             "het signaal verschuift.")
    r.append("")

    # 6. niet gedaan
    r.append("## 6. Bewust niet gedaan, met reden")
    r.append("")
    r.append("- **Her-extractie 2024-09-19 t/m 2025-01-01** (Sinterklaas en "
             "Kerst 2024 in het verzekeringsarchief): zou de novemberweken en "
             "decemberweken een tweede waarneming geven, maar antwoord 24 van "
             "de klant noemde sep–dec 2024 implementatieruis in Odoo. Eerst "
             "die spanning beslechten (één vraag), dan pas meten — een "
             "seizoenscorrectie op ruis is erger dan geen correctie.")
    r.append("- **Zwaarder model (ML)**: de kalenderstructuur zit er nu "
             "expliciet in; op ±500 open dagen is er weinig over om te leren. "
             "Herzien bij een tweede volledige jaarcyclus.")
    r.append("")

    UIT.parent.mkdir(parents=True, exist_ok=True)
    UIT.write_text("\n".join(r) + "\n", encoding="utf-8")
    print(f"E4 geschreven: {UIT.relative_to(REPO)} ({UIT.stat().st_size:,} bytes, "
          "gitignored)".replace(",", "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
