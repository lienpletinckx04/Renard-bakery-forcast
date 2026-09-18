import assert from "node:assert/strict";
import { test } from "node:test";

import type {
  Antwoord,
  BronStand,
  StandData,
  Trackrecord,
  Wachter,
} from "../lib/contract";
import { datakwaliteitVoettekst, statusWoord } from "../lib/stand";
import { maakT } from "../lib/taal";

const t = maakT("nl");

test("statuswoorden verliezen hun underscore en verder niets", () => {
  assert.equal(statusWoord("vers"), "vers");
  assert.equal(statusWoord("achter"), "achter");
  assert.equal(statusWoord("let_op"), "let op");
  // Een nieuw woord uit de berekeningslaag valt niet stil van het scherm.
  assert.equal(statusWoord("iets_nieuws"), "iets nieuws");
});

test("bij goed staat er niets in de voettekst — geen alarmvermoeidheid", () => {
  assert.equal(datakwaliteitVoettekst("goed", t), null);
});

test("let op en fout dragen elk hun eigen regel", () => {
  assert.equal(datakwaliteitVoettekst("let_op", t), "Let op: datakwaliteit");
  assert.equal(datakwaliteitVoettekst("fout", t), "Alarm: datakwaliteit");
});

test("een onbekende uitkomst wordt nooit als goed gelezen: alarm", () => {
  // Het onbekende woord zelf staat op Instellingen (statusWoord); de
  // voettekst kiest de zwaarste regel in plaats van te zwijgen.
  assert.equal(datakwaliteitVoettekst("paniek", t), "Alarm: datakwaliteit");
});

/**
 * Typedekking: de twee nieuwe contractvormen moeten compileren zoals de
 * generator ze schrijft. `tsc --noEmit` bewaakt dit; de runtime-asserts
 * hieronder zijn er alleen opdat de test iets uitvoert.
 */
test("de standvorm uit het contract compileert met alle statussen", () => {
  const bronnen: BronStand[] = [
    {
      bron: "odoo",
      laatste_meetdag: "2026-08-12",
      rijen: 1234,
      status: "vers",
      toelichting: "Gisteren gemeten.",
    },
    {
      bron: "deliveroo",
      laatste_meetdag: "2026-08-01",
      rijen: 56,
      status: "achter",
      toelichting: "Elf dagen zonder nieuwe meting.",
    },
    { bron: "a", laatste_meetdag: null, rijen: 0, status: "stil", toelichting: "" },
    { bron: "b", laatste_meetdag: null, rijen: 0, status: "gesloten", toelichting: "" },
    { bron: "c", laatste_meetdag: null, rijen: 0, status: "ontbreekt", toelichting: "" },
  ];
  const wachters: Wachter[] = [
    { naam: "rijen per dag", uitkomst: "goed", toelichting: "" },
    { naam: "omzet tegen kassa", uitkomst: "let_op", toelichting: "" },
    { naam: "dubbele dagen", uitkomst: "fout", toelichting: "" },
  ];
  const antwoord: Antwoord<StandData> = {
    versie: 1,
    bijgewerkt_op: "2026-08-13T04:00:00+02:00",
    gemeten_tot: "2026-08-12",
    bron: ["odoo", "deliveroo"],
    onbeschikbaar: [],
    briefing: { punten: [], leeg: "" },
    data: { bronnen, wachters, ergste: "let_op" },
  };
  assert.equal(antwoord.data.bronnen.length, 5);
  assert.equal(antwoord.data.wachters.length, 3);
});

test("de trackrecordvorm compileert, aanwezig en null", () => {
  const aanwezig: Trackrecord = {
    grafiek: {
      reeksen: [
        { naam: "gemeten", kleur: "warmgrijs", punten: [{ x: "ma", y: 1 }] },
        { naam: "voorspeld", kleur: "bordeaux", punten: [{ x: "ma", y: 2 }] },
      ],
      y_as: { ticks: [{ y: 0, label: "€ 0" }] },
    },
    dagen: 14,
    wape: "10.0",
    van: "2026-07-29",
    tot: "2026-08-11",
  };
  // Null is de andere helft van het contract: geen trackrecord, reden in
  // onbeschikbaar. En wape mag los daarvan null zijn.
  const afwezig: Trackrecord | null = null;
  const zonderWape: Trackrecord = { ...aanwezig, wape: null };
  assert.equal(aanwezig.grafiek.reeksen.length, 2);
  assert.equal(afwezig, null);
  assert.equal(zonderWape.wape, null);
});
