import { allesGedeeld, bedragTekst, ONBEKEND, opVolgorde } from "@/lib/briefing";
import type { Briefing as BriefingInhoud, BriefingPunt } from "@/lib/contract";

/**
 * De briefing bovenaan een scherm: een handvol punten die zeggen wat er
 * opvalt, waarom, en wat er nodig is van wie. Signalering, geen advies.
 *
 * Deze component toont en verzint niets. Elke kop, elke reden, elk statuswoord
 * en elk bedrag komt uit het contract; er wordt hier geen zin geschreven, geen
 * drempel getoetst en geen cijfer gerekend (harde regel 4). Wat de component
 * wél doet, is de punten op hun statussleutel groeperen — zie lib/briefing.ts.
 *
 * DE STATUS DRAAGT SINDS 18 SEPTEMBER 2026 OOK KLEUR, MAAR NOOIT ALLEEN KLEUR.
 * Tot die dag gold hier "geen betekeniskleur"; de opdrachtgever heeft die
 * regel herroepen omdat het scherm zonder kleur te traag leesbaar was. Wat
 * niet mee herroepen is, is de reden erachter: kleur komt erbíj, nooit in de
 * plaats. De vier dragers hieronder blijven dus alle vier staan, en ze werken
 * alle vier zonder kleurwaarneming -- op een zwart-witafdruk en voor wie
 * kleurenblind is, verandert er niets aan wat dit blok zegt. Gekleurd zijn
 * alleen de verticale lijn en het statuswoord; het cijfer rechts blijft zwart,
 * want dat was een aparte regel met een eigen reden (zie globals.css).
 *
 *  1. HET WOORD. `statuswoord` staat voluit boven de kop, in het
 *     kapitaalregister van het logo. Het staat binnen de <h3>, zodat wie op
 *     koppen navigeert "actie — marge ontbreekt voor drie groepen" hoort en
 *     niet alleen het tweede deel.
 *  2. DE POSITIE. Acties staan bovenaan, dan wat aandacht vraagt, dan wat goed
 *     gaat. Zie `opVolgorde` in lib/briefing.ts.
 *  3. DE LIJN EN DE INSPRONG. Een dunne verticale lijn links van het punt, die
 *     zwaarder is naarmate er meer van de lezer gevraagd wordt: 2px zwart,
 *     1px warmgrijs, 1px beige, en bij een actie een inspring méér. Drie
 *     stappen van dezelfde vorm, niet drie kleuren met een betekenis — de lijn
 *     is een versterking van het woord, nooit de drager van de boodschap. Wie
 *     haar niet ziet, mist niets.
 *  4. DE MAAT VAN DE KOP. Een actie staat een tekstmaat groter en een gewicht
 *     zwaarder dan wat aandacht vraagt; wat goed gaat, staat lichter dan beide.
 *
 * Punt 4 is er op 18 augustus 2026 bijgekomen, na een externe review: "alles
 * heeft vaak ongeveer hetzelfde gewicht". Dat klopte. Het statuswoord staat op
 * 11px, en op 11px is halfvet naast medium geen ladder maar een nuance —
 * "ACTIE NODIG" en "LET OP" waren op een schermafbeelding niet te scheiden.
 * De maat van de kop is de eerste trap die je zonder meten ziet.
 *
 * Wat NIET meevarieert, en waarom: het bedrag rechts. Dat houdt overal dezelfde
 * maat en hetzelfde gewicht, zodat de cijferbreedtes over de punten heen blijven
 * uitlijnen. Varieerde ook dat mee, dan was het geen ladder meer maar drukte —
 * en een kolom cijfers die niet meer uitlijnt, leest slechter dan een die dat
 * wel doet.
 */

/**
 * De verticale lijn links van het punt: dikte én kleur. De dikte is de oude
 * ladder en blijft de drager voor wie geen kleur ziet; de kleur is de snelle
 * herkenning voor wie wel kijkt. `goed` krijgt 1px en niet 2px: wat goed gaat
 * hoort niet even hard te roepen als wat actie vraagt, ook niet in het groen.
 */
const LIJN: Record<BriefingPunt["status"], string> = {
  actie: "border-l-2 border-signaal-actie pl-5",
  let_op: "border-l border-signaal-letop pl-4",
  goed: "border-l border-signaal-goed pl-4",
};

/** Het statuswoord in dezelfde signaalkleur als de lijn ernaast. */
const WOORDKLEUR: Record<BriefingPunt["status"], string> = {
  actie: "text-signaal-actie",
  let_op: "text-signaal-letop",
  goed: "text-signaal-goed",
};

const GEWICHT: Record<BriefingPunt["status"], string> = {
  actie: "font-semibold",
  let_op: "font-medium",
  goed: "font-light",
};

/** De maat en het gewicht van de kop; de zichtbaarste trap van de ladder. */
const KOP: Record<BriefingPunt["status"], string> = {
  actie: "text-lg font-semibold",
  let_op: "text-base font-medium",
  goed: "text-base font-normal",
};

export default function Briefing({
  briefing,
  titel,
}: {
  briefing: BriefingInhoud;
  /**
   * De kop boven de punten, en meteen de naam van dit blok voor een
   * schermlezer. Altijd meegeven: deze component kent de taal van de lezer
   * niet, en een Nederlandse terugval zou op een Frans scherm één Nederlandse
   * kop achterlaten.
   */
  titel: string;
}) {
  /**
   * DE LEGE STAAT. Geen signalen is de normale, goede toestand van een scherm,
   * en dan hoort er ook niets te staan dat om aandacht vraagt: geen wit
   * paneel, geen kop in kapitalen, geen kader met "geen meldingen". Eén rustige
   * regel op het beige vlak, in dezelfde lichte tekst als een ondertitel — te
   * lezen voor wie kijkt, te negeren voor wie doorloopt.
   *
   * De zin komt uit het contract. Levert het contract er geen, dan zwijgt de
   * component: een lege alinea met marges zou een gat op het scherm zijn, en
   * zelf een zin bedenken mag niet (harde regel 4).
   */
  if (briefing.punten.length === 0) {
    const zin = briefing.leeg.trim();
    if (zin === "") return null;
    return <p className="max-w-prose text-sm font-light text-zwart">{zin}</p>;
  }

  const punten = opVolgorde(briefing.punten);

  return (
    /* `paneel`: hetzelfde afdrukhaakje als in Kaart — zie daar waarom.
     *
     * DIT BLOK WEEGT ZWAARDER DAN EEN KAART, en dat mag je zien zonder het te
     * lezen. Drie middelen, geen ervan kleur: meer lucht binnen het paneel
     * (p-8 tegen p-6 elders), de kop een maat en een gewicht groter
     * (.kapitaal-label-zwaar), en één zwarte haarlijn onder die kop. Die lijn is
     * het enige zwart-op-wit lijnwerk in het platform — elders zijn lijnen
     * warmgrijs — en markeert dus zonder woorden welk blok het eerst gelezen
     * hoort te worden. De positie doet de rest: de briefing staat op elk scherm
     * direct onder de paginakop.
     */
    /* `data-alles-gedeeld`: het haakje waarmee het rapport dit blok in zijn
       geheel kan laten vallen wanneer er na het verbergen van de gedeelde
       punten niets eigens meer over is. Buiten /rapport doet het niets — zie
       globals.css.

       Een haakje zonder waarde, en dat is opzet: de CSS toetst de aanwezigheid
       (`[data-alles-gedeeld]`). Een waarde zou een woord zijn dat in geen van
       beide talen bestaat, en die zoekt de wacht in geen-harde-tekst.test.ts
       terecht op. */
    <section
      aria-labelledby="briefing-kop"
      {...(allesGedeeld(punten) ? { "data-alles-gedeeld": "" } : {})}
      className="paneel rounded-klein bg-wit p-8"
    >
      <h2
        id="briefing-kop"
        className="kapitaal-label-zwaar border-b border-zwart pb-3 text-zwart"
      >
        {titel}
      </h2>
      {/* Een geordende lijst: de volgorde is de derde drager van de status,
          dus ze is inhoud en geen opmaak. */}
      <ol className="mt-6 space-y-7">
        {punten.map((punt, i) => (
          <li
            key={`${punt.status}-${punt.kop}-${i}`}
            /* Alleen gezet als het contract het punt gedeeld noemt, en zonder
               waarde: de CSS toetst de aanwezigheid. Een attribuut dat er
               altijd staat, nodigt uit tot een regel op de negatieve waarde, en
               dan hangt het gedrag af van een attribuut dat er per ongeluk niet
               staat. */
            {...(punt.gedeeld ? { "data-gedeeld": "" } : {})}
            className={`flex flex-wrap items-start justify-between gap-x-8 gap-y-1 ${
              LIJN[punt.status] ?? LIJN[ONBEKEND]
            }`}
          >
            {/* `grow` en niet `flex-1`: die laatste zet ook de basis op nul en
                zou met basis-64 om voorrang vechten in de gegenereerde CSS. */}
            <div className="min-w-0 grow basis-64">
              <h3
                className={`text-zwart ${KOP[punt.status] ?? KOP[ONBEKEND]}`}
              >
                {/* Het kapitaalregister uit het logo, hier met de hand gezet en
                    niet via .kapitaal-label: die utility legt het gewicht vast,
                    en juist het gewicht is hier het verschil tussen de drie
                    statussen. */}
                <span
                  className={`block text-[0.6875rem] uppercase tracking-[0.14em] ${
                    GEWICHT[punt.status] ?? GEWICHT[ONBEKEND]
                  } ${WOORDKLEUR[punt.status] ?? WOORDKLEUR[ONBEKEND]}`}
                >
                  {punt.statuswoord}
                </span>
                <span className="mt-1 block">{punt.kop}</span>
              </h3>
              <p className="mt-1 max-w-prose text-sm font-light text-zwart">
                {punt.waarom}
              </p>
              {/* Wat er nodig is, staat een gewicht zwaarder dan het waarom.
                  Geen label ervoor: de component heeft geen woord om het mee
                  aan te kondigen dat niet uit het contract komt. */}
              {punt.nodig ? (
                <p className="mt-1 max-w-prose text-sm font-medium text-zwart">
                  {punt.nodig}
                </p>
              ) : null}
            </div>
            {/* Het cijfer staat in zwart, rechts, met cijferbreedtes die over
                de punten heen uitlijnen. Richting komt uit de pijl en uit het
                teken dat format.ts zet. */}
            {punt.bedrag !== null ? (
              <p className="text-sm font-medium whitespace-nowrap text-zwart tabular-nums">
                {punt.richting ? (
                  <span aria-hidden="true">
                    {punt.richting === "neer" ? "↓ " : "↑ "}
                  </span>
                ) : null}
                {bedragTekst(punt.bedrag, punt.soort)}
                {/* De eenheid komt uit het contract, in de taal van de boom:
                    "9" is een notificatieteller, "9 dagen" is een feit. */}
                {punt.eenheid ? ` ${punt.eenheid}` : null}
              </p>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
