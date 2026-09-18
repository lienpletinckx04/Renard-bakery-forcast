import MeerInfo from "@/components/MeerInfo";
import type { T } from "@/lib/taal";

/**
 * De onbeschikbaar-toestand, eersteklas onderdeel van het ontwerp.
 * Een cijfer dat er nog niet is, wordt nooit een nul, een streepje of een
 * leeg vak: het vak blijft staan en zegt waarom er niets staat.
 *
 * Wat NOOIT inklapt: de titel en de regel "Nog niet beschikbaar". Dát er iets
 * ontbreekt, is precies wat zichtbaar moet blijven (harde regel 8, en de
 * huisstijl zegt het met zoveel woorden). Wat WEL inklapt: de reden.
 * In het CFO-rapport staat die toch open — Rapportknoppen.tsx zet elke
 * <details> in het rapport open vóór het afdrukken, dus op papier gaat er
 * niets verloren.
 *
 * ALTIJD INKLAPPEN, EN NIET BOVEN EEN LENGTEGRENS
 *
 * De eerste versie hiervan (18 aug 2026) klapte alleen in boven 160 tekens,
 * gekozen op een meting van de 32 redenen in het contract: kortste 98,
 * mediaan 243, langste 1112. Die grens is er na één blik op de
 * schermafbeeldingen weer uit gegaan, want Frans is systematisch langer dan
 * Nederlands: het kostenmodelvak stond op 143 tekens open in het Nederlands
 * en op 163 tekens ingeklapt in het Frans. Hetzelfde vak, twee structuren,
 * afhankelijk van de taal van de lezer — precies het soort stille halfheid
 * dat deze repo elders al drie keer heeft opgeruimd.
 *
 * Eén regel is beter dan een slimme regel: de reden staat altijd achter
 * "Waarom niet". Met een mediaan van 243 tekens is dat voor bijna elke reden
 * toch al het geval, en de lezer weet na één scherm waar hij moet klikken.
 */
export default function Onbeschikbaar({
  titel,
  reden,
  t,
}: {
  titel: string;
  reden: string;
  /**
   * De vertaler van de bladzijde. Verplicht en niet optioneel met een
   * Nederlandse terugval: een vergeten prop zou dan één Nederlands blok
   * midden in een Frans scherm zetten, en dat is precies het soort stille
   * halfheid dat je pas op een schermafbeelding ziet.
   */
  t: T;
}) {
  return (
    /* `paneel`: het afdrukhaakje uit Kaart. Dit vak hoort heel op één bladzijde
       te blijven — juist een blok dat uitlegt waarom een cijfer ontbreekt, mag
       niet halverwege afbreken.

       WAAROM DIT VAK ZWAARDER WEEGT DAN EEN KAART (18 aug 2026). Tot vandaag had
       dit vak een dunne warmgrijze rand rondom, precies zoals de toelichting
       onderaan een scherm — de rand markeerde dus juist de twee lichtste blokken,
       en een externe reviewer las alles even zwaar. De rand is nu één zwarte lijn
       links, 2px, dezelfde lijn die in de briefing een punt met "actie nodig"
       markeert: één vormtaal voor "hier moet iemand iets doen". En de regel "nog
       niet beschikbaar" staat een maat groter, want dát is de boodschap van het
       vak. Geen kleur in het spel: rangorde uit lijndikte, gewicht en grootte.
       Op papier valt de linkerlijn weg (de afdrukregel in globals.css geeft elk
       paneel een haarlijn rondom); de zwaardere typografie blijft, en die draagt
       de boodschap ook alleen. */
    <section className="paneel rounded-klein border-l-2 border-zwart bg-wit p-6">
      <h2 className="kapitaal-label-zwaar text-zwart">{titel}</h2>
      <p className="mt-3 text-base font-semibold text-zwart">
        {t("algemeen.nogNietBeschikbaar")}
      </p>
      <MeerInfo label={t("algemeen.waaromNiet")}>
        <p>{reden}</p>
      </MeerInfo>
    </section>
  );
}
