/**
 * De dodemansknop aan de UI-kant (lib/syncstand.ts).
 *
 * Wat hier vastligt is gedrag, geen implementatie: dat de bestandsroute deze
 * vraag helemaal niet stelt, dat een onbereikbare of onbekende database het
 * scherm niet omvergooit, en dat elk `geval` dat migratie 010 kan teruggeven
 * een zin heeft in beide talen. Dat laatste is de test die er het meest toe
 * doet — een nieuw geval in SQL zonder zin in het woordenboek zou op het
 * scherm een kale machinesleutel opleveren, en precies dat is O12.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

import { laadSyncStand, syncInVoettekst } from "../lib/syncstand";
import { maakT, TALEN } from "../lib/taal";

/** De gevallen zoals db/migraties/010_syncstand.sql ze noemt. */
const GEVALLEN = [
  "nooit", "vers", "achter", "oud", "gefaald", "loopt", "gestrand",
] as const;

const DB_OMGEVING = {
  CONTRACT_BRON: "db",
  NEXT_PUBLIC_SUPABASE_URL: "https://voorbeeld.supabase.co",
  SUPABASE_SECRET_KEY: "verzonnen-sleutel",
};

/** Vervangt fetch voor de duur van één test en zet hem daarna terug. */
async function metFetch<T>(
  nep: typeof globalThis.fetch,
  doe: () => Promise<T>,
): Promise<T> {
  const echt = globalThis.fetch;
  globalThis.fetch = nep;
  try {
    return await doe();
  } finally {
    globalThis.fetch = echt;
  }
}

const antwoord = (lichaam: unknown, ok = true) =>
  ({ ok, json: async () => lichaam }) as Response;

test("op de bestandsroute bestaat deze vraag niet", async () => {
  // En dan wordt er ook niets gevraagd: geen database, geen sync, niets om
  // over te waken. Een fetch hier zou al een fout zijn.
  const uit = await metFetch(
    () => {
      throw new Error("er hoort niets gevraagd te worden");
    },
    () => laadSyncStand({ CONTRACT_BRON: "bestand" }),
  );
  assert.equal(uit, null);
});

test("een geldige stand komt er onveranderd uit", async () => {
  const uit = await metFetch(
    async () =>
      antwoord({
        geval: "achter",
        oordeel: "let_op",
        geslaagd_gestart_op: "2026-08-17T01:42:00+00:00",
        laatste_melding: null,
      }),
    () => laadSyncStand(DB_OMGEVING),
  );
  assert.deepEqual(uit, {
    geval: "achter",
    oordeel: "let_op",
    geslaagd_gestart_op: "2026-08-17T01:42:00+00:00",
    laatste_melding: null,
  });
});

test("een onbereikbare database gooit het scherm niet om", async () => {
  // Anders dan bij het contract: valt dít weg, dan blijven alle cijfers staan
  // en ontbreekt alleen het toezicht erop. Een heel scherm laten omvallen
  // omdat de bewaker onbereikbaar was, is het middel erger dan de kwaal.
  const stuk = await metFetch(
    async () => {
      throw new Error("netwerk weg");
    },
    () => laadSyncStand(DB_OMGEVING),
  );
  assert.equal(stuk, null);

  const vierhonderd = await metFetch(
    async () => antwoord({}, false),
    () => laadSyncStand(DB_OMGEVING),
  );
  assert.equal(vierhonderd, null);
});

test("een onbekend geval wordt niet getoond", async () => {
  // Een nieuwere migratie met een achtste geval hoort geen kale
  // machinesleutel op het scherm te zetten; zwijgen is dan beter.
  const uit = await metFetch(
    async () => antwoord({ geval: "iets_nieuws", oordeel: "goed" }),
    () => laadSyncStand(DB_OMGEVING),
  );
  assert.equal(uit, null);
});

test("de voettekst zwijgt bij goed en spreekt bij de rest", () => {
  assert.equal(syncInVoettekst(null), false);
  const stand = (oordeel: string) => ({
    geval: "vers" as const,
    oordeel,
    geslaagd_gestart_op: null,
    laatste_melding: null,
  });
  assert.equal(syncInVoettekst(stand("goed")), false);
  assert.equal(syncInVoettekst(stand("let_op")), true);
  assert.equal(syncInVoettekst(stand("fout")), true);
});

test("elk geval uit migratie 010 heeft een zin in beide talen", () => {
  for (const taal of TALEN) {
    const t = maakT(taal);
    for (const geval of GEVALLEN) {
      const zin = t(`sync.${geval}`, { moment: "17 augustus" });
      assert.ok(
        zin && zin !== `sync.${geval}`,
        `sync.${geval} ontbreekt in het woordenboek (${taal})`,
      );
      assert.ok(
        !zin.includes("{moment}"),
        `sync.${geval} laat een invulgat staan (${taal})`,
      );
    }
  }
});

test("de gevallen hier lopen gelijk met de migratie", () => {
  // Dezelfde afspraak als tussen SCHERMEN en het Scherm-type: wie in SQL een
  // geval toevoegt, hoort het gesprek over de zin erbij te krijgen.
  const sql = readFileSync(
    path.join(import.meta.dirname, "..", "..", "db", "migraties",
              "010_syncstand.sql"),
    "utf-8",
  );
  for (const geval of GEVALLEN) {
    assert.ok(
      sql.includes(`'${geval}'`),
      `migratie 010 kent het geval "${geval}" niet meer`,
    );
  }
});
