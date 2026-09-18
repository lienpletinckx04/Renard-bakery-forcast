"""Tests voor het backtest-harnas.

De belangrijkste test hieronder is `test_voorspelling_op_andere_dagen_wordt_geweigerd`.
De vorige versie van `evalueer()` vergeleek voorspelling en werkelijkheid met
`zip()`, dus op positie. Op een reeks met sluitingsdagen liepen die uiteen en
rekende het harnas stilzwijgend de verkeerde dagen tegen elkaar af. Een backtest
die een geloofwaardig maar verkeerd cijfer produceert, is gevaarlijker dan geen
backtest.
"""
import numpy as np
import pandas as pd
import pytest

from bakkerij.backtest.rolling import (
    Resultaat,
    band_per_stap,
    dekking,
    evalueer,
    kalibreer_kwantielen,
    origins,
    per_horizon,
    trackrecord,
    vergelijk,
)
from bakkerij.model.baseline import naive, seizoen_naive

PATROON = np.array([10.0, 10.0, 10.0, 10.0, 20.0, 30.0, 5.0])


def _reeks(dagen=200, start="2025-01-06") -> pd.Series:
    index = pd.date_range(start, periods=dagen, freq="D")
    return pd.Series(PATROON[index.dayofweek], index=index)


# --- origins ----------------------------------------------------------------

def test_origins_laat_voorspelling_en_werkelijkheid_op_dezelfde_dagen_vallen():
    r = _reeks()
    met_gat = r.drop(pd.date_range("2025-03-03", periods=3, freq="D"))
    for venster in origins(met_gat, min_train=60, stap=5, horizon=7):
        assert venster.doeldagen.equals(venster.werkelijk.index)
        # En geen enkele doeldag valt binnen de trainperiode.
        assert venster.doeldagen.min() > venster.train.index.max()


def test_origins_voorspelt_nooit_een_dag_die_niet_gemeten_is():
    """Horizon is in open dagen. Een gesloten dag komt niet voor als doeldag."""
    r = _reeks()
    dicht = pd.date_range("2025-03-03", periods=10, freq="D")
    met_gat = r.drop(dicht)
    alle_doeldagen = [
        d for v in origins(met_gat, min_train=40, stap=3, horizon=7) for d in v.doeldagen
    ]
    assert not set(alle_doeldagen) & set(dicht)
    assert set(alle_doeldagen) <= set(met_gat.index)


def test_origins_weigert_een_te_korte_reeks():
    with pytest.raises(ValueError, match="Te weinig open dagen"):
        list(origins(_reeks(dagen=20), min_train=90, horizon=7))


def test_origins_weigert_dubbele_datums():
    r = _reeks(dagen=100)
    dubbel = pd.concat([r, r.iloc[[5]]]).sort_index()
    with pytest.raises(ValueError, match="[Dd]ubbele datums"):
        list(origins(dubbel, min_train=50, horizon=7))


def test_origins_weigert_een_ongesorteerde_reeks():
    with pytest.raises(ValueError, match="gesorteerd"):
        list(origins(_reeks(dagen=200).iloc[::-1], min_train=90, horizon=7))


# --- evalueer ---------------------------------------------------------------

def test_perfecte_voorspeller_heeft_nul_afwijking():
    r = _reeks()
    res = evalueer(r, seizoen_naive, naam="seizoen_naive", min_train=60, horizon=7)
    assert res.som_absolute_fout == pytest.approx(0.0)
    assert res.wape == pytest.approx(0.0)
    assert res.bias_euro == pytest.approx(0.0)
    assert res.n_dagen > 0


def test_perfecte_voorspeller_blijft_perfect_over_een_sluiting():
    """Zonder de datumuitlijning zou dit een fout van tientallen procenten geven."""
    r = _reeks()
    met_gat = r.drop(pd.date_range("2025-03-03", periods=3, freq="D"))
    res = evalueer(met_gat, seizoen_naive, naam="seizoen_naive",
                   min_train=60, horizon=7)
    assert res.som_absolute_fout == pytest.approx(0.0)


def test_bias_ziet_een_structureel_te_hoge_voorspelling():
    r = _reeks()

    def tien_procent_te_hoog(historiek, doeldagen):
        return seizoen_naive(historiek, doeldagen) * 1.10

    res = evalueer(r, tien_procent_te_hoog, naam="te hoog", min_train=60, horizon=7)
    assert res.bias_euro > 0
    assert res.wape == pytest.approx(0.10, abs=1e-9)


def test_voorspelling_op_andere_dagen_wordt_geweigerd():
    """De regel die het harnas eerlijk houdt."""
    r = _reeks()

    def verschoven(historiek, doeldagen):
        return pd.Series(1.0, index=doeldagen + pd.Timedelta(days=1))

    with pytest.raises(ValueError, match="andere dagen dan gevraagd"):
        evalueer(r, verschoven, naam="verschoven", min_train=60, horizon=7)


def test_wape_is_de_afwijking_als_aandeel_van_de_omzet():
    r = pd.Series(100.0, index=pd.date_range("2025-01-06", periods=120, freq="D"))

    def altijd_negentig(historiek, doeldagen):
        return pd.Series(90.0, index=doeldagen)

    res = evalueer(r, altijd_negentig, naam="90", min_train=60, horizon=7)
    assert res.wape == pytest.approx(0.10)
    assert res.mae_euro == pytest.approx(10.0)


def test_zonder_economie_blijft_de_kost_leeg():
    """De kostprijzen bestaan niet (vraag 19); dat mag geen verzonnen nul worden."""
    res = evalueer(_reeks(), naive, naam="naive", min_train=60, horizon=7)
    assert res.kost_euro is None


def test_alleen_dagen_beperkt_de_afrekening_maar_niet_de_training():
    """Een feestdagcorrectie raakt een handvol dagen per jaar; in het
    totaalcijfer verdrinkt zo'n effect. `alleen_dagen` rekent alleen die dagen
    af, met dezelfde training en dezelfde origins."""
    reeks = _reeks()
    alles = evalueer(reeks, seizoen_naive, naam="alles", min_train=60, horizon=7)

    zaterdagen = reeks.index[reeks.index.dayofweek == 5]
    alleen_za = evalueer(reeks, seizoen_naive, naam="za", min_train=60, horizon=7,
                         alleen_dagen=zaterdagen)
    assert 0 < alleen_za.n_dagen < alles.n_dagen
    # Elke afgerekende dag is een zaterdag: op een perfect weekpatroon is de
    # seizoen-naive foutloos, dus de som blijft nul — maar de dagteller toont
    # dat er echt alleen zaterdagen geteld zijn.
    assert alleen_za.n_dagen == alles.n_dagen // 7


def test_alleen_dagen_zonder_enige_treffer_geeft_nul_dagen():
    reeks = _reeks()
    buiten = pd.DatetimeIndex(["2030-01-01"])
    res = evalueer(reeks, seizoen_naive, naam="x", min_train=60, horizon=7,
                   alleen_dagen=buiten)
    assert res.n_dagen == 0
    assert res.som_absolute_fout == 0.0


# --- per_horizon, dekking, trackrecord --------------------------------------

def test_per_horizon_geeft_een_rij_per_stap():
    df = per_horizon(_reeks(), seizoen_naive, min_train=60, horizon=7)
    assert list(df["stap"]) == [1, 2, 3, 4, 5, 6, 7]
    # Perfect weekpatroon: seizoen-naive is foutloos op elke stap.
    assert (df["wape"] == 0.0).all()
    assert (df["q_onder"] == 0.0).all()
    assert (df["q_boven"] == 0.0).all()


def test_per_horizon_maakt_de_fout_per_stap_zichtbaar():
    # naive zet de laatste trainingsdag op alles. Op het weekpatroon raakt dat
    # sommige stappen exact (de herhaalde 10-en) en andere fors ernaast: de
    # fout verschilt dus per stap, en dat is precies wat een gepoolde band
    # verbergt en deze meting toont.
    df = per_horizon(_reeks(), naive, min_train=60, horizon=7)
    assert df["wape"].max() > 0.4
    assert df["wape"].min() == pytest.approx(0.0)
    assert df["wape"].nunique() > 1


def test_dekking_is_out_of_sample_en_dekt_een_foutloze_voorspeller_volledig():
    df = dekking(_reeks(400), seizoen_naive, min_train=60, horizon=7)
    gemeten = df.dropna(subset=["binnen_band"])
    # Foutloze voorspeller: de werkelijkheid ligt altijd op de puntvoorspelling
    # en dus binnen elke band.
    assert (gemeten["binnen_band"] == 1.0).all()
    assert np.allclose(gemeten["beloofd"], 0.8)


def test_dekking_telt_pas_na_genoeg_eerdere_origins():
    # Korte reeks: te weinig origins om ooit een band te bouwen -> nul tellingen.
    df = dekking(_reeks(120), seizoen_naive, min_train=60, horizon=7)
    assert (df["n"] == 0).all()


def test_trackrecord_is_out_of_sample_en_dekt_de_gevraagde_dagen():
    df = trackrecord(_reeks(200), seizoen_naive, dagen=28, min_train=60, horizon=7)
    assert len(df) == 28
    # Elke dag hoort bij het weekpatroon en de voorspelling was foutloos.
    assert (df["verwacht"] == df["werkelijk"]).all()
    # De stappen lopen 1..7: elke dag is door precies één venster voorspeld.
    assert set(df["stap"]) <= set(range(1, 8))
    # En de datums zijn uniek én oplopend.
    assert df["datum"].is_unique
    assert df["datum"].is_monotonic_increasing


def test_band_per_stap_verbreedt_met_de_horizon():
    stappen = pd.DataFrame({
        "stap": [1, 2],
        "q_onder": [-0.05, -0.20],
        "q_boven": [0.05, 0.25],
    })
    punt = pd.Series([100.0, 100.0, 100.0],
                     index=pd.date_range("2026-05-01", periods=3, freq="D"))
    band = band_per_stap(punt, stappen)
    # Dag 1 draagt de smalle band van stap 1, dag 2 de brede van stap 2, en
    # dag 3 (voorbij de gemeten stappen) erft die van de laatste stap.
    assert band.loc[0, "boven"] - band.loc[0, "onder"] < (
        band.loc[1, "boven"] - band.loc[1, "onder"]
    )
    assert band.loc[2, "onder"] == band.loc[1, "onder"]
    assert band.loc[0, "onder"] == pytest.approx(100 / 1.05)
    assert band.loc[0, "boven"] == pytest.approx(100 / 0.95)


def test_band_per_stap_weigert_lege_kwantielen():
    punt = pd.Series([100.0], index=pd.date_range("2026-05-01", periods=1))
    with pytest.raises(ValueError, match="per_horizon"):
        band_per_stap(punt, pd.DataFrame())


# --- vergelijk --------------------------------------------------------------

def _resultaat(naam: str, fout: float) -> Resultaat:
    return Resultaat(
        naam=naam, n_dagen=100, som_werkelijk=10_000.0,
        som_absolute_fout=fout, som_fout=0.0, mediane_absolute_fout=fout / 100,
    )


def test_vergelijk_rangschikt_op_afwijking_en_noemt_de_winst():
    tekst = vergelijk([_resultaat("slecht", 900.0), _resultaat("goed", 500.0)])
    assert tekst.index("goed") < tekst.index("slecht")
    assert "44.4%" in tekst


def test_vergelijk_waarschuwt_als_het_verschil_binnen_de_ruis_valt():
    tekst = vergelijk([_resultaat("a", 1000.0), _resultaat("b", 980.0)])
    assert "gelijkwaardig" in tekst


def test_vergelijk_zonder_resultaten_valt_niet_om():
    assert vergelijk([]) == "Geen resultaten."


# --- bandkalibratie -----------------------------------------------------------

def _ruisreeks(schaal: float, dagen: int = 300) -> pd.Series:
    """Weekpatroon met vaste, gezaaide ruis. Geen klok, geen echte data."""
    index = pd.date_range("2025-01-06", periods=dagen, freq="D")
    rng = np.random.default_rng(7)
    basis = PATROON[index.dayofweek]
    return pd.Series(basis * (1 + rng.normal(0, schaal, dagen)), index=index)


def test_kalibratie_kiest_de_smalste_band_die_het_doel_haalt():
    """Zelfs met 2% ruis dekt de nominale 10-90-band out-of-sample maar ~69%:
    kwantielen op een handvol residuen per stap zijn zelf ruis. De kalibratie
    hoort dan één stap te verbreden — naar het smalste paar dat het doel
    haalt — en niet meteen naar de breedste kandidaat te springen."""
    kal = kalibreer_kwantielen(_ruisreeks(0.02), seizoen_naive, doel=0.80,
                               min_train=90, stap=7, horizon=7)
    assert (kal.onder, kal.boven) == (0.075, 0.925)
    assert kal.gemeten >= kal.doel - 0.05


def test_kalibratie_verbreedt_wanneer_de_smalle_band_te_weinig_dekt():
    """Zware, dikstaartige ruis: 10-90 uit eerdere origins dekt te weinig en
    de kalibratie moet doorschuiven naar een breder paar."""
    index = pd.date_range("2025-01-06", periods=300, freq="D")
    rng = np.random.default_rng(11)
    # t-verdeling met 2 vrijheidsgraden: dikke staarten, precies het geval
    # waarin in-sample-kwantielen out-of-sample onderschatten.
    ruis = rng.standard_t(2, 300) * 0.25
    reeks = pd.Series(PATROON[index.dayofweek] * np.clip(1 + ruis, 0.05, None),
                      index=index)
    smal = kalibreer_kwantielen(reeks, naive, doel=0.95, tolerantie=0.0,
                                min_train=90, stap=7, horizon=7)
    assert (smal.onder, smal.boven) != (0.10, 0.90)
    assert not smal.dekking.empty


def test_kalibratie_weigert_zonder_meetbare_dekking():
    with pytest.raises(ValueError, match="origins"):
        kalibreer_kwantielen(_reeks(dagen=100), naive,
                             min_train=90, stap=7, horizon=7)
