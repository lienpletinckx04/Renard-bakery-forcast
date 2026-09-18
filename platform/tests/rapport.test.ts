import assert from "node:assert/strict";
import { test } from "node:test";

import { DEEL_NAAM, kiesDelen, RAPPORT_DELEN } from "../lib/rapport";
import { SLEUTELS } from "../lib/taal";

/**
 * De keuze van rapportonderdelen komt uit een URL, en een URL is invoer van
 * buiten: hij kan leeg zijn, dubbel, in de verkeerde orde, of onzin bevatten.
 * Wat er in geen geval mag gebeuren, is dat het rapport stil iets anders wordt
 * dan gevraagd — een lezer die een leeg of half document afdrukt zonder dat het
 * document dat zegt, weet niet wat hij mist.
 */

test("zonder parameter bevat het rapport alle onderdelen", () => {
  assert.deepEqual(kiesDelen(undefined), [...RAPPORT_DELEN]);
  assert.deepEqual(kiesDelen(""), [...RAPPORT_DELEN]);
  assert.deepEqual(kiesDelen([]), [...RAPPORT_DELEN]);
});

test("vinkjes uit het formulier komen als herhaalde parameter binnen", () => {
  assert.deepEqual(kiesDelen(["kanalen", "prognose"]), ["kanalen", "prognose"]);
  assert.deepEqual(kiesDelen("marge"), ["marge"]);
});

test("een met de hand getypte kommalijst werkt ook", () => {
  assert.deepEqual(kiesDelen("kanalen,prognose"), ["kanalen", "prognose"]);
  assert.deepEqual(kiesDelen(" kanalen , prognose "), ["kanalen", "prognose"]);
  assert.deepEqual(kiesDelen(["kanalen,marge", "prognose"]), [
    "kanalen",
    "marge",
    "prognose",
  ]);
});

test("de volgorde is die van het rapport, niet die van de parameters", () => {
  // Dezelfde keuze levert altijd hetzelfde document op, ongeacht in welke orde
  // de vinkjes of de parameters staan.
  assert.deepEqual(kiesDelen(["prognose", "overzicht", "kanalen"]), [
    "overzicht",
    "kanalen",
    "prognose",
  ]);
});

test("een onderdeel dat twee keer gevraagd wordt, staat er één keer in", () => {
  assert.deepEqual(kiesDelen(["marge", "marge", "marge"]), ["marge"]);
});

test("onzin wordt genegeerd, en alleen onzin levert het hele rapport", () => {
  assert.deepEqual(kiesDelen(["kanalen", "kanaal", "../etc/passwd"]), [
    "kanalen",
  ]);
  // Niet een leeg document: dat zou een tikfout in een adres veranderen in een
  // rapport zonder cijfers, zonder dat iets dat meldt.
  assert.deepEqual(kiesDelen(["onbekend"]), [...RAPPORT_DELEN]);
  assert.deepEqual(kiesDelen("KANALEN"), [...RAPPORT_DELEN]);
});

test("elk onderdeel heeft een naam die in beide talen bestaat", () => {
  // Anders staat er in het menu of in de inhoudsopgave van het rapport een
  // sleutel in plaats van een naam, en dat valt pas op een schermafbeelding op.
  for (const deel of RAPPORT_DELEN) {
    assert.ok(
      SLEUTELS.includes(DEEL_NAAM[deel]),
      `${deel} verwijst naar een sleutel die niet in het woordenboek staat`,
    );
  }
});
