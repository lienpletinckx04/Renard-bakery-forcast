/**
 * Bronwacht: verdwijnt er iets stil van de afdruk?
 *
 * WAAROM DEZE TEST BESTAAT. Het rapport is sinds 18 augustus 2026 geen gebouwd
 * bestand meer maar een weergave: `/rapport` zet de gekozen schermen achter
 * elkaar en de browser maakt de PDF. Dat is één tekening voor scherm en papier,
 * en dat is de winst — maar het legt de afdruk wel vast in twee dingen die
 * niemand ziet falen: de klasse `uitklap-kop` op een <summary>, en de
 * afdrukregels in `globals.css` die op die klasse mikken.
 *
 * Op 19 augustus 2026 bleek dat drie keer misgegaan, en alle drie stil:
 *
 *  1. De drill-downregels van Producten en Prognose droegen de klasse niet. In
 *     het rapport stonden daardoor negentien producttabellen zonder groepsnaam
 *     en zeven dagtabellen zonder categorie — gegevens die in de tabel eronder
 *     nergens staan.
 *  2. `Toelichting` droeg de klasse niet, en zijn <h2> zit ín de summary. "Wat
 *     hier niet staat, en waarom" verscheen op elke bladzijde als een naamloze
 *     lijst onder een haarlijn.
 *  3. De regel die de summary verbergt, was niet afgebakend tot `.rapport` en
 *     gold dus ook bij Ctrl+P op een gewoon scherm — waar niets opengezet wordt.
 *     Een dichte uitklap verloor daar zijn énige zichtbare regel.
 *
 * Geen ervan gaf een foutmelding, en geen ervan is te zien zonder een PDF te
 * maken en na te lopen. Vandaar een bronwacht: hij is goedkoop, en hij meet
 * precies wat een mens over het hoofd ziet.
 *
 * WAT ER MOET GEBEUREN ALS HIJ FAALT. Draagt de summary de kop of een cijfer
 * van het blok — een naam, een aandeel, een totaal dat verderop niet herhaald
 * wordt — geef hem dan `uitklap-kop`. Is de summary alleen een klikregel
 * ("Meer info") waarvan de inhoud eronder hangt, zet hem dan hieronder in
 * KLIKREGELS met de reden erbij.
 */

import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const WORTEL = path.join(import.meta.dirname, "..");
const MAPPEN = ["app", "components"];

/**
 * Summary's die op papier wél mogen verdwijnen, met de reden. Voorwaarde voor
 * elke regel hier: alles wat de summary zegt, staat open en bloot in de inhoud
 * eronder of is schermchroom dat op papier niets te zoeken heeft.
 */
const KLIKREGELS = new Map([
  [
    "components/MeerInfo.tsx",
    // De summary is het woord "Meer info" en niets meer; de hele inhoud hangt
    // eronder en staat in het rapport open. Op papier is de klikregel dus
    // precies de ruis waarvoor de afdrukregel bedoeld is.
    "de klikregel draagt alleen een label, de inhoud hangt eronder",
  ],
  [
    "components/RapportMenu.tsx",
    // Het keuzemenu van het rapport is schermchroom: het kiest wát er afgedrukt
    // wordt en hoort zelf niet op de afdruk. Het staat al in `niet-afdrukken`.
    "schermchroom: het menu kiest de afdruk en staat er zelf niet op",
  ],
]);

/** Elk `.tsx`-bestand onder een map, recursief. */
function bronBestanden(map: string): string[] {
  const uit: string[] = [];
  for (const naam of readdirSync(map)) {
    const pad = path.join(map, naam);
    if (statSync(pad).isDirectory()) {
      uit.push(...bronBestanden(pad));
      continue;
    }
    if (naam.endsWith(".tsx")) uit.push(pad);
  }
  return uit;
}

/**
 * De classname van elke `<summary`-tag in een bron. Bewust ruw: de wacht hoeft
 * geen JSX te ontleden, hij hoeft alleen te zien of het woord `uitklap-kop`
 * binnen de openingstag staat.
 *
 * Commentaar gaat er eerst uit. De componenten van dit platform leggen in hun
 * kop uit wat ze doen, en die uitleg noemt `<summary>` bij naam — de eerste
 * versie van deze wacht viel prompt over de kop van `KaartUitklap`, die de
 * afdrukregel beschrijft in het bestand dat hem correct toepast.
 */
function summaryTags(bron: string): string[] {
  const zonderCommentaar = bron
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
  return [...zonderCommentaar.matchAll(/<summary\b[^>]*>/g)].map((m) => m[0]);
}

test("elke summary die een kop draagt, overleeft de afdruk", () => {
  const overtredingen: string[] = [];

  for (const map of MAPPEN) {
    for (const bestand of bronBestanden(path.join(WORTEL, map))) {
      const relatief = path.relative(WORTEL, bestand);
      const tags = summaryTags(readFileSync(bestand, "utf-8"));
      if (tags.length === 0) continue;
      const vrijgesteld = KLIKREGELS.has(relatief);
      for (const tag of tags) {
        const heeftHaakje = tag.includes("uitklap-kop");
        if (heeftHaakje && vrijgesteld) {
          overtredingen.push(
            `${relatief}: staat in KLIKREGELS maar draagt uitklap-kop — ` +
              "één van beide klopt niet",
          );
        }
        if (!heeftHaakje && !vrijgesteld) {
          overtredingen.push(
            `${relatief}: <summary> zonder uitklap-kop. Draagt hij de kop of ` +
              "een cijfer van het blok, geef hem de klasse; is hij alleen een " +
              "klikregel, zet het bestand in KLIKREGELS met de reden",
          );
        }
      }
    }
  }

  assert.deepEqual(overtredingen, [], overtredingen.join("\n  "));
});

test("de afdrukregel verbergt alleen binnen het rapport", () => {
  const css = readFileSync(path.join(WORTEL, "app/globals.css"), "utf-8");

  // De regel hoort afgebakend te zijn tot `.rapport`. Buiten het rapport zet
  // niemand de uitklappers open (dat doet Rapportknoppen, en die draait alleen
  // daar), dus daar is de summary geen ruis maar het bewijs dat er iets onder
  // zit — precies wat harde regel 8 zichtbaar wil houden.
  assert.match(
    css,
    /\.rapport details > summary:not\(\.uitklap-kop\)/,
    "De afdrukregel die een <summary> verbergt, hoort afgebakend te zijn tot " +
      ".rapport. Zonder die afbakening verliest een gewoon scherm bij Ctrl+P " +
      "de klikregel van elke dichte uitklap, en daarmee het blok zelf.",
  );
  assert.doesNotMatch(
    css,
    /^\s{2}details > summary:not\(\.uitklap-kop\)/m,
    "Er staat nog een ongebonden variant van de afdrukregel in globals.css.",
  );
});
