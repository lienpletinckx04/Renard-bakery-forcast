"""De vertaling contractboom -> databaserijen (bakkerij/db/contract_rijen.py).

Wat hier vastligt is gedrag, niet implementatie: welke boom welke rijen
oplevert, en dat elke vorm van half gebouwd contract luid faalt in plaats
van half geüpload te worden. De fixtures zijn verzonnen JSON zonder enige
klantdata.
"""

import json

import pytest

from bakkerij.db import contract_rijen as cr
from bakkerij.taal import TALEN


def _schrijf_taalmap(map_, winkels=()):
    """Een minimale maar volledige taalmap: zes schermen plus de index."""
    map_.mkdir(parents=True, exist_ok=True)
    for scherm in cr.SCHERMEN:
        (map_ / f"{scherm}.json").write_text(
            json.dumps({"scherm": scherm}), encoding="utf-8"
        )
    index = {
        "winkels": [{"naam": s.capitalize(), "slug": s} for s in winkels],
        "niet_toegewezen": [],
        "melding": None,
        "overgeslagen": [],
    }
    (map_ / "winkels.json").write_text(json.dumps(index), encoding="utf-8")
    for slug in winkels:
        doel = map_ / "winkels" / slug
        doel.mkdir(parents=True)
        for scherm in cr.SCHERMEN:
            (doel / f"{scherm}.json").write_text(
                json.dumps({"scherm": scherm, "winkel": slug}),
                encoding="utf-8",
            )


def _boom(tmp_path, winkels=()):
    _schrijf_taalmap(tmp_path, winkels)
    _schrijf_taalmap(tmp_path / "fr", winkels)
    return tmp_path


def test_volledige_boom_zonder_winkels(tmp_path):
    rijen = cr.verzamel(_boom(tmp_path))
    # Per taal: zes schermen plus de winkelindex.
    assert len(rijen) == len(TALEN) * (len(cr.SCHERMEN) + 1)
    assert {r.taal for r in rijen} == set(TALEN)
    assert all(r.winkel == cr.TOTAAL for r in rijen)
    schermen_nl = [r.scherm for r in rijen if r.taal == "nl"]
    assert schermen_nl == list(cr.SCHERMEN) + [cr.WINKELINDEX]


def test_winkels_rijden_mee(tmp_path):
    rijen = cr.verzamel(_boom(tmp_path, winkels=("centrum", "markt")))
    per_taal = len(cr.SCHERMEN) + 1 + 2 * len(cr.SCHERMEN)
    assert len(rijen) == len(TALEN) * per_taal
    winkels = {r.winkel for r in rijen} - {cr.TOTAAL}
    assert winkels == {"centrum", "markt"}
    # De winkelrij draagt de winkel-JSON, niet die van het totaal.
    rij = next(r for r in rijen
               if r.taal == "fr" and r.winkel == "markt" and r.scherm == "marge")
    assert json.loads(rij.antwoord) == {"scherm": "marge", "winkel": "markt"}


def test_de_json_gaat_er_onaangeraakt_in(tmp_path):
    boom = _boom(tmp_path)
    origineel = (boom / "overzicht.json").read_text(encoding="utf-8")
    rij = next(r for r in cr.verzamel(boom)
               if r.taal == "nl" and r.scherm == "overzicht")
    assert rij.antwoord == origineel


def test_twee_runs_geven_dezelfde_volgorde(tmp_path):
    boom = _boom(tmp_path, winkels=("b", "a"))
    assert cr.verzamel(boom) == cr.verzamel(boom)


def test_ontbrekend_scherm_faalt_luid(tmp_path):
    boom = _boom(tmp_path)
    (boom / "prognose.json").unlink()
    with pytest.raises(FileNotFoundError, match="prognose"):
        cr.verzamel(boom)


def test_ontbrekende_taalmap_faalt_luid(tmp_path):
    _schrijf_taalmap(tmp_path)  # alleen nl, geen fr/
    with pytest.raises(FileNotFoundError, match="fr"):
        cr.verzamel(tmp_path)


def test_kapotte_json_faalt_luid(tmp_path):
    boom = _boom(tmp_path)
    (boom / "fr" / "stand.json").write_text("{half", encoding="utf-8")
    with pytest.raises(ValueError, match="stand"):
        cr.verzamel(boom)


def test_winkelmap_buiten_de_index_faalt_luid(tmp_path):
    boom = _boom(tmp_path, winkels=("centrum",))
    spook = boom / "winkels" / "spook"
    spook.mkdir()
    with pytest.raises(ValueError, match="half gebouwd"):
        cr.verzamel(boom)


def test_index_zonder_winkelmap_faalt_luid(tmp_path):
    boom = _boom(tmp_path, winkels=("centrum",))
    index_pad = boom / "winkels.json"
    index = json.loads(index_pad.read_text(encoding="utf-8"))
    index["winkels"].append({"naam": "Erbij", "slug": "erbij"})
    index_pad.write_text(json.dumps(index), encoding="utf-8")
    with pytest.raises(ValueError, match="half gebouwd"):
        cr.verzamel(boom)


def test_schermen_lopen_gelijk_met_de_ui():
    """Het Scherm-type in laadContract.ts noemt dezelfde zes namen. Wijzigt
    één van beide kanten, dan hoort deze test het gesprek af te dwingen."""
    from pathlib import Path

    bron = (Path(__file__).resolve().parents[1]
            / "platform" / "lib" / "laadContract.ts").read_text(encoding="utf-8")
    for scherm in cr.SCHERMEN:
        assert f'"{scherm}"' in bron, f"UI kent scherm {scherm!r} niet"


# --- de krimpwacht ----------------------------------------------------------

def test_geen_krimp_is_geen_bezwaar():
    """Dezelfde sleutels opnieuw schrijven is de normale nachtelijke run."""
    sleutels = {("overzicht", "nl", ""), ("overzicht", "fr", "")}
    assert cr.ontbrekende_sleutels(sleutels, sleutels) == set()


def test_een_erbij_gekomen_winkel_is_geen_krimp():
    bestaand = {("overzicht", "nl", "")}
    nieuw = {("overzicht", "nl", ""), ("overzicht", "nl", "centrum")}
    assert cr.ontbrekende_sleutels(bestaand, nieuw) == set()


def test_een_verdwenen_winkel_wordt_gemeld():
    """Het runner-scenario: zonder data/config/winkels.json bouwt de sync geen
    winkelantwoorden, en die zouden anders stilzwijgend het volledige contract
    vervangen -- een groene run met minder cijfers op het scherm."""
    bestaand = {("overzicht", "nl", ""), ("overzicht", "nl", "centrum")}
    nieuw = {("overzicht", "nl", "")}
    assert cr.ontbrekende_sleutels(bestaand, nieuw) == {("overzicht", "nl", "centrum")}


def test_een_verdwenen_taal_wordt_gemeld():
    bestaand = {("overzicht", "nl", ""), ("overzicht", "fr", "")}
    nieuw = {("overzicht", "nl", "")}
    assert cr.ontbrekende_sleutels(bestaand, nieuw) == {("overzicht", "fr", "")}


# --- de tweede helft: dezelfde sleutels, armere inhoud ----------------------

SLEUTEL = ("kanalen", "nl", "")


def _rijk(bronnen=("tgtg", "winkel"), onbeschikbaar=()):
    """Een Rijkdom zoals de contractbouw hem zou opleveren."""
    return cr.rijkdom_uit_velden(
        list(bronnen), [{"veld": v, "reden": "..."} for v in onbeschikbaar]
    )


def test_rijkdom_uit_json_leest_de_twee_velden():
    antwoord = json.dumps({
        "versie": 1,
        "bron": ["tgtg", "winkel"],
        "onbeschikbaar": [{"veld": "marge_per_groep", "reden": "geen kosten"}],
        "data": {"van alles": "wat hier niet toe doet"},
    })
    r = cr.rijkdom_uit_json(antwoord)
    assert r.bronnen == frozenset({"tgtg", "winkel"})
    assert r.ontbrekende_invoer == frozenset({"marge_per_groep"})


def test_een_antwoord_zonder_bron_is_geen_fout():
    """De winkelindex draagt geen bron en geen onbeschikbaar; dat mag."""
    r = cr.rijkdom_uit_json(json.dumps({"winkels": [], "onbeschikbaar": None}))
    assert r == cr.Rijkdom(frozenset(), frozenset())


def test_gemeten_onbeschikbaarheid_telt_niet_mee():
    """Een kerncijfer zonder jaarvergelijking is een gemeten feit, geen
    ontbrekende invoer -- die komen en gaan met de periode op het scherm, en
    een wacht die daarop aanslaat kleurt de nachtrun rood op een dinsdag."""
    r = _rijk(onbeschikbaar=("kerncijfer.omzet_7",))
    assert r.ontbrekende_invoer == frozenset()


def test_dezelfde_bouw_is_geen_verarming():
    stand = {SLEUTEL: _rijk()}
    assert cr.verarming(stand, stand) == []


def test_een_verdwenen_bron_wordt_gemeld():
    """Het runner-scenario: zonder data/interim/ bouwt de sync exact dezelfde
    veertien sleutels, met TGTG eruit."""
    bestaand = {SLEUTEL: _rijk(("tgtg", "winkel"))}
    nieuw = {SLEUTEL: _rijk(("winkel",))}
    [gevonden] = cr.verarming(bestaand, nieuw)
    assert gevonden.sleutel == SLEUTEL
    assert gevonden.verloren_bronnen == frozenset({"tgtg"})
    assert "tgtg" in gevonden.beschrijf()


def test_een_weggevallen_kostenmodel_wordt_gemeld():
    bestaand = {SLEUTEL: _rijk()}
    nieuw = {SLEUTEL: _rijk(onbeschikbaar=("marge_per_groep",))}
    [gevonden] = cr.verarming(bestaand, nieuw)
    assert gevonden.verloren_invoer == frozenset({"marge_per_groep"})


def test_rijker_worden_mag_stilzwijgend():
    """De eerste nacht ná de Deliveroo-historiek hoort niemand wakker te
    maken, en evenmin de eerste nacht ná het invullen van het kostenmodel."""
    bestaand = {SLEUTEL: _rijk(("winkel",), onbeschikbaar=("marge_per_groep",))}
    nieuw = {SLEUTEL: _rijk(("deliveroo", "tgtg", "winkel"))}
    assert cr.verarming(bestaand, nieuw) == []


def test_een_verdwenen_sleutel_telt_hier_niet_dubbel():
    """Die meldt `ontbrekende_sleutels` al; twee meldingen over één feit
    maken de gefaalde run juist moeilijker te lezen."""
    bestaand = {SLEUTEL: _rijk(), ("kanalen", "nl", "centrum"): _rijk()}
    nieuw = {SLEUTEL: _rijk()}
    assert cr.verarming(bestaand, nieuw) == []


def test_een_lege_bestaande_tabel_blokkeert_de_eerste_run_niet():
    assert cr.verarming({}, {SLEUTEL: _rijk()}) == []


def test_de_melding_draagt_geen_inhoud():
    """Alleen machinewaarden: scherm, taal, winkel, kanaal, veldnaam."""
    bestaand = {SLEUTEL: _rijk(("tgtg", "winkel"))}
    nieuw = {SLEUTEL: _rijk(("winkel",), onbeschikbaar=("marge_per_groep",))}
    regel = cr.verarming(bestaand, nieuw)[0].beschrijf()
    assert regel == "kanalen/nl (bron weg: tgtg; invoer weg: marge_per_groep)"


def test_verarming_staat_op_vaste_volgorde():
    bestaand = {
        ("prognose", "nl", ""): _rijk(),
        ("kanalen", "nl", ""): _rijk(),
        ("marge", "fr", ""): _rijk(),
    }
    nieuw = {s: _rijk(("winkel",)) for s in bestaand}
    assert [v.sleutel for v in cr.verarming(bestaand, nieuw)] == [
        ("kanalen", "nl", ""), ("marge", "fr", ""), ("prognose", "nl", ""),
    ]
