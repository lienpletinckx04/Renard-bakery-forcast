import type { KerncijferData } from "@/lib/contract";
import { aantal, euro, verschilProcent } from "@/lib/format";
import { richtingChip } from "@/lib/signaal";
import type { T } from "@/lib/taal";

/**
 * Label in wijd gespatieerde kapitalen, groot getal, verschil met pijl.
 *
 * HET VERSCHIL DRAAGT SINDS 18 SEPTEMBER 2026 KLEUR, het grote getal niet.
 * De opdrachtgever wil in één blik zien of het goed of slecht gaat; dit is de
 * eerste rij op het scherm, dus hier hoort dat oordeel. Het getal zelf blijft
 * zwart -- dat was een aparte regel met een eigen reden (globals.css) -- en de
 * pijl en het teken blijven staan: kleur komt erbij, nooit in de plaats.
 *
 * De accentvariant is een effen bordeaux vlak met witte cijfers, naar de
 * flyer uit de logogids. Dat vlak is identiteit en nooit betekenis: het
 * accent ligt vast op het eerste kerncijfer en verhuist niet met goed of
 * slecht nieuws mee. OP DAT VLAK KRIJGT HET VERSCHIL GÉÉN KLEUR: groen of
 * rood op bordeaux is onleesbaar, en een signaalkleur die niet te lezen is,
 * is erger dan geen. Daar dragen pijl en teken het alleen, zoals voorheen.
 */
export default function Kerncijfer({
  cijfer,
  t,
  accent = false,
}: {
  cijfer: KerncijferData;
  /** De vertaler van de bladzijde; verplicht, om dezelfde reden als in
      Onbeschikbaar: een vergeten prop zet één Nederlands woord midden in
      een Frans scherm, en dat zie je pas op een schermafbeelding. */
  t: T;
  accent?: boolean;
}) {
  const waarde = cijfer.soort === "euro" ? euro(cijfer.waarde) : aantal(cijfer.waarde);
  const vlak = accent ? "bg-bordeaux" : "bg-wit";
  const inkt = accent ? "text-wit" : "text-zwart";
  const label = accent ? "text-beige" : "text-zwart";

  return (
    /* `kerncijfer` en `kerncijfer-accent` zijn afdrukhaakjes (zie Kaart). Voor
       het accentvlak is het meer dan een haarlijn: wit cijfer op bordeaux wordt
       wit op wit zodra de printer de vulling weglaat, en dat is geen cijfer
       meer. Op papier wordt dit vlak daarom een paneel met zwarte cijfers —
       dezelfde vaste positie, andere drager. De huisstijlregel blijft precies
       overeind: de kleur van een cijfer volgt zijn drager en draagt nooit
       betekenis. */
    <div
      className={`kerncijfer rounded-klein p-6 ${accent ? "kerncijfer-accent " : ""}${vlak}`}
    >
      <div className={`kapitaal-label ${label}`}>{cijfer.label}</div>
      <div className={`mt-2 text-3xl font-semibold tabular-nums whitespace-nowrap ${inkt}`}>
        {waarde}
      </div>
      {cijfer.verschil ? (
        <div className={`mt-1 text-sm tabular-nums ${inkt}`}>
          {/* Geen pijl als het contract geen richting geeft. De vorige versie
              tekende ↑ zodra `richting` niet exact "neer" was, dus ook bij
              null — bij een verschil van −0,04% stond er dan "↑ −0,0%": een
              stijgingspijl bij een daling. Het teken komt uit format.ts en
              staat er hoe dan ook; de pijl is versterking, en een versterking
              die de verkeerde kant op wijst is erger dan geen pijl. */}
          {/* Een chip en geen los gekleurd woord: op een wit vlak met een
              groot zwart getal erboven verdween gekleurde tekst; een vlakje
              met de kleur erachter niet. Op het bordeaux accent geen chip, om
              de reden in de kop van dit bestand. */}
          <span
            className={`text-base ${
              accent ? "font-bold" : richtingChip(cijfer.richting) || "font-bold"
            }`}
          >
            {cijfer.richting ? (
              <>
                <span aria-hidden="true">
                  {cijfer.richting === "neer" ? "↓" : "↑"}
                </span>{" "}
              </>
            ) : null}
            {verschilProcent(cijfer.verschil)}
          </span>{" "}
          {/* Dit is een label, geen cijfer: op het bordeaux vlak dus beige,
              zoals het kop-label hierboven (huisstijl-verfijning 12 aug). */}
          <span className={`font-light ${label}`}>{t("algemeen.tovVorigJaar")}</span>
        </div>
      ) : null}
    </div>
  );
}
