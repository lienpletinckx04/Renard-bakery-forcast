import assert from "node:assert/strict";
import { test } from "node:test";

import { datumKort, datumMetTijd } from "../lib/format";
import { datakwaliteitVoettekst, statusWoord } from "../lib/stand";
import { alsTaal, maakT, SLEUTELS, STANDAARDTAAL, TALEN } from "../lib/taal";
import { versheid } from "../lib/versheid";

test("beide talen leveren voor elke sleutel een niet-lege tekst", () => {
  // Het woordenboek is een object met vaste paren, dus een ontbrekende
  // vertaling is een typefout. Deze test vangt het andere geval: een paar
  // waarin per ongeluk een lege string staat. Tot 18 augustus was dit een
  // steekproef van drie sleutels; die bewaakte de andere ~250 niet.
  for (const taal of TALEN) {
    const t = maakT(taal);
    for (const s of SLEUTELS) {
      assert.ok(t(s).length > 0, `${taal}/${s} is leeg`);
    }
  }
});

test("de twee talen geven verschillende teksten", () => {
  assert.notEqual(maakT("nl")("nav.prognose"), maakT("fr")("nav.prognose"));
  assert.equal(maakT("nl")("nav.prognose"), "Prognose");
  assert.equal(maakT("fr")("nav.prognose"), "Prévision");
});

test("invulplaatsen worden gevuld, in beide talen", () => {
  assert.equal(
    maakT("nl")("winkel.alleen", { naam: "Elsene" }),
    "Alleen Elsene",
  );
  assert.equal(
    maakT("fr")("winkel.alleen", { naam: "Elsene" }),
    "Uniquement Elsene",
  );
});

test("een ontbrekende invulwaarde blijft zichtbaar in plaats van te verdwijnen", () => {
  // Een zichtbaar gat is te herstellen; een stil gat niet. "Alleen " zonder
  // naam zou op het scherm nergens naar wijzen.
  assert.equal(maakT("nl")("winkel.alleen", {}), "Alleen {naam}");
});

test("een onbekende taalwaarde valt terug op de standaardtaal", () => {
  // De cookie wordt in laadContract een MAPNAAM. Alles wat hier doorkomt en
  // niet "nl" of "fr" is, zou een pad kunnen kiezen.
  for (const rommel of ["", "de", "../../etc", "NL", undefined, null]) {
    assert.equal(alsTaal(rommel as string | undefined), STANDAARDTAAL);
  }
  assert.equal(alsTaal("fr"), "fr");
  assert.equal(alsTaal("nl"), "nl");
});

test("datums volgen de taal, de getalopmaak niet", () => {
  assert.equal(datumKort("2026-08-14", "nl"), "14 aug 2026");
  assert.equal(datumKort("2026-08-14", "fr"), "14 août 2026");
  assert.equal(datumMetTijd("2026-08-14T07:30:00+02:00", "fr"),
               "14 août 2026, 07:30");
});

test("zonder taal blijft alles Nederlands: geen bestaande aanroep verandert", () => {
  // Elke functie die een taal kreeg, kreeg die als LAATSTE argument met een
  // standaardwaarde. Deze test pint vast dat de oude aanroepvorm hetzelfde
  // blijft doen — dat was de voorwaarde om het Frans in te voeren zonder de
  // Nederlandse route aan te raken.
  assert.equal(datumKort("2026-08-14"), "14 aug 2026");
  assert.equal(versheid("2026-08-12T21:53:55+02:00", "2026-07-31").cijfers,
               "Cijfers tot en met 31 jul 2026");
  assert.equal(statusWoord("let_op"), "let op");
});

test("de versheid staat in beide talen", () => {
  const fr = versheid("2026-08-12T21:53:55+02:00", "2026-07-31", "fr");
  assert.equal(fr.cijfers, "Chiffres jusqu'au 31 juil 2026 inclus");
  assert.equal(fr.verwerkt, "traité le 12 août 2026, 21:53");
});

test("een onbekend meetbereik wordt in beide talen uitgesproken", () => {
  const nl = versheid("2026-08-12T21:53:55+02:00", null);
  const fr = versheid("2026-08-12T21:53:55+02:00", null, "fr");
  assert.ok(nl.cijfers.includes("onbekend"));
  assert.ok(fr.cijfers.includes("inconnue"));
});

test("de datakwaliteitsregel volgt de taal, en zwijgt bij goed", () => {
  assert.equal(datakwaliteitVoettekst("goed", maakT("nl")), null);
  assert.equal(datakwaliteitVoettekst("goed", maakT("fr")), null);
  assert.equal(datakwaliteitVoettekst("let_op", maakT("nl")),
               "Let op: datakwaliteit");
  assert.equal(datakwaliteitVoettekst("let_op", maakT("fr")),
               "Attention : qualité des données");
});

test("een onbekende status verdwijnt niet maar wordt uitgeschreven", () => {
  // Een nieuwe uitkomst uit de berekeningslaag mag nooit stil van het scherm
  // vallen, ook niet in een taal waarvoor niemand hem vertaald heeft.
  assert.equal(statusWoord("iets_nieuws", "fr"), "iets nieuws");
});
