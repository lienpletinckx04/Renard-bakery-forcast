import assert from "node:assert/strict";
import { test } from "node:test";

import {
  berekenStaafas,
  HOEK,
  kortAf,
  LABELOFFSET,
  MAXTEKENS,
  TEKENBREEDTE,
  VLAK,
} from "../lib/staafas";

const cos = Math.cos((HOEK * Math.PI) / 180);
const sin = Math.sin((HOEK * Math.PI) / 180);

/** De acht productgroepen zoals ze werkelijk voorkomen, alleen hun lengtes. */
const PRODUCTGROEPEN = [7, 12, 14, 20, 24, 29, 30, 31].map((l) => "x".repeat(l));

/**
 * De meetkundige voorwaarde: een schuin label hangt rechts uitgelijnd aan het
 * midden van zijn staaf en loopt van daar naar links-onder. Het moet links
 * binnen de viewBox blijven en onderaan binnen de hoogte, want de viewBox clipt.
 */
function valtBinnenBeeld(labels: string[]) {
  const as = berekenStaafas(labels);
  const n = labels.length;
  const groepB = (VLAK.breedte - as.links - VLAK.marge.rechts) / n;
  const eersteMidden = as.links + groepB / 2;
  const getekend = Math.max(
    ...labels.map((l) => kortAf(l, as.maxTekens).length * TEKENBREEDTE),
  );
  const anker = as.hoogte - as.ondermarge + LABELOFFSET;
  return {
    as,
    linksOver: eersteMidden - getekend * cos, // moet >= 0
    onderOver: as.hoogte - (anker + getekend * sin), // moet >= 0
    getekend,
  };
}

test("lange productgroepen vallen links en onder binnen de viewBox", () => {
  const { as, linksOver, onderOver } = valtBinnenBeeld(PRODUCTGROEPEN);
  assert.equal(as.schuin, true);
  // Niet krap aan maar met speling: de labelbreedte is een schatting, en een
  // lettertype dat een halve pixel breder valt mag niets afsnijden.
  assert.ok(
    linksOver >= 4,
    `label loopt tot op ${linksOver.toFixed(1)}px van de rand`,
  );
  assert.ok(
    onderOver >= 4,
    `label loopt tot op ${onderOver.toFixed(1)}px van de onderrand`,
  );
});

test("de oude vaste marges zouden dit geval hebben afgesneden", () => {
  // Aantoonbaar: met de vroegere linkermarge van 56 en ondermarge 92 paste het
  // langste label niet. Dit is de regressie zelf, niet een cijfer uit de fix.
  const as = berekenStaafas(PRODUCTGROEPEN);
  const oudeGroepB =
    (VLAK.breedte - VLAK.marge.links - VLAK.marge.rechts) / PRODUCTGROEPEN.length;
  const oudMidden = VLAK.marge.links + oudeGroepB / 2;
  assert.ok(oudMidden - as.labelbreedte * cos < 0);
  assert.ok(as.links > VLAK.marge.links);
  assert.ok(as.ondermarge > 92);
  assert.ok(as.hoogte > VLAK.hoogte + 64);
});

test("de aangenomen labelbreedte is nooit kleiner dan wat er getekend wordt", () => {
  for (const langste of [7, 12, 31, 39, 40, 60, 200]) {
    const labels = ["kort", "x".repeat(langste)];
    const { as, getekend } = valtBinnenBeeld(labels);
    assert.ok(
      getekend <= as.labelbreedte + 0.001,
      `bij ${langste} tekens: getekend ${getekend} > aangenomen ${as.labelbreedte}`,
    );
  }
});

test("ook bij extreem lange of veel labels valt niets buiten beeld", () => {
  const gevallen: string[][] = [
    ["x".repeat(31)],
    Array.from({ length: 12 }, () => "x".repeat(31)),
    Array.from({ length: 8 }, () => "x".repeat(200)),
    ["Brood / Desembroden - dagelijks", "Patisserie / Individueel gebak"],
  ];
  for (const labels of gevallen) {
    const { linksOver, onderOver } = valtBinnenBeeld(labels);
    assert.ok(linksOver >= 4, `links buiten beeld bij ${labels.length} labels`);
    assert.ok(onderOver >= 4, `onder beeld uit bij ${labels.length} labels`);
  }
});

test("er blijft ruimte voor de staven over", () => {
  const as = berekenStaafas(Array.from({ length: 8 }, () => "x".repeat(200)));
  const vlakB = VLAK.breedte - as.links - VLAK.marge.rechts;
  assert.ok(vlakB > VLAK.breedte / 2, `tekenvlak geslonken tot ${vlakB}px`);
});

test("korte labels houden de oude, rechte maatvoering", () => {
  const as = berekenStaafas(["ma", "di", "wo", "do", "vr", "za", "zo"]);
  assert.equal(as.schuin, false);
  assert.equal(as.links, VLAK.marge.links);
  assert.equal(as.ondermarge, VLAK.marge.onder);
  assert.equal(as.hoogte, VLAK.hoogte);
});

test("een lege reeks levert de rechte maatvoering en geen deling door nul", () => {
  const as = berekenStaafas([]);
  assert.equal(as.schuin, false);
  assert.ok(Number.isFinite(as.hoogte));
  assert.ok(Number.isFinite(as.links));
});

test("afkorten gebruikt een weglatingsteken en blijft binnen de grens", () => {
  assert.equal(kortAf("Brood", MAXTEKENS), "Brood");
  const lang = "x".repeat(80);
  const kort = kortAf(lang, MAXTEKENS);
  assert.ok(kort.length <= MAXTEKENS);
  assert.ok(kort.endsWith("…"));
  assert.equal(kortAf("x".repeat(31), MAXTEKENS), "x".repeat(31));
});
