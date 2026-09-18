/**
 * Validatie van het sluitingsdagen-formulier, los van Next zodat het testbaar
 * is met de kale node-testrunner — zelfde opzet als lib/kostenmodel.ts.
 *
 * De vorm volgt migratie 011/012 en bakkerij/sluitingskalender.py: uitspraken
 * per dag (toestand `open` of `dicht`; onbekend is het ontbreken van een rij)
 * plus hoogstens één wekelijkse sluitingsregel. Dit is de eerste poort, niet
 * de enige: de functie bewaar_sluitingskalender (012) en de checks van 011
 * toetsen aan de andere kant opnieuw.
 *
 * Fouten zijn SLEUTELS uit het woordenboek plus invulwaarden, geen zinnen:
 * deze module draait in een server-actie, en die kent de taal van de lezer
 * niet — het formulier vertaalt bij het tonen.
 */

import type { Sleutel } from "./taal";

/** Spiegelt bakkerij/sluitingsdagen.py MAX_DAGEN_PER_PERIODE. */
export const MAX_PERIODE_DAGEN = 120;
/** Spiegelt de vangrail van 1000 dagen in migratie 012. */
export const MAX_DAGEN = 1000;
/** Spiegelt bakkerij/sluitingsdagen.py REDEN_MAX. */
export const REDEN_MAX = 120;

export type Toestand = "open" | "dicht";

/** Eén uitspraak zoals de rpc hem verwacht (en de tabel hem draagt). */
export type DagRij = {
  /** ISO-datum. */
  datum: string;
  toestand: Toestand;
  reden: string;
  bron: "feestdag" | "periode" | "bestand";
};

export type RegelRij = {
  /** 0 = maandag, zoals overal in dit project. */
  weekdag: number;
  vanaf: string;
  tot: string | null;
  reden: string;
};

export type SluitingenFout = {
  sleutel: Sleutel;
  waarden: Record<string, string>;
};

export type SluitingenValidatie = {
  dagen: DagRij[];
  regels: RegelRij[];
  fouten: SluitingenFout[];
};

/** "2026-12-25" en niets anders; Date.parse slikt te veel. */
function geldigeDatum(tekst: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(tekst)) return false;
  const d = new Date(`${tekst}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === tekst;
}

/** Kalenderdagen tussen twee ISO-datums, inclusief beide uiteinden. */
function dagenTussen(van: string, tot: string): string[] {
  const uit: string[] = [];
  const d = new Date(`${van}T00:00:00Z`);
  const eind = new Date(`${tot}T00:00:00Z`);
  while (d <= eind) {
    uit.push(d.toISOString().slice(0, 10));
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return uit;
}

function nettoReden(ruw: string): string {
  return ruw.replace(/\s+/g, " ").trim();
}

/**
 * Van formulierinvoer naar rpc-rijen.
 *
 * `kandidaten` zijn de feestdagen uit het contract, elk met de toestand die
 * de beheerder koos ("open" | "dicht" | "onbekend"); alleen open en dicht
 * worden een rij — onbekend ís het ontbreken van een uitspraak. `periodes`
 * zijn de eigen sluitingsperiodes (jaarlijkse sluiting, verbouwing), altijd
 * dicht, hier uitgerold naar losse dagen zoals de tabel ze draagt. `regel`
 * is de vaste wekelijkse sluitingsdag, of null.
 *
 * Botst een periode met een bevestigd-open feestdag, dan is dat een echte
 * tegenspraak en een fout — de beheerder moet kiezen. Botst ze met een
 * bevestigd-dichte feestdag, dan zeggen twee invoeren hetzelfde en wint de
 * feestdag (die draagt de naam als reden).
 */
export function valideerSluitingen(
  kandidaten: { datum: string; naam: string; toestand: string }[],
  periodes: { van: string; tot: string; reden: string }[],
  regel: { weekdag: string; vanaf: string; tot: string } | null,
): SluitingenValidatie {
  const fouten: SluitingenFout[] = [];
  const perDag = new Map<string, DagRij>();

  for (const k of kandidaten) {
    if (k.toestand !== "open" && k.toestand !== "dicht") continue;
    if (!geldigeDatum(k.datum)) {
      fouten.push({ sleutel: "sluit.datumOngeldig", waarden: { datum: k.datum } });
      continue;
    }
    perDag.set(k.datum, {
      datum: k.datum,
      toestand: k.toestand,
      reden: nettoReden(k.naam).slice(0, REDEN_MAX),
      bron: "feestdag",
    });
  }

  for (const p of periodes) {
    const van = p.van.trim();
    const tot = p.tot.trim() || van;
    const reden = nettoReden(p.reden);
    if (van === "" && p.tot.trim() === "" && reden === "") continue; // lege rij
    if (!geldigeDatum(van) || !geldigeDatum(tot)) {
      fouten.push({
        sleutel: "sluit.datumOngeldig",
        waarden: { datum: van || tot },
      });
      continue;
    }
    if (tot < van) {
      fouten.push({ sleutel: "sluit.totVoorVan", waarden: { van, tot } });
      continue;
    }
    if (reden.length > REDEN_MAX) {
      fouten.push({
        sleutel: "sluit.redenTeLang",
        waarden: { max: String(REDEN_MAX) },
      });
      continue;
    }
    const dagen = dagenTussen(van, tot);
    if (dagen.length > MAX_PERIODE_DAGEN) {
      fouten.push({
        sleutel: "sluit.periodeTeLang",
        waarden: {
          van,
          tot,
          dagen: String(dagen.length),
          max: String(MAX_PERIODE_DAGEN),
        },
      });
      continue;
    }
    for (const dag of dagen) {
      const bestaand = perDag.get(dag);
      if (bestaand?.toestand === "open") {
        fouten.push({
          sleutel: "sluit.openDichtConflict",
          waarden: { datum: dag },
        });
        continue;
      }
      if (bestaand !== undefined) continue; // twee keer dicht: de feestdag wint
      perDag.set(dag, { datum: dag, toestand: "dicht", reden, bron: "periode" });
    }
  }

  const regels: RegelRij[] = [];
  if (regel !== null && regel.weekdag.trim() !== "") {
    const weekdag = Number(regel.weekdag);
    const vanaf = regel.vanaf.trim();
    const tot = regel.tot.trim();
    if (!Number.isInteger(weekdag) || weekdag < 0 || weekdag > 6) {
      fouten.push({
        sleutel: "sluit.weekdagOngeldig",
        waarden: { weekdag: regel.weekdag },
      });
    } else if (vanaf === "" || !geldigeDatum(vanaf)) {
      fouten.push({ sleutel: "sluit.vanafOntbreekt", waarden: {} });
    } else if (tot !== "" && !geldigeDatum(tot)) {
      fouten.push({ sleutel: "sluit.datumOngeldig", waarden: { datum: tot } });
    } else if (tot !== "" && tot < vanaf) {
      fouten.push({ sleutel: "sluit.totVoorVan", waarden: { van: vanaf, tot } });
    } else {
      regels.push({ weekdag, vanaf, tot: tot === "" ? null : tot, reden: "" });
    }
  }

  const dagen = [...perDag.values()].sort((a, b) =>
    a.datum < b.datum ? -1 : 1,
  );
  if (dagen.length > MAX_DAGEN) {
    fouten.push({
      sleutel: "sluit.teVeel",
      waarden: { aantal: String(dagen.length), max: String(MAX_DAGEN) },
    });
  }

  return { dagen, regels, fouten };
}

/**
 * Aaneengesloten dagen met dezelfde reden terug naar periodes, voor het
 * formulier: de tabel draagt losse dagen (één uitspraak per dag, zoals de
 * prognose ze leest), maar een mens denkt in "17 t/m 23 augustus". Puur
 * presentatie — er wordt niets gewogen of geteld dat een cijfer wordt.
 */
export function groepeerPeriodes(
  dagen: { datum: string; reden: string }[],
): { van: string; tot: string; reden: string }[] {
  const gesorteerd = [...dagen].sort((a, b) => (a.datum < b.datum ? -1 : 1));
  const uit: { van: string; tot: string; reden: string }[] = [];
  for (const dag of gesorteerd) {
    const vorige = uit[uit.length - 1];
    if (
      vorige !== undefined &&
      vorige.reden === dag.reden &&
      dagenTussen(vorige.tot, dag.datum).length === 2
    ) {
      vorige.tot = dag.datum;
    } else {
      uit.push({ van: dag.datum, tot: dag.datum, reden: dag.reden });
    }
  }
  return uit;
}

/**
 * De samenvoeging met wat er al in de database staat: het formulier beheert
 * de feestdagkandidaten van dit jaar, de eigen periodes en de weekregel —
 * uitspraken daarbuiten (feestdagen van vorig jaar, de eenmalige overname
 * uit het bestand) blijven staan. Zonder deze stap zou elke opslag de
 * geschiedenis wissen, want de rpc vervangt alles (één transactie).
 *
 * Botst een bewaarde dag met nieuwe invoer, dan wint de nieuwe invoer: die
 * is later en bewuster gedaan.
 */
export function voegSamen(
  bewaard: DagRij[],
  kandidaatDatums: Set<string>,
  nieuw: DagRij[],
): DagRij[] {
  const nieuweDatums = new Set(nieuw.map((d) => d.datum));
  const behouden = bewaard.filter(
    (d) =>
      !kandidaatDatums.has(d.datum) &&
      d.bron !== "periode" &&
      !nieuweDatums.has(d.datum),
  );
  return [...behouden, ...nieuw].sort((a, b) => (a.datum < b.datum ? -1 : 1));
}
