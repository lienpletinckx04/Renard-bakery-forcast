import assert from "node:assert/strict";
import { test } from "node:test";

import {
  aantal,
  datumKort,
  datumMetTijd,
  euro,
  euroBedrag,
  geheelGetal,
  procent,
  verschilProcent,
} from "../lib/format";

test("euro groepeert lexicaal en rekent niet", () => {
  assert.equal(euro("1234.56"), "€ 1.234,56");
  assert.equal(euro("0.00"), "€ 0,00");
  assert.equal(euro("-12.50"), "€ −12,50");
  assert.equal(euro("1234567.89"), "€ 1.234.567,89");
});

test("procent en verschilprocent dragen de echte minus en de plus", () => {
  assert.equal(procent("12.3"), "12,3 %");
  assert.equal(procent("-4.2"), "−4,2 %");
  assert.equal(verschilProcent("3.1"), "+3,1 %");
  assert.equal(verschilProcent("-4.2"), "−4,2 %");
});

test("aantal en geheelGetal groeperen zonder decimalen te verzinnen", () => {
  assert.equal(aantal("1234"), "1.234");
  assert.equal(geheelGetal(28), "28");
  assert.equal(geheelGetal(12345), "12.345");
});

test("euroBedrag zet plotgeometrie vast op twee decimalen", () => {
  assert.equal(euroBedrag(2481.5), "€ 2.481,50");
  assert.equal(euroBedrag(7), "€ 7,00");
});

test("datums in Belgisch kort formaat", () => {
  assert.equal(datumKort("2026-08-12T04:00:00+02:00"), "12 aug 2026");
  assert.equal(datumKort("2026-01-05"), "5 jan 2026");
  assert.equal(datumMetTijd("2026-08-12T04:00:00+02:00"), "12 aug 2026, 04:00");
});

test("de eerste van de maand is in het Frans 1er, in het Nederlands 1", () => {
  assert.equal(datumKort("2026-01-01", "fr"), "1er janv 2026");
  assert.equal(datumKort("2026-01-02", "fr"), "2 janv 2026");
  assert.equal(datumKort("2026-01-01", "nl"), "1 jan 2026");
  assert.equal(datumMetTijd("2026-01-01T04:00:00+01:00", "fr"), "1er janv 2026, 04:00");
});

test("een kapotte datum crasht het scherm niet maar komt rauw terug", () => {
  assert.equal(datumKort(""), "");
  assert.equal(datumKort("geen datum"), "geen datum");
  assert.equal(datumKort("2026-13-40"), "2026-13-40");
  assert.equal(datumMetTijd("2026-08-12"), "12 aug 2026");
});
