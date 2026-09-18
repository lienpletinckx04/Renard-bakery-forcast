import {
  DEEL_NAAM,
  DEEL_PARAM,
  RAPPORT_DELEN,
  type RapportDeel,
} from "@/lib/rapport";
import type { T } from "@/lib/taal";

/**
 * Het keuzemenu van het rapport: vinkjes per onderdeel en één knop die het
 * rapport opent met precies die onderdelen erin.
 *
 * WAAROM ZONDER JAVASCRIPT. Dit is een `<details>` met een gewoon
 * GET-formulier: de vinkjes worden URL-parameters en het rapport is een adres
 * (`/rapport?deel=kanalen&deel=prognose`). Daarmee is de keuze deelbaar, te
 * bewaren als bladwijzer en te herhalen — een keuze die alleen in het geheugen
 * van de browser leeft, kun je niemand doorsturen. En er is geen toestand die
 * kan gaan afwijken van wat het rapport werkelijk toont.
 *
 * WAAROM `<details>` EN GEEN POPOVER. De native popover-API geeft
 * licht-sluiten gratis, maar plaatst het paneel midden in het beeld tenzij je
 * ankerpositionering gebruikt, en die is nog niet overal beschikbaar. Een
 * `<details>` staat waar de knop staat, op elke browser. Prijs: hij sluit niet
 * bij een klik ernaast, alleen door nog eens op de knop te klikken of door het
 * rapport te openen.
 *
 * HUISSTIJL. Beide knoppen staan in het kapitaalregister van het logo. De
 * openknop is een effen bordeaux vlak met beige tekst — dezelfde behandeling
 * als het actieve item in de navigatie, en dus identiteit en geen betekenis.
 * Er staat geen cijfer op.
 */
export default function RapportMenu({
  t,
  gekozen = RAPPORT_DELEN,
  nieuwTabblad = true,
}: {
  /** De vertaler van de bladzijde; dit onderdeel kent de taal niet zelf. */
  t: T;
  /** Welke vinkjes aanstaan. Op het rapport zelf: de huidige keuze. */
  gekozen?: readonly RapportDeel[];
  /**
   * Vanuit een scherm opent het rapport in een nieuw tabblad, zodat de lezer
   * zijn scherm niet kwijt is. Op het rapport zelf niet: daar is dit menu er
   * om de keuze te wijzigen, en een nieuw tabblad per wijziging levert een rij
   * verweesde rapporten op.
   */
  nieuwTabblad?: boolean;
}) {
  return (
    <details className="niet-afdrukken relative">
      <summary className="kapitaal-label inline-flex cursor-pointer list-none items-center rounded-klein border border-bordeaux px-3 py-1.5 text-bordeaux hover:bg-bordeaux/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart [&::-webkit-details-marker]:hidden">
        {/* Op een scherm heet de knop naar wat hij oplevert ("Rapport"); in het
            rapport zelf naar wat hij daar doet ("Onderdelen"). */}
        {t(nieuwTabblad ? "rapport.knop" : "rapport.onderdelen")}
      </summary>
      <form
        action="/rapport"
        method="get"
        target={nieuwTabblad ? "_blank" : undefined}
        className="absolute right-0 z-30 mt-2 w-72 rounded-klein border border-warmgrijs bg-wit p-5"
      >
        <fieldset>
          <legend className="kapitaal-label text-zwart">
            {t("rapport.onderdelen")}
          </legend>
          <ul className="mt-3 space-y-2">
            {RAPPORT_DELEN.map((deel) => (
              <li key={deel}>
                <label className="flex cursor-pointer items-center gap-2.5 text-sm text-zwart">
                  <input
                    type="checkbox"
                    name={DEEL_PARAM}
                    value={deel}
                    defaultChecked={gekozen.includes(deel)}
                    className="size-4 shrink-0 accent-bordeaux"
                  />
                  {t(DEEL_NAAM[deel])}
                </label>
              </li>
            ))}
          </ul>
        </fieldset>
        {/* Geen "alles aanvinken"-knop: dat zou JavaScript vragen voor iets wat
            de terugval al doet. Niets aangevinkt is het hele rapport, en dat
            staat hier zodat het geen verrassing is. */}
        <p className="mt-3 max-w-prose text-xs font-light text-zwart">
          {t("rapport.terugvalAlles")}
        </p>
        <button
          type="submit"
          className="kapitaal-label mt-4 w-full rounded-klein bg-bordeaux px-3 py-2 text-beige focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart"
        >
          {t(nieuwTabblad ? "rapport.openen" : "rapport.wijzigen")}
        </button>
      </form>
    </details>
  );
}
