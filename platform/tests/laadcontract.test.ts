import assert from "node:assert/strict";
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";

/**
 * laadWinkels() en het verschil tussen "er is nog geen index" en "de index is
 * stuk". Wat hier vastligt: alleen op de bestandsroute en alleen bij ENOENT
 * is een lege index het juiste antwoord (de beginstand vóór de eerste
 * contractbouw met winkelconfig); elke andere fout — en élke fout op de
 * databaseroute — werpt. Een gesmoorde fout liet de winkelkiezer stil
 * verdwijnen, waarna elk scherm het totaal toonde onder de naam van een
 * gekozen winkel (zie het doc-commentaar bij laadContract).
 */

// CONTRACT_DIR in laadContract.ts wordt bij het laden van de module uit
// process.cwd() berekend, en de echte contractmap van dit project bevat een
// winkels.json. Om de beginstand te kunnen testen verhuist dit bestand dus
// éérst naar een lege map, en importeert de module pas daarna. Elk testbestand
// draait onder node --test in zijn eigen proces, dus deze chdir raakt geen
// andere tests.
const wortel = await mkdtemp(path.join(tmpdir(), "laadcontract-test-"));
process.chdir(wortel);

const { laadWinkels } = await import("../lib/laadContract");

/**
 * Zet env-variabelen voor één test en geef de hersteller terug. Waar
 * contract-bron.test.ts de omgeving als argument kan meegeven, leest
 * laadWinkels process.env zelf — dus hier: zetten, en in finally terugzetten.
 */
function metOmgeving(waarden: Record<string, string | undefined>): () => void {
  const oud = new Map(Object.keys(waarden).map((k) => [k, process.env[k]]));
  for (const [k, w] of Object.entries(waarden)) {
    if (w === undefined) delete process.env[k];
    else process.env[k] = w;
  }
  return () => {
    for (const [k, w] of oud) {
      if (w === undefined) delete process.env[k];
      else process.env[k] = w;
    }
  };
}

test("bestandsroute zonder winkels.json: de lege beginstand, geen fout", async () => {
  const herstel = metOmgeving({ CONTRACT_BRON: undefined });
  try {
    assert.deepEqual(await laadWinkels(), {
      winkels: [],
      niet_toegewezen: [],
      melding: null,
      overgeslagen: [],
    });
  } finally {
    herstel();
  }
});

test("databaseroute zonder serveromgeving: een fout, geen stille lege index", async () => {
  // Op de databaseroute betekent een fout: verkeerde sleutel, netwerk weg of
  // sync niet gedraaid. Stil LEEG teruggeven zou dat verzwijgen als "er is
  // gewoon geen winkelindeling".
  const herstel = metOmgeving({
    CONTRACT_BRON: "db",
    NEXT_PUBLIC_SUPABASE_URL: undefined,
    SUPABASE_SECRET_KEY: undefined,
  });
  try {
    await assert.rejects(laadWinkels(), (fout: Error) => {
      assert.match(fout.message, /winkelindex/);
      assert.match(fout.message, /nachtelijke sync/);
      // De oorzaak reist mee, met de namen van de ontbrekende variabelen.
      assert.match(
        (fout.cause as Error).message,
        /NEXT_PUBLIC_SUPABASE_URL en SUPABASE_SECRET_KEY/,
      );
      return true;
    });
  } finally {
    herstel();
  }
});

test("bestandsroute met een kapot winkels.json: werpen, dit is geen beginstand", async () => {
  // Alleen ENOENT is de normale beginstand; een bestand dat er wél staat maar
  // niet parseert, is een echte fout en moet als fout verschijnen.
  const herstel = metOmgeving({ CONTRACT_BRON: undefined });
  await mkdir(path.join(wortel, "contract"), { recursive: true });
  await writeFile(
    path.join(wortel, "contract", "winkels.json"),
    "{ dit is geen json",
    "utf-8",
  );
  try {
    await assert.rejects(laadWinkels(), (fout: Error) => {
      assert.match(fout.message, /winkelindex/);
      assert.match(fout.message, /make contract/);
      return true;
    });
  } finally {
    herstel();
  }
});
