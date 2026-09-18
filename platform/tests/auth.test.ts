import assert from "node:assert/strict";
import { test } from "node:test";

import {
  erZijnGebruikers,
  klopt,
  lees,
  maakAfdruk,
  teken,
  verifieer,
  type Sessie,
} from "../lib/auth";

// Een vaste sleutel voor de sessietests. 32 bytes, base64url — zoals de echte.
const TESTSLEUTEL = "dGVzdHNsZXV0ZWwtMzItYnl0ZXMtbGFuZy1nZW5vZWc";

test("een afdruk overleeft de env-loader: geen enkel teken met bijbetekenis", async () => {
  // De login was ooit een avond stuk omdat de afdruk een `$` bevatte en de
  // env-loader van Next alles vanaf dat teken als variabele wegexpandeerde.
  // Deze test is het hek om dat gat.
  const a = await maakAfdruk("proefwachtwoord");
  assert.ok(!a.includes("$"), "een $ wordt door dotenv-expand weggeknipt");
  assert.match(a, /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/, "vorm is <zout>.<afdruk>, beide base64url");
});

test("afdruk en controle vormen een gesloten paar", async () => {
  const a = await maakAfdruk("juist-wachtwoord");
  assert.equal(await klopt("juist-wachtwoord", a), true);
  assert.equal(await klopt("fout-wachtwoord", a), false);
  assert.equal(await klopt("", a), false);
});

test("een kapotte opgeslagen afdruk keurt alles af in plaats van te crashen", async () => {
  assert.equal(await klopt("wachtwoord", ""), false);
  assert.equal(await klopt("wachtwoord", "alleen-zout-geen-punt"), false);
  assert.equal(await klopt("wachtwoord", "zout$oude-vorm-met-dollar"), false);
});

test("verifieer kent alleen geldige regels, en meldt ongeldige hardop", async (t) => {
  const afdruk = await maakAfdruk("geheim123");
  const meldingen: string[] = [];
  t.mock.method(console, "warn", (m: string) => void meldingen.push(m));
  process.env.PLATFORM_GEBRUIKERS = [
    `kwinten:beheerder:${afdruk}`,
    "kapot:beheerder:afdruk-zonder-punt", // zoals na dotenv-expansie van een $
    "half:onbekenderol:x.y",
  ].join(",");

  assert.ok(erZijnGebruikers());
  const sessie = await verifieer("kwinten", "geheim123");
  assert.equal(sessie?.gebruiker, "kwinten");
  assert.equal(sessie?.rol, "beheerder");
  assert.equal(await verifieer("kwinten", "verkeerd"), null);
  assert.equal(await verifieer("kapot", "wat dan ook"), null);
  assert.equal(meldingen.length, 2, "beide kapotte regels geven een waarschuwing");
});

test("naam is niet hoofdlettergevoelig, het wachtwoord wel", async () => {
  const afdruk = await maakAfdruk("Geheim123");
  process.env.PLATFORM_GEBRUIKERS = `Kwinten:lezer:${afdruk}`;
  assert.equal((await verifieer("KWINTEN", "Geheim123"))?.gebruiker, "kwinten");
  assert.equal(await verifieer("kwinten", "geheim123"), null);
});

test('de oude rolnaam "bekijker" blijft geldig en wordt "lezer"', async () => {
  // De rol heet sinds 18 aug 2026 "lezer" (scope D6, vraag 57); bestaande
  // PLATFORM_GEBRUIKERS-regels met "bekijker" mogen daar niet op breken.
  const afdruk = await maakAfdruk("Geheim123");
  process.env.PLATFORM_GEBRUIKERS = `kwinten:bekijker:${afdruk}`;
  assert.equal((await verifieer("kwinten", "Geheim123"))?.rol, "lezer");
});

test("zonder gebruikers komt niemand binnen", async () => {
  process.env.PLATFORM_GEBRUIKERS = "";
  assert.equal(erZijnGebruikers(), false);
  assert.equal(await verifieer("kwinten", "asklien"), null);
});

test("een sessie overleeft de reis token-heen, token-terug", async () => {
  process.env.PLATFORM_SESSIE_SLEUTEL = TESTSLEUTEL;
  // Sinds 14 aug toetst lees() de gebruiker en rol tegen de actuele omgeving:
  // een cookie is tot 12 uur oud, de omgeving is de waarheid.
  process.env.PLATFORM_GEBRUIKERS = "kwinten:beheerder:zout.afdruk";
  const sessie: Sessie = {
    gebruiker: "kwinten",
    rol: "beheerder",
    exp: Math.floor(Date.now() / 1000) + 60,
  };
  const token = await teken(sessie);
  assert.deepEqual(await lees(token), sessie);
});

test("een geschrapte gebruiker of ingetrokken rol werkt meteen door", async () => {
  process.env.PLATFORM_SESSIE_SLEUTEL = TESTSLEUTEL;
  process.env.PLATFORM_GEBRUIKERS = "kwinten:beheerder:zout.afdruk";
  const token = await teken({
    gebruiker: "kwinten",
    rol: "beheerder",
    exp: Math.floor(Date.now() / 1000) + 60,
  });

  // Rol in de omgeving verlaagd: de cookie zegt beheerder, de omgeving wint.
  process.env.PLATFORM_GEBRUIKERS = "kwinten:lezer:zout.afdruk";
  assert.equal((await lees(token))?.rol, "lezer");

  // Gebruiker geschrapt: de nog geldige cookie is meteen waardeloos.
  process.env.PLATFORM_GEBRUIKERS = "";
  assert.equal(await lees(token), null);
});

test("op Supabase geeft lees() de sessie uit de cookie terug, zonder omgevingslijst", async () => {
  process.env.PLATFORM_SESSIE_SLEUTEL = TESTSLEUTEL;
  process.env.AUTH_BRON = "supabase";
  // Op Supabase staan de gebruikers bij Supabase, niet in de omgeving.
  // Vóór de fix van 18 aug toetste lees() tóch tegen de (lege) omgevingslijst
  // en verwierp het elke geldige sessie: een oneindige inloglus.
  delete process.env.PLATFORM_GEBRUIKERS;
  try {
    const sessie: Sessie = {
      gebruiker: "lien@voorbeeld.be",
      rol: "beheerder",
      exp: Math.floor(Date.now() / 1000) + 60,
    };
    const token = await teken(sessie);
    assert.deepEqual(await lees(token), sessie);

    // De branch slaat alleen de omgevingsherbevestiging over; handtekening en
    // vervaltijd worden ook op Supabase nog altijd getoetst.
    const verlopen = await teken({ ...sessie, exp: Math.floor(Date.now() / 1000) - 1 });
    assert.equal(await lees(verlopen), null);
  } finally {
    delete process.env.AUTH_BRON;
  }
});

test("op de omgevingslaag blijft een verwijderde gebruiker verworpen", async () => {
  // Het spiegelbeeld van de Supabase-test hierboven: de prijs van het
  // overslaan geldt alleen dáár. Op de omgevingslaag blijft de omgeving de
  // waarheid, en is een geschrapte gebruiker meteen buiten.
  process.env.PLATFORM_SESSIE_SLEUTEL = TESTSLEUTEL;
  process.env.AUTH_BRON = "omgeving";
  try {
    process.env.PLATFORM_GEBRUIKERS = "kwinten:beheerder:zout.afdruk";
    const token = await teken({
      gebruiker: "kwinten",
      rol: "beheerder",
      exp: Math.floor(Date.now() / 1000) + 60,
    });
    process.env.PLATFORM_GEBRUIKERS = "";
    assert.equal(await lees(token), null);
  } finally {
    delete process.env.AUTH_BRON;
  }
});

test("een vervalste of verlopen sessie wordt geweigerd", async () => {
  process.env.PLATFORM_SESSIE_SLEUTEL = TESTSLEUTEL;
  const echt = await teken({ gebruiker: "kwinten", rol: "beheerder", exp: Math.floor(Date.now() / 1000) + 60 });
  const [payload] = echt.split(".");

  assert.equal(await lees(undefined), null);
  assert.equal(await lees("onzin"), null);
  assert.equal(await lees(`${payload}.vervalste-handtekening`), null);

  const verlopen = await teken({ gebruiker: "kwinten", rol: "beheerder", exp: Math.floor(Date.now() / 1000) - 1 });
  assert.equal(await lees(verlopen), null);

  // Payload aangepast maar handtekening van het echte token: weigeren.
  const anderePayload = Buffer.from(JSON.stringify({ gebruiker: "indringer", rol: "beheerder", exp: 9999999999 })).toString("base64url");
  assert.equal(await lees(`${anderePayload}.${echt.split(".")[1]}`), null);
});
