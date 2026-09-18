"""bakkerij/omgeving: de ene .env-lezer die alle scripts delen (18 aug 2026).

Twee gedragingen zijn contractueel en staan hier vast: een al gezette
omgevingsvariabele wint van .env (anders overschrijft een achtergebleven
lokale .env een CI-secret), en een ontbrekend bestand is geen fout (een
verse machine zonder .env moet de droge paden gewoon kunnen draaien).
"""
import os

from bakkerij.omgeving import laad_env


def test_bestaande_variabele_wint_van_env_bestand(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "# commentaar telt niet\n"
        "OMGEVING_TEST_A=uit_bestand\n"
        "OMGEVING_TEST_B = met spaties \n"
        "regel zonder isteken\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OMGEVING_TEST_A", "al_gezet")
    monkeypatch.delenv("OMGEVING_TEST_B", raising=False)
    try:
        laad_env(env)
        assert os.environ["OMGEVING_TEST_A"] == "al_gezet"
        assert os.environ["OMGEVING_TEST_B"] == "met spaties"
    finally:
        os.environ.pop("OMGEVING_TEST_B", None)


def test_ontbrekend_bestand_is_geen_fout(tmp_path):
    laad_env(tmp_path / "bestaat-niet.env")
