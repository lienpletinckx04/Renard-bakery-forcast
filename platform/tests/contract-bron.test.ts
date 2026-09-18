import assert from "node:assert/strict";
import path from "node:path";
import { test } from "node:test";

import { contractBron, contractPad, dbVerzoek } from "../lib/contract-bron";

/**
 * De wissel van O13. Het belangrijkste gedrag dat hier vastligt is negatief:
 * ZONDER CONTRACT_BRON verandert er niets — de bron is "bestand" en het
 * bestandspad is het pad van altijd. Dat is de garantie waarop de hele
 * voorbereiding tot S11 rust; wie haar breekt, hoort het hier.
 */

test("zonder vlag is de bron 'bestand' — de standaardroute wijzigt niet", () => {
  assert.equal(contractBron({}), "bestand");
  assert.equal(contractBron({ CONTRACT_BRON: undefined }), "bestand");
  assert.equal(contractBron({ CONTRACT_BRON: "bestand" }), "bestand");
});

test("met de vlag op db wisselt de bron", () => {
  assert.equal(contractBron({ CONTRACT_BRON: "db" }), "db");
});

test("een onbekende waarde werpt in plaats van stil terug te vallen", () => {
  assert.throws(
    () => contractBron({ CONTRACT_BRON: "postgres" }),
    /CONTRACT_BRON=postgres is onbekend/,
  );
});

test("het bestandspad ligt waar het altijd lag", () => {
  const wortel = path.join("/app", "contract");
  // Nederlands in de wortel, Frans in een submap, winkels in winkels/<slug>/ —
  // letterlijk de paden die laadContract vóór de wissel bouwde.
  assert.equal(
    contractPad(wortel, "overzicht", "nl", null),
    path.join(wortel, "overzicht.json"),
  );
  assert.equal(
    contractPad(wortel, "prognose", "fr", null),
    path.join(wortel, "fr", "prognose.json"),
  );
  assert.equal(
    contractPad(wortel, "marge", "nl", "centrum"),
    path.join(wortel, "winkels", "centrum", "marge.json"),
  );
  assert.equal(
    contractPad(wortel, "marge", "fr", "centrum"),
    path.join(wortel, "fr", "winkels", "centrum", "marge.json"),
  );
});

const OMGEVING = {
  NEXT_PUBLIC_SUPABASE_URL: "https://ref.supabase.co",
  SUPABASE_SECRET_KEY: "sb_secret_x",
};

test("het databaseverzoek draagt de sleutel scherm × taal × winkel", () => {
  const { url, headers } = dbVerzoek("kanalen", "fr", null, OMGEVING);
  const u = new URL(url);
  assert.equal(u.origin, "https://ref.supabase.co");
  assert.equal(u.pathname, "/rest/v1/contract_antwoord");
  assert.equal(u.searchParams.get("select"), "antwoord");
  assert.equal(u.searchParams.get("scherm"), "eq.kanalen");
  assert.equal(u.searchParams.get("taal"), "eq.fr");
  // Het totaal is de lege string, dezelfde afspraak als migratie 006.
  assert.equal(u.searchParams.get("winkel"), "eq.");
  assert.equal(headers.apikey, "sb_secret_x");
  assert.equal(headers.Authorization, "Bearer sb_secret_x");
  // Eén object, geen lijst: nul rijen moet een fout worden, geen leeg array.
  assert.equal(headers.Accept, "application/vnd.pgrst.object+json");
});

test("een winkelslug reist mee als winkel-sleutel", () => {
  const { url } = dbVerzoek("marge", "nl", "centrum", OMGEVING);
  assert.equal(new URL(url).searchParams.get("winkel"), "eq.centrum");
});

test("zonder serveromgeving werpt het verzoek leesbaar", () => {
  assert.throws(
    () => dbVerzoek("stand", "nl", null, {}),
    /NEXT_PUBLIC_SUPABASE_URL en SUPABASE_SECRET_KEY/,
  );
  assert.throws(
    () => dbVerzoek("stand", "nl", null, {
      NEXT_PUBLIC_SUPABASE_URL: "https://ref.supabase.co",
    }),
    /SUPABASE_SECRET_KEY/,
  );
});
