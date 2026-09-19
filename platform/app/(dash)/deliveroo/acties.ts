"use server";

import { createHash } from "node:crypto";
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { COOKIE, lees } from "@/lib/auth";
import { contractBron } from "@/lib/contract-bron";
import {
  BRON,
  bepaalMediatype,
  naarBase64,
  valideerUpload,
} from "@/lib/deliveroo-upload";
import {
  AL_GELADEN,
  bewaarUploadInDatabase,
} from "@/lib/deliveroo-upload-db";
import type { Sleutel } from "@/lib/taal";

/**
 * Eén regel per bestand: de sleutel van de melding plus de invulwaarden.
 * Sleutels en geen tekst — de actie kent de taal van de lezer niet, het
 * formulier vertaalt bij het tonen (zelfde patroon als het kostenmodel en de
 * sluitingskalender).
 */
export type UploadRegel = {
  sleutel: Sleutel;
  waarden?: Record<string, string>;
  /** true als het bestand bewaard is (of er al stond); false bij een weigering. */
  gelukt: boolean;
};

/**
 * De uitkomst van één opladen. `fout` is de melding die het hele formulier
 * tegenhoudt (sessie, rol, omgeving, geen bestand gekozen); `regels` is de
 * uitkomst per gekozen bestand, in de volgorde van kiezen.
 */
export type UploadUitkomst = {
  fout?: Sleutel;
  waarden?: Record<string, string>;
  regels: UploadRegel[];
};

/**
 * Laadt één of meer bronbestanden op: exports zoals ze van Deliveroo komen.
 *
 * MEERDERE TEGELIJK, ELK VOOR ZICH. De Partner Hub levert exports van zestien
 * dagen, dus wie een jaar inhaalt heeft er twintig. Eén per keer kiezen is
 * dan de reden waarom het niet gebeurt. Het veld neemt daarom meerdere
 * bestanden aan, en elk bestand krijgt zijn eigen regel: een dubbel of een
 * verkeerd type houdt de andere niet tegen, en de lezer ziet per bestand wat
 * ermee gebeurd is. De grens per aanroep is die van de server-actie
 * (`serverActions.bodySizeLimit` in next.config); een export van zestien
 * dagen is een paar honderd kilobyte, dus dat is ruim.
 *
 * WAT DEZE ACTIE NIET DOET, EN DAT IS DE KERN. Ze leest het bestand niet en
 * pakt het niet uit. Ze kijkt naar naam, aangekondigd type en omvang, neemt de
 * vingerafdruk, en zet de bytes ongewijzigd in de database. Het uitpakken
 * gebeurt 's nachts in de Python-inlaadlaag — op één plaats, en niet ook nog
 * eens hier (harde regel 4: de UI rekent nooit). Een tweede lezer van hetzelfde
 * bestand is een tweede waarheid in wording.
 *
 * DE VINGERAFDRUK IS DE POORT TEGEN DUBBELE INVOER. De rpc weigert een tweede
 * rij met dezelfde sha256 en geeft dan 0 terug; wie per ongeluk dezelfde export
 * twee keer oplaadt, krijgt dat te horen in plaats van dat de cijfers stil
 * verdubbelen. Het is dus geen fout, maar wel een melding.
 */
export async function laadBestandOp(
  _vorige: UploadUitkomst,
  formulier: FormData,
): Promise<UploadUitkomst> {
  const sessie = await lees((await cookies()).get(COOKIE)?.value);
  if (!sessie) {
    return { fout: "deliveroo.sessieVerlopen", regels: [] };
  }
  if (sessie.rol !== "beheerder") {
    return { fout: "deliveroo.alleenBeheerder", regels: [] };
  }
  if (contractBron(process.env) !== "db") {
    return { fout: "deliveroo.alleenDb", regels: [] };
  }

  // Een formulierveld is invoer van buiten: zonder deze controle is een
  // waarde net zo goed een tekenreeks, en dan zou `.arrayBuffer()` het scherm
  // omleggen in plaats van te weigeren. Een leeg veld stuurt één File zonder
  // naam mee; die telt niet als gekozen bestand.
  const bestanden = formulier
    .getAll("bestand")
    .filter((v): v is File => v instanceof File && v.size > 0 && v.name !== "");
  if (bestanden.length === 0) {
    return { fout: "deliveroo.geenBestand", regels: [] };
  }

  const regels: UploadRegel[] = [];
  for (const veld of bestanden) {
    regels.push(await laadEenBestandOp(veld, sessie.gebruiker));
  }
  if (regels.some((r) => r.gelukt)) {
    revalidatePath("/deliveroo");
  }
  return { regels };
}

/** Eén bestand door de poort en naar de database; geeft de regel voor het scherm. */
async function laadEenBestandOp(veld: File, gebruiker: string): Promise<UploadRegel> {
  const { fouten } = valideerUpload({
    bestandsnaam: veld.name,
    mediatype: veld.type,
    bytes: veld.size,
  });
  if (fouten.length > 0) {
    // Eén fout per bestand: de eerste. Wie meer bezwaren heeft, ziet na
    // herstel vanzelf het volgende — een sleutel draagt maar één zin.
    return { sleutel: fouten[0].sleutel, waarden: fouten[0].waarden, gelukt: false };
  }

  const bestandsnaam = veld.name.trim();
  const mediatype = bepaalMediatype(bestandsnaam, veld.type);
  if (mediatype === null) {
    return { sleutel: "deliveroo.typeOnbekend", waarden: { bestandsnaam }, gelukt: false };
  }

  const bytes = new Uint8Array(await veld.arrayBuffer());
  const sha256 = createHash("sha256").update(bytes).digest("hex");

  const melding = await bewaarUploadInDatabase(
    {
      bron: BRON,
      bestandsnaam,
      mediatype,
      sha256,
      inhoud_base64: naarBase64(bytes),
    },
    gebruiker,
  );
  if (melding === AL_GELADEN) {
    return { sleutel: "deliveroo.alGeladen", waarden: { bestandsnaam }, gelukt: true };
  }
  if (melding !== null) {
    // De reden hoort in de log en niet op het scherm: een afwijzing van
    // Postgres kan de gegevens van de mislukte rij dragen.
    console.error("laadBestandOp: bewaar_bron_upload weigerde", melding);
    return { sleutel: "deliveroo.dbOpslaanMislukt", waarden: { bestandsnaam }, gelukt: false };
  }
  return { sleutel: "deliveroo.bewaard", waarden: { bestandsnaam }, gelukt: true };
}
