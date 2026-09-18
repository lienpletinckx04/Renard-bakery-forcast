"use client";

import { useActionState } from "react";

import { maakT, type T, type Taal } from "@/lib/taal";

import { laadBestandOp, type UploadUitkomst } from "./acties";

const LEEG: UploadUitkomst = {};

function meldingTekst(uitkomst: UploadUitkomst, t: T): string {
  const sleutel = uitkomst.fout ?? uitkomst.ok;
  if (!sleutel) return "";
  return t(sleutel, uitkomst.waarden);
}

const invoerKlasse =
  "rounded-klein border border-warmgrijs bg-wit px-3 py-1.5 text-sm text-zwart outline-none placeholder:text-zwart/45 focus:border-zwart focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart";

/**
 * Het uploadveld met zijn knop. Eén veld, één handeling: kies een bestand en
 * laad het op.
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
      <p
        aria-live="polite"
        className="mt-3 min-h-[1.25rem] max-w-prose text-sm font-light text-zwart"
      >
        {meldingTekst(uitkomst, t)}
      </p>
    </form>
  );
}
