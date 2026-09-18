# Stand van zaken

_Bijgewerkt 18 augustus 2026, na de inspectieronde. Geschreven als overdracht: wie hier verder werkt — met een ander account, een ander model of een andere kop koffie — moet aan dit document genoeg hebben. De secties onder de streep zijn ouder dan de kop; het dagboek en `volgende-sessie.md` zijn leidend, en **de actuele blokkadelijst staat alleen in `todo.md` (S-nummers)** — de O-tabellen hieronder zijn de stand van 12–13 augustus en worden niet meer bijgehouden._

Opleverdatum fase 1: **27 augustus 2026**. Nog negen kalenderdagen.

> **Inspectieronde 18 augustus.** Vier verkenners over de hele opdracht (Python-kern, platform, docs, database/sync/CI), gevolgd door een reparatieronde. De grootste vondsten: de dagsleutel van het kernextract stond in UTC waar de rest van de ketting Brussels rekent (gerepareerd, `bakkerij/tijd.py`); onder `AUTH_BRON=supabase` verwierp `lees()` elke sessie meteen weer (gerepareerd — het platform was in die modus onbereikbaar); `schema_migraties` was de enige tabel zonder RLS (gerepareerd, plus `revoke` voor `authenticated` overal en check-constraints in migratie 007); een gevallen poortwachter liet geen spoor in `etl_run` (gerepareerd); en de nachtelijke cron stond klaar om elke nacht rood te lopen omdat de runner de TGTG-bestanden en de beheerconfig niet heeft — de planning staat nu bewust uit tot dat is opgelost (zie `todo.md`, infra-lijst). Er draait sinds vandaag ook een test-CI op elke push. Details: dagboek 18 aug (tweede entry) en `beslissingen.md`.

> **Handover 17 augustus (tweede sessie).** Alles wat zonder input van anderen kon, is af en gepusht. Spoor A en B van 17 aug (eerste sessie): Frans compleet, briefing-eenheden, audit-restpunten, blok 8 droog (nachtelijke sync + `write_date`-poortwachter), blok 12 (`AUTH_BRON=supabase`) en blok 22 (`PROGNOSE_SCENARIOS=1`) voorbereid tot op de sleutel; blok 9 geschrapt op vraag van Lien. Spoor D (tweede sessie): beheerdraaiboek en oplevering geactualiseerd tegen de code, rauwe bronnamen gelabeld in beide talen, en de **visuele steekproef is blijvend gereedschap** (`scripts/visuele_steekproef.mjs`: draaiende dev-server, getekende sessiecookie, echt Chrome, alle schermen × beide talen × dicht/open). De browserautomatisering die hieronder nog ontbrak, bestaat dus.
>
> **De steekproef ving acht bevindingen; zes gerepareerd, beide wachten aangescherpt.** Het afgekapte datumlabel bleek een latent gebrek van álle lijngrafieken; de Franse productmix toonde Nederlands dat hardgecodeerd in de UI stond (schending regel 4 — komt nu uit het contract); percentages staan in beide lagen als "7,8 %" uit één functie; browsertab en `lang` volgen nu de taalcookie. De vertaalteller classificeert expliciet in plaats van op woordlengte te raden, de platformwacht leest ook literals in props-expressies. Zie dagboek 17 aug (beide entries) en `beslissingen.md`.
>
> **Latten:** de volledige suite, lint en typecheck groen (de aantallen meldt `make test` zelf — zie de regel onder §1), contract in beide talen herbouwd, hersteekproef (24 schermafbeeldingen) nagekeken op elk gerepareerd punt.
>
> **Eerste taak voor wie oppikt: `volgende-sessie.md`.** Alles wat rest hangt aan anderen: S11 (databasewachtwoord — het draaiboek voor die dag staat klaar; ná ~21 aug haalt de databasetrack de 27e niet), S12/S13 (login), S1 (Deliveroo-CSV's, elke dag permanent verlies), vraag 55 (scenario's tonen). De workflow `nachtelijke-sync.yml` faalt elke nacht leesbaar zolang de secrets ontbreken; desnoods disabled tot S11.
>
> _Correctie 18 augustus op de regel hierboven: de nachtelijke planning staat sinds de inspectieronde van 18 aug bewust uit (het schedule-blok in de workflow is uitgecommentarieerd), dus er faalt niets meer elke nacht. Handmatig starten kan via workflow_dispatch. Zie `beheerdraaiboek.md`._
>
> _Correctie 19 augustus, en die haalt het grootste deel van de twee regels hierboven onderuit: **S11 is binnengekomen op 18 augustus.** Diezelfde avond zijn de migraties toegepast, is de database gevuld (316.469 rijen) en staat het platform online op `https://renard-bakery.vercel.app` met de database als contractbron. De vijf workflow-secrets staan gezet en de runner-invoer is op 19 augustus geregeld; wat nog rest vóór de planning aan mag, is één handmatige run in GitHub Actions die groen komt. Wat wél openstaat: S12/S13 (login), S1 (Deliveroo-CSV's, elke dag permanent verlies) en vraag 55 (scenario's tonen)._

---

## 1. Wat er draait

Het platform is een werkende keten van bron tot scherm. Eén commando bouwt alles opnieuw:

```
make canoniek     bronbestanden  -> canoniek datamodel + kalender
make contract     canoniek       -> één JSON-antwoord per scherm
make ui           contract       -> het platform op localhost:3000
make test         de volledige suite
make lint         bakkerij/ + tests/ + scripts/
make backtest     de lat voor de prognose
```

Het aantal tests staat hier bewust niet: `make test` meldt het zelf, en een getal in een document is binnen een week achterhaald. `make lint` dekt sinds 12 augustus ook `scripts/` (O18) — daarvóór was die map alleen door de ruff-hook gedekt en dus weggedreven.

| Laag | Stand | Waar |
|---|---|---|
| **Inlaadlaag** | Odoo (kassa) en TGTG draaien. Deliveroo ontbreekt (O2) | `bakkerij/sources/`, `scripts/odoo_extract.py`, `scripts/tgtg_extract.py` |
| **Canoniek model** | 221.375 rijen. `datum · filiaal_id · product_id · product_naam · kanaal · aantal · omzet_excl_btw` + kalenderlaag | `bakkerij/canoniek.py` |
| **Database** | **Draait.** Supabase (14 aug, `eu-north-1`), migraties toegepast op 18 aug en de feiten geladen (316.469 rijen); het platform leest zijn contract eruit (`CONTRACT_BRON=db`) | `db/migraties/`, `bakkerij/db/` |
| **Berekening** | Pure functies, databaseloos, met tests | `bakkerij/berekening.py` |
| **Contract** | Eén genummerd JSON-antwoord per scherm (overzicht, kanalen, producten, marge, prognose, stand), plus de winkelindex. Geen float in een bedrag, `onbeschikbaar` als eersteklas veld. De envelope draagt sinds deze ronde naast `bijgewerkt_op` ook `gemeten_tot`: de jongste gemeten open winkeldag, of `null` | `bakkerij/contract.py`, `platform/lib/contract.ts` |
| **Toegang** | **Werkt.** Login, sessie van 12u, bewaking vóór de router | `platform/lib/auth.ts`, `platform/proxy.ts` |
| **Schermen** | Zes schermen; acht routes, waarvan zeven achter de login (alleen het aanmeldscherm erbuiten; de achtste is `/rapport`, sinds 18 aug een weergave van de gekozen schermen in plaats van een PDF-bestand — eveneens bewaakt). Huisstijl, lezen uitsluitend uit het contract | `platform/app/` |
| **Prognose** | 7 dagen dagomzet, band uit de backtest. **7,8% WAPE** op dagniveau (sinds 15 aug; was 8,4% bij de eerste meting), 20,2% per product per dag | `bakkerij/model/`, `bakkerij/backtest/` |

**Aanmelden:** gebruikers `lien` en `kwinten`, beide rol `beheerder`. Het wachtwoord staat niet in de repo — alleen een PBKDF2-afdruk in `platform/.env.local`, dat gitignored is. Een nieuwe gebruiker of een nieuw wachtwoord:

```
printf '%s' '<wachtwoord>' | node scripts/maak_gebruiker.mjs <naam> beheerder
```

> **Het huidige wachtwoord is een testwachtwoord en is gedeeld tussen twee mensen.** Het moet vervangen zijn vóór de eindklant het platform ziet, en dan met één wachtwoord per persoon.

### Wat er bewust leeg is

Het margescherm is leeg met opgave van reden, en dat is nu **gemeten en niet aangenomen**: van de 425 producten heeft er **3** een kostprijs in Odoo. Zie punt 4 hieronder — er is een uitweg.

---

## 2. Wat er niet draait, en waarom dat pijn doet

**Online staat het platform niet.** Dat blokkeert op meer dan Vercel-toegang: `platform/contract/` is gitignored omdat het geaggregeerde klantomzet is, dus een git-deploy komt zonder data aan. Drie wegen, en de keuze is aan de opdrachtgever:

1. **Supabase eerst** (O1) — de data komt uit de database, de deploy leest die. Dit is ook de architectuur die er hoort te staan.
2. **Eenmalig een snapshot committen** voor een staging-deploy. Snel, maar het zet klantomzet in de repo, tegen harde regel 2. Niet doen zonder uitdrukkelijke opdracht.
3. **Een tunnel naar de lokale server.** Ook snel, maar dan lopen de cijfers over een derde partij zonder verwerkersovereenkomst.

Aanbeveling: 1, en tot dan lokaal testen. Functioneel is dat identiek.

---

> **De secties 3 tot en met 6 hieronder zijn de stand van 12–13 augustus, bewaard als achtergrond.** Veel van wat erin als open staat is intussen dicht (de periodekiezer en het categoriescherm zijn gebouwd, de kalender zit in het model, categorieprognoses en trackrecord staan op het scherm, `platform/mock/` is verwijderd, de visuele steekproef bestaat en draait, en O11/O8/O12/O13/O14/O15/O17/O19/O21 zijn 13–18 aug afgehandeld — zie `open-punten.md`). Wat nog echt open is, staat in `todo.md`.

## 3. Wat er ongebruikt ligt (gemeten, 12 augustus)

Het dashboard is vandaag een omzetrapport. Dat is niet omdat de data ontbreekt: **vier dimensies liggen ongebruikt in het verzekeringsarchief dat al op schijf staat** (`data/raw/verzekering/2026-08-12/`).

| Dimensie | Wat er is |
|---|---|
| **Bonnen** | 678.309 bonnen, gem. € 10,54, mediaan € 7,50, 2,3 regels per bon, 1.258 bonnen per dag |
| **Uur** | `date_order` 100% gevuld, verkoop van 7u tot 18u lokaal |
| **Categorieboom** | 33 categorieën met hiërarchie, inclusief zes seizoenscategorieën |
| **Betaalwijze** | 91,0% Bancontact · 7,5% cash · 1,4% "Facture fin du mois pas payé" |

Zes categorieën dragen 80% van de omzet: Koffiekoeken 28,9% · Lunch 16,4% · Desembroden dagelijks 13,9% · Individueel gebak 7,9% · Pistolets & baguettes 6,8% · Croûtes 6,8%. Driekoningen alleen is 3,2% van de jaaromzet.

ABC op product: **85 producten = 80% van de omzet, 173 producten samen = 5%.**

Gemeten en verworpen: kortingen (0,03% van de regels), retouren (0,075%), kassa-vergelijking (drie registers in één winkel meet wachtrij, geen bedrijfsvoering).

### De negen voorstellen, met de volgorde die ik zou aanhouden

Voorstel **0** is een randvoorwaarde en geen scherm: *inzoomen op dag of week is een contractbeslissing.* Het contract bestaat nu uit zes bestanden met vaste vensters (7, 30, 56 en 90 dagen, 4 weken, 12 maanden). Zoomen betekent dat een antwoord een periode als parameter krijgt. Zolang de database ontbreekt, is de weg een **periodekubus**: de berekening zet elke dag, week, maand en kwartaal vooraf uitgerekend klaar, en het scherm *kiest* een rij in plaats van te rekenen. Dat bewaart harde regel 4 en het is dezelfde vorm die de API later krijgt.

| # | Voorstel | Werk | Volgorde |
|---|---|---|---|
| 3 | Periodekiezer op elk scherm (dag/week/maand/kwartaal/jaar + vergelijkingsperiode) | middel | **eerst** |
| 1 | ~~Omzetontbinding: bonnen × bonwaarde~~ **gebouwd 13 aug**, als "Klanten of mandje?" op het Dagoverzicht | klein | ✅ |
| 2 | Categoriescherm met drill-down Brood → Desembroden → product, sorteerbaar en filterbaar | middel | **eerst** |
| 4 | ~~ABC-analyse van het assortiment~~ **gebouwd 13 aug**, als "Waar de omzet op leunt" op Productmix | klein | ✅ |
| 7 | Seizoenspieken (Driekoningen, Sinterklaas, Pasen, Valentijn, Moederdag) | klein | daarna |
| 5 | Intradagprofiel: omzet per uur per weekdag | middel | later |
| 6 | Uitverkoopdetectie: producten waarvan de laatste bon uren vóór sluiting valt | middel | later |
| 8 | Signalenpaneel "wat is er opvallend": dagen buiten 2σ, producten die >30% zakten | middel | later |
| 9 | Betaalmix, met de openstaande facturen apart | klein | later |

### De prognose krachtiger maken, in deze volgorde

1. **De kalender in het model.** De prognose negeert vandaag feestdagen, brugdagen en schoolvakanties, terwijl die kolommen al in de kalenderlaag staan. Een weekdaggemiddelde voorspelt 24 december als een gewone dinsdag. Goedkoopste echte verbetering, en meetbaar in de backtest.
2. **Trackrecord op het scherm.** Wat deden de vorige prognoses tegenover de werkelijkheid. Het harnas bestaat al.
3. **Prognose per categorie.** Zes categorieën dekken 80%; per product blijft het op 20,2% WAPE steken.
4. **Horizon instelbaar** (7 / 14 / 28), met een band die per horizon breder wordt zoals de backtest hem meet.

---

## 4. Twee dingen die vandaag veranderd zijn en die actie vragen

**De marge is onmogelijk gemeten, maar er is een uitweg.** 3 van 425 producten hebben een kostprijs. We hebben geen 425 kostprijzen nodig — **tien categorieën dekken 95% van de omzet.** Vraag 19 zou daarop geherformuleerd moeten worden: een invulbaar lijstje van een tiental categoriemarges in plaats van een onmogelijke oefening. Dan kan het margescherm mogelijk toch aan in fase 1.

**We gooien 3,5 maand historiek weg.** Het extract loopt vanaf 2025-01-02, het archief begint 2024-09-19. Die maanden bevatten Sinterklaas en Kerst 2024 — precies de periode waarvan we nu één waarneming hebben. Eén hernieuwde extractie verdubbelt de seizoenswaarnemingen voor november en december. Kost: één commando.

---

## 5. Open vragen en punten

### 5a. Blokkeert het kritieke pad naar 27 augustus

**Deze tabel is vervangen door de S-lijst in `todo.md` en wordt hier niet meer bijgehouden.** Stand 18 aug in één regel: O1 is binnen (project 14 aug) en opgevolgd door **S11** (databasewachtwoord, de enige databaseblokkade); O2 = **S1** en blijft het urgentste punt (dagelijks permanent verlies); O3 is binnen (13 aug); O4 (G5/G6) staat open bij de eindklant.

### 5b. Vragen aan de opdrachtgever — bepalen wat het platform mag beweren

| # | Vraag | Bij wie | Gevolg als ze open blijft |
|---|---|---|---|
| O5 | Wordt een deel van het assortiment maar op bepaalde dagen aangeboden? (vraag 44) | bakkerij, via Lien | De prognose blijft beperkt tot 103 kernproducten (84,1% van de stuks) |
| O6 | Sluitingskalender vooruit (vragen 45, 46) | bakkerij, via Lien | De prognose slaat de gemeten sluitingsdagen over, maar neemt voor de dagen buiten het gemeten bereik aan dat de winkel open is, en zegt dat op het scherm (aanname `prognose.sluitingsdagen`) |
| O7 | Brutomarges — **te herformuleren naar categorieniveau**, zie punt 4 (vraag 19, poort G1) | eindklant, via Lien | Margescherm blijft leeg met reden |
| O9 | Het bestelkanaal: € 1,8 miljoen B2B naast de kassa. In of buiten scope? (vraag 43) | Lien | Nu buiten scope. Erin betekent een vierde kanaal en een scopewijziging |
| O10 | Schoolvakanties: Franstalig, Nederlandstalig of beide? (vraag 47) | Lien | Kalenderkolom ontbreekt; in Elsene lopen de twee regimes niet gelijk |
| — | Wachtwoordbeleid: één wachtwoord per persoon vóór oplevering, en wie beheert ze? | Lien / Kwinten | Vandaag één gedeeld testwachtwoord voor twee mensen |
| — | Verwerkersovereenkomst en exitregeling bij het hostingmodel (vraag 41) | Kwinten → Lien | Staat al op de blokkadelijst als S10 |

### 5c. Wat wij zelf moeten beslissen

| # | Punt | Voorstel |
|---|---|---|
| **O11** | Het laatste verkoopuur per product per dag zit niet in het canonieke model, terwijl `deliverables.md` A2 het eist. Het is het signaal voor censurering (O8) | **Toevoegen.** De data staat in het archief (`date_order` is 100% gevuld) — het is bij het aggregeren weggevallen, niet bij het ophalen |
| **O8** | Censurering: meet de kassa vraag of alleen verkoop? Als de croissants om tien uur op zijn, telt de kassa de rek en niet de klant | Meten hoe vaak het patroon voorkomt en het als bevinding rapporteren. Wordt voorstel 6 |
| O12 | `onbeschikbaar.veld` is een technische sleutel en wordt zo op het scherm getoond ("prognose.startpunt") | **In herstel, deze ronde.** Eindtoestand: de sleutel komt niet meer op een scherm. De omzetting naar een leesbaar label gebeurt in de presentatielaag; het contract houdt `onbeschikbaar` als `[{veld, reden}]`. Het oudere voorstel om een `label` aan het contracttype toe te voegen is daarmee vervallen — een label is tekst, geen cijfer, en hoort dus niet in het contract |
| O13 | De voettekst leest altijd `contract/overzicht.json` voor `bijgewerkt_op`, ongeacht het actieve scherm | **In herstel, deze ronde.** Eindtoestand: elk scherm draagt zijn eigen envelope, en de voettekst toont `bijgewerkt_op` en `gemeten_tot` van het antwoord dát op dat scherm staat |
| O14 | Dodemansknop ontbreekt. De nachtelijke run is best-effort; niemand merkt dat het platform stilstaat | Bouwen bij B6 |
| O15 | Datakwaliteitswachters (B6) bestaan niet als laag | Bouwen |
| O17 | De prognose begint op de dag na de laatste meting, niet op vandaag. Bij een sluiting of een mislukte synchronisatie voorspelt hij deels het verleden | **In herstel, deze ronde.** De horizon schuift mee met vandaag; de regel staat hieronder uitgeschreven |
| O18 | `make lint` dekt `scripts/` niet, de ruff-hook wel. Twee latten | **Afgehandeld, 12 aug.** `scripts/` staat in het lint-doel en de map is schoon: 22 openstaande ruff-fouten inhoudelijk opgelost, niet met een `noqa` weggezet. Enige uitzondering op de opruiming was `scripts/contract_bouw.py`, en die was al schoon |
| O19 | `deliverables.md` klopt op tien plaatsen niet meer (A2, A3, A6, A7, A8, D1, E1, E2, G1, G2) | Bijwerken |
| O21 | Aanname A11 over `filiaal_id` kan dicht nu vraag 18 beantwoord is | Bijwerken in `aannames.md` |
| — | Rollen: `lien` en `kwinten` zijn allebei `beheerder`. De tweede rol heet sinds 18 aug `lezer` (niet meer `bekijker`) en is de enige niet-beheerdersrol; wat hij níét mag, is vandaag alleen het kostenmodel opslaan | Beslissen wat een lezer verder níét mag zien |

#### De horizonregel voor de prognose, uitgeschreven (vastgelegd 12 augustus)

Dit is de beslissing achter O17. De prognose begon op de dag na de laatste meting; bij een sluiting of een mislukte synchronisatie voorspelde ze daarmee deels het verleden. De regel wordt:

```
start = max(gemeten_tot + 1 dag, vandaag)
loop van start vooruit; sla elke dag over waarvoor de kalender zegt
    winkel_gemeten == True EN winkel_open == False
neem zo HORIZON dagen
```

Dagen buiten het gemeten bereik (`winkel_gemeten == False`) gelden als onbekend en worden dus meegenomen. Dat is niet nieuw en het is geen stilzwijgende keuze: het is de al gedocumenteerde aanname `prognose.sluitingsdagen`, die op het scherm staat en die verdwijnt zodra de sluitingskalender vooruit er is (O6).

Twee velden in het contract bestaan enkel om harde regel 4 te bewaren — de UI mag niet rekenen, ook niet tellen:

- `prognose.data.weektotaal_dagen` — het aantal dagen dat in de weeksom zit. Zonder dit veld zou het scherm de dagen moeten tellen om de som te kunnen uitleggen, en dan rekent het scherm.
- `overzicht.data.weekdagprofiel[].meetdagen` — het aantal dagen achter elk punt van het profiel. Een gemiddelde over twee dagen en een gemiddelde over vijftig zien er anders even hard uit; dit veld maakt het verschil zichtbaar zonder dat het scherm iets uitrekent.

En in de envelope van alle antwoorden: `gemeten_tot`, de ISO-datum van de jongste gemeten open winkeldag, of `null`. `bijgewerkt_op` blijft wat het was — het moment van bouwen. De twee zijn niet hetzelfde en werden op één scherm door elkaar gehaald; dat is precies O13.

### 5d. Gesloten sinds gisteren

- **Vraag 18: drie kassa's, één winkel.** Definitief. Alle drie tellen mee en worden opgeteld.
- **Vraag 19 deels:** de kostprijzen bestaan niet in Odoo. Gemeten, geen aanname meer.
- **De naam:** "Vooruitblik" heet voortaan "Prognose", doorgevoerd tot in de contractsleutels.
- **O16:** het agendaspoor is gebouwd vóór vraag 46 beantwoord is, op uitdrukkelijke instructie. Geïsoleerd en optioneel; de kost bij afwijzing is één map en één import.
- **O20:** `scope.md` "Eén kassa" is rechtgezet.

---

## 6. Wat er nog openstaat in de code

- **O23 (eerst):** wachters op bon- en uurniveau; `kwaliteit.wachters()` heeft `bonnen_df`/`uren_df` al in de signatuur.
- **De schermen worden sinds 17 aug wél visueel nagelopen** (`scripts/visuele_steekproef.mjs`, zie de handover-box bovenaan); de opmerking hieronder over het aantal kaarten op het Dagoverzicht blijft het bekijken waard. De volgorde en de indeling zitten volledig in de twee `page.tsx`-bestanden — de contractlaag legt geen indeling vast, dat is met opzet.
- **Wie de schermen zonder browser wil natrekken:** start `npm run dev`, teken een sessie met `teken()` uit `lib/auth.ts` (draaien met `node --env-file=.env.local`), en haal de route op met die cookie. `next build` doet dit niet voor je: alle routes zijn dynamisch en worden dus niet vooraf gerenderd.
- **Taak 6:** het agendaspoor afmaken — `AGENDA_ICS_URL` in `.env.example`, ophaalfunctie met time-out, inhaken in `canoniek_bouw.py` achter de optionele vlag, afwijkingsrapport in `reports/`.
- ~~De mockbestanden in `platform/mock/`~~ — verwijderd op 14 aug.
- De toegangslaag heeft sinds 13 augustus negen tests (`platform/tests/auth.test.ts`), met het dotenv-expand-gat als eerste. End-to-end (307/200/307) blijft handwerk.

**Valkuilen voor wie hier werkt** (alle drie deze nacht in het echt geraakt):
1. `.env`-bestanden gaan door variabele-expansie (@next/env): een `$` in een waarde wordt stil opgegeten. Geen `$` in secrets of afdrukken.
2. `pytest | tail -1` maskeert de exitcode via de pipe; er is zo één keer met een falende test gecommit. Altijd `pytest > /dev/null 2>&1 &&` vóór een commit.
3. De permissielaag weigert het lezen van `data/`-bestanden — dat is de bedoeling (harde regel 1). Metingen doe je met een script dat alleen aggregaten print.

---

## 7. Vaste leesvolgorde bij het oppikken

De leesroute staat op één plek, in `start-hier.md`, zodat er niet twee lijsten uit elkaar kunnen groeien: start-hier → `volgende-sessie.md` → `todo.md` (de ene blokkadelijst) → `scope.md` → `CLAUDE.md`. Dit document is achtergrond bij die route, geen vervanging ervan.
