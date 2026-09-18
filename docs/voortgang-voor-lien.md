# Renard Bakery — CFO-platform: waar we staan

_Voor Lien Pletinckx · opgemaakt 19 augustus 2026 (vervangt de versie van 18 augustus) · opleverdatum fase 1: 27 augustus 2026_

---

## In één alinea

**Het platform staat online en leest uit de database.** Het databasewachtwoord kwam op 18 augustus binnen en dezelfde avond is de hele keten erdoorheen gegaan: acht migraties, 316.469 rijen in Stockholm, en de contractantwoorden erachteraan in beide talen. Het platform draait op `https://renard-bakery.vercel.app` achter onze eigen login; van buitenaf is de database gemeten dicht. Daarmee is de databasetrack — de enige track die op jouw sleutel wachtte — afgerond, negen dagen vóór de deadline. Wat nu nog telt zijn vier dingen, en het eerste is met afstand het urgentste: **de Deliveroo-rapporten via Sophie**, waar elke dag wachten een dag geschiedenis is die permanent verdwijnt.

---

## 1. Wat er werkt

**De keten van kassa tot scherm loopt volledig, en staat nu écht op een database.** De verkoopdata komt uit Odoo, de TGTG-cijfers uit de maandrapporten, en alles wordt samengebracht in één model waarin elke dag, elk product en elk kanaal op dezelfde manier geteld wordt. Dat model staat sinds 18 augustus in Supabase: 316.469 rijen, waarvan 221.375 verkoopregels vanaf januari 2025. De schermen lezen hun cijfers uit die database en niet meer uit bestanden op één machine. De afscherming is nagemeten en niet aangenomen: elke tabel staat op slot, en wie zonder login iets probeert op te halen krijgt een weigering.

**Zes schermen achter een login, in twee talen.** Dagoverzicht, Verkoopkanalen, Productmix, Margebewaking, Prognose en Instellingen — in het echte woordmerk, de beige en bordeaux van de logogids, volledig in het Nederlands én het Frans tot in de foutmeldingen. Bovenaan elk scherm staat een briefing: wat valt op, waarom, en wat er nodig is van wie. Het CFO-rapport is een bladzijde in het platform waarin je zelf aanvinkt welke onderdelen erin komen en die je met één knop afdrukt of als PDF bewaart. De schermen werken ook op een telefoon.

**De kanalen die Odoo niet kent.** TGTG staat erin met bruto-omzet én netto-opbrengst per pakket, apart van de winkelverkoop, want de marge is er een andere. Eén gevolg van de beslissing van 17 augustus om de maandmail-constructie niet op te zetten hoort hier eerlijk bij: **het TGTG-kanaal loopt tot en met juli 2026 en veroudert vanaf nu zichtbaar.** Het platform toont per kanaal tot wanneer de data loopt. Er gaat niets verloren: TGTG bewaart de documenten zelf, en wie het kanaal later weer wil laten meelopen, kan dat.

**Een prognose die zich verantwoordt.** Zeven dagen vooruit, per dag een verwachte omzet met een bandbreedte, plus een prognose per categorie. Gemeten door telkens alleen het verleden te gebruiken en dat te vergelijken met wat er werkelijk gebeurde: **7,8% gemiddelde afwijking op de dagomzet.** Op het scherm staat ook het trackrecord. Per product per dag is de afwijking 20,2%; dat cijfer is te zwak om beslissingen op te bouwen en staat daarom bewust níét als voorspelling op een scherm.

**Het platform zwijgt niet over wat het niet weet.** Waar een cijfer ontbreekt staat er geen schatting maar de reden. Margebewaking is daarvan het duidelijkste voorbeeld: marges zijn — jouw beslissing van 12 augustus — een add-on geworden omdat de kostprijsdata niet bij de klant bestaat. Nieuw sinds 19 augustus is dat de invoer nu ook op de online omgeving werkt: een beheerder vult op Instellingen per productgroep een kostenopbouw in, en Margebewaking rekent er meteen mee. Vijf minuten werk zodra iemand de percentages kent.

---

## 2. Wat er op 18 en 19 augustus is gebeurd

**De database is gevuld en het platform staat online.** Acht migraties, idempotent (een tweede ronde doet niets), 316.469 rijen, en veertien contractantwoorden in beide talen. Daarna is elk scherm uit beide bronnen — bestanden en database — opgehaald en vergeleken: inhoudelijk identiek. De eerste deploy was overigens groen en dood: Vercel bouwde het project zonder het als Next-toepassing te herkennen, waardoor elke pagina een 404 gaf terwijl de bouw slaagde. Gevonden door de URL na te rekenen in plaats van hem te delen, en dezelfde avond hersteld.

**De nachtelijke synchronisatie is af, en er is geen inhoudelijke blokkade meer.** Die stond op vier problemen en staat er nu op nul: de bewaking die een verarmde bouw moest tegenhouden weegt nu ook de inhoud en niet alleen het aantal antwoorden; het TGTG-kanaal wordt uit de database gelezen in plaats van van een lokale schijf (nagemeten: 1.872 regels, € 106.415,75, rij voor rij gelijk); drie onderdelen van de workflow draaiden op een afgeschreven runtime en zijn bijgewerkt; en de lijst met sluitingsdagen staat nu in de repo waar ze hoort. Wat rest is één handeling die een mens hoort te doen: de synchronisatie één keer met de hand starten en die run groen zien. Pas daarna gaat de planning aan — een planning die nog nooit geslaagd is, levert elke nacht een rode job op waar niemand naar kijkt.

**Het platform meldt het nu zelf wanneer de synchronisatie stilvalt.** Er werd al bijgehouden of een synchronisatie slaagde, maar niemand las het: drie nachten uitval was op het scherm onzichtbaar. Dat oordeel valt nu op het moment van kijken, met vastgelegde drempels, en verschijnt voluit op Instellingen en als "Let op: synchronisatie" in de voettekst van elk scherm. Vandaag staat er eerlijk: *"De nachtelijke synchronisatie heeft nog niet gedraaid; de planning staat uit en de cijfers worden met de hand ververst."*

**Eén fout is de moeite waard om zelf te melden.** Het platform meldde tien dagen die "niet uit de bronsystemen zijn ingeladen", terwijl de kalender wist dat de bakkerij tot 23 augustus gepland dicht is. Het beschuldigde zichzelf dus van veroudering omdat de zaak op vakantie is — en voor een CFO-platform zijn die woorden dodelijk voor het vertrouwen. Gerepareerd op beide plaatsen waar de fout zat: tijdens een sluiting staat er nu dat de zaak dicht is, met de eerste open dag erbij, en dat is uitdrukkelijk géén achterstand. Vooruit gesimuleerd: 24 augustus zwijgt, 27 augustus meldt wél een achterstand — de vangrail werkt dus nog.

---

## 3. Wat ik van jou nodig heb, in volgorde

| | Wat | Waarom nu |
|---|---|---|
| **1** | **De Deliveroo-rapporten, via Sophie** — in Partner Hub onder Reports: *Items Sold* en *Orders*, twaalf maanden in vier blokken van negentig dagen | **Het enige punt waar uitstel onherstelbaar is.** Het twaalfmaandsvenster schuift elke dag op; wat eruit valt is nergens meer te halen. Voorstel uit vraag 49: is er op 20 augustus niets binnen, dan levert fase 1 op met Deliveroo als "onbeschikbaar, met reden" |
| **2** | **De gebruikers.** Zoals afgesproken op 19 augustus stel jij de lijst zelf samen en leveren wij de mogelijkheid om gebruikers aan te maken. Wat we daarnaast nog van je nodig hebben: **wie de eerste beheerder is** (zonder die eerste komt niemand binnen, zelfregistratie staat uit) en **de bewaarregel bij uitdiensttreding** | Per persoon horen naam, e-mailadres en rol (lezer of beheerder) erbij. Het verschil is niet administratief: een beheerder wijzigt de kostencriteria en daarmee de marge die het hele platform toont. De accounts zijn de enige persoonsgegevens in het systeem, dus de bewaarregel hoort in het verwerkingsregister van de eindklant |
| **3** | **Eén leeg Vercel-project `renard-bakery` in team `asklien`.** Niets instellen: geen variabelen, geen koppeling, alleen het project | De huidige URL werkt en de demo is niet in gevaar, maar het platform staat nu tijdelijk in een persoonlijke omgeving. Zodra dit project bestaat verhuist het naar jouw team, waar het thuishoort bij de partij die het onderhoud draagt — en dan komt het ook in dezelfde regio als de database te staan |
| **4** | Antwoord op **vraag 55**: scenario's op de prognose in fase 1 of fase 2? De motor is voorbereid; het scherm is een halve dag | Bepaalt of die halve dag nog vóór de 27e valt |
| **5** | **Twee korte bevestigingen (vraag 58):** (a) de vijf uitbreidingen die binnen de raming zijn meegebouwd — tweetaligheid, kostenmodel-invoer, winkelindeling, briefing, het samenstelbare CFO-rapport — horen bij fase 1; (b) notificaties en de AI-uitleglaag: ons voorstel is fase 2 | Zodat de aanvaarding op 27 augustus nergens op een verrassing rust |

De heropening van de bakkerij op 24 augustus beantwoordt vanzelf de synchronisatievraag: vanaf dan komen er weer verse cijfers binnen en zien we meteen of de keten meeloopt.

---

## 4. Eerlijk over de kwaliteit

Alle controles staan groen: 870 tests (Python én platform, waarvan een deel tegen een echte Postgres), de typecontrole, de productiebouw, en een visuele steekproef die elk scherm in beide talen fotografeert en naloopt. Die steekproef ving op 19 augustus opnieuw een echte fout, en dat is precies waarvoor ze bestaat.

Wat het platform níét kan, staat op de schermen zelf en in het opleverdocument: geen marge zonder ingevuld kostenmodel, geen Deliveroo zonder rapporten, geen productprognose als voorspelling, en TGTG bevroren op juli 2026 zolang de aanvoer uit staat. Eén zwakke plek in de prognose wordt niet verhuld: januari draagt bijna een kwart van de jaarlijkse fout en de drie galette-dagen rond Driekoningen zitten op 46% afwijking. De oorzaak is de historiek en niet het model — de kassagegevens beginnen in 2025, dus er is precies één januari om op te toetsen. Elke kandidaat-oplossing is gemeten en verloor; een correctie die nergens tegen getoetst kan worden is een mening, en meningen komen dit platform niet in.

---

## 5. Wat er klaarligt voor daarna

De repo gaat naar jou over en je deployt zelf. Er ligt daarvoor een overdrachtsdocument klaar (`docs/overdracht.md`) met wat er precies moet gebeuren: de sleutels die niet automatisch meeverhuizen, de rotatie, en wat er in het dossier van de eindklant hoort. Dat is geen vragenlijst voor nu, maar het staat op papier vóór de opleverdag in plaats van erna.

En bij het uitspitten van de data bleek er veel meer in te zitten dan het platform vandaag gebruikt — geteld, niet vermoed: 678.309 kassabonnen met het verkoopuur bij elke bon, een categorieboom van 33 categorieën, en de betaalmix. Daarmee kan een volgende fase vragen beantwoorden als: daalt de omzet omdat er minder klanten komen of omdat ze minder meenemen, en welke producten verkopen uit vóór sluitingstijd? Er ligt ook een gemeten B2B-bestelkanaal van € 1,8 miljoen naast de kassa (vraag 43) — binnen of buiten scope is een keuze die bij jou ligt. De scope van fase 1 blijft de scope; dit is voor het gesprek na de 27e.
