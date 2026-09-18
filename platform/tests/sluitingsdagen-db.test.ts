import assert from "node:assert/strict";
import { test } from "node:test";

import type { DagRij, RegelRij } from "../lib/sluitingsdagen";
import { bewaarVerzoek, laadSluitingen, RPC } from "../lib/sluitingsdagen-db";

/**
 * De schrijfroute van de sluitingskalender op de gehoste omgeving, naar het
 * model van tests/kostenmodel-db.test.ts. Wat hier vastligt, valt niet met
 * het oog te controleren: dat het ÉÉN verzoek is (dus één transactie, dus
 * alles of niets), dat het naar de functie van migratie 012 gaat en niet
 * naar de tabellen, en dat de body exact de rijvorm van de rpc draagt.
 */

const OMGEVING = {
  NEXT_PUBLIC_SUPABASE_URL: "https://ref.supabase.co",
  SUPABASE_SECRET_KEY: "sb_secret_x",
};

const DAGEN: DagRij[] = [
  { datum: "2026-12-25", toestand: "dicht", reden: "Kerstmis", bron: "feestdag" },
  {
    datum: "2026-08-17",
    toestand: "dicht",
    reden: "Jaarlijkse sluiting",
    bron: "periode",
  },
];
const REGELS: RegelRij[] = [
  { weekdag: 0, vanaf: "2026-09-01", tot: null, reden: "" },
];

test("het verzoek gaat naar de functie van migratie 012, niet naar de tabellen", () => {
  const { url, headers } = bewaarVerzoek(DAGEN, REGELS, "lien", OMGEVING);
  const u = new URL(url);
  assert.equal(u.origin, "https://ref.supabase.co");
  // Rechtstreeks naar sluitingsdag en sluitingsregel schrijven zou twee
  // verzoeken vergen en dus twee transacties; de rol achter de secret key
  // heeft daar bovendien geen insert-recht op (migratie 011).
  assert.equal(u.pathname, `/rest/v1/rpc/${RPC}`);
  assert.equal(headers.apikey, "sb_secret_x");
  assert.equal(headers.Authorization, "Bearer sb_secret_x");
  assert.equal(headers["Content-Type"], "application/json");
});

test("de body draagt de kalender met dagen en regels, plus wie hem bewaarde", () => {
  const { body } = bewaarVerzoek(DAGEN, REGELS, "lien", OMGEVING);
  const gelezen = JSON.parse(body);
  // De sleutels kalender en door zijn de parameternamen van de SQL-functie —
  // de PostgREST-conventie, precies zoals bij bewaar_kostenmodel.
  assert.deepEqual(gelezen, {
    kalender: {
      dagen: [
        {
          datum: "2026-12-25",
          toestand: "dicht",
          reden: "Kerstmis",
          bron: "feestdag",
        },
        {
          datum: "2026-08-17",
          toestand: "dicht",
          reden: "Jaarlijkse sluiting",
          bron: "periode",
        },
      ],
      regels: [{ weekdag: 0, vanaf: "2026-09-01", tot: null, reden: "" }],
    },
    door: "lien",
  });
});

test("een lege kalender is een geldig verzoek: leegmaken hoort te kunnen", () => {
  const { body } = bewaarVerzoek([], [], "lien", OMGEVING);
  const gelezen = JSON.parse(body);
  assert.deepEqual(gelezen.kalender.dagen, []);
  assert.deepEqual(gelezen.kalender.regels, []);
  assert.equal(gelezen.door, "lien");
});

test("een projecturl met slotstreep levert geen dubbele schuine streep", () => {
  const { url } = bewaarVerzoek(DAGEN, REGELS, "lien", {
    ...OMGEVING,
    NEXT_PUBLIC_SUPABASE_URL: "https://ref.supabase.co/",
  });
  assert.equal(new URL(url).pathname, `/rest/v1/rpc/${RPC}`);
});

test("zonder serveromgeving werpt het verzoek leesbaar", () => {
  assert.throws(
    () => bewaarVerzoek(DAGEN, REGELS, "lien", {}),
    /NEXT_PUBLIC_SUPABASE_URL en SUPABASE_SECRET_KEY/,
  );
});

test("laadSluitingen is null op de bestandsroute: de vraag bestaat daar niet", async () => {
  // Zonder CONTRACT_BRON=db is er geen database om uit te lezen; null en
  // geen lege stand, want de server-actie moet dan weigeren te bewaren.
  const uit = await laadSluitingen({ CONTRACT_BRON: "bestand" });
  assert.equal(uit, null);
});
