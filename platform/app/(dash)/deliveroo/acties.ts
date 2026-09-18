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
 * De uitkomst draagt SLEUTELS en geen tekst, plus eventuele invulwaarden —
 * hetzelfde patroon als het kostenmodel en de sluitingskalender: de actie kent
 * de taal van de lezer niet, het formulier vertaalt bij het tonen.
 */
export type UploadUitkomst = {
  ok?: Sleutel;
  fout?: Sleutel;
  waarden?: Record<string, string>;
};

/**
 * Laadt één bronbestand op: een export zoals ze van Deliveroo komt.
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
    return { fout: "deliveroo.sessieVerlopen" };
  }
  if (sessie.rol !== "beheerder") {
    return { fout: "deliveroo.alleenBeheerder" };
  }
  if (contractBron(process.env) !== "db") {
    return { fout: "deliveroo.alleenDb" };
  }

  const veld = formulier.get("bestand");
  // Een formulierveld is invoer van buiten: zonder deze controle is `veld` net
  // zo goed een tekenreeks, en dan zou `.arrayBuffer()` het scherm omleggen in
  // plaats van te weigeren.
  if (!(veld instanceof File) || veld.size === 0 || veld.name === "") {
    return { fout: "deliveroo.geenBestand" };
  }

  const { fouten } = valideerUpload({
    bestandsnaam: veld.name,
    mediatype: veld.type,
    bytes: veld.size,
  });
  if (fouten.length > 0) {
    // Eén fout per keer: de eerste. Wie meer bezwaren heeft, ziet na herstel
    // vanzelf het volgende — een sleutel draagt maar één zin.
    return { fout: fouten[0].sleutel, waarden: fouten[0].waarden };
  }

  const bestandsnaam = veld.name.trim();
  const mediatype = bepaalMediatype(bestandsnaam, veld.type);
  if (mediatype === null) {
    return { fout: "deliveroo.typeOnbekend", waarden: { bestandsnaam } };
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
    sessie.gebruiker,
  );
  if (melding === AL_GELADEN) {
    return { fout: "deliveroo.alGeladen", waarden: { bestandsnaam } };
  }
  if (melding !== null) {
    // De reden hoort in de log en niet op het scherm: een afwijzing van
    // Postgres kan de gegevens van de mislukte rij dragen.
    console.error("laadBestandOp: bewaar_bron_upload weigerde", melding);
    return { fout: "deliveroo.dbOpslaanMislukt" };
  }
  revalidatePath("/deliveroo");

  return { ok: "deliveroo.bewaard", waarden: { bestandsnaam } };
}
