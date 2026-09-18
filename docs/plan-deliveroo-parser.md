# Plan: de Deliveroo-parser (blok 5)

_Opgesteld 25 augustus 2026, aangevuld 28 augustus 2026. Status: **fase 1 gebouwd, fase 2 wacht op bruikbare bestanden.** Dit document is de vervolglijst — wie blok 5 afmaakt, hoeft alleen dit te lezen en hoeft niets meer uit te zoeken. De beslissingen eronder staan in `beslissingen.md` (25 augustus, vier entries; 28 augustus, één entry over de btw); de blokkade staat in `todo.md` (S1)._

---

## Naschrift 28 augustus 2026 — er is Deliveroo-data, en ze kwam langs een andere weg

_Dit blok is toegevoegd op 28 augustus 2026 en gaat vóór op wat er verderop over de route staat. De drie stappen zelf blijven gelden; wat verandert is wie de bestanden aanlevert en hoe ze binnenkomen._

Op 27 augustus stuurde Mathias Joosten, accountmanager bij Deliveroo, twee bestanden naar Lien: `Renard Bakery - Blad1.pdf` en `Renard Bakery - Order Volume.pdf`. Niet Sophie die zelf uit Partner Hub downloadt, maar Deliveroo dat rechtstreeks levert — en hij schrijft er expliciet bij: *"If not, please let me know what needs to be added or changed."* Dat aanbod staat open, en het is op dit moment het goedkoopste pad naar wat we missen.

**Wat die bestanden zijn.** PDF-afdrukken van een Excel-draaitabel. Dertien maanden, van augustus 2025 tot en met augustus 2026, per maand, per artikel en per restaurant: verkoopwaarde en aantal stuks. Plus per restaurant per maand het aantal bestellingen. Nagerekend en sluitend: € 864.391,95 over dertien maanden, 295.445 artikelen, 33.060 bestellingen, 288 verschillende artikelen. Ter verhouding: de winkelomzet uit Odoo over dezelfde twaalf maanden (augustus 2025 tot en met juli 2026) is € 4.320.789 exclusief btw en Deliveroo € 857.042 — grofweg een vijfde, en een orde van grootte groter dan TGTG, dat op € 106.416 over zeven jaar staat.

**Wat er niet in zit:** geen dagniveau (alles is per maand opgeteld), geen commissie en geen netto-uitbetaling, geen btw-uitsplitsing.

**Drie restaurantnamen die elkaar aflossen.** "Renard Bakery" (augustus 2025 tot en met juli 2026, € 815.162,54), "Renard Bakery Ixelles" (vanaf juli 2026, € 49.099,31) en "Renard Bakery Uccle" (vanaf augustus 2026, € 130,10 op vijf bestellingen). De voor de hand liggende lezing is dat de oorspronkelijke vermelding in juli hernoemd is naar Ixelles en dat Ukkel er in augustus bij is gekomen. Die lezing is niet bevestigd.

**De print verliest data.** Drie aantallen en één totaalregel zijn rechts afgekapt — `1,68` waar `1.680` hoort te staan. Alle vier zijn met zekerheid teruggerekend, omdat het document zijn eigen maandtotalen draagt en er per maand precies één sluitende lezing overbleef. Dat werkt zolang het om een handvol cellen gaat en niet langer.

**De twee documenten spreken elkaar één keer tegen.** In juni 2026 zegt de artikellijst € 74.840,73 en het bestellingenoverzicht € 74.846, een verschil van € 5,27. Dat is geen leesfout van ons: onze som is gelijk aan de totaalregel die in het document zelf staat. De twee rapporten draaien dus niet op precies dezelfde filter.

**De API is opnieuw nagegaan bij de bron en blijft geen weg.** Deliveroo biedt partners drie suites: Order, Menu en Site. Alle drie zijn operationeel — bestellingen in real time, menu's bijwerken, openingsuren zetten. Er is geen rapportage-, financiële, afrekenings- of historiek-API. Dat bevestigt de beslissing van 12 augustus; de overname door DoorDash heeft daar niets aan veranderd.

### Wat er op 28 augustus gebouwd is

Twee dingen, en ze gaan allebei over hoe een export aankomt en niet over wat hij betekent:

- **Migratie `015_bronupload.sql`** — een postbustabel `bron_upload` plus de schrijffunctie `bewaar_bron_upload`. De reden is de gehoste omgeving: Vercel heeft geen schijf die iets onthoudt, dus `data/raw/Deliveroo/<bereik>/` werkt op de laptop van wie het uitzoekt en nergens anders.
- **Het eerste uploadscherm van het platform, `/deliveroo`.** Een beheerder legt een bestand neer; de server leest het niet en ontleedt het niet, maar zet de bytes ongewijzigd in de database. Het uitpakken hoort in de Python-inlaadlaag en gebeurt daar.

Diezelfde dag zijn daar nog drie dingen bijgekomen, en ze horen bij elkaar:

- **De postbus wordt ook leeggemaakt.** `bakkerij/db/uploads.py` leest de wachtrij en vinkt af; `scripts/uploads_verwerk.py` is de opdrachtregel eromheen (`make uploads` toont wat er ligt, `make uploads-haal` schrijft de wachtende bestanden naar `data/raw/postbus/` zonder ze af te vinken — ophalen is geen verwerken). Eén onderscheid draagt die module: een bestand dat we nog niet **kunnen** lezen blijft staan, een bestand dat **stuk** is wordt afgevinkt. Werpt de lezer `NotImplementedError`, dan zegt dat iets over ons en niets over het bestand. Zonder dat onderscheid leegt de postbus zichzelf door alles wat ze niet begrijpt als kapot te bestempelen, en dan is de dag dat de parser af is de dag dat er niets meer te verwerken valt. Er is vandaag nog geen lezer geregistreerd, dus alles blijft staan als `nog-niet-leesbaar`.
- **Migratie `016_checks_uploads.sql`** laat de stapnaam `uploads` toe in `etl_run`. Zonder die migratie breekt `laden.start_run` de transactie op zijn eerste regel — dezelfde fout die 013 al eens voor `kostenmodel` moest repareren. Twee tests in `tests/test_uploads.py` lezen de migratiebestanden en bewaken dat de lijsten in Python en de checks in SQL niet uit elkaar lopen.
- **Een trap uit `bakkerij/kwaliteit.py` gehaald.** `bronstanden` routeerde op de kanaalnaam `"tgtg"` en niet op het begrip. Nu leest de routering twee lijsten: `BEVROREN` (komt niet meer bij) en de sleutels van `ACHTER_DAGEN_PER_KANAAL` (komt bij, maar niet dagelijks). Dat maakt de derde mogelijkheid die bij `BEKEND_AFWEZIG` beschreven staat eindelijk bereikbaar — en dat is precies wat Deliveroo wordt: een periodieke oplading via het uploadscherm, met een eigen lat in de orde van 90 dagen in plaats van de twee dagen van een dagelijkse bron. Aanzetten is één regel in die tabel; er is vandaag bewust niets voor Deliveroo toegevoegd.

`make controle` staat groen: 801 Python-tests en 188 platform-tests.

### Wat dit betekent voor de drie stappen hieronder

| Stap | Stand op 28 augustus |
|---|---|
| **1 — de probe** | Ongewijzigd van inhoud, maar niet langer de enige weg. De drie dingen die de probe moet uitwijzen (dagniveau, order-sleutel, datumnotatie) zijn precies de drie dingen die aan Mathias gevraagd worden. Levert hij ze, dan is de probe overbodig; levert hij ze niet, dan is Partner Hub weer de eerste weg |
| **2 — de volledige historiek** | Deels binnen, maar in de verkeerde vorm. Dertien maanden verkoopwaarde per maand is géén vervanging voor de twaalf maanden op dagniveau: het venster in Partner Hub schuift nog altijd elke dag op, en wat eruit valt is nergens meer te halen. De urgentie van S1 daalt niet |
| **3 — de bouw** | Onaangeroerd. Wat binnenkwam is niet te lezen met de parser die er ligt (zie hieronder), dus er is niets bijgekomen om op te bouwen |

### Waarom de ontvangen bestanden de parser niet raken

`bakkerij/sources/deliveroo_parse.py` is voorzien op **CSV** — `parse_items_sold` en `parse_orders` nemen allebei `tekst: str` — en op **twee specifieke Partner Hub-rapporten**: `Items Sold` (per dag, per artikel) en `Orders` (per bestelling, met de kolommen `Deliveroo commission` en `VAT on Deliveroo commission`). Wat er binnenkwam matcht daar geen enkele as van: het is PDF in plaats van CSV, per maand in plaats van per dag, en zonder commissie.

Dat is de reden om die twee rapporten **bij naam** te vragen in plaats van te omschrijven wat we willen. Dat bericht staat uitgewerkt in `docs/vragen-aan-lien.md`, onder "Wat wij aan Mathias zouden vragen, in één bericht" — inclusief de vervolgvragen over de order-sleutel, het vestigingskenmerk en het verschil in juni. Het wordt hier niet herhaald, zodat er één versie van blijft bestaan.

---

## Waarom dit een eigen document is

Blok 5 stond in `todo.md` op 0,5 dag met één blokkade (S1). Dat klopt niet helemaal, en het verschil is de moeite waard om vóór de bouwdag te weten: bij TGTG is de commissie één vast tarief per pakket van de maandfactuur, bij Deliveroo staat de commissie **per bestelling** terwijl de omzet **per artikel** staat. Er moet dus iets toegewezen worden dat bij TGTG niet bestond, en hoe duur dat is hangt af van één ding dat we nog niet weten.

Daarom is het werk gesplitst: alles wat niet van de documentvorm afhangt is op 25 augustus gebouwd, en het lezen zelf wacht op echte CSV's.

## Wat er al staat (25 augustus 2026)

| Bestand | Wat erin zit |
|---|---|
| `bakkerij/sources/deliveroo_parse.py` | `DeliverooFormaatFout`, de vorm van beide rapporten (`Artikelregel`, `Orderregel`), de mappenconventie, `bereik_uit_pad`, `klopt_met_bereik`, `gaten_in_dekking`. `parse_items_sold` en `parse_orders` heffen `NotImplementedError` met de weg erin |
| `scripts/deliveroo_extract.py` | Inventaris van de downloads: welke bereiken er liggen, welk rapporttype mist, welke bestanden buiten de conventie vallen, en waar de gaten in de twaalf maanden zitten. Schrijft niets naar `data/interim` |
| `tests/test_deliveroo_parse.py` | 12 tests, zonder nagebouwde CSV-tekst — bewust, zie hieronder |
| `Makefile` | `make deliveroo`. Bewust **niet** in `alles` |
| `bakkerij/kwaliteit.py` | De schakelinstructie op beide plekken (`BEKEND_AFWEZIG` en `BEVROREN`). Niets omgezet: dat gebeurt op de laaddag |

**Waarom er geen nagebouwde CSV in de tests staat.** De les van de TGTG-parser is dat de vorm van echte documenten verrast: drie datumnotaties over zeven jaar, drie namen voor dezelfde artikelregel, een euroteken vóór, achter of nergens. Een test op een bedachte kopregel bewijst alleen dat de parser de verzinner begrijpt. Wat wél getest is, is alles dat van ónze conventie afhangt en niet van die van Deliveroo.

## Stap 1 — de probe. Drie dagen, en hij beslist de rest

**Vraag aan Lien (vraag 66): één bereik van drie dagen uit Partner Hub → Reports, beide rapporttypes (Items Sold én Orders).**

> **28 augustus 2026 — tweede keus geworden, niet vervallen.** Sinds Deliveroo zelf levert, is dezelfde vraag goedkoper rechtstreeks aan Mathias te stellen. Vraag 66 blijft staan voor het geval hij niet levert wat we nodig hebben; dan is Partner Hub opnieuw de enige bron die de commissie draagt. Wat de probe moet uitwijzen, verandert niet.


Dit is de goedkoopste beslissende meting in het hele blok. Drie dingen komen er in één keer uit, en alle drie bepalen wat er daarna gebeurt:

| Wat de probe uitwijst | Waarom het de bouw bepaalt |
|---|---|
| Splitst Items Sold **per dag** uit, of telt het over de periode op? | Aggregeert het, dan moet het rapport per kalenderdag gedraaid worden: ~365 downloads in plaats van 4. Dat verandert de opdracht aan de zaakvoerder volledig, en dat wil je weten vóór ze aan de volledige download begint |
| Dragen Items Sold en Orders een **gemeenschappelijke order-sleutel**? | Dit is de kern. Mét sleutel is de marge per product verdedigbaar; zonder is ze een benadering. Zie stap 3 |
| Welke **datumnotatie**, en welke kolomnamen? | Partner Hub is Engelstalig. `05/03` is 5 maart of 3 mei, en van de 365 dagen in een jaar zijn er 132 waarop de omwisseling een andere, even geldige datum oplevert. `klopt_met_bereik` betrapt dat, maar de parser moet het meteen goed doen |

Drie dagen volstaan: de vorm van een export verandert niet met de lengte van het bereik.

## Stap 2 — de volledige historiek, en die wacht niet op code

**Vier blokken van maximaal 90 dagen over de laatste twaalf maanden, beide rapporttypes.** Dit hangt niet aan de parser en hoort niet op de bouwdag te wachten.

Het venster van twaalf maanden in Partner Hub schuift **elke dag op**. Wat eruit valt is nergens meer te halen: niet via de rapporten, niet via de facturen, en niet via de API (die geeft niets ouder dan dertig dagen). Dit is het enige openstaande punt van het hele project waar uitstel onherstelbaar is. S1 staat open sinds 12 augustus.

Waar de bestanden heen moeten wanneer iemand ze **lokaal** verwerkt — één submap per download, en de **map** draagt het bereik, niet de bestandsnaam:

```
data/raw/Deliveroo/2025-08-25_2025-11-22/items-sold.csv
data/raw/Deliveroo/2025-08-25_2025-11-22/orders.csv
```

`make deliveroo` controleert dat, meldt wat er buiten de conventie valt, en wijst de gaten in de reeks aan. Draai het meteen na elke download: een vergeten blok is een stille leegte in een reeks die gewoon doorloopt.

> **28 augustus 2026 — de mappenconventie is niet langer de enige weg.** Dit blok ging ervan uit dat Sophie zelf downloadt en de bestanden op een schijf legt. Sinds vandaag is er een tweede route, en waarschijnlijk de snellere: Deliveroo levert rechtstreeks (zie het naschrift bovenaan), en het uploadscherm `/deliveroo` neemt een bestand aan in de gehoste omgeving, waar geen schijf bestaat. De conventie hierboven blijft onverkort gelden voor wie lokaal werkt — dat is de weg waarop `make deliveroo` en `bereik_uit_pad` gebouwd zijn — maar wie een bestand via het scherm binnenbrengt, geeft het bereik niet met een mapnaam mee. De controle op dag/maand-omwisseling die aan die mapnaam hangt, is er voor die route dus niet.

## Stap 3 — de bouw

De volgorde is die van de TGTG-keten, want het patroon is bewezen: pure functies in `sources/`, alle bestandsverwerking in `scripts/`, normalisatie in `canoniek.py`.

| | Waar | Wat |
|---|---|---|
| 1 | `sources/deliveroo_parse.py` | `parse_items_sold` en `parse_orders` vullen. Kopregelcontrole eerst, dan de datumnotatie. Faalt luid via `DeliverooFormaatFout`, nooit een lege lijst |
| 2 | `sources/deliveroo_parse.py` | `verdeel_commissie()` — de toewijzing, zie hieronder. Dit is het echte werk |
| 3 | `canoniek.py` | `deliveroo_naar_canoniek()` (netto-omzet per product-dag) en `kanaalkost_deliveroo()` (de wig per maand) |
| 4 | `scripts/deliveroo_extract.py` | De inventaris uitbreiden naar echt lezen: ontdubbelen op de order-sleutel (de blokken van 90 dagen overlappen), `klopt_met_bereik` per download, wegschrijven naar `data/interim/deliveroo_*.csv` |
| 5 | `scripts/canoniek_bouw.py` | `haal_deliveroo()` naar het model van `haal_tgtg()`, en `bouw_verkopen(winkel, tgtg, deliveroo)` |
| 6 | `bakkerij/kwaliteit.py` | **De schakel.** Zie de eigen sectie hieronder |
| 7 | `tests/test_deliveroo_parse.py` | Nu wél met echte-vorm-fixtures, geanonimiseerd |
| 8 | `Makefile` | `deliveroo` opnemen in de keten waar hij hoort |

### De toewijzing: van commissie-per-order naar netto-per-artikel

Twee routes, en de probe beslist welke:

- **Mét order-sleutel:** join op de sleutel, en de ordercommissie pro rata over de artikelregels naar subtotaal. Zuiver, en dan is een uitspraak over de marge per product verdedigbaar.
- **Zonder:** een effectief dagtarief — de dagcommissie gedeeld door de dagbruto — pro rata toegepast. Op dagniveau exact goed, per product een benadering.

**Welke route gebruikt is, hoort in de uitvoer te staan** en niet in het hoofd van wie het gebouwd heeft. Een stille keuze tussen deze twee is precies het soort verschil dat niemand naast elkaar legt tot het te laat is.

### De schakel in `kwaliteit.py`, in dezelfde commit als het laden

Op de dag dat Deliveroo geladen wordt, verhuist het kanaal van `BEKEND_AFWEZIG` naar `BEVROREN`. **Beide regels, niet één.**

- Blijft het in `BEKEND_AFWEZIG` staan, dan wordt een achterstand nooit gemeld terwijl er wél data is.
- Haal je het weg zonder het in `BEVROREN` te zetten, dan valt het kanaal in `bronstanden` niet in de TGTG-tak maar in `_stand_dagelijks`, en daar staat `MAX_ONGEMETEN_DAGEN` op **twee**. Twee dagen na de laatste geladen dag staat het kanaal permanent 'achter' — op een bron die per definitie niet dagelijks bijkomt. Dezelfde fout die op 19 augustus voor TGTG gerepareerd is, maar twintig keer sneller. `_stand_dagelijks` verklaart ongemeten dagen bovendien aan de hand van de *winkel*kalender, en een bezorgplatform volgt de openingsdagen van de toog niet.

Wordt er wél een periodieke Hub-download afgesproken (maandelijks of per kwartaal, via het uploadscherm `/deliveroo`, dat sinds 28 augustus bestaat), dan hoort het kanaal in **geen van beide** lijsten en krijgt het een eigen drempel in de orde van 90 dagen — zoals `TGTG_ACHTER_DAGEN` dat voor een maandelijkse bron doet. Dat is een derde mogelijkheid, geen variant op de twee hierboven.

De volledige afweging staat als commentaar bij `BEKEND_AFWEZIG` zelf, want dat is de plek waar iemand hem nodig heeft.

### Wat de database niet vraagt

Niets. `fact_kanaalkost` heeft `check (kanaal in ('winkel','deliveroo','tgtg','overig'))` al staan sinds migratie 002, `db_laad.bereid_kanaalkost` geeft de kanaalkolom al door, en `fact_verkoop` is kanaal-agnostisch. **De kanaalkost vraagt geen migratie.** De kanaalkost van Deliveroo wordt naar maand geaggregeerd om in die tabel te passen; de ruwe ordercommissie blijft in de tussenbestanden staan, dus een latere verfijning naar dagniveau gooit niets weg.

> **28 augustus 2026 — twee dingen die niet verward mogen worden.** Hierboven stond tot vandaag "Geen migratie 015". Die zin klopt nog steeds voor wat ze bedoelde — de kanaalkost van Deliveroo past ongewijzigd in `fact_kanaalkost` — maar er ligt sinds vandaag wél een `015_bronupload.sql`, en die gaat over iets anders. Uit elkaar gehouden:
>
> - **Wat de export betekent** (kanaalkost, netto-omzet, de wig per maand): geen migratie, niet toen en niet nu. De tabellen die dat dragen bestaan al.
> - **Hoe de export aankomt** (een bestand dat een mens neerlegt in een omgeving zonder schijf): dát is migratie 015 — de tabel `bron_upload` en de schrijffunctie `bewaar_bron_upload`, samen met het scherm `/deliveroo`.
>
> Wie het nummer 015 tegenkomt en deze sectie leest, moet niet concluderen dat de kanaalkostkant van gedachten veranderd is. Dat is niet gebeurd.

Let op de betekenis: `commissie_per_stuk` is bij TGTG een *tarief* en bij Deliveroo een *gemeten gemiddelde*. Dat hoort in de docstring van `kanaalkost_deliveroo`, want wie er later een voorspelling op bouwt, moet het weten.

## Raming

| | |
|---|---|
| Fase 1 (gebouwd, 25 aug) | — |
| Fase 2, mét order-sleutel | 0,5 dag |
| Fase 2, zonder order-sleutel | 1 – 1,5 dag |

De oorspronkelijke 0,5 dag in `todo.md` gold voor het gunstige geval. De probe beslist welke van de twee het is, en dat is de reden om die drie dagen CSV apart te vragen in plaats van te wachten tot de volledige historiek binnen is.

## Wat expliciet buiten fase 1 blijft

- **De Order API.** Op 12 augustus uit het ontwerp geschrapt en die beslissing staat: dertig dagen historiek, geen commissie en geen netto-uitbetaling in de webhook, geen finance- of settlement-endpoint, toegang op uitnodiging en gericht op kassaleveranciers. Ze komt alleen terug in beeld als de klant dagverse, volautomatische Deliveroo-productcijfers eist, en dan is dat een eigen fase.
- **De koppeling van Deliveroo-artikelen aan de Odoo-productdimensie.** Deliveroo-artikelen krijgen een `dl-`-prefix en vallen op het kanalenscherm onder "Overige", mét reden. De categorieprognose blijft ongemoeid: `categorie_reeksen` draait op `kanaal="winkel"`. Fase 2, samen met de marge per product.
- **Vergelijken per vestiging over kanalen heen.** Deliveroo-winkels houden hun eigen id, zoals TGTG zijn `store_id` houdt.
- **Automatische aanvoer.** De ingestmailbox is op 17 augustus geschrapt op vraag van de opdrachtgever. Wat overblijft is de handmatige aanvoer: een download uit Partner Hub of een levering door Deliveroo zelf, in beide gevallen door een mens neergelegd. Het uploadscherm daarvoor is geen toekomstplan meer — `/deliveroo` staat er sinds 28 augustus, samen met migratie 015.

## Risico op middellange termijn

DoorDash rondde de overname van Deliveroo af op 2 oktober 2025. Een migratie van het partnerplatform is niet aangekondigd, maar het is een reden om niet te lang op de huidige structuur te bouwen — en een tweede reden om de historiek nú te redden in plaats van te vertrouwen op een portaal dat volgend jaar anders kan heten.

---

_25 augustus 2026, aangevuld 28 augustus 2026. Bron: `docs/koppelingen.md` (12 augustus, het onderzoek naar de rapporten en de API, met het naschrift van 28 augustus), `docs/beslissingen.md` (25 augustus, vier entries; 28 augustus, de btw-behandeling), `docs/vragen-aan-lien.md` (28 augustus, wat er binnenkwam en wat er aan Mathias gevraagd wordt), en de code zoals ze op 28 augustus in de repo staat._
