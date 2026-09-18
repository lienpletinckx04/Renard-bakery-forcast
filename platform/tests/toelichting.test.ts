import assert from "node:assert/strict";
import { test } from "node:test";

import type { Onbeschikbaar } from "../lib/contract";
import { reden, veldLabel, verdeelPrognoseRegels } from "../lib/toelichting";

const regel = (veld: string): Onbeschikbaar => ({ veld, reden: `reden ${veld}` });

const CONTRACT: Onbeschikbaar[] = [
  regel("prognose.startpunt"),
  regel("prognose.sluitingsdagen"),
  regel("prognose.weektotaal"),
  regel("prognose.nauwkeurigheid"),
];

function alleVelden(v: ReturnType<typeof verdeelPrognoseRegels>): string[] {
  return [...v.kop, ...v.tegel, ...v.dagen, ...v.trackrecord, ...v.overig].map(
    (r) => r.veld,
  );
}

test("geen enkele reden verdwijnt van het scherm", () => {
  const v = verdeelPrognoseRegels(CONTRACT);
  assert.deepEqual(
    [...alleVelden(v)].sort(),
    CONTRACT.map((r) => r.veld).sort(),
  );
});

test("een onbekend veld belandt in overig en blijft dus zichtbaar", () => {
  // Dit is het geval waar het om gaat: de berekeningslaag verzint morgen een
  // nieuwe reden en die mag niet stil in de JSON blijven zitten.
  const met = [...CONTRACT, regel("prognose.iets.nieuws"), regel("bron.marktkraam")];
  const v = verdeelPrognoseRegels(met);
  assert.deepEqual(
    v.overig.map((r) => r.veld),
    ["prognose.iets.nieuws", "bron.marktkraam"],
  );
  assert.equal(alleVelden(v).length, met.length);
});

test("het meetgat staat bovenaan, niet onderaan", () => {
  const v = verdeelPrognoseRegels([...CONTRACT, regel("prognose.meetgat")]);
  assert.ok(v.kop.some((r) => r.veld === "prognose.meetgat"));
  assert.ok(!v.overig.some((r) => r.veld === "prognose.meetgat"));
});

test("de nauwkeurigheid uit de backtest staat vooraan, en het weektotaal bij zijn tegel", () => {
  const v = verdeelPrognoseRegels(CONTRACT);
  assert.equal(v.kop[0].veld, "prognose.nauwkeurigheid");
  assert.deepEqual(
    v.kop.map((r) => r.veld),
    ["prognose.nauwkeurigheid", "prognose.startpunt"],
  );
  assert.deepEqual(
    v.tegel.map((r) => r.veld),
    ["prognose.weektotaal"],
  );
  assert.deepEqual(
    v.dagen.map((r) => r.veld),
    ["prognose.sluitingsdagen"],
  );
  assert.deepEqual(v.overig, []);
});

test("de indeling hangt niet af van de volgorde in de JSON", () => {
  const omgekeerd = [...CONTRACT].reverse();
  assert.deepEqual(
    verdeelPrognoseRegels(omgekeerd).kop.map((r) => r.veld),
    verdeelPrognoseRegels(CONTRACT).kop.map((r) => r.veld),
  );
});

test("de reden voor een ontbrekend trackrecord hoort bij zijn vak, niet onderaan", () => {
  const v = verdeelPrognoseRegels([...CONTRACT, regel("prognose.trackrecord")]);
  assert.deepEqual(
    v.trackrecord.map((r) => r.veld),
    ["prognose.trackrecord"],
  );
  assert.ok(!v.overig.some((r) => r.veld === "prognose.trackrecord"));
});

test("een leeg contract levert lege groepen, geen undefined", () => {
  const v = verdeelPrognoseRegels([]);
  assert.deepEqual(v, {
    kop: [],
    tegel: [],
    dagen: [],
    trackrecord: [],
    overig: [],
  });
});

test("reden geeft de tekst uit het contract, of null als die er niet is", () => {
  assert.equal(reden(CONTRACT, "prognose.weektotaal"), "reden prognose.weektotaal");
  assert.equal(reden(CONTRACT, "prognose.bestaat.niet"), null);
});

/* --- veldLabel: geen contractsleutel op een scherm (O12) ----------------- */

test("een bekende sleutel krijgt zijn eigen label", () => {
  assert.equal(veldLabel("prognose.startpunt", "nl"), "Startpunt van de prognose");
  assert.equal(veldLabel("weken.gesloten", "nl"), "Weken zonder meting");
  // "prognose.geplande_sluiting" viel tot 17 aug op het vangnet en stond als
  // "Prévision : geplande sluiting" op het Franse scherm.
  assert.equal(veldLabel("prognose.geplande_sluiting", "nl"), "Geplande sluiting");
  assert.equal(veldLabel("prognose.geplande_sluiting", "fr"), "Fermeture prévue");
});

test("een sleutel met een staart uit de data houdt die staart", () => {
  // "weekdagprofiel.<dag>" is niet vooraf op te schrijven: de staart komt uit
  // de data. Het voorvoegsel wordt vertaald, de rest blijft staan.
  assert.equal(veldLabel("weekdagprofiel.zondag", "nl"), "Weekdagprofiel: zondag");
  assert.equal(veldLabel("kanaal.nieuw_kanaal", "fr"), "Canal : nieuw kanaal");
});

test("de vier kerncijfers dragen een label, niet hun machinenaam", () => {
  // Sinds 19 aug 2026 is `onbeschikbaar[].veld` voor een kerncijfer een
  // machinesleutel en niet meer het (tweetalige) label. Die vier sleutels
  // moeten hier voluit staan: zonder eigen label maakt het voorvoegselvangnet
  // er "Kerncijfer: Omzet 7" van, en dat is een variabelenaam op het scherm.
  const paren: [string, string, string][] = [
    ["kerncijfer.omzet_7", "Omzet laatste 7 open dagen",
     "Chiffre d'affaires, 7 derniers jours d'ouverture"],
    ["kerncijfer.omzet_30", "Omzet laatste 30 open dagen",
     "Chiffre d'affaires, 30 derniers jours d'ouverture"],
    ["kerncijfer.stuks_7", "Stuks laatste 7 open dagen",
     "Unités, 7 derniers jours d'ouverture"],
    ["kerncijfer.gemiddelde_dagomzet", "Gemiddelde dagomzet",
     "Chiffre d'affaires moyen par jour"],
  ];
  for (const [sleutel, nl, fr] of paren) {
    assert.equal(veldLabel(sleutel, "nl"), nl);
    assert.equal(veldLabel(sleutel, "fr"), fr);
    // En het label mag geen spoor van de machinenaam dragen.
    assert.ok(!veldLabel(sleutel, "nl").includes("_"));
  }
});

test("een onbekende sleutel wordt leesbaar en verdwijnt niet", () => {
  assert.equal(veldLabel("nieuw_iets.van_later", "nl"), "Nieuw iets van later");
});

test("de wachters van het standscherm dragen een Nederlands label", () => {
  // De vijf namen uit stand.json. Ze stonden ruw op /instellingen; dat is het
  // gat dat O12 op dat ene scherm oversloeg.
  assert.equal(veldLabel("gat_in_de_reeks", "nl"), "Gat in de reeks open dagen");
  assert.equal(veldLabel("dubbele_sleutels", "nl"), "Dubbele sleutels");
  assert.equal(veldLabel("negatieve_waarden", "nl"), "Negatieve omzet of aantallen");
  assert.equal(veldLabel("kalenderdekking", "nl"), "Dekking van de kalender");
  assert.equal(veldLabel("drempelrand", "nl"), "Dagen dicht bij de drempel");
});

test("de bronnen van het standscherm dragen een net label in beide talen", () => {
  // De bronnamen uit stand.json (bronstanden[].bron). De sleutel blijft
  // in het contract; alleen de weergave verandert.
  assert.equal(veldLabel("odoo-kassa", "nl"), "Odoo-kassa's");
  assert.equal(veldLabel("odoo-kassa", "fr"), "Caisses Odoo");
  assert.equal(veldLabel("deliveroo", "nl"), "Deliveroo");
  assert.equal(veldLabel("deliveroo", "fr"), "Deliveroo");
});

test("de bronnamen in de envelope, in de voettekst, dragen hetzelfde label", () => {
  // De voettekst toont `bron[]` uit de envelope; daar staat "winkel" naast
  // "deliveroo". De envelope-sleutel "winkel" en de bronstand "odoo-kassa" zijn
  // dezelfde bron — de Odoo-kassa's — dus dragen voettekst en Instellingen
  // hetzelfde label. Eén bron, één naam, in beide talen.
  assert.equal(veldLabel("winkel", "nl"), "Odoo-kassa's");
  assert.equal(veldLabel("winkel", "fr"), "Caisses Odoo");
});

test("een bron die er later bijkomt, wordt leesbaar en verdwijnt niet", () => {
  // Het vangnet, niet de tabel: een nieuwe bron uit de berekeningslaag mag
  // nooit als kale sleutel op het scherm staan.
  assert.equal(veldLabel("uber_eats", "nl"), "Uber eats");
});

test("een wachter die er later bijkomt, wordt leesbaar zonder codewijziging", () => {
  // Er komen wachters op bon- en uurniveau. Hun namen staan niet in de tabel
  // en horen daar ook niet te hoeven staan: het vangnet is de vangrail.
  assert.equal(
    veldLabel("bonnen_zonder_regels", "nl"),
    "Bonnen zonder regels",
  );
  assert.equal(
    veldLabel("verkoop_buiten_de_openingsuren", "nl"),
    "Verkoop buiten de openingsuren",
  );
});

test("elk bekend label bestaat in beide talen en verschilt waar het hoort", () => {
  // De labeltabel is tweetalig sinds 17 aug: een Frans scherm droeg tot dan
  // Nederlandse veldlabels boven vertaalde redenen. Merknamen ("Marge
  // Deliveroo") mogen gelijk blijven; een zin als "Weken zonder meting" niet.
  assert.equal(veldLabel("prognose.startpunt", "fr"), "Point de départ de la prévision");
  assert.equal(veldLabel("weken.gesloten", "fr"), "Semaines sans mesure");
  assert.equal(veldLabel("gat_in_de_reeks", "fr"), "Trou dans la série des jours d'ouverture");
  // Het voorvoegselpad vertaalt mee; de staart uit de data blijft staan.
  assert.equal(
    veldLabel("weekdagprofiel.zondag", "fr"),
    "Profil par jour de la semaine : zondag",
  );
});

test("geen enkel label draagt nog een punt of een liggend streepje", () => {
  // De eigenschap waar het om gaat: wat er ook uit de berekeningslaag komt,
  // er verschijnt geen variabelenaam op het scherm.
  const sleutels = [
    "prognose.nauwkeurigheid",
    "bonritme.ontbinding",
    "afwijkende_dagen",
    "marge_per_kanaal",
    "iets.wat_nog_niet_bestaat",
    // Verzonnen wachternamen: snake_case, nu nog onbekend, straks echt.
    "bon_zonder_regels",
    "uurpiek_buiten_de_openingsuren",
    "mand_zonder_uitbetaling",
    // Een onbekende staart achter een bekend voorvoegsel: dit pad liet de
    // streepjes vroeger ongemoeid door.
    "kanaal.nieuw_kanaal",
    "prognose.wachter_op_bonniveau",
    // Rafelranden: dubbele scheidingstekens en een staart die niets overhoudt.
    "bonritme.",
    "iets__met__dubbele__streepjes",
  ];
  for (const sleutel of sleutels) {
    const label = veldLabel(sleutel, "nl");
    assert.ok(!/[._]/.test(label), `${sleutel} -> ${label}`);
    assert.ok(label.trim().length > 0, `${sleutel} levert een leeg label`);
  }
});
