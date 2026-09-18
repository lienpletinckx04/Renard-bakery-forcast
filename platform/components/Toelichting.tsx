import type { Onbeschikbaar as OnbeschikbaarRegel } from "@/lib/contract";
import type { T } from "@/lib/taal";
import { veldLabel, type LabelTaal } from "@/lib/toelichting";

/**
 * De voetnoten van een scherm: wat er niet staat, en waarom niet.
 *
 * `Onbeschikbaar` is voor een heel vak dat leeg blijft (een margescherm, een
 * kanaal zonder data). Dit is voor het kleinere geval: een cijfer staat er wél,
 * maar iets eraan is beperkt — geen vergelijking met vorig jaar, een maand die
 * uit een grafiek is weggelaten, een aanname in een voorspelling.
 *
 * Harde regel 8 vraagt dat zoiets zichtbaar is. Zonder dit blok is een
 * ontbrekende jaar-op-jaarpijl niet te onderscheiden van een pijl die iemand
 * vergeten heeft, en dat is precies het soort stilte waarin een dashboard begint
 * te liegen.
 */
export default function Toelichting({
  regels,
  titel,
  t,
  taal,
}: {
  regels: OnbeschikbaarRegel[];
  /** Voor het telwoord achter de kop; de teksten zelf komen uit het contract. */
  t: T;
  /** De taal van de veldlabels; de redenen eronder komen al vertaald binnen. */
  taal: LabelTaal;
  /**
   * Altijd meegeven. Tot 14 augustus 2026 stond hier een Nederlandse
   * standaardwaarde; die zou op een Frans scherm de kop in het Nederlands
   * zetten zonder dat iemand het merkt.
   *
   * Oorspronkelijke reden voor een eigen kop:
   * Een eigen kop, voor het geval dat een deel van de voorbehouden niet
   * onderaan hoort maar vooraan: de nauwkeurigheid van een voorspelling leest
   * niemand meer als ze onder "wat hier niet staat" is beland.
   */
  titel?: string;
}) {
  if (regels.length === 0) return null;

  return (
    /* GEEN PANEEL MEER, MAAR EEN VOETNOOT (18 aug 2026). Dit blok stond in een
       wit paneel met een rand rondom, en woog daarmee op het scherm even zwaar
       als een briefing of een onbeschikbaar-vak. Dat was de kritiek van de
       externe review, en ze was terecht: dit is de kleine lettertjes van een
       scherm, geen mededeling.

       Wat er is veranderd: het vlak en de rand zijn weg, één warmgrijze haarlijn
       bovenaan scheidt de voetnoot van wat erboven staat. De tekst staat nu
       rechtstreeks op het beige vlak — de huisstijl vraagt "veel witruimte, dunne
       lijnen, geen kaders om alles heen", en een voetnoot is bij uitstek het blok
       dat geen kader nodig heeft. Niets wordt verborgen: de kop en het aantal
       punten blijven staan (toegankelijkheidsregel van 14 aug), alleen de tekst
       klapt in zoals voorheen.

       Het afdrukhaakje `paneel` gaat mee weg, en dat is geen vergetelheid: het
       geeft in print een rand rondom, en een rand rondom een blok zonder
       zijpadding zet de tekst tegen de lijn aan. Op papier blijft de haarlijn
       bovenaan staan — een printer laat vlakken weg, geen lijnen — dus de
       voetnoot is daar hetzelfde blok als op het scherm. Wat we opgeven is
       `break-inside: avoid`; voor een lijst voorbehouden is dat winst, want die
       hoort te mogen doorlopen in plaats van een halve bladzijde open te laten. */
    <section className="border-t border-warmgrijs pt-5">
      {/* De kop met het aantal blijft altijd zichtbaar — dát er voorbehouden
          zijn is de eerlijkheid van het scherm (harde regel 8). De volle tekst
          klapt uit: wie hem elke dag leest, kent hem al; wie hem nodig heeft,
          is één klik verwijderd. Native <details>: werkt zonder JavaScript. */}
      <details className="group">
        {/* `uitklap-kop`: het afdrukhaakje uit globals.css. Zonder die klasse
            verbergt de afdrukregel deze summary — en de <h2> hieronder zit
            erín, dus de voetnoot verscheen in de PDF als een naamloze lijst
            onder een haarlijn. Gevonden 19 aug 2026, op elke bladzijde van het
            rapport. De klasse heeft buiten @media print geen enkele opmaak. */}
        <summary className="uitklap-kop inline-flex cursor-pointer list-none items-baseline gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zwart [&::-webkit-details-marker]:hidden">
          <span
            aria-hidden
            className="text-xs text-zwart transition-transform group-open:rotate-90"
          >
            ▸
          </span>
          <h2 className="kapitaal-label inline text-zwart">{titel}</h2>
          <span className="text-sm font-light text-zwart">
            {regels.length === 1
              ? t("algemeen.eenPunt")
              : t("algemeen.nPunten", { n: String(regels.length) })}
          </span>
        </summary>
        <dl className="mt-4 space-y-3">
          {regels.map((r) => (
            <div key={r.veld} className="max-w-prose">
              {/* De contractsleutel is een variabelenaam en hoort niet op een
                  scherm (O12). Hij blijft wel de sleutel in het contract: stabiel
                  en herkenbaar voor de app van fase 2. */}
              <dt className="text-sm font-medium text-zwart">
                {veldLabel(r.veld, taal)}
              </dt>
              <dd className="text-sm font-light text-zwart">{r.reden}</dd>
            </div>
          ))}
        </dl>
      </details>
    </section>
  );
}
