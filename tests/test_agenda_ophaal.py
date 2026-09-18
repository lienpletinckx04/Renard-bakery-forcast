"""Tests voor het ophalen en de configuratie van de agendafeed.

Er komt hier geen enkele echte agenda aan te pas. Waar een netwerk nodig is,
draait er een webserver op 127.0.0.1 die de voorbeeldfeed uit `tests/fixtures/`
serveert — dat is een echte HTTP-heenweg met echte statuscodes, en het bewijst
meer dan een nagemaakte `urlopen`.

De drie faalgevallen die de nachtelijke keten niet mogen omleggen, staan hier
alle drie: onbereikbaar, 404, en iets dat geen iCal is.
"""
from __future__ import annotations

import contextlib
import datetime
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from bakkerij.sources import agenda as ag
from bakkerij.sources import agenda_ophaal as op

FIXTURE = Path(__file__).parent / "fixtures" / "agenda-voorbeeld.ics"


# --- gereedschap ------------------------------------------------------------

@contextlib.contextmanager
def _webserver(antwoorden: dict[str, tuple[int, str, bytes]]):
    """Serveert vaste antwoorden op 127.0.0.1 en geeft het basisadres terug."""

    class Behandelaar(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        # De naam do_GET ligt vast in http.server en volgt niet onze stijl.
        def do_GET(self):
            status, soort, lijf = antwoorden.get(
                self.path, (404, "text/plain; charset=utf-8", b"Not Found"))
            self.send_response(status)
            self.send_header("Content-Type", soort)
            self.send_header("Content-Length", str(len(lijf)))
            self.end_headers()
            self.wfile.write(lijf)

        def log_message(self, *_args):
            pass  # geen serverruis in de testuitvoer

    server = ThreadingHTTPServer(("127.0.0.1", 0), Behandelaar)
    # Kleine pollstap: anders kost het afsluiten van elke server een halve
    # seconde en wordt de suite trager dan de rest bij elkaar.
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02},
                     daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


def _dichte_poort() -> int:
    """Een poort die gegarandeerd niemand beantwoordt."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    poort = s.getsockname()[1]
    s.close()
    return poort


def _feed_bytes() -> bytes:
    # Echte agenda's leveren CRLF af, zoals RFC 5545 voorschrijft.
    return FIXTURE.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8")


# --- configuratie: zonder sleutel doet de laag niets ------------------------

def test_zonder_sleutel_en_zonder_env_doet_de_laag_niets(tmp_path):
    inst = op.lees_instelling(omgeving={}, env_pad=tmp_path / "bestaat-niet.env")
    assert inst.ingesteld is False

    a = op.haal_agenda(inst)
    assert a.bruikbaar is False
    assert "niet ingesteld" in a.reden_onbruikbaar
    assert a.dagen == []


def test_lege_sleutel_telt_als_niet_ingesteld(tmp_path):
    env = tmp_path / ".env"
    env.write_text("AGENDA_ICS_URL=\n", encoding="utf-8")
    assert op.lees_instelling(omgeving={}, env_pad=env).ingesteld is False


def test_env_bestand_wordt_gelezen_met_commentaar_en_aanhalingstekens(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "# commentaar\n"
        "\n"
        "ANDERE_SLEUTEL=iets\n"
        'AGENDA_ICS_URL="https://example.test/geheim.ics"\n',
        encoding="utf-8")
    sleutels = op.lees_env_bestand(env)
    assert sleutels["AGENDA_ICS_URL"] == "https://example.test/geheim.ics"
    assert sleutels["ANDERE_SLEUTEL"] == "iets"


def test_ontbrekend_env_bestand_is_geen_fout(tmp_path):
    assert op.lees_env_bestand(tmp_path / "weg.env") == {}


def test_omgevingsvariabele_wint_van_env_bestand(tmp_path):
    env = tmp_path / ".env"
    env.write_text("AGENDA_ICS_URL=https://uit-bestand.test/a.ics\n", encoding="utf-8")
    inst = op.lees_instelling(
        omgeving={"AGENDA_ICS_URL": "https://uit-omgeving.test/a.ics"}, env_pad=env)
    assert inst.url == "https://uit-omgeving.test/a.ics"
    assert "omgevingsvariabele" in inst.herkomst


# --- wat er wel en niet opgehaald mag worden --------------------------------

def test_webcal_wordt_https():
    assert op.normaliseer_url("webcal://p1.test/x.ics") == "https://p1.test/x.ics"


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "ftp://ergens.test/agenda.ics",
    "gewoon-wat-tekst",
    "https://",
])
def test_alleen_http_en_https_mogen_opgehaald_worden(url):
    a = op.haal_agenda(op.Instelling(url=url))
    assert a.bruikbaar is False
    assert a.reden_onbruikbaar


def test_de_geheime_link_komt_niet_in_de_melding():
    # De iCal-link is een wachtwoord. Een reden die op het scherm mag, mag hem
    # niet bevatten.
    geheim = f"http://127.0.0.1:{_dichte_poort()}/geheim-pad-abc123.ics"
    a = op.haal_agenda(op.Instelling(url=geheim), timeout=2.0)
    assert a.bruikbaar is False
    assert "geheim-pad-abc123" not in a.reden_onbruikbaar
    assert op.kort_adres(geheim) == "http://127.0.0.1/…"


# --- het ophalen zelf, tegen een echte server -------------------------------

def test_de_voorbeeldfeed_wordt_over_http_opgehaald_en_gelezen():
    lijf = _feed_bytes()
    with _webserver({"/geheim.ics": (200, "text/calendar; charset=utf-8", lijf)}) as basis:
        a = op.haal_agenda(op.Instelling(url=f"{basis}/geheim.ics"))

    assert a.bruikbaar
    # De zomersluiting van 3 t/m 17 augustus (DTEND 18 is exclusief).
    dicht = sorted(d.datum for d in a.dagen if d.kenmerk == "gepland_dicht")
    assert dicht[0] == datetime.date(2026, 8, 3)
    assert datetime.date(2026, 8, 17) in dicht
    assert datetime.date(2026, 8, 18) not in dicht
    # Alle vier de kenmerken zitten in de voorbeeldfeed.
    assert {d.kenmerk for d in a.dagen} == {
        "gepland_dicht", "andere_uren", "promotie", "evenement"}
    # De agenda reikt tot de laatste dag die erin staat, en geen dag verder.
    assert a.tot == datetime.date(2026, 12, 24)


def test_de_voorbeeldfeed_meldt_wat_ze_niet_leest():
    lijf = _feed_bytes()
    with _webserver({"/a.ics": (200, "text/calendar", lijf)}) as basis:
        a = op.haal_agenda(op.Instelling(url=f"{basis}/a.ics"))

    assert any("herhalende reeks" in w for w in a.waarschuwingen)
    assert any("levering bloem" in w for w in a.waarschuwingen)


def test_de_ontsnapte_komma_van_google_staat_niet_in_de_reden():
    lijf = _feed_bytes()
    with _webserver({"/a.ics": (200, "text/calendar", lijf)}) as basis:
        a = op.haal_agenda(op.Instelling(url=f"{basis}/a.ics"))

    redenen = {d.reden for d in a.dagen}
    assert "jaarlijkse zomersluiting, winkel en atelier" in redenen
    assert not any("\\" in r for r in redenen)


def test_een_gevouwen_titel_komt_heel_terug():
    lijf = _feed_bytes()
    with _webserver({"/a.ics": (200, "text/calendar", lijf)}) as basis:
        a = op.haal_agenda(op.Instelling(url=f"{basis}/a.ics"))

    evenement = next(d for d in a.dagen if d.kenmerk == "evenement")
    assert evenement.reden.endswith("over twee regels afbreekt")


def test_de_ruwe_tekst_komt_mee_terug_en_is_leeg_als_het_misging():
    lijf = _feed_bytes()
    with _webserver({"/a.ics": (200, "text/calendar", lijf)}) as basis:
        agenda, ruw = op.haal_agenda_en_tekst(op.Instelling(url=f"{basis}/a.ics"))
    assert agenda.bruikbaar
    assert ruw.startswith("BEGIN:VCALENDAR")

    _, ruw_mislukt = op.haal_agenda_en_tekst(
        op.Instelling(url=f"http://127.0.0.1:{_dichte_poort()}/a.ics"), timeout=2.0)
    assert ruw_mislukt == ""


# --- de drie faalgevallen ---------------------------------------------------

def test_onbereikbare_agenda_geeft_een_reden_en_geen_fout():
    url = f"http://127.0.0.1:{_dichte_poort()}/a.ics"
    a = op.haal_agenda(op.Instelling(url=url), timeout=2.0)
    assert a.bruikbaar is False
    assert "niet bereikbaar" in a.reden_onbruikbaar
    assert a.dagen == []


def test_404_geeft_een_reden_en_geen_fout():
    with _webserver({}) as basis:
        a = op.haal_agenda(op.Instelling(url=f"{basis}/bestaat-niet.ics"))
    assert a.bruikbaar is False
    assert "404" in a.reden_onbruikbaar


def test_een_inlogpagina_is_geen_agenda():
    pagina = b"<!doctype html><html><body>Log in om verder te gaan</body></html>"
    with _webserver({"/a.ics": (200, "text/html; charset=utf-8", pagina)}) as basis:
        a = op.haal_agenda(op.Instelling(url=f"{basis}/a.ics"))
    assert a.bruikbaar is False
    assert "geen iCal-bestand" in a.reden_onbruikbaar


# --- de overige manieren waarop het misgaat ---------------------------------

def test_serverfout_geeft_een_reden_en_geen_fout():
    with _webserver({"/a.ics": (500, "text/plain", b"kapot")}) as basis:
        a = op.haal_agenda(op.Instelling(url=f"{basis}/a.ics"))
    assert a.bruikbaar is False
    assert "500" in a.reden_onbruikbaar


def test_een_lege_maar_geldige_agenda_is_onbruikbaar_en_niet_open():
    leeg = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"
    with _webserver({"/a.ics": (200, "text/calendar", leeg)}) as basis:
        a = op.haal_agenda(op.Instelling(url=f"{basis}/a.ics"))
    assert a.bruikbaar is False
    assert a.dagen == []
    # En het gevolg dat ertoe doet: de prognose schuift geen dag op.
    grens, reden = ag.prognose_grens(a, datetime.date(2026, 8, 7))
    assert grens == datetime.date(2026, 8, 7)
    assert reden


def test_een_te_groot_bestand_wordt_niet_binnengehaald():
    veel = b"BEGIN:VCALENDAR\r\n" + b"X-VULLING:x\r\n" * 1000
    with _webserver({"/a.ics": (200, "text/calendar", veel)}) as basis:
        a = op.haal_agenda(op.Instelling(url=f"{basis}/a.ics"), max_bytes=500)
    assert a.bruikbaar is False
    assert "groter dan" in a.reden_onbruikbaar


def test_bestand_dat_geen_utf8_is_wordt_gemeld():
    rommel = b"BEGIN:VCALENDAR\xff\xfe\r\nEND:VCALENDAR"
    with _webserver({"/a.ics": (200, "text/calendar; charset=utf-8", rommel)}) as basis:
        a = op.haal_agenda(op.Instelling(url=f"{basis}/a.ics"))
    assert a.bruikbaar is False
    assert "leesbare tekst" in a.reden_onbruikbaar


def test_een_trage_agenda_loopt_af_op_de_timeout(monkeypatch):
    def traag(*_args, **_kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(op.urllib.request, "urlopen", traag)
    a = op.haal_agenda(op.Instelling(url="https://traag.test/a.ics"), timeout=3)
    assert a.bruikbaar is False
    assert "3 seconden" in a.reden_onbruikbaar


def test_een_fout_in_onze_eigen_code_crasht_luidruchtig(monkeypatch):
    # O18: geen blinde except. Wat het net niet stuk maakt, hoort te vallen.
    def stuk(*_args, **_kwargs):
        raise TypeError("dit is onze eigen schuld")

    monkeypatch.setattr(op.urllib.request, "urlopen", stuk)
    with pytest.raises(TypeError):
        op.haal_agenda(op.Instelling(url="https://example.test/a.ics"))
