"""Nederlands en Frans in de berekeningslaag, want de labels horen bij de cijfers.

WAAROM DIT HIER STAAT EN NIET IN DE UI

`platform/lib/contract.ts` zegt het al: "Elk label dat een mens leest, staat
kant-en-klaar in de data." Dat is harde regel 4 in zijn scherpste vorm — de UI
rekent niet, en ze verzint ook geen tekst. Een Franse gebruiker die "Verwachte
omzet" op zijn as ziet staan, kijkt naar een label dat de berekeningslaag heeft
gemaakt; de UI kan daar niets aan doen zonder de regel te breken.

Dus wordt het contract twee keer gebouwd, één keer per taal, en leest de UI de
map die bij de gekozen taal hoort. Een echte API zou hetzelfde doen met
`Accept-Language`: zelfde cijfers, andere labels.

HOE

`t("Verwachte omzet", "Chiffre d'affaires attendu")` geeft de tekst in de
ingestelde taal. De taal staat in een modulewaarde en wordt gezet met
`in_taal("fr")`. Dat is bewust globale toestand, en de reden is eerlijkheid over
het alternatief: de tekst zit verspreid over honderd plaatsen in `contract.py`,
en een taalparameter door al die functies draaien zou een refactor zijn met veel
meer kans op een fout dan dit. De contractbouw is één draad en bouwt de talen na
elkaar; `in_taal` is een contextmanager die altijd terugzet.

WAT NIET VERTAALD WORDT, EN DAT IS EEN BESLISSING

Productnamen komen uit Odoo en blijven staan zoals de bakkerij ze heeft
ingevoerd. "Pistolet" heet in het Nederlands ook pistolet, en een
machinevertaling van het assortiment zou namen produceren die op geen enkele
kassabon staan. Hetzelfde geldt voor kanaalnamen die merknamen zijn
(Deliveroo).

Getallen en bedragen blijven ook gelijk opgemaakt. Zie de noot in
`platform/lib/taal.ts`.

WAT ONVERTAALD BLIJFT, WORDT GEMELD

`ONVERTAALD` verzamelt elke tekst die in het Frans op zijn Nederlandse variant
terugvalt. De contractbouw drukt die lijst af. Dat is dezelfde gedachte als
harde regel 8, toegepast op onszelf: een half vertaald scherm is geen ramp, maar
stil half vertaald wél — dan denkt iedereen dat het klaar is.
"""

from __future__ import annotations

from contextlib import contextmanager

TALEN = ("nl", "fr")
STANDAARDTAAL = "nl"

_huidig: str = STANDAARDTAAL

#: Teksten die in het Frans niet aangeleverd zijn. Verzameld tijdens de bouw,
#: afgedrukt door contract_bouw.py. Set, want dezelfde tekst komt vaak terug.
ONVERTAALD: set[str] = set()


def huidige_taal() -> str:
    return _huidig


def is_frans() -> bool:
    return _huidig == "fr"


@contextmanager
def in_taal(taal: str):
    """Bouw binnen dit blok in `taal`. Zet altijd terug, ook bij een fout."""
    if taal not in TALEN:
        raise ValueError(f"Onbekende taal {taal!r}; keuze uit {TALEN}.")
    global _huidig
    vorige, _huidig = _huidig, taal
    try:
        yield
    finally:
        _huidig = vorige


def t(nl: str, fr: str | None = None) -> str:
    """De tekst in de ingestelde taal.

    Zonder Franse variant valt de tekst terug op het Nederlands en komt hij in
    `ONVERTAALD`. Dat is met opzet geen fout: een ontbrekende vertaling mag de
    cijfers niet blokkeren. Ze mag alleen niet onzichtbaar zijn.
    """
    if _huidig == "nl":
        return nl
    if fr is None:
        ONVERTAALD.add(nl)
        return nl
    return fr


# --- de gesloten verzamelingen: datums, maanden, weekdagen ------------------
#
# Deze horen niet in een woordenboek van losse teksten maar in tabellen, want
# ze worden per index opgezocht en niet per tekst.

MAANDEN_VOL = {
    "nl": ["januari", "februari", "maart", "april", "mei", "juni", "juli",
           "augustus", "september", "oktober", "november", "december"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"],
}

MAANDEN_KORT = {
    "nl": ["jan", "feb", "mrt", "apr", "mei", "jun",
           "jul", "aug", "sep", "okt", "nov", "dec"],
    "fr": ["janv", "févr", "mars", "avr", "mai", "juin",
           "juil", "août", "sept", "oct", "nov", "déc"],
}

WEEKDAGEN = {
    "nl": ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag",
           "zaterdag", "zondag"],
    "fr": ["lundi", "mardi", "mercredi", "jeudi", "vendredi",
           "samedi", "dimanche"],
}

WEEKDAGEN_KORT = {
    "nl": ["ma", "di", "wo", "do", "vr", "za", "zo"],
    "fr": ["lu", "ma", "me", "je", "ve", "sa", "di"],
}


def maand_vol(nummer: int) -> str:
    """1-12 -> maandnaam in de ingestelde taal."""
    return MAANDEN_VOL[_huidig][nummer - 1]


def maand_kort(nummer: int) -> str:
    return MAANDEN_KORT[_huidig][nummer - 1]


def weekdag(index: int) -> str:
    """0 = maandag, zoals pandas `dayofweek`."""
    return WEEKDAGEN[_huidig][index]


def weekdag_kort(index: int) -> str:
    return WEEKDAGEN_KORT[_huidig][index]


def dagnummer(dag: int) -> str:
    """De dag van de maand als tekst: '1er' in het Frans, anders het getal.

    Het Frans schrijft alleen de eerste van de maand als rangtelwoord
    ("le 1er janvier, le 2 janvier"); het Nederlands nooit. Eén hulpfunctie
    in plaats van drie losse f-strings, zodat de regel maar op één plek staat.
    """
    if _huidig == "fr" and dag == 1:
        return "1er"
    return str(dag)


# --- getallen in lopende tekst ----------------------------------------------


def procent_tekst(fractie: float, decimalen: int = 1) -> str:
    """Een percentage in proza: 0.078 -> '7,8 %'. In beide talen gelijk.

    Komma als decimaalteken en een gewone spatie vóór het procentteken —
    exact de notatie van `platform/lib/format.ts` (procent), zodat een
    percentage in een volzin er hetzelfde uitziet als in een tabelcel.

    Dit is met opzet de enige plek waar een percentage tekst wordt. Tot
    17 augustus 2026 hadden contract.py, briefing.py en kwaliteit.py elk hun
    eigen kopie zonder spatie, en toonde het scherm dus "7,8%" naast "8,1 %".
    """
    return f"{fractie * 100:.{decimalen}f}".replace(".", ",") + " %"


#: De kanalen. Merknamen blijven staan; alleen de gewone woorden gaan mee.
KANAALNAMEN = {
    "winkel": {"nl": "Winkel", "fr": "Magasin"},
    "deliveroo": {"nl": "Deliveroo", "fr": "Deliveroo"},
    "overig": {"nl": "Overig", "fr": "Autres"},
}


def kanaalnaam(kanaal: str) -> str:
    tabel = KANAALNAMEN.get(kanaal)
    if tabel is None:
        return kanaal
    return tabel[_huidig]
