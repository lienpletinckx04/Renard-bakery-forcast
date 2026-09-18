/**
 * De poort van het uploadscherm: wat mag er binnen, en hoe gaat het als bytes
 * de deur door. Los van Next zodat het testbaar is met de kale
 * node-testrunner — zelfde opzet als lib/sluitingsdagen.ts.
 *
 * WAT HIER NIET GEBEURT, EN DAT IS DE KERN. Dit bestand LEEST het bestand
 * niet. Het kijkt naar de naam, het aangekondigde mediatype en het aantal
 * bytes, en verder gaat het niet: de inhoud reist onaangeroerd naar de
 * database, waar de Python-inlaadlaag hem 's nachts uit haalt. Parsen hoort
 * in de inlaadlaag en niet in een browser of in Next (harde regel 4: de UI
 * rekent nooit). Een csv die hier al uit elkaar gehaald wordt, is een tweede
 * lezer van hetzelfde bestand, en twee lezers gaan vroeg of laat uit elkaar
 * lopen.
 *
 * Fouten zijn SLEUTELS uit het woordenboek plus invulwaarden, geen zinnen:
 * deze module draait in een server-actie, en die kent de taal van de lezer
 * niet — het formulier vertaalt bij het tonen. Zelfde afspraak als
 * lib/sluitingsdagen.ts.
 */

// Relatief en niet via de @/-alias: deze module draait ook onder de kale
// node-testloper (tests/ts-resolve.mjs), die de Next-alias niet kent.
import type { Sleutel } from "./taal";

/** De waarde van de kolom `bron` in bron_upload. Eén bron voorlopig. */
export const BRON = "deliveroo";

/**
 * De grens in megabytes staat vooraan, want dat is de grens die op het scherm
 * uitgesproken wordt. De bytegrens volgt eruit; twee losse getallen zouden uit
 * elkaar kunnen lopen en dan noemt de melding een andere grens dan de poort
 * hanteert.
 */
export const MAX_MB = 10;
export const MAX_BYTES = MAX_MB * 1024 * 1024;

/**
 * Wat een Deliveroo-export kan zijn. Bewust een korte lijst: alles wat hier
 * niet in staat, wordt geweigerd vóór het bytes in de database kost.
 */
export const TOEGESTANE_MEDIATYPES = [
  "application/pdf",
  "text/csv",
  // .xlsx
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  // .xls
  "application/vnd.ms-excel",
] as const;

export type Mediatype = (typeof TOEGESTANE_MEDIATYPES)[number];

/**
 * De terugval op de extensie. Een browser kondigt lang niet altijd een
 * bruikbaar mediatype aan: een csv die uit Excel komt heet op Windows geregeld
 * "application/vnd.ms-excel", en een bestand dat het systeem niet herkent komt
 * binnen als "application/octet-stream" of met een lege tekenreeks. Weigeren op
 * die grond zou een geldige export tegenhouden om een eigenschap van de
 * computer van de beheerder.
 */
export const EXTENSIE_MEDIATYPE: Record<string, Mediatype> = {
  ".pdf": "application/pdf",
  ".csv": "text/csv",
  ".xlsx":
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ".xls": "application/vnd.ms-excel",
};

export const TOEGESTANE_EXTENSIES = Object.keys(EXTENSIE_MEDIATYPE);

/**
 * De waarde van het accept-attribuut op het bestandsveld: dezelfde lijst, als
 * één tekenreeks. Ze staat hier en niet in het formulier omdat het formulier
 * een clientcomponent is: die mag deze module niet invoeren, want `naarBase64`
 * hieronder gebruikt Buffer en dat bestaat alleen op de server. De
 * servercomponent geeft deze waarde door als prop.
 *
 * Het attribuut is een hulp bij het kiezen, geen poort: een browser mag het
 * negeren en een bestand dat er doorheen komt wordt hieronder alsnog getoetst.
 */
export const ACCEPT = [...TOEGESTANE_MEDIATYPES, ...TOEGESTANE_EXTENSIES].join(
  ",",
);

export type UploadFout = {
  sleutel: Sleutel;
  waarden: Record<string, string>;
};

export type UploadValidatie = { fouten: UploadFout[] };

/** De extensie inclusief punt, in kleine letters; leeg als er geen is. */
function extensieVan(bestandsnaam: string): string {
  const punt = bestandsnaam.lastIndexOf(".");
  if (punt <= 0) return "";
  return bestandsnaam.slice(punt).toLowerCase();
}

/**
 * Het mediatype waarmee dit bestand bewaard wordt, of null wanneer noch het
 * aangekondigde type noch de extensie iets bekends oplevert.
 *
 * Het aangekondigde type wint als het toegestaan is; anders beslist de
 * extensie. Dat de extensie mag beslissen is geen zwakte van de poort: de
 * inhoud wordt hier toch niet gelezen, en de inlaadlaag toetst aan de andere
 * kant opnieuw wat ze werkelijk in handen heeft.
 */
export function bepaalMediatype(
  bestandsnaam: string,
  mediatype: string,
): Mediatype | null {
  const gemeld = mediatype.trim().toLowerCase().split(";")[0] ?? "";
  const bekend = TOEGESTANE_MEDIATYPES.find((m) => m === gemeld);
  if (bekend !== undefined) return bekend;
  return EXTENSIE_MEDIATYPE[extensieVan(bestandsnaam)] ?? null;
}

/**
 * De poort vóór het opladen. Alle bezwaren tegelijk, want ze zijn goedkoop te
 * bepalen; de server-actie toont er één (de eerste), zoals het
 * sluitingsdagenformulier dat ook doet — een sleutel draagt maar één zin.
 *
 * De naam mag geen padscheidingsteken dragen. Een browser stuurt alleen de
 * kale bestandsnaam, dus in de praktijk gebeurt dat niet; maar de naam komt
 * ongewijzigd in de database en van daaruit onder ogen van de inlaadlaag, en
 * een naam die eruitziet als een pad is precies het soort waarde waar een
 * later script over struikelt.
 */
export function valideerUpload(bestand: {
  bestandsnaam: string;
  mediatype: string;
  bytes: number;
}): UploadValidatie {
  const fouten: UploadFout[] = [];
  const bestandsnaam = bestand.bestandsnaam.trim();

  if (bestandsnaam === "" || /[/\\]/.test(bestandsnaam)) {
    fouten.push({
      sleutel: "deliveroo.naamOngeldig",
      waarden: { bestandsnaam },
    });
  }
  if (bestand.bytes <= 0) {
    fouten.push({ sleutel: "deliveroo.leegBestand", waarden: {} });
  } else if (bestand.bytes > MAX_BYTES) {
    fouten.push({
      sleutel: "deliveroo.teGroot",
      waarden: { max: String(MAX_MB) },
    });
  }
  if (bepaalMediatype(bestandsnaam, bestand.mediatype) === null) {
    fouten.push({
      sleutel: "deliveroo.typeOnbekend",
      waarden: { bestandsnaam },
    });
  }

  return { fouten };
}

/**
 * De bytes naar base64, want json draagt geen ruwe bytes en de rpc neemt het
 * bestand als `inhoud_base64` aan.
 *
 * ÉÉN WEG, EN WAAROM DEZE. Buffer, niet een lus met String.fromCharCode. Deze
 * module wordt alleen vanaf de server ingevoerd (de server-actie; het
 * clientformulier krijgt de accept-waarde als prop juist om dit bestand niet
 * te hoeven invoeren), dus Buffer is er gewoon. Hij doet de omzetting in één
 * stap in C++, zonder tussenliggende tekenreeks van tien miljoen tekens en
 * zonder één functieaanroep met een miljoen argumenten — dat laatste is
 * precies wat `String.fromCharCode(...bytes)` doet, en op een megabyte legt
 * dat de argumentenstack om. De blokkenlus die je in een browser nodig hebt
 * lost een probleem op dat hier niet bestaat; twee wegen naast elkaar zou
 * betekenen dat de ene nooit gedraaid wordt en dus stilletjes kan bederven.
 */
export function naarBase64(data: Uint8Array | ArrayBuffer): string {
  const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
  return Buffer.from(bytes).toString("base64");
}
