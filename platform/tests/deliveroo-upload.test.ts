import assert from "node:assert/strict";
import { test } from "node:test";

import {
  bepaalMediatype,
  MAX_BYTES,
  MAX_MB,
  naarBase64,
  valideerUpload,
} from "../lib/deliveroo-upload";

/**
 * De poort van het uploadscherm, naar het model van
 * tests/sluitingsdagen.test.ts. Wat hier vastligt, kost geld of vertrouwen als
 * het schuift: een bestand dat te groot is mag niet eerst tien megabyte door de
 * server-actie reizen om daarna geweigerd te worden, en een geldige export mag
 * niet stranden op een mediatype dat de computer van de beheerder verzint.
 */

/** Kortere schrijfwijze; alle drie de velden zijn altijd nodig. */
function fouten(bestandsnaam: string, mediatype: string, bytes: number) {
  return valideerUpload({ bestandsnaam, mediatype, bytes }).fouten.map(
    (f) => f.sleutel,
  );
}

test("een gewone export komt zonder bezwaar door de poort", () => {
  assert.deepEqual(fouten("deliveroo-augustus.csv", "text/csv", 12_000), []);
  assert.deepEqual(fouten("afrekening.pdf", "application/pdf", 400_000), []);
});

test("een bestand boven de grens wordt geweigerd, precies op de grens niet", () => {
  assert.deepEqual(fouten("groot.csv", "text/csv", MAX_BYTES), []);
  assert.deepEqual(fouten("groot.csv", "text/csv", MAX_BYTES + 1), [
    "deliveroo.teGroot",
  ]);
});

test("de melding over de grens noemt de megabytes en niet de bytes", () => {
  // 10485760 op een scherm zegt een mens niets; de poort levert daarom het
  // getal dat in de zin hoort.
  const [fout] = valideerUpload({
    bestandsnaam: "groot.csv",
    mediatype: "text/csv",
    bytes: MAX_BYTES + 1,
  }).fouten;
  assert.deepEqual(fout.waarden, { max: String(MAX_MB) });
});

test("een leeg bestand is een eigen bezwaar en geen te-groot-bezwaar", () => {
  // Een browser levert een bestand van nul bytes zonder morren; zonder deze
  // controle staat er een lege rij in de database die de inlaadlaag 's nachts
  // moet afwijzen.
  assert.deepEqual(fouten("leeg.csv", "text/csv", 0), [
    "deliveroo.leegBestand",
  ]);
});

test("een bestand van een ander soort wordt geweigerd", () => {
  assert.deepEqual(fouten("schermafdruk.png", "image/png", 5_000), [
    "deliveroo.typeOnbekend",
  ]);
  // Zonder extensie én zonder bruikbaar mediatype valt er niets te bepalen.
  assert.deepEqual(fouten("export", "application/octet-stream", 5_000), [
    "deliveroo.typeOnbekend",
  ]);
});

test("zonder bruikbaar mediatype beslist de extensie", () => {
  // Dit is de gewone gang van zaken en geen randgeval: een csv uit Excel komt
  // op Windows binnen als octet-stream of met een lege tekenreeks, en die
  // weigeren zou een geldige export tegenhouden om een eigenschap van de
  // computer van de beheerder.
  assert.deepEqual(fouten("export.csv", "application/octet-stream", 900), []);
  assert.deepEqual(fouten("export.xlsx", "", 900), []);
  assert.equal(
    bepaalMediatype("export.csv", "application/octet-stream"),
    "text/csv",
  );
  assert.equal(
    bepaalMediatype("Export.XLSX", ""),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  );
});

test("een aangekondigd type met parameters wordt herkend", () => {
  assert.equal(bepaalMediatype("export.csv", "text/csv; charset=utf-8"), "text/csv");
});

test("een naam met een padscheidingsteken komt er niet in", () => {
  // Een browser stuurt alleen de kale naam, dus dit hoort niet te gebeuren —
  // maar de naam komt ongewijzigd in de database en van daaruit onder ogen van
  // de inlaadlaag, en daar struikelt een script over.
  assert.deepEqual(fouten("../../etc/passwd.csv", "text/csv", 900), [
    "deliveroo.naamOngeldig",
  ]);
  assert.deepEqual(fouten("map/export.csv", "text/csv", 900), [
    "deliveroo.naamOngeldig",
  ]);
  assert.deepEqual(fouten("map\\export.csv", "text/csv", 900), [
    "deliveroo.naamOngeldig",
  ]);
  // Een naam van louter spaties is evenmin een naam. Het mediatype is hier
  // wél bruikbaar, dus dit blijft één bezwaar.
  assert.deepEqual(fouten("   ", "text/csv", 900), ["deliveroo.naamOngeldig"]);
});

test("alle bezwaren komen tegelijk terug; de actie toont er één", () => {
  assert.deepEqual(fouten("map/schermafdruk.png", "image/png", 0), [
    "deliveroo.naamOngeldig",
    "deliveroo.leegBestand",
    "deliveroo.typeOnbekend",
  ]);
});

test("een grote buffer gaat heel naar base64, zonder de stack te breken", () => {
  // Drie megabyte: ruim boven de grens waar `String.fromCharCode(...bytes)` de
  // argumentenstack omlegt. Dat die vorm hier niet gebruikt wordt, is precies
  // wat deze test bewaakt — hij zou anders niet falen maar omvallen.
  const n = 3 * 1024 * 1024;
  const groot = new Uint8Array(n);
  for (let i = 0; i < n; i++) groot[i] = i % 256;

  const b64 = naarBase64(groot);
  assert.equal(b64.length, 4 * Math.ceil(n / 3));
  // Heen en terug: elke byte staat er nog, in dezelfde volgorde.
  const terug = new Uint8Array(Buffer.from(b64, "base64"));
  assert.equal(terug.length, n);
  assert.ok(terug.every((waarde, i) => waarde === groot[i]));
});

test("een ArrayBuffer levert dezelfde base64 als de bijbehorende Uint8Array", () => {
  // `File.arrayBuffer()` geeft een ArrayBuffer; beide vormen moeten dezelfde
  // tekenreeks opleveren, anders hangt de vingerafdruk aan de vorm.
  const ruw = new ArrayBuffer(6);
  new Uint8Array(ruw).set([0, 1, 2, 253, 254, 255]);
  assert.equal(naarBase64(ruw), naarBase64(new Uint8Array(ruw)));
});
