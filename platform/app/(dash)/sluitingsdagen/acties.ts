"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";

import { COOKIE, lees } from "@/lib/auth";
import { contractBron } from "@/lib/contract-bron";
import { laadContract } from "@/lib/laadContract";
import { valideerSluitingen, voegSamen } from "@/lib/sluitingsdagen";
import { bewaarInDatabase, laadSluitingen } from "@/lib/sluitingsdagen-db";
import type { SluitingsdagenData } from "@/lib/contract";
import type { Sleutel } from "@/lib/taal";

/**
 * De uitkomst draagt SLEUTELS en geen tekst, plus eventuele invulwaarden —
 * hetzelfde patroon als het kostenmodel (instellingen/acties.ts): de actie
 * kent de taal van de lezer niet, het formulier vertaalt bij het tonen.
 */
export type SluitingenUitkomst = {
  ok?: Sleutel;
  fout?: Sleutel;
  waarden?: Record<string, string>;
};

/**
 * De feestdagkandidaten uit het contract — niet uit het formulier. Een
 * formulier is invoer van buiten: alleen datums die de berekeningslaag zelf
 * als kandidaat kent, worden als feestdag-uitspraak bewaard.
 */
async function bekendeKandidaten(): Promise<Map<string, string> | null> {
  try {
    const antwoord = await laadContract<SluitingsdagenData>("sluitingsdagen", {
      totaal: true,
    });
    return new Map(antwoord.data.kandidaten.map((k) => [k.datum, k.naam]));
  } catch (fout) {
    console.error("bekendeKandidaten: contract onleesbaar", fout);
    return null;
  }
}

/**
 * Bewaart de sluitingskalender: de antwoorden op de feestdagenlijst, de eigen
 * periodes en de vaste wekelijkse sluitingsdag. Het rekenwerk blijft in de
 * berekeningslaag (harde regel 4): dit schrijft alleen invoer, en de prognose
 * ziet haar bij de eerstvolgende nachtelijke herrekening.
 *
 * ANDERS DAN HET KOSTENMODEL is er hier geen bestandsroute. De sluitingslijst
 * in git (config/sluitingsdagen.json) is sinds 19 augustus 2026 een eenmalige
 * invoer en een historisch record; een server die een bestand in een
 * git-repository herschrijft, lost precies niets op — dat bestand was het
 * probleem. Zonder database weigert de actie eerlijk.
 *
 * DE SAMENVOEGING IS DE KERN. De rpc vervangt alles (één transactie), maar
 * het formulier beheert alleen de kandidaten van dit jaar, de periodes en de
 * regel. Uitspraken daarbuiten — feestdagen van vorig jaar, de eenmalig
 * overgenomen bestandslijst — moeten blijven staan. Daarom: eerst de
 * bewaarde stand lezen, dan samenvoegen, dan alles terugschrijven. Is die
 * stand niet leesbaar, dan wordt er NIET bewaard: samenvoegen met een
 * onbekende basis zou bewaarde uitspraken wissen.
 */
export async function bewaarSluitingen(
  _vorige: SluitingenUitkomst,
  formulier: FormData,
): Promise<SluitingenUitkomst> {
  const sessie = await lees((await cookies()).get(COOKIE)?.value);
  if (!sessie) {
    return { fout: "sluit.sessieVerlopen" };
  }
  if (sessie.rol !== "beheerder") {
    return { fout: "sluit.alleenBeheerder" };
  }
  if (contractBron(process.env) !== "db") {
    return { fout: "sluit.alleenDb" };
  }

  const kandidaten = await bekendeKandidaten();
  if (kandidaten === null) {
    return { fout: "sluit.contractOnleesbaar" };
  }
  const bewaard = await laadSluitingen();
  if (bewaard === null) {
    return { fout: "sluit.dbOnbereikbaar" };
  }

  // Toestanden: velden toestand:<iso-datum> met open|dicht|onbekend.
  // Periodes: velden periode:<n>:van, periode:<n>:tot, periode:<n>:reden.
  // De regel: regel:weekdag (leeg = geen), regel:vanaf, regel:tot.
  const toestanden: { datum: string; naam: string; toestand: string }[] = [];
  const periodesRuw = new Map<
    string,
    { van: string; tot: string; reden: string }
  >();
  const regelRuw = { weekdag: "", vanaf: "", tot: "" };
  for (const [sleutel, waarde] of formulier.entries()) {
    if (typeof waarde !== "string") continue;
    const toestand = /^toestand:(\d{4}-\d{2}-\d{2})$/.exec(sleutel);
    if (toestand) {
      const naam = kandidaten.get(toestand[1]);
      if (naam === undefined) continue; // onbekende datum: niet bewaren
      toestanden.push({ datum: toestand[1], naam, toestand: waarde });
      continue;
    }
    const periode = /^periode:(\d+):(van|tot|reden)$/.exec(sleutel);
    if (periode) {
      const rij = periodesRuw.get(periode[1]) ?? {
        van: "",
        tot: "",
        reden: "",
      };
      rij[periode[2] as "van" | "tot" | "reden"] = waarde;
      periodesRuw.set(periode[1], rij);
      continue;
    }
    const regel = /^regel:(weekdag|vanaf|tot)$/.exec(sleutel);
    if (regel) {
      regelRuw[regel[1] as "weekdag" | "vanaf" | "tot"] = waarde;
    }
  }
  const periodes = [...periodesRuw.entries()]
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([, rij]) => rij);

  const { dagen, regels, fouten } = valideerSluitingen(
    toestanden,
    periodes,
    regelRuw,
  );
  if (fouten.length > 0) {
    // Eén fout per keer: de eerste. Wie meer fouten heeft, ziet na herstel
    // vanzelf de volgende — een sleutel draagt maar één zin.
    return { fout: fouten[0].sleutel, waarden: fouten[0].waarden };
  }

  const alles = voegSamen(bewaard.dagen, new Set(kandidaten.keys()), dagen);

  const reden = await bewaarInDatabase(alles, regels, sessie.gebruiker);
  if (reden !== null) {
    // De reden hoort in de log en niet op het scherm: een afwijzing van
    // Postgres kan de gegevens van de mislukte rij dragen.
    console.error("bewaarSluitingen: bewaar_sluitingskalender weigerde", reden);
    return { fout: "sluit.dbOpslaanMislukt" };
  }
  revalidatePath("/sluitingsdagen");

  // Kale aantallen als invulwaarden; de zin kiest het formulier bij het
  // tonen. Geteld over de volledige bewaarde kalender, want dat is wat er
  // vanaf nu staat.
  const dicht = alles.filter((d) => d.toestand === "dicht").length;
  const open = alles.filter((d) => d.toestand === "open").length;
  return {
    ok: "sluit.bewaard",
    waarden: { dicht: String(dicht), open: String(open) },
  };
}
