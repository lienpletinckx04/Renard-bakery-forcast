/**
 * De maatvoering van de staafgrafiek: hoeveel ruimte de schuine aslabels nodig
 * hebben, en waar het tekenvlak dus mag beginnen.
 *
 * Waarom dit een eigen module met een test is: de marges stonden als vaste
 * getallen in het component (ondermarge 92, hoogte 220 + 64), onafhankelijk van
 * de labels. Bij productgroepen van 31 tekens ("Brood / Desembroden - ...")
 * strekte het eerste label zich naar links buiten de viewBox uit, en die clipt.
 * Onzichtbaar in code, zichtbaar op het scherm als een half aslabel.
 *
 * Hier wordt niets uit de data gerekend — alleen tekengeometrie, net als in de
 * grafiekcomponenten zelf. De schaling van waarden blijft in het component.
 */

/** Vaste maten van het tekenvlak, gedeeld door Lijngrafiek en Staafgrafiek. */
export const VLAK = {
  breedte: 640,
  hoogte: 220,
  marge: { links: 56, rechts: 12, boven: 12, onder: 28 },
} as const;

/**
 * De zes huisstijlkleuren, op één adres. De reekskleuren uit het contract
 * (bordeaux, warmgrijs, geel) én de vaste tekenkleuren van de grafieken (as en
 * raster in warmgrijs, labels in zwart, de puntrand in wit) slaan hier aan.
 * Tot 18 augustus 2026 stond deze map bit-voor-bit dubbel in Lijngrafiek en
 * Staafgrafiek, met daarnaast losse hexwaarden in de SVG-attributen: één
 * kleur bijstellen betekende tien plaatsen zoeken.
 */
export const KLEUR = {
  beige: "#F4EDE6",
  bordeaux: "#A6192E",
  geel: "#F2F0A1",
  warmgrijs: "#C9C0AF",
  wit: "#FFFFFF",
  zwart: "#000000",
} as const;

/**
 * Geschatte breedte van één teken Inter Tight op 10px. Er kan in een
 * server-render niets gemeten worden, dus is deze schatting royaal genomen:
 * te ruim betekent wat extra witruimte, te krap betekent een afgesneden label.
 */
export const TEKENBREEDTE = 5.6;

/** De hoek waaronder lange labels staan, in graden. */
export const HOEK = 30;

/** Afstand van de basislijn tot het ankerpunt van een schuin label. */
export const LABELOFFSET = 14;

/** Onderaan blijft dit over onder het langste label. */
const VOETRUIMTE = 8;

/**
 * Speling op de berekende marges. De labelbreedte is een schatting; met een
 * marge van precies nul zou een lettertype dat een halve pixel breder valt het
 * eerste label alweer afsnijden. Vier pixels kosten niets en nemen dat risico weg.
 */
const SPELING = 4;

/**
 * Bovengrens voor de labelbreedte in px. Daarboven wordt afgekort: anders zou
 * één uitzonderlijk lang label het tekenvlak van de staven opeten. ~39 tekens.
 */
export const MAXLABEL = 220;

/** Labels langer dan dit worden afgekort; de volle tekst gaat naar een title. */
export const MAXTEKENS = Math.floor(MAXLABEL / TEKENBREEDTE);

const rad = (graden: number) => (graden * Math.PI) / 180;

export type Staafas = {
  /** Staan de labels schuin? Korte labels (ma, jan) blijven recht. */
  schuin: boolean;
  /** Linkermarge: groot genoeg dat het eerste schuine label binnen beeld valt. */
  links: number;
  /** Ondermarge onder de basislijn, groot genoeg voor het langste label. */
  ondermarge: number;
  /** Totale hoogte van de viewBox. Het plotvlak blijft altijd even hoog. */
  hoogte: number;
  /** De aangenomen labelbreedte in px, na de bovengrens. */
  labelbreedte: number;
  /** Boven dit aantal tekens wordt een label afgekort. */
  maxTekens: number;
};

/**
 * Bepaalt de marges uit de aslabels zelf.
 *
 * Het eerste label is het krappe geval: het staat rechts uitgelijnd op het
 * midden van de eerste staaf en loopt van daar naar links-onder. Horizontaal
 * heeft het `breedte · cos(hoek)` nodig, en dat moet passen binnen
 * `links + groepbreedte / 2`. Omdat de groepbreedte zelf van `links` afhangt,
 * staat de benodigde linkermarge hieronder in opgeloste vorm.
 */
export function berekenStaafas(labels: string[]): Staafas {
  const n = labels.length;
  const schuin = labels.some((l) => l.length > 6);

  if (!schuin || n === 0) {
    return {
      schuin: false,
      links: VLAK.marge.links,
      ondermarge: VLAK.marge.onder,
      hoogte: VLAK.hoogte,
      labelbreedte: 0,
      maxTekens: MAXTEKENS,
    };
  }

  const langste = Math.max(...labels.map((l) => l.length));
  const labelbreedte = Math.min(langste * TEKENBREEDTE, MAXLABEL);

  // links + (B − links − rechts) / (2n) ≥ breedte · cos(hoek), opgelost naar links.
  const nodigLinks =
    (labelbreedte * Math.cos(rad(HOEK)) -
      (VLAK.breedte - VLAK.marge.rechts) / (2 * n)) /
    (1 - 1 / (2 * n));

  const links = Math.max(VLAK.marge.links, Math.ceil(nodigLinks + SPELING));
  const ondermarge = Math.ceil(
    LABELOFFSET + labelbreedte * Math.sin(rad(HOEK)) + VOETRUIMTE + SPELING,
  );
  // Het plotvlak houdt de hoogte die het bij rechte labels ook had; alleen de
  // viewBox groeit mee, zodat de staven niet platter worden door lange namen.
  const plotvlak = VLAK.hoogte - VLAK.marge.boven - VLAK.marge.onder;
  const hoogte = VLAK.marge.boven + plotvlak + ondermarge;

  return { schuin: true, links, ondermarge, hoogte, labelbreedte, maxTekens: MAXTEKENS };
}

/**
 * Kort een label af op `maxTekens`, met een echt weglatingsteken. De volle
 * tekst hoort dan in een `<title>` te staan: afkorten mag, verzwijgen niet.
 */
export function kortAf(label: string, maxTekens: number): string {
  if (label.length <= maxTekens) return label;
  return `${label.slice(0, Math.max(maxTekens - 1, 1)).trimEnd()}…`;
}
