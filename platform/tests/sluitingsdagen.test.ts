import assert from "node:assert/strict";
import { test } from "node:test";

import {
  MAX_PERIODE_DAGEN,
  REDEN_MAX,
  groepeerPeriodes,
  valideerSluitingen,
  voegSamen,
  type DagRij,
} from "../lib/sluitingsdagen";

/**
 * De eerste poort van het sluitingsformulier, zelfde opzet als
 * tests/kostenmodel.test.ts: fouten zijn sleutels met invulwaarden (het
 * formulier vertaalt), en wat de poort doorlaat is exact de rijvorm die de
 * rpc van migratie 012 verwacht.
 */

const GEEN_REGEL = { weekdag: "", vanaf: "", tot: "" };

test("een kandidaat met open of dicht wordt een feestdag-rij met de naam als reden", () => {
  const uit = valideerSluitingen(
    [
      { datum: "2026-12-25", naam: "Kerstmis", toestand: "dicht" },
      { datum: "2026-07-21", naam: "Nationale feestdag", toestand: "open" },
    ],
    [],
    GEEN_REGEL,
  );
  assert.deepEqual(uit.fouten, []);
  assert.deepEqual(uit.dagen, [
    // De naam van de feestdag reist mee als reden: de prognose en het scherm
    // hoeven de kandidatenlijst dan niet opnieuw op te zoeken.
    {
      datum: "2026-07-21",
      toestand: "open",
      reden: "Nationale feestdag",
      bron: "feestdag",
    },
    { datum: "2026-12-25", toestand: "dicht", reden: "Kerstmis", bron: "feestdag" },
  ]);
});

test("onbekend en onbekende toestandwoorden zijn geen uitspraak, dus geen rij", () => {
  const uit = valideerSluitingen(
    [
      { datum: "2026-12-25", naam: "Kerstmis", toestand: "onbekend" },
      { datum: "2026-07-21", naam: "Nationale feestdag", toestand: "misschien" },
    ],
    [],
    GEEN_REGEL,
  );
  // Onbekend ís het ontbreken van een rij — geen fout, geen stille "dicht".
  assert.deepEqual(uit.fouten, []);
  assert.deepEqual(uit.dagen, []);
});

test("een periode wordt uitgerold naar losse dagen met bron periode", () => {
  const uit = valideerSluitingen(
    [],
    [{ van: "2026-08-17", tot: "2026-08-19", reden: "Jaarlijkse sluiting" }],
    GEEN_REGEL,
  );
  assert.deepEqual(uit.fouten, []);
  assert.deepEqual(uit.dagen, [
    {
      datum: "2026-08-17",
      toestand: "dicht",
      reden: "Jaarlijkse sluiting",
      bron: "periode",
    },
    {
      datum: "2026-08-18",
      toestand: "dicht",
      reden: "Jaarlijkse sluiting",
      bron: "periode",
    },
    {
      datum: "2026-08-19",
      toestand: "dicht",
      reden: "Jaarlijkse sluiting",
      bron: "periode",
    },
  ]);
});

test("een periode zonder tot is één dag", () => {
  const uit = valideerSluitingen(
    [],
    [{ van: "2026-11-02", tot: "", reden: "Verbouwing" }],
    GEEN_REGEL,
  );
  assert.deepEqual(uit.fouten, []);
  assert.equal(uit.dagen.length, 1);
  assert.equal(uit.dagen[0].datum, "2026-11-02");
  assert.equal(uit.dagen[0].bron, "periode");
});

test("een volledig lege periode-rij wordt stil overgeslagen", () => {
  const uit = valideerSluitingen(
    [],
    [{ van: "", tot: "", reden: "" }],
    GEEN_REGEL,
  );
  // Het formulier toont altijd één lege invoerrij; die is geen invoer.
  assert.deepEqual(uit.fouten, []);
  assert.deepEqual(uit.dagen, []);
});

test("tot vóór van is een fout met beide datums erin", () => {
  const uit = valideerSluitingen(
    [],
    [{ van: "2026-08-19", tot: "2026-08-17", reden: "" }],
    GEEN_REGEL,
  );
  assert.equal(uit.fouten.length, 1);
  assert.equal(uit.fouten[0].sleutel, "sluit.totVoorVan");
  assert.deepEqual(uit.fouten[0].waarden, {
    van: "2026-08-19",
    tot: "2026-08-17",
  });
  assert.deepEqual(uit.dagen, []);
});

test("een ongeldige datum is een fout, ook als ze er bijna uitziet als een", () => {
  const uit = valideerSluitingen(
    [],
    [{ van: "2026-02-30", tot: "", reden: "" }],
    GEEN_REGEL,
  );
  // 30 februari haalt de regex maar bestaat niet; Date.parse zou hem stil
  // naar maart schuiven, en dat is precies wat geldigeDatum tegenhoudt.
  assert.equal(uit.fouten.length, 1);
  assert.equal(uit.fouten[0].sleutel, "sluit.datumOngeldig");
  assert.equal(uit.fouten[0].waarden.datum, "2026-02-30");
});

test("een reden langer dan het maximum is een fout, geen stille afkap", () => {
  const uit = valideerSluitingen(
    [],
    [{ van: "2026-08-17", tot: "", reden: "x".repeat(REDEN_MAX + 1) }],
    GEEN_REGEL,
  );
  assert.equal(uit.fouten.length, 1);
  assert.equal(uit.fouten[0].sleutel, "sluit.redenTeLang");
  assert.equal(uit.fouten[0].waarden.max, String(REDEN_MAX));
  assert.deepEqual(uit.dagen, []);
});

test("een periode langer dan het maximum aantal dagen is een fout", () => {
  // 1 januari t/m 1 mei 2026 is 121 dagen, één over de grens.
  const uit = valideerSluitingen(
    [],
    [{ van: "2026-01-01", tot: "2026-05-01", reden: "" }],
    GEEN_REGEL,
  );
  assert.equal(uit.fouten.length, 1);
  assert.equal(uit.fouten[0].sleutel, "sluit.periodeTeLang");
  assert.deepEqual(uit.fouten[0].waarden, {
    van: "2026-01-01",
    tot: "2026-05-01",
    dagen: "121",
    max: String(MAX_PERIODE_DAGEN),
  });
  assert.deepEqual(uit.dagen, []);
});

test("een periode over een bevestigd-open feestdag is een echte tegenspraak", () => {
  const uit = valideerSluitingen(
    [{ datum: "2026-07-21", naam: "Nationale feestdag", toestand: "open" }],
    [{ van: "2026-07-20", tot: "2026-07-22", reden: "Sluiting" }],
    GEEN_REGEL,
  );
  assert.equal(uit.fouten.length, 1);
  assert.equal(uit.fouten[0].sleutel, "sluit.openDichtConflict");
  assert.equal(uit.fouten[0].waarden.datum, "2026-07-21");
  // De niet-botsende dagen van de periode staan er wél; de open feestdag
  // blijft open — de beheerder moet de tegenspraak zelf oplossen.
  assert.deepEqual(
    uit.dagen.map((d) => `${d.datum}:${d.toestand}:${d.bron}`),
    [
      "2026-07-20:dicht:periode",
      "2026-07-21:open:feestdag",
      "2026-07-22:dicht:periode",
    ],
  );
});

test("een periode over een bevestigd-dichte feestdag is geen fout en de feestdag wint", () => {
  const uit = valideerSluitingen(
    [{ datum: "2026-12-25", naam: "Kerstmis", toestand: "dicht" }],
    [{ van: "2026-12-24", tot: "2026-12-26", reden: "Kerstsluiting" }],
    GEEN_REGEL,
  );
  // Twee invoeren zeggen hetzelfde; de feestdag draagt de naam als reden.
  assert.deepEqual(uit.fouten, []);
  const kerst = uit.dagen.find((d) => d.datum === "2026-12-25");
  assert.deepEqual(kerst, {
    datum: "2026-12-25",
    toestand: "dicht",
    reden: "Kerstmis",
    bron: "feestdag",
  });
  assert.equal(uit.dagen.length, 3);
});

test("een lege weekdag is geen regel, geen fout", () => {
  const uit = valideerSluitingen([], [], {
    weekdag: "",
    vanaf: "2026-09-01",
    tot: "",
  });
  assert.deepEqual(uit.fouten, []);
  assert.deepEqual(uit.regels, []);
});

test("een geldige regel wordt een regelrij, met tot null wanneer leeg", () => {
  const uit = valideerSluitingen([], [], {
    weekdag: "0",
    vanaf: "2026-09-01",
    tot: "",
  });
  assert.deepEqual(uit.fouten, []);
  assert.deepEqual(uit.regels, [
    { weekdag: 0, vanaf: "2026-09-01", tot: null, reden: "" },
  ]);
});

test("een regel zonder vanaf is een fout: een regel zonder begin bestaat niet", () => {
  const uit = valideerSluitingen([], [], {
    weekdag: "1",
    vanaf: "",
    tot: "",
  });
  assert.equal(uit.fouten.length, 1);
  assert.equal(uit.fouten[0].sleutel, "sluit.vanafOntbreekt");
  assert.deepEqual(uit.regels, []);
});

test("weekdag 7 is ongeldig: de week loopt van 0 (maandag) tot 6", () => {
  const uit = valideerSluitingen([], [], {
    weekdag: "7",
    vanaf: "2026-09-01",
    tot: "",
  });
  assert.equal(uit.fouten.length, 1);
  assert.equal(uit.fouten[0].sleutel, "sluit.weekdagOngeldig");
  assert.equal(uit.fouten[0].waarden.weekdag, "7");
  assert.deepEqual(uit.regels, []);
});

test("de uitvoer is gesorteerd op datum, hoe de invoer ook binnenkwam", () => {
  const uit = valideerSluitingen(
    [{ datum: "2026-12-25", naam: "Kerstmis", toestand: "dicht" }],
    [
      { van: "2026-08-17", tot: "", reden: "b" },
      { van: "2026-01-01", tot: "", reden: "a" },
    ],
    GEEN_REGEL,
  );
  assert.deepEqual(
    uit.dagen.map((d) => d.datum),
    ["2026-01-01", "2026-08-17", "2026-12-25"],
  );
});

// -- voegSamen: de samenvoeging met de bewaarde stand ------------------------

const dag = (
  datum: string,
  bron: DagRij["bron"],
  toestand: DagRij["toestand"] = "dicht",
  reden = "",
): DagRij => ({ datum, toestand, reden, bron });

test("bewaarde dagen buiten de kandidaten en zonder bron periode blijven staan", () => {
  const uit = voegSamen(
    [dag("2025-12-25", "feestdag", "dicht", "Kerstmis"), dag("2025-08-01", "bestand")],
    new Set(["2026-12-25"]),
    [dag("2026-12-25", "feestdag", "dicht", "Kerstmis")],
  );
  // De feestdag van vorig jaar en de eenmalige bestandsovername zijn geen
  // formulierinvoer; zonder dit behoud zou elke opslag de geschiedenis wissen.
  assert.deepEqual(
    uit.map((d) => d.datum),
    ["2025-08-01", "2025-12-25", "2026-12-25"],
  );
});

test("bewaarde dagen met bron periode worden vervangen door de nieuwe invoer", () => {
  const uit = voegSamen(
    [dag("2026-08-17", "periode"), dag("2026-08-18", "periode")],
    new Set(),
    [dag("2026-08-20", "periode")],
  );
  // Het formulier toont álle periodes; wat de beheerder schrapte, moet ook
  // uit de database verdwijnen.
  assert.deepEqual(
    uit.map((d) => d.datum),
    ["2026-08-20"],
  );
});

test("kandidaat-datums worden vervangen, ook wanneer de nieuwe invoer ze weglaat", () => {
  const uit = voegSamen(
    [dag("2026-07-21", "feestdag", "open", "Nationale feestdag")],
    new Set(["2026-07-21"]),
    [],
  );
  // De beheerder zette de kandidaat terug op onbekend: de uitspraak vervalt.
  assert.deepEqual(uit, []);
});

test("bij een botsende datum wint de nieuwe invoer", () => {
  const uit = voegSamen(
    [dag("2026-11-02", "bestand", "dicht", "oude reden")],
    new Set(),
    [dag("2026-11-02", "periode", "dicht", "Verbouwing")],
  );
  assert.equal(uit.length, 1);
  assert.equal(uit[0].reden, "Verbouwing");
  assert.equal(uit[0].bron, "periode");
});

// -- groepeerPeriodes: losse dagen terug naar mensentaal ---------------------

test("aaneengesloten dagen met dezelfde reden worden één periode", () => {
  const uit = groepeerPeriodes([
    { datum: "2026-08-17", reden: "Jaarlijkse sluiting" },
    { datum: "2026-08-18", reden: "Jaarlijkse sluiting" },
    { datum: "2026-08-19", reden: "Jaarlijkse sluiting" },
  ]);
  assert.deepEqual(uit, [
    { van: "2026-08-17", tot: "2026-08-19", reden: "Jaarlijkse sluiting" },
  ]);
});

test("een gat of een andere reden breekt de reeks", () => {
  const uit = groepeerPeriodes([
    { datum: "2026-08-17", reden: "a" },
    { datum: "2026-08-18", reden: "b" }, // andere reden
    { datum: "2026-08-20", reden: "b" }, // gat van één dag
  ]);
  assert.deepEqual(uit, [
    { van: "2026-08-17", tot: "2026-08-17", reden: "a" },
    { van: "2026-08-18", tot: "2026-08-18", reden: "b" },
    { van: "2026-08-20", tot: "2026-08-20", reden: "b" },
  ]);
});

test("lege invoer is een lege lijst, geen fout", () => {
  assert.deepEqual(groepeerPeriodes([]), []);
});

test("ongesorteerde invoer wordt gesorteerd voor het groeperen", () => {
  const uit = groepeerPeriodes([
    { datum: "2026-08-19", reden: "a" },
    { datum: "2026-08-17", reden: "a" },
    { datum: "2026-08-18", reden: "a" },
  ]);
  assert.deepEqual(uit, [{ van: "2026-08-17", tot: "2026-08-19", reden: "a" }]);
});
