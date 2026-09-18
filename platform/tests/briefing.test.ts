import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { allesGedeeld, bedragTekst, opVolgorde } from "../lib/briefing";
import type { Briefing, BriefingPunt } from "../lib/contract";
import { aantal, euro, verschilProcent } from "../lib/format";

/**
 * De briefing bovenaan elk scherm, in drie soorten tests:
 *
 *  1. TYPEDEKKING — de vorm die de berekeningslaag schrijft, in al haar
 *     varianten. `tsc --noEmit` bewaakt dit; de asserts eronder zijn er opdat
 *     de test ook iets uitvoert.
 *  2. DE OPMAAK — wat de component per `soort` op het scherm zet, gemeten op
 *     de functies uit format.ts die ze daarvoor gebruikt.
 *  3. DE BRONWACHT — een handvol huisstijlregels die je aan een component niet
 *     kunt aflezen door haar te draaien, maar wel aan haar bron: geen
 *     betekeniskleur, geen eigen getalopmaak, en een lege staat zonder paneel.
 *
 * WAAROM DE COMPONENT NIET GERENDERD WORDT. De testrunner van dit project is
 * `node --experimental-strip-types`, en die laadt geen .tsx: JSX is geen
 * TypeScript-type dat je kunt wegstrippen. De projectgewoonte is daarom dat
 * logica die getest moet worden in `lib/` staat en niet in een component. Deze
 * component houdt zich daaraan door bijna niets te doen — ze kiest een
 * opmaakfunctie, een lijndikte en een gewicht — maar wie later een echte
 * beslissing aan haar toevoegt, hoort die eerst naar `lib/` te verhuizen.
 */

const BRON = readFileSync(new URL("../components/Briefing.tsx", import.meta.url), "utf8");

/* ---- 1. typedekking ------------------------------------------------------ */

test("de briefingvorm compileert met alle drie de statussen", () => {
  const punten: BriefingPunt[] = [
    {
      kop: "Marge onbekend voor drie productgroepen",
      waarom: "Voor deze groepen is nog geen kostencriterium ingevuld.",
      nodig: "Lien vraagt de brutomarges op bij de bakkerij.",
      bedrag: "12480.50",
      soort: "euro",
      eenheid: null,
      richting: null,
      status: "actie",
      statuswoord: "actie",
    },
    {
      kop: "Omzet ligt onder het gebruikelijke niveau",
      waarom: "De laatste zeven open dagen liggen onder de weekdagmediaan.",
      nodig: null,
      bedrag: "-4.2",
      soort: "verschil",
      eenheid: null,
      richting: "neer",
      status: "let_op",
      statuswoord: "let op",
    },
    {
      kop: "Too Good To Go loopt zoals verwacht",
      waarom: "Het aantal pakketten blijft binnen de gemeten bandbreedte.",
      nodig: null,
      bedrag: "312",
      soort: "aantal",
      eenheid: "pakketten",
      richting: "op",
      status: "goed",
      statuswoord: "goed",
    },
  ];
  const briefing: Briefing = { punten, leeg: "Niets dat opvalt vandaag." };
  assert.equal(briefing.punten.length, 3);
  assert.equal(briefing.punten[0].status, "actie");
});

test("een punt zonder bedrag, zonder richting en zonder actie is geldig", () => {
  const punt: BriefingPunt = {
    kop: "De koppeling met Deliveroo bestaat nog niet",
    waarom: "Er is nog geen bron aangesloten.",
    nodig: null,
    bedrag: null,
    soort: null,
    eenheid: null,
    richting: null,
    status: "let_op",
    statuswoord: "let op",
  };
  assert.equal(punt.bedrag, null);
  assert.equal(punt.soort, null);
});

test("de lege briefing is een geldige briefing, met haar eigen zin", () => {
  const leeg: Briefing = { punten: [], leeg: "Niets dat opvalt vandaag." };
  assert.equal(leeg.punten.length, 0);
  assert.notEqual(leeg.leeg.trim(), "");
});

/* ---- 2. de opmaak van het bedrag ---------------------------------------- */

test("elk soort bedrag krijgt de opmaak van het scherm, uit format.ts", () => {
  assert.equal(euro("12480.50"), "€ 12.480,50");
  assert.equal(aantal("312"), "312");
  // Het teken zit in de tekst en niet alleen in de pijl: een schermlezer die
  // de pijl niet voorleest, hoort de richting nog steeds.
  assert.equal(verschilProcent("-4.2"), "−4,2 %");
  assert.equal(verschilProcent("3.1"), "+3,1 %");
});

test("een bedrag met een minteken draagt de echte minus, geen koppelteken", () => {
  assert.equal(euro("-1234.56"), "€ −1.234,56");
  assert.ok(!euro("-1234.56").includes("-"));
});

/* ---- 3. de bronwacht ----------------------------------------------------- */

test("de status draagt geen kleur: geen bordeaux, geen geel, geen paletkleur", () => {
  // Bordeaux is identiteit en nooit betekenis, en een briefingpunt is bij
  // uitstek de plek waar iemand er "belangrijk" mee zou willen zeggen.
  assert.ok(
    !/\b(?:text|bg|border|fill|stroke|decoration)-(?:bordeaux|geel)\b/.test(BRON),
    "de briefing gebruikt bordeaux of geel als drager van een status",
  );
  // En geen kleur van buiten de zes tokens, in welke vorm dan ook.
  assert.ok(
    !/\b(?:text|bg|border|fill|stroke)-(?:red|green|orange|amber|yellow|emerald|rose|lime|teal|blue)\b/.test(
      BRON,
    ),
    "de briefing gebruikt een kleur die niet in de logogids staat",
  );
});

test("het statuswoord staat als tekst in de DOM, niet alleen als vorm", () => {
  // Komt de status niet uit kleur, dan moet ze uit het woord komen — ook voor
  // wie het scherm niet ziet.
  assert.ok(BRON.includes("{punt.statuswoord}"));
  // Het woord staat binnen de kop, zodat koppennavigatie het meeneemt.
  const kop = BRON.indexOf("<h3");
  const statuswoord = BRON.indexOf("{punt.statuswoord}");
  const eindeKop = BRON.indexOf("</h3>");
  assert.ok(kop !== -1 && eindeKop !== -1);
  assert.ok(statuswoord > kop && statuswoord < eindeKop);
});

test("acties staan bovenaan, en de volgorde binnen een status blijft", () => {
  const punt = (status: BriefingPunt["status"], kop: string): BriefingPunt => ({
    kop,
    waarom: "",
    nodig: null,
    bedrag: null,
    soort: null,
    eenheid: null,
    richting: null,
    status,
    statuswoord: status,
  });
  const in_ = [
    punt("goed", "g1"),
    punt("let_op", "l1"),
    punt("actie", "a1"),
    punt("let_op", "l2"),
    punt("actie", "a2"),
  ];
  assert.deepEqual(
    opVolgorde(in_).map((p) => p.kop),
    ["a1", "a2", "l1", "l2", "g1"],
  );
  // De invoer wordt niet gemuteerd: de lijst komt uit het contract.
  assert.equal(in_[0]!.kop, "g1");
});

test("een onbekende status valt niet van het scherm maar komt in het midden", () => {
  const punt = (status: string, kop: string) =>
    ({ kop, waarom: "", nodig: null, bedrag: null, soort: null,
       richting: null, status, statuswoord: status }) as unknown as BriefingPunt;
  const uit = opVolgorde([
    punt("goed", "g"),
    punt("nieuw_soort", "n"),
    punt("actie", "a"),
  ]);
  assert.deepEqual(uit.map((p) => p.kop), ["a", "n", "g"]);
});

test("bedragTekst kiest de opmaak per soort, en verzint geen eenheid", () => {
  assert.equal(bedragTekst("12480.50", "euro"), "€ 12.480,50");
  assert.equal(bedragTekst("-4.2", "verschil"), "−4,2 %");
  assert.equal(bedragTekst("312", "aantal"), "312");
  // Zonder soort: wel het getal, geen verzonnen euroteken of procent.
  const kaal = bedragTekst("1234", null);
  assert.equal(kaal, "1.234");
  assert.ok(!kaal.includes("€") && !kaal.includes("%"));
});

test("elk cijfer gaat door format.ts, nooit door een eigen opmaak", () => {
  // De opmaak zelf woont sinds de verplaatsing in lib/briefing.ts, zodat ze
  // uitvoerbaar te toetsen is; die module leunt op format.ts en de test
  // hierboven meet dat aan de uitkomst. Wat hier telt, is dat de component
  // geen eigen opmaak náást die weg heeft.
  assert.ok(BRON.includes('from "@/lib/briefing"'));
  assert.ok(!BRON.includes("toLocaleString"));
  assert.ok(!BRON.includes("Intl.NumberFormat"));
  // Geen rekenwerk in de presentatielaag (harde regel 4).
  assert.ok(!/\bparseFloat\b|\bNumber\(/.test(BRON));
});

test("de pijl is versiering; de richting staat ook zonder haar in de tekst", () => {
  const pijl = BRON.indexOf("↓");
  const ariaVerborgen = BRON.lastIndexOf('aria-hidden="true"', pijl);
  assert.ok(pijl !== -1 && ariaVerborgen !== -1 && pijl - ariaVerborgen < 200);
});

test("de focusring wordt nergens uitgezet", () => {
  assert.ok(!BRON.includes("outline-none"));
});

test("de lege staat is geen leeg kader: geen paneel, geen kop, geen kader", () => {
  const begin = BRON.indexOf("briefing.punten.length === 0");
  const eind = BRON.indexOf("const punten =");
  assert.ok(begin !== -1 && eind > begin);
  const tak = BRON.slice(begin, eind);
  assert.ok(!tak.includes("bg-wit"), "de lege staat trekt een wit paneel op");
  assert.ok(!tak.includes("rounded-klein"), "de lege staat trekt een kader op");
  assert.ok(!tak.includes("kapitaal"), "de lege staat zet een kop in kapitalen");
  // Eén paneel in het hele bestand: dat van de gevulde staat.
  assert.equal(BRON.split("bg-wit").length - 1, 1);
});

test("de lege zin komt uit het contract en wordt niet verzonnen", () => {
  assert.ok(BRON.includes("briefing.leeg"));
  // De component zwijgt als het contract geen zin levert, in plaats van er
  // zelf een te schrijven.
  assert.ok(BRON.includes('if (zin === "") return null;'));
});

/* ---- 4. het gedeelde punt in het rapport --------------------------------- */
//
// Zie `bakkerij/briefing.BriefingPunt.gedeeld` en de regel voor `data-gedeeld`
// in globals.css. Wat hier bewaakt wordt is de keten: het contract merkt het
// punt, de component zet het haakje, de CSS gebruikt het — en één ontbrekende
// schakel is stil, want een punt te veel valt niemand op.

const CSS = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

function _punt(over: Partial<BriefingPunt> = {}): BriefingPunt {
  return {
    kop: "De bakkerij is gesloten",
    waarom: "De zaak is dicht sinds 1 augustus 2026.",
    nodig: null,
    bedrag: null,
    soort: null,
    eenheid: null,
    richting: null,
    status: "let_op",
    statuswoord: "Let op",
    ...over,
  };
}

test("een briefing met alleen gedeelde punten heet zo, een gemengde niet", () => {
  assert.equal(allesGedeeld([_punt({ gedeeld: true })]), true);
  assert.equal(
    allesGedeeld([_punt({ gedeeld: true }), _punt({ gedeeld: false })]),
    false,
  );
  // Een punt zonder het veld is een contract van vóór 19 aug 2026: niet
  // gemerkt is niet gedeeld, en dus blijft het blok gewoon staan.
  assert.equal(allesGedeeld([_punt()]), false);
});

test("een lege briefing is niet 'alles gedeeld'", () => {
  // Daar toont de component de leeg-zin, en die hoort in het rapport op elke
  // bladzijde te blijven staan: ze zegt dat er niets te melden is, en dat is
  // per scherm een eigen uitspraak.
  assert.equal(allesGedeeld([]), false);
});

test("de component zet het haakje alleen als het contract het punt merkt", () => {
  assert.ok(BRON.includes('punt.gedeeld ? { "data-gedeeld": "" }'));
  assert.ok(BRON.includes('allesGedeeld(punten) ? { "data-alles-gedeeld": "" }'));
  // Aanwezigheid, geen waarde: een attribuut dat er altijd staat, nodigt uit
  // tot een CSS-regel op de negatieve waarde — en dan hangt het gedrag van een
  // scherm af van een attribuut dat er per ongeluk niet staat.
  assert.ok(!/data-(?:alles-)?gedeeld":\s*"[^"]/.test(BRON));
});

test("de CSS verbergt het gedeelde punt alleen in het rapport, en niet in het eerste deel", () => {
  const regel = ".rapport .rapportdeel ~ .rapportdeel";
  assert.ok(CSS.includes(`${regel} [data-gedeeld]`));
  assert.ok(CSS.includes(`${regel} [data-alles-gedeeld]`));
  // De regel hangt aan .rapport: op een gewoon scherm staat elk punt er, ook
  // wanneer iemand dat scherm met Ctrl+P afdrukt.
  assert.ok(!/^\s*\[data-(?:alles-)?gedeeld\]/m.test(CSS));
  // display:none en niet visibility — anders leest een schermlezer de alinea
  // alsnog zes keer.
  const na = CSS.slice(CSS.indexOf(`${regel} [data-gedeeld]`));
  assert.ok(na.slice(0, 200).includes("display: none"));
});
