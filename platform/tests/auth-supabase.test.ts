import assert from "node:assert/strict";
import { test } from "node:test";

import { rolUit, sessieUitSupabase } from "../lib/auth-supabase";

/**
 * De vertaling van een Supabase-gebruiker naar onze sessie. Gedrag dat hier
 * vastligt: de rol komt alleen uit app_metadata, en zonder geldige rol komt
 * er geen sessie — "dan maar lezer" zou een achterdeur zijn.
 */

test("de rol komt uit app_metadata", () => {
  assert.equal(rolUit({ app_metadata: { rol: "beheerder" } }), "beheerder");
  assert.equal(rolUit({ app_metadata: { rol: "lezer" } }), "lezer");
});

test("zonder rol, met een onbekende rol of met rol op de verkeerde plek: geen rol", () => {
  assert.equal(rolUit({}), null);
  assert.equal(rolUit({ app_metadata: {} }), null);
  assert.equal(rolUit({ app_metadata: { rol: "admin" } }), null);
  // user_metadata is door de gebruiker zelf te schrijven; een rol daar telt
  // niet, anders benoemt een lezer zichzelf tot beheerder.
  assert.equal(
    rolUit({ app_metadata: {}, ...{ user_metadata: { rol: "beheerder" } } }),
    null,
  );
});

test("een geldige gebruiker wordt een sessie met onze looptijd", () => {
  const nu = 1_700_000_000;
  const sessie = sessieUitSupabase(
    { email: "Lien@Voorbeeld.be", app_metadata: { rol: "lezer" } },
    nu,
  );
  assert.ok(sessie);
  assert.equal(sessie.gebruiker, "lien@voorbeeld.be");
  assert.equal(sessie.rol, "lezer");
  assert.equal(sessie.exp, nu + 12 * 60 * 60);
});

test("zonder rol of zonder e-mail komt er geen sessie", () => {
  assert.equal(
    sessieUitSupabase({ email: "x@y.be", app_metadata: {} }, 0),
    null,
  );
  assert.equal(
    sessieUitSupabase({ app_metadata: { rol: "beheerder" } }, 0),
    null,
  );
});
