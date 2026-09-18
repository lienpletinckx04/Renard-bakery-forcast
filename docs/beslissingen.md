# Beslissingen

> Eén blok per beslissing die later ter discussie kan komen. Datum, wat, waarom, en wat het alternatief was. Kort houden. Een beslissing die je niet in vijf regels kan uitleggen, is nog geen beslissing.

---

### 2026-08-07, Aparte repository, lokaal op macOS
**Wat:** dit project krijgt een eigen private repository onder eigen beheer, en er wordt lokaal op de Mac gebouwd, niet in een cloud-ontwikkelomgeving.
**Waarom:** klantdata blijft daarmee op één machine die volledig onder eigen controle staat. In een cloud-omgeving staat de data al bij een derde partij vóór je iets pusht, en een fout in de gitignore is dan meteen een datalek in plaats van een lokale slordigheid. Bovendien is de rekenlast klein, dus cloud-compute voegt niets toe.
**Alternatief:** ontwikkelen in een codespace. Verworpen om bovenstaande reden.

---

### 2026-08-07, Aparte Claude Code-configuratiemap
**Wat:** dit project draait Claude Code met een eigen configuratiemap, ingelogd op het teamabonnement van de opdrachtgever.
**Waarom:** het bouwwerk gebeurt op afgesproken credits van de opdrachtgever, maar het eigen account moet ingelogd blijven voor eigen werk. Zonder gescheiden configuratie is inloggen op het ene account uitloggen op het andere.
**Alternatief:** telkens heen en weer inloggen. Verworpen, want dat leidt gegarandeerd tot een sessie waarin de verkeerde credits branden.

---

### 2026-08-07, Beslismodel boven voorspelmodel
**Wat:** het project levert een baklijst, niet een voorspelling. De voorspelling is een tussenstap.
**Waarom:** de bakker beslist een aantal, niet een verwachting. Het optimale aantal ligt boven de mediaan wanneer een gemiste verkoop meer kost dan een onverkocht stuk, en Too Good To Go verschuift dat optimum verder omhoog. Wie de voorspelling als eindproduct levert, laat structureel marge liggen en legt de moeilijkste stap bij de klant.
**Alternatief:** klassiek forecastingdashboard. Verworpen, zie `model-ontwerp.md`.

---

### 2026-08-07, Backtest-harnas vóór het model
**Wat:** de rolling-origin backtest en de baselines worden gebouwd vóór er aan het eigenlijke model gewerkt wordt.
**Waarom:** zonder harnas weet je niet of een model iets doet, en zonder baselines weet je niet of het beter is dan niets doen. Voor een bakkerij is "dezelfde weekdag vorige week" een sterke baseline, en het is beter dat vroeg te weten dan na vijf dagen modelwerk.
**Alternatief:** model eerst, evaluatie erna. Verworpen, dat is de manier waarop dit soort projecten in een niet-verifieerbare belofte eindigt.

---

### 2026-08-12, CFO-platform in fase 1, als tweede spoor op één fundering
**Wat:** fase 1 levert twee deliverables: de baklijst (spoor A) en het CFO-platform (spoor B). Beide lezen uit hetzelfde canonieke datamodel en dezelfde nachtelijke berekening. De cijferlaag wordt één keer gebouwd.
**Waarom:** de opdrachtgever heeft het platform als deliverable bevestigd. Als twee losse bouwwerken zou de cijferlaag twee keer bestaan en na de eerste wijziging uit elkaar lopen, waarna de baklijst en het dashboard verschillende getallen tonen voor hetzelfde product. Dat is het soort fout dat het vertrouwen in beide breekt.
**Alternatief:** het platform als aparte fase na de baklijst. Verworpen op vraag van de opdrachtgever. Gevolg: de raming gaat van vijf tot zes dagen naar tien tot dertien, en dat wacht op schriftelijke bevestiging (vraag 28).

---

### 2026-08-12, App-gereedheid via een contractlaag, niet via een frameworkkeuze
**Wat:** in een latere fase komt er een mobiele app op beide sporen. Fase 1 bouwt die niet, maar legt wel vast dat de kern headless is en dat elk scherm uit een genummerd JSON-contract leest. Er wordt in fase 1 geen app-framework gekozen.
**Waarom:** het verschil tussen "de app later aanhaken" en "de app later herbouwen" is niet de technologie maar de vraag of de bedrijfslogica in de kern of in de schermen zit. Een contractlaag kost in fase 1 vrijwel niets en houdt die keuze open. Een frameworkkeuze nu is een keuze op de minst geïnformeerde dag van het project.
**Alternatief:** meteen een app-stack kiezen en daar de web-UI op bouwen. Verworpen: dat betaalt de kost van de app vóór er iemand bevestigd heeft hoe ze eruitziet.

---

### 2026-08-12, De baklijst is geschrapt, het platform is het product
**Wat:** fase 1 levert één deliverable, een CFO-platform met login, database en koppelingen. De baklijst en de beslislaag zijn uit de scope. Het voorspelmodel blijft, maar als vooruitblik binnen het platform. Deze beslissing vervangt de twee-sporenbeslissing van eerder vandaag.
**Waarom:** beslist door de opdrachtgever. Het platform is wat de eindklant koopt en wat in latere fasen de app draagt.
**Gevolg:** `CLAUDE.md`, `README.md`, `scope.md` en `plan-fase1.md` zijn omgeschreven. Alle drie zeiden voordien dat wie dit als dashboardproject behandelt het verkeerde ding bouwt; dat is niet langer waar en het staat er niet meer. `model-ontwerp.md` blijft staan als voorbereiding op een latere fase en is als zodanig gemarkeerd.
**Alternatief:** beide sporen behouden. Verworpen door de opdrachtgever. De raming gaat daarmee van 10 tot 13 dagen naar 11,5 tot 16,5, want het platform wint aan omvang wat de baklijst verliest.

---

### 2026-08-12, Klantdata mag naar een beheerde database, onder drie voorwaarden
**Wat:** de beslissing van 7 augustus dat klantdata op één machine blijft en niet naar een gehoste omgeving gaat, wordt herzien. De geaggregeerde verkoopcijfers komen in een beheerde Postgres.
**Waarom:** een platform met een login kan niet anders. De cijfers moeten staan waar de gebruiker ze bereikt. Vasthouden aan de oude regel zou betekenen dat de deliverable niet te leveren is.
**Voorwaarden:** (1) EU-regio, (2) verwerkersovereenkomst met de leverancier en infrastructuur op naam van de eindklant, (3) uitsluitend geaggregeerde productverkoop — geen `partner_id`, geen naam, geen adres, geen bonnotitie, precies zoals de extractie ze vandaag al nooit opvraagt.
**Wat onveranderd blijft:** de rúwe brondata (Odoo-extract, TGTG-pdf's) blijft lokaal en gaat nooit de repo in. Wat naar de database gaat, is het geaggregeerde datamodel en niet de dump.
**Alternatief:** zelf hosten op een kleine server. Niet verworpen, wel afhankelijk van G7: dat is een eigendoms- en factuurvraag, geen technische.

---

### 2026-08-12, Cijfers worden nooit gekleurd
**Wat:** elk getal in het platform staat in zwart. Ook stijging en daling. Richting komt uit het teken en een pijl. Kleur zit alleen in de vlakken en lijnen van een grafiek, waar bordeaux identiteit is en nooit betekenis.
**Waarom:** het merk ís rood. In een financiële tool leest rood als verlies. Die twee kunnen niet naast elkaar bestaan zonder dat één van beide zijn betekenis verliest. Zwarte cijfers lossen het op in plaats van het te verdoezelen, en ze overleven bovendien een zwart-witafdruk en kleurenblindheid.
**Alternatief:** merkrood voor negatief, groen voor positief. Verworpen: dan betekent de merkkleur "slecht nieuws" op elk scherm.

---

### 2026-08-12, Verzekeringsextract: de volledige historiek op bonregelniveau, lokaal
**Wat:** naast het geaggregeerde werkextract wordt de volledige onbewerkte historiek uit Odoo gearchiveerd: alle bonregels (~1,56 miljoen), de orderkoppen, de betalingen per bon en de dimensietabellen (producten, categorieën, kassa's, betaalmethodes). Als parquet, lokaal, nooit in git. Klantvelden worden nooit opgevraagd — geen `partner_id`, geen naam, geen bonnotitie.
**Waarom:** de API-toegang is fragieler dan hij lijkt. De productieomgeving is geblokkeerd op een betalende licentie (G6), en de preprod is op 7 augustus al eens herbouwd waarbij de toegang brak. Valt de toegang definitief weg, dan is zeven jaar verkoophistoriek onherstelbaar verloren. Met dit archief blijft elke toekomstige vraag — mandjesanalyse, betaalmix, uurpatronen, een andere aggregatiekeuze — beantwoordbaar zonder Odoo ooit nog nodig te hebben.
**Alternatief:** alleen het geaggregeerde werkextract bewaren. Verworpen: aggregatie is een keuze, en elke keuze die we vandaag maken gooit informatie weg die morgen de verkeerde kan blijken. Het archief kost eenmalig enkele minuten API-tijd en wat schijfruimte.

---

### 2026-08-12, Een sluitingsdag met één losse bon blijft een sluitingsdag
**Wat:** `winkel_open` wordt niet langer bepaald door "er is minstens één kassabon", maar door een drempel: een dag geldt als open wanneer de dagomzet minstens 10% is van de mediaan van diezelfde weekdag. Onder die drempel is de dag gesloten en telt hij niet mee in baselines, backtest of afgeleide tabellen. De regel staat op één plek (`DREMPEL_OPEN` in `bakkerij/canoniek.py`) en `alleen_open_dagen()` is de enige poort waar erop gefilterd wordt.
**Waarom:** de oude regel markeerde vijf dagen als open die aantoonbaar sluitingsdagen waren — 1 tot 6 bonregels, € 0,03 tot € 54,18, alle vijf middenin een sluitingsperiode (paassluiting 2025, Nieuwjaar 2026, zomersluiting 2026). Uitgedrukt als aandeel van de mediaan van hun weekdag zitten ze op 0,000 tot 0,004; de laagste échte openingsdag zit op 0,67. Tussen die twee ligt geen enkele dag, dus de drempel is niet kritisch: 0,10 heeft een factor 25 marge naar onder en 6,7 naar boven. Zonder de zeef krijgt elk van die dagen in de backtest een fout ter grootte van een volledige dagomzet, en dat is een meetartefact dat als voorspelfout zou worden gerapporteerd. Het aantal sluitingsdagen gaat daarmee van 49 naar 54.
**Gevolg:** de bonregels van zo'n dag blijven wél in de verkooptabel staan. Het zijn echte transacties en de feitentabel liegt niet; de interpretatie zit in de kalender. Vier tests leggen het gedrag vast, inclusief de ondergrens waaronder de drempel wegvalt (minder dan acht dagen per weekdag is geen mediaan).
**Alternatief:** de rijen uit de verkooptabel verwijderen. Verworpen: dan is de feitentabel niet meer af te stemmen op Odoo, en is de correctie onzichtbaar voor wie later controleert.

---

### 2026-08-12, Bij een product is "geen rij" geen nulvraag
**Wat:** op dag × product mag de afwezigheid van een rij niet als nulvraag gelezen worden. Per product geldt eerst een beschikbaarheidsvenster; alleen binnen dat venster is een gat een echte nul. De vooruitblik per product wordt gebouwd op de 103 kernproducten met minstens 95% dagdekking, en de overige producten worden getoond als onbeschikbaar met reden (harde regel 8) tot hun aanbodpatroon bevestigd is.
**Waarom:** gemeten over de 529 open dagen heeft slechts een derde van de 329 producten een dekking van 95% of meer. 106 producten verkopen pas meer dan dertig dagen na de start voor het eerst, 122 stoppen meer dan dertig dagen voor het einde, en 11,1% van de omzet zit in producten die de periode niet overspannen. Twee gemeten voorbeelden maken het concreet: het grootste product van het assortiment (€ 308.000) verkoopt op 96 tot 100% van de dagen maandag tot vrijdag maar op 7% van de zaterdagen en 1% van de zondagen — het wordt in het weekend niet aangeboden. Een ander product doet € 91.000 op 62 dagen: 100% van de open dagen in januari, 4% in februari, nul de rest van het jaar. Wie zijn 467 lege dagen als nulvraag inleest, leert het model dat een product van € 91.000 vrijwel geen vraag kent. De 103 kernproducten dekken 84,1% van alle verkochte stuks, dus de afbakening kost weinig dekking en voorkomt een hele klasse van onzin.
**Alternatief:** alle 329 producten voorspellen en de gaten als nul inlezen. Verworpen om de bovenstaande reden. Tweede alternatief — het aanbodpatroon per product uit de data afleiden — is niet verworpen maar uitgesteld: het is te doen, en vraag 44 bepaalt of het nodig is of dat de bakkerij het patroon simpelweg kan aanleveren.

---

### 2026-08-12, De backtest rekent af in euro's omzet, niet in de kost van een bakbeslissing
**Wat:** de kernmaat van het harnas is de afwijking in euro's omzet — MAE per dag, WAPE als aandeel van de totale omzet, en de bias om te zien of de vooruitblik structureel te hoog of te laag zit. De newsvendor-afrekening blijft beschikbaar via een optionele `economie=`, maar ze is niet de maat waarop fase 1 beoordeeld wordt.
**Waarom:** de oorspronkelijke maat was de kost van een bakbeslissing, en die is in fase 1 niet te berekenen. Ze vraagt per product een productiekost en een restwaarde, en vraag 19 stelde vast dat die niet bestaan: Odoo berekende de kostprijs op alle 1.556.770 kassabonregels en kwam 1.556.054 keer op nul uit. Daarbij is de baklijst op 12 augustus uit de scope gehaald, dus de beslislaag is niet het product. Een harnas dat afrekent in een eenheid die niemand kan aanleveren, is een harnas dat nooit draait. WAPE is bovendien niet de MAPE die het modelontwerp terecht afwijst: MAPE straft fouten op kleine dagen onevenredig, WAPE weegt op omzet en is één percentage dat over periodes vergelijkbaar blijft.
**Gevolg:** gemeten op de canonieke data, 343 beslissingen per baseline: `weekdag_gemiddelde` haalt 8,4% WAPE op de dagomzet (€ 1.088 afwijking per dag op een gemiddelde van € 12.748, bias +€ 49). Per product per dag over de 103 kernproducten, 35.161 beslissingen: `weekdag_mediaan` haalt 20,2%. Dat is de lat. `naive` zit op 27,4% respectievelijk 37,2%, wat bevestigt dat het weekpatroon het dominante signaal is.
**Alternatief:** wachten met het harnas tot de marges er zijn. Verworpen: dan is er in fase 1 geen enkele manier om een vooruitblik te verantwoorden, en harde regel 7 verbiedt een voorspelling zonder backtest.

---

### 2026-08-12, Baselines krijgen expliciete doeldagen, en er wordt nergens op positie gerekend
**Wat:** elke baseline neemt de historiek plus een expliciete lijst datums die voorspeld moeten worden, en leidt de weekdag uit die datums af. Het harnas haalt die doeldagen uit de index van de werkelijkheid, en weigert een voorspelling die op andere dagen staat dan gevraagd. Een horizon van zeven betekent zeven **open** dagen, niet zeven kalenderdagen.
**Waarom:** de eerste versie rekende positioneel — `reeks.iloc[-7:]` voor de baseline, `zip()` voor de vergelijking. Dat is correct op een aaneensluitende reeks, en de verkoopreeks van deze bakkerij is dat niet: 54 van de 583 gemeten dagen was de zaak dicht, in blokken van acht dagen, ruim drie weken en losse feestdagen. Vrijwel geen van die blokken is een veelvoud van zeven. Gemeten met een sluiting van drie dagen: drie van de zeven voorspellingen landden op de verkeerde weekdag — maandag kreeg de waarde van een vrijdag (130 tegen 100), dinsdag die van een zaterdag (160 tegen 95, 68% te hoog). En bij twee van de drie origins vielen de datums van voorspelling en werkelijkheid niet samen, waarna `zip()` een vrijdagvoorspelling tegen een maandagwerkelijkheid afrekende. Een harnas dat stilzwijgend het verkeerde paar vergelijkt is erger dan geen harnas: het levert een cijfer dat betrouwbaar lijkt.
**Gevolg:** de oude tests draaiden uitsluitend op aaneensluitende reeksen, en dat is precies waarom dit nooit was opgevallen. Elke test over weekdagen bestaat nu in twee varianten, met en zonder een sluiting die geen veelvoud van zeven is. De testsuite gaat van 36 naar 76. `make baseline` en `make backtest` draaiden op een verzonnen demoreeks; die zijn vervangen door één `make backtest` op de echte canonieke data.
**Alternatief:** de reeks opvullen met nullen op sluitingsdagen zodat hij aaneensluitend wordt. Verworpen om dezelfde reden als bij de sluitingsdagen: dan leert het model dat er in augustus geen vraag naar brood is.

---

### 2026-08-12, De sluitingskalender vooruit komt uit de agenda van de klant, als optionele laag
**Wat:** de geplande sluitingen van de komende maanden worden opgehaald uit één agenda die de bakkerij zelf onderhoudt, gedeeld als geheime iCal-link, met een vaste titelconventie (`DICHT:`, `ANDERE UREN:`, `PROMO:`, `EVENT:`). De laag is optioneel: zonder ingestelde feed verandert er niets aan de kalender en aan geen enkel cijfer. De agenda overschrijft nooit een meting — voor gemeten dagen blijft de kassa de waarheid en dient de agenda alleen als controle; alleen voorbij het gemeten bereik is ze de enige bron. Reikt de agenda niet verder dan een bepaalde datum, dan is de vooruitblik daarna onbeschikbaar mét die reden.
**Waarom:** de vooruitblik heeft de sluitingen van de komende twaalf maanden nodig en die staan in geen enkele dataset; een voorspelling voor een dag waarop de zaak dicht is, is ruis. Handmatig doorgeven werkt één keer en daarna niet meer. Een iCal-link vraagt geen API-sleutel, geen OAuth en geen toegang tot andere agenda's, en de klant onderhoudt hem op zijn telefoon in plaats van in een bestand dat iemand moet mailen. De bijvangst is een controle die we anders niet hebben: als de agenda ook historiek bevat, moeten twee onafhankelijke bronnen het over dezelfde 54 sluitingsdagen eens zijn, in plaats van dat één gemeten drempel op zijn woord geloofd wordt.
**Voorwaarden:** de klant moet ermee instemmen en de agenda onderhouden (vraag 46). Zolang dat niet bevestigd is, blijft de laag ongebruikt en zichtbaar afwezig.
**Alternatief:** de Google Places API voor openingsuren. Verworpen op een harde grond en niet op een voorkeur: die API geeft alleen de huidige uren en maximaal een week vooruit aan speciale uren, en kent geen historiek — "was deze zaak open op 15 april 2025" is er niet uit te halen, terwijl onze behoefte 534 dagen verleden is. Vooruit is het bovendien de zwakste bron die er is, want speciale uren worden door ondernemers structureel niet bijgehouden, en een zomersluiting van drie weken is precies het geval dat er niet in staat. Tweede alternatief — een invulscherm in het platform zelf — is niet verworpen maar uitgesteld: dat is de betere langetermijnoplossing en het is nieuwe scope.
**Gevolg:** een half begrepen agenda-item wordt gemeld en niet gebruikt. Een herhalende reeks (RRULE), een titel zonder bekend voorvoegsel en een item met een uur in plaats van een hele dag leveren elk een waarschuwing op in plaats van een stille interpretatie. Dertien tests leggen dat vast, waaronder de test dat een ongebruikte feed de kalender letterlijk ongewijzigd laat.

---

### 2026-08-12, De berekeningslaag en het contract worden databaseloos gebouwd
**Wat:** de berekeningslaag bestaat uit pure functies op DataFrames en de contractlaag maakt daar JSON van. Geen van beide raakt een database. De uitvoer gaat vandaag naar bestanden in `platform/contract/`; zodra het Supabase-project er is, schrijft dezelfde berekening naar tabellen en serveert een API-route hetzelfde antwoord. De vorm verandert daarbij niet.
**Waarom:** poort G7 — waar de database komt te staan — blokkeert formeel alles vanaf de database, en met een deadline op 27 augustus is wachten niet betaalbaar. De blokkade geldt echter alleen het *hosten*, niet het *bouwen*: een aggregatie heeft geen Postgres nodig om te kloppen, en een JSON-antwoord heeft geen API nodig om zijn vorm te bewijzen. Door de berekening databaseloos te houden, is de databasestap straks een dunne schrijflaag in plaats van het fundament. Bijkomend voordeel: de hele keten is met één commando herbouwbaar zonder netwerk, en de tests draaien zonder testdatabase.
**Gevolg:** alle zeven schermen draaien vanavond lokaal op echte cijfers, en het contract is gebonden vóór de eerste tabel bestaat — precies de volgorde die `CLAUDE.md` voorschrijft (stap 4 vóór stap 6).
**Alternatief:** wachten op G7 en dan schema-eerst bouwen. Verworpen: dat legt het bewijs dat de cijfers kloppen achter een beslissing die bij iemand anders ligt.

---

### 2026-08-12, De gegenereerde contract-JSON gaat niet in git
**Wat:** `platform/contract/` is gitignored. De generator (`scripts/contract_bouw.py`) staat wel in versiebeheer, de uitvoer niet. Wie het platform wil draaien, draait eerst `make contract`.
**Waarom:** wat er uit komt is geaggregeerde dagomzet, productomzet en kanaalverdeling van de eindklant. Harde regel 2 zegt dat klantdata de repo niet in gaat, en die regel maakt geen uitzondering voor "maar het is al geaggregeerd". Geaggregeerd mag naar de gehoste database onder de drie voorwaarden van de databasebeslissing; een git-repo is geen van die drie. Het verschil is bovendien praktisch: een repo is te klonen, te forken en te pushen naar een plek die niemand overzien heeft, en een commit is niet terug te nemen.
**Gevolg:** de mock-bestanden blijven bestaan als vorm-referentie, maar de schermen lezen `@/contract/` en niet meer `@/mock/`. Een schone kloon van de repo bouwt niet zonder eerst `make contract` te draaien, en dat is de bedoeling.
**Alternatief:** de JSON committen zodat het platform meteen bouwt. Verworpen om bovenstaande reden. Tweede alternatief — een verkleinde of verzonnen variant committen — is niet verworpen maar niet nodig: `platform/mock/` doet dat al.

---

### 2026-08-12, Een beperking aan een cijfer is even zichtbaar als het cijfer zelf
**Wat:** `onbeschikbaar` in het contract dekt niet alleen een heel leeg vak, maar ook een cijfer dat er wél staat met een beperking eraan: geen vergelijking met vorig jaar, een maand die uit een grafiek weggelaten is, een aanname in een voorspelling. Elk scherm toont die regels onderaan in een blok "Wat hier niet staat, en waarom".
**Waarom:** harde regel 8 stond er al voor een geblokkeerd cijfer, maar het stillere geval is gevaarlijker. Drie van de vier kerncijfers op het overzichtsscherm hadden geen jaar-op-jaarpijl omdat het vorige jaar in die periode een ander aantal open dagen had. Zonder uitleg is een ontbrekende pijl niet te onderscheiden van een pijl die iemand vergeten heeft. Hetzelfde geldt voor de jaarvergelijking: augustus 2026 telt drie gemeten open dagen tegen negen in augustus 2025, en een staaf naast een staaf zou daar een instorting tonen die er niet is. Die maanden worden nu weggelaten mét vermelding, in plaats van getoond zonder.
**Gevolg:** het overzichtsscherm draagt vandaag drie zulke regels, de vooruitblik drie. Dat is geen onafheid maar de eerlijke staat van de data.
**Alternatief:** de vergelijking tonen en de scheefheid negeren. Verworpen: dat is precies de fout die een CFO-platform onbruikbaar maakt op het moment dat iemand erop wil handelen.

---

### 2026-08-12, De toegang wordt gebouwd zonder database, in de vorm die Supabase Auth later overneemt
**Wat:** aanmelden met gebruikersnaam en wachtwoord, bewaakt door `platform/proxy.ts` vóór de router. Gebruikers staan in de omgevingsvariabele `PLATFORM_GEBRUIKERS` als `naam:rol:<zout>$<afdruk>` met PBKDF2-SHA256 op 210.000 iteraties; de sessie is een HMAC-ondertekende HttpOnly-cookie van twaalf uur. Twee gebruikers ingesteld: `lien` en `kwinten`, beide met rol `beheerder`.
**Waarom:** dezelfde redenering als bij de berekening en het contract — poort G7 blokkeert de gehoste database, niet het afschermen van het platform. Wat straks wisselt is één functie (`verifieer`); de cookie, de bewaking en de schermen blijven. De bewaking staat bewust vóór de router en niet in elk scherm apart: één vergeten scherm zou genoeg zijn om de omzetcijfers van de klant openbaar te maken. Om diezelfde reden staan de dashboardschermen nu op `force-dynamic` — een vooraf gebouwde bladzijde draagt de cijfers al in zich vóór iemand zich aanmeldt.
**Gevolg:** geen wachtwoord in de code, in een commit of in `.env.example`; alleen afdrukken, en die staan in het gitignored `platform/.env.local`. Een lege `PLATFORM_GEBRUIKERS` betekent dat niemand binnenkomt, niet dat de deur openstaat. **Het gedeelde wachtwoord van vandaag is een testwachtwoord en moet vervangen zijn vóór de eindklant het platform ziet** — dat is één keer `scripts/maak_gebruiker.mjs` draaien.
**Alternatief:** wachten op Supabase Auth. Verworpen: dat maakt de afscherming afhankelijk van een poort die buiten ons ligt, terwijl de schermen nu al cijfers tonen.

---

### 2026-08-12, "Vooruitblik" heet voortaan "Prognose"
**Wat:** de naam is doorgevoerd tot in de code — route, contractsleutels, `onbeschikbaar`-velden, modulenamen en het backtest-script.
**Waarom:** beslissing van de opdrachtgever. "Prognose" is de term die in een financiële context gelezen wordt zoals ze bedoeld is; "vooruitblik" leest als een rubriek.
**Gevolg:** `/prognose` in plaats van `/vooruitblik`, `prognose.json` in het contract, `scripts/backtest_prognose.py`. De oudere dagboekentry's zijn niet herschreven: die leggen vast wat er op dat moment gebouwd is, en dat hoort te blijven kloppen.
**Alternatief:** alleen het label op het scherm wisselen. Verworpen: twee namen voor hetzelfde ding is precies hoe een contract uit elkaar loopt.

---

### 2026-08-12, Bordeaux vlakken met witte cijfers, als verfijning van "alle cijfers zwart"
**Wat:** twee vaste kerncijfers — het eerste kerncijfer op Dagoverzicht en het weektotaal op Prognose — staan op een effen bordeaux vlak, naar de flyer uit de logogids, met het cijfer in wit en het label in beige. Alle andere cijfers blijven zwart.
**Waarom:** de regel van 12 augustus dat elk cijfer zwart is, gaat over betekenis: kleur mag nooit "goed" of "slecht" zeggen. Een vlak dat altijd bordeaux is, op een vaste plek, zegt dat niet — het draagt merkidentiteit, geen richting. Vastgelegd in `.claude/skills/huisstijl/SKILL.md`; herroepbaar door Lien, want het is haar huisstijlregel die hier verfijnd wordt.
**Voorwaarden:** zo'n vlak ligt vast op een positie en verhuist nooit mee met goed of slecht nieuws. Zou een bordeaux vlak ooit worden ingezet om een resultaat te markeren, dan vervalt deze uitzondering.
**Alternatief:** strikt vasthouden aan uitsluitend zwarte cijfers, zonder uitzondering. Verworpen: de logogids toont dit patroon zelf op de flyer, en de uitzondering blijft beperkt tot twee vaste posities die nooit van kleur wisselen.

---

### 2026-08-12, Prognose blijft Prognose, geen "Planning"
**Wat:** het navigatie-item en de route heten Prognose. Het voorstel om ze te hernoemen naar "Planning" is niet doorgevoerd.
**Waarom:** het scherm toont een voorspelling met bandbreedte, geen planningsinstrument. "Planning" zou functionaliteit beloven die buiten scope ligt — de baklijst en de beslislaag zijn dezelfde dag geschrapt. Herroepbaar door Kwinten; de naam "Prognose" zelf is de dag ervoor al vastgelegd op vraag van de opdrachtgever (zie "'Vooruitblik' heet voortaan 'Prognose'").
**Alternatief:** de naam "Planning" overnemen, voorgesteld in een externe codex-review. Verworpen om bovenstaande reden. De overige voorgestelde hernoemingen — Overzicht→Dagoverzicht, Kanalen→Verkoopkanalen, Producten→Productmix, Marge→Margebewaking — zijn wel doorgevoerd.

---

### 2026-08-12, Productverschuiving rangschikt op euroverschil, niet op procenten
**Wat:** de stijgers/dalers-tabellen op Productmix rangschikken op het verschil in euro's tussen de laatste 30 dagen en de 30 ervoor, niet op het percentage. Een product zonder omzet in de vorige periode krijgt geen percentage — dat zou een deling door nul zijn — maar de markering "nieuw".
**Waarom:** een product dat van € 10 naar € 30 gaat (200%) is geen groter nieuws dan een brood dat € 400 inlevert. Op percentage rangschikken zou de tabel laten domineren door kleine producten met toevallige uitschieters.
**Alternatief:** rangschikken op percentage. Verworpen om bovenstaande reden. Herroepbaar door Kwinten.

---

### 2026-08-12, Het prognose-weektotaal staat er zonder bandbreedte
**Wat:** Prognose toont een weektotaal als som van de dagverwachtingen, zonder bandbreedte eromheen. De reden staat als onbeschikbaar-regel op het scherm (harde regel 8).
**Waarom:** de bandbreedte per dag komt uit dagfouten, en fouten van opeenvolgende dagen hangen samen. Ze zomaar optellen tot een weekband zou een zekerheid tonen die de backtest nooit gemeten heeft — harde regel 7 verbiedt precies dat.
**Alternatief:** de dagbanden optellen tot een weekband. Verworpen om bovenstaande reden. Herroepbaar door Kwinten, mocht een backtest op weekniveau ooit de echte spreiding aantonen.

---

### 2026-08-12, De merkbeelden (/brand/) zijn uitgesloten van de toegangsproxy
**Wat:** `platform/proxy.ts` laat alles onder `/brand/` door zonder sessie, naast de bestaande uitzonderingen voor de statische Next-bestanden en het lettertype. Het contract en alle cijferdata blijven achter de bewaking.
**Waarom:** logo en fotografie zijn identiteit, geen cijfers, en het inlogscherm heeft ze nodig vóór er een sessie bestaat. Zonder de uitzondering laadden de merkbeelden niet op het inlogscherm zelf.
**Alternatief:** de merkbeelden inbakken in de applicatiecode in plaats van als statisch bestand serveren. Verworpen: dat maakt het vervangen van een beeld een codewijziging in plaats van een bestand droppen. Herroepbaar door Kwinten.

---

### 2026-08-13, De prognose begint nooit vóór vandaag, en het meetgat krijgt een reden

**Wat:** de prognose start op `max(gemeten_tot + 1 dag, vandaag)`, niet langer onvoorwaardelijk op de dag na de laatste meting. De kalender loopt daarvoor 60 dagen (`VOORUIT_DAGEN`) door voorbij de laatste gemeten verkoopdag, zodat er voor elke voorspelde dag een kalenderrij bestaat. Dagen die in de kalender als gemeten én gesloten staan, worden binnen dat venster overgeslagen. Het gat tussen de laatste meting en vandaag verschijnt als `onbeschikbaar` met reden, uitgesplitst naar "gemeten en gesloten" tegenover "nog niet ingeladen".
**Waarom:** de oude regel startte altijd op gemeten_tot + 1, ongeacht hoe oud die meting was. Op 12 augustus 2026 liep het extract elf dagen achter; zonder de correctie voorspelt het scherm dan een week die grotendeels al voorbij is, zonder dat te zeggen. Zestig dagen vooruit is ruim genoeg voor een horizon van een week plus een extract dat bijna twee maanden achterloopt.
**Gevolg:** `bakkerij/canoniek.py` krijgt `prognosevenster()` en `Prognosevenster`/`Meetgat` als vaste plek voor deze regel; `bakkerij/contract.py` bouwt de prognose nu op dat vensterobject in plaats van op een losse `gemeten_tot`.
**Alternatief:** onvoorwaardelijk op gemeten_tot + 1 starten en het gat verzwijgen. Dat was het bestaande gedrag en is verworpen: harde regel 8 verbiedt een cijfer dat een periode voorspelt die al voorbij is zonder dat te melden.

---

### 2026-08-13, Productverschuiving vergelijkt alleen vensters met evenveel gemeten verkoopdagen

**Wat:** de stijgers/dalers-tabel op Productmix vergelijkt twee vensters van gelijke lengte in gemeten open verkoopdagen, niet in kalenderdagen. Tellen de twee vensters niet evenveel dagen, dan is er geen vergelijking: de tabel is leeg en het scherm toont de reden met beide daglengtes erbij, in plaats van cijfers te tonen.
**Waarom:** op kalenderdagen gerekend telt een venster van 30 dagen kort na een sluitingsperiode minder verkoopdagen dan het venster ervoor. Zo'n scheve vergelijking laat op papier vrijwel elk product stijgen en toont dalers die niet gedaald zijn — een sluiting die zich voordoet als vraaguitval.
**Alternatief:** op kalenderdagen blijven vergelijken en de scheefheid negeren. Verworpen om bovenstaande reden; het is dezelfde afweging als bij de baselines van 12 augustus ("Baselines krijgen expliciete doeldagen"), nu toegepast op dit scherm.

---

### 2026-08-13, PBKDF2-scheidingsteken wordt een punt, niet een dollarteken

**Wat:** in `PLATFORM_GEBRUIKERS` scheidt voortaan een punt het zout van de afdruk (`naam:rol:<zout>.<afdruk>`), niet langer een dollarteken. Dit vervangt het formaat uit de beslissing van 12 augustus over de toegang. Een gebruikersregel die niet aan de vorm voldoet, wordt eenmalig hardop gelogd in plaats van stil overgeslagen.
**Waarom:** de env-loader van Next doet variabele-expansie op `.env`-bestanden: alles vanaf een `$` werd stilletjes vervangen door niets, waardoor elke afdruk werd afgeknipt en geen enkel wachtwoord meer klopte. Een punt komt niet voor in base64url en betekent voor geen enkele env-loader iets.
**Gevolg:** bestaande gebruikersregels in `platform/.env.local` moesten worden herafgedrukt met het nieuwe scheidingsteken.
**Alternatief:** de waarde in `.env.local` tussen enkele aanhalingstekens zetten. Verworpen: dat werkt alleen lokaal en vergt discipline bij elke toekomstige omgeving, terwijl het dollarformaat op Vercel of in CI wél had gewerkt — dan waren er twee vormen van hetzelfde bestand in omloop geweest.

---

### 2026-08-13, Censurering telt pas als drie signalen samenvallen, niet één drempel

**Wat:** een product-dag telt als censureringssignaal (leeg rek, geen gebrek aan vraag) alleen wanneer drie voorwaarden tegelijk gelden: minstens 10 bonnen die dag (`MIN_BONNEN`), de laatste bon minstens 2 uur vóór de laatste bon van de hele winkel díe dag (`DREMPEL_UREN`, tegen een dagelijkse sluitproxy, niet een vaste sluittijd), én minstens 2 uur onder de eigen p90-referentie van dat product op zijn drukke dagen. Alle drie staan als moduleconstanten met motivering in `bakkerij/censurering.py`.
**Waarom:** een eerste, eenvoudigere versie met één drempel tegen een vaste sluittijd rapporteerde 54% censurering, en dat bleek grotendeels schaarste-vertekening: een product met vier bonnen per dag heeft zijn laatste bon toevallig uren voor sluit, ook met volle rekken. Tegen een vaste sluittijd gemeten gaf dezelfde opzet 97% op zondag — dat was de kortere zondagopening, geen leeg rek. Elk van de drie filters snijdt precies één van die vertekeningen weg. Gemeten op 41.940 gewogen product-dagen: 33% draagt een leeg-reksignaal, en 98 producten (66% van de omzet) zijn structureel gecensureerd (≥20% van hun gewogen dagen).
**Gevolg:** de prognose meet dus verkoop, niet vraag; die bevinding hoort in het backtest-rapport (E4) en niet alleen in deze module. De meting is een ondergrens — een product dat altijd vroeg uitverkocht is, heeft een vroege referentie en wordt nooit gevlagd — en die bovengrens wordt apart gerapporteerd (`bovengrens`-kolom) zodat de blinde vlek zichtbaar blijft in plaats van verzwegen.
**Alternatief:** één drempel tegen een vaste sluittijd. Verworpen: die meet beide vertekeningen (schaarste en de korte zondag) en geen van beide onderscheidt hij van een echt leeg rek.

---

### 2026-08-13, Het laatste verkoopuur komt in een eigen extractie, niet in het canonieke model

**Wat:** O11 (het laatste verkoopuur per product per dag) wordt beantwoord met een aparte aggregaat-extractie — datum × product_id × eerste/laatste uur × aantal bonnen (`scripts/odoo_laatste_uur.py`) — en niet door een uurkolom aan de canonieke `verkopen`-tabel toe te voegen.
**Waarom:** het uur dient uitsluitend de censureringsvraag (O8): is de kassa vraag aan het meten of een leeg rek? Geen ander scherm, geen andere berekening heeft het nodig. Het canonieke model verbreden voor één vraag zou een kolom toevoegen die overal moet worden meegesleept — migraties, tests, contract — voor een gebruik dat maar op één plek bestaat.
**Alternatief:** het canonieke datamodel verbreden met een uurveld. Verworpen om bovenstaande reden; herroepbaar zodra een tweede vraag hetzelfde uur nodig heeft.

---

### 2026-08-13, De prognose draait voortaan op `weekdag_niveau`, ondanks een winst onder de eigen vijfprocentregel

**Wat:** de productieprognose gebruikt `weekdag_niveau` (weekdagmediaan over de laatste 8 weken, geschaald met een niveaufactor uit de laatste 14 open dagen, beide geklemd op [0,5–2,0]) in plaats van `weekdag_gemiddelde`.
**Waarom:** gemeten 8,2% WAPE op de dagomzet tegen 8,4% voorheen, en 20,1% tegen 20,2% per product-dag — een winst die onder de eigen vijfprocentregel van `vergelijk()` blijft ("rapporteer als gelijkwaardig en kies dan de eenvoudigste"). Die regel wordt hier bewust niet gevolgd: de dragende reden is niet de WAPE-winst maar de aanpassingssnelheid na een heropening. `weekdag_gemiddelde` heeft acht weken nodig om een niveauverschuiving te volgen, `weekdag_niveau` twee. Na de zomersluiting is dat precies het scenario waarin het platform staat.
**Gevolg:** `scripts/contract_bouw.py` wijst nu naar `bakkerij.model.verfijning.weekdag_niveau`; de vergelijkbaarheidsregel van 12 augustus ("Baselines krijgen expliciete doeldagen") blijft gelden, `weekdag_niveau` bouwt erop voort.
**Alternatief:** bij `weekdag_gemiddelde` blijven conform de vijfprocentregel. Verworpen: die regel is gemaakt voor het geval dat twee modellen inwisselbaar zijn in een stabiel regime, en dit is geen stabiel regime.

---

### 2026-08-13, De feestdagcorrectie is gebouwd en afgewezen — de code blijft voor een tweede jaar historiek

**Wat:** `bakkerij/model/verfijning.py` bevat `met_feestdagcorrectie`, die de baseline per kalenderkenmerk (feestdag, dag ervoor, brugdag) schaalt met een uit de historiek geschatte factor. Ze draait niet in productie. `evalueer()` kreeg er een parameter `alleen_dagen` bij om zo'n correctie te toetsen op precies de dagen die ze raakt, in plaats van in het totaalcijfer te laten verdwijnen.
**Waarom:** afgerekend op alleen de geraakte dagen zelf scoort de correctie slechter dan de basisbaseline — 11,7% WAPE tegen 10,7%. Eén jaar historiek bevat te weinig feestdagen om de factoren betrouwbaar te schatten; een mediaan over een handvol dagen is een gok. Harde regel 7 verbiedt een voorspelling zonder backtest, en deze backtest zegt nee.
**Gevolg:** de code blijft in de repository staan voor herkansing zodra een tweede jaar historiek beschikbaar is; ze wordt niet aangeroepen vanuit `scripts/contract_bouw.py`.
**Alternatief:** de correctie toch meenemen omdat het idee op zich klopt. Verworpen: harde regel 7 geldt ongeacht hoe plausibel de redenering is zonder meting.

---

### 2026-08-13, De prognoseband komt per horizonstap uit gemeten kwantielen, niet uit één gepoolde band

**Wat:** de band rond de prognose wordt per dag gebouwd uit de residukwantielen van díe horizonstap (`rolling.per_horizon` + `band_per_stap`): de eerstvolgende dag draagt de kwantielen van stap 1, de zevende dag die van stap 7. Eerder kwam de hele band uit één gepoolde meting over alle stappen samen. De gemeten dekking van de band (`rolling.dekking`, causaal gemeten — de band voor origin k komt uit de residuen van eerdere origins, niet uit zichzelf) staat voortaan hardop in de nauwkeurigheidstekst van het contractantwoord.
**Waarom:** de out-of-sample dekkingsmeting van 13 augustus 2026 toonde dat de gepoolde 10-90-band maar 56 à 74% dekte waar 80% beloofd werd — te breed voor morgen, te smal voor over een week. Per horizonstap gemeten dekt de band 56 tot 82%; die spreiding wordt getoond in plaats van weggewerkt, precies zoals harde regel 7 een voorspelling zonder eerlijke backtest verbiedt.
**Gevolg:** `contract.prognose()` krijgt drie optionele parameters (`stappen`, `track`, `banddekking`); het prognose-antwoord draagt nu ook een trackrecord (28 dagen voorspeld naast werkelijk, out-of-sample) als aparte grafiek, zodat de belofte van de band naast de belofte van het model te controleren staat.
**Alternatief:** de gepoolde band houden, of de kwantielen oprekken tot de gemeten dekking uitkomt op 80%. Verworpen: beide maskeren de meting in plaats van haar te tonen.

---

### 2026-08-13, De kruisterm is de sluitpost in beide ontbindingen, niet een apart afgeronde term

**Wat:** in `ontbinding_prijs_volume` en `bonritme` (`bakkerij/berekening.py`) worden de overige termen en het gemeten verschil elk op de cent afgerond, en de kruisterm wordt berekend als het restant dat de som exact op het verschil laat uitkomen. De invariant — volume + prijs + kruisterm + nieuw − verdwenen == verschil, respectievelijk bonneneffect + bonbedrag_effect + kruisterm == verschil — klopt daardoor altijd op de cent.
**Waarom:** de kruisterm is wiskundig toch al het restant van de andere termen. Vijf termen elk apart op de cent afronden en dan eisen dat ze optellen, kan tot twee cent naast het gemeten verschil landen; een ontbinding die niet optelt is geen ontbinding.
**Alternatief:** alle termen apart afronden en de afrondingsfout laten staan of verzwijgen. Verworpen: beide laten een gat van tot twee cent, zichtbaar of onzichtbaar, terwijl de sluitpost-aanpak exact optelt zonder de andere termen te vervalsen.

---

### 2026-08-13, Bonritme rekent alleen over dagen die in zowel de omzet- als de bonnenbron zitten

**Wat:** `bonritme()` (`bakkerij/berekening.py`) vergelijkt bonnen per dag en gemiddeld bonbedrag alleen over gemeten open dagen die zowel in de omzettabel als in de bonnentelling voorkomen. Een dag met omzet maar zonder bonnenmeting doet niet mee in het venster of de ontbinding, en wordt apart geteld in `dagen_zonder_bonnen`.
**Waarom:** zo'n dag met nul bonnen meetellen zou het gemiddeld bonbedrag (omzet/bonnen) naar oneindig sturen en de ontbinding in bonnen- en bonbedrag-effect vergiftigen met een verzonnen getal.
**Alternatief:** de ontbrekende bonnendag met bonnen op nul meetellen. Verworpen om bovenstaande reden — dat is het soort verzonnen meting dat harde regel 6 en 8 uitsluiten.

---

### 2026-08-13, De datakwaliteitsstatus verschijnt als tekst zonder kleurcodering, en zwijgt wanneer alles goed is

**Wat:** het standscherm (Instellingen) en de voettekst van elk scherm tonen de status per bron en per wachter (`goed`, `let_op`, `fout`) als gewoon Nederlands woord, zonder gekleurde bolletjes of badges. De voettekst toont bij de ergste uitkomst `goed` niets; alleen bij `let_op` of `fout` verschijnt één sober linkje naar Instellingen.
**Waarom:** de huisstijl laat kleur nooit een oordeel dragen — tot nu toe toegepast op cijfers en grafieklijnen, hier voor het eerst op statusindicatoren, waar het gangbare patroon juist rood/oranje/groen is. Een voettekst die ook bij "goed" iets meldt, is precies de alarmvermoeidheid waardoor niemand meer leest wanneer het wél misgaat.
**Alternatief:** gekleurde statusbolletjes zoals in de meeste dashboards, en een geruststellende melding bij een goede stand. Beide verworpen: het eerste omdat de huisstijl geen betekeniskleuren kent, het tweede omdat stilte een sterkere garantie is dan herhaalde bevestiging.

---

### 2026-08-13, De CFO-metrieken verdelen zich over twee schermen, en de twee ontbindingen komen nooit naast elkaar

**Wat:** van de zeven metrieken landen bonritme, weekdagmix, weken, maandritme en afwijkende dagen op het Dagoverzicht, en concentratie en de prijs/volume-ontbinding op Productmix. De twee ontbindingen — klanten × mandje, en stuks × prijs — staan bewust op verschillende schermen.
**Waarom:** het zijn allebei ontbindingen van een omzetverschil, maar niet van hetzelfde getal: het bonritme ontbindt de verandering in omzet **per dag**, de prijs/volume-ontbinding de verandering **over het hele venster van dertig dagen**. Naast elkaar nodigen ze uit tot een optelling of een vergelijking die nergens op slaat. Beide toelichtingen zeggen daarom ook met zoveel woorden over welke grootheid ze gaan.
**Alternatief:** één "waarom bewoog de omzet"-scherm met beide ontbindingen. Verworpen om bovenstaande reden. Een tweede alternatief — de twee op dezelfde noemer brengen — is verworpen omdat de prijs/volume-ontbinding per open dag delen betekent, en dat is een cijfer dat de berekeningslaag niet meet.

---

### 2026-08-13, De weekdagmix toont alleen het aandeel, niet het gemiddelde

**Wat:** `weekdagmix` levert een gemiddelde per weekdag én een aandeel; het contract geeft alleen het aandeel door aan het scherm. Het gemiddelde per weekdag blijft komen van het bestaande weekdagprofiel, dat over kalenderweken middelt.
**Waarom:** de twee vensters verschillen — het profiel loopt over acht kalenderweken, de mix over de laatste 56 gemeten open dagen — dus hun zaterdaggemiddelde is niet hetzelfde getal. Twee verschillende gemiddelden voor dezelfde zaterdag op één scherm maakt ze allebei ongeloofwaardig, en de klant heeft geen manier om te weten welke van de twee de juiste is. De toelichting onder de mix benoemt het verschil in vensters expliciet.
**Alternatief:** het weekdagprofiel vervangen door de weekdagmix. Verworpen: de toelichting van het profiel verwijst naar de prognose en dat verband is met de backtest onderbouwd; dat opgeven voor een consistenter venster kost meer dan het oplevert.

---

### 2026-08-13, "Uit het assortiment" gaat als negatieve term het contract in

**Wat:** de invariant van `ontbinding_prijs_volume` trekt de post `verdwenen` af (volume + prijs + kruisterm + nieuw − verdwenen == verschil). Het contract levert die term daarom met een minteken, zodat de vijf termen op het scherm optellen tot het gemeten verschil.
**Waarom:** de contractlaag rekent de optelling na en weigert een ontbinding die niet uitkomt (`_ontbinding` werpt een `ValueError`). Zou de term positief doorgegeven worden, dan zou het scherm een lijstje tonen waarvan de som niet klopt met het totaal eronder — precies de fout die de sluitpost-beslissing van eerder vandaag wilde uitsluiten.
**Alternatief:** de term positief tonen met het woord "af" erbij. Verworpen: dan moet de lezer zelf het teken omkeren, en dat is rekenen door de lezer in plaats van door de berekeningslaag.

---

### 2026-08-13, De contractsleutel wordt in de presentatielaag naar een label vertaald (O12)

**Wat:** `onbeschikbaar[].veld` blijft in het contract een technische sleutel ("prognose.startpunt", "bonritme.ontbinding"). De omzetting naar een leesbaar label gebeurt in `platform/lib/toelichting.ts` (`veldLabel`), met drie stappen: exacte match, bekend voorvoegsel plus de staart uit de data, en anders een leesbaar gemaakte sleutel.
**Waarom:** de sleutel moet stabiel blijven — de app van fase 2 herkent hem, en hij overleeft een hertaling — maar hij hoort niet op een scherm: wie "prognose.startpunt" leest, leest een variabelenaam. De derde stap is er zodat een nieuwe reden uit de berekeningslaag altijd verschijnt, desnoods met een onhandig label; verzwijgen is erger dan onhandig.
**Alternatief:** een `label`-veld aan het contract toevoegen. Verworpen zoals eerder in `open-punten.md` vastgelegd: een label is tekst en geen cijfer, en het contract draagt cijfers.

---

### 2026-08-13, De censureringswachter slaat aan bij 8 procentpunt verschuiving over 90 meetdagen

**Wat:** `censureringsdrempel` vergelijkt het aandeel gewogen product-dagen met een leeg-reksignaal over de laatste 90 gemeten open dagen met dat over alles daarvóór (minstens 60 dagen), en meldt vanaf 8 procentpunt verschil. Er wordt geteld in meetdagen, nooit in kalenderdagen.
**Waarom:** over 529 open dagen staat het aandeel op 33,3%, en van alle 440 rollende vensters van 90 meetdagen week er geen enkel verder dan 3,7 procentpunt af. Acht is ruim twee keer die grootste natuurlijke uitschieter: geen enkel venster uit de gemeten historiek zou zijn afgegaan, terwijl een breuk die een kwart van het signaal verschuift (33% naar 25% of naar 41%) er meteen doorheen komt.
**Voorwaarden:** de referentie-uren worden één keer over het hele bereik berekend en pas daarna in twee periodes gesneden. Per periode meten laat de lat meeschuiven met precies de verandering die de wachter moet zien.
**Alternatief:** vensters van 60 meetdagen. Verworpen: daar loopt de natuurlijke drift op tot 5,2 procentpunt, en dan moet de drempel zo hoog dat er niets meer doorheen komt.

---

### 2026-08-13, De bonnenwachter toetst aanwezigheid van verkoopregels, niet omzet boven nul

**Wat:** `bonnen_omzetdekking` legt per dag de bonnentelling naast de kassaverkoop en toetst of er verkoopregels zijn, niet of de omzet boven nul ligt.
**Waarom:** de drempelregel `DREMPEL_OPEN` maakt een dag met verwaarloosbare omzet *dicht* en niet *leeg*. Op de gemeten data dragen 5 van de 54 gemeten gesloten dagen wél losse bonnen. Met een omzet-boven-nul-toets zou deze wachter permanent op rood staan — en dat is precies de fout die O14 beschrijft: een wachter die altijd alarm slaat, is op de dag van de echte storing onzichtbaar.
**Gevolg:** er wordt alleen getoetst binnen het bereik dat béide extracties dekken, zodat een achterlopende bonnenextractie het bereik verkort in plaats van alarm te slaan.
**Alternatief:** toetsen op omzet boven nul. Verworpen om bovenstaande reden.

---

### 2026-08-13, RLS staat in dezelfde migratie waarin de tabel ontstaat

**Wat:** elke tabel krijgt `enable row level security`, `force row level security`, een select-policy met expliciete `to authenticated`, en `revoke all ... from anon` in hetzelfde migratiebestand dat de tabel aanmaakt. Er zijn bewust geen insert-, update- of delete-policies.
**Waarom:** in Supabase hangt PostgREST aan de database, dus een tabel zonder RLS is leesbaar voor iedereen met de publiceerbare sleutel — en die sleutel staat per definitie in de JavaScript-bundel. RLS in een latere migratie is daarmee een venster waarin de omzet van de klant publiek staat. Schrijven doet alleen de ETL, via een rechtstreekse Postgres-verbinding die RLS omzeilt.
**Gevolg:** twee tests bewaken dit — één die eist dat elke aangemaakte tabel in hetzelfde bestand RLS krijgt, één die eist dat elke policy een expliciete `TO` draagt. Zonder `TO` geldt een policy namelijk ook voor anonieme bezoekers.
**Alternatief:** één aparte migratie die RLS over alle tabellen tegelijk zet. Verworpen om bovenstaande reden.

---

### 2026-08-13, Een kalenderkolom die niet gemeten wordt, blijft weg in plaats van leeg

**Wat:** `dim_kalender` draagt geen `schoolvakantie` en geen `evenement`, hoewel het canonieke datamodel in `CLAUDE.md` ze noemt. Ze komen erbij zodra de kalenderlaag ze levert.
**Waarom:** `schoolvakantie` hangt op vraag 47 — Franstalig, Nederlandstalig of beide, en in Elsene lopen die twee regimes niet gelijk. Voor `evenement` is er geen bron. Een kolom die er wél staat maar altijd leeg is, suggereert dat er gemeten is en dat er niets gevonden is; een kolom die er niet staat, zegt dat er niet gemeten is.
**Alternatief:** de kolommen alvast aanmaken en op null laten. Verworpen om bovenstaande reden — het is dezelfde regel die harde regel 8 op schermniveau stelt, hier toegepast op het schema.

---

### 2026-08-13, In `dim_product` wint de jongste productnaam

**Wat:** een product dat onder meerdere schrijfwijzen in de bron voorkomt, krijgt in `dim_product` de naam van de laatste datum waarop het verkocht is. Staan er twee namen op diezelfde laatste dag, dan wint de alfabetisch eerste.
**Waarom:** de naam hoort in de dimensie en niet in de feitrij. Een hernoeming in Odoo maakt er geen ander product van, en met de naam in elke feitrij zou zo'n hernoeming de historie in tweeën splitsen. De jongste naam is de naam die de bakker vandaag gebruikt, en het scherm toont het assortiment van vandaag. De alfabetische tiebreak bestaat alleen zodat de tabel niet afhangt van de rijvolgorde in het bronbestand.
**Alternatief:** de meest voorkomende naam, of simpelweg de eerste rij. Het eerste verandert bij elke nieuwe verkoop; het tweede maakt de uitkomst afhankelijk van de volgorde waarin de extractie toevallig schreef, en dan is de tabel niet reproduceerbaar.

---

### 2026-08-13, Wegschrijven gebeurt met COPY plus insert-on-conflict, nooit met truncate-en-insert

**Wat:** de laadlaag kopieert naar een tijdelijke tabel en voert daarna één `insert ... on conflict do update` uit, binnen dezelfde transactie. Alles of niets.
**Waarom:** bij truncate-en-insert bestaat er een moment waarop de tabel leeg is. Faalt de run daarna, dan staat het platform zonder cijfers. Met on-conflict blijft de oude inhoud staan tot de nieuwe eroverheen gaat. Rij voor rij invoegen valt af omdat 221.375 rijen met een netwerkrondgang per rij over een pooler-verbinding uren duren, en een run die halverwege sterft de tabel in een halve staat achterlaat.
**Alternatief:** truncate-en-insert, of schrijven via PostgREST. Het tweede kent geen COPY en geen transacties over meerdere statements.

---

### 2026-08-13, `*.sql` betekent datadump, behalve in `db/migraties/`

**Wat:** `.gitignore` negeert alle `.sql`-bestanden en `.claude/hooks/geen-klantdata.sh` blokkeert een commit die er een bevat, met precies één uitzondering: `db/migraties/*.sql`.
**Waarom:** de oorspronkelijke regel ving ook de migraties, en die waren daardoor onzichtbaar voor git. Zonder deze uitzondering zou de migratielaag gecommit zijn zónder haar migraties, en krijgt wie de repo daarna kloont een runner die op `FileNotFoundError` valt en een database die niemand meer kan herbouwen uit de bron — terwijl lokaal alles blijft werken.
**Gevolg:** een test draait `git check-ignore` op elke migratie. De uitzondering in de hook is bewust smal gehouden (`db/migraties/[^/]+\.sql`), en er is nagemeten dat een dump in `data/` nog steeds geblokkeerd wordt. Wie dit verbreedt naar `db/` of naar alle `.sql`, zet de vangrail uit.
**Alternatief:** de migraties een andere extensie geven, of ze in Python-code zetten. Het eerste maakt ze onleesbaar voor elk databasegereedschap, het tweede haalt ze uit de versiebeheerde SQL waar de projectregel juist om vraagt.

---

### 2026-08-13, Het agendaspoor krijgt zijn ophaallaag, maar geen van de keuzes die aan vraag 46 hangen

**Wat:** gebouwd zijn het ophalen, de configuratie (`AGENDA_ICS_URL`) en het netjes falen. Niet gebouwd zijn: de aansluiting op kalender, contract of scherm; één agenda tegenover meerdere; wat `ANDERE UREN`, `PROMO` en `EVENT` mogen doen; of de agenda de prognosehorizon mag opschuiven (O6); ophaalfrequentie en versheidsdrempel; alarmering bij een kapotte feed; en of een reden als "DICHT: begrafenis" op een scherm mag verschijnen.
**Waarom:** het ophalen is technisch en staat los van wat de klant kiest. Alles in de tweede lijst verandert wat het platform *beweert*, en dat is niet aan ons om in te vullen.
**Gevolg:** de laag blijft geïsoleerd — geen enkele module importeert haar, `make agenda` staat bewust niet in `alles`, en de opruimkost bij afwijzing blijft wat O16 belooft.
**Alternatief:** wachten met alles tot vraag 46 beantwoord is, of alvast een voorlopige invulling kiezen. Het eerste laat werk liggen dat hoe dan ook nodig is; het tweede is precies de aanname die harde regel 6 verbiedt.

---

### 2026-08-13, De Deliveroo-API is geen route naar de historiek, en blijft buiten fase 1

**Wat:** Deliveroo komt in fase 1 binnen via de CSV-rapporten uit Partner Hub (historiek) en de wekelijkse factuurmail (commissie). De Order API blijft eruit. Ze komt alleen in beeld als de klant expliciet dagverse, volautomatische Deliveroo-productcijfers eist, en dat is dan een eigen fase met eigen dagen.
**Waarom:** de Order API geeft niets terug dat ouder is dan dertig dagen — een vangnet voor gemiste webhook-events, geen archief. Vandaag aangesloten dekt hij ongeveer 14 juli tot nu, een maand die de CSV-export al heeft; het verlies zit aan het andere uiteinde. De payload bevat bovendien geen commissie en geen netto-uitbetaling, dus de marge per kanaal kan er niet uit komen. Toegang is op uitnodiging en gericht op kassaleveranciers, en webhooks vragen een publiek bereikbaar eindpunt terwijl de ETL bewust op GitHub Actions-cron draait om geen dienst te hoeven beheren.
**Voorwaarden:** dit berust op documentatieonderzoek van 12 augustus, niet op een test tegen een draaiende API — we hebben geen toegang. Vraag 48 legt de controlevraag bij de accountmanager.
**Gevolg:** deze beslissing stond tot vandaag alleen in `koppelingen.md` en niet hier, waardoor ze op 13 augustus heropend werd zonder dat de onderbouwing meekwam. Middleware (Deliverect, Flipdish, Lightspeed) verandert niets: die kunnen niet tonen wat de webhook niet bevat.
**Alternatief:** de API alsnog in fase 1 nemen. Verworpen: ze lost het enige urgente probleem niet op, ze vervangt geen enkele andere bron, en de deadline van 27 augustus telt elf werkdagen tegen een resterende raming van 14–19.

---

### 2026-08-13, Een product zonder naam blijft bestaan, met de ontbrekende naam als tekst

**Wat:** een `product_id` dat in het hele extract nergens een productnaam draagt, komt in `dim_product` te staan met de naam `(naam ontbreekt in de bron)`. Het verdwijnt niet uit de dimensie en zijn omzet blijft in `fact_verkoop`.
**Waarom:** gemeten op 13 augustus gaat het om vier product_id's, samen 28 rijen en € 400,91 — 0,006% van de omzet, alle vier in januari 2025 en alleen in het kanaal winkel. Zouden ze uit `dim_product` vallen, dan moet hun omzet uit `fact_verkoop` geschrapt worden om de refereert-naar-beperking te halen, en dan sluiten de kanaaltotalen niet meer aan op de bron. Een verschil van vierhonderd euro dat niemand kan verklaren kost meer vertrouwen dan een product dat eerlijk zegt dat zijn naam ontbreekt.
**Gevolg:** `dim_product` gaat van 327 naar 331 rijen. De tekst is voor een lezer geschreven en niet voor een ontwikkelaar; een test bewaakt dat er geen `None`, `NaN` of `UNKNOWN` op een scherm belandt.
**Alternatief:** de rijen laten vallen, of de naam op de `product_id` zetten. Het eerste is stilzwijgend omzet weggooien; het tweede zet een technische sleutel op het scherm en dat is precies wat O12 heeft uitgeroeid.

---

### 2026-08-13, Twee verkoopregels met dezelfde sleutel worden opgeteld, en het aantal wordt gemeld

**Wat:** vindt de laadlaag meerdere rijen met dezelfde `datum`, `kanaal`, `filiaal_id` en `product_id`, dan telt ze `aantal` en `omzet_excl_btw` bij elkaar op. Het aantal samengevallen rijen wordt geprint.
**Waarom:** `insert ... on conflict do update` kan een rij niet twee keer in hetzelfde statement raken — Postgres werpt daarop en de laadrun valt om. Zou je dat omzeilen door per rij te schrijven, dan wint stilzwijgend de laatste en is de omzet van de andere weg. Optellen is bovendien de juiste behandeling en geen keuze uit gemak: twee rijen met dezelfde sleutel zijn twee stukken van dezelfde verkoop, geen tegenstrijdige metingen.
**Voorwaarden:** dit geldt niet voor `fact_product_uren`. Een uur optellen is onzin, dus daar is een dubbele sleutel een bronfout die luidruchtig hoort te falen op de primaire sleutel.
**Alternatief:** stilzwijgend ontdubbelen, of de laatste laten winnen. Het eerste is precies zo erg als het probleem — een tabel die minder rijen bevat dan de bron, zonder dat iemand weet hoeveel.

---

### 2026-08-13, Marges worden een add-on buiten fase 1 — met terugwerkende kracht vastgelegd

**Wat:** het margescherm blijft in fase 1 in de onbeschikbaar-staat, met de reden erbij. Stap S6 (brutomarges als losstaande opdracht) uit het plan is vervallen. Vraag 19 is herschreven van "kostprijs per product" naar "brutomarge per productgroep", aan te leveren door de bakker.
**Waarom:** gemeten dat van de 425 producten er 3 een kostprijs dragen, en dat Odoo de kostprijs op alle 1.556.770 kassabonregels berekende en 1.556.054 keer op nul uitkwam — de data ontbreekt niet toevallig, ze bestaat niet. Tien categorieën dekken wel 95% van de omzet, dus een invulbaar lijstje van groepsmarges is haalbaar waar een kostprijs per artikel dat niet is.
**Gevolg:** deze beslissing stond tot vandaag alleen in `docs/todo.md` en `docs/vragen-aan-lien.md`, niet hier — hetzelfde patroon waardoor de Deliveroo-beslissing op 13 augustus heropend werd. Ze wordt hierbij deels herzien, zie het volgende blok.
**Alternatief:** wachten tot de eindklant per product een kostprijs aanlevert. Verworpen: die data bestaat niet in Odoo en is met een dataverzoek niet op te lossen.

---

### 2026-08-13, Het margescherm vult zich toch, via handmatige invoer per productgroep

**Wat:** een gebruiker met rol `beheerder` vult op Instellingen per productgroep een brutomarge in. Dat herziet de eindtoestand "blijvend leeg" van de beslissing hierboven: het scherm toont voortaan een gewogen marge zodra er invoer is. De invoer leeft in `data/config/marges.json`, buiten git, en niet in de database.
**Waarom:** de data bestaat niet in de bronsystemen, maar de bakker kan een brutomarge per groep wél zelf aanleveren — een halfuur werk, geen kostprijscalculatie per artikel. Een bestand in plaats van meteen een databasetabel houdt de invoer, net als de rest van de berekeningslaag, los van poort G7 (de gehoste database).
**Gevolg:** migratie 004 (`marge_instelling`) legt de databasevorm nu al vast, met dezelfde RLS-regels als de rest van het schema (eigen select-policy, geen insert/update/delete-policy, schrijven via de directe verbinding), zodat het bestand bij S2 1-op-1 overgenomen kan worden zonder de vorm te wijzigen.
**Alternatief:** wachten tot de database er is en dan pas een invoerscherm bouwen. Verworpen: de invoer hoeft niet op S2 te wachten, net zomin als de rest van de berekeningslaag dat doet.

---

### 2026-08-13, De gewogen brutomarge telt alleen mee waar een marge is ingevuld

**Wat:** de gewogen brutomarge op het margescherm rekent uitsluitend over productgroepen met een ingevulde marge. Groepen zonder invoer tellen niet mee in het gewogen percentage; ze verschijnen in `onbeschikbaar` met hun aandeel in de winkelomzet, met naam en al.
**Waarom:** een groep zonder invoer aanvullen met 0% zou het gewogen cijfer kunstmatig omlaag halen, en aanvullen met een aanname (bijvoorbeeld de mediaan van de andere groepen) zou een marge tonen die niemand heeft aangeleverd. Harde regel 8 verbiedt beide: een geblokkeerd cijfer wordt getoond als onbeschikbaar, niet geschat.
**Alternatief:** de ontbrekende groepen invullen met 0% of met een aanname zodat het percentage altijd over de volle omzet gaat. Verworpen om bovenstaande reden.

---

### 2026-08-13, TGTG krijgt geen winkelmarge op het margescherm

**Wat:** de ingevulde groepsmarges op het margescherm gelden alleen voor winkelomzet. Too Good To Go krijgt geen winkelmarge toegepast; de reden staat in het contract als `marge.tgtg`.
**Waarom:** TGTG verkoopt hetzelfde assortiment tegen restprijs, niet tegen winkelprijs, en de canonieke TGTG-omzet is al netto van de TGTG-commissie. Een winkelmarge daarop loslaten zou winst tonen die er niet is.
**Alternatief:** dezelfde groepsmarge op alle kanalen toepassen. Verworpen om bovenstaande reden; de kanaalkost van TGTG staat apart op het scherm Verkoopkanalen.

---

### 2026-08-13, De periodekubus vergelijkt op het gemiddelde per gemeten open dag, niet op totalen

**Wat:** de vier voorgebakken vensters van de periodekubus (30 dagen, 13 weken, 12 maanden, dit jaar) vergelijken met de vorige periode op het gemiddelde per gemeten open dag, niet op de strikte regel "alleen vergelijken bij gelijk aantal open dagen" die elders geldt (Venster-machinerie, productverschuiving, bonritme). Beide aantallen gemeten open dagen staan in het vergelijkingslabel.
**Waarom:** een week, maand of jaar telt vrijwel nooit exact evenveel open dagen als de vorige — de strikte regel zou hier neerkomen op "vrijwel nooit een vergelijking". Op totalen vergelijken zou daarentegen liegen bij sluitingen: een venster met minder open dagen zou als daling ogen die er niet is.
**Alternatief:** de strikte gelijke-dagenregel doortrekken naar de periodekubus. Verworpen: dat levert op dit schaalniveau vrijwel nooit een vergelijking op. Tweede alternatief — vergelijken op totalen — verworpen omdat dat een sluitingsperiode als vraaguitval toont.

---

### 2026-08-13, Het CFO-rapport wordt vooraf gebouwd, niet on-the-fly geserveerd

> **HERROEPEN op 18 augustus 2026.** Zie "Het CFO-rapport is een weergave geworden" onderaan dit document. De twee gebreken die dit ontwerp had, waren met opmaak niet te verhelpen: het bestand kon ouder zijn dan de cijfers op het scherm, en het was een tweede tekenlaag van hetzelfde document.

**Wat:** het PDF-rapport komt tot stand via `make rapport-pdf` (onderdeel van `make alles`), gebouwd door de Python-berekeningslaag uit dezelfde contractantwoorden als de UI. Het platform serveert het bestand alleen van schijf (`/rapport`, achter de login); Next bouwt niets bij het verzoek zelf.
**Waarom:** het rapport is een contractconsument zoals de UI (harde regel 4) en hoort dus niet zelf te rekenen. De Python-laag heeft de huisstijl-SVG's en de contractlogica al, en de nachtelijke run kan het rapport straks meebouwen zonder extra infrastructuur.
**Alternatief:** het rapport bij elk verzoek in Node renderen. Verworpen: dat verplaatst rekenwerk naar de presentatielaag en dupliceert de opmaaklogica die in Python al bestaat.

---

### 2026-08-13, WeasyPrint als PDF-renderer, met een systeemafhankelijkheid

> **HERROEPEN op 18 augustus 2026**, op precies de grond die deze beslissing zelf als herroepingsvoorwaarde noteerde: "herroepbaar zodra de systeemafhankelijkheid ergens hindert (bijvoorbeeld op een CI- of hostingplatform zonder Homebrew)". Het platform draait op Vercel, en daar is geen pango. WeasyPrint is uit `requirements.txt` verdwenen.

**Wat:** het rapport wordt gerenderd met WeasyPrint (BSD, HTML/CSS naar PDF). Dat vraagt pango via Homebrew en `DYLD_FALLBACK_LIBRARY_PATH` in het make-doel. `bouw_html` blijft een pure functie; alleen `schrijf_pdf` raakt WeasyPrint aan, zodat de 8 tests geen pango nodig hebben.
**Waarom:** WeasyPrint hergebruikt de bestaande HTML/CSS-aanpak en de huisstijl-SVG's rechtstreeks. Het alternatief, reportlab, heeft geen systeemafhankelijkheden maar vraagt handmatige layout — elke tegel, kolom en pagina-afbreking opnieuw in code, in plaats van in CSS.
**Alternatief:** reportlab. Verworpen om bovenstaande reden; herroepbaar zodra de systeemafhankelijkheid ergens hindert (bijvoorbeeld op een CI- of hostingplatform zonder Homebrew).

---

### 2026-08-13, De prognoseband wordt gekalibreerd op gemeten dekking, niet op de nominale kwantielnaam

**Wat:** `rolling.kalibreer_kwantielen` kiest uit een oplopende reeks kandidaten (10-90, 7,5-92,5, 5-95, 2,5-97,5) de smalste band waarvan de out-of-sample gemeten dekking minstens doel min tolerantie haalt (doel 80%, tolerantie 5 procentpunt). Gekozen: 7,5-92,5, gemeten 69 tot 82% per horizonstap. Het contract benoemt kwantielen, doel én gemeten dekking naast elkaar.
**Waarom:** de meting van 13 augustus toonde dat een 10-90-band uit de eigen trainingsresiduen out-of-sample maar 56 tot 74% dekte waar 80% beloofd werd. De naam van een kwantiel is geen belofte over dekking; de meting wel.
**Alternatief:** de 10-90-band houden en de te lage dekking alleen benoemen — dat was de stand tot vandaag. Of de band met een vaste factor oprekken tot de dekking uitkomt. Beide verworpen: het eerste toont een cijfer waarvan al bekend is dat het niet klopt, het tweede verzint een verdeling in plaats van haar te meten.

---

### 2026-08-13, De som van categorieprognoses vervangt de directe dagprognose niet

**Wat:** de prognose per categorie (zes plus een restgroep, elk met eigen gemeten WAPE en band) blijft een apart, uitklapbaar onderdeel van het Prognosescherm. De categorieën tellen niet op tot het dagtotaal; de dagprognose blijft rechtstreeks berekend.
**Waarom:** de som van de categorieën is als tweede kandidaat voor de dagprognose door hetzelfde harnas gehaald: 7,74% WAPE tegen 8,17% voor de directe dagprognose, 0,42 punt beter — onder de vooraf gestelde lat van 0,5 punt om een model te vervangen. Consistentie ("de categorieën tellen op tot het totaal") verliest het van die latdiscipline.
**Alternatief:** de som toch aannemen omdat optellende categorieën prettiger ogen dan twee cijfers die niet overeenkomen. Verworpen: harde regel 7 en de eigen vergelijkingslat gelden ongeacht hoe het oogt.

---

### 2026-08-13, De schoolvakantiecorrectie draait op het Franstalige regime, ondanks een totaallat die niet gehaald is

**Wat:** de productievoorspeller krijgt een schoolvakantiecorrectie op het Franstalige regime (`met_feestdagcorrectie` met kenmerk `schoolvakantie`, kalender uit `SCHOOLVAKANTIES_FR`). Dit is een empirisch antwoord op O10/vraag 47: van de twee regimes verklaart het Franstalige het koopgedrag van deze bakkerij (Elsene) het best.
**Waarom:** op het totaal haalt de correctie +0,41 punt WAPE, onder de vooraf gestelde lat van 0,5 punt. Maar het harnas rekent een kenmerk dat een deelvenster raakt bewust op dat deelvenster af (`rolling.evalueer`, `alleen_dagen`) — dezelfde regel waarmee de feestdagcorrectie destijds op de geraakte dagen is afgerekend en afgewezen. Op de 86 geraakte vakantiedagen wint het Franstalige regime ruim (7,8% naar 6,0% WAPE) en verliest het nergens. Het Vlaamse regime is even goed gemeten en afgewezen: +0,19 punt totaal, 9,5% naar 8,6% op de geraakte dagen — een kleinere en minder eenduidige winst.
**Alternatief:** strikt de totaallat van 0,5 punt volgen en de correctie afwijzen. Verworpen: die lat is gemaakt om een kenmerk te beoordelen op wat het zou moeten raken, en op dát venster wint de correctie zonder voorbehoud.

---

### 2026-08-13, Beide schoolvakantieregimes staan als publieke, geverifieerde data in de kalenderlaag

**Wat:** `features/calendar.py` draagt zowel `SCHOOLVAKANTIES_VL` als `SCHOOLVAKANTIES_FR` als vaste, dichtgetimmerde datareeksen (bronnen: Vlaanderen.be-afgeleiden, RTBF en enseignement.be voor de FWB). De randdatums staan als aanname A20 in `docs/aannames.md`.
**Waarom:** sinds de hervorming van 2022 lopen de twee gemeenschappen niet meer gelijk, en welk regime het koopgedrag stuurt was tot vandaag onbeantwoord (O10). Zonder beide regimes in de code was er niets om te meten, en de meting is precies wat de vorige twee beslissingen onderbouwt.
**Alternatief:** wachten met beide regimes tot vraag 47 door de opdrachtgever beantwoord is. Verworpen: de data is publiek en controleerbaar, en de meting zelf is nu het sterkste antwoord op de vraag — bevestiging door Lien blijft niettemin gewenst.

---

### 2026-08-13, De canoniekbouw blijft offline: de agenda komt uit een bestand, nooit uit een netwerkcall

**Wat:** `scripts/canoniek_bouw.py` leest een al opgehaalde `data/raw/agenda.ics`, geschreven door `make agenda`. De nachtelijke canoniekbouw zelf doet geen netwerkcall. Zonder dat bestand verandert er niets aan de kalender.
**Waarom:** het ophalen van een externe iCal-feed kan haperen — trage server, verlopen link, lege respons. Zit die aanroep in de nachtelijke keten, dan legt zo'n hapering de hele bouw om en wordt de bouw niet-deterministisch: dezelfde bron kan de ene nacht wel en de andere nacht niet lukken.
**Alternatief:** de agenda rechtstreeks ophalen binnen `canoniek_bouw`. Verworpen: minder stappen, maar het netwerk als afhankelijkheid in een keten die met één commando herbouwbaar moet zijn (`CLAUDE.md`, laag 2-3).

---

### 2026-08-13, Het agenda-afwijkingsrapport draagt datums en soorten, nooit de redenen uit de agenda

**Wat:** `reports/agenda-afwijkingen.md` toont per afwijkende dag de datum, of de dag gemeten open was en of hij gepland dicht stond, en het soort agendaregel (`DICHT`, `ANDERE UREN`, ...). De vrije tekst achter zo'n titel — de reden — komt er niet in.
**Waarom:** een reden in een agenda kan een persoonlijk gegeven zijn, bijvoorbeeld "DICHT: begrafenis". Wie de reden nodig heeft, draait `scripts/agenda_ophalen.py --detail` bewust en lokaal; het rapport zelf is bedoeld om te delen.
**Alternatief:** de redenen mee opnemen. Verworpen: dat is leesbaarder, maar een rapport wordt gedeeld en een agenda-regel is daar niet voor bedoeld.

---

### 2026-08-14, De marge-invoer wordt een kostenmodel, niet langer één brutomarge-veld

**Wat:** op Instellingen stelt de beheerder zelf kostencriteria samen (toevoegen, hernoemen, verwijderen, ten hoogste 12) en vult per productgroep per criterium een percentage van de omzet in. De brutomarge van een groep is 100 min de som van haar ingevulde criteria; een groep telt al als "gedekt" zodra minstens één criterium is ingevuld, niet pas wanneer alle criteria staan. Loopt de som boven 100, dan wordt de resulterende negatieve marge getoond met een waarschuwing, niet geweigerd. Deze beslissing herziet de brutomarge-invoer van 13 augustus ("Het margescherm vult zich toch, via handmatige invoer per productgroep"); de regel dat een ongedekte groep niet meetelt in het gewogen percentage blijft ongewijzigd staan, alleen wat "gedekt" betekent is nu ruimer.
**Waarom:** een direct brutomarge-veld liet geen opbouw en geen criteria-beheer toe, terwijl de zaakvoerder in foodcost-termen denkt (grondstoffen, verlies en verspilling, basisingrediënten) en dat per groep wil kunnen bijstellen. "Gedekt bij ≥1 criterium" is de enige leesbare semantiek: het alternatief — pas tonen bij "volledige" invoer — vraagt een definitie van volledig die niemand heeft (zie aanname A21). Een half ingevuld beeld toont daarmee een marge die aan de hoge kant kan liggen, omdat ontbrekende kostenposten haar nog niet drukken.
**Gevolg:** eerder ingevulde v1-marges (`data/config/marges.json`) blijven leesbaar als één criterium "Totale kost" (100 − marge) zodra er geen v2-bestand is; dat is een herschrijving van dezelfde invoer, bewust geen nieuw cijfer. Migratie 005 legt de databasevorm al vast (`kosten_criterium`, `kosten_waarde`).
**Alternatief:** het directe brutomarge-veld houden — eenvoudiger, maar zonder opbouw en zonder criteria-beheer door de klant. Tweede alternatief, marge pas tonen bij "volledige" invoer, verworpen omdat niemand "volledig" kan definiëren.

---

### 2026-08-14, Winkels worden een instelling, niet een aanname in de code

**Wat:** `data/config/winkels.json` wijst filialen toe aan winkels. Is er een indeling, dan schrijft de contractbouw naast het totaal een eigen contractmap per winkel, elk met een eigen gebackteste prognose. Een winkel met minder dan 187 gemeten open dagen (het bestaande `MIN_TRAIN` van 180 plus de horizon van 7) krijgt geen prognose, maar een reden. Zonder bestand verandert er niets: alles telt als één geheel, zoals vandaag.
**Waarom:** `filiaal_id` bestaat al sinds dag één in het canonieke model, maar vraag 18 (registers of vestigingen) staat nog open. Een configbestand houdt die vraag open terwijl het platform toch al schaalt: komt er een tweede vestiging, dan is dat één configregel in plaats van een verbouwing. Harde regel 7 verbiedt een voorspelling zonder backtest, dus een winkel met te weinig historiek krijgt eerlijk geen cijfer in plaats van een gegokt cijfer.
**Alternatief:** de winkel als queryparameter in één contract. Verworpen: het contract is voorgebakken JSON per harde regel 4, geen live query. Tweede alternatief, wachten tot er een tweede vestiging echt bestaat, verworpen: dan is het een verbouwing in plaats van een configregel.

---

### 2026-08-14, Schermen lezen het contract per verzoek van schijf, niet als statische import

**Wat:** `platform/lib/laadContract.ts` leest elk contractantwoord per verzoek van schijf in plaats van als statische import in de bundel. De winkelkeuze leeft in een cookie, maar die wordt nooit als bestandspad vertrouwd: alleen een slug die in de door de contractbouw geschreven winkelindex staat, wordt een mapnaam. Staat een winkel wél in die index maar is haar contractbestand onleesbaar, dan is dat een harde fout met melding, geen stille terugval op het totaal.
**Waarom:** een statisch geïmporteerde contract zit in de build; na "invoer opslaan → contract herrekend" bleef een productiebuild het oude antwoord tonen. Van schijf lezen maakt het scherm zo vers als het laatst gebouwde contract. Een cookie als vertrouwd pad zou een gebruiker toelaten een willekeurige mapnaam te kiezen; een stille terugval bij een kapot winkelbestand zou de cijfers van het hele geheel tonen onder de naam van één winkel, en dat is een fout die niemand zou opmerken.
**Alternatief:** de statische import houden en na elke opslag de hele applicatie herbouwen. Verworpen: te traag voor een opslagactie die meteen effect moet tonen.

---

### 2026-08-14, Sessies worden per verzoek hertoetst, en de login krijgt een pogingenslot

**Wat:** `platform/lib/auth.ts` toetst bij elk verzoek de rol en het bestaan van de gebruiker opnieuw tegen de omgevingsvariabele `PLATFORM_GEBRUIKERS`; de cookie draagt alleen de identiteit, de omgeving is de waarheid voor wie er nog mag zijn en met welke rol. Een geschrapte gebruiker of ingetrokken beheerdersrol werkt meteen, niet pas na twaalf uur wanneer de cookie verloopt. Daarnaast krijgt de login een pogingenslot: vijf mislukte pogingen op één gebruikersnaam sluiten die naam een minuut af, bijgehouden in het geheugen van het proces en niet per IP.
**Waarom:** de sessie-cookie is twaalf uur geldig; zonder hertoetsing zou een ingetrokken toegang een halve werkdag blijven werken. Het slot zit op de naam en niet op het IP omdat dit platform een handvol bekende gebruikers heeft; een aanvaller die IP's roteert, botst bij naamgebonden vergrendeling per naam opnieuw op het slot.
**Alternatief:** een sessielijst in een database om sessies expliciet te kunnen intrekken. Niet verworpen maar uitgesteld: dat komt gratis mee zodra S2/Supabase Auth er is, en tot dan dicht de hertoetsing het praktische gat.

---

### 2026-08-14, Alle schrijvers van gedeelde bestanden schrijven atomair, en opslag krijgt een herrekeningslock

**Wat:** elke schrijver van een bestand dat meerdere processen kunnen lezen — de contract-JSON's, de canonieke CSV's uit `scripts/canoniek_bouw.py`, en de configbestanden (`kostenmodel.json`, `winkels.json`) — schrijft eerst naar een tijdelijk bestand en hernoemt dat pas (tmp + rename/`os.replace`). De opslagactie op Instellingen laat bovendien maar één herrekening tegelijk toe; een tweede opslag terwijl er al een contractbouw loopt, wacht af in plaats van tegelijk te schrijven. `scripts/db_laad.py` doet één commit na alle tabellen in plaats van één per tabel, met een `rollback()` vóór de foutregistratie zodat de foutmelding zelf niet ook omvalt in een afgebroken transactie.
**Waarom:** een niet-atomaire schrijfactie laat een venster open waarin een lezer (de contractbouw, een scherm, een volgende run) een halfgeschreven bestand ziet. Zonder de lock zouden twee gelijktijdige opslagacties door elkaar in `platform/contract/` schrijven. Zonder de late commit liet een tabel die halverwege omviel de database in een halve staat achter.
**Alternatief:** rechtstreeks naar het doelbestand schrijven en gelijktijdigheid negeren. Verworpen: het risico is klein per keer maar de schade — een halve JSON die een scherm laat crashen, of een halve database-lading — is groot genoeg om de paar regels code niet te laten liggen.

---

### 2026-08-14, Lange toelichting klapt uit, de kop en het aantal blijven altijd zichtbaar

**Wat:** het "Wat hier niet staat, en waarom"-blok (`Toelichting.tsx`) toont de titel en het aantal voorbehouden altijd, ook dichtgeklapt; de volle tekst per regel zit in een native `<details>`-uitklap. Langere methodetoelichting elders krijgt dezelfde behandeling via een nieuwe `MeerInfo.tsx`-component.
**Waarom:** wie het blok elke dag leest, kent de tekst al; wie hem nodig heeft, is één klik verwijderd. Harde regel 8 gaat over wát ontbreekt, niet over hoeveel tekst daarover op het scherm staat — zolang het aantal voorbehouden zichtbaar blijft zonder klik, blijft de regel onverkort overeind. Native `<details>` werkt zonder JavaScript en zonder een bewaarde open/dicht-staat.
**Alternatief:** de volle toelichting altijd tonen, zoals tot nu toe. Verworpen: bij meerdere regels per scherm werd het blok een muur tekst die de kerncijfers verdrong.

---

### 2026-08-14, Weer blijft gepauzeerd, geen weerfactor in het model

**Wat:** het model krijgt geen weerfactor.
**Waarom:** de kalender absorbeert het gemiddelde weereffect al (een warme juli zit al in het weekdag- en maandpatroon). Wat weer daarbovenop zou toevoegen, is alleen de afwijking van de seizoensnorm, en eerlijk backtesten daarvoor vergt historische weersverwáchtingen, niet gemeten weer — gemeten weer is achteraf bekend en zou de backtest flatteren met kennis die een echte prognose nooit had.
**Voorwaarden:** heropening alleen via een residuen-meting op eigen data, en niet vóór fase 2.
**Alternatief:** meteen Open-Meteo-data in het model opnemen. Verworpen om bovenstaande reden.

---

### 2026-08-14, De schoolvakantiekalender wordt verversbaar, niet zelfwijzigend

**Wat:** schoolvakanties verhuizen van hardgecodeerde tabellen in `calendar.py` naar data met bron en ophaaldatum, nachtelijk ververst via de OpenHolidays-API. Nieuwe, toekomstige periodes worden automatisch overgenomen en gelogd; wijzigingen aan periodes binnen het al gemeten historische venster worden nooit stil doorgevoerd. Reikt de kalenderdekking niet tot het einde van de prognosehorizon, dan meldt de prognose zich daar als beperkt betrouwbaar in plaats van die dagen stil als gewone dagen te behandelen (harde regel 8). Feestdagen blijven algoritmisch (holidays-pakket), evenementen blijven klantbeheerd.
**Waarom:** de huidige tabellen eindigen op 31 augustus 2026 — de herfstvakantie 2026 ontbreekt — en de productieprognose draait mét vakantiecorrectie. Zonder ingreep behandelt de prognose vanaf eind oktober vakantiedagen stil als gewone dagen.
**Alternatief:** ook wijzigingen in het historische venster automatisch overnemen zodra de bron ze meldt. Verworpen: dat verandert stilzwijgend trainingskenmerken en het trackrecord van een model dat al gebackt is op de oude indeling.

---

### 2026-08-14, Scenario's op de prognose mogen alleen kalenderinvoer wisselen, nooit geleerde factoren

**Wat:** een scenario zoals "toon deze week als vakantieweek" wisselt alleen de kalenderinvoer van hetzelfde gebackteste mechanisme. Varianten worden vooraf berekend in de contractbouw; de UI wisselt enkel tussen aangeleverde getallen (harde regel 4). Vrije schuiven — "prijs +5%", een feestdagfactor met de hand op 1,5 — zijn afgewezen.
**Waarom:** zonder gebackteste elasticiteit is een vrije schuif een mening op een scherm dat vertrouwen moet verdienen (harde regel 7).
**Voorwaarden:** bouwen wacht op vraag 55 aan Lien. Voorbereiden mag, tonen niet.
**Alternatief:** vrije scenario-schuiven zoals de externe audit voorstelde. Verworpen om bovenstaande reden.

---

### 2026-08-14, De briefing bovenaan elk scherm is signalering, geen productie-advies

**Wat:** elk scherm krijgt bovenaan een briefing: per punt wat opvalt, waarom, en wat er nodig is van wie, met een bedrag alléén als de berekeningslaag het staaft. Statuschips dragen hun betekenis in het woord, niet in kleur (huisstijl: kleur draagt nooit betekenis).
**Waarom:** concreet productie-advies ("plan maandag lager") is de beslislaag die op 12 augustus uit fase 1 is geschrapt. Die grens blijft staan tot vraag 56 beantwoord is.
**Alternatief:** verder gaan naar concrete productie-indicaties per categorie, zoals de externe audit aanraadt. Voor fase 1 verworpen om bovenstaande reden.

---

### 2026-08-14, De externe audit wordt gelezen met een Renard-only-regel

**Wat:** alle aanbevelingen uit de externe audit (GPT 5.5, 14 aug) die veronderstellen dat dit een product voor meerdere bakkerijgroepen wordt — demo-modus, salesverhaal, multi-tenant — zijn genegeerd. De 404 op `/winkels` is bevestigd als ontwerp, geen gebrek: de winkelkiezer verschijnt pas zodra er twee winkels geconfigureerd zijn.
**Waarom:** dit platform is voor Renard alleen. Multi-tenant-infrastructuur bouwen voor een klant die er niet is, is scope die niemand gevraagd heeft.
**Alternatief:** de audit-aanbevelingen overnemen om het platform generiek herbruikbaar te maken. Verworpen: buiten `docs/scope.md`, en niet gevraagd door de opdrachtgever.

---

### 2026-08-14, De heropeningscorrectie na een schoolvakantie is geadopteerd, twee alternatieven zijn gemeten en afgewezen

**Wat:** de productievoorspeller krijgt een extra kenmerk "heropening" — de eerste 3 open dagen na het einde van een FR-schoolvakantie — bovenop de bestaande schoolvakantiecorrectie in `met_feestdagcorrectie`. De vlaglogica (`overgangsdagen`, `bakkerij/features/calendar.py`) staat op één plek, gedeeld door productie, contractbouw en het meetscript.
**Waarom:** de WAPE-diagnose (blok 23, ronde 1) vond de zwakste plek van het model: de eerste 3 open dagen na een FR-vakantie zaten op 21,0% WAPE met een structurele bias van −2.823 €/dag, omdat het 14-daagse niveauvenster het vakantieregime mee de heropening in sleept. Met de correctie: heropeningsdagen (n=15) 21,0% → 18,5% (+2,45 punt), bias −2.823 → −2.448; totaal (n=343) 7,8% → 7,6%; geen enkel ander deelvenster geschaad (vakantiedagen ±0,00, januari −0,01). De band is herkalibreerd, dekking nu 74,4–84,6% op doel 80%. Het adoptiecriterium was het E4-precedent: het deelvenster duidelijk winnen zonder elders meer dan 0,05 punt te schaden.
**Gevolg:** de methodenaam op het scherm wordt "weekdagmediaan, geschaald naar het niveau van de laatste twee weken, met schoolvakantie- en heropeningscorrectie (Franstalig regime)".
**Alternatief:** variant B, een vakantiebewust niveauvenster (niveaufactor uit de jongste 14 open dagen met dezelfde vakantiestatus als de doeldag), won de heropeningsdagen even goed (18,6%) maar brak de vakantiedagen zelf (6,0% → 10,7%, −4,68 punt) en het totaal (−0,63 punt): het per-status-venster maakt het niveau bínnen de vakantie verouderd en ruizig. Variant C, een galette-seizoensfactor voor 1–15 januari geleerd op januari 2025 en getoetst op januari 2026, verslechterde zowel heel januari (17,2% → 18,4%) als de eerste helft (21,2% → 23,6%, bias klapt om van −2.738 naar +559) en miste de piekdag van 6 januari 2026 (voorspelling 14.448 tegen werkelijk ~30.800). Bevinding: het galette-effect is één à twee specifieke dagen, geen 15-daags regime — op te lossen via de agenda-feed (vraag 46) of een tweede januari in de historiek. Beide varianten zijn verworpen, variant A is geadopteerd.

---

### 2026-08-14 (avond), Aangekondigde sluitingen sturen het prognosevenster, uit een configlijst en niet uit de agenda

**Wat:** `canoniek.prognosevenster` slaat vanaf nu ook dagen over die vooraf als gesloten zijn aangekondigd, niet alleen dagen die gemeten én gesloten zijn. De bron is een nieuwe configlijst, `data/config/sluitingsdagen.json`, ingelezen door `bakkerij/sluitingsdagen.py` en verwerkt in de canoniekbouw.

**Waarom:** het scherm zette een omzetverwachting op de week van 17 augustus, waarin de zaak dicht is. De oorzaak was niet dat het ontwerp ontbrak maar dat niemand ernaar keek: de kolom `gepland_dicht` bestaat al sinds blok 17 (`sources/agenda.py`), en de horizonregel las alleen `winkel_gemeten AND NOT winkel_open` — een toekomstige dag is per definitie niet gemeten, dus die zeef kon een aangekondigde sluiting nooit vangen. Dat is het soort fout dat een test niet vindt zolang niemand een toekomstige sluiting invoert.

**Waarom een configlijst en niet wachten op de agenda:** de iCal-route is de nettere bron — de bakkerij houdt haar eigen agenda bij, wij lezen mee — maar die wacht op vraag 46 en dat venster is al weken open. Een lijst die wij of de beheerder bijhoudt, wacht op niemand. Beide bronnen vullen bewust **dezelfde kolom met dezelfde reden**, dus er is één begrip "gepland dicht" met twee bronnen en niet twee soorten sluiting; wie later de agenda aansluit, verandert niets aan de prognose. Bij overlap gaat de reden uit de agenda voor: die komt van de bakkerij zelf.

**Wat expliciet niet verandert:** de meting blijft de waarheid. Voor een dag die gemeten is en open bleek, is de kassa de bron — ook als er een sluiting voor aangekondigd stond. Die tegenspraak wordt gerapporteerd (`sluitingsdagen.afwijkingen`, net als bij de agenda) en niet stil opgelost. En buiten de lijst blijft niets-weten geen sluiting: die dagen gaan mee als gewone dagen, met op het scherm de mededeling tot waar de lijst reikt. Aanname `prognose.sluitingsdagen` is daarmee niet verdwenen maar verschoven, en de tekst op het scherm volgt nu wat er werkelijk bekend is in plaats van wat er in augustus 2026 waar was.

**Alternatief:** de gesloten dagen tonen als nul of als lege staaf in de grafiek. Verworpen: een nul suggereert een verwachte omzet van nul euro, en dat is niet wat er aan de hand is (harde regel 8). Het venster schuift door naar de eerstvolgende open dagen, met de reden en de sluitingsnaam erbij.

---

### 2026-08-14 (avond), Het platform is tweetalig via een cookie, en het contract wordt twee keer gebouwd

**Wat:** NL/FR, met een taalknop vast linksonder op elk scherm inclusief het aanmeldscherm. De keuze leeft in een cookie (`renard_taal`); het contract wordt per taal gebouwd — `platform/contract/` blijft Nederlands, `platform/contract/fr/` is Frans — en de UI leest de map die bij de gekozen taal hoort.

**Waarom het contract en niet alleen de UI:** elk label dat een mens leest, komt uit de berekeningslaag (harde regel 4, en `lib/contract.ts` zegt het expliciet). Een Franse gebruiker die "Verwachte omzet" op zijn as ziet, kijkt naar een label dat de berekening heeft gemaakt; de UI kan dat niet vertalen zonder zelf tekst te gaan verzinnen. Twee contractmappen is wat een echte API met `Accept-Language` ook zou doen: dezelfde cijfers, andere labels. Getoetst: de cijfers zijn per constructie identiek, alleen de tekst verschilt.

**Waarom een cookie en geen `/fr/`-pad:** de Next-gids raadt een taalpad aan, en voor een publieke site is dat juist — zoekmachines moeten elke taal als eigen adres kunnen indexeren. Dit is een afgeschermd dashboard achter een login: geen zoekmachine ziet het, en alle bladzijden onder `app/[lang]/` schuiven zou elke bestaande link breken. De winkelkeuze gebruikt al een cookie; één manier om een leesvoorkeur te bewaren is beter dan twee. De cookiewaarde wordt getoetst vóór gebruik, want ze wordt een mapnaam.

**Waarom de taalknop géén sessie vereist,** anders dan de winkelkiezer: `kiesWinkel` leest de winkelindex om de keuze te toetsen, en die verklapt hoeveel vestigingen de klant heeft. Een taal verklapt niets en geeft toegang tot niets. Zou hij een sessie eisen, dan kan een Franstalige gebruiker juist het aanmeldscherm niet in zijn taal lezen.

**Wat er niet meegaat:** de getalopmaak (`€ 1.234,56` in beide talen — het Belgisch Frans schrijft in de praktijk dezelfde punt en komma, en de scheidingstekens verzetten zou de enige laag raken waar dit platform met bedragen omgaat) en de productnamen (die komen uit Odoo; een vertaald assortiment toont namen die op geen kassabon staan).

**Wat nog niet klaar is, en hoe dat zichtbaar blijft:** 63 prozateksten (868 woorden) staan in de Franse contractmap nog in het Nederlands — vooral de langere `toelichting`- en `reden`-teksten op Productmix, Dagoverzicht en Instellingen. Dat wordt gemeten door de twee gebouwde contractbomen te vergelijken en bij elke `make contract` afgedrukt, met de volledige lijst in `reports/onvertaald.md`. De eerste versie van die teller mat alleen wat door de vertaalfunctie ging, en meldde daarmee "elke tekst bestaat in beide talen" terwijl de helft van het proza nog Nederlands was: een teller die alleen meet wat hij al kent, meldt schoon zodra je hem niet gebruikt. Dat is rechtgezet.

---

### 2026-08-14, Het Supabase-project blijft in eu-north-1 (Stockholm), niet in het Frankfurt uit de handleiding

**Wat:** `docs/setup-supabase.md` schreef `eu-central-1` (Frankfurt) voor. Lien heeft het project in `eu-north-1` (Stockholm) aangemaakt. Dat blijft zo; de handleiding en de foutmeldingen zijn aangepast naar `<regio>` in plaats van naar een vaste regio.

**Waarom:** Frankfurt stond in de handleiding om latentie en om niets anders. Stockholm is even goed een EU-lidstaat, dus aan de eis achter de keuze — data in de EU — is voldaan. Een project herbouwen om een paar milliseconden is die herbouw niet waard, zeker niet met de deadline van 27 augustus. Bij de deploy zetten we de Vercel-regio op `arn1` in plaats van `fra1`, zodat compute en database naast elkaar staan en de latentie alsnog klopt.

**Gevolg:** de controle in `bakkerij/db/verbinding.py` kijkt bewust alleen naar het achtervoegsel `.pooler.supabase.com` en nooit naar de regio. Een project verhuizen mag geen codewijziging vergen.

**Alternatief:** het project opnieuw aanmaken in Frankfurt. Verworpen: dat kost een wachtronde bij de opdrachtgever voor een voordeel dat we met de Vercel-regio gratis krijgen.

---

<!-- Nieuwe beslissingen hieronder, chronologisch -->

### 2026-08-15, De heropeningscorrectie is teruggedraaid: ze corrigeerde januari, niet heropeningen

**Wat:** het kenmerk "heropening" is uit de productievoorspeller gehaald, één dag na de adoptie. De methodenaam op het scherm is weer "weekdagmediaan, geschaald naar het niveau van de laatste twee weken, met schoolvakantiecorrectie (Franstalig regime)", en de gemeten fout staat op 7,8% WAPE in plaats van de 7,6% van gisteren.

**Waarom:** de meting waarop ze is aangenomen, klopte niet. `prognosekalender` leidde de open dagen af uit `winkel_open`, en die kolom staat buiten het gemeten bereik overal op `False` — `canoniek.py` waarschuwt daar met zoveel woorden voor, twintig regels boven de plek waar het misging. `overgangsdagen` neemt "de eerste drie open dagen ná het einde van een vakantie" uit die lijst, dus voor élke vakantie die vóór de meting eindigde kwam ze uit bij de eerste dagen van de meting zelf. Dat waren 2, 3 en 4 januari 2025: precies de galette-dagen rond Driekoningen, het zwaarste seizoenseffect in de historiek en volgens dezelfde diagnose goed voor 24% van de jaarfout. De correctie verdiende haar winst dus niet op heropeningen maar op januari, onder een verkeerde naam — terwijl een galette-seizoensfactor in ronde 2 van de diagnose uitdrukkelijk gemeten en afgewezen was.

**De hermeting** (drie spookdagen minder, n=343 out-of-sample): zonder heropening 7,754% totaal en 20,996% op de heropeningsdagen (n=15); mét heropening 7,766% en 21,240%. Ze verliest haar eigen deelvenster én het totaal. De E4-lat is "wint zijn deelvenster duidelijk zonder het totaal te schaden", en daar voldoet ze in geen van beide richtingen aan.

**Gevolg voor de toekomst:** de fout werkte ook vooruit. Omdat elke toekomstige dag als gesloten las, vuurde de correctie nooit op de getoonde prognose — de modelkaart beloofde "met heropeningscorrectie" en WAPE 7,6% terwijl het cijfer op het scherm uit een ander model kwam (harde regel 7). Dat is nu opgelost door open dagen te bepalen met exact de regel van `prognosevenster`: dicht is gemeten-én-dicht óf vooraf aangekondigd dicht, en al de rest is open.

**Wat blijft:** de vlag, `overgangsdagen` en negen nieuwe tests op een functie die er geen enkele had. Dat laatste is de eigenlijke les: de correctie was gemeten, geadopteerd, in twee bestanden gedocumenteerd en hier vastgelegd, en er raakte geen enkele test aan de functie die haar zette.

**Alternatief:** de correctie laten staan en alleen de vooruitwerkende fout herstellen. Verworpen: dan draait er een kenmerk mee dat zijn eigen deelvenster verliest, en dat is een model dat iets doet zonder dat iemand kan zeggen wat.

---

### 2026-08-15, Vaste schermteksten wonen in het woordenboek van de UI, niet in het contract

**Wat:** proza dat niet uit een meting volgt — de uitleg bij het kostenmodel, de sectorreferentie, het gebruikersbeheer, de wig-uitleg op Verkoopkanalen — staat in `platform/lib/taal.ts` met beide talen, en gaat niet door het contract. Wat wél uit een meting volgt (elk label bij een cijfer, elke reden, elke toelichting) blijft uit de berekeningslaag komen.

**Waarom:** harde regel 4 gaat over rekenen en over labels bij cijfers: de UI mag geen getal en geen bewering over een getal verzinnen. Een vaste alinea die uitlegt wat een foodcost is, hangt aan geen enkel cijfer en verandert nooit mee met de data. Die door de contractbouw laten lopen zou het contract vullen met tekst die niets met de meting te maken heeft, en elke zin twee keer laten bouwen zonder dat er iets aan verandert.

**Voorwaarde, en die is hard:** dan moet er wél iets zijn dat meet of die teksten in beide talen bestaan. De onvertaald-teller vergelijkt de twee contractbomen en kan per constructie niet zien wat er in een `.tsx` staat; daardoor stonden er op 15 augustus vijfentwintig Nederlandse teksten op de Franse schermen terwijl de teller netjes zijn contractteksten opsomde. `platform/tests/geen-harde-tekst.test.ts` meet nu die andere helft en faalt op leesbare tekst die niet door `t()` gaat.

**Alternatief:** álle schermtekst door het contract laten lopen, ook de vaste alinea's. Verworpen om bovenstaande reden — maar het blijft de nettere leer, en wie hem later toch wil doorvoeren, hoeft alleen het woordenboek leeg te trekken.

---

### 2026-08-17, Blok 9 (ingestmailbox) is geschrapt, TGTG bevriest op de historiek t/m juli 2026

**Wat:** het ingestmailbox-blok vervalt op vraag van de opdrachtgever, inclusief de periodieke TGTG-aanvoer (S7) en de Deliveroo-commissiemail (S8). Het TGTG-kanaal blijft in het platform staan, maar bevriest op de geparste historiek tot en met juli 2026 en veroudert vanaf dan zichtbaar: het scherm toont per kanaal tot wanneer de data loopt, in plaats van "geen data ingeladen" (harde regel 8).
**Waarom:** Lien wil de mailboxconstructie niet en aanvaardt dat TGTG zonder periodieke aanvoer blijft. Er gaat niets onherstelbaar verloren — TGTG bewaart de documenten zelf in MyStore, en de maandmail kan later alsnog aangezet worden, waarna het kanaal weer meeloopt vanaf dat moment.
**Gevolg:** S7, S8 en S9 vervallen uit `docs/todo.md`. Kwintens bezwaar — dit kiest bewust voor lagere datakwaliteit — is gemeld en staat genoteerd bij vraag 34/38 in `docs/vragen-aan-lien.md`.
**Alternatief:** de mailbox toch bouwen tegen het advies in, of wachten met beslissen. Verworpen: de opdrachtgever heeft de keuze expliciet gemaakt, en het platform kan een bevroren kanaal eerlijk tonen in plaats van op de aanvoer te wachten.

---

### 2026-08-17, De nachtelijke sync draait op een poortwachter over `write_date`, niet op een incrementeel extract

**Wat:** `bakkerij/db/sync.py` beslist per nacht of de volledige ketting (extract → canoniek → laden) draait, op basis van de jongste `write_date` in Odoo tegenover de laatste geslaagde run in `etl_run`, met één uur speling voor het tijdsverschil tussen Odoo-server en runner. Bij geen wijziging stopt de job na één goedkope vraag en één logregel. Het extract zelf blijft bij een run altijd volledig, nooit gedeeltelijk.
**Waarom:** de oorspronkelijke planning (todo, blok 8) ging uit van een incrementeel extract op `write_date`. Het extract aggregeert echter aan de bron tot dag × product × kassa, en een dag die maar half opnieuw wordt opgehaald en dan geüpsert overschrijft het volledige dagtotaal met een gedeeltelijk — stille corruptie die pas op het scherm zichtbaar wordt. Het volledige extract is sinds de herschrijving van 12 augustus goedkoop genoeg om elke nacht te draaien; bij nul wijzigingen (zomersluiting) doet de job zo bijna niets.
**Alternatief:** per-dag heraggregatie van alleen de dagen die de wijziging raakt. Overwogen en afgewezen om het corruptierisico: dat vraagt zekerheid over welke dagen precies geraakt zijn, en die zekerheid is er zonder zelf alles opnieuw op te halen niet.

---

### 2026-08-17, Elk aantal in de briefing draagt verplicht zijn eenheid

**Wat:** een `BriefingPunt` van soort `aantal` moet een `eenheid` meekrijgen ("dagen", "groepen", ...); `bakkerij/briefing.py` weigert met een `ValueError` zowel een aantal zonder eenheid als een eenheid bij een ander soort dan `aantal`. Euro's en verschillen krijgen geen eenheid — die maken zichzelf al leesbaar ("€ 1.234,56", "+0,4%").
**Waarom:** bij de visuele controle van 17 augustus las een kaal aantal ("9") rechtsboven in de briefing als een notificatieteller, niet als een cijfer met betekenis.
**Alternatief:** het aantal zonder eenheid tonen, zoals het tot dan deed, en het onderscheid met een teller aan de lay-out overlaten. Verworpen: de fout bleek pas zichtbaar op het scherm zelf, en de motor is de plek waar ze niet terug kan binnensluipen.

---

### 2026-08-17, De Supabase-rol komt strikt uit `app_metadata`, en zonder rol is er geen sessie

**Wat:** `platform/lib/auth-supabase.ts` leest de rol van een aangemelde gebruiker uitsluitend uit `app_metadata.rol` ("beheerder" of "bekijker"). Staat er geen geldige rol, dan levert `verifieerSupabase` geen sessie op: geen sessie zonder rol, en geen terugval op een standaardrol zoals "bekijker".
**Waarom:** `user_metadata` is door de gebruiker zelf te wijzigen via de Auth-API van Supabase; zou de rol daaruit gelezen worden, dan kan een bekijker zichzelf tot beheerder benoemen. Alleen `app_metadata` is voorbehouden aan wie de gebruiker beheert.
**Gevolg:** dit is het codepad achter `AUTH_BRON=supabase`, de belofte van 12 augustus dat alleen de functie `verifieer()` zou wisselen. Omschakelen wacht nog op S12 (zelfregistratie uit) en S13 (de gebruikerslijst).
**Alternatief:** de rol ook uit `user_metadata` aanvaarden, of een gebruiker zonder rol standaard als "bekijker" toelaten. Beide verworpen: het eerste is een privilege-escalatie die de gebruiker zelf kan uitvoeren, het tweede verzwijgt een configuratiefout als geldige toegang.

---

### 2026-08-17, Een percentage in lopende tekst komt uit één functie, in de bestaande spatienotatie

**Wat:** elk percentage in lopende tekst — Nederlands en Frans, backend en frontend — staat als "7,8 %": komma als decimaalteken, een gewone spatie vóór het procentteken. In Python komt dat voortaan uit `bakkerij/taal.py::procent_tekst`, in dezelfde notatie als `platform/lib/format.ts::procent`; `bakkerij/kwaliteit.py` roept haar nu aan in plaats van een eigen kopie te dragen.
**Waarom:** de visuele steekproef van 17 augustus vond op één scherm "7,8%" naast "8,1 %" — `contract.py`, `briefing.py` en `kwaliteit.py` droegen elk hun eigen `f"{...:.1f}".replace(".", ",")`, met en zonder spatie.
**Alternatief:** de losse kopieën per module laten staan, of een typografisch preciezere no-break-spatie invoeren. Beide verworpen: het eerste liet de inconsistentie bestaan, het tweede zou een tweede notatie naast de bestaande TS-conventie zetten.

---

### 2026-08-17, Kolomkoppen en telwoorden van Productmix komen uit het contract, niet uit de UI

**Wat:** de tabelkoppen en de samengevatte rijlabels op het productmixscherm ("komt van", "van het assortiment", "overige 23 producten") worden voortaan door de contractbouw vertaald en aangeleverd (`concentratie.kolommen`, `r.label`, `g.rest.label`); `platform/app/(dash)/producten/page.tsx` plakt er zelf geen tekst meer bij.
**Waarom:** de visuele steekproef van 17 augustus vond die drie teksten op het Franse scherm nog in het Nederlands. Ze stonden hard in de pagina en gingen daardoor buiten de vertaalfunctie én buiten de contractteller om — een schending van harde regel 4, want een telwoord als "23 producten" is een bewering over een telling, en die telling hoort in de berekeningslaag te gebeuren.
**Alternatief:** de UI zelf laten vertalen via het woordenboek (`platform/lib/taal.ts`). Verworpen: dat zet tekst die van een telling afhangt in de presentatielaag, en dat is precies wat harde regel 4 uitsluit.

---

### 2026-08-17, De vertaalteller classificeert expliciet welke gelijke tekst normaal is, niet meer op woordlengte

**Wat:** `scripts/contract_bouw.py::vergelijk_talen` beslist per contractpad of een tekst die in beide taalversies identiek is, terecht gelijk is — via vier expliciete lijsten (`BRONVELDEN`, `BRONPADEN`, `MACHINEPADEN`, `MERKNAMEN`) — in plaats van via de vroegere regel "drie woorden of minder is wel een productnaam". `LEESBARE_VELDEN` is bovendien uitgebreid met kolomkoppen, drempels, briefingproza en tekstwaarden die voorheen niet meetelden.
**Waarom:** de oude drempel liet "komt van", "29 producten" en "overige 8 producten" ongezien door, want die zijn alle drie kort. De nieuwe teller ving daardoor 13 onvertaalde teksten die de oude nooit zag, en na vertaling geen enkele meer.
**Alternatief:** de lengteheuristiek bijschaven met een andere woordgrens. Verworpen: elke grens vangt evenveel toevallig kort proza als hij productnamen doorlaat; alleen weten wát een pad ís (een productnaam, een merknaam, proza) lost het structureel op.

---

### 2026-08-18, CONTRACT_BRON=db leest via PostgREST met de secret key, niet via een rechtstreekse Postgres-verbinding

**Wat:** de leesroute van het contract uit de database loopt bij `CONTRACT_BRON=db` via PostgREST, met `SUPABASE_SECRET_KEY` als server-only sleutel. Er komt geen aparte Postgres-verbinding voor het lezen.
**Waarom:** de secretstabel in `docs/stack.md` houdt `SUPABASE_DB_URL` (het databasewachtwoord) weg van Vercel; de PostgREST-bezwaren in datzelfde document (geen COPY, geen transacties, chunking) gelden voor de schrijvende ETL, niet voor het lezen van één voorgeaggregeerde JSONB-rij per scherm. Het scheelt bovendien een npm-dependency (`pg`) in het platform.
**Alternatief:** een aparte read-only Postgres-rol met eigen wachtwoord op Vercel. Verworpen: dat is een extra geheim, rolbeheer op clusterniveau, en poolerbeheer in een serverless omgeving voor een lezing die PostgREST net zo goed aankan. Zie `platform/lib/contract-bron.ts`.

---

### 2026-08-18, `contract_antwoord` is één tabel, sleutel scherm × taal × winkel, zonder normalisatie van de inhoud

**Wat:** de gehoste vorm van het contract is één tabel met de JSON als geheel in een `jsonb`-kolom, sleutel scherm × taal × winkel (`''` voor het totaal). Er worden geen velden uit de JSON in eigen kolommen getrokken.
**Waarom:** het contract ís het contract — één vorm voor alle consumenten. Kolommen eruit trekken zou een tweede waarheid maken die bij elke contractwijziging mee moet verhuizen. De sleutel scherm × taal lag al vast in het draaiboek; winkel is eraan toegevoegd zodat de winkelkiezer later niet om een nieuwe migratie vraagt.
**Alternatief:** de inhoud normaliseren naar eigen kolommen of tabellen. Verworpen om bovenstaande reden. Zie `db/migraties/006_contract.sql`.

---

### 2026-08-18, Het contract wordt geladen met delete-alles plus insert-alles in één transactie, geen upsert

**Wat:** `scripts/contract_laad.py` wist eerst de volledige `contract_antwoord`-tabel en voegt daarna alle rijen opnieuw in, binnen één transactie.
**Waarom:** een winkel die uit de indeling verdwijnt moet ook uit de database verdwijnen — de contractbouw leegt om dezelfde reden eerst de winkels-map. Binnen één transactie ziet geen lezer ooit een lege tabel, en bij zo'n veertien rijen per taal is COPY-met-tijdelijke-tabel overkill.
**Gevolg:** dit wijkt bewust af van het upsert-patroon van de feitentabellen (zie "Wegschrijven gebeurt met COPY plus insert-on-conflict" van 13 augustus); het commentaar bij `VERWIJDER_SQL` in `bakkerij/db/contract_rijen.py` legt het verschil uit.
**Alternatief:** insert-on-conflict, zoals bij de feitentabellen. Verworpen: dat laat spookwinkels staan die uit de indeling zijn verdwenen.

---

### 2026-08-18, De contractverzameling faalt luid op een half gebouwde contractboom

**Wat:** `bakkerij/db/contract_rijen.verzamel` werpt een fout zodra er iets ontbreekt of niet klopt — een ontbrekend scherm, kapotte JSON, een winkelmap die niet in de winkelindex staat — in plaats van te uploaden wat er wél leesbaar is.
**Waarom:** de nachtelijke sync draait zonder toeschouwer. Een half contract naar de database schrijven is erger dan een gefaalde run: dat laatste laat een leesbare reden na in `etl_run` en het platform blijft op het vorige, wél volledige contract draaien (dankzij de alles-of-niets-transactie hierboven).
**Alternatief:** zoveel mogelijk uploaden en de rest overslaan met een waarschuwing. Verworpen: dat zou een deel van het platform op oude cijfers laten draaien en een ander deel op nieuwe, zonder dat iemand dat ziet.

---

### 2026-08-18 (inspectieronde), Een leeg Odoo-extract is een fout, geen lege dag

**Wat:** het extractscript stopt voortaan met exitcode 1 zodra Odoo nul orders teruggeeft voor de gevraagde periode, in plaats van exitcode 0 door te geven. `canoniek_bouw` mag dat resultaat daardoor niet meer stilzwijgend inruilen voor het extract van de vorige dag.
**Waarom:** deze bakkerij kent geen dag zonder verkoop — een leeg extract is bij haar per definitie een falend contact met Odoo, geen echte nulmeting. Met exitcode 0 pakte de canoniekbouw ongemerkt gisterens bestand en meldde de ketting "goed" op data die niet van vandaag was.
**Alternatief:** een leeg extract aanvaarden als geldige lege dag, voor het geval de winkel echt niets verkocht. Verworpen: dat geval bestaat niet bij deze bakkerij, en de stille variant verstopt precies de storing die een wachter hoort te vangen.

---

### 2026-08-18 (inspectieronde), Revoke geldt nu ook voor `authenticated`, en `schema_migraties` krijgt RLS — de checksums van migraties 001-006 zijn herschreven

**Wat:** elke migratie trekt schrijfrechten voortaan in van zowel `anon` als `authenticated`, en `schema_migraties` krijgt dezelfde RLS-behandeling als elke andere tabel in `public`. Daardoor zijn de checksums van migraties 001 tot en met 006 gewijzigd.
**Waarom:** de revoke gold tot dan alleen `anon`, waardoor `authenticated` zijn standaard-schrijfrechten hield en RLS de enige verdedigingslaag was in plaats van één van twee. `schema_migraties` was de enige tabel in `public` zonder RLS: met de publiceerbare sleutel was ze via PostgREST niet alleen leesbaar maar ook schrijfbaar, en rijen wissen betekent alle migraties opnieuw laten draaien.
**Voorwaarden:** het wijzigen van een checksum van een migratie die al is uitgevoerd, is normaal verboden. Dat het hier wel kan, is enkel omdat er nog nergens een echte database op deze migraties draait (S11 ontbreekt); zodra die er is, geldt de gewone regel weer.
**Alternatief:** de bestaande migraties laten staan en de correctie in een nieuwe migratie zetten. Voor S11 verworpen: het kost niets om de fout nu recht te zetten in plaats van haar als schuld mee te dragen naar de eerste echte database.

---

### 2026-08-18 (inspectieronde), De klantdatavangrail matcht op kolomstammen, met een bewuste uitzondering voor het kale `btw`

**Wat:** `controleer_kolommen` in `bakkerij/db/laden.py` weigert een kolom zodra haar naam een stam uit een vaste lijst bevat (`partner`, `klant`, `adres`, `street`, `note`, `email`, `vat`, `btw_nummer`, ...), in plaats van te toetsen op een lijst exacte kolomnamen. De stam `btw` op zich staat bewust niet op de lijst.
**Waarom:** de exacte-naamlijst liet `customer_note` en `partner_street` gewoon door — precies de vormen waarin Odoo klantvelden aanlevert. Toetsen op stammen vangt die varianten in één keer. Zonder de uitzondering voor `btw` zou de vangrail de eigen kernkolom `omzet_excl_btw` weigeren.
**Alternatief:** de exacte-naamlijst uitbreiden met elke nieuwe variant die opduikt. Verworpen: dat blijft achter de feiten aanlopen, terwijl een stam de hele familie van varianten in één keer afvangt.

---

### 2026-08-18 (inspectieronde), De nachtelijke cron blijft bewust uit tot S11

**Wat:** de schedule van `nachtelijke-sync.yml` staat uit. Aanzetten wacht op S11 (het databasewachtwoord op de runner) en op de invoer die niet in git staat (TGTG-bestanden, beheerconfig). Het recept om de cron aan te zetten staat in het workflowbestand zelf.
**Waarom:** een verse runner mist vandaag beide. Elke nacht laten draaien zou ofwel een rode run opleveren waar niemand naar kijkt, ofwel — erger — een verarmd contract dat het goede contract stilzwijgend overschrijft.
**Alternatief:** de cron nu al aanzetten en de rode runs tot S11 aanvaarden. Verworpen: een falende nachtrun die niemand leest is geen wachter maar ruis, en ruis camoufleert de echte storing wanneer die zich voordoet.

---

### 2026-08-18 (inspectieronde), In supabase-modus wordt een sessie niet per verzoek bij Supabase herbevestigd; een ingetrokken rol werkt pas door na de cookie

**Wat:** `lees()` toetst een sessiecookie onder `AUTH_BRON=supabase` alleen op handtekening en vervaltijd, niet langer tegen een gebruikerslijst — die lijst (`PLATFORM_GEBRUIKERS`) is in deze modus leeg. Een ingetrokken rol of een verwijderde gebruiker werkt daardoor pas door zodra de cookie afloopt, ten hoogste twaalf uur later.
**Waarom:** de bestaande hertoetsing van 14 augustus was geschreven voor de omgevingsgebaseerde inlog en toetste ook in supabase-modus tegen diezelfde lege lijst. Elke geldige sessie werd daardoor meteen verworpen: login en de toegangsproxy kaatsten elkaar eindeloos door, en het platform was in deze modus onbereikbaar zonder dat een test dat zag.
**Alternatief:** bij elk verzoek de rol opnieuw bij Supabase navragen. Niet verworpen maar uitgesteld: dat sluit het gat volledig maar kost een aanroep per verzoek; de twaalf-uursgrens van de bestaande cookie is de prijs die voorlopig aanvaard is.

---

### 2026-08-18 (inspectieronde), Het kostenmodel weigert op te slaan onder `CONTRACT_BRON=db`, in plaats van te schrijven naar een schijf die niemand leest

**Wat:** `bewaarKostenmodel` weigert een opslagpoging zodra `CONTRACT_BRON=db` staat; het scherm toont in dat geval het Onbeschikbaar-vak met de reden. De echte schrijfroute (`kosten_criterium`/`kosten_waarde` via PostgREST) is nog niet gebouwd en volgt bij de S11-uitrol.
**Waarom:** vóór deze wijziging schreef het formulier naar een lokaal bestand en gaf het er een make-instructie bij aan een bakker die geen terminal gebruikt — een opslagactie die niets opsloeg van wat het gelezen scherm toont. Harde regel 8 verbiedt precies dat: een geblokkeerd cijfer hoort als onbeschikbaar getoond te worden, niet alsof de opslag werkt.
**Alternatief:** de echte databaseschrijfroute meteen bouwen. Uitgesteld, niet verworpen: die hoort logisch bij de S11-uitrol van de rest van het schrijfpad, en tot dan is eerlijk weigeren beter dan een stille no-op.

---

### 2026-08-18 (onderhoudsronde), De rol heet voortaan "lezer", niet "bekijker"

**Wat:** de rolnaam in code is "beheerder" of "lezer". Een bestaande `PLATFORM_GEBRUIKERS`-regel met "bekijker" blijft geldig en normaliseert bij het inlezen naar "lezer".
**Waarom:** `scope.md` (D6) en vraag 57 — de gebruikerslijst die bij de klant ligt — spreken al van "lezer"; de code droeg tot vandaag een eigen woord. De hernoeming gebeurt bewust nu, vóór S13 de eerste echte accounts aanlevert; na S13 zou dezelfde ingreep bestaande accounts raken.
**Alternatief:** de documentatie ombuigen naar "bekijker" in plaats van de code aan te passen. Verworpen: "lezer" is de term die al bij de klant ligt (vraag 57), en die weegt zwaarder dan de naam die toevallig het eerst in code stond.

---

### 2026-08-18 (onderhoudsronde), DROOG betekent overal "alles behalve schrijven"

**Wat:** `canoniek_bouw.py` en `contract_bouw.py` honoreren de vlag `DROOG` nu net als de rest van het platform: de volledige bouw draait — beide talen, alle winkels, alle wachters — en alleen het wegschrijven en het wissen van bestanden vervalt.
**Waarom:** tot vandaag negeerden beide scripts de vlag. `make sync-droog`, die "zonder schrijven" belooft, overschreef daardoor stil de laatst goede bouw op een productiemachine. Een droge run bewijst het nu: 221.375 rijen gebouwd, nul bytes geschreven.
**Alternatief:** het Makefile-commentaar afzwakken naar wat de vlag tot nu toe werkelijk deed. Verworpen: dat maakt een droge run onbruikbaar als veilige proef, en dat is precies waarvoor hij bedoeld is.

---

### 2026-08-18 (onderhoudsronde), requirements.txt krijgt bovengrenzen op major, en ondergrenzen die kloppen met wat draait

**Wat:** elke dependency in `requirements.txt` draagt voortaan een bovengrens op de eerstvolgende major-versie (`pandas>=3.0,<4`, `numpy>=2.1,<3`, ...), behalve ruff, die strakker vastzit op de minor (`>=0.16,<0.17`). De ondergrenzen zijn opgetrokken naar wat er op 18 augustus 2026 werkelijk draait en getest is.
**Waarom:** de venv draaide al pandas 3 terwijl het bestand `>=2.2` beloofde — een compatibiliteit die niemand meer toetste. Zonder bovengrens kan een stille major-upgrade de reden worden dat een cijfer verandert, zonder dat iemand dat besliste. Ruff voegt bij elke minor nieuwe lintregels toe, die een onschuldige push rood kunnen maken.
**Alternatief:** een lockfile, of alle versies vrij laten. Een lockfile is niet gekozen omdat het project bewust kort blijft ("elke dependency moet zich verdienen in de backtest") en geen apart lock-bestand wil onderhouden; vrij laten is verworpen om de reden hierboven.

---

### 2026-08-18 (onderhoudsronde), S12 blijkt smaller: ES256 blokkeert niets, alleen zelfregistratie-uit en S13 doen dat

**Wat:** van de twee Authentication-instellingen die aan S12 hangen, blokkeert alleen "zelfregistratie uit" het overschakelen naar `AUTH_BRON=supabase`. "ES256 aan" blijft aan Lien gevraagd als toekomstvaste instelling, maar niet langer als blokkade.
**Waarom:** de oorspronkelijke motivering — zonder ES256 doet `getClaims()` een netwerkcall per verzoek — is tegen de code gelegd en klopt niet: `platform/lib/auth-supabase.ts` gebruikt geen SDK en geen `getClaims()`, toetst het wachtwoord via de token-endpoint en tekent daarna een eigen HMAC-cookie. Er wordt nergens een Supabase-JWT geverifieerd, dus het ondertekeningsalgoritme is voor dit platform onverschillig.
**Gevolg:** `docs/todo.md` en `docs/setup-supabase.md` zijn aangepast: S12 blijft als nummer en als gevraagde instelling bestaan, maar de tekst zegt nu expliciet dat alleen zelfregistratie-uit (plus S13, de gebruikerslijst) blok 12 tegenhoudt.
**Alternatief:** de oude motivering laten staan en ES256 als blokkade blijven vragen. Verworpen: dat vraagt de opdrachtgever een wachtronde voor een instelling die de code niet nodig heeft.

---

### 2026-08-18 (onderhoudsronde), .xls wordt geweigerd met een reden, xlrd komt er niet bij

**Wat:** `bakkerij/io_load.py` leest geen `.xls` meer. Een `.xls`-bestand levert een `ValueError` met de instructie het opnieuw op te slaan als `.xlsx`, in plaats van dat pandas een `xlrd`-`ImportError` uit haar binnenwerk laat komen.
**Waarom:** het oude `.xls`-formaat vraagt de losse dependency `xlrd`, die bewust niet in `requirements.txt` staat. Eén export opnieuw opslaan als `.xlsx` is voor wie dit raakt sneller dan een extra bibliotheek dragen voor een formaat dat sinds 2007 vervangen is.
**Alternatief:** `xlrd` toevoegen zodat `.xls` gewoon werkt. Verworpen: dat voegt een dependency toe voor een uitfaserend formaat, terwijl de gebruiker het probleem zelf met één "opslaan als" oplost.

---

### 2026-08-18, Het CFO-rapport is een weergave geworden, geen gebouwd bestand

**Wat:** `/rapport` is geen PDF-download meer maar een bladzijde in het platform die de gekozen schermen achter elkaar zet, gelezen uit hetzelfde contract op het moment van opvragen. De browser maakt de PDF (afdrukken → opslaan als PDF). Opgeheven: `bakkerij/report/pdf.py` (563 regels), `scripts/rapport_pdf.py`, `tests/test_rapport_pdf.py`, het make-doel `rapport-pdf`, de PDF-stap in `make alles` en de WeasyPrint-afhankelijkheid. Dit herroept de twee beslissingen van 13 augustus over dit rapport.
**Waarom:** twee gebreken die met opmaak niet te verhelpen waren. (1) Het bestand was zo vers als de laatste bouw: wie na een herberekening op de knop drukte, kreeg andere cijfers dan op het scherm ernaast — precies wat `laadContract` voor de schermen juist voorkomt. (2) Het was een tweede tekenlaag met een eigen kopie van de huisstijl (kleuren, tabellen, SVG-geometrie), en twee tekenlagen van hetzelfde document lopen uiteen; `open-punten.md` had dat al genoteerd als "de PDF vertelt minder dan de schermen".
**Alternatief:** de PDF-bouwer bijwerken tot hij de schermen inhaalt. Verworpen: dan is er nog steeds een tweede laag die opnieuw kan achterlopen, plus een systeemafhankelijkheid (pango) die op Vercel niet bestaat. Tweede alternatief: een headless browser in het platform die bij elk verzoek een PDF rendert. Verworpen: ~50 MB chromium in een serverless functie, voor iets wat de browser van de lezer al kan.
**Heropening:** vraagt iemand ooit een PDF zonder browser (maandelijkse archiefkopie, bijlage per mail), dan is dat een klein script over dezelfde route — Chrome openen op `/rapport` met een sessiekoekje en `page.pdf()`, in de trant van `scripts/visuele_steekproef.mjs`. Op 18 aug gemeten en werkend bevonden; bewust niet gebouwd zolang niemand het vraagt.

---

### 2026-08-18, Het rapport hergebruikt de schermcomponenten, en stelt niets zelf samen

**Wat:** de onderdelen van het rapport zijn de paginacomponenten van de zes schermen, geïmporteerd en achter elkaar gerenderd — geen tweede opbouw uit het contract. Wat niet op papier hoort (het kostenformulier, het gebruikersbeheer) draagt `data-buiten-rapport` in het scherm zelf en valt in het rapport weg.
**Waarom:** dit is de enige vorm waarin het rapport niet kan achterlopen op de schermen. Een blok dat op een scherm bijkomt, staat daarmee ook in het rapport, zonder dat iemand eraan hoeft te denken. Dezelfde reden waarom `RAPPORT_DELEN` één lijst is die zowel het menu als het rapport leest.
**Alternatief:** een curatie per onderdeel (zoals de WeasyPrint-bouwer had: een eigen selectie van tegels, tabellen en grafieken). Verworpen: dat is precies de tweede samenstelling die uiteen ging lopen. De prijs van deze keuze is dat het rapport net zo uitvoerig is als de schermen; het keuzemenu is het antwoord daarop.

---

### 2026-08-18, De keuze van rapportonderdelen leeft in de URL, niet in een cookie

**Wat:** het keuzemenu is een `<details>` met een gewoon GET-formulier; de vinkjes worden URL-parameters (`/rapport?deel=kanalen&deel=prognose`). Geen JavaScript, geen bewaarde voorkeur. Onbekende waarden worden genegeerd, en zonder geldige waarde bevat het rapport alle onderdelen.
**Waarom:** een rapport is dan een adres: deelbaar, te bewaren als bladwijzer, en te herhalen. En er bestaat geen tweede plek waar de keuze leeft, dus geen stand waarin de bewaarde voorkeur iets anders zegt dan het document toont. De terugval "niets gevraagd = alles" is de veilige kant: liever te veel dan een lezer die niet weet wat er uit zijn afdruk weggelaten is.
**Alternatief:** de keuze in een cookie zoals de taal en de winkel. Verworpen: die twee zijn leesvoorkeuren die je één keer zet, een rapportselectie is een keuze per document. Tweede alternatief: de native popover-API in plaats van `<details>` (die geeft licht-sluiten gratis). Verworpen zolang ankerpositionering niet overal beschikbaar is — het paneel zou dan midden in het beeld verschijnen in plaats van bij de knop.

---

### 2026-08-18, Op papier draagt de haarlijn de structuur, en het bordeaux kerncijfervlak wordt wit

**Wat:** in de afdrukregels (`globals.css`) krijgt elk wit paneel een haarlijn in warmgrijs, wordt de paginavloed wit, en wordt het vaste bordeaux kerncijfervlak een paneel met zwarte cijfers. Bordeaux blijft op papier in de koppen, de staven en de lijnen van elke grafiek.
**Waarom:** een printer neemt achtergrondvlakken pas mee als de lezer dat aanvinkt, en dat staat in Chrome, Safari en Firefox standaard uit. Een ontwerp dat op vullingen leunt, valt daar om: witte panelen worden onvindbaar op wit papier en een wit cijfer op bordeaux wordt onleesbaar. Tekst en SVG neemt een printer altijd mee. Zo ziet de afdruk er hetzelfde uit met of zonder dat vinkje — één voorspelbaar document.
**Huisstijl:** de regel die hier geldt, blijft onverkort overeind. De kleur van een cijfer volgt de drager waarop het staat en draagt nooit betekenis; het accent blijft op zijn vaste positie (het eerste kerncijfer, het weektotaal) en verhuist niet met goed of slecht nieuws. Alleen de drager verandert met het medium.
**Alternatief:** bordeaux forceren met `print-color-adjust: exact`. Verworpen: die eigenschap onderdrukt kleuroptimalisatie, maar overstemt het vinkje "achtergronden meenemen" niet — het resultaat zou zijn dat de afdruk soms leesbaar is en soms niet.

---

### 2026-08-18, De databasesuite draait tegen een echte Postgres, ook in CI

**Wat:** `tests/test_db_echt.py` plus een `echte_db`-fixture die verbindt via `TEST_DB_URL`. Zonder die variabele slaat de suite zichzelf over; in CI draait een `postgres:17`-servicecontainer waarin eerst de drie Supabase-rollen (`anon`, `authenticated`, `service_role`) worden aangemaakt. Dit herroept de uitspraak in de kop van `tests.yml` dat er "geen database nodig" is.
**Waarom:** de databaseloze opzet was zuinig en verdedigbaar tot de eerste echte run. Die vond op één ochtend drie fouten die geen enkele bestaande test kón zien: een COPY die lege tekst als NULL aanbood aan een `not null`-kolom (de laadstap stierf op rij één van de eerste tabel), een migratie die grants deed op een tabel die een latere migratie weer weghaalt, en een rol zonder leesrecht op precies de tabel waaruit het platform leest. 88 groene tests zeiden daar niets over, en de droge modus kon het per constructie niet zien — die stopt vóór het schrijven. Een wegwerp-Postgres kost twintig seconden per push en geen enkel geheim: er gaat schema in, nooit klantdata.
**Alternatief:** wachten tot S11 en dan tegen Supabase testen. Verworpen: dat is precies de volgorde die het risico maakte — de eerste echte run zou dan in de laatste week vallen, met vier dagen marge en elke fout serieel.
**De fixture omzeilt bewust `verbind()`:** die eist `sslmode=require` en poort 5432, en dat hoort ze te blijven eisen. Een wegwerpdatabase op localhost heeft dat niet nodig, en de productiewacht versoepelen om een test te laten draaien is de verkeerde kant op.

---

### 2026-08-18, De jaar-op-jaarschuif is 364 dagen en geen 365

**Wat:** `JAARSCHUIF = pd.Timedelta(days=364)` in `bakkerij/berekening.py`. Elk jaar-op-jaarcijfer op het overzichtsscherm verschuift daarmee met 52 hele weken in plaats van met een kalenderjaar.
**Waarom:** 365 is geen veelvoud van zeven, dus een schuif van 365 legt zaterdag naast vrijdag. In een bakkerij is de weekdag de sterkste verklarende variabele die er is — zaterdag doet ruwweg het dubbele van dinsdag — dus die faseverschuiving zit als systematische fout in élke jaarvergelijking. Gemeten op de echte reeks: over 30 open dagen gaf 365 een jaarverschil van +22,1% en 364 een van +26,9%. Bijna vijf procentpunt, puur uit de keuze van deze constante. `vorig_volledig` telt alleen open dagen en kan een faseverschuiving niet zien.
**Alternatief:** 365 houden en de weekdagverdeling apart corrigeren. Verworpen: dat is een model bovenop een venster, terwijl het venster zelf goedkoop juist te kiezen is. Tweede alternatief: schuiven op weeknummer. Verworpen: ISO-weken lopen niet gelijk met de peildatum en introduceren hun eigen randgevallen rond de jaarwisseling.
**De prijs:** het vergelijkingsvenster schuift elk jaar één dag verder van de kalenderdatum af. Over de horizon van dit platform (twee jaar historiek) is dat één à twee dagen, en dat weegt niet op tegen een structureel verschoven weekdag.

---

### 2026-08-18, De bouw weigert op Vercel zonder CONTRACT_BRON=db

**Wat:** `platform/next.config.ts` werpt bij `process.env.VERCEL && CONTRACT_BRON !== "db"`, met de reden en de op te lossen stap in de melding. Lokaal en in `next dev` verandert er niets.
**Waarom:** dit is de gevaarlijkste faalvorm die het platform kent, en hij is stil. `platform/contract/` is gitignored (geaggregeerde omzetcijfers), dus op Vercel bestaat die map niet; alle routes zijn dynamisch, dus de build raakt het contract nooit aan en merkt niets. Gemeten: `npm run build` slaagt in 791 ms zonder één contractbestand. De deploy wordt groen en élk scherm valt daarna om met ENOENT — en je ontdekt dat op de dag dat je de URL deelt. Een bouwfout met een leesbare reden is oneindig veel beter dan een geslaagde deploy die niet werkt.
**Alternatief:** `outputFileTracingIncludes` gebruiken om de contractmap in de functiebundel te trekken. Verworpen: die bestanden staan niet in git, dus op Vercel valt er niets te tracen — het zou een vangnet zijn dat per constructie nooit vangt. Tweede alternatief: het contract alsnog committen. Verworpen: dat zet klantomzet in de repo.

---

### 2026-08-18, Migratie 008 maakt de leesrechten van service_role expliciet

**Wat:** een migratie die `grant select` geeft aan `service_role` op alle dertien tabellen. Geen enkele eerdere migratie deed dat.
**Waarom:** het platform leest het contract met `SUPABASE_SECRET_KEY`, en die sleutel komt bij PostgREST binnen als `service_role`. Die rol draagt BYPASSRLS, maar dat zegt niets over tabelrechten. Dat het tot nu toe werkte, komt door default privileges die Supabase zelf op schema `public` heeft staan — een eigenschap van de omgeving, niet van deze repo: ze staat in geen enkel bestand, ze is niet herbouwbaar uit de migraties, en Supabase kan haar wijzigen zonder dat hier iets verandert. Op een kale Postgres gaf dezelfde code `permission denied for table contract_antwoord`, en onder `CONTRACT_BRON=db` is dat élk scherm. De projectregel is dat de database herbouwbaar is uit de migraties; dan hoort ook het rechtenmodel erin te staan.
**Alternatief:** vertrouwen op de Supabase-defaults en het in `stack.md` documenteren. Verworpen: een aanname die je opschrijft blijft een aanname, en deze is met dertien regels SQL een feit te maken. Bovendien raakt het de exitregeling — een herstel naar een niet-Supabase Postgres zou stil een onleesbaar contract opleveren.
**Alleen select:** de ETL schrijft als eigenaar over de Postgres-verbinding, niet via PostgREST. Wie hier ooit schrijfrechten aan toevoegt, moet eerst uitleggen waarom die route niet meer volstaat.

---

### 2026-08-18, De contractlader weigert een krimpend contract

**Wat:** `scripts/contract_laad.py` vergelijkt de sleutels (scherm, taal, winkel) die het gaat schrijven met wat er al staat, en weigert wanneer er antwoorden zouden verdwijnen. Te overrulen met `CONTRACT_KRIMP_OK=1`.
**Waarom:** het schrijven is `delete` gevolgd door `insert` in één transactie, en dat is de juiste vorm — een winkel die uit de indeling verdwijnt, hoort ook uit de database te verdwijnen. Maar diezelfde vorm maakt een verarmde bouw gevaarlijk. De nachtelijke sync draait op een GitHub-runner, en die heeft `data/config/` en de TGTG-bestanden niet: die staan gitignored en alleen op de bouwmachine. Bouwt de runner daar een contract zonder winkelindeling, dan schrijft hij dat met succes over het goede heen. Groene run, minder cijfers op het scherm, geen melding. `todo.md` had dit risico al benoemd zonder er iets tegenover te zetten.
**Alternatief:** de runner de ontbrekende config laten ophalen. Verworpen voor nu: dat is blok 9-werk dat op 17 augustus geschrapt is, en de wacht is drie regels. Tweede alternatief: op rijaantallen vergelijken in plaats van op sleutels. Verworpen: dan glipt een bouw met evenveel rijen maar andere schermen erdoor.
**Bewust een omgevingsvariabele en geen make-vlag:** krimp hoort een eenmalige, bewuste handeling van een mens te zijn en niet iets dat in een make-doel kan inslijten.

---

### 2026-08-18, De heropeningscorrectie is voor de tweede keer teruggedraaid, nu omdat twee metingen elkaar tegenspreken

**Wat:** het kenmerk "heropening" is opnieuw geadopteerd en binnen het uur weer uit `KENMERKEN` gehaald. Productie blijft `weekdagmediaan, geschaald naar het niveau van de laatste twee weken, met schoolvakantiecorrectie (Franstalig regime)`, 7,8 % WAPE. Adoptie was uitdrukkelijk gevraagd door de opdrachtnemer; het terugdraaien is een meetuitkomst, geen voorkeur.

**Waarom niet geadopteerd:** twee constructies van dezelfde vlag geven een tegengesteld verdict over hetzelfde totaal.

| | WAPE | Gem. fout €/dag | Bias |
|---|---:|---:|---:|
| niveau + vakantie FR | 7,8 % | 1.004 | −119 |
| niveau + vakantie + heropening FR | 7,8 % | 1.006 | −120 |

E4 (dat sinds vanavond de échte productieconstructie leent in plaats van hem na te bouwen) meet dus een fractie *slechter*, waar de diagnose +0,12 punt winst meldt. Het verschil zit niet in het model: de diagnose leidt de ná-vakantiedagen af uit `reeks.index` (alleen gemeten dagen), `prognosekalender` uit `open_of_gepland_open` over de hele kalender inclusief toekomst. Op 14 augustus was één constructie fout; nu zijn er twee die van elkaar afwijken. Zolang dat zo is, is geen enkele adoptie van dit kenmerk eerlijk te onderbouwen — en een modelwijziging op de avond vóór de pre-flight verdient het voordeel van de twijfel niet (harde regel 7).

**Wat de ronde wél heeft opgeleverd, en blijft staan:**

1. **De januari-splitsing in de diagnose.** Het vermoeden was dat de correctie haar winst uit de galette-dagen haalt: de kerstvakantie eindigt begin januari, dus de eerste open dagen ná die vakantie *zijn* elk jaar Driekoningen — geen vlaggenfout zoals op 14 augustus, maar een echte samenloop. Gemeten en weerlegd: ná-dagen in januari (n=3) 46,1 % → 46,1 % (−0,08 pt), buiten januari (n=12) 8,8 % → 5,2 % (**+3,68 pt**), bias −869 → −396. De correctie doet dus wél wat haar naam belooft; alleen is niet vast te stellen hoeveel.
2. **`MIN_VENSTER_DAGEN` in de diagnose.** Die januari-splitsing klapte het mechanische oordeel om op −0,08 punt over drie dagen met 46 % WAPE. Een venster dat te dun is om een winst te bewijzen, is ook te dun voor een veto; anders straft het meetinstrument je voor het toevoegen van een venster.
3. **E4 leent de productievoorspeller.** Zonder die wijziging was deze tegenspraak onzichtbaar gebleven: het rapport noemde een halve dag het verkeerde model "in productie", en het label leest zichzelf nu uit `KENMERKEN`.
4. **Drift opgeruimd:** `bouw_voorspeller` heette `weekdag_niveau_vakantie_heropening_fr` en zei in zijn docstring "met heropeningscorrectie", drie dagen nadat dat kenmerk eruit was. Die naam bereikte het contract en de database niet (nagekeken: 0 antwoorden), maar hij zette twee lezers op het verkeerde been — waaronder de agent die vanavond ging adopteren wat er al uit was.

**Voorwaarde voor een derde poging:** eerst één constructie van de productievoorspeller, in `bakkerij/` in plaats van drie keer in `scripts/`. Dan opnieuw meten, dan beslissen.

**Alternatief:** adopteren op de diagnose alleen, omdat het totaal per saldo een wash is en de heropeningsdagen aantoonbaar beter worden. Verworpen: dan staat er een claim in de modelkaart waarvan het ondersteunende cijfer (7,8 % tegen 7,8 %) geen winst laat zien, en dat is precies de vorm van 14 augustus.

---

### 2026-08-18, De reden van een onbeschikbaar-vak klapt altijd in, en niet boven een lengtegrens

**Wat:** in `Onbeschikbaar` gaat de reden altijd achter `MeerInfo` ("Waarom niet"). De titel en de regel "Nog niet beschikbaar" blijven altijd staan.

**Waarom een uitklap:** de 32 redenen in het gebouwde contract zijn kortste 98 tekens, mediaan 243, langste 1112. Op een scherm met vier onbeschikbaar-vakken is dat een muur waar niemand meer door leest, en dan verliest harde regel 8 juist zijn werking. Wat de regel eist is dat zichtbaar is *dát* er iets ontbreekt; dat blijft hier onverkort staan. De volle reden is één klik weg, en in het CFO-rapport staat ze altijd open (`Rapportknoppen.tsx` opent elke `<details>` voor het afdrukken).

**Waarom geen lengtegrens:** de eerste versie klapte alleen in boven 160 tekens, gekozen op diezelfde meting. De visuele steekproef liet binnen één ronde zien wat daaraan fout is: Frans is systematisch langer dan Nederlands, dus het kostenmodelvak stond open in het Nederlands (143 tekens) en ingeklapt in het Frans (163). Hetzelfde vak, twee structuren, afhankelijk van de taal van de lezer — precies het soort stille halfheid dat in dit platform al drie keer is opgeruimd. Eén regel is beter dan een slimme regel.

**Alternatief:** de reden splitsen op de eerste punt, zodat de eerste zin blijft staan. Verworpen: "bv.", "o.a." en "1 à 2%." breken een reden middenin een afkorting af, en dan staat er onzin op het scherm van de klant.

---

### 2026-08-18, De rangorde tussen de blokken loopt over typografie en lijnen, en één afdrukhaakje is daarvoor opgegeven

**Wat:** de blokken op een scherm hebben nu een expliciete visuele ladder — briefing, dan een onbeschikbaar-vak, dan een gewone kaart, dan de toelichting. De ladder staat uitgeschreven in `.claude/skills/huisstijl/SKILL.md`. Twee vormmiddelen zijn nieuw: één zwarte haarlijn onder de briefingkop (de enige zwarte lijn op wit in het platform; elders is een lijn warmgrijs) en een zwarte lijn van 2px links op een onbeschikbaar-vak, dezelfde lijn die in de briefing "actie nodig" markeert.

**Waarom niet met kleur:** een externe review vond terecht dat alles ongeveer even zwaar weegt, maar de gebruikelijke oplossing — rood voor alert — is hier verboden. Bordeaux is identiteit en nooit betekenis, en cijfers staan altijd in zwart. Blijft over: gewicht, grootte, witruimte, lijndikte en positie. Het bordeaux vlak uit de logogids is overwogen en niet gebruikt: die uitzondering geldt voor een cijfer op een vaste positie die nooit meeverhuist met goed of slecht nieuws, en in de briefing komen en gaan de punten.

**De prijs, expliciet:** de toelichting is geen paneel meer, en daarmee verliest ze het afdrukhaakje `paneel` en dus `break-inside: avoid`. In het CFO-rapport kan die lijst voorbehouden nu over een bladzijdegrens breken. Dat is aanvaard: een rand rondom een blok zonder zijpadding zet de tekst tegen de lijn aan, en van alle blokken op een scherm is de toelichting het blok dat een afbreking het beste verdraagt. Wie dit terugdraait, moet de padding meenemen.

**Alternatief:** de rangorde in het contract zetten (een `gewicht`-veld per blok) in plaats van in de componenten. Verworpen: de rangorde is een eigenschap van het ontwerp en niet van de data, en de UI mag over opmaak wél beslissen — alleen niet over cijfers.

---

### 2026-08-19, Een aangekondigde sluiting is geen achterstand, en het veld dat dat verwarde is hernoemd

**Wat:** de versheidsmelding onderscheidt nu drie soorten dagen zonder meting: **gemeten gesloten**, **gepland dicht** en **niet ingeladen**. Alleen de laatste is een achterstand die het platformbeheer moet nakijken. Tijdens een sluiting verschijnt in plaats daarvan een punt "De bakkerij is gesloten" met de begindatum, de reden en de eerste dag dat de zaak weer opengaat.

**Waarom:** het platform meldde tijdens de zomersluiting "10 dagen die niet uit de bronsystemen zijn ingeladen — de nachtelijke synchronisatie moet nagekeken worden", terwijl `gepland_dicht = True` staat voor 2026-08-01 t/m 2026-08-23 en er dus niets te laden was. Het beschuldigde zichzelf van veroudering omdat de bakkerij op vakantie is. Een externe reviewer concludeerde daaruit dat de cijfers achterlopen en noemde dat "dodelijk voor vertrouwen" voor een CFO-platform — begrijpelijk, en het was de duurste van al zijn opmerkingen. De fout zat op twee plaatsen (`canoniek._meetgat` en `kwaliteit._stand_dagelijks`) en op identieke wijze: beide telden een ongemeten dag zonder de kalenderkolom te lezen die ernaast stond en die `prognosevenster` al wél gebruikte.

**De rename is opzettelijk:** `Meetgat.niet_gemeten` heet nu `niet_ingeladen`. De betekenis veranderde (aangekondigde dagen zitten er niet meer in), en een gewijzigde betekenis onder een onveranderde naam is precies hoe deze fout kon blijven staan.

**Waarom `let_op` en niet `actie`, en waarom zonder `nodig`:** een sluiting is geen storing. Er is niemand die iets moet nakijken, dus het veld dat om een handeling vraagt blijft leeg. Zou de melding om actie vragen, dan hebben we de oorspronkelijke fout alleen van naam veranderd.

**Drempel `SLUITING_MIN_DAGEN = 3`:** een vaste wekelijkse sluitingsdag mag geen wekelijks briefingpunt opleveren. Dezelfde afweging als `sluitingsdagen.MIN_REEKS_DAGEN`. Vooruit gesimuleerd op de echte kalender: 18 aug geeft de sluitingsmelding, 24 aug zwijgt, 26 aug zwijgt (twee dagen, onder de drempel), 27 aug geeft wél een achterstandsmelding. De vangrail blijft dus werken.

**Alternatief:** de achterstandsdrempel simpelweg verhogen zodat een sluiting eronder blijft. Verworpen: dan verdwijnt ook een echte achterstand van tien dagen uit het zicht, en het onderscheid dat het platform wél kan maken blijft ongebruikt. Tweede alternatief: de melding in de UI onderdrukken tijdens een sluiting. Verworpen wegens harde regel 4 — dit is een bevinding en die hoort in de berekeningslaag, niet in een component.

**Onvertaald gebleven:** de reden ("Jaarlijkse sluiting") komt uit `data/config/sluitingsdagen.json` en staat dus ook in de Franse tekst in het Nederlands, zoals de wachtertoelichtingen. Aangeleverde tekst vertalen we niet.

---

### 2026-08-19, De kosteninvoer schrijft naar de database via één functie, niet via grants

**Wat:** het kostenmodelformulier op Instellingen schrijft onder `CONTRACT_BRON=db` naar `kosten_criterium` en `kosten_waarde`, via één `security definer`-functie `bewaar_kostenmodel(jsonb, text)` uit migratie 009. Daarmee vervalt de onbeschikbaar-melding op de gehoste omgeving — **niet weggemoffeld, maar vervallen omdat de reden vervallen is.** Dit vervangt de noot in de entry van 18 augustus die zegt dat de schrijfroute nog niet bestaat.

**Waarom een functie en geen schrijfrechten:** het platform op Vercel heeft geen Postgres-verbinding — `SUPABASE_DB_URL` staat daar bewust niet en dat blijft zo. Het schrijft via PostgREST, en daar is één verzoek één transactie. Het kostenmodel bewaren raakt twee tabellen, en dat moet alles-of-niets zijn: anders bestaat er een moment met criteria weg en waarden nog niet geschreven, en dan staat er een kostenmodel in de database dat niemand heeft ingevuld. Eén functie is één verzoek en één transactie. Het is bovendien strakker dan grants: `service_role` krijgt nog steeds geen `insert`, `update` of `delete` op die tabellen, alleen uitvoerrecht op deze ene functie — waarmee de regel van migratie 008 ("select en niets meer") overeind blijft.

**De val die dichtgezet is:** een nieuwe functie krijgt in Postgres standaard uitvoerrecht voor `public`. Bij `security definer` betekent dat: `anon` — de publiceerbare sleutel, die in elke JavaScript-bundel zit — mag het kostenmodel van de klant overschrijven. De migratie trekt daarom eerst álle rechten in en geeft daarna één rol uitvoerrecht. `set search_path = ''` sluit de tweede val (een aanroeper die zijn eigen `public` vóór de echte zet); alle tabellen staan volledig gekwalificeerd. Gemeten in `tests/test_db_echt.py`: `service_role` mag de functie en niet de tabel, `anon` mag niets.

**De bug die dit blootlegde, en die er al stond:** `scripts/contract_bouw.py:_briefings` gaf `kosten_model or {}` door aan `berekening.marge_per_groep`, die een dict verwacht. Met een écht kostenmodel wierp dat `AttributeError: 'Kostenmodel' object has no attribute 'get'` — **de hele contractbouw viel om, in beide talen.** Onvindbaar tot vandaag, want `kosten_model` was altijd `None` en `None or {}` is een dict. Er is dus nooit een contract met kosten gebouwd. Dat maakt de vondst belangrijker dan de functie: zonder deze reparatie zou de eerste beheerder die kosten invulde het platform hebben gesloopt.

**De zwakste schakel, expliciet:** herrekenen kan de gehoste omgeving niet — daar staat geen Python en geen canonieke data. Na het opslaan zegt het scherm dat de cijfers bij de volgende berekening volgen. Maar **de nachtelijke cron staat uit** (en moet uit blijven tot de krimpwacht ook op inhoudsverarming let), dus tot dan moet iemand `make sync` draaien. De tekst liegt niet — ze noemt die tweede weg — maar dit is de plek waar de lus vandaag rammelt.

**Alternatief:** `service_role` gewoon `insert`/`delete` geven op de twee tabellen. Verworpen: dan is er geen transactiegrens over twee tabellen, en het opent een schrijfpad dat verder reikt dan deze ene handeling. Tweede alternatief: schrijven over een Postgres-verbinding vanuit Vercel. Verworpen: dan moet het databasewachtwoord daar staan, en dat is precies de secret die er weg moet blijven.

---

### 2026-08-19, Eén constructie van de productievoorspeller, en de heropeningscorrectie definitief afgewezen
**Wat:** `BASIS`, `KENMERKEN`, `prognosekalender`, `open_of_gepland_open` en `bouw_voorspeller` staan nu in `bakkerij/model/productie.py`. De contractbouw, de diagnose en het backtest-rapport lenen ze daar alle drie; geen enkel script bouwt de voorspeller nog na. Met die ene constructie is de heropeningscorrectie opnieuw gemeten en **afgewezen**.
**Waarom:** er waren drie constructies, en het verschil zat niet in het model maar in één vlag. De diagnose leidde "de eerste open dagen ná een vakantie" af uit `reeks.index` (alleen gemeten dagen), productie uit `open_of_gepland_open` (de hele kalender). Daardoor gaven twee rapporten over hetzelfde kenmerk een tegengesteld verdict — +0,12 punt tegen −0,002 — en kon er twee sessies lang niets eerlijk beslist worden. Met één constructie zegt de diagnose nu hetzelfde als E4: totaal −0,01 punt, de ná-vakantiedagen −0,24 punt, de galette-dagen −0,32 punt. De kandidaat wint nergens. Vóór de refactor rapporteerde datzelfde script +2,45 punt op precies die dagen; die winst was een artefact van de vlaggenconstructie, niet van het model.
**Gemeten:** de productiecijfers bewogen niet — 343 dagen out-of-sample, 7,8 % WAPE, −119 €/dag, en alle veertien contractantwoorden bit voor bit gelijk op het bouwmoment na. Dat is precies wat een refactor hoort te doen.
**Alternatief:** de constructies laten staan en op gevoel kiezen welk rapport gelijk had. Verworpen: dat is harde regel 7 met extra stappen. Wat níét is opgelost is januari — zie het blok hieronder.

---

### 2026-08-19, Driekoningen blijft open, en dat wordt niet verhuld
**Wat:** de galette-/Driekoningenpiek blijft de grootste onopgeloste fout van de prognose. Er is vandaag niets aan gerepareerd en er wordt ook niets aan geschat.
**Waarom:** januari draagt 24,2 % van de totale jaarfout en herbergt 10 van de 20 grootste missers; de drie galette-dagen zelf staan op 46,1 % WAPE en −10.640 €/dag. Elke kandidaat die erop gericht was, is gemeten en verloor: een `vroege_januari`-factor maakt januari 1,22 punt slechter en 1 t/m 15 januari 2,39 punt; de heropeningscorrectie laat de galette-dagen onaangeroerd (−0,32 punt). De oorzaak is structureel en niet oplosbaar met modelwerk: de kassahistoriek begint in 2025, dus er is precies één januari in het venster. Een factor die op de enige januari gepast wordt, kan niet out-of-sample op een andere januari getoetst worden, en dan is ze een mening (harde regel 7).
**Wat het wél zou oplossen:** een tweede januari in de historiek (januari 2027, dus na de oplevering), of eerder de agenda-feed (vraag 46) met de galette-dagen als evenement — dan is het een kalenderkenmerk in plaats van een geschatte seizoensvorm.
**Alternatief:** de piek toch met een handmatige factor opvangen. Verworpen: dat is precies het soort cijfer waar dit platform geen vertrouwen mee verdient.

---

### 2026-08-19, De sluitingslijst gaat in git, de rest van `data/` niet
**Wat:** `data/config/sluitingsdagen.json` is verhuisd naar `config/sluitingsdagen.json` en staat daarmee in de repo. De commit-wachter kreeg er één uitzondering bij, met de reden erbij.
**Waarom:** `data/` is gitignored omdat daar klantdata staat (harde regel 2). Deze lijst is geen klantdata: datums waarop de zaak dicht is, en een zakelijke reden. Geen transacties, geen personen, geen bedragen. Zolang ze buiten git stond, kon de nachtelijke synchronisatie op geen enkele GitHub-runner slagen — zonder haar verdwijnt `gepland_dicht` uit de kalender, en dan meldt het platform een geplande sluiting als achterstand. Dat is precies de fout die op 19 augustus is gerepareerd, langs de achterdeur weer binnen.
**Het risico, en wat ertegen staat:** het veld `reden` is vrije tekst en kan een persoonlijk gegeven dragen ("Sophie ziek"). Eenmaal gecommit staat dat voorgoed in de geschiedenis. Daarom staat er nu een waarschuwing in het bestand zelf: hou de reden zakelijk, of laat hem leeg — het veld mag leeg.
**Alternatief:** de lijst naar de database, zoals het kostenmodel (migratie 011 plus een beheerscherm). Niet verworpen maar niet nodig: dat is een dag werk voor een bestand van één regel dat door ons wordt bijgehouden, en het lost hetzelfde op. Blijft de betere vorm zodra de bakkerij hem zelf wil beheren.

---

### 2026-08-19, Een bevroren kanaal wordt uit de database teruggelezen
**Wat:** ontbreken de TGTG-bestanden en staat `CONTRACT_BRON=db`, dan haalt de canoniekbouw dat kanaal terug uit `fact_verkoop` en `fact_kanaalkost` in plaats van te stoppen (`bakkerij/db/bevroren.py`).
**Waarom:** de bronbestanden zijn pdf's met klantdata en staan dus buiten git; op een runner bestaan ze niet. En ze hoeven daar ook niet te zijn: sinds blok 9 op 17 augustus geschrapt is, krijgt TGTG geen nieuwe aanvoer meer, dus wat in de database staat ís de historiek. Wat bevroren is, hoeft niet elke nacht opnieuw uit de bron gebouwd te worden.
**Wat het níét is:** een tweede waarheid. Bestaan de bestanden, dan blijven zij de bron en wordt deze weg niet geraakt. Er wordt niets herberekend — ook de commissiewig komt terug zoals hij erin ging, want die twee keer afleiden zou de commissieregel op twee plaatsen zetten.
**Gemeten:** 1.872 regels, € 106.415,75, rij voor rij gelijk aan de bestandsroute; kanaalkost tot op vier decimalen gelijk over 83 maanden.
**Alternatief:** de bestanden meesturen naar de runner (kan niet, harde regel 2) of het kanaal op de runner laten vallen (dat is stil dataverlies, en precies wat de krimpwacht moet tegenhouden).

---

### 2026-08-19, De dodemansknop leeft in de database, niet in het contract
**Wat:** het oordeel of de nachtelijke synchronisatie nog leeft, staat in een databaseview (`public.sync_stand`, migratie 010) en niet als veld in het contract. Het platform toont alleen wat eruit komt.
**Waarom:** het contract wordt gebouwd dóór de sync. Op het moment van bouwen staat de eigen run op 'bezig', dus een contractveld zou voor eeuwig "loopt nu" zeggen — ook drie nachten nadat er niets meer gedraaid heeft. Een oordeel over versheid dat zelf bevriest, is geen dodemansknop. Het moet dus vallen op het moment van kijken, en dat kan maar op twee plaatsen: in de UI of in de database. In de UI mag het niet (harde regel 4: een drempel in een component bestaat niet voor de app van fase 2 en niet voor een export). Blijft de database.
**Drempels, en waarom zo:** 36 uur nog 'goed' (de planner van GitHub Actions is best effort; één gemiste nacht mag geen alarm zijn, twee wel), drie dagen 'fout' (de grens die de opdracht zelf noemde), drie uur op 'bezig' is gestrand (de job heeft een timeout van 90 minuten, dus daarboven loopt hij niet meer).
**Alternatief:** het oordeel in de UI berekenen uit een contractveld met de ruwe tijdstippen. Verworpen: dat is rekenen in de presentatielaag, en dan bestaat de regel alleen voor dit ene scherm.

---

### 2026-08-19, Wat mag inklappen, en wat nooit
**Wat:** er is een uitklapbare kaart (`KaartUitklap`) naast de gewone. Verdieping mag dicht: modelkaart, detailtabellen, het weekdagprofiel, het kostenmodelformulier. **Kerncijfers en onbeschikbaar-vakken klappen nooit in.**
**Waarom:** dat er iets ontbreekt is precies wat zichtbaar moet blijven (harde regel 8). Een onbeschikbaar-vak achter een klik is functioneel hetzelfde als het weglaten, en dat is nu juist wat dit platform niet doet. Voor de rest geldt het omgekeerde: een scherm dat alles tegelijk toont, dwingt de lezer elke dag door verantwoording te scrollen die hij één keer wil nalezen.
**De modelkaart draagt geen cijfer in haar kop.** Eerste versie wel — de gemeten afwijking, zodat de kaart dicht geklapt toch verantwoord bleef. Maar dat cijfer kwam uit het trackrecord (8,1 %, laatste 28 dagen) terwijl de kaart zelf 7,8 % noemt (de hele backtest): twee metingen onder één label, en dicht geklapt zag je juist de verkeerde. Een rij uit `modelkaart.rijen` kiezen kan niet — die labels komen vertaald uit het contract, en op een label zoeken is raden. Het trackrecord staat erboven, open, en toont de meting voluit; harde regel 7 vraagt dat ze op het scherm staat, niet dat ze er twee keer staat.
**Alternatief:** een `sleutel` per modelkaartrij in het contract, zodat de UI de WAPE-rij zonder raden kan aanwijzen. Netter, en de aangewezen weg als die kop er ooit toch moet komen — nu niet gedaan omdat het een contractwijziging is voor iets wat het scherm al toont.

---

### 2026-08-19 (nacht), Welke kaart dicht staat: proza beslist, niet het onderwerp
**Wat:** de vorige beslissing zei *wat* mag inklappen. Ze zei niet wanneer, en het gevolg was dat zeven van de acht uitklapbare kaarten op `standaardOpen` stonden: het mechanisme werkte, maar er klapte niets in. De regel is nu: **wat proza draagt, klapt dicht; wat alleen een grafiek is, blijft open.** Losse toelichtingsalinea's binnen een open kaart gaan achter `MeerInfo`.
**Waarom een regel over de vórm en niet over het onderwerp:** elke andere grens die we probeerden, moest per blok bevochten worden ("is een maandritme dagelijks of maandelijks?"), en dat is precies het soort keuze dat over een half jaar willekeurig oogt. De tekstlast is bovendien meetbaar en het onderwerp niet. En de regel plaatst de vólgende kaart vanzelf, zonder dat er opnieuw over vergaderd hoeft te worden.
**Eén uitzondering, met eigen reden:** de margestaaf klapt dicht terwijl ze geen letter proza draagt. Ze toont dezelfde gegevens als de tabel eronder, en van die twee is de tabel de bruikbare — dat is dubbeling, geen verdieping.
**Wat open blijft, en dat is de grens:** kerncijfers, elk onbeschikbaar-vak, de briefing, en het trackrecord van de prognose. Dat laatste is niet vrijblijvend: de modelkaart eronder mág alleen dicht omdát het trackrecord erboven de gemeten afwijking voluit toont (harde regel 7). Zet je het trackrecord dicht, dan valt de grond onder de vorige beslissing weg.
**Alternatief:** de `Blok`-helper op Dagoverzicht verbreden zodat ook die kaarten konden inklappen. Netter van vorm — het heft een echte inconsistentie op, want vier gelijksoortige grafiekblokken werden op twee manieren behandeld. Toch niet gedaan: het voegt een tweede mechanisme toe waar `MeerInfo` op dezelfde alinea's hetzelfde bereikt, en de opdracht was uitdrukkelijk om geen verse complexiteit te introduceren. Blijft staan als de aangewezen weg zodra die kaarten méér gaan dragen dan één alinea.

---

### 2026-08-19 (nacht), Een bevroren bron wordt niet tegen de klok gemeten
**Wat:** TGTG krijgt de status `bevroren` in plaats van te verouderen naar `achter`. Die status weegt als goed, levert geen briefingpunt, en telt niet mee in `ergste` — het oordeel dat de voettekst van elk scherm draagt. Een nieuwe constante `BEVROREN` naast het bestaande `BEKEND_AFWEZIG`.
**Waarom, en waarom dit geen wegmoffelen is:** het kanaal wordt niet meer aangevuld (blok 9 geschrapt, 17 augustus, op vraag van de opdrachtgever), dus de afstand tot vandaag groeit elke nacht zonder dat er iets verandert. Op 14 september 2026 — achttien dagen na de oplevering — zou het kanaal de lat van 45 dagen passeren en daarna voorgoed 'achter' staan, met een briefingpunt op elk scherm en een gele voettekst op elk scherm. De module verbiedt dat zelf al met zoveel woorden ("een alarm dat permanent afgaat, is geen alarm"), en het bestaande `BEKEND_AFWEZIG` past die regel al toe op Deliveroo. Dit is dezelfde regel op de keerzijde: die bron kwam nooit, deze komt niet meer.
**Wat er zichtbaar blijft:** de bron staat mét haar jongste meetdag en de volledige reden in het bronnenlijstje op Instellingen, in beide talen. Harde regel 8 gaat over het tonen van wat er ontbreekt, en dat gebeurt — wat verdwijnt is uitsluitend het alarm.
**Alternatief 1:** de lat van 45 dagen verhogen. Verworpen: dat verplaatst de datum en lost niets op; over een jaar staat hij er alsnog.
**Alternatief 2:** de bevriezingsdatum als gegeven in het contract of de database zetten, zodat het platform zelf ziet dat er weer aanvoer is. Netter, en nodig zodra er meer dan één bevroren kanaal bestaat. Nu niet gedaan: het is één kanaal en één regel, en de constante draagt in haar commentaar de instructie om het kanaal er weer uit te halen zodra er aanvoer komt. Wat je ervoor terugkrijgt is een tweede plek waar de waarheid over dit kanaal staat.
**Wat dit níét dekt:** komt er onverwacht tóch nieuwe TGTG-data binnen, dan blijft de status 'bevroren' en zwijgt het platform daarover. Dat is bewust — de historiek is dan gewoon langer — maar het is de rand van deze beslissing.

---

### 2026-08-19 (nacht), Eén test mag wél de klok lezen
**Wat:** `tests/test_vakanties.py` leidt zijn dekkingsgrens af uit `datetime.now(tz=BRUSSEL).date()` in plaats van uit een vaste datum. Dat is de enige test in de suite die dat doet, en dat blijft zo.
**Waarom deze uitzondering verdedigbaar is:** overal elders is "vandaag" gif in een test — het maakt de uitkomst afhankelijk van wanneer je hem draait, en dan meet je de klok in plaats van de code. Hier is de klok het ónderwerp. `schoolvakanties.json` is data die vanzelf veroudert; de code eromheen niet. Een vaste grens meet één keer iets en daarna niets meer: er stond "≥ 31 augustus 2027", en vanaf september 2027 zou die assert groen blijven op een kalender die het lopende schooljaar niet meer dekt, want de grens ligt dan in het verleden. De test hoort juist rood te worden op de dag dat `make vakanties` had moeten draaien.
**Nagemeten:** groen vandaag en op 1 september 2026, rood vanaf 1 september 2027 — precies het bedoelde moment. `date.today()` kon niet (ruff DTZ011), vandaar de expliciete tijdzone.
**Wat het níét vervangt:** een rode test na de oplevering wordt alleen gezien door wie de tests draait, en dat is na de overdracht niemand met zekerheid. De menselijke kant staat daarom apart in `beheerdraaiboek.md` onder "Twee datums waarop iets ophoudt", met de meting erbij dat de OpenHolidays-API het Franstalige regime op 19 augustus 2026 zelf nog niet verder publiceerde dan 9 mei 2027 — het is dus een wachtstand en geen vergeten commando.
**Alternatief:** de grens elk jaar met de hand ophogen. Verworpen om dezelfde reden als hierboven: dat is precies de handeling die niemand doet, en het falen ervan is onzichtbaar.

---

### 2026-08-19 (nacht), Een sluiting is invoer, geen modelkenmerk
**Wat:** de prognose voorspelt op 25 december een gewone vrijdagomzet, en dat wordt níét opgelost door `feestdag` aan `productie.KENMERKEN` toe te voegen. Het wordt opgelost door invoer: welke dagen de zaak dicht is (vraag 64 eenmalig, vraag 65 duurzaam).
**Waarom dit onderscheid ertoe doet:** het zijn twee verschillende dingen die makkelijk door elkaar lopen. Een feestdag*factor* is een uitspraak over gedrag — "op de dag vóór Kerstmis wordt er meer brood gekocht" — en die hoort gebackteste te worden. Dat is gemeten en afgewezen: elke feestdagnaam komt hoogstens twee keer voor in de anderhalf jaar kassahistoriek (Odoo begint in 2025), en een factor op twee waarnemingen is nergens tegen te toetsen (harde regel 7). Een *sluiting* is geen uitspraak over gedrag maar een feit over de zaak: op een dag dat de deur dicht is, valt er niets te voorspellen — niet minder, maar niets. Dat feit hoort dus niet in het model maar in de kalender, en het is per definitie niet uit de data af te leiden voor een dag die nog moet komen.
**Gevolg voor de vorm van de oplossing:** een gesloten dag valt uit het venster (dat mechanisme bestaat en werkt), en het platform hoeft er geen enkele parameter voor te leren. Het heeft alleen iemand nodig die het zegt.
**Wat dit níét uitsluit:** komt er ooit een tweede en derde januari in de historiek, dan wordt een feestdagfactor wél toetsbaar en is dat een aparte, gemeten beslissing. De galette-/Driekoningenpiek wacht daar al op.
**Alternatief:** aannemen dat een bakkerij op de wettelijke feestdagen dicht is en die dagen automatisch overslaan. Verworpen, en niet uit voorzichtigheid: bij Renard is 6 januari juist een van de drukste dagen van het jaar, en veel bakkerijen zijn op feestdagen open. Het zou bovendien een aanname over de zaak in code vastleggen, en harde regel 6 vraagt dat zoiets bevestigd wordt door wie het weet.

---

### 2026-08-19 (dagsessie), De sluitingskalender is gebouwd vóór de schriftelijke bevestiging van vraag 65

**Wat:** Kwinten heeft beslist de sluitingskalender (migraties 011–014, het scherm Sluitingsdagen) op 19 augustus meteen te bouwen, in plaats van eerst op Liens schriftelijke bevestiging van vraag 65 te wachten zoals de wijzigingsprocedure normaal vraagt. Vraag 65 is daarmee een bevestiging achteraf geworden: akkoord dat dit binnen de opdracht valt, in plaats van een go/no-go vooraf.
**Waarom:** het enige openstaande punt waarvan de datum bekend was waarop het zichtbaar misgaat, is 19 december 2026 — de dag waarop de kerstsluiting binnen het prognosevenster van 60 dagen komt. Op de bevestiging wachten kon dat venster voorbij laten lopen; het bouwwerk kostte één dag, ruim onder de eerdere raming van 1,5 dag, en liet de eenmalig overgenomen bestandslijst (23 dagen zomersluiting) als vangnet intact zodat de kalender niet leeg begon.
**Alternatief:** wachten met bouwen tot Lien vraag 65 schriftelijk bevestigt. Verworpen: de procedure beschermt tegen werk dat niet nodig blijkt, maar hier stond een harde datum tegenover een wachtronde waarvan de duur niet vaststond.

---

### 2026-08-19 (dagsessie), Rangorde tussen de drie sluitingsbronnen: agenda > database > bestand, en binnen de database wint de uitspraak van de weekregel

**Wat:** drie bronnen kunnen iets over dezelfde dag zeggen. De agenda (iCal, vraag 46) gaat voor op de database (het scherm Sluitingsdagen), die gaat voor op het bestand (`sluitingsdagen.json`, eenmalig overgenomen). Een dag die de agenda dicht noemt, blijft dicht óók als de database hem bevestigd open noemt — dat conflict wordt gemeld (`agenda_conflicten`) en niet stil beslecht. Een dag die de database bevestigd open noemt, knipt een dicht-dag uit de bestandslijst weg (`zonder_dagen`). Binnen de database zelf wint een uitspraak over één specifieke dag altijd van de wekelijkse regel: "elke maandag dicht" plus "maandag 6 januari bevestigd open" betekent dat 6 januari open is.
**Waarom:** de agenda komt rechtstreeks van de bakkerij, de database van de beheerder via het scherm, het bestand is de oudste en eenmalige invoer — de rangorde volgt wie het meest recent en het meest specifiek over een dag heeft gesproken. Een uitspraak over precies één dag is per definitie specifieker dan een regel die een hele weekdag dekt.
**Gevolg:** `bakkerij/sluitingskalender.py` (rangorde en conflictdetectie) en `scripts/canoniek_bouw.py` (leesvolgorde onder `CONTRACT_BRON=db`).
**Alternatief:** de bronnen zonder vaste volgorde laten samenlopen, of de laatst gelezen bron stil laten winnen. Verworpen: dat maakt een tegenspraak tussen twee bronnen onzichtbaar, en harde regel 8 vraagt juist dat zo'n tegenstelling gemeld wordt in plaats van weggewerkt.

---

### 2026-08-19 (dagsessie), Het scherm Sluitingsdagen leest live uit de database, en de opslag weigert bij een onleesbare basis

**Wat:** het scherm Sluitingsdagen leest de bewaarde uitspraken rechtstreeks uit de tabellen van migratie 011, niet uit het contract — een bewuste uitzondering op "alles komt uit het contract" (harde regel 4), met hetzelfde argument als de syncstand van 19 augustus: wie net een feestdag bevestigd heeft, moet zijn eigen invoer meteen terugzien en niet pas na de volgende nachtelijke contractbouw. De server-actie (`bewaarSluitingen`) voegt de nieuwe formulierinvoer samen met die bewaarde stand vóór ze terugschrijft, en weigert de opslag zodra die stand niet leesbaar is.
**Waarom:** de schrijffunctie (migratie 012) vervangt bij elke opslag de volledige kalender in één transactie, maar het formulier beheert alleen de kandidaten van dit jaar, de eigen periodes en de regel — uitspraken daarbuiten (oudere feestdagen, de overgenomen bestandslijst) moeten blijven staan. Samenvoegen met een basis die niet gelezen kon worden, zou die eerder bewaarde uitspraken zonder dat iemand het ziet kunnen wissen.
**Alternatief:** bij een onleesbare stand toch opslaan, bijvoorbeeld leeg beginnen. Verworpen om bovenstaande reden — dat is precies het soort stille dataverlies dat harde regel 8 en de rest van dit platform uitsluiten.

---

### 2026-08-19 (dagsessie), `delete ... where true` in de twee schrijffuncties, na een gehoste schrijfroute die nooit gewerkt had

**Wat:** de twee `security definer`-schrijffuncties die de gehoste omgeving gebruikt (`bewaar_kostenmodel`, `bewaar_sluitingskalender`) doen voortaan `delete ... where true` in plaats van een kaal `delete` (migratie 014).
**Waarom:** Supabase laadt op de PostgREST-verbinding de bibliotheek pg-safeupdate, die elk delete zonder where-clausule weigert, ook binnen een definer-functie. De eerste opslagpoging vanaf het nieuwe scherm kwam terug met "400, DELETE requires a WHERE clause". Nagemeten bleek `bewaar_kostenmodel` (migratie 009, gebouwd op 19 augustus) op de gehoste route om exact dezelfde reden nooit gewerkt te hebben: sinds die functie bestaat heeft geen enkele beheerder ooit met succes een kostenmodel opgeslagen, en dat was nooit opgevallen omdat de kostentabellen leeg bleven. Een lokale Postgres en de CI-container laden pg-safeupdate niet, dus de 30 db-tests tegen een echte Postgres (beslissing van 18 augustus, "De databasesuite draait tegen een echte Postgres") bleven daar groen terwijl de gehoste schrijfroute stuk was.
**Gevolg:** dit scherpt de beslissing van 18 augustus aan: een echte Postgres in CI bewijst dat schema en rechten kloppen, maar niet dat de gehoste route werkt zodra die omgeving een bibliotheek laadt die de testdatabase niet heeft. Beide schrijfroutes zijn na deze reparatie apart tegen de echte gehoste omgeving bewezen (bevestigen, bewaren, herladen, terugzetten).
**Alternatief:** wachten tot iemand het op de echte gehoste omgeving zou proberen. Dat is exact wat er gebeurde — bij toeval, bij de eerste opslag vanaf een nieuw scherm — en de fout had net zo goed nooit ontdekt kunnen worden, met een kostenmodel dat op Instellingen leek te werken en op de server nooit opsloeg.

---

### 2026-08-19 (dagsessie), Het sluitingsvoorbehoud op de prognose werkt per dag, niet meer over het hele venster

**Wat:** het sluitingsvoorbehoud op het prognosescherm noemt voortaan de onbeantwoorde dagen zelf (`sluitingskalender.onbekende_dagen`) in plaats van één tekst over het hele venster van de bestandslijst. Drie gevallen, drie teksten: geen enkele sluitingsbron (de oude, algemene tekst), één of meer onbeantwoorde dagen (die dagen bij naam, met de handeling erbij), of alles beantwoord (het voorbehoud vervalt). Binnen het bereik van de bestandslijst claimt de tekst geen dekking verder dan die lijst kan waarmaken: alleen een uitspraak per dag telt als bevestiging, het bereik van de lijst zelf is een bereik en geen bevestiging.
**Waarom:** de oudere tekst zei over het hele venster van de bestandslijst "voor deze dagen is de stand aangeleverd en niet aangenomen", en dat bleek op 15 augustus 2026 aantoonbaar onwaar: de zomersluiting stond in het bestand als 17 tot 23 augustus terwijl ze op 1 augustus al begon, en over 15 en 16 augustus zelf — waarover niemand ooit iets gezegd had — beweerde die zin dat de stand aangeleverd was. Die les (geen dekkingsclaim die verder gaat dan een bron kan waarmaken) blijft nu overeind terwijl het voorbehoud verfijnt van "over het venster" naar "per dag", nu de database een tweede bron van uitspraken is naast de bestandslijst.
**Gevolg:** `bakkerij/contract.py::prognose` krijgt de parameter `bevestigde_dagen`; er zijn drie teksten in plaats van twee, in beide talen.
**Alternatief:** de oude, algemene venstertekst behouden zodra er wél databaseuitspraken bijkomen. Verworpen: dat zou de precisie die de database net mogelijk maakt (een enkele bevestigde dag) laten liggen, en de lezer een grovere waarschuwing tonen dan wat er werkelijk bekend is.

---

### 2026-08-19 (dagsessie), Geen eigen jarengrens in de weekregel-uitrol — de kalender begrenst zelf

**Wat:** `regel_dagen()` (`bakkerij/sluitingskalender.py`), die een wekelijkse sluitingsregel naar losse dichte dagen uitrolt, draagt bewust geen eigen grens op de omvang van het bereik. Een eerdere versie tijdens de bouw van vandaag had wél een grens van vijf jaar, en die viel om bij de eerste run tegen de echte kalender — die beslaat op 19 augustus 2026 ruim zeven jaar (de volledige kassahistoriek plus het prognosevenster).
**Waarom:** de aanroeper (de canoniekbouw) geeft `van` en `tot` al mee en begrenst het bereik dus al; een tweede grens in de functie zelf zou de bouw net laten omvallen op precies de data waarvoor de functie bestaat. De lus springt per week naar de juiste weekdag in plaats van dag voor dag te proberen, dus ook decennia blijven goedkoop — er was geen prestatiereden om de grens te houden.
**Alternatief:** de grens optrekken naar bijvoorbeeld twintig of vijftig jaar in plaats van haar weg te halen. Verworpen: elke vaste grens is een tweede plek die met de kalender moet meegroeien, terwijl de aanroeper de begrenzing al draagt en dat nooit uit de pas kan lopen.

---

### 2026-08-19 (avondsessie), `gedeeld` op een briefingpunt betekent "staat op elk scherm", niet "komt vaker voor"

**Wat:** een briefingpunt draagt sinds vandaag `gedeeld`, en het rapport toont zo'n punt alleen in het eerste onderdeel. Het merk is voorbehouden aan de punten uit `_versheidspunten` (de sluiting, de achterstand), die door alle zes de schermfuncties gebouwd worden. Het bronpunt over Deliveroo herhaalt zich óók — op Verkoopkanalen en op Instellingen — maar krijgt het merk uitdrukkelijk niet.
**Waarom:** de ontdubbeling in het rapport is een CSS-regel op positie (`.rapportdeel ~ .rapportdeel`), en die verbergt een gemerkt punt in élk onderdeel behalve het eerste, ongeacht of het daarvóór al ergens stond. Dat is alleen veilig zolang het eerste onderdeel het punt zeker draagt. Merk je een punt dat op twee van de zes schermen staat, dan verdwijnt het uit elk rapport dat met een van de andere vier begint — en in dit geval was dat een punt met status 'actie' over data die dagelijks onherstelbaar verloren gaat. Liever tweemaal in een document dan nul keer (harde regel 8).
**Alternatief:** alle herhaalde punten merken en ze in het rapport één keer bovenaan tonen, in een eigen blok dat de unie van de gekozen contracten leest. Dat lost beide gevallen op, maar het vergt dat de rapportpagina alle gekozen antwoorden zelf inlaadt en samenvoegt — een tweede samenstelling naast de schermen, precies wat de rapportpagina bewust níét is. Genoteerd als kandidaat, niet gebouwd.

---

### 2026-08-25, De Deliveroo-parser wacht op echte CSV's; het skelet komt nu

**Wat:** blok 5 (de Deliveroo-parser) wordt in twee stukken gebouwd. Nu: de foutklasse, de vorm van de twee rapporten, de mappenconventie in code, de bereikcontrole, de dekkingsmeting, en een `make deliveroo` die inventariseert. Later, op de dag dat de eerste echte export uit Partner Hub binnenkomt: het lezen zelf. De drie beslissingen hieronder horen bij dat tweede stuk en zijn nú genomen, zodat de bouwdag geen denkdag is.
**Waarom:** de les van de TGTG-parser is dat de vorm van echte documenten verrast — drie datumnotaties over zeven jaar, drie namen voor dezelfde artikelregel, een euroteken dat vóór, achter of nergens staat. Een parser op een bedachte CSV bewijst alleen dat hij de verzinner begrijpt, en je bouwt hem daarna een tweede keer. Wat wél nu kan, is alles dat niet van de documentvorm afhangt: de conventie waar de bestanden moeten staan, de controle die dag/maand-omwisseling betrapt, en de meting die zegt of de twaalf maanden compleet zijn.
**Gevolg:** `bakkerij/sources/deliveroo_parse.py` (skelet, twee werkende controles), `scripts/deliveroo_extract.py` (inventaris, schrijft niets), `tests/test_deliveroo_parse.py`, `make deliveroo` (bewust niet in `alles`). `parse_items_sold` en `parse_orders` heffen `NotImplementedError` met de weg erin — geen lege lijst, want dat zou een leeg kanaal op nul zetten.
**Alternatief:** het geheel uitstellen tot de CSV's er zijn. Verworpen: de mappenconventie is nu nodig, want ze bepaalt wat de zaakvoerder moet doen bij het downloaden, en dat gesprek loopt nu. Dan is die conventie beter code dan een regel in een document.

---

### 2026-08-25, De ordercommissie wordt over de artikelregels verdeeld, en welke route dat gebeurde staat in de uitvoer

**Wat:** netto-omzet per product-dag voor Deliveroo komt uit een toewijzing van de commissie per bestelling over de artikelregels van diezelfde bestelling. Dragen Items Sold en Orders een gemeenschappelijke order-sleutel, dan: join, en pro rata naar subtotaal. Dragen ze die niet, dan: een effectief dagtarief (de dagcommissie gedeeld door de dagbruto), pro rata toegepast. Welke van de twee gebruikt is, hoort in de uitvoer te staan.
**Waarom:** dit is het werk dat bij TGTG niet bestond en dat de raming van een halve dag scheef zet. TGTG rekent één vast tarief per pakket, af te lezen van de maandfactuur; Deliveroo rekent per bestelling terwijl de omzet per artikel staat. Zonder toewijzing is er geen marge per product op dit kanaal. De tweede route is op dagniveau exact goed en per product een benadering — bruikbaar, maar niet hetzelfde, en het verschil bepaalt of een uitspraak over de marge per product verdedigbaar is. Een stille keuze tussen die twee is precies het soort verschil dat niemand naast elkaar legt tot het te laat is.
**Gevolg:** de probe van drie dagen (beide rapporttypes, één bereik) beslist welke route het wordt, en is daarom de eerste handeling — nog vóór de volledige download van twaalf maanden. De raming voor het tweede stuk is 0,5 dag mét sleutel en 1 à 1,5 dag zonder.
**Alternatief:** alleen het dagtarief bouwen en de marge per product op dit kanaal niet aanbieden. Blijft de terugvaloptie als de sleutel er niet is; niet als eerste keuze, want de sleutel is gratis als hij bestaat.

---

### 2026-08-25, `fact_kanaalkost` blijft per maand, ook voor Deliveroo

**Wat:** de kanaalkost van Deliveroo wordt naar maand geaggregeerd en gaat in de bestaande tabel (`kanaal | maand | stuks | bruto_per_stuk | commissie_per_stuk | inhouding_pct`). Geen migratie, geen dagniveau voor één kanaal. De check-constraint van migratie 002 laat `deliveroo` al toe en `db_laad.bereid_kanaalkost` geeft de kanaalkolom al door, dus de databasekant vraagt niets.
**Waarom:** het schemacommentaar zegt "per maand, omdat dat het niveau is waarop TGTG zijn tarieven zet". Bij Deliveroo kán het per dag, want daar is de commissie geen tarief maar een uitkomst. Toch niet: het kanalenscherm spreekt in maanden, en één kanaal op dagniveau maakt de twee onvergelijkbaar op precies het scherm dat ze naast elkaar zet.
**Gevolg:** `commissie_per_stuk` betekent voor de twee kanalen niet hetzelfde — bij TGTG een tarief, bij Deliveroo een gemeten gemiddelde. Dat hoort in de docstring van `kanaalkost_deliveroo` te staan en niet in iemands hoofd, want wie er later een voorspelling op bouwt, moet het weten.
**Alternatief:** de tabel uitbreiden met een dagniveau. Verworpen voor fase 1: het levert geen scherm en het maakt de twee kanalen onvergelijkbaar. De ruwe ordercommissie blijft in de tussenbestanden staan, dus een latere verfijning gooit niets weg.

---

### 2026-08-25, Deliveroo-artikelen belanden onder "Overige", en dat wordt gezegd in plaats van gemaskeerd

**Wat:** Deliveroo-artikelen krijgen een eigen `product_id` met een `dl-`-prefix en worden niet gekoppeld aan de Odoo-productdimensie. Gevolg: op het kanalenscherm valt hun omzet onder "Overige". Dat wordt getoond met de reden, niet weggewerkt.
**Waarom:** `categorie_reeksen` mapt `product_id -> categorie` uit de productendimensie van Odoo, en Deliveroo-artikelnamen staan daar niet in. Een naam-naar-product koppeling is een eigen klus met eigen onzekerheid (naamvarianten, menu-items die geen enkel Odoo-product zijn) en die hoort niet in fase 1. De prefix is er om de fout te voorkomen waar `CANONIEK_DTYPES` in `canoniek.py` voor waarschuwt: id's uit twee bronnen in één naamruimte, waarna een botsing stil de verkeerde categorie oplevert.
**Gevolg:** de categorieprognose blijft ongemoeid — `categorie_reeksen` draait op `kanaal="winkel"`, dus dit is een gat op het kanalenscherm en geen vervuiling van het model. Datzelfde geldt voor `filiaal_id`: Deliveroo-winkels houden hun eigen id, zoals TGTG zijn `store_id` houdt, en vergelijken per vestiging over kanalen heen valt daarmee buiten fase 1.
**Alternatief:** de koppeling meteen bouwen. Verworpen als scope-uitbreiding (harde regel 5); genoteerd als kandidaat voor fase 2, waar ze samen met de marge per product thuishoort.

---

### 2026-08-28, De Deliveroo-opbrengst volgt het TGTG-precedent: in `omzet_excl_btw`, met het voorbehoud als onbeschikbaar-item

**Wat:** de netto-opbrengst van Deliveroo gaat in het canonieke veld `omzet_excl_btw`, precies zoals de netto-opbrengst van TGTG dat sinds het begin doet. Zolang het btw-regime van die opbrengst niet bevestigd is, wordt dat voorbehoud eerlijk gemeld: als een `onbeschikbaar`-item in het contract, met de reden erbij, in het Nederlands en het Frans. Niet stilzwijgend weggelaten, en niet geschat.
**Waarom:** het precedent staat er al en het is bewust zo gebouwd. De moduledocstring van `bakkerij/canoniek.py` zegt over TGTG met zoveel woorden dat de btw-behandeling van de netto-opbrengst nog niet bevestigd is en dat `omzet_excl_btw` voor dat kanaal tot dan te lezen is als netto-opbrengst. Het voorbehoud blijft niet in die docstring hangen: `bakkerij/contract.py` zet voor het kanaal `tgtg` een onbeschikbaar-item op het veld `kanaal.tgtg.aandeel`, met als reden dat het aandeel een nettobedrag naast bedragen exclusief btw legt en dus een benadering is zolang de bevestiging ontbreekt. Het commentaar daarboven formuleert de regel algemener dan TGTG: harde regel 8 gaat over cijfers die niet te geven zijn, en dit is de aangrenzende plicht — een cijfer dat er wél staat mag geen onbevestigde aanname verzwijgen. Die redenering geldt woord voor woord voor Deliveroo, en Deliveroo is bovendien het grotere kanaal: € 857.042 over twaalf maanden tegen € 106.416 voor TGTG over zeven jaar. Twee kanalen die hetzelfde probleem op twee manieren oplossen, is de duurste uitkomst — dan staat er op één scherm een voorbehoud en op het andere niet, zonder dat het verschil iets betekent.
**Alternatief 1:** een tweede kolom naast `omzet_excl_btw` voor opbrengsten waarvan het regime onbekend is. Verworpen: dat splitst de canonieke verkooptabel op een onzekerheid in plaats van op een feit, en elke som over kanalen heen moet daarna weten welke van de twee kolommen ze moet optellen. De onzekerheid hoort in de toelichting bij het cijfer, niet in de vorm van de tabel.
**Alternatief 2:** de btw zelf uitrekenen door een tarief te veronderstellen. Verworpen op harde regel 6 — dat is precies een aanname over de zaak die door de klant bevestigd moet worden — en bij Deliveroo bovendien niet uitvoerbaar, zie hieronder.
**Wat openstaat:** de bevestiging van het btw-regime zelf. Dat is een vraag aan de klant en niet iets wat uit de data volgt. **Bij Deliveroo komt er een complicatie bij die TGTG niet had:** een bakkerij verkoopt tegen 6 % (brood, gebak) én tegen 21 % (dranken), dus één deling volstaat niet. Zelfs mét een bevestigd regime blijft de uitsplitsing afhankelijk van de verhouding tussen beide tarieven in de Deliveroo-mix, en die staat in de ontvangen bestanden niet. Tot dat rond is, blijft het voorbehoud staan zoals het bij TGTG staat.
