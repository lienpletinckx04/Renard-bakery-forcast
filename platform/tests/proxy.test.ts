/**
 * De wacht op de toegangspoort: welke paden bewaakt `proxy.ts`, en welke laat
 * het bewust vrij?
 *
 * De matcher is de kritiekste regel van het platform — één uitzondering te
 * veel en de cijfers van de klant staan open, één te weinig en het inlogscherm
 * verliest zijn lettertype en merkbeelden. Tot 18 augustus 2026 toetste niets
 * hem.
 *
 * WAAROM DE TEST DE BRON LEEST EN NIET IMPORTEERT. Twee redenen, elk op
 * zichzelf voldoende:
 *  1. proxy.ts importeert next/server en @/lib/auth; de @-alias is van de
 *     Next-bundler en de testrunner lost hem niet op.
 *  2. Belangrijker: de matcher naar een importeerbaar module verhuizen mag
 *     níét. Next eist dat de matcher een constante literal is en negeert
 *     dynamische waarden stilzwijgend (node_modules/next/dist/docs/…/
 *     proxy.md: "Dynamic values such as variables will be ignored") — de
 *     extractie zou de bewaking in productie dus geruisloos uitschakelen.
 * Daarom dezelfde techniek als de wachtwoordparameters-test: de bron lezen en
 * exact de tekst toetsen die Next bij het bouwen leest.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const PROXY = path.join(import.meta.dirname, "..", "proxy.ts");

/** Het ene matcherpatroon uit `export const config` in proxy.ts. */
function leesMatcher(): string {
  const bron = readFileSync(PROXY, "utf-8");
  const m = /matcher:\s*\[\s*"([^"]+)"\s*\]/.exec(bron);
  assert.ok(m, "proxy.ts: geen matcher gevonden — is de config herschreven?");
  return m[1]!;
}

/**
 * Bootst na hoe Next het patroon toepast: het is al een regulier
 * (path-to-regexp-)patroon over het volledige pad, getoetst zonder de query.
 */
function bewaakt(url: string): boolean {
  const pad = url.split("?")[0]!;
  return new RegExp(`^${leesMatcher()}$`).test(pad);
}

test("de proxy bewaakt elke bladzijde, ook het inlogscherm zelf", () => {
  // /login staat er bewust bij: de proxy behandelt dat pad apart (wie al is
  // aangemeld wordt doorgestuurd), maar het moet daarvoor wél langs de proxy.
  for (const pad of ["/", "/instellingen", "/rapport", "/login"]) {
    assert.ok(bewaakt(pad), `${pad} moet door de proxy bewaakt worden`);
  }
});

test("de proxy laat alleen de statische bestanden en de merkbeelden vrij", () => {
  // De vrijgestelde paden zijn identiteit en machinerie, geen cijfers: de
  // bundels van Next, het favicon, het lettertype en de merkbeelden die het
  // inlogscherm nodig heeft vóór er een sessie bestaat.
  for (const pad of [
    "/_next/static/x.js",
    "/_next/image?x",
    "/favicon.ico",
    "/fonts/a.woff2",
    "/brand/logo.png",
  ]) {
    assert.ok(!bewaakt(pad), `${pad} hoort vrijgesteld te zijn van de proxy`);
  }
});

test("de vrijstelling geldt het voorvoegsel, niet het woord", () => {
  // Een pad dat op een vrijgesteld woord lijkt maar er niet mee begint, blijft
  // bewaakt: de uitzondering is een prefix in een lookahead, geen zoekwoord.
  for (const pad of ["/rapport/fonts/x", "/brandpunt", "/x/_next/static/y.js"]) {
    assert.ok(bewaakt(pad), `${pad} moet bewaakt blijven`);
  }
});
