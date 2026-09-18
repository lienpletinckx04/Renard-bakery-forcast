"""TGTG-restwaarde per kwartaal (deliverable A5).

Elke verkochte verrassingszak is omzet uit producten die anders derving
waren. Dit rapport zet per kwartaal op een rij wat dat opleverde: netto (wat
er binnenkwam), en met de kanaalkosttabel erbij ook bruto en commissie.

Uitvoer naar reports/ — gitignored, want dit zijn omzetcijfers van de
eindklant (harde regel 2).

Draaien:  make tgtg-restwaarde   (na make canoniek)
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pandas as pd

from bakkerij import berekening as bk
from bakkerij import canoniek
from bakkerij import contract as ct
from bakkerij.opmaak import euro_nl

INTERIM = REPO / "data" / "interim"
UIT = REPO / "reports" / "tgtg-restwaarde.md"


def main() -> int:
    for nodig in ("canoniek_verkopen.csv", "canoniek_kalender.csv"):
        if not (INTERIM / nodig).exists():
            raise SystemExit(f"data/interim/{nodig} ontbreekt. Draai eerst: make canoniek")
    verkopen = pd.read_csv(INTERIM / "canoniek_verkopen.csv", parse_dates=["datum"],
                           dtype=canoniek.CANONIEK_DTYPES)
    kalender = pd.read_csv(INTERIM / "canoniek_kalender.csv", parse_dates=["datum"])
    kost_pad = INTERIM / "canoniek_kanaalkost.csv"
    kanaalkost = (pd.read_csv(kost_pad, dtype={"maand": str})
                  if kost_pad.exists() else None)

    open_v = bk.open_verkopen(verkopen, kalender)
    totalen = bk.dagtotalen(open_v)
    tabel = bk.tgtg_restwaarde_per_kwartaal(totalen, kanaalkost)

    r: list[str] = ["# TGTG-restwaarde per kwartaal (A5)", ""]
    r.append(f"*Gebouwd {ct.nu().date().isoformat()}. Elke verkochte "
             "verrassingszak is omzet uit producten die anders derving waren; "
             "netto is wat er werkelijk binnenkwam, bruto wat de klant "
             "betaalde, commissie het verschil. NB: TGTG meet ook op dagen "
             "dat de winkel dicht is; die tellen hier gewoon mee.*")
    r.append("")
    if tabel.empty:
        r.append("Geen TGTG-verkoop in het canonieke model.")
    else:
        r.append("| Kwartaal | Stuks | Netto (restwaarde) | Commissie | Bruto |")
        r.append("|---|---:|---:|---:|---:|")
        for rij in tabel.itertuples():
            commissie = euro_nl(str(rij.commissie)) if rij.commissie is not None \
                else "niet te berekenen"
            bruto = euro_nl(str(rij.bruto)) if rij.bruto is not None \
                else "niet te berekenen"
            r.append(f"| {rij.kwartaal} | {rij.stuks} | {euro_nl(str(rij.netto))} "
                     f"| {commissie} | {bruto} |")
        r.append("")
        r.append("Kanttekening: het jongste kwartaal is doorgaans onvolledig "
                 "gemeten; vergelijk kwartalen pas wanneer ze allebei vol zijn.")

    UIT.parent.mkdir(parents=True, exist_ok=True)
    UIT.write_text("\n".join(r) + "\n", encoding="utf-8")
    print(f"A5 geschreven: {UIT.relative_to(REPO)} (gitignored), "
          f"{len(tabel)} kwartalen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
