# Open punten

_Bijgewerkt 18 augustus 2026. Dit is de lijst om samen door te nemen._

Dit document is iets anders dan `vragen-aan-lien.md`. Dáár staan vragen aan de opdrachtgever; hier staat alles wat open is, ook wat wij zelf moeten beslissen of nog moeten bouwen. Elk punt heeft een eigenaar en een gevolg als het niet beslist wordt.

De rangschikking is op wat er stilvalt als het punt blijft liggen, niet op hoe interessant het is.

> **De herstelronde op de reviewbevindingen is afgerond en nagemeten** (13 augustus, ochtend): O17 is af, O13 is bewust half opgelost en staat hieronder met de motivering. O12 is dezelfde ochtend te vroeg afgemeld en pas 's middags echt dichtgegaan.
>
> **13 augustus, middag: O22 is dicht.** De zeven CFO-metrieken staan op het scherm. Suite (221 tests), `make lint`, `npm test` (39) en de typecheck zijn samen groen.
>
> **13 augustus, namiddag: O23 is dicht, en blok 7 (database) staat.** Supabase en Vercel zijn toegekend, maar het aanmaken van het project blokkeert nog op een rechtenkwestie — zie S2. Het schema, de migraties, de migratierunner en de laadlaag zijn gebouwd en volledig getest zónder database; ze wachten alleen op `SUPABASE_DB_URL`. Suite staat op 329 tests, `make lint` groen.

---

## 1. Blokkeert het kritieke pad naar de oplevering (27 augustus)

De actuele blokkadelijst staat in `todo.md` (de S-nummers); dit document draagt de interne punten. Sinds 14 augustus is de actuele blokkade op dit pad **S11**, het databasewachtwoord (bij Lien).

| # | Punt | Bij wie | Wat er stilvalt |
|---|---|---|---|
| O1 | ~~**Supabase-project** (EU-regio, projectsleutels). Poort G7~~ | ✅ **binnen 14 aug** (eu-north-1, Stockholm) | Wat rest is S11: zonder het databasewachtwoord blijft de gehoste route droog |
| ~~O2~~ | ~~**Deliveroo-historiek** uit Partner Hub, 12 maanden in blokken van 90 dagen~~ | ✅ **Binnen op 18 sep 2026, geladen op 19 sep.** 23 downloads (Orders én Items Sold), 3 sep 2025 t/m 2 sep 2026, aaneengesloten. Eén echt gat: 25 jan t/m 9 feb 2026 heeft geen Orders-bestand, en dat venster is uit Partner Hub geschoven. Het kanaal staat in de database via de postbus; zie `beslissingen.md` 19 sep voor wat er nog openstaat (bedragen in het weekrapport, productmix, zomersluiting) | — |
| O3 | ~~**Vercel-toegang**~~ | ✅ **binnen 13 aug** | — |
| O4 | **Odoo-productielicentie** (G6) en of de preprod meesynchroniseert (G5) | eindklant / Idealis | Oplevering op echte, dagverse data. Vandaag draaien we op een extract van 12 augustus |

## 2. Bepaalt wat het platform mag beweren

| # | Punt | Bij wie | Gevolg |
|---|---|---|---|
| O5 | **Aanbodpatroon per product** (vraag 44). Wordt een deel van het assortiment maar op bepaalde dagen aangeboden? | bakkerij, via Lien | Zonder dit blijft de prognose beperkt tot de 103 kernproducten (84,1% van de stuks). De overige 226 producten tonen zich als onbeschikbaar |
| O6 | **Sluitingskalender vooruit** (vragen 45 en 46) | bakkerij, via Lien | De prognose slaat de sluitingsdagen over die de kalender gemeten heeft, maar voor de dagen daarbuiten neemt ze aan dat de winkel open is, en zegt dat ook op het scherm (aanname `prognose.sluitingsdagen`). Zodra de agenda vooruit er is, verdwijnt die aanname |
| O7 | **Brutomarges per productgroep** (vraag 19, poort G1) | eindklant, via Lien | Het margescherm blijft leeg met reden. Nu een add-on, geen fase 1 |
| O8 | ~~Censurering: is uitverkoop meetbaar?~~ **GEMETEN 13 aug: ja, en structureel.** 33% van de gewogen product-dagen draagt een leeg-reksignaal; 98 producten met 66% van de omzet zijn structureel gecensureerd (`bakkerij/censurering.py`, drie samenvallende signalen). De prognose meet verkoop, niet vraag — dat hoort met deze cijfers in E4 | ✅ gemeten; bevinding naar het backtest-rapport | Zie punt 5 hieronder voor de meetdefinitie |
| O9 | **Het bestelkanaal** (vraag 43): € 1,8 miljoen B2B naast de kassa. In of buiten scope? | Lien | Nu buiten scope. Erin nemen betekent een vierde kanaal en een scopewijziging |
| O10 | **Schoolvakanties: Franstalig, Nederlandstalig of beide?** (vraag 47) | Lien | **Empirisch beantwoord 13 aug:** beide regimes staan in de kalenderlaag en zijn door de backtest gehaald; het Fránstalige regime verklaart het koopgedrag het best (op vakantiedagen 7,8%→6,0% WAPE, n=86) en draait in de prognose. Bevestiging door Lien blijft gewenst; randdatums als aanname A20 |

## 3. Wat wij moeten beslissen, niet de klant

| # | Punt | Stand |
|---|---|---|
| O11 | ~~Het laatste verkoopuur per product per dag zit niet in het canonieke model~~ **AFGEHANDELD 13 aug:** eigen aggregaat-extractie (`odoo_laatste_uur.py`, 90.453 product-dagen, UTC→Brussel) plus `canoniek_uren.csv` met lader en tests. O8 is ermee beantwoord | ✅ |
| O12 | ~~`onbeschikbaar.veld` is een technische sleutel op het scherm~~ **AFGEHANDELD 13 aug (middag).** De ochtendmelding was te vroeg: `verdeelPrognoseRegels` zette de redenen op de juiste plek, maar de component `Toelichting` drukte de sleutel nog letterlijk af als term — op vijf schermen. Nu vertaalt `veldLabel` (`platform/lib/toelichting.ts`) elke sleutel naar een label, met een leesbaar vangnet voor sleutels die er nog niet in staan; een test bewaakt dat geen enkel label nog een punt of liggend streepje draagt. Het contract houdt `onbeschikbaar` als `[{veld, reden}]` | ✅ |
| O13 | **De voettekst leest `contract/overzicht.json`** voor de versheid, ongeacht welk scherm actief is | **Half opgelost, bewust.** Alle antwoorden komen uit één generator-run en dragen dezelfde `bijgewerkt_op`/`gemeten_tot`, dus de voettekst kan vandaag niet liegen; dat staat als commentaar in `layout.tsx`. _Nazorg 18 aug: de route per scherm is er — migratie 006 (`contract_antwoord`), de sync schrijft de antwoorden erin, en `CONTRACT_BRON=db` laat `laadContract` per scherm uit Postgres lezen. De vlag staat sinds 18 aug om en is tegen de echte database getest. Wat nog rest van dit punt: de voettekst hoort de envelope van het eigen antwoord te dragen in plaats van die van `overzicht`_ |
| O14 | ~~Dodemansknop ontbreekt~~ **AFGEHANDELD 13 aug:** `bakkerij/kwaliteit.py` met sluitingsbewuste bronstanden (een dodemansknop die vier weken zomersluiting alarm slaat, is op de dag van de echte storing onzichtbaar), elf tests, en het zesde contractantwoord `stand.json`. Het Instellingen-scherm toont het voluit ("Leeft het platform?"), de voettekst van elk scherm draagt de ergste uitkomst | ✅ |
| O15 | ~~Datakwaliteitswachters (B6) bestaan niet~~ **AFGEHANDELD 13 aug**, zelfde module als O14: vijf wachters (dubbele sleutels, negatieve waarden, gat in de reeks, kalenderdekking, drempelrand), elk met een toelichting óók bij "goed". Wachters op bon- en uurniveau zijn in de signatuur gereserveerd maar nog niet gebouwd | ✅ |
| O16 | **Het agendaspoor is gebouwd vóór vraag 46 beantwoord is.** Dat gaat in tegen de projectregel "noteer het en bouw het niet", op uitdrukkelijke instructie van Kwinten. De laag is geïsoleerd en optioneel, dus de kost bij afwijzing is één map en één import | Ter kennisgeving, geen actie |
| O17 | ~~De prognose begint op de dag na de laatste meting~~ **AFGEHANDELD:** de horizon schuift mee met vandaag (`canoniek.prognosevenster`: `start = max(gemeten_tot + 1, vandaag)`, gemeten-gesloten dagen worden overgeslagen, het meetgat staat op het scherm). Nagemeten 13 aug: de prognose begint op vandaag, het gat van 1 t/m 12 augustus staat als reden in het antwoord | ✅ |
| O22 | ~~Zeven CFO-metrieken hangen nog niet aan het contract~~ **AFGEHANDELD 13 aug (middag).** Alle zeven staan op een scherm: bonritme, weekdagmix, weken, maandritme en afwijkende dagen op het Dagoverzicht, concentratie en prijs/volume op Productmix. `heleweken` kreeg er één functie bij (`weekomzet`), want vensters zonder omzet zijn geen scherm — en de omzet erbij rekenen in de contract- of presentatielaag zou harde regel 4 breken. Elk blok kan `null` zijn met een reden in `onbeschikbaar`; beide ontbindingen worden in de contractlaag nagerekend en werpen een fout als ze niet op de cent optellen | ✅ |
| O23 | ~~Wachters op bon- en uurniveau~~ **AFGEHANDELD 13 aug (namiddag).** Twee wachters: `bonnen_omzetdekking` legt de bonnentelling naast de kassaverkoop en is daarmee een onafhankelijke getuige — `gat_in_de_reeks` weegt de verkopen tegen een kalender die zélf uit die verkopen gebouwd is en ziet een gat in het verkoopextract dus niet. `censureringsdrempel` vergelijkt het leeg-reksignaal over de laatste 90 meetdagen met dat daarvóór, drempel 8 procentpunt (empirisch: van 440 rollende vensters week er geen enkel verder dan 3,7 punt af). Beide staan `goed` op de echte data; `stand.json` draagt nu zeven wachters | ✅ |
| O18 | **`make lint` dekt `scripts/` niet**, terwijl de ruff-hook dat wel doet. Twee verschillende lat­ten | **Afgehandeld, 12 aug.** `scripts/` staat in het lint-doel en de map is schoon. De 22 openstaande fouten zijn inhoudelijk opgelost, niet met een `noqa` weggezet: de blinde `except`-blokken vangen nu de fouten van de Odoo-koppeling en niets meer, `try`-`except`-`pass` slikt niets meer stil in, en `date.today()` en `strptime` zijn tijdzonebewust op Europe/Brussels. Gevolg voor het gedrag: een fout in ons eigen telwerk crasht nu luidruchtig in plaats van als "read_group mislukt" op het scherm te komen |

## 4. Documenten die nog niet kloppen

| # | Punt | Stand |
|---|---|---|
| O19 | ~~`deliverables.md` klopt op tien plaatsen niet meer~~ | **Afgehandeld 13 aug**, alle tien statussen bijgewerkt |
| O20 | **`scope.md` "Eén kassa" is rechtgezet** naar drie kassa's, één winkel (bevestigd 12 aug). Andere documenten kunnen de oude aanname nog dragen | Nagelopen: `CLAUDE.md` en `canoniek.py` zijn correct |
| O21 | ~~Aanname A11 over `filiaal_id`~~ | **Afgehandeld 13 aug**, gesloten in `aannames.md` |

## 5. De censureringsvraag, uitgeschreven

Dit staat apart omdat het het enige punt is dat de geloofwaardigheid van de prognose raakt en waar we zelf iets kunnen meten.

Wat de kassa meet is **verkoop**, niet **vraag**. Als de croissants om tien uur op zijn, telt de kassa de rek en niet de klant. Een prognose die op verkoop gekalibreerd is, voorspelt dus de rek en niet de vraag — en die twee lopen precies uiteen op de dagen waarop het geld te verdienen valt.

`model-ontwerp.md:68` maakt de correctie voorwaardelijk: alleen als de audit uitwijst dat uitverkoop meetbaar is. Dat is te toetsen, en het antwoord zit in het laatste verkoopuur per product per dag: een product dat structureel om 10u zijn laatste bon heeft terwijl de winkel tot 17u open is, was uitverkocht. Dat veld staat in `deliverables.md` A2 als eis, maar zit niet in het canonieke model (O11).

**Voorstel:** het laatste verkoopuur toevoegen aan het werkextract, meten hoe vaak het patroon voorkomt, en het resultaat als bevinding rapporteren. Blijkt uitverkoop zeldzaam, dan is de censurering een voetnoot. Blijkt ze structureel, dan hoort ze in het opleverdocument bij wat de prognose niet kan — en dat is waardevoller dan een model dat een halve procent nauwkeuriger is.

---

## Wat vandaag wél af is en niet meer op deze lijst hoort

- Canoniek datamodel, kalenderlaag, drempelregel voor sluitingsdagen
- Baselines en het rolling-origin backtest-harnas, met een gemeten lat: 8,4% WAPE op de dagomzet, 20,2% per product per dag
- Berekeningslaag als pure functies, met tests
- Contractlaag: één genummerd JSON-antwoord per scherm (plus de winkelindex), geen float in een bedrag, `onbeschikbaar` als eersteklas veld
- Zes schermen draaien lokaal op het echte contract (acht routes, waarvan zeven achter de login; alleen het aanmeldscherm staat erbuiten)
- Vraag 18 gesloten: drie kassa's, één winkel
- Eén lat op alle Python: `make lint` dekt `bakkerij/`, `tests/` én `scripts/`, en `scripts/` is schoon (O18)
- De kwaliteitslaag: dodemansknop + vijf wachters, met een eigen contractantwoord op het scherm (O14/O15)
- De prognoseband per horizonstap, het trackrecord (28 dagen out-of-sample) en de gemeten banddekking hardop in het antwoord
- De censureringsmeting: 33% van de gewogen product-dagen draagt een leeg-reksignaal (O8/O11)

---

## Audit 14 augustus: wat gedicht is, en wat nog open staat

Een volledige zwakke-plekken-doorlichting (onbreekbaarheid, beveiliging, eerlijke UI, tests, operabiliteit, toegankelijkheid, regel-4-consistentie) leverde ~60 vondsten. **Dezelfde dag gedicht:** atomaire writes voor contract-JSON's, canonieke CSV's en configbestanden; een herrekenings-lock plus foutlogging in de opslag-actie; het contract wordt per verzoek van schijf gelezen (de statische import toonde in een productiebuild verouderde cijfers ná een opslag); rolhertoetsing tegen de actuele omgeving bij élk verzoek; een pogingenslot op de login; `db_laad` alles-of-niets (één commit, rollback vóór de foutregistratie); het dode gebruikersformulier vervangen door een eerlijke S2-melding; "€ 0,00" voor een onbekende commissie vervangen door "onbekend"; de reden-sleutel van een lege prognose hersteld; vier ontbrekende schermlabels; datumopmaak die niet meer crasht op een kapot veld (met tests, ook op format.ts); globale focus-stijl, skip-link, aria-label op de staafgrafiek, leesbaar placeholder-contrast; `make test` dekt nu ook de TypeScript-helft; de dode `platform/mock/` is weg en de mock-uitzondering in de klantdata-hook is gesloten.

**Bewust open, op volgorde van gewicht:**

| Vondst | Waarom nog open |
|---|---|
| ~~**`fact_bonnen` draagt preprod-kassanamen en stopt op 7 augustus**~~ | **Opgelost in code op 18 sep 2026, wacht nog op één sync.** De diagnose hierboven klopte, maar de voorgestelde oplossing ("één run van `make extract-bonnen` met de hand") was de verkeerde: precies dát is nooit gebeurd, en daarom stond er op het overzichtsscherm permanent dat het aantal klanten niet gemeten is. Een optionele stap die niemand draait, is geen optie maar een gat. Daarom staat `odoo_bonnen.py` nu ín de nachtelijke ketting (`scripts/nachtelijke_sync.py`, stap 2b) en haalt migratie `019_bonnen_preprod.sql` de preprodrijen weg — die twee horen bij elkaar, want los geladen zouden productie- en preprodnamen naast elkaar komen te staan en zou het klantenaantal voor jan 2025 t/m aug 2026 verdubbelen, de fout die 018 voor `fact_verkoop` moest opruimen. De kostenzorg uit de oude tekst berustte op een leesfout: `odoo_bonnen.py` leest `pos.order` met twee velden, dus bonnen en geen bonregels. **Wat nog moet gebeuren:** één sync draaien die deze stappen bevat; tot dan staat het scherm nog op de oude melding |
| ~~`make tgtg` kan bij een kapotte omgeving een lege CSV met exitcode 0 achterlaten~~ | **Vervallen 18 sep 2026**: TGTG is uit scope, `make tgtg` en het hele handmatige pad bestaan niet meer (zie `beslissingen.md`). `make extract` is stil bij nul rijen en er is geen netwerktimeout op de Odoo-client blijft wél open |
| Een ontbrekende productendimensie maakt van alles stil "Overige" | De eerdere toewijzing "hoort bij blok 9" is vervallen — blok 9 is op 17 aug geschrapt. Eerlijke status: dit is een losse wachter voor de kwaliteitslaag (het zesde antwoord) zonder blok dat hem draagt; hij moet op eigen merites ingepland worden of expliciet blijven liggen |
| Geen intrekbare sessies (staatloze HMAC-tokens) | Rolhertoetsing dicht het praktische gat; échte intrekbaarheid komt gratis mee met Supabase Auth (blok 12, na S12/S13) |
| `secure`-cookievlag hangt aan NODE_ENV | Correct op Vercel (productie = production); expliciete schakelaar meenemen bij de S11-uitrol (de Vercel-deploy) |
| ~~PDF-rapport vertelt minder dan de schermen (geen jaarvergelijking, weekdagprofiel, kostenopbouw) en kort aslabels af~~ | ✅ **opgelost 18 aug** — en niet door de PDF bij te werken: het rapport is een weergave van de schermen zelf geworden (`platform/app/rapport/page.tsx`), dus het toont per definitie hetzelfde. De tweede opmaaklaag die achterliep (WeasyPrint) is opgeheven |
| Float-randjes in contract.py (gemiddelde per open dag, weektotaal-som als float vóór de stringgrens) | Uitvoer blijft strings met centen; de afwijking is hoogstens één cent in een niet-optelbare context. Opruimen bij de eerstvolgende contract-sessie, met de cent-invariant als test |
| Grafiek zonder punten verdwijnt zonder reden binnen een kaart | Vergt een contractafspraak (lege reeks → reden meesturen); meenemen bij de volgende contractwijziging |
| io_load.py, audit/profile.py, odoo_client.py, scripts/ zonder tests; requirements zonder bovengrenzen | Testschuld benoemd; eerst de deliverables van fase 1, dan deze bodem |
| Tablist zonder tab-semantiek (PeriodePaneel), grafieken zonder toetsenbordtoegang | Toegankelijkheidsverdieping; de informatie staat ook in tabellen op dezelfde schermen |
| `bakkerij/report/baklijst.py` noemde zichzelf de deliverable (geschrapt 12 aug) | Afgehandeld: het bestand is op 18 aug daadwerkelijk verwijderd. Het denkwerk staat in `model-ontwerp.md` en de git-historie bewaart de code voor fase 2+ |

---

## Inspectieronde 18 augustus: wat gedicht is, en wat bewust blijft liggen

Vier verkenners over de hele opdracht (Python-kern, platform, docs, database/sync/CI), gevolgd door een reparatieronde over ~40 vondsten. **Dezelfde dag gedicht:** de UTC-dagsleutel in het kernextract (`bakkerij/tijd.py`, met randgevaltests); een leeg extract eindigt niet langer op exitcode 0; de inloglus onder `AUTH_BRON=supabase`; `laadWinkels` faalt luid op de databaseroute; de kostenmodel-actie weigert onder `CONTRACT_BRON=db`; RLS op `schema_migraties`, `revoke` voor `authenticated` op alle tabellen, herhaalbare policies en migratie 007 (check-constraints); de etl_run-registratie van een gevallen poortwachter (en de foutafhandelaar die de echte fout kon maskeren); `DROOG` op één plek gelezen (`droge_modus`); `connect_timeout` op de verbinding; test-CI op elke push; faalmelding als GitHub-issue; de cron bewust uit tot de runner-invoer geregeld is; de eentalige teksten en huisstijl-afwijkingen op het platform; de bronwacht uitgebreid naar `.ts`; de docs-drift over de hele linie (scope derde herziening, verse voortgangsnota, vraag 58); `baklijst.py` en `uitleg()` verwijderd; de `parse_getallen`-duizendtalbug met 23 nieuwe tests; het scenariopad serialiseert via `ct._s`.

**Bewust open, op volgorde van gewicht:**

| Vondst | Waarom nog open |
|---|---|
| ~~De diagnose herbouwt de productievoorspeller met de hand~~ | ✅ **19 aug gedaan.** `bakkerij/model/productie.py` draagt BASIS, KENMERKEN, `prognosekalender`, `open_of_gepland_open`, `wikkel` en `bouw_voorspeller`; contractbouw, diagnose en rapport lenen ze daar. Bronwachten in `tests/test_productie.py` weren een tweede constructie. **En het loste meteen de patstelling op:** met één constructie zegt de diagnose hetzelfde als E4 en is de heropeningscorrectie definitief afgewezen (−0,01 pt totaal, waar hetzelfde script eerder +0,12 pt meldde). Productie bewoog niet: 7,8 % WAPE, −119 €/dag, alle veertien contractantwoorden ongewijzigd |
| ~~`etl_run` wordt geschreven maar door niets gelezen~~ | ✅ **19 aug gedaan**, en niet als contractveld — dat zou bevriezen op "loopt nu", want de sync bouwt het contract zelf. Migratie 010 (`public.sync_stand`) velt het oordeel op het moment van kijken; het platform toont alleen. Zie `todo.md` |
| ~~De runner mist de TGTG-bestanden~~ | ✅ **19 aug gedaan** (het kanaal was bevroren, dus de database was er de bewaarplaats van: `bakkerij/db/bevroren.py`, met een heen-en-terugtest tegen een echte Postgres en een meting tegen de echte Supabase — 1.872 regels, rij voor rij gelijk). **Vervallen 18 sep 2026**: TGTG is uit scope, het kanaal en `bakkerij/db/bevroren.py` zijn verwijderd (zie `beslissingen.md`). Wat nog wél ontbreekt op een runner is `sluitingsdagen.json` — zie `todo.md` |
| ~~`min_train` heeft twee standaardwaarden in één backtestmodule~~ | ✅ **19 aug gedaan**: alle zes de functies in `rolling.py` staan standaard op `MIN_TRAIN`/`STAP`/`HORIZON`. Nagegaan met een AST-scan dat geen enkele aanroeper het argument weglaat, dus het gedrag verandert niet — de val is alleen weg |
| Vier tijdzoneconversies buiten `bakkerij/tijd.py` (bonnen, uren, audit, verzekering) en vier `--vanaf`-standaarden voor dezelfde historiek | De kernfout is gedicht; de adoptie van tijd.py en één `HISTORIEK_START` is opruimwerk voor de eerstvolgende extractsessie |
| Ruff draait op de standaardregelset; de `# noqa: BLE001`-onderdrukkingen suggereren strengheid die er niet is | Een `pyproject.toml` met o.a. `DTZ` (vangt precies de tijdzonefout van vandaag) — maar de nieuwe regelset produceert eerst een schoonmaakgolf; aparte sessie |
| Drie implementaties van "€ 1.234,56" (kwaliteit, contract, opmaak) | Eén module onder alle drie; laag risico, laag gewicht. Sinds 18 aug is de derde `bakkerij/opmaak.py` (was `report/pdf.py`, opgeheven met de WeasyPrint-laag); de twee andere nemen een fractie in plaats van een string en zijn dus geen kopie maar een variant — dat is precies wat het samenvoegen werk maakt |
| `euroBedrag()` in de grafiektooltips formatteert een float (`toFixed`); de echte fix is een `label`-veld op `Punt` in het contract | Raakt contractvorm én beide grafiekcomponenten; meenemen bij de eerstvolgende contractwijziging, samen met de lege-reeks-reden die hierboven al stond. _Bewust niet meegenomen in de contractronde van 19 aug (avond): die twee wijzigingen (`gedeeld`, `kerncijfer.sleutel`) waren additief en raakten geen enkele bestaande waarde; een `label` op `Punt` verandert de vorm van elke grafiekreeks en dat is een andere soort ingreep, acht dagen voor de oplevering_ |
| `import "server-only"` ontbreekt in `contract-bron.ts` (de belofte staat als proza) | Vergt een dependency plus een stub in de testresolver; klein, maar niet gratis — bij de S11-uitrol toetsen |
| ~~De huisstijl-skill claimt een CSP die niet bestaat~~ | **Gedicht 18 aug (docs-ronde): de CSP-bijzin is uit de skill geschrapt** — de regel "lettertype lokaal, nooit via CDN" blijft als beleid staan. Een echte CSP-header blijft het overwegen waard bij de Vercel-deploy (S11-spoor), maar er wordt niets meer geclaimd dat niet bestaat |

---

## Onderhoudsronde 19 augustus (nacht): wat gedicht is, en wat bewust blijft liggen

Vier verkenners (schermtekst, Python-kern, docs, TypeScript/CI/gereedschap), gevolgd door een reparatieronde. **Dezelfde nacht gedicht:** het TGTG-alarm dat op 14 september permanent zou afgaan (`kwaliteit.BEVROREN`); drie afdrukfouten waardoor negentien producttabellen en zeven dagtabellen hun kop verloren in de PDF, plus een afdrukregel die buiten het rapport hele blokken liet verdwijnen (met een bronwacht erop); de klantdata-vangrail die `.png` en `.json.gz` doorliet én "schoon" meldde als het script ontbrak; `als_bool` op de vier kolommen waar de hele berekening op staat (met een test die aantoonbaar faalt zonder de reparatie); de datasleutels van het contract gepind tegenover `platform/lib/contract.ts`; `make controle` en `make help`; twee tsc-vlaggen en zes carets; `isAlles` en `rapport.menuLabel` (dode code, één met test); `na-commit.sh` die na een mislukte commit de vórige meldde; de S11-drift over tien documenten; `docs/overdracht.md`; de inklapronde over alle zes de schermen.

**Bewust open, op volgorde van gewicht:**

| Vondst | Waarom nog open |
|---|---|
| ~~**Hetzelfde briefingpunt staat zesmaal in een volledig rapport.**~~ | ✅ **19 aug (avondsessie) opgelost, en langs de nette route.** Een briefingpunt draagt `gedeeld`, gezet op één plek (de uitgangen van `_versheidspunten`) in plaats van per constructie. De gevreesde "prop door zes schermcomponenten heen" bleek niet nodig: de component zet `data-gedeeld`, en één CSS-regel bij `data-buiten-rapport` verbergt het punt in elk onderdeel behalve het eerste — een briefing die daarna niets eigens overhoudt, valt in zijn geheel weg. Op de schermen verandert er niets. **De grens die erbij hoort:** `gedeeld` betekent "staat op élk scherm", niet "komt vaker voor" — de ontdubbeling hangt aan positie, dus een punt op twee van de zes schermen zou verdwijnen uit elk rapport dat met een van de andere vier begint. Het Deliveroo-punt (status 'actie') krijgt het merk daarom níét en staat er nog tweemaal in; zie `beslissingen.md`. `briefing.leeg` blijft zesmaal in het contract staan: die zin wordt alleen getoond als een scherm géén punten heeft, en dan is ze per scherm een eigen uitspraak |
| ~~**`kerncijfer.<label>` is een vertaalde contractsleutel.**~~ | ✅ **19 aug (avondsessie) opgelost.** `berekening.Kerncijfer` draagt een `sleutel` naast zijn `label`: `omzet_7`, `omzet_30`, `stuks_7`, `gemiddelde_dagomzet`. De vier staan voluit in de labelkaart van `platform/lib/toelichting.ts` — zonder die regels zou het voorvoegselvangnet er "Kerncijfer: Omzet 7" van maken. Twee wachten: de sleutels zijn in beide talen dezelfde, en een test leest het TypeScript-bestand om te toetsen dat elke sleutel daar een label heeft (er is geen andere koppeling tussen die twee bestanden) |
| **De FR-vertaalwacht blokkeert nooit en kan niet in CI.** `vertaalrapport()` print en schrijft `reports/onvertaald.md`, maar faalt niet en zet geen exitcode; en omdat hij echte data nodig heeft, kán CI hem niet draaien | Vandaag theoretisch: `onvertaald.md` meldt "Niets", en NL/FR zijn onafhankelijk vergeleken op alle veldsleutels en uniewaarden. De wacht zelf is goed gebouwd en getest — het is de kóppeling die ontbreekt. Een exitcode erop is één regel, maar dan faalt de nachtrun op een vertaalgat, en dat is een andere afweging dan hij nu maakt |
| **De denies op `Edit`/`Write` naar `data/` staan in `.claude/settings.local.json`**, dat gitignored is; op een verse checkout zijn ze weg. `data/config/` ontbreekt bovendien in de lijst | Harnasconfiguratie is een keuze van de ontwikkelaar en niet van een onderhoudsronde. Genoteerd, niet gewijzigd |
| **De periodevergelijking weet niets van sluitingen** (uit het sluitingskalender-ontwerp, 19 aug). Een week met een bevestigde sluiting naast een week zonder is een oneerlijke vergelijking, en sinds de sluitingskalender wéét het platform dat vooraf | Bewust niet meegebouwd op 19 aug: het is echt werk in de vergelijkingslaag en hoort in een eigen afweging, niet als bijvangst van een invoerscherm. Zelfde status: kandidaat, geen belofte |
| **Een briefingpunt "volgende week bent u twee dagen dicht"** (idem): klein, binnen de grens van signalering (geen advies), en de invoer bestaat nu | Bewust niet meegebouwd op 19 aug; kandidaat voor daarna, samen met het punt hierboven af te wegen |
| **Het dode `if:`-veld in `.claude/settings.json`** (`"if": "Bash(git commit:*)"`) leest als een werkende filter; beide hooks filteren zelf omdat die filter daar niet werkt | Idem: harnasconfiguratie. De hooks zijn wél gerepareerd |
| **`noUncheckedIndexedAccess` geeft 28 fouten**, tweederde in tests | Middel werk in werkende code. Niet de week vóór een oplevering |
| **Python-lockfile ontbreekt** (`requirements.txt` gebruikt bereiken); elke nachtrun installeert vers uit PyPI | Reëel, maar een lockfile verkeerd invoeren breekt CI op de dag zelf, en de bovengrenzen dekken het ergste af |
| **Een falende nachtsync maakt onvoorwaardelijk een issue aan**; een week ongeldige sleutel geeft zeven issues | Nieuwe logica in de enige stap die de faalmelding draagt. Een fout dáár maakt het stiller in plaats van luider — precies de verkeerde richting |
| **Negen tautologische asserts** (kolomlijsten die de implementatie herhalen, drempels die als invoer én als verwachting uit dezelfde constante komen) | Vals vertrouwen, geen risico. Puur testwerk, kan na de oplevering |
