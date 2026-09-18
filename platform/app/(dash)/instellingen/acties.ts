"use server";

import { execFile } from "node:child_process";
import { mkdir, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";

import { COOKIE, lees } from "@/lib/auth";
import { contractBron } from "@/lib/contract-bron";
import { valideerKostenmodel } from "@/lib/kostenmodel";
import { bewaarInDatabase } from "@/lib/kostenmodel-db";
import { laadContract } from "@/lib/laadContract";
import type { MargeData } from "@/lib/contract";
import type { Sleutel } from "@/lib/taal";

const uitvoeren = promisify(execFile);

/**
 * De uitkomst draagt SLEUTELS en geen tekst, plus eventuele invulwaarden —
 * hetzelfde patroon als het aanmelden (login/acties.ts): de actie weet niet
 * welke taal de lezer gekozen heeft, het formulier vertaalt bij het tonen.
 */
export type KostenUitkomst = {
  ok?: Sleutel;
  fout?: Sleutel;
  waarden?: Record<string, string>;
};

/** De repowortel: de dev-server draait in platform/, de data ligt erboven. */
function repo(): string {
  return path.resolve(process.cwd(), "..");
}

/**
 * Er draait hoogstens één herberekening tegelijk. Twee beheerders (of één
 * dubbelklik) die allebei een contractbouw starten, zouden door elkaar in
 * platform/contract/ schrijven; de tweede wacht gewoon zijn beurt af.
 */
let herrekeningBezig = false;

/**
 * De groepen die werkelijk bestaan, uit het marge-antwoord van het contract.
 * Het formulier stuurt groepsnamen mee, maar een formulier is invoer van
 * buiten: alleen namen die de berekeningslaag zelf al kent, worden bewaard.
 * Bewust het totaal en niet de gekozen winkel: de kostinvoer geldt voor het
 * hele assortiment, dus de volledige groepenlijst is hier de waarheid.
 */
async function bekendeGroepen(): Promise<Set<string> | null> {
  try {
    const antwoord = await laadContract<MargeData>("marge", { totaal: true });
    const rijen =
      "per_groep" in antwoord.data ? antwoord.data.per_groep : [];
    return new Set(rijen.map((r) => r.groep));
  } catch (fout) {
    console.error("bekendeGroepen: contract onleesbaar", fout);
    return null;
  }
}

/**
 * Bewaart het kostenmodel (criteria + waarden per groep). Het rekenwerk blijft
 * in de berekeningslaag (harde regel 4): dit schrijft alleen invoer.
 *
 * TWEE ROUTES, ÉÉN BRON. Waar het platform het contract leest, schrijft het ook
 * de invoer — anders bestaan er twee kostenmodellen die kunnen uiteenlopen.
 *
 *   CONTRACT_BRON leeg/bestand : data/config/kostenmodel.json, atomair
 *                                (tmp + rename), plus meteen een herberekening
 *                                zodat Margebewaking de nieuwe cijfers toont.
 *   CONTRACT_BRON=db           : kosten_criterium/kosten_waarde via de functie
 *                                uit migratie 009 (één transactie). Herrekenen
 *                                kan hier niet: op de gehoste omgeving staat
 *                                geen Python en geen canonieke data. De cijfers
 *                                volgen bij de volgende contractbouw, en de
 *                                meldingssleutel zegt dat ook — beloven dat het
 *                                margescherm nú bijstaat, zou liegen.
 */
export async function bewaarKostenmodel(
  _vorige: KostenUitkomst,
  formulier: FormData,
): Promise<KostenUitkomst> {
  const sessie = await lees((await cookies()).get(COOKIE)?.value);
  if (!sessie) {
    return { fout: "kosten.sessieVerlopen" };
  }
  if (sessie.rol !== "beheerder") {
    return { fout: "kosten.alleenBeheerder" };
  }

  const groepen = await bekendeGroepen();
  if (groepen === null) {
    // Herstel voor de beheerder van de omgeving: `make contract` draaien.
    return { fout: "kosten.contractOnleesbaar" };
  }

  // Criteria: velden criterium:<id>:naam en criterium:<id>:omschrijving.
  // Kosten: velden kost:<id>:<groep-url-encoded>. Het id is de stabiele
  // client-sleutel van het formulier; hier wordt het terugvertaald naar de
  // criteriumnaam, zodat hernoemen de ingevulde cellen meeneemt.
  const criteriaRuw = new Map<string, { naam: string; omschrijving: string }>();
  const kostenRuw: { groep: string; id: string; waarde: string }[] = [];
  for (const [sleutel, waarde] of formulier.entries()) {
    if (typeof waarde !== "string") continue;
    const crit = /^criterium:(\d+):(naam|omschrijving)$/.exec(sleutel);
    if (crit) {
      const rij = criteriaRuw.get(crit[1]) ?? { naam: "", omschrijving: "" };
      rij[crit[2] as "naam" | "omschrijving"] = waarde;
      criteriaRuw.set(crit[1], rij);
      continue;
    }
    const kost = /^kost:(\d+):(.*)$/.exec(sleutel);
    if (kost) {
      const groep = decodeURIComponent(kost[2]);
      if (!groepen.has(groep)) continue; // onbekende groep: niet bewaren
      kostenRuw.push({ groep, id: kost[1], waarde });
    }
  }
  const criteriaInvoer = [...criteriaRuw.entries()]
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([, rij]) => rij);
  const kostenInvoer = kostenRuw.flatMap(({ groep, id, waarde }) => {
    const criterium = criteriaRuw.get(id)?.naam ?? "";
    return criterium === "" ? [] : [{ groep, criterium, waarde }];
  });

  const { criteria, waarden, fouten } = valideerKostenmodel(
    criteriaInvoer,
    kostenInvoer,
  );
  if (fouten.length > 0) {
    // Eén fout per keer: de eerste. Wie meer fouten heeft, ziet na herstel
    // vanzelf de volgende — een sleutel draagt maar één zin.
    return { fout: fouten[0].sleutel, waarden: fouten[0].waarden };
  }
  if (criteria.length === 0 && Object.keys(waarden).length > 0) {
    return { fout: "kosten.geenCriterium" };
  }

  const groepenMetKosten = Object.keys(waarden).length;

  // De gehoste route: één PostgREST-verzoek naar de functie van migratie 009,
  // dus één transactie. Geen bestand, geen herberekening — beide bestaan daar
  // niet, en doen alsof zou precies de stille no-op zijn die het formulier tot
  // vandaag eerlijk weigerde.
  if (contractBron(process.env) === "db") {
    const reden = await bewaarInDatabase(criteria, waarden, sessie.gebruiker);
    if (reden !== null) {
      // De reden hoort in de log en niet op het scherm: een afwijzing van
      // Postgres kan de gegevens van de mislukte rij dragen.
      console.error("bewaarKostenmodel: bewaar_kostenmodel weigerde", reden);
      return { fout: "kosten.dbOpslaanMislukt" };
    }
    revalidatePath("/marge");
    revalidatePath("/instellingen");
    return groepenMetKosten === 0
      ? { ok: "kosten.leeggemaaktDb" }
      : {
          ok: "kosten.bewaardDb",
          waarden: {
            criteria: String(criteria.length),
            groepen: String(groepenMetKosten),
          },
        };
  }

  const map = path.join(repo(), "data", "config");
  await mkdir(map, { recursive: true });
  const inhoud = {
    versie: 2,
    ingevuld_door: sessie.gebruiker,
    ingevuld_op: new Date().toISOString(),
    criteria,
    waarden,
  };
  // Atomair: een nachtelijke of gelijktijdige lezer ziet nooit een half bestand.
  const doel = path.join(map, "kostenmodel.json");
  const tmp = doel + ".tmp";
  await writeFile(tmp, JSON.stringify(inhoud, null, 2) + "\n", "utf-8");
  await rename(tmp, doel);

  if (herrekeningBezig) {
    // Handmatig herstel voor wie niet wil wachten: `make contract`.
    return { fout: "kosten.herrekeningLoopt" };
  }
  herrekeningBezig = true;
  try {
    await uitvoeren(
      path.join(repo(), ".venv", "bin", "python"),
      [path.join(repo(), "scripts", "contract_bouw.py")],
      { cwd: repo(), timeout: 180_000 },
    );
  } catch (fout) {
    console.error("contract_bouw.py faalde na kostenmodel-opslag", fout);
    // Herstel voor de beheerder van de omgeving: `make contract` draaien en
    // de uitvoer lezen; die boodschap hoort niet bij de lezer van het scherm.
    return { fout: "kosten.herrekenenMislukt" };
  } finally {
    herrekeningBezig = false;
  }

  revalidatePath("/marge");
  revalidatePath("/instellingen");

  // Kale aantallen als invulwaarden; enkelvoud of meervoud kiest het
  // formulier bij het tonen (presentatie, geen serverzaak).
  return groepenMetKosten === 0
    ? { ok: "kosten.leeggemaakt" }
    : {
        ok: "kosten.bewaard",
        waarden: {
          criteria: String(criteria.length),
          groepen: String(groepenMetKosten),
        },
      };
}
