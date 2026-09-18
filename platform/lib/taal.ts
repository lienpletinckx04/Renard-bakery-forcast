/**
 * Nederlands en Frans, want de bakkerij staat in Elsene.
 *
 * WAAROM EEN COOKIE EN GEEN `/fr/`-PAD. De Next-gids raadt een taalpad aan
 * (`app/[lang]/...`), en voor een publieke site is dat juist: zoekmachines
 * moeten elke taal als eigen adres kunnen indexeren. Dit is een afgeschermd
 * dashboard achter een login — er is geen zoekmachine die het ziet, en het
 * hele adressenstelsel omgooien zou elke bestaande link breken. De winkelkeuze
 * gebruikt al een cookie (`WINKEL_COOKIE`); de taalkeuze volgt datzelfde
 * patroon. Eén manier om een leesvoorkeur te bewaren, niet twee.
 *
 * WAAR DE GRENS LIGT. Dit bestand vertaalt de vaste teksten van de schermen:
 * navigatie, koppen, knoppen, kolomnamen. Het vertaalt GEEN cijfers en geen
 * labels die uit het contract komen — die worden in de berekeningslaag
 * gebouwd en komen per taal uit `platform/contract/<taal>/`. Zie
 * `bakkerij/taal.py`. Harde regel 4 blijft dus onverkort: de UI rekent niet,
 * en ze verzint ook geen labels.
 *
 * GETALLEN BLIJVEN GETALLEN. `format.ts` groepeert in beide talen gelijk
 * ("€ 1.234,56"). Dat is geen slordigheid: het Belgisch Frans schrijft in de
 * praktijk dezelfde punt en komma, en de scheidingstekens verzetten zou de
 * enige laag raken waar dit platform met bedragen omgaat. Wat wél meegaat zijn
 * de maandnamen, en die staan hier.
 */

export const TALEN = ["nl", "fr"] as const;
export type Taal = (typeof TALEN)[number];

export const STANDAARDTAAL: Taal = "nl";
export const TAAL_COOKIE = "renard_taal";

/** Een onbekende waarde uit een cookie of URL wordt nooit vertrouwd. */
export function alsTaal(waarde: string | undefined | null): Taal {
  return TALEN.includes(waarde as Taal) ? (waarde as Taal) : STANDAARDTAAL;
}

/**
 * Het woordenboek. Eén sleutel per tekst, allebei de talen ernaast, zodat een
 * ontbrekende vertaling een typefout is en niet iets dat je pas op het scherm
 * ziet. `{...}` in een tekst is een invulplaats.
 */
const WOORDEN = {
  // --- navigatie en chroom ---
  "nav.dagoverzicht": ["Dagoverzicht", "Aperçu du jour"],
  "nav.kanalen": ["Verkoopkanalen", "Canaux de vente"],
  "nav.producten": ["Productmix", "Mix de produits"],
  "nav.marge": ["Margebewaking", "Suivi des marges"],
  "nav.sluitingsdagen": ["Sluitingsdagen", "Jours de fermeture"],
  "nav.prognose": ["Prognose", "Prévision"],
  "nav.deliveroo": ["Deliveroo-import", "Import Deliveroo"],
  "nav.instellingen": ["Instellingen", "Paramètres"],
  "nav.ondertitel": ["Financieel overzicht", "Aperçu financier"],
  "nav.hoofdnavigatie": ["Hoofdnavigatie", "Navigation principale"],
  "nav.afmelden": ["Afmelden", "Se déconnecter"],
  "nav.naarInhoud": ["Naar de inhoud", "Aller au contenu"],

  // --- taalkiezer ---
  "taal.label": ["Taal", "Langue"],

  // --- winkelkiezer ---
  "winkel.label": ["Winkel", "Magasin"],
  "winkel.kies": ["Kies een winkel", "Choisir un magasin"],
  "winkel.alle": ["Alle winkels", "Tous les magasins"],
  "winkel.alleSamen": ["Alle winkels samen", "Tous les magasins réunis"],
  "winkel.inclusiefNietToegewezen": [
    ", inclusief niet-toegewezen filialen",
    ", y compris les points de vente non attribués",
  ],
  "winkel.alleen": ["Alleen {naam}", "Uniquement {naam}"],

  // --- versheid en voettekst ---
  "versheid.cijfersTot": [
    "Cijfers tot en met {datum}",
    "Chiffres jusqu'au {datum} inclus",
  ],
  "versheid.onbekend": [
    "Meetbereik onbekend: het contract meldt geen gemeten open winkeldag",
    "Période de mesure inconnue : le contrat ne signale aucun jour d'ouverture mesuré",
  ],
  "versheid.verwerkt": ["verwerkt op {datum}", "traité le {datum}"],
  "voet.bron": ["bron", "source"],

  // --- datakwaliteit ---
  "kwaliteit.letOp": ["Let op: datakwaliteit", "Attention : qualité des données"],
  "kwaliteit.alarm": ["Alarm: datakwaliteit", "Alerte : qualité des données"],

  // --- login ---
  "login.titel": ["Aanmelden", "Connexion"],
  "login.gebruiker": ["Gebruikersnaam", "Nom d'utilisateur"],
  "login.wachtwoord": ["Wachtwoord", "Mot de passe"],
  "login.knop": ["Aanmelden", "Se connecter"],
  "login.bezig": ["Bezig…", "En cours…"],
  "login.ondertitel": [
    "Toegang voor benoemde gebruikers.",
    "Accès réservé aux utilisateurs désignés.",
  ],
  "login.merkregel": ["Artisan sourdough bakery", "Artisan sourdough bakery"],
  "login.fotoAlt": [
    "Broodzakken en brood van Renard Bakery",
    "Sacs à pain et pains de Renard Bakery",
  ],
  // De foutmeldingen van het aanmelden. Ze komen uit een server-actie en gaan
  // als sleutel over de lijn, niet als tekst: welke taal er geldt, weet de
  // bladzijde en niet de actie.
  "login.geenGebruikers": [
    "Er zijn nog geen gebruikers ingesteld op deze omgeving.",
    "Aucun utilisateur n'est encore configuré dans cet environnement.",
  ],
  "login.leegVeld": [
    "Vul een gebruikersnaam en een wachtwoord in.",
    "Saisissez un nom d'utilisateur et un mot de passe.",
  ],
  "login.opSlot": [
    "Te veel mislukte pogingen voor deze naam. Wacht een minuut en probeer opnieuw.",
    "Trop de tentatives échouées pour ce nom. Attendez une minute et réessayez.",
  ],
  "login.mislukt": [
    "Gebruikersnaam of wachtwoord klopt niet.",
    "Le nom d'utilisateur ou le mot de passe est incorrect.",
  ],

  // --- Dagoverzicht ---
  "dag.titel": ["Dagoverzicht", "Aperçu du jour"],
  "dag.ondertitel": [
    "Winkelverkoop tot en met de laatste gemeten open dag.",
    "Ventes en magasin jusqu'au dernier jour d'ouverture mesuré inclus.",
  ],
  "dag.omzetverloop": ["Omzetverloop", "Évolution du chiffre d'affaires"],
  "dag.omzetverloop30": [
    "Omzetverloop laatste 30 open dagen",
    "Évolution du chiffre d'affaires sur les 30 derniers jours d'ouverture",
  ],
  "dag.waarvandaan": [
    "Waar komt de verandering vandaan: klanten of mandje?",
    "D'où vient la variation : les clients ou le panier ?",
  ],
  "dag.weekdag": [
    "Gemiddelde omzet per weekdag",
    "Chiffre d'affaires moyen par jour de la semaine",
  ],
  "dag.permaand": [
    "Omzet per open dag, per maand",
    "Chiffre d'affaires par jour d'ouverture, par mois",
  ],
  "dag.jaaropjaar": ["Jaar-op-jaar per maand", "Année après année, par mois"],
  "dag.opvallend": ["Opvallende dagen", "Jours remarquables"],
  "dag.andereHelftVoor": [
    "De andere helft van de groeivraag — meer stuks, of een andere prijs? — staat op",
    "L'autre moitié de la question de la croissance — plus d'unités, ou un autre prix ? — se trouve dans",
  ],
  "dag.andereHelftNa": [
    ", omdat ze per product gerekend wordt. De twee ontbindingen staan bewust niet naast elkaar: deze gaat per dag, die over het hele venster.",
    ", car elle se calcule par produit. Les deux décompositions ne sont volontairement pas côte à côte : celle-ci va par jour, l'autre porte sur toute la période.",
  ],
  "dag.aandeelWeekdag": [
    "Aandeel per weekdag in de week",
    "Part de chaque jour de la semaine",
  ],

  // --- Verkoopkanalen ---
  "kanalen.titel": ["Verkoopkanalen", "Canaux de vente"],
  "kanalen.ondertitel": [
    "Wat elk kanaal werkelijk bijdraagt: bruto, commissie en netto, elk over zijn eigen laatste 30 dagen.",
    "Ce que chaque canal rapporte réellement : brut, commission et net, chacun sur ses 30 derniers jours.",
  ],
  "kanalen.watblijft": [
    "Wat blijft er over per kanaal?",
    "Que reste-t-il par canal ?",
  ],
  "kanalen.geenKoppeling": [
    "Deze koppeling bestaat nog niet.",
    "Cette intégration n'existe pas encore.",
  ],
  "kanalen.brutoVerkocht": ["Bruto verkocht", "Vendu brut"],
  "kanalen.perMeetdag": ["Gemiddelde per meetdag", "Moyenne par jour mesuré"],
  "kanalen.wigUitleg": [
    "Laatste 30 dagen per kanaal. Bruto is wat de klant betaalde, commissie is wat het platform inhield, netto is wat er binnenkwam — de omzet elders op de schermen is altijd netto.",
    "30 derniers jours par canal. Le brut est ce que le client a payé, la commission est ce que la plateforme a retenu, le net est ce qui est effectivement rentré — le chiffre d'affaires affiché ailleurs est toujours net.",
  ],
  "kanalen.onbekend": ["onbekend", "inconnu"],
  "kanalen.geen": ["geen", "aucune"],
  "kanalen.laatste30Aandeel": [
    "laatste 30 dagen · aandeel",
    "30 derniers jours · part",
  ],
  "kanalen.commissiePct": ["Commissie ({pct})", "Commission ({pct})"],

  // --- Productmix ---
  "prod.titel": ["Productmix", "Mix de produits"],
  "prod.ondertitel": [
    "Waar de omzet vandaan komt, per product en per groep.",
    "D'où vient le chiffre d'affaires, par produit et par groupe.",
  ],
  "prod.top30": [
    "Topproducten laatste 30 dagen",
    "Meilleurs produits des 30 derniers jours",
  ],
  "prod.stuksOfPrijs": [
    "Meer stuks, of een andere prijs?",
    "Plus d'unités, ou un autre prix ?",
  ],
  "prod.watbeweegt": ["Wat beweegt er", "Ce qui bouge"],
  "prod.stijgers": ["Sterkste stijgers", "Plus fortes hausses"],
  "prod.dalers": ["Sterkste dalers", "Plus fortes baisses"],
  "prod.leunt": ["Waar de omzet op leunt", "Sur quoi repose le chiffre d'affaires"],
  "prod.verkocht": ["Producten verkocht", "Produits vendus"],
  "prod.nieuw": ["nieuw", "nouveau"],
  "prod.pergroep": [
    "Omzet per productgroep",
    "Chiffre d'affaires par groupe de produits",
  ],
  "prod.staart": [
    "Staart, {aantal} producten",
    "Traîne, {aantal} produits",
  ],
  "prod.vanDeOmzet": [
    "· {pct} van de omzet",
    "· {pct} du chiffre d'affaires",
  ],
  "prod.vanGroepNaarProduct": [
    "Van groep naar product",
    "Du groupe au produit",
  ],

  // --- Margebewaking ---
  "marge.titel": ["Margebewaking", "Suivi des marges"],
  "marge.ondertitel": [
    "Brutomarge op de winkelomzet, opgebouwd uit de eigen kostencriteria.",
    "Marge brute sur les ventes en magasin, construite à partir de vos propres critères de coûts.",
  ],
  "marge.pergroep": ["Marge per productgroep", "Marge par groupe de produits"],
  "marge.nogniet": ["Nog niet beschikbaar.", "Pas encore disponible."],
  "marge.opbouwLeeg": ["niet ingevuld", "non saisi"],
  "marge.gewogen": ["Gewogen brutomarge", "Marge brute pondérée"],
  "marge.brutomarge30": ["Brutomarge, 30 dagen", "Marge brute, 30 jours"],
  "marge.dekking": ["Dekking van de invoer", "Couverture des données saisies"],
  "marge.vanomzet": [
    "Van omzet naar marge, 30 dagen",
    "Du chiffre d'affaires à la marge, 30 jours",
  ],
  "marge.gedekt": ["Gedekte winkelomzet", "Chiffre d'affaires magasin couvert"],
  "marge.brutoPerGroep": [
    "Brutomarge per productgroep, 30 dagen",
    "Marge brute par groupe de produits, 30 jours",
  ],
  "marge.perGroepKort": ["Per productgroep", "Par groupe de produits"],
  "marge.opGedekteOmzet": [
    "op {bedrag} gedekte omzet",
    "sur {bedrag} de chiffre d'affaires couvert",
  ],
  "marge.overGedekt": [
    "over de gedekte winkelomzet",
    "sur le chiffre d'affaires magasin couvert",
  ],
  "marge.heeftKosten": [
    "van de winkelomzet heeft ingevulde kosten",
    "du chiffre d'affaires magasin a des coûts saisis",
  ],
  // De groepenteller in de kostenopbouwtabel. Enkelvoud en meervoud zijn twee
  // sleutels omdat de vertaalfunctie geen meervoudsregels kent en het scherm
  // die keuze als presentatie zelf maakt (zoals het kostenformulier hieronder).
  "marge.groepEnkelvoud": ["({n} groep)", "({n} groupe)"],
  "marge.groepMeervoud": ["({n} groepen)", "({n} groupes)"],
  "marge.streepjeUitleg": [
    "Een streepje is geen nul: een groep zonder ingevulde kosten telt niet mee in het gewogen cijfer en staat hier open. De opbouw en de percentages komen uit het kostenmodel op Instellingen; de bedragen zijn omzet maal die percentages, gerekend door de berekeningslaag.",
    "Un tiret n'est pas un zéro : un groupe sans coûts saisis n'entre pas dans le chiffre pondéré et reste ouvert ici. La composition et les pourcentages proviennent du modèle de coûts dans Paramètres ; les montants sont le chiffre d'affaires multiplié par ces pourcentages, calculés par la couche de calcul.",
  ],

  // --- Prognose ---
  "prog.titel": ["Prognose", "Prévision"],
  "prog.opbouwKolom": [
    "Opbouw: basis × niveau × kalender",
    "Composition : base × niveau × calendrier",
  ],
  "prog.verwachtTotaal": ["Verwacht totaal", "Total attendu"],
  "prog.hoelezen": [
    "Hoe deze prognose gelezen moet worden",
    "Comment lire cette prévision",
  ],
  "prog.percategorie": ["Verwachting per categorie", "Prévision par catégorie"],
  "prog.perdag": ["Per dag", "Par jour"],
  // Blijft in de kop staan als "Per dag" dichtgeklapt is, zodat de kaart ook
  // dicht zegt hoe groot ze is.
  "prog.dagenInVenster": ["{n} dagen", "{n} jours"],
  // Idem voor de categoriekaart: dicht geklapt zegt de kop hoeveel er onder zit.
  "prog.categorieenInVenster": ["{n} categorieën", "{n} catégories"],
  "prog.hoegoed": [
    "Hoe goed voorspelde het model tot nu?",
    "Quelle a été la justesse du modèle jusqu'ici ?",
  ],
  "prog.gemetenDagen": ["Gemeten dagen", "Jours mesurés"],
  "prog.gemAfwijking": ["Gemiddelde afwijking", "Écart moyen"],
  "prog.modelkaart": ["Modelkaart", "Fiche du modèle"],
  "prog.ondertitelMet": [
    "Verwachte dagomzet voor {n} dagen vooruit, met bandbreedte. De gele band toont de onzekerheidsmarge. Welke dagen dat precies zijn, staat in de tabel.",
    "Chiffre d'affaires journalier attendu pour les {n} prochains jours, avec intervalle. La bande jaune indique la marge d'incertitude. Le détail des jours figure dans le tableau.",
  ],
  "prog.ondertitelZonder": [
    "Verwachte dagomzet per dag, met bandbreedte.",
    "Chiffre d'affaires journalier attendu, avec intervalle.",
  ],
  "prog.somVan": [
    "som van {n} dagverwachtingen",
    "somme de {n} prévisions journalières",
  ],
  "leeg.prognosedagen": [
    "Het contract levert geen prognosedagen, en geeft geen reden waarom niet.",
    "Le contrat ne fournit aucun jour de prévision, et n'indique pas pourquoi.",
  ],

  // --- Instellingen ---
  "inst.titel": ["Instellingen", "Paramètres"],
  "inst.ondertitel": [
    "De stand van het platform, het kostenmodel en de winkels.",
    "L'état de la plateforme, le modèle de coûts et les magasins.",
  ],
  "inst.leeft": ["Leeft het platform?", "La plateforme est-elle à jour ?"],
  "inst.bronnen": ["Bronnen", "Sources"],

  // --- De dodemansknop: leeft de nachtelijke synchronisatie nog? ---
  // Eén zin per geval, uit db/migraties/010_syncstand.sql. De sleutels zijn
  // machinewaarden uit de database; hier staat de taal.
  "sync.titel": [
    "Nachtelijke synchronisatie",
    "Synchronisation nocturne",
  ],
  "sync.voettekst": [
    "Let op: synchronisatie",
    "Attention : synchronisation",
  ],
  "sync.nooit": [
    "De nachtelijke synchronisatie heeft nog niet gedraaid; de planning staat uit en de cijfers worden met de hand ververst.",
    "La synchronisation nocturne n'a pas encore tourné : la planification est désactivée et les chiffres sont actualisés à la main.",
  ],
  "sync.vers": [
    "De jongste synchronisatie is geslaagd op {moment}.",
    "La dernière synchronisation a réussi le {moment}.",
  ],
  "sync.achter": [
    "De jongste geslaagde synchronisatie was op {moment}; er is sindsdien minstens één nacht overgeslagen.",
    "La dernière synchronisation réussie date du {moment} ; au moins une nuit a été sautée depuis.",
  ],
  "sync.oud": [
    "De jongste geslaagde synchronisatie was op {moment}, meer dan drie dagen geleden. De cijfers hieronder zijn niet ververst sindsdien.",
    "La dernière synchronisation réussie date du {moment}, il y a plus de trois jours. Les chiffres ci-dessous n'ont pas été actualisés depuis.",
  ],
  "sync.gefaald": [
    "De jongste synchronisatie is gefaald. De cijfers staan op de stand van de laatste geslaagde run.",
    "La dernière synchronisation a échoué. Les chiffres reflètent la dernière exécution réussie.",
  ],
  "sync.loopt": [
    "Er loopt op dit moment een synchronisatie.",
    "Une synchronisation est en cours.",
  ],
  "sync.gestrand": [
    "Een synchronisatie is begonnen en nooit afgemaakt. Zolang dat zo staat, ververst er niets.",
    "Une synchronisation a démarré sans jamais se terminer. Tant que cela reste ainsi, rien ne s'actualise.",
  ],
  "sync.geenGeslaagde": [
    "Er is nog geen enkele geslaagde synchronisatie.",
    "Aucune synchronisation n'a encore réussi.",
  ],
  "sync.melding": ["Melding: {tekst}", "Message : {tekst}"],
  "inst.kostenmodel": [
    "Kostenmodel per productgroep",
    "Modèle de coûts par groupe de produits",
  ],
  "inst.hoewerkt": ["Hoe dit werkt", "Comment cela fonctionne"],
  "inst.winkels": ["Winkels", "Magasins"],
  "inst.gebruikers": ["Gebruikers", "Utilisateurs"],
  "inst.nieuwCriterium": [
    "Naam van een nieuw criterium",
    "Nom d'un nouveau critère",
  ],
  "inst.herrekenen": ["Bezig met herrekenen…", "Recalcul en cours…"],
  "inst.opslaan": ["Opslaan", "Enregistrer"],
  "inst.nieuwPlaceholder": [
    "nieuw criterium, bv. Verpakking",
    "nouveau critère, p. ex. Emballage",
  ],
  "inst.geenGroepen": [
    "Er zijn nog geen productgroepen met gemeten omzet; zonder groepen valt er niets in te vullen.",
    "Il n'y a pas encore de groupes de produits avec un chiffre d'affaires mesuré ; sans groupes, il n'y a rien à saisir.",
  ],
  "inst.wachters": ["Wachters", "Sentinelles"],
  // De uitklap achter één bron- of wachterregel. De regel zelf (naam, status,
  // meetdag, aantal) blijft staan en lijnt in kolommen uit; de toelichting
  // eronder was met vijf bronnen en zeven wachters een lap tekst.
  "inst.toelichting": ["toelichting", "détail"],
  "inst.laatsteMeetdag": ["laatste meetdag {datum}", "dernier jour mesuré {datum}"],
  "inst.geenMeetdag": ["geen meetdag", "aucun jour mesuré"],
  "inst.rijen": ["{aantal} rijen", "{aantal} lignes"],
  "inst.kostenVoedt": [
    "Deze invoer voedt het scherm Margebewaking: brutomarge = 100 min de som van de ingevulde criteria. Een leeg veld betekent “niet ingevuld” en telt nergens als nul mee; alleen een beheerder kan opslaan.",
    "Ces données alimentent l'écran Suivi des marges : marge brute = 100 moins la somme des critères saisis. Un champ vide signifie « non saisi » et ne compte jamais comme un zéro ; seul un administrateur peut enregistrer.",
  ],
  "inst.uitlegCriterium": [
    "Elk criterium is een kostensoort als percentage van de omzet van een groep: grondstoffen (foodcost), verlies en verspilling, basisingrediënten, verpakking — wat de zaak zelf relevant vindt. Het menu is vrij aan te passen; de cijfers zijn een schatting van de zaakvoerder en per groep later bij te stellen.",
    "Chaque critère est un type de coût exprimé en pourcentage du chiffre d'affaires d'un groupe : matières premières (food cost), pertes et gaspillage, ingrédients de base, emballage — ce que l'entreprise juge pertinent. Le menu est librement modifiable ; les chiffres sont une estimation du gérant et peuvent être ajustés groupe par groupe.",
  ],
  "inst.uitlegReferentie": [
    "Ter referentie uit de sector: een foodcost rond de 30% geldt in de horeca als gangbaar, met uitschieters tot 45%; voor verlies wordt vaak zo’n 5% gerekend en voor basisingrediënten 1 à 2%. Dat zijn richtwaarden om de eigen schatting tegen af te zetten, geen norm voor deze bakkerij.",
    "À titre de référence sectorielle : un food cost d'environ 30 % est courant en horeca, avec des pointes jusqu'à 45 % ; pour les pertes on compte souvent quelque 5 %, et 1 à 2 % pour les ingrédients de base. Ce sont des ordres de grandeur pour situer sa propre estimation, pas une norme pour cette boulangerie.",
  ],
  "inst.uitlegNaOpslaan": [
    "Na het opslaan wordt het contract herrekend en toont Margebewaking meteen de nieuwe opbouw. Wat níét is ingevuld, blijft eerlijk buiten het gewogen cijfer.",
    "Après l'enregistrement, le contrat est recalculé et Suivi des marges affiche immédiatement la nouvelle composition. Ce qui n'est pas saisi reste honnêtement en dehors du chiffre pondéré.",
  ],
  "inst.nietToegewezen": [
    "Niet aan een winkel toegewezen en dus alleen in het totaal zichtbaar: filiaal {filialen}. Toewijzen kan in",
    "Non attribué à un magasin et donc visible uniquement dans le total : point de vente {filialen}. L'attribution se fait dans",
  ],
  "inst.winkelOvergeslagen": [
    "{naam} staat in de winkelindeling maar heeft geen eigen schermen gekregen:",
    "{naam} figure dans la répartition des magasins mais n'a pas reçu ses propres écrans :",
  ],
  "inst.eenGeheel": [
    "Alle verkooppunten tellen nu als één geheel.",
    "Tous les points de vente comptent actuellement comme un seul ensemble.",
  ],
  "inst.winkelbestandGenegeerd": [
    " Het winkelbestand wordt genegeerd: {melding}",
    " Le fichier des magasins est ignoré : {melding}",
  ],
  "inst.winkelsLater": [
    " Zodra er meer vestigingen zijn, wijst de beheerder in data/config/winkels.json filialen aan winkels toe; elke winkel krijgt dan eigen schermen en een eigen gebackteste prognose, en het totaal blijft bestaan.",
    " Dès qu'il y aura plusieurs établissements, l'administrateur attribuera les points de vente à des magasins dans data/config/winkels.json ; chaque magasin aura alors ses propres écrans et sa propre prévision backtestée, et le total subsistera.",
  ],
  "inst.gebruikersLater": [
    // Deze tekst zei tot 18 aug 2026 "komt er samen met de database (S2)".
    // Twee fouten in één zin: de database staat er sinds die avond, en `S2`
    // is onze eigen blokkadecode uit todo.md — die hoort niet op een scherm
    // van de klant. Waar het nu écht op wacht, is de gebruikerslijst.
    "Gebruikersbeheer vanuit dit scherm komt er samen met de aanmelding via Supabase; daarvoor is de gebruikerslijst van de bakkerij nodig. Tot dan worden gebruikers vastgelegd in de omgevingsvariabele van het platform; vraag de beheerder van de hosting om iemand toe te voegen of te verwijderen. Rollen: lezer (ziet alles, wijzigt niets) en beheerder (beheert instellingen zoals het kostenmodel).",
    "La gestion des utilisateurs depuis cet écran arrivera avec la connexion via Supabase ; elle nécessite la liste des utilisateurs de la boulangerie. D'ici là, les utilisateurs sont définis dans la variable d'environnement de la plateforme ; demandez à l'administrateur de l'hébergement d'ajouter ou de supprimer quelqu'un. Rôles : lecteur (voit tout, ne modifie rien) et administrateur (gère les paramètres tels que le modèle de coûts).",
  ],

  // --- het kostenformulier ---
  "inst.menuVoorzet": [
    "Dit menu is een voorzet naar de gangbare foodcost-opbouw; er hangt nog geen enkel cijfer aan. Pas het gerust aan: hernoem, verwijder of voeg toe wat bij de eigen kostenstructuur past.",
    "Ce menu est une proposition inspirée de la structure de food cost habituelle ; aucun chiffre n'y est encore attaché. Adaptez-le librement : renommez, supprimez ou ajoutez ce qui correspond à votre propre structure de coûts.",
  ],
  "inst.deCriteria": ["De criteria (het menu)", "Les critères (le menu)"],
  "inst.verwijderen": ["Verwijderen", "Supprimer"],
  "inst.toevoegen": ["Toevoegen", "Ajouter"],
  "inst.hoogstensCriteria": [
    "hoogstens {aantal} criteria",
    "{aantal} critères au maximum",
  ],
  "inst.naamVanCriterium": [
    "Naam van criterium {nummer}",
    "Nom du critère {nummer}",
  ],
  "inst.omschrijvingPlaceholder": [
    "omschrijving (optioneel)",
    "description (facultatif)",
  ],
  "inst.omschrijvingVan": ["Omschrijving van {naam}", "Description de {naam}"],
  "inst.criteriumNummer": ["criterium {nummer}", "critère {nummer}"],
  "inst.criterium": ["criterium", "critère"],
  "inst.bevestigVerwijder": [
    "Criterium \"{naam}\" verwijderen? De ingevulde percentages van deze kolom gaan bij het opslaan mee verloren.",
    "Supprimer le critère « {naam} » ? Les pourcentages saisis dans cette colonne seront perdus lors de l'enregistrement.",
  ],
  "inst.tabelBijschrift": [
    "Kosten per productgroep per criterium, als percentage van de omzet van die groep",
    "Coûts par groupe de produits et par critère, en pourcentage du chiffre d'affaires de ce groupe",
  ],
  "inst.celLabel": [
    "{criterium} van {groep}, percentage",
    "{criterium} de {groep}, pourcentage",
  ],
  "inst.allesInPct": [
    "Alles in % van de omzet van de groep. De brutomarge-kolom is 100 min de som van de ingevulde criteria, herrekend door de berekeningslaag bij het opslaan.",
    "Tout est exprimé en % du chiffre d'affaires du groupe. La colonne marge brute vaut 100 moins la somme des critères saisis, recalculée par la couche de calcul lors de l'enregistrement.",
  ],
  "inst.zonderCriteria": [
    "Zonder criteria valt er niets in te vullen; opslaan maakt dan ook alle eerdere kosten leeg.",
    "Sans critères, il n'y a rien à saisir ; enregistrer effacera donc tous les coûts précédents.",
  ],

  // --- de uitkomsten van het kostenmodel-opslaan ---
  // De server-actie geeft SLEUTELS terug, geen zinnen, om dezelfde reden als
  // bij het aanmelden (zie login/acties.ts): de actie kent de taal van de
  // lezer niet, de bladzijde wel. Invulwaarden reizen als losse strings mee.
  // Hier stond tot 18 aug 2026 (avond) `kosten.dbNogNiet`: "dit formulier kan
  // daar nog niet in schrijven". Dat kan het nu wel — de invoer gaat naar
  // kosten_criterium/kosten_waarde via de functie uit migratie 009. Een
  // onbeschikbaar-melding laten staan die niet meer waar is, is precies zo
  // misleidend als de opslag die ze verving.
  "kosten.dbOpslaanMislukt": [
    "De invoer is niet bewaard: de database weigerde de wijziging. Er is niets half opgeslagen — de vorige kosten staan er nog. Probeer het opnieuw; blijft het misgaan, vraag de beheerder van het platform om het logboek na te kijken.",
    "La saisie n'a pas été enregistrée : la base de données a refusé la modification. Rien n'a été enregistré à moitié — les coûts précédents sont toujours là. Réessayez ; si le problème persiste, demandez à l'administrateur de la plateforme de consulter le journal.",
  ],
  "kosten.sessieVerlopen": [
    "Je sessie is verlopen. Meld opnieuw aan.",
    "Votre session a expiré. Reconnectez-vous.",
  ],
  "kosten.alleenBeheerder": [
    "Alleen een beheerder kan het kostenmodel wijzigen.",
    "Seul un administrateur peut modifier le modèle de coûts.",
  ],
  "kosten.contractOnleesbaar": [
    "Het contract is op dit moment niet leesbaar, dus de invoer kan niet tegen de echte groepen getoetst worden. Probeer het straks opnieuw.",
    "Le contrat est illisible pour le moment ; la saisie ne peut donc pas être vérifiée par rapport aux groupes réels. Réessayez plus tard.",
  ],
  "kosten.geenCriterium": [
    "Er zijn kosten ingevuld maar geen enkel criterium.",
    "Des coûts sont saisis, mais aucun critère ne l'est.",
  ],
  "kosten.herrekeningLoopt": [
    "De invoer is bewaard, maar er loopt al een herberekening. Wacht tot die klaar is en sla dan opnieuw op.",
    "La saisie est enregistrée, mais un recalcul est déjà en cours. Attendez qu'il se termine, puis enregistrez à nouveau.",
  ],
  "kosten.herrekenenMislukt": [
    "De invoer is bewaard, maar het herrekenen van het contract is mislukt. Vraag de beheerder van het platform om de contractbouw na te kijken.",
    "La saisie est enregistrée, mais le recalcul du contrat a échoué. Demandez à l'administrateur de la plateforme de vérifier la génération du contrat.",
  ],
  "kosten.leeggemaakt": [
    "Alle kosten leeggemaakt. Margebewaking staat weer op onbeschikbaar.",
    "Tous les coûts ont été effacés. Suivi des marges est à nouveau indisponible.",
  ],
  // {criteria} en {groepen} zijn zelf vertaalde woordgroepen ("3 criteria"),
  // gekozen door het formulier uit de vier sleutels hieronder: de actie stuurt
  // kale aantallen, de meervoudskeuze is presentatie.
  "kosten.bewaard": [
    "Bewaard: {criteria}, kosten voor {groepen}. Margebewaking rekent nu met de nieuwe opbouw.",
    "Enregistré : {criteria}, coûts pour {groepen}. Suivi des marges calcule désormais avec la nouvelle composition.",
  ],
  // De gehoste route (CONTRACT_BRON=db) bewaart wél, maar herrekent niet: op de
  // gehoste omgeving staat geen berekeningslaag. Het verschil met
  // `kosten.bewaard` is dus geen nuance maar de waarheid — beloven dat
  // Margebewaking nú met de nieuwe opbouw rekent, zou een cijfer toezeggen dat
  // er nog niet is (harde regel 8).
  "kosten.leeggemaaktDb": [
    "Alle kosten leeggemaakt. Margebewaking staat weer op onbeschikbaar zodra de cijfers opnieuw berekend zijn.",
    "Tous les coûts ont été effacés. Suivi des marges sera à nouveau indisponible dès que les chiffres auront été recalculés.",
  ],
  "kosten.bewaardDb": [
    "Bewaard: {criteria}, kosten voor {groepen}. Margebewaking rekent met de nieuwe opbouw zodra de cijfers opnieuw berekend zijn — dat gebeurt 's nachts, of eerder als de beheerder de berekening start. Tot dan staat daar de vorige stand.",
    "Enregistré : {criteria}, coûts pour {groepen}. Suivi des marges calculera avec la nouvelle composition dès que les chiffres auront été recalculés — cela se fait la nuit, ou plus tôt si l'administrateur lance le calcul. En attendant, l'écran affiche l'état précédent.",
  ],
  "kosten.criteriumEnkelvoud": ["{n} criterium", "{n} critère"],
  "kosten.criteriumMeervoud": ["{n} criteria", "{n} critères"],
  "kosten.groepEnkelvoud": ["{n} groep", "{n} groupe"],
  "kosten.groepMeervoud": ["{n} groepen", "{n} groupes"],
  // De validatiefouten uit lib/kostenmodel.ts, met dezelfde sleutel+waarden-vorm.
  "kosten.naamTeLang": [
    "De criteriumnaam \"{naam}…\" is langer dan {max} tekens.",
    "Le nom de critère « {naam}… » dépasse {max} caractères.",
  ],
  "kosten.dubbelCriterium": [
    "Het criterium \"{naam}\" staat er twee keer in.",
    "Le critère « {naam} » apparaît deux fois.",
  ],
  "kosten.teVeelCriteria": [
    "{aantal} criteria; het kostenmodel draagt er hoogstens {max}.",
    "{aantal} critères ; le modèle de coûts en accepte au maximum {max}.",
  ],
  "kosten.geenPercentage": [
    "De kost \"{criterium}\" van \"{groep}\" ({waarde}) is geen percentage. Vul een getal in, hoogstens twee decimalen.",
    "Le coût « {criterium} » de « {groep} » ({waarde}) n'est pas un pourcentage. Saisissez un nombre, avec deux décimales au maximum.",
  ],
  "kosten.buitenBereik": [
    "De kost \"{criterium}\" van \"{groep}\" moet tussen 0 en 100 liggen.",
    "Le coût « {criterium} » de « {groep} » doit être compris entre 0 et 100.",
  ],

  // --- het scherm Sluitingsdagen ---
  "sluit.titel": ["Sluitingsdagen", "Jours de fermeture"],
  "sluit.ondertitel": [
    "Wanneer is de zaak dicht? Een bevestigde sluitingsdag krijgt geen omzetverwachting meer.",
    "Quand la boutique est-elle fermée ? Un jour de fermeture confirmé ne reçoit plus de prévision de chiffre d'affaires.",
  ],
  "sluit.hoewerkt": ["Hoe werkt dit?", "Comment cela fonctionne-t-il ?"],
  "sluit.uitlegKandidaten": [
    "Het platform kent de Belgische feestdagen al. Beantwoord per dag de ene vraag die alleen de bakkerij kan beantwoorden: is de zaak die dag open of dicht? Twee klikken per rij, één keer per jaar. Ook \"open\" is echte informatie — een bevestigde open dag verliest zijn voorbehoud in de prognose.",
    "La plateforme connaît déjà les jours fériés belges. Répondez pour chaque jour à la seule question que seule la boulangerie peut trancher : la boutique est-elle ouverte ou fermée ce jour-là ? Deux clics par ligne, une fois par an. « Ouvert » aussi est une vraie information — un jour confirmé ouvert perd sa réserve dans la prévision.",
  ],
  "sluit.uitlegNachtelijk": [
    "Wat je hier bewaart, staat meteen op dit scherm en telt mee in de prognose vanaf de eerstvolgende nachtelijke herrekening. De prognose van dit moment rekent dus nog met de vorige stand.",
    "Ce que vous enregistrez ici apparaît immédiatement sur cet écran et compte dans la prévision à partir du prochain recalcul nocturne. La prévision actuelle repose donc encore sur l'état précédent.",
  ],
  "sluit.uitlegOnbekend": [
    "Een dag zonder antwoord is niet \"open\" maar \"onbekend\": de prognose neemt daar open aan en zegt dat er eerlijk bij.",
    "Un jour sans réponse n'est pas « ouvert » mais « inconnu » : la prévision y suppose l'ouverture et le dit honnêtement.",
  ],
  "sluit.feestdagen": [
    "Feestdagen — de komende twaalf maanden",
    "Jours fériés — les douze prochains mois",
  ],
  "sluit.open": ["open", "ouvert"],
  "sluit.dicht": ["dicht", "fermé"],
  "sluit.onbekend": ["nog niet beantwoord", "pas encore répondu"],
  "sluit.onbekendKnop": ["?", "?"],
  "sluit.toestandVan": ["Toestand van {datum}", "État du {datum}"],
  "sluit.periodes": [
    "Eigen sluitingsperiodes",
    "Périodes de fermeture propres",
  ],
  "sluit.periodesUitleg": [
    "Voor alles wat geen feestdag is: de jaarlijkse sluiting, een verbouwing, een brugdag die de zaak zelf neemt. De einddatum mag leeg blijven voor één dag. De reden komt op het prognosescherm — houd hem zakelijk en zet er nooit een naam of persoonlijke omstandigheid in.",
    "Pour tout ce qui n'est pas un jour férié : la fermeture annuelle, des travaux, un pont que la boutique prend elle-même. La date de fin peut rester vide pour un seul jour. Le motif apparaît sur l'écran de prévision — restez factuel et n'y mettez jamais de nom ni de circonstance personnelle.",
  ],
  "sluit.periodeToevoegen": [
    "+ een periode toevoegen",
    "+ ajouter une période",
  ],
  "sluit.van": ["Van", "Du"],
  "sluit.tot": ["Tot en met", "Jusqu'au"],
  "sluit.reden": ["Reden", "Motif"],
  "sluit.redenVoorbeeld": [
    "Jaarlijkse sluiting",
    "Fermeture annuelle",
  ],
  "sluit.verwijder": ["Verwijderen", "Supprimer"],
  "sluit.verwijderPeriode": [
    "Periode van {van} verwijderen",
    "Supprimer la période du {van}",
  ],
  "sluit.regel": [
    "Vaste wekelijkse sluitingsdag",
    "Jour de fermeture hebdomadaire fixe",
  ],
  "sluit.regelUitleg": [
    "Eén dag per week altijd dicht, als regel in plaats van losse datums — een regel loopt nooit af. De einddatum mag leeg blijven; dan geldt hij tot nader order.",
    "Un jour par semaine toujours fermé, sous forme de règle plutôt que de dates séparées — une règle n'expire jamais. La date de fin peut rester vide ; la règle vaut alors jusqu'à nouvel ordre.",
  ],
  "sluit.geenRegel": ["geen vaste sluitingsdag", "pas de jour fixe"],
  "sluit.weekdagLabel": ["Weekdag", "Jour de la semaine"],
  "sluit.vanafLabel": ["Vanaf", "À partir du"],
  "sluit.totLabel": ["Tot en met (mag leeg)", "Jusqu'au (peut rester vide)"],
  "sluit.wd0": ["maandag", "lundi"],
  "sluit.wd1": ["dinsdag", "mardi"],
  "sluit.wd2": ["woensdag", "mercredi"],
  "sluit.wd3": ["donderdag", "jeudi"],
  "sluit.wd4": ["vrijdag", "vendredi"],
  "sluit.wd5": ["zaterdag", "samedi"],
  "sluit.wd6": ["zondag", "dimanche"],
  "sluit.opslaan": ["Sluitingsdagen bewaren", "Enregistrer les fermetures"],
  "sluit.opslaanBezig": ["Bewaren…", "Enregistrement…"],
  "sluit.bestandsdekking": [
    "De oude sluitingslijst (beheerd door de bouwers) reikt tot {tot}; die dagen staan hieronder al als bewaarde invoer.",
    "L'ancienne liste des fermetures (gérée par les développeurs) va jusqu'au {tot} ; ces jours figurent déjà ci-dessous comme saisie enregistrée.",
  ],
  "sluit.bewaardeInvoer": [
    "Bewaarde invoer buiten deze lijst",
    "Saisies enregistrées hors de cette liste",
  ],
  "sluit.bewaardeInvoerUitleg": [
    "Uitspraken over dagen die niet in de feestdagenlijst hierboven staan: eigen periodes en de eenmalig overgenomen oude lijst. Eigen periodes bewerk je hierboven; de rest blijft staan als geschiedenis.",
    "Réponses sur des jours absents de la liste des jours fériés ci-dessus : périodes propres et ancienne liste reprise une seule fois. Les périodes propres se modifient ci-dessus ; le reste demeure comme historique.",
  ],
  // De uitkomsten van het opslaan, zelfde patroon als kosten.*: sleutels, geen
  // zinnen; de actie kent de taal van de lezer niet.
  "sluit.sessieVerlopen": [
    "Je sessie is verlopen. Meld opnieuw aan.",
    "Votre session a expiré. Reconnectez-vous.",
  ],
  "sluit.alleenBeheerder": [
    "Alleen een beheerder kan sluitingsdagen wijzigen.",
    "Seul un administrateur peut modifier les jours de fermeture.",
  ],
  "sluit.alleenBeheerderVak": [
    "Bekijken kan iedereen; wijzigen kan alleen een beheerder. De lijst hieronder toont de bewaarde stand.",
    "Tout le monde peut consulter ; seul un administrateur peut modifier. La liste ci-dessous montre l'état enregistré.",
  ],
  "sluit.alleenDb": [
    "Deze omgeving leest het contract uit bestanden en heeft geen database om sluitingsdagen in te bewaren. Op de gehoste omgeving werkt dit scherm wel.",
    "Cet environnement lit le contrat depuis des fichiers et n'a pas de base de données pour enregistrer les fermetures. Sur l'environnement hébergé, cet écran fonctionne.",
  ],
  "sluit.dbOnbereikbaar": [
    "De database gaf geen antwoord, dus de bewaarde sluitingsdagen zijn nu niet leesbaar. Er is niets gewijzigd. Probeer het straks opnieuw; blijft het misgaan, vraag de beheerder van het platform om het logboek na te kijken.",
    "La base de données n'a pas répondu ; les jours de fermeture enregistrés sont donc illisibles pour le moment. Rien n'a été modifié. Réessayez plus tard ; si le problème persiste, demandez à l'administrateur de la plateforme de consulter le journal.",
  ],
  "sluit.dbOpslaanMislukt": [
    "De invoer is niet bewaard: de database weigerde de wijziging. Er is niets half opgeslagen — de vorige kalender staat er nog. Probeer het opnieuw; blijft het misgaan, vraag de beheerder van het platform om het logboek na te kijken.",
    "La saisie n'a pas été enregistrée : la base de données a refusé la modification. Rien n'a été enregistré à moitié — le calendrier précédent est toujours là. Réessayez ; si le problème persiste, demandez à l'administrateur de la plateforme de consulter le journal.",
  ],
  "sluit.contractOnleesbaar": [
    "Het contract is op dit moment niet leesbaar, dus de feestdagenlijst kan niet opgehaald worden. Probeer het straks opnieuw.",
    "Le contrat est illisible pour le moment ; la liste des jours fériés ne peut donc pas être récupérée. Réessayez plus tard.",
  ],
  "sluit.bewaard": [
    "Bewaard: {dicht} bevestigd dicht, {open} bevestigd open. De prognose rekent ermee vanaf de eerstvolgende nachtelijke herrekening; tot dan staat daar de vorige stand.",
    "Enregistré : {dicht} confirmés fermés, {open} confirmés ouverts. La prévision en tiendra compte à partir du prochain recalcul nocturne ; d'ici là, elle affiche l'état précédent.",
  ],
  // De validatiefouten uit lib/sluitingsdagen.ts.
  "sluit.datumOngeldig": [
    "\"{datum}\" is geen geldige datum.",
    "« {datum} » n'est pas une date valide.",
  ],
  "sluit.totVoorVan": [
    "De periode van {van} eindigt op {tot}, en dat is eerder. Wissel de datums om.",
    "La période du {van} se termine le {tot}, soit avant son début. Inversez les dates.",
  ],
  "sluit.periodeTeLang": [
    "De periode van {van} tot {tot} duurt {dagen} dagen, meer dan de {max} die deze kalender aanvaardt. Controleer of er geen jaartal verkeerd staat.",
    "La période du {van} au {tot} dure {dagen} jours, plus que les {max} que ce calendrier accepte. Vérifiez qu'aucune année n'est erronée.",
  ],
  "sluit.redenTeLang": [
    "De reden is langer dan {max} tekens; ze komt op een scherm terecht.",
    "Le motif dépasse {max} caractères ; il apparaît sur un écran.",
  ],
  "sluit.openDichtConflict": [
    "{datum} staat als bevestigd open én valt in een sluitingsperiode. Kies één van de twee.",
    "Le {datum} est confirmé ouvert et tombe dans une période de fermeture. Choisissez l'un des deux.",
  ],
  "sluit.weekdagOngeldig": [
    "\"{weekdag}\" is geen weekdag.",
    "« {weekdag} » n'est pas un jour de la semaine.",
  ],
  "sluit.vanafOntbreekt": [
    "De vaste sluitingsdag heeft een begindatum nodig.",
    "Le jour de fermeture fixe a besoin d'une date de début.",
  ],
  "sluit.teVeel": [
    "{aantal} dagen; deze kalender draagt er hoogstens {max}.",
    "{aantal} jours ; ce calendrier en accepte au maximum {max}.",
  ],

  // --- het scherm Deliveroo-import ---
  "deliveroo.titel": ["Deliveroo-import", "Import Deliveroo"],
  "deliveroo.ondertitel": [
    "Een export van Deliveroo opladen. Het bestand wordt bewaard en 's nachts verwerkt.",
    "Charger un export Deliveroo. Le fichier est conservé et traité pendant la nuit.",
  ],
  "deliveroo.hoewerkt": ["Hoe werkt dit?", "Comment cela fonctionne-t-il ?"],
  "deliveroo.uitlegOpladen": [
    "Kies de export zoals ze van Deliveroo komt en laad ze op. Toegestaan: pdf, csv en de twee Excel-vormen, tot {max} MB per bestand.",
    "Choisissez l'export tel qu'il arrive de Deliveroo et chargez-le. Formats acceptés : pdf, csv et les deux formats Excel, jusqu'à {max} Mo par fichier.",
  ],
  "deliveroo.uitlegNachtelijk": [
    "Het bestand wordt bewaard zoals het is en 's nachts verwerkt. Tot dan staat de stand op \"nog niet verwerkt\", en de cijfers op de andere schermen veranderen niet. Er komt hier dus geen onmiddellijk resultaat.",
    "Le fichier est conservé tel quel et traité pendant la nuit. D'ici là, l'état reste « pas encore traité » et les chiffres des autres écrans ne changent pas. Aucun résultat immédiat n'apparaît donc ici.",
  ],
  "deliveroo.uitlegNietGelezen": [
    "Dit scherm leest het bestand niet en rekent er niets uit: het geeft de bytes ongewijzigd door aan de database. Het uitpakken gebeurt in de verwerkingslaag, op één plaats.",
    "Cet écran ne lit pas le fichier et n'en calcule rien : il transmet les octets tels quels à la base de données. Le dépouillement a lieu dans la couche de traitement, en un seul endroit.",
  ],
  "deliveroo.bestandLabel": ["Bestand", "Fichier"],
  "deliveroo.opladen": ["Bestand opladen", "Charger le fichier"],
  "deliveroo.opladenBezig": ["Opladen…", "Chargement…"],
  "deliveroo.alleenBeheerderVak": [
    "Opladen kan alleen een beheerder. De lijst hieronder toont wat er al opgeladen is.",
    "Seul un administrateur peut charger un fichier. La liste ci-dessous montre ce qui a déjà été chargé.",
  ],
  "deliveroo.lijstTitel": [
    "Eerder opgeladen bestanden",
    "Fichiers déjà chargés",
  ],
  "deliveroo.lijstUitleg": [
    "De jongste {max} bestanden, het recentste eerst.",
    "Les {max} fichiers les plus récents, le dernier en tête.",
  ],
  "deliveroo.geenBestanden": [
    "Er is nog geen bestand opgeladen.",
    "Aucun fichier n'a encore été chargé.",
  ],
  "deliveroo.kolBestand": ["Bestand", "Fichier"],
  "deliveroo.kolOpgeladen": ["Opgeladen", "Chargé"],
  "deliveroo.kolOmvang": ["Omvang", "Taille"],
  "deliveroo.kolVerwerking": ["Verwerking", "Traitement"],
  "deliveroo.bytes": ["{aantal} bytes", "{aantal} octets"],
  "deliveroo.doorWie": ["door {gebruiker}", "par {gebruiker}"],
  "deliveroo.nogNietVerwerkt": ["nog niet verwerkt", "pas encore traité"],
  "deliveroo.verwerktGelukt": ["verwerkt op {datum}", "traité le {datum}"],
  "deliveroo.verwerktMislukt": ["verwerking mislukt", "échec du traitement"],
  "deliveroo.verwerktMisluktUitleg": [
    "Staat er een mislukte verwerking in de lijst, dan is dat bestand niet in de cijfers terechtgekomen. De reden staat in het logboek van de verwerking; vraag de beheerder van het platform om die na te kijken.",
    "Si un traitement a échoué, ce fichier n'est pas entré dans les chiffres. Le motif figure dans le journal de traitement ; demandez à l'administrateur de la plateforme de le consulter.",
  ],
  // De uitkomsten van het opladen, zelfde patroon als sluit.* en kosten.*:
  // sleutels, geen zinnen; de actie kent de taal van de lezer niet.
  "deliveroo.sessieVerlopen": [
    "Je sessie is verlopen. Meld opnieuw aan.",
    "Votre session a expiré. Reconnectez-vous.",
  ],
  "deliveroo.alleenBeheerder": [
    "Alleen een beheerder kan een bestand opladen.",
    "Seul un administrateur peut charger un fichier.",
  ],
  "deliveroo.alleenDb": [
    "Deze omgeving leest het contract uit bestanden en heeft geen database om een export in te bewaren. Op de gehoste omgeving werkt dit scherm wel.",
    "Cet environnement lit le contrat depuis des fichiers et n'a pas de base de données pour conserver un export. Sur l'environnement hébergé, cet écran fonctionne.",
  ],
  "deliveroo.dbOnbereikbaar": [
    "De database gaf geen antwoord, dus de opgeladen bestanden zijn nu niet leesbaar. Er is niets gewijzigd. Probeer het straks opnieuw; blijft het misgaan, vraag de beheerder van het platform om het logboek na te kijken.",
    "La base de données n'a pas répondu ; les fichiers chargés sont donc illisibles pour le moment. Rien n'a été modifié. Réessayez plus tard ; si le problème persiste, demandez à l'administrateur de la plateforme de consulter le journal.",
  ],
  "deliveroo.dbOpslaanMislukt": [
    "Het bestand is niet bewaard: de database weigerde de opslag. Er staat niets half opgeslagen. Probeer het opnieuw; blijft het misgaan, vraag de beheerder van het platform om het logboek na te kijken.",
    "Le fichier n'a pas été conservé : la base de données a refusé l'enregistrement. Rien n'est enregistré à moitié. Réessayez ; si le problème persiste, demandez à l'administrateur de la plateforme de consulter le journal.",
  ],
  "deliveroo.bewaard": [
    "\"{bestandsnaam}\" is bewaard en staat klaar. De verwerking gebeurt vannacht; tot dan blijft de stand op \"nog niet verwerkt\".",
    "« {bestandsnaam} » est conservé et prêt. Le traitement a lieu cette nuit ; d'ici là, l'état reste « pas encore traité ».",
  ],
  "deliveroo.alGeladen": [
    "\"{bestandsnaam}\" stond er al: precies dit bestand is eerder opgeladen. Er is niets bijgekomen en de vorige rij blijft staan.",
    "« {bestandsnaam} » était déjà présent : ce fichier exact a été chargé auparavant. Rien n'a été ajouté et la ligne précédente demeure.",
  ],
  // De poort uit lib/deliveroo-upload.ts.
  "deliveroo.geenBestand": [
    "Er is geen bestand gekozen.",
    "Aucun fichier n'a été choisi.",
  ],
  "deliveroo.naamOngeldig": [
    "\"{bestandsnaam}\" is geen bruikbare bestandsnaam: ze mag geen schuine streep of backslash bevatten.",
    "« {bestandsnaam} » n'est pas un nom de fichier utilisable : il ne peut contenir ni barre oblique ni barre oblique inversée.",
  ],
  "deliveroo.leegBestand": [
    "Het gekozen bestand is leeg.",
    "Le fichier choisi est vide.",
  ],
  "deliveroo.teGroot": [
    "Het bestand is groter dan {max} MB. Laad de export per periode op in plaats van in één keer.",
    "Le fichier dépasse {max} Mo. Chargez l'export par période plutôt qu'en une seule fois.",
  ],
  "deliveroo.typeOnbekend": [
    "\"{bestandsnaam}\" is geen pdf, csv of Excel-bestand. Laad de export op zoals Deliveroo hem levert.",
    "« {bestandsnaam} » n'est ni un pdf, ni un csv, ni un fichier Excel. Chargez l'export tel que Deliveroo le fournit.",
  ],

  // --- kolomnamen, overal ---
  "kol.dag": ["Dag", "Jour"],
  "kol.feestdag": ["Feestdag", "Jour férié"],
  "kol.toestand": ["Open of dicht?", "Ouvert ou fermé ?"],
  "kol.omzet": ["Omzet", "Chiffre d'affaires"],
  "kol.gebruikelijk": ["Gebruikelijk", "Habituel"],
  "kol.verschil": ["Verschil", "Écart"],
  "kol.kanaal": ["Kanaal", "Canal"],
  "kol.bruto": ["Bruto", "Brut"],
  "kol.commissie": ["Commissie", "Commission"],
  "kol.netto": ["Netto", "Net"],
  "kol.inhouding": ["Inhouding", "Retenue"],
  "kol.product": ["Product", "Produit"],
  "kol.groep": ["Groep", "Groupe"],
  "kol.stuks": ["Stuks", "Unités"],
  "kol.aandeel": ["Aandeel", "Part"],
  "kol.nu": ["Nu", "Maintenant"],
  "kol.ervoor": ["Ervoor", "Avant"],
  "kol.indegroep": ["In de groep", "Dans le groupe"],
  "kol.gewogen": ["Gewogen", "Pondéré"],
  "kol.bedrag30d": ["Bedrag 30 d", "Montant 30 j"],
  "kol.aandeelOmzet": ["Aandeel omzet", "Part du chiffre d'affaires"],
  "kol.kostenopbouw": ["Kostenopbouw", "Composition des coûts"],
  "kol.marge": ["Marge", "Marge"],
  "kol.omzet30d": ["Omzet 30 d", "CA 30 j"],
  "kol.brutomarge30d": ["Brutomarge 30 d", "Marge brute 30 j"],
  "kol.verwacht": ["Verwacht", "Attendu"],
  "kol.verwachteOmzet": ["Verwachte omzet", "Chiffre d'affaires attendu"],
  "kol.onder": ["Onder", "Bas"],
  "kol.boven": ["Boven", "Haut"],
  "kol.ondergrens": ["Ondergrens", "Borne inférieure"],
  "kol.bovengrens": ["Bovengrens", "Borne supérieure"],
  "kol.productgroep": ["Productgroep", "Groupe de produits"],
  "kol.brutomarge": ["Brutomarge", "Marge brute"],
  "kol.meetdagen": ["Meetdagen", "Jours mesurés"],

  // --- ontbrekende blokken: het contract levert niets EN geen reden ---
  "leeg.blok": [
    "Het contract levert dit blok niet, en geeft geen reden waarom niet.",
    "Le contrat ne fournit pas ce bloc, et n'indique pas pourquoi.",
  ],
  "leeg.ontbinding": [
    "Het contract levert geen ontbinding, en geeft geen reden waarom niet.",
    "Le contrat ne fournit pas de décomposition, et n'indique pas pourquoi.",
  ],
  "leeg.geenOntbinding": [
    "Geen ontbinding beschikbaar.",
    "Aucune décomposition disponible.",
  ],
  "leeg.totaal": [
    "Het contract levert geen totaal, en geeft geen reden waarom niet.",
    "Le contrat ne fournit pas de total, et n'indique pas pourquoi.",
  ],
  "leeg.trackrecord": [
    "Het contract levert geen trackrecord, en geeft geen reden waarom niet.",
    "Le contrat ne fournit pas d'historique de performance, et n'indique pas pourquoi.",
  ],
  "leeg.verschuiving": [
    "Het contract levert geen verschuiving, en geeft geen reden waarom niet.",
    "Le contrat ne fournit pas de variation, et n'indique pas pourquoi.",
  ],
  "leeg.verdeling": [
    "Het contract levert geen verdeling, en geeft geen reden waarom niet.",
    "Le contrat ne fournit pas de répartition, et n'indique pas pourquoi.",
  ],

  // --- algemene bouwstenen ---
  // De browsertab en de zoekmachine-omschrijving. Tot 17 aug stonden die hard
  // in layout.tsx en login/page.tsx en bleven ze Nederlands op een Frans
  // scherm.
  "meta.titel": [
    "Renard Bakery — financieel overzicht",
    "Renard Bakery — aperçu financier",
  ],
  "meta.omschrijving": [
    "CFO-platform voor Renard Bakery",
    "Plateforme CFO pour Renard Bakery",
  ],
  "meta.login": ["Aanmelden · Renard Bakery", "Connexion · Renard Bakery"],
  "algemeen.onbeschikbaar": ["Niet beschikbaar", "Non disponible"],
  "algemeen.eenPunt": ["1 punt", "1 point"],
  "algemeen.meetdagenTitel": [
    "{x}: gemiddelde over {n} gemeten dagen",
    "{x} : moyenne sur {n} jours mesurés",
  ],
  "algemeen.geenMetingTitel": [
    "{x}: geen gemeten dagen",
    "{x} : aucun jour mesuré",
  ],
  "algemeen.geenMeting": ["geen gemeten dagen", "aucun jour mesuré"],
  "algemeen.meetdagenKort": ["{n} meetdagen", "{n} jours mesurés"],
  "dag.weekdagMeetdagen": [
    "{naam}, {n} gemeten dagen",
    "{naam}, {n} jours mesurés",
  ],
  "prog.dagomzetTitel": [
    "Verwachte dagomzet, {n} dagen vooruit",
    "Chiffre d'affaires attendu par jour, {n} jours à venir",
  ],
  "prog.categorieMeta": [
    "{aandeel} van de omzet · gemeten afwijking {wape}",
    "{aandeel} du chiffre d'affaires · écart mesuré {wape}",
  ],
  "algemeen.nietMeegeleverd": [
    "niet meegeleverd door de berekeningslaag",
    "non fourni par la couche de calcul",
  ],
  "algemeen.nPunten": ["{n} punten", "{n} points"],
  "algemeen.meerInfo": ["Meer info", "Plus d'infos"],
  "algemeen.periode": ["Periode", "Période"],
  "algemeen.nogNietBeschikbaar": ["Nog niet beschikbaar", "Pas encore disponible"],
  // De uitklap van een onbeschikbaar-vak. Dát er iets ontbreekt blijft altijd
  // staan; alleen de lange reden gaat hierachter. Zie Onbeschikbaar.tsx voor
  // waarom er een lengtegrens in zit en waar die op rust.
  "algemeen.waaromNiet": ["Waarom niet", "Pourquoi pas"],
  "algemeen.watNietStaat": [
    "Wat hier niet staat, en waarom",
    "Ce qui ne figure pas ici, et pourquoi",
  ],
  "algemeen.tovVorigJaar": ["t.o.v. vorig jaar", "par rapport à l'an dernier"],
  // Het bandje in de grafiektooltip: "band € 900,00 – € 1.100,00".
  "algemeen.band": ["band", "intervalle"],

  // --- het CFO-rapport (het keuzemenu en /rapport) ---
  // Het rapport is geen bestand meer dat vooraf gebouwd wordt, maar een
  // weergave van dezelfde schermen: wat je kiest, lees je hier van dezelfde
  // contractantwoorden, en de browser maakt er een PDF van.
  "rapport.titel": ["CFO-rapport", "Rapport CFO"],
  "rapport.knop": ["Rapport", "Rapport"],
  // Hier stond `rapport.menuLabel` ("Kies wat er in het rapport komt"),
  // bedoeld als toegankelijke naam voor het keuzemenu en nooit aangesloten —
  // de enige van de sleutels die nergens gebruikt werd. Geschrapt op 19 aug
  // 2026 en niet alsnog ingehangen: de knop draagt al een naam ("Rapport" of
  // "Onderdelen") en het paneel eronder een `legend`. Een aria-label op die
  // knop zou de zichtbare tekst juist overschrijven, en dat is voor wie met
  // stembediening werkt een verslechtering.
  "rapport.onderdelen": ["Onderdelen", "Sections"],
  "rapport.openen": ["Rapport openen", "Ouvrir le rapport"],
  "rapport.wijzigen": ["Onderdelen wijzigen", "Modifier les sections"],
  "rapport.terugvalAlles": [
    "Zonder vinkje bevat het rapport alle onderdelen.",
    "Sans case cochée, le rapport contient toutes les sections.",
  ],
  // Twee lengtes van dezelfde knop: de korte staat erop (een balk met één lange
  // kapitaalregel erin is geen rustige balk), de lange is wat een schermlezer
  // voorleest en wat er bij aanwijzen verschijnt.
  "rapport.afdrukken": ["Afdrukken of PDF", "Imprimer ou PDF"],
  "rapport.afdrukkenLang": [
    "Afdrukken of opslaan als PDF",
    "Imprimer ou enregistrer en PDF",
  ],
  "rapport.terug": ["Terug naar het platform", "Retour à la plateforme"],
  "rapport.bevat": ["Dit rapport bevat", "Ce rapport contient"],
  "rapport.deelStand": ["Stand van het platform", "État de la plateforme"],
  // Op papier staat er geen navigatie omheen die vertelt wat dit is; deze zin
  // doet dat, en hij zegt ook waar de cijfers vandaan komen.
  "rapport.herkomst": [
    "Elk cijfer komt uit de berekeningslaag van het platform, langs hetzelfde datacontract als de schermen. Wat daar onbeschikbaar is, staat hier als onbeschikbaar met de reden.",
    "Chaque chiffre provient de la couche de calcul de la plateforme, via le même contrat de données que les écrans. Ce qui y est indisponible figure ici comme indisponible, avec la raison.",
  ],

  // --- de briefing bovenaan elk scherm ---
  // "Wat opvalt" en niet "Aandachtspunten": het tweede belooft dat er iets
  // mis is, en de briefing meldt ook wat gewoon goed gaat.
  "briefing.titel": ["Wat opvalt", "Ce qui ressort"],

  // --- de foutgrens ---
  // Next vervangt een serverfout in productie door een generieke tekst plus een
  // digest; de zorgvuldig geformuleerde reden uit laadContract haalt het scherm
  // dus niet. Wat een lezer wél hoort te krijgen: dat er niets getoond wordt
  // omdat het misging en niet omdat er geen omzet was, wat hij nu kan doen, en
  // de code waarmee een beheerder het in de log terugvindt. Dat is dezelfde
  // plicht als harde regel 8, één laag hoger.
  "fout.titel": ["De cijfers konden niet geladen worden", "Impossible de charger les chiffres"],
  "fout.uitleg": [
    "Dit is een storing en geen uitkomst: er staat hier niets omdat het ophalen mislukte, niet omdat er niets te tonen was.",
    "Il s'agit d'une panne et non d'un résultat : rien ne s'affiche parce que le chargement a échoué, pas parce qu'il n'y avait rien à montrer.",
  ],
  "fout.opnieuw": ["Opnieuw proberen", "Réessayer"],
  "fout.beheerder": [
    "Blijft dit staan, geef dan deze code door aan de beheerder:",
    "Si le problème persiste, communiquez ce code à l'administrateur :",
  ],
  "fout.geenCode": ["geen code beschikbaar", "aucun code disponible"],

  // Een lezer kreeg tot 18 aug 2026 het volledige kostenformulier te zien, met
  // een opslaan-knop die de server altijd weigerde. Geen beveiligingsgat (de
  // actie controleert de rol zelf), wel een scherm dat iets belooft wat het
  // niet doet. Onbeschikbaar mét reden is hier het eerlijke antwoord.
  //
  // Bewust een eigen sleutel naast `kosten.alleenBeheerder`: die is de
  // weigering ná een poging ("alleen een beheerder kan dit wijzigen"), deze is
  // de toestand vóóraf, en die mag erbij zeggen waar de cijfers wél staan.
  "inst.kostenAlleenBeheerder": [
    "Het kostenmodel wordt ingevuld door een beheerder. Je bekijkt het platform als lezer: de cijfers die eruit volgen, staan wel op Margebewaking.",
    "Le modèle de coûts est complété par un administrateur. Vous consultez la plateforme en tant que lecteur : les chiffres qui en découlent figurent bien dans Suivi des marges.",
  ],
} as const satisfies Record<string, readonly [string, string]>;

export type Sleutel = keyof typeof WOORDEN;

/**
 * Alle sleutels als runtime-lijst, voor de test die elke vertaling op
 * niet-leegte toetst: een type is op testtijd niet af te lopen, en een
 * steekproef van drie sleutels bewaakte de andere ~250 niet (18 aug 2026).
 */
export const SLEUTELS = Object.keys(WOORDEN) as readonly Sleutel[];

const INDEX: Record<Taal, 0 | 1> = { nl: 0, fr: 1 };

/**
 * De vertaalfunctie voor één taal. Gebruik:
 *
 *     const t = maakT(taal);
 *     t("nav.prognose")
 *     t("winkel.alleen", { naam: "Elsene" })
 *
 * Een onbekende sleutel kan door het type niet voorkomen. Een ontbrekende
 * invulplaats blijft zichtbaar als `{naam}` in plaats van te verdwijnen: een
 * zichtbaar gat is te herstellen, een stil gat niet.
 */
export function maakT(taal: Taal) {
  const i = INDEX[taal];
  return function t(sleutel: Sleutel, waarden?: Record<string, string>): string {
    const tekst = WOORDEN[sleutel][i];
    if (!waarden) return tekst;
    return tekst.replace(/\{(\w+)\}/g, (heel, naam: string) =>
      naam in waarden ? waarden[naam] : heel,
    );
  };
}

export type T = ReturnType<typeof maakT>;
