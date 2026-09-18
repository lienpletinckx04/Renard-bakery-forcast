import assert from "node:assert/strict";
import { test } from "node:test";

import { geheelGetal } from "../lib/format";
import { versheid } from "../lib/versheid";

test("versheid noemt beide tijdstippen, elk met zijn betekenis", () => {
  const v = versheid("2026-08-12T21:53:55+02:00", "2026-07-31");
  assert.equal(v.cijfers, "Cijfers tot en met 31 jul 2026");
  assert.equal(v.verwerkt, "verwerkt op 12 aug 2026, 21:53");
});

test("de meetdatum wordt niet verward met het verwerkingsmoment", () => {
  // Twaalf dagen ertussen: precies het geval waarin de oude voettekst
  // ("Bijgewerkt op 12 aug") de lezer een verkeerde versheid voorspiegelde.
  const v = versheid("2026-08-12T21:53:55+02:00", "2026-07-31");
  assert.ok(v.cijfers.includes("31 jul 2026"));
  assert.ok(!v.cijfers.includes("12 aug 2026"));
  assert.ok(v.verwerkt.includes("12 aug 2026"));
});

test("zonder meetbereik staat er een reden, geen stilte en geen streepje", () => {
  for (const leeg of [null, undefined]) {
    const v = versheid("2026-08-12T21:53:55+02:00", leeg);
    assert.ok(v.cijfers.length > 0);
    assert.ok(!["-", "—", "−", ""].includes(v.cijfers.trim()));
    assert.ok(/onbekend/i.test(v.cijfers));
    // Geen datum verzinnen als er geen meting is.
    assert.ok(!/\d{4}/.test(v.cijfers));
    // Het verwerkingsmoment blijft wel gewoon staan.
    assert.equal(v.verwerkt, "verwerkt op 12 aug 2026, 21:53");
  }
});

test("een gehele datum met tijd mag ook als meetbereik binnenkomen", () => {
  const v = versheid("2026-08-12T21:53:55+02:00", "2026-07-31T00:00:00+02:00");
  assert.equal(v.cijfers, "Cijfers tot en met 31 jul 2026");
});

test("gehele getallen krijgen de Belgische groepering", () => {
  assert.equal(geheelGetal(0), "0");
  assert.equal(geheelGetal(7), "7");
  assert.equal(geheelGetal(1234), "1.234");
  assert.equal(geheelGetal(1234567), "1.234.567");
});
