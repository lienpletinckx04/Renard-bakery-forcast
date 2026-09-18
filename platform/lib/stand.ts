import type { T, Taal } from "./taal";

/**
 * De stand van het platform, in woorden. Twee kleine vertalingen, en bewust
 * niet meer dan dat: het oordeel zelf ("vers", "let_op", "fout") komt uit de
 * berekeningslaag en wordt hier alleen leesbaar gemaakt. Er wordt niets
 * gewogen, geteld of samengevat — ook `ergste` is al door de berekeningslaag
 * bepaald.
 *
 * Statuswoorden blijven tekst, geen kleur: de huisstijl kent geen
 * betekeniskleuren, en "achter" in gewone letters zegt precies genoeg.
 */

/**
 * "let_op" -> "let op" / "attention". De contractsleutels dragen underscores
 * omdat het machinewaarden zijn; op het scherm staat gewoon taal. Een status
 * die hier niet in de tabel staat, gaat ongewijzigd door (op de underscore na)
 * in plaats van te verdwijnen: een nieuwe uitkomst uit de berekeningslaag mag
 * nooit stil van het scherm vallen.
 */
const STATUSWOORDEN: Record<string, Record<Taal, string>> = {
  goed: { nl: "goed", fr: "bon" },
  let_op: { nl: "let op", fr: "attention" },
  fout: { nl: "fout", fr: "erreur" },
  achter: { nl: "achter", fr: "en retard" },
  gesloten: { nl: "gesloten", fr: "fermé" },
  vers: { nl: "vers", fr: "à jour" },
  stil: { nl: "stil", fr: "muet" },
  ontbreekt: { nl: "ontbreekt", fr: "manquant" },
  // Een bron die niet meer aangevuld wordt (TGTG sinds 19 aug 2026). Bewust
  // niet "verouderd": dat zou een verwijt zijn aan iets wat volgens afspraak
  // stilstaat. Zie kwaliteit.BEVROREN.
  bevroren: { nl: "bevroren", fr: "figé" },
};

export function statusWoord(status: string, taal: Taal = "nl"): string {
  return STATUSWOORDEN[status]?.[taal] ?? status.replaceAll("_", " ");
}

/**
 * De regel die de voettekst van elk scherm draagt wanneer de datakwaliteit
 * niet in orde is, of null bij "goed" — geen alarmvermoeidheid: als alles
 * klopt, staat er niets. De teksten komen uit het woordenboek (kwaliteit.*);
 * de aanroeper geeft zijn vertaalfunctie mee, zoals overal elders.
 *
 * Een onbekende uitkomst wordt niet als "goed" gelezen maar krijgt de
 * alarmregel: stilte is het enige antwoord dat hier fout kan zijn, en de
 * voettekst linkt naar Instellingen, waar `statusWoord` de uitkomst zelf
 * uitschrijft.
 */
export function datakwaliteitVoettekst(ergste: string, t: T): string | null {
  if (ergste === "goed") return null;
  return ergste === "let_op" ? t("kwaliteit.letOp") : t("kwaliteit.alarm");
}
