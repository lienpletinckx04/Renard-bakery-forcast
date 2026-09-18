import assert from "node:assert/strict";
import { test } from "node:test";

import { MAX_CRITERIA, valideerKostenmodel } from "../lib/kostenmodel";

const GRONDSTOFFEN = { naam: "Grondstoffen", omschrijving: "Foodcost." };
const VERLIES = { naam: "Verlies", omschrijving: "" };

test("komma en punt zijn allebei geldig, opgeslagen wordt de punt", () => {
  const uit = valideerKostenmodel(
    [GRONDSTOFFEN, VERLIES],
    [
      { groep: "Brood", criterium: "Grondstoffen", waarde: "30,5" },
      { groep: "Brood", criterium: "Verlies", waarde: "5.25" },
    ],
  );
  assert.deepEqual(uit.fouten, []);
  assert.deepEqual(uit.waarden, {
    Brood: { Grondstoffen: "30.5", Verlies: "5.25" },
  });
});

test("een leeg veld is geen nul maar geen invoer", () => {
  const uit = valideerKostenmodel(
    [GRONDSTOFFEN],
    [
      { groep: "Brood", criterium: "Grondstoffen", waarde: "  " },
      { groep: "Lunch", criterium: "Grondstoffen", waarde: "40" },
    ],
  );
  assert.deepEqual(uit.fouten, []);
  assert.deepEqual(uit.waarden, { Lunch: { Grondstoffen: "40" } });
});

test("onzin en buiten bereik zijn fouten met groep én criterium erin", () => {
  const uit = valideerKostenmodel(
    [GRONDSTOFFEN],
    [
      { groep: "Brood", criterium: "Grondstoffen", waarde: "veel" },
      { groep: "Lunch", criterium: "Grondstoffen", waarde: "101" },
      { groep: "Dranken", criterium: "Grondstoffen", waarde: "-3" },
    ],
  );
  assert.deepEqual(uit.waarden, {});
  assert.equal(uit.fouten.length, 3);
  // Fouten zijn sleutels met invulwaarden (het formulier vertaalt); de groep
  // en het criterium reizen mee als waarden, zodat de zin ze kan noemen.
  assert.equal(uit.fouten[0].sleutel, "kosten.geenPercentage");
  assert.equal(uit.fouten[0].waarden.groep, "Brood");
  assert.equal(uit.fouten[0].waarden.criterium, "Grondstoffen");
  assert.equal(uit.fouten[1].sleutel, "kosten.buitenBereik");
  assert.equal(uit.fouten[1].waarden.groep, "Lunch");
  // "-3" haalt de vormcontrole niet eens: ook een fout, geen stille nul.
  assert.equal(uit.fouten[2].sleutel, "kosten.geenPercentage");
  assert.equal(uit.fouten[2].waarden.groep, "Dranken");
});

test("hoogstens twee decimalen, meer is een fout en geen stille afronding", () => {
  const uit = valideerKostenmodel(
    [GRONDSTOFFEN],
    [{ groep: "Brood", criterium: "Grondstoffen", waarde: "30.505" }],
  );
  assert.equal(uit.fouten.length, 1);
  assert.equal(uit.fouten[0].sleutel, "kosten.geenPercentage");
  assert.equal(uit.fouten[0].waarden.waarde, "30.505");
});

test("een leeggelaten criteriumnaam is geen criterium, geen fout", () => {
  const uit = valideerKostenmodel(
    [{ naam: "  ", omschrijving: "" }, GRONDSTOFFEN],
    [],
  );
  assert.deepEqual(uit.fouten, []);
  assert.deepEqual(
    uit.criteria.map((c) => c.naam),
    ["Grondstoffen"],
  );
});

test("dubbele criteriumnamen zijn een fout, ook met andere hoofdletters", () => {
  const uit = valideerKostenmodel(
    [GRONDSTOFFEN, { naam: "grondstoffen", omschrijving: "" }],
    [],
  );
  assert.equal(uit.fouten.length, 1);
  assert.equal(uit.fouten[0].sleutel, "kosten.dubbelCriterium");
});

test("meer dan het maximum aantal criteria is een fout", () => {
  const veel = Array.from({ length: MAX_CRITERIA + 1 }, (_, i) => ({
    naam: `C${i}`,
    omschrijving: "",
  }));
  const uit = valideerKostenmodel(veel, []);
  assert.equal(uit.fouten.length, 1);
  assert.equal(uit.fouten[0].sleutel, "kosten.teVeelCriteria");
});

test("een waarde voor een geschrapt criterium verdwijnt bewust stil", () => {
  const uit = valideerKostenmodel(
    [GRONDSTOFFEN],
    [{ groep: "Brood", criterium: "Verpakking", waarde: "3" }],
  );
  assert.deepEqual(uit.fouten, []);
  assert.deepEqual(uit.waarden, {});
});

test("criteriumnamen worden genormaliseerd op witruimte", () => {
  const uit = valideerKostenmodel(
    [{ naam: "  Verlies   en  verspilling ", omschrijving: "" }],
    [{ groep: "Brood", criterium: "Verlies en verspilling", waarde: "5" }],
  );
  assert.deepEqual(uit.fouten, []);
  assert.deepEqual(uit.waarden, { Brood: { "Verlies en verspilling": "5" } });
});
