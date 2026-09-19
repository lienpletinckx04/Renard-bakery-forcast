"use client";

import { useActionState } from "react";

import { maakT, type T, type Taal } from "@/lib/taal";

import { laadBestandOp, type UploadUitkomst } from "./acties";

const LEEG: UploadUitkomst = { regels: [] };

function foutTekst(uitkomst: UploadUitkomst, t: T): string {
  if (!uitkomst.fout) return "";
  return t(uitkomst.fout, uitkomst.waarden);
}

const invoerKlasse =
  "rounded-klein border border-warmgrijs bg-wit px-3 py-1.5 text-sm text-zwart outline-none placeholder:text-zwart/45 focus:border-zwart focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart";

/**
 * Het uploadveld met zijn knop. Eén veld, één handeling: kies één of meer
 * bestanden en laad ze op. Elk bestand krijgt na afloop zijn eigen regel, in
 * de kleur van de uitkomst: wie twintig exports tegelijk kiest, ziet in één
 * oogopslag welke bewaard zijn, welke er al stonden en welke geweigerd zijn.
 *
 * DIT FORMULIER LEEST HET BESTAND NIET. Er is geen FileReader, geen voorbeeld,
 * geen telling van rijen — de bytes gaan via de server-actie ongewijzigd naar
 * de database, en het uitpakken gebeurt 's nachts in de verwerkingslaag.
 * Daarom staat hier ook geen voortgangsbalk: er valt niets te tonen tussen
 * "gekozen" en "bewaard".
 *
 * De accept-waarde komt als prop uit lib/deliveroo-upload.ts via de
 * servercomponent. Die module rechtstreeks invoeren zou Buffer in de
 * clientbundel trekken, en dat bestaat daar niet.
 */
export default function UploadFormulier({
  accept,
  taal,
}: {
  accept: string;
  taal: Taal;
}) {
  const t = maakT(taal);
  const [uitkomst, actie, bezig] = useActionState(laadBestandOp, LEEG);

  return (
    <form action={actie}>
      <label className="flex flex-wrap items-center gap-2 text-sm font-light text-zwart">
        {t("deliveroo.bestandLabel")}
        <input
          type="file"
          name="bestand"
          accept={accept}
          multiple
          className={`min-w-64 flex-1 ${invoerKlasse}`}
        />
      </label>
      <button
        type="submit"
        disabled={bezig}
        className="mt-6 rounded-klein bg-bordeaux px-5 py-2.5 text-xs font-semibold uppercase tracking-[0.14em] text-wit transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart disabled:opacity-50"
      >
        {bezig ? t("deliveroo.opladenBezig") : t("deliveroo.opladen")}
      </button>
      {/* Vaste hoogte, zodat het formulier niet verspringt bij een melding. */}
      <div aria-live="polite" className="mt-3 min-h-[1.25rem] max-w-prose text-sm">
        {uitkomst.fout ? (
          <p className="font-bold text-signaal-actie">{foutTekst(uitkomst, t)}</p>
        ) : null}
        {uitkomst.regels.length > 0 ? (
          <ul className="space-y-1">
            {uitkomst.regels.map((regel, i) => (
              <li
                key={i}
                className={`rounded-klein border-l-4 py-1 pl-3 ${
                  regel.gelukt
                    ? "border-signaal-goed bg-signaal-goed-vlak text-zwart"
                    : "border-signaal-actie bg-signaal-actie-vlak font-bold text-signaal-actie"
                }`}
              >
                {t(regel.sleutel, regel.waarden)}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </form>
  );
}
