/**
 * Bronwacht: staat er nog leesbare tekst hard in een component?
 *
 * WAAROM DEZE TEST BESTAAT. Bij het invoeren van het Frans (14 augustus 2026)
 * is geteld hoeveel teksten nog onvertaald waren door de Nederlandse en de
 * Franse contractboom te vergelijken. Die teller is goed, maar hij kan per
 * constructie alleen zien wat door het contract gaat. Tekst die rechtstreeks
 * in een `.tsx` staat, komt in geen van beide bomen voor — en meldde zich dus
 * nergens. Op 15 augustus stonden er zo nog vijfentwintig Nederlandse teksten
 * op de schermen, waaronder vrijwel heel Instellingen, terwijl de teller
 * netjes zijn drieënzestig contractteksten opsomde.
 *
 * Dat is dezelfde fout als die van de eerste versie van die teller, en het
 * dagboek had haar al benoemd: een teller die alleen meet wat hij al kent,
 * meldt schoon zodra je hem niet gebruikt. Deze test meet de andere helft.
 *
 * Sinds 18 augustus scant hij ook de `.ts`-bestanden in app/ en lib/: de
 * foutmeldingen van server-acties bleken net zo goed schermtekst als JSX, en
 * precies daar stond de hele meldingslaag van het kostenmodel eentalig.
 *
 * WAT ER MOET GEBEUREN ALS HIJ FAALT. Zet de tekst in het woordenboek in
 * `lib/taal.ts`, met beide talen, en roep hem aan met `t("sleutel")`. Niet:
 * hem hieronder in TOEGESTAAN of MACHINEWOORDEN zetten. Die lijsten zijn voor
 * tekst die géén taal heeft — een bestandspad, een merknaam, een
 * contractwaarde — en elke regel erin draagt de reden waarom.
 */

import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const WORTEL = path.join(import.meta.dirname, "..");
const MAPPEN = ["app", "components", "lib"];

/**
 * Bronbestanden buiten die drie mappen. `proxy.ts` ligt per Next-conventie in
 * de wortel van platform/ en viel daardoor tot 18 augustus buiten de wacht —
 * precies het bestand dat elke bezoeker als eerste raakt.
 */
const LOSSE_BESTANDEN = ["proxy.ts"];

/**
 * Bestanden die de wacht overslaat, elk met de reden. Dit zijn geen
 * schermen: het zijn de woordenboeken zelf (die dragen per constructie beide
 * talen naast elkaar) en de modules waarvan de strings beheerdersfouten voor
 * de terminal of de log zijn — bewust eentalig gereedschap, geen tekst die
 * een lezer van het platform ooit als scherm ziet.
 */
const OVERGESLAGEN = new Set([
  "lib/taal.ts", // hét woordenboek: elke regel is per definitie tweetalig
  "lib/toelichting.ts", // de veldlabeltabel, zelfde [nl, fr]-vorm als het woordenboek
  "lib/stand.ts", // de statuswoorden, per taal naast elkaar
  "lib/format.ts", // de maandnamen per taal; verder alleen stringbewerking
  "lib/contract.ts", // alleen types: elke string is een contractmachinewaarde
  "lib/auth.ts", // werpt/logt beheerdersfouten (env-configuratie); geen schermtekst
  "lib/auth-supabase.ts", // idem: configuratie- en bereikbaarheidsfouten voor de log
  "lib/laadContract.ts", // werpt beheerdersfouten ("draai make contract"); geen schermtekst
  "lib/contract-bron.ts", // idem: configuratiefouten over omgevingsvariabelen
  // idem, en om dezelfde reden als laadContract.ts hierboven: PostgREST-loodwerk
  // (methode, headers, statusregels). Elke tekst die een lezer van dit formulier
  // ziet, is een woordenboeksleutel die de server-actie teruggeeft — deze module
  // geeft nooit tekst terug, alleen een reden voor de log.
  "lib/kostenmodel-db.ts",
  // idem, de derde toepassing van dezelfde keten: PostgREST-loodwerk voor de
  // sluitingskalender (migratie 011/012). Leest tabelrijen en geeft bij falen
  // alleen een reden voor de log; elke schermtekst is een woordenboeksleutel
  // uit de server-actie.
  "lib/sluitingsdagen-db.ts",
  // idem: PostgREST-loodwerk plus de zeven machinewaarden die migratie 010 als
  // `geval` teruggeeft ("vers", "gestrand", …). Die zeven zijn sleutels en geen
  // zinnen — de zin die erbij hoort staat als `sync.<geval>` in het
  // woordenboek, en dat is precies waar de wacht op wil dat ze staat.
  "lib/syncstand.ts",
  // idem, de vierde toepassing van dezelfde keten: PostgREST-loodwerk voor de
  // bronbestanden (migratie 015). De kolomnamen in de select en de statusregel
  // bij een weigering zijn machinetekst voor de log; elke zin die een lezer van
  // dit scherm ziet, is een woordenboeksleutel uit de server-actie of de pagina.
  "lib/deliveroo-upload-db.ts",
]);

/**
 * Tekst zonder taal. Wie hier iets toevoegt, schrijft erbij waarom het in
 * het Frans hetzelfde blijft; anders hoort het in het woordenboek.
 */
const TOEGESTAAN = new Set([
  "config/winkels.json", // een bestandspad, geen zin
  "Too Good To Go", // merknaam
  "Deliveroo", // merknaam
  "Odoo", // merknaam
  "Renard Bakery", // eigennaam
  "use client", // Next.js-directive, geen zin
  "use server", // Next.js-directive, geen zin
  "Enter", // KeyboardEvent.key, de naam van de toets
  "opacity 120ms", // CSS-overgangswaarde
  "_blank", // HTML-doelwaarde van een form/link, geen woord
  "--font-inter-tight", // CSS-variabele van next/font
]);

/**
 * Losse machinewoorden die als stringliteral in de code staan maar nooit als
 * tekst op een scherm: contractwaarden waar de code op vergelijkt, de namen
 * van schermen en formuliervelden, cookie-instellingen. Tot 18 augustus was
 * élk los woord in kleine letters vrijgesteld — zo ontsnapten "band", "groep"
 * en "groepen". Nu is de vrijstelling deze expliciete lijst: een nieuw los
 * Nederlands woord valt door de mand tot iemand hier opschrijft waarom niet.
 */
const MACHINEWOORDEN = new Set([
  // contractwaarden waarop de componenten vergelijken (lib/contract.ts)
  "euro",
  "aantal",
  "verschil",
  "neer",
  "op",
  "lijn",
  "staaf",
  "links",
  "rechts",
  "goed",
  "ingevuld",
  "suggestie",
  // contractveldnamen: sleutels van het antwoord ("kern" in data) en de
  // eigenschappen waarop gesorteerd wordt
  "kern",
  "weekdagmix",
  "verschuiving",
  "concentratie",
  "status",
  "soort",
  // taalcodes: de waarden van het Taal-type zelf
  "nl",
  "fr",
  // de waarden van CONTRACT_BRON (lib/contract-bron.ts)
  "bestand",
  "db",
  // de schermnamen van laadContract en de winkel-cookie
  "overzicht",
  "kanalen",
  "producten",
  "marge",
  "prognose",
  "stand",
  "sluitingsdagen",
  "winkels",
  "winkel",
  // machinesleutels van de sluitingskalender (migratie 011/012): de
  // toestanden en bronnen waarop code vergelijkt, en de veldnaamdelen van
  // het formulier (toestand:<datum>, periode:<n>:van, regel:weekdag)
  "open",
  "dicht",
  "onbekend",
  "periode",
  "feestdag",
  "van",
  "tot",
  "reden",
  "weekdag",
  "vanaf",
  // rollen en bronnen: machinesleutels uit auth en de envelope
  "beheerder",
  // formulierveldnamen (FormData.get) en cookie-attributen
  "gebruiker",
  "wachtwoord",
  "terug",
  "taal",
  "lax",
  "production",
  "naam",
  "omschrijving",
  // bestandsnamen en mapdelen in path.join-aanroepen
  "contract",
  "data",
  "config",
  "scripts",
  "bin",
  "python",
  // waarden van HTML/Next-machinerie: aria-current, font-display,
  // revalidatePath("/", "layout")
  "page",
  "swap",
  "layout",
  // de bronwaarde van bron_upload (migratie 015): de kolom `bron` draagt
  // 'deliveroo' in kleine letters als machinewaarde. De merknaam met
  // hoofdletter staat hierboven in TOEGESTAAN; dit is de databasewaarde.
  "deliveroo",
  // de namen van het hashalgoritme, zijn uitvoervorm en de codering waarin het
  // bestand in de json past: node crypto en Buffer noemen ze zo, in elke taal.
  "sha256",
  "hex",
  "base64",
]);

/** Padachtige tokens: routes ("/instellingen"), bestanden ("kostenmodel.json"),
 * extensies (".tmp"). Een pad draagt geen taal. */
const PADVORM = /^\.?[\w-]*[/.][\w./-]*$/;

/**
 * Woordenboek- en contractsleutels ("nav.prognose", "let_op", "odoo-kassa"):
 * kleine letters met punten, underscores of koppeltekens als naden. Een echte
 * zin haalt die vorm nooit; een sleutel is een machinewaarde.
 */
const SLEUTELVORM = /^[a-z][a-zA-Z0-9]*(?:[._-][a-zA-Z0-9]+)+$/;

function bronBestanden(map: string): string[] {
  const uit: string[] = [];
  for (const naam of readdirSync(map)) {
    const pad = path.join(map, naam);
    if (statSync(pad).isDirectory()) uit.push(...bronBestanden(pad));
    else if (naam.endsWith(".tsx") || naam.endsWith(".ts")) uit.push(pad);
  }
  return uit;
}

function zonderCommentaar(bron: string): string {
  return bron
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .replace(/^\s*\/\/.*$/gm, " ");
}

/**
 * `${…}` wordt `{}` — dezelfde gedaante als een invulplaats uit het
 * woordenboek. De oude aanpak (een regex zonder oog voor nesting) liet bij
 * `${t("x", { n: y })}` een staart ` })` achter, en dat restje codetekens
 * keurde de héle kandidaat als code goed — Nederlands in zo'n template
 * ontsnapte. Daarom hier een teller in plaats van een regex: pas als alle
 * accolades van het gat dicht zijn, gaat de tekst verder.
 */
function zonderInvullingen(s: string): string {
  let uit = "";
  let diepte = 0;
  for (let i = 0; i < s.length; i++) {
    if (diepte === 0 && s[i] === "$" && s[i + 1] === "{") {
      diepte = 1;
      i++;
      uit += "{}";
    } else if (diepte > 0) {
      if (s[i] === "{") diepte++;
      else if (s[i] === "}") diepte--;
    } else {
      uit += s[i];
    }
  }
  return uit;
}

/**
 * De drie plaatsen waar letterlijke JSX-tekst kan staan. Alle drie eisen ze
 * dat er géén accolade in de tekst zelf zit; zo blijft een expressie code en
 * wordt alleen wat eromheen staat als tekst gelezen.
 *
 *   >tekst<     een gewone tekstknoop
 *   >tekst{     tekst vlak vóór een expressie
 *   }tekst<     tekst vlak ná een expressie
 *
 * Die tweede en derde vorm zijn geen franje: zo stond er "laatste 30 dagen ·
 * aandeel{" "}" op het kanalenscherm, en precies die vorm ontsnapte aan de
 * eerste versie van deze wacht.
 *
 * Wat NIET werkt en waarom het hier niet staat: eerst alle `{...}` wegstrippen
 * en dan pas zoeken. De body van een component is zelf één accoladepaar, dus
 * dan verdwijnt het hele scherm en meldt de wacht altijd schoon -- dezelfde
 * val als de teller die deze test moest aanvullen.
 */
const TEKSTKNOPEN = [
  />([^<>{}]+)</g,
  />([^<>{}]+)\{/g,
  /\}([^<>{}]+)</g,
  // Tekst tussen twéé expressies — `{procent(x)} van de omzet {procent(y)}`.
  // Ontbrak tot 17 augustus; precies in die vorm stond er Nederlands op het
  // Franse prognosescherm.
  /\}([^<>{}]+)\{/g,
];

/**
 * Het vierde lek, gevonden 17 augustus: een stringliteral bínnen een expressie
 * die zelf op tekstpositie staat — `{n === 1 ? "1 punt" : `${n} punten`}` —
 * is voor de drie patronen hierboven onzichtbaar, want de tekst zit in de
 * accolades in plaats van ernaast. Dit patroon pakt de expressie tussen `>` en
 * `<` en haalt er de aanhalingstekens-literals uit; van template-literals
 * blijft de tekst tussen de `${...}`-gaten over. Attributen (className en co)
 * staan nooit op tekstpositie en blijven dus buiten schot.
 */
const EXPRESSIE_OP_TEKSTPOSITIE = />\s*\{([^<>]+)\}\s*</g;

function literalsUit(expressie: string): string[] {
  const uit: string[] = [];
  for (const m of expressie.matchAll(/"([^"]*)"|'([^']*)'/g)) {
    uit.push(m[1] ?? m[2] ?? "");
  }
  for (const m of expressie.matchAll(/`([^`]*)`/g)) {
    uit.push(zonderInvullingen(m[1] ?? ""));
  }
  return uit;
}

/**
 * Attributen waarvan de waarde door een mens gelezen of voorgelezen wordt.
 * Twee vormen: `titel="…"` en `titel={`…`}` — die tweede ontsnapte tot
 * 17 augustus ("Verwachte dagomzet, ${n} dagen vooruit" op het Franse
 * prognosescherm). Van een template blijft de tekst tussen de `${…}`-gaten
 * over; de gaten zelf zijn code.
 */
const ZICHTBARE_ATTRIBUTEN =
  /\b(placeholder|aria-label|aria-description|title|alt|label|titel|reden|ondertitel)\s*=\s*(?:"([^"]+)"|\{`([^`]+)`\})/g;

/**
 * Het vijfde lek, gevonden 17 augustus: een literal in een props-expressie die
 * geen attribuutwaarde en geen tekstpositie is — `data={{ kolommen: ["komt
 * van", …] }}` naar een tabelcomponent die hem als kop rendert. Op het Franse
 * productenscherm stonden zo "komt van", "van het assortiment" en "overige 23
 * producten", onzichtbaar voor alle patronen hierboven én voor de
 * contractteller (de tekst stond in geen van beide contractbomen).
 *
 * De dichting scant daarom álle string- en template-literals in het bestand en
 * laat de bestaande filters (codewoorden, codetekens, machinewoorden) de code
 * van het proza scheiden. Drie soorten waarden zijn taal-loos en gaan er
 * vooraf uit: `className`-waarden (CSS-klassen dragen spaties maar geen taal),
 * importpaden, en console-aanroepen — logregels voor de beheerder zijn bewust
 * eentalig gereedschap, net als de foutmeldingen in de overgeslagen
 * lib-bestanden hierboven.
 */
/** De attribuutnamen waarvan de waarde een mens bereikt; alle andere
 * attribuutwaarden ("text", "submit", "polite") zijn HTML-machinewoorden. */
const ZICHTBAAR_ATTRIBUUT = new Set([
  "placeholder",
  "aria-label",
  "aria-description",
  "title",
  "alt",
  "label",
  "titel",
  "reden",
  "ondertitel",
]);

function zonderTaalloos(bron: string): string {
  return (
    bron
      .replace(/\bclassName\s*=\s*(?:"[^"]*"|\{`[^`]*`\}|\{[^{}]*\})/g, " ")
      // Formulierveldnamen zijn machinesleutels ("kost:<id>:<groep>"), geen
      // tekst die een lezer ziet.
      .replace(/\bname\s*=\s*(?:"[^"]*"|\{`[^`]*`\})/g, " ")
      // Attribuutwaarden die geen mens leest (`type="text"`, `scope="col"`,
      // `aria-live="polite"`) zijn machinewoorden van HTML zelf. De zichtbare
      // attributen blijven staan: die vangt ZICHTBARE_ATTRIBUTEN hierboven,
      // en hun literals mogen gerust nogmaals door de zeef.
      .replace(/\b([\w-]+)\s*=\s*"([^"]*)"/g, (heel, naam: string) =>
        ZICHTBAAR_ATTRIBUUT.has(naam) ? heel : " ",
      )
      .replace(/\bconsole\.\w+\s*\([^)]*\)/g, " ")
      .replace(/\bimport\s[^;]*?from\s*"[^"]*"/g, " ")
      .replace(/\bfrom\s*"[^"]*"/g, " ")
  );
}

/**
 * CSS-klassen die niet in een `className`-attribuut staan (een ternair, een
 * const die later in een className belandt): elk token oogt als een
 * utility-klasse én draagt een koppelteken, dubbelepunt, schuine streep of
 * cijfer. Een echte zin haalt dat nooit met ál zijn woorden; twijfelgevallen
 * blijven dus hangen en worden met de hand beoordeeld.
 */
const KLASSE_TOKEN = /^[!a-z0-9:_/.\-\[\]%#()&>*~]+$/;
function lijktOpKlassen(s: string): boolean {
  // Een `{}` is een genormaliseerd `${…}`-gat (zie zonderInvullingen) en telt
  // niet mee: `${basis} bg-beige text-bordeaux` is nog steeds een klassenrij.
  const tokens = s.split(/\s+/).filter((t) => t !== "{}");
  return (
    tokens.length > 1 &&
    tokens.every((t) => KLASSE_TOKEN.test(t) && /[-:/0-9]/.test(t))
  );
}

/** SVG-paddata (het woordmerk): padcommando's, cijfers, komma's, punten. */
const SVG_PAD = /^M[0-9.,\-\sMmZzLlHhVvCcSsQqTtAaEe0-9]*$/;

function alleLiterals(bron: string): string[] {
  return literalsUit(zonderTaalloos(bron));
}

/**
 * Sleutelwoorden van de taal zelf. Een generiek type (`Record<A, B>`) heeft
 * een `<` en een `>` en lijkt na het wegstrippen van de accolades op een
 * tekstknoop. Nederlandse of Franse schermtekst bevat deze woorden niet, dus
 * dit onderscheidt code van proza zonder echte tekst te laten ontsnappen.
 */
const CODEWOORDEN =
  /\b(const|let|var|function|return|import|export|interface|type|typeof|await|async|new|null|undefined|true|false|try|catch|finally|else|throw|switch|case|break|continue|default|Record|Readonly|Promise|React|string|number|boolean)\b/;

/**
 * Leestekens die in code thuishoren en niet in een Nederlandse of Franse
 * schermtekst. De twee patronen die tekst náást een expressie oppikken, zien
 * onvermijdelijk ook stukjes JavaScript; dit is wat die twee uit elkaar houdt.
 *
 * Bewust NIET in deze lijst: punt, komma, puntkomma, dubbele punt, vraagteken,
 * procent, koppelteken en de kastlijn. Die komen in echte schermtekst voor, en
 * ze weren zou de wacht blind maken voor precies het soort zin dat hij zoekt.
 *
 * Ook niet (meer) in de lijst: het isgelijkteken. Dat lag hier tot 18
 * augustus, en daardoor gold "= Brutomarge" — een rijlabel dat een mens
 * leest — als code. Alleen de samengestelde operatoren zijn ondubbelzinnig
 * code, en die staan hieronder apart.
 */
const CODETEKENS = /[()[\]`$|&!<>@#\\]/;
/**
 * Wat er van het isgelijkteken als codesignaal overblijft: de samengestelde
 * operatoren, en een `=` dat vastgeplakt zit aan een naam of een
 * aanhalingsteken (`ondertitel=`, `width=`) — dat is een attribuut of een
 * toewijzing. Proza gebruikt een los isgelijkteken met ruimte eromheen
 * ("= Brutomarge"), en juist dát moet door de zeef heen blijven vallen.
 */
const CODE_OPERATOREN = /=>|===|!==|==|&&|\|\||[\w"'-]=/;

function verdachteTeksten(bron: string): string[] {
  const gevonden: string[] = [];

  for (const m of bron.matchAll(ZICHTBARE_ATTRIBUTEN)) {
    if (m[2] !== undefined) gevonden.push(m[2]);
    else gevonden.push(zonderInvullingen(m[3]!));
  }

  const kaal = zonderCommentaar(bron);
  for (const patroon of TEKSTKNOPEN) {
    for (const m of kaal.matchAll(patroon)) gevonden.push(m[1]!);
  }
  for (const m of kaal.matchAll(EXPRESSIE_OP_TEKSTPOSITIE)) {
    gevonden.push(...literalsUit(m[1]!));
  }
  gevonden.push(...alleLiterals(kaal));

  return gevonden
    .map((s) => s.replace(/\s+/g, " ").trim())
    .filter((s) => {
      if (TOEGESTAAN.has(s)) return false;
      if (CODEWOORDEN.test(s) || CODETEKENS.test(s)) return false;
      if (CODE_OPERATOREN.test(s)) return false;
      if (lijktOpKlassen(s) || SVG_PAD.test(s)) return false;
      // Twee letters achter elkaar maakt het een woord; losse leestekens,
      // cijfers, pijlen en scheidingstekens blijven buiten schot.
      if (!/\p{Letter}{2,}/u.test(s)) return false;
      // Machinewaarden: paden, sleutels, en de expliciete woordenlijst.
      // Meer vrijstelling is er niet — een los Nederlands woord ("band",
      // "groepen") is sinds 18 augustus gewoon een overtreding.
      if (PADVORM.test(s) || SLEUTELVORM.test(s)) return false;
      // Een sleutel met invulgaten ("periodes.{}", "doel-{}", "{}-tab-{}"):
      // elk gat is een genormaliseerd `${…}` en de rest is een machinesleutel
      // — spaties zouden er een zin van maken, en die vallen hier dus niet
      // onder. Meerdere gaten maken het niet taliger (18 aug: de tab-ids van
      // PeriodePaneel dragen er twee).
      if (/^[\w.-]*(?:\{\}[\w.-]*)+$/.test(s)) return false;
      if (!/\s/.test(s) && !/^\p{Lu}/u.test(s) && MACHINEWOORDEN.has(s)) {
        return false;
      }
      return true;
    });
}

test("geen leesbare tekst hard in de componenten", () => {
  const overtredingen: string[] = [];

  const bestanden = [
    ...MAPPEN.flatMap((map) => bronBestanden(path.join(WORTEL, map))),
    ...LOSSE_BESTANDEN.map((naam) => path.join(WORTEL, naam)),
  ];
  for (const bestand of bestanden) {
    const relatief = path.relative(WORTEL, bestand);
    if (OVERGESLAGEN.has(relatief)) continue;
    const bron = readFileSync(bestand, "utf-8");
    for (const tekst of verdachteTeksten(bron)) {
      overtredingen.push(`${relatief}: ${tekst}`);
    }
  }

  assert.deepEqual(
    overtredingen,
    [],
    "Deze teksten staan hard in een component en bestaan dus maar in één " +
      "taal. Zet ze in het woordenboek in lib/taal.ts en roep ze aan met " +
      `t("sleutel"):\n  ${overtredingen.join("\n  ")}\n`,
  );
});
