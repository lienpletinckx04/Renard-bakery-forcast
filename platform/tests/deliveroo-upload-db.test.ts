import assert from "node:assert/strict";
import { test } from "node:test";

import {
  AL_GELADEN,
  bewaarUploadInDatabase,
  bewaarUploadVerzoek,
  laadUploads,
  LIMIET,
  type NieuweUpload,
  RPC,
} from "../lib/deliveroo-upload-db";

/**
 * De schrijf- en leesroute van de bronbestanden op de gehoste omgeving, naar
 * het model van tests/sluitingsdagen-db.test.ts. Wat hier vastligt, valt met
 * het oog niet te controleren: dat het ÉÉN verzoek is (dus één transactie, dus
 * alles of niets), dat het naar de functie van migratie 015 gaat en niet naar
 * de tabel, dat de body exact de vorm draagt die de rpc verwacht — en dat de
 * lijst de kolom `inhoud` niet meevraagt.
 */

const OMGEVING = {
  CONTRACT_BRON: "db",
  NEXT_PUBLIC_SUPABASE_URL: "https://ref.supabase.co",
  SUPABASE_SECRET_KEY: "sb_secret_x",
};

const UPLOAD: NieuweUpload = {
  bron: "deliveroo",
  bestandsnaam: "export-augustus.csv",
  mediatype: "text/csv",
  sha256: "a".repeat(64),
  inhoud_base64: "Zm9v",
};

/** Vervangt fetch voor de duur van één aanroep en houdt de verzoeken bij. */
async function metGevangenFetch<R>(
  antwoord: () => Response,
  werk: () => Promise<R>,
): Promise<{ uit: R; verzoeken: { url: string; init?: RequestInit }[] }> {
  const echt = globalThis.fetch;
  const verzoeken: { url: string; init?: RequestInit }[] = [];
  globalThis.fetch = (async (invoer: string | URL, init?: RequestInit) => {
    verzoeken.push({ url: String(invoer), init });
    return antwoord();
  }) as typeof globalThis.fetch;
  try {
    return { uit: await werk(), verzoeken };
  } finally {
    globalThis.fetch = echt;
  }
}

test("het verzoek gaat naar de functie van migratie 015, niet naar de tabel", () => {
  const { url, headers } = bewaarUploadVerzoek(UPLOAD, "lien", OMGEVING);
  const u = new URL(url);
  assert.equal(u.origin, "https://ref.supabase.co");
  // Rechtstreeks in bron_upload schrijven zou de rol achter de secret key
  // insert-recht op de tabel geven, en dat heeft ze niet (migratie 015).
  assert.equal(u.pathname, `/rest/v1/rpc/${RPC}`);
  assert.equal(headers.apikey, "sb_secret_x");
  assert.equal(headers.Authorization, "Bearer sb_secret_x");
  assert.equal(headers["Content-Type"], "application/json");
});

test("de body draagt het bestand met zijn kenmerken, plus wie het opgeladen heeft", () => {
  const { body } = bewaarUploadVerzoek(UPLOAD, "lien", OMGEVING);
  // De sleutels upload en door zijn de parameternamen van de SQL-functie — de
  // PostgREST-conventie, precies zoals bij bewaar_sluitingskalender.
  assert.deepEqual(JSON.parse(body), {
    upload: {
      bron: "deliveroo",
      bestandsnaam: "export-augustus.csv",
      mediatype: "text/csv",
      sha256: "a".repeat(64),
      inhoud_base64: "Zm9v",
    },
    door: "lien",
  });
});

test("een projecturl met slotstreep levert geen dubbele schuine streep", () => {
  const { url } = bewaarUploadVerzoek(UPLOAD, "lien", {
    ...OMGEVING,
    NEXT_PUBLIC_SUPABASE_URL: "https://ref.supabase.co/",
  });
  assert.equal(new URL(url).pathname, `/rest/v1/rpc/${RPC}`);
});

test("zonder serveromgeving werpt het verzoek leesbaar", () => {
  assert.throws(
    () => bewaarUploadVerzoek(UPLOAD, "lien", {}),
    /NEXT_PUBLIC_SUPABASE_URL en SUPABASE_SECRET_KEY/,
  );
});

test("bewaren is één verzoek, en een nieuwe rij levert geen melding op", async () => {
  const { uit, verzoeken } = await metGevangenFetch(
    () => new Response("1", { status: 200 }),
    () => bewaarUploadInDatabase(UPLOAD, "lien", OMGEVING),
  );
  assert.equal(verzoeken.length, 1);
  assert.equal(new URL(verzoeken[0].url).pathname, `/rest/v1/rpc/${RPC}`);
  assert.equal(verzoeken[0].init?.method, "POST");
  assert.equal(uit, null);
});

test("een rpc die 0 teruggeeft, meldt dat het bestand er al stond", async () => {
  // Geen storing: de vingerafdruk was er al. De aanroeper mag dat niet als
  // fout in de log gooien en moet het wél aan de beheerder zeggen.
  const { uit } = await metGevangenFetch(
    () => new Response("0", { status: 200 }),
    () => bewaarUploadInDatabase(UPLOAD, "lien", OMGEVING),
  );
  assert.equal(uit, AL_GELADEN);
});

test("een weigering van Postgres komt terug als reden voor de log", async () => {
  const { uit } = await metGevangenFetch(
    () => new Response("iets ging mis", { status: 400, statusText: "Bad Request" }),
    () => bewaarUploadInDatabase(UPLOAD, "lien", OMGEVING),
  );
  assert.match(String(uit), /^400 /);
  assert.notEqual(uit, AL_GELADEN);
});

test("de lijst vraagt de kolom inhoud niet op", async () => {
  const { uit, verzoeken } = await metGevangenFetch(
    () => Response.json([]),
    () => laadUploads(OMGEVING),
  );
  assert.deepEqual(uit, []);
  assert.equal(verzoeken.length, 1);
  const u = new URL(verzoeken[0].url);
  assert.equal(u.pathname, "/rest/v1/bron_upload");
  const select = u.searchParams.get("select") ?? "";
  const kolommen = select.split(",");
  // `inhoud` is het bestand zelf: tot tien megabyte per rij, en op het scherm
  // heeft het niets te zoeken. Een select met `*` zou een lijst van vijftig
  // bestanden een lezing van honderden megabytes maken.
  assert.ok(!kolommen.includes("inhoud"));
  assert.ok(kolommen.includes("bestandsnaam"));
  assert.ok(kolommen.includes("verwerkt_status"));
  assert.equal(u.searchParams.get("limit"), String(LIMIET));
  assert.equal(u.searchParams.get("order"), "geladen_op.desc");
});

test("een rij die het schema niet draagt, maakt de hele lezing null", async () => {
  // Zwijgen is eerlijker dan een halve lijst: een opgeladen bestand dat
  // ontbreekt, laat de beheerder denken dat het niet aangekomen is.
  const { uit } = await metGevangenFetch(
    () => Response.json([{ upload_id: 1, bestandsnaam: 7, bytes: 3, geladen_op: "x" }]),
    () => laadUploads(OMGEVING),
  );
  assert.equal(uit, null);
});

test("laadUploads is null op de bestandsroute: de vraag bestaat daar niet", async () => {
  // Zonder CONTRACT_BRON=db is er geen database om uit te lezen; null en geen
  // lege lijst, want leeg zou "er is nog niets opgeladen" beweren.
  assert.equal(await laadUploads({ CONTRACT_BRON: "bestand" }), null);
});
