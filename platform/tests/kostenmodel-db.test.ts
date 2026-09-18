import assert from "node:assert/strict";
import { test } from "node:test";

import { bewaarVerzoek, RPC } from "../lib/kostenmodel-db";

/**
 * De schrijfroute van het kostenmodel op de gehoste omgeving. Wat hier
 * vastligt, is precies wat er niet met het oog te controleren valt: dat het
 * ÉÉN verzoek is (dus één transactie, dus alles of niets), dat het naar de
 * functie van migratie 009 gaat en niet naar de tabellen, en dat percentages
 * als tekst reizen in plaats van als getal.
 */

const OMGEVING = {
  NEXT_PUBLIC_SUPABASE_URL: "https://ref.supabase.co",
  SUPABASE_SECRET_KEY: "sb_secret_x",
};

const CRITERIA = [
  { naam: "Grondstoffen", omschrijving: "foodcost" },
  { naam: "Verlies en verspilling", omschrijving: "" },
];
const WAARDEN = {
  Brood: { Grondstoffen: "30.5", "Verlies en verspilling": "2" },
};

test("het verzoek gaat naar de functie van migratie 009, niet naar de tabellen", () => {
  const { url, headers } = bewaarVerzoek(CRITERIA, WAARDEN, "lien", OMGEVING);
  const u = new URL(url);
  assert.equal(u.origin, "https://ref.supabase.co");
  // Rechtstreeks naar kosten_criterium schrijven zou twee verzoeken vergen en
  // dus twee transacties; de rol achter de secret key heeft daar bovendien geen
  // recht op (migratie 008 gaf haar alleen select).
  assert.equal(u.pathname, `/rest/v1/rpc/${RPC}`);
  assert.equal(headers.apikey, "sb_secret_x");
  assert.equal(headers.Authorization, "Bearer sb_secret_x");
  assert.equal(headers["Content-Type"], "application/json");
});

test("de body draagt de bestandsvorm van het kostenmodel, plus wie het bewaarde", () => {
  const { body } = bewaarVerzoek(CRITERIA, WAARDEN, "lien", OMGEVING);
  const gelezen = JSON.parse(body);
  // Exact de vorm die bakkerij/kostenmodel.py in het bestand schrijft: dan leest
  // de contractbouw uit de database wat hij uit een bestand zou lezen, en is er
  // één vorm in plaats van twee.
  assert.equal(gelezen.model.versie, 2);
  assert.deepEqual(gelezen.model.criteria, CRITERIA);
  assert.deepEqual(gelezen.model.waarden, WAARDEN);
  // bewaard_door is `not null` in migratie 005: elke wijziging aan de
  // cijferbasis draagt de naam van wie hem deed.
  assert.equal(gelezen.door, "lien");
});

test("percentages reizen als tekst, nooit als getal", () => {
  const { body } = bewaarVerzoek(
    [{ naam: "Grondstoffen", omschrijving: "" }],
    { Brood: { Grondstoffen: "30.50" } },
    "lien",
    OMGEVING,
  );
  // "30.50" en niet 30.5: een JSON-getal gaat door een float, en dan is 30,5 %
  // op het scherm een keer 30,499... De kolom is `numeric` om dezelfde reden.
  assert.match(body, /"30\.50"/);
  assert.equal(typeof JSON.parse(body).model.waarden.Brood.Grondstoffen, "string");
});

test("een leeg model is een geldig verzoek: leegmaken hoort te kunnen", () => {
  const { body } = bewaarVerzoek([], {}, "lien", OMGEVING);
  const gelezen = JSON.parse(body);
  assert.deepEqual(gelezen.model.criteria, []);
  assert.deepEqual(gelezen.model.waarden, {});
});

test("een projecturl met slotstreep levert geen dubbele schuine streep", () => {
  const { url } = bewaarVerzoek(CRITERIA, WAARDEN, "lien", {
    ...OMGEVING,
    NEXT_PUBLIC_SUPABASE_URL: "https://ref.supabase.co/",
  });
  assert.equal(new URL(url).pathname, `/rest/v1/rpc/${RPC}`);
});

test("zonder serveromgeving werpt het verzoek leesbaar", () => {
  assert.throws(
    () => bewaarVerzoek(CRITERIA, WAARDEN, "lien", {}),
    /NEXT_PUBLIC_SUPABASE_URL en SUPABASE_SECRET_KEY/,
  );
});
