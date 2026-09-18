# Beheerdraaiboek (F2)

_Stand 19 augustus 2026. Hoe het platform draait, wat er periodiek moet
gebeuren, en wat te doen als iets faalt. Het Supabase-project bestaat sinds
14 augustus (S2 is daarmee vervallen) en het databasewachtwoord (S11) kwam
binnen op 18 augustus: de database staat vol, en het platform staat online op
`https://renard-bakery.vercel.app` en leest zijn cijfers daaruit. Lokaal
draaien kan nog steeds en blijft de route voor ontwikkelwerk. Het verslag van
de uitrol staat onderaan, het draaiboek zelf in `setup-supabase.md`._

## De keten, van bron tot scherm

```
make tgtg          TGTG-pdf's (data/raw/TGTG overzicht) -> data/interim
make extract       Odoo -> data/raw (vereist .env met Odoo-sleutel)
make canoniek      bronnen -> canoniek model (+ agenda-verrijking als
                   data/raw/agenda.ics bestaat)
make contract      canoniek -> platform/contract/*.json (NL) én
                   platform/contract/fr/ (FR): één antwoord per scherm,
                   twee keer
make ui            contract herbouwen + dev-server op http://localhost:3000
make dev           alleen de dev-server, zonder contractbouw
make alles         canoniek + contract + backtest
make sync          de nachtelijke ketting handmatig (vergt Odoo-sleutels
                   en SUPABASE_DB_URL; zie hieronder)
make sync-droog    dezelfde ketting zonder Odoo en zonder schrijven
```

Dat is de keten, niet de volledige lijst. Sinds 19 augustus 2026 is er
`make help`: dat toont alle negenendertig doelen met de eerste regel van hun
uitleg, rechtstreeks uit de Makefile. Het lijstje hierboven blijft staan omdat
het de vólgorde toont — welk doel na welk — en dat is precies wat `make help`
niet kan. Voor "welk doel bestaat er ook alweer" is `make help` de bron; het
lijstje hierboven bijwerken hoeft dus niet meer als er een doel bijkomt.

Controles: **`make controle`** is de volledige lat en draait alles wat CI ook
doet — `check-data`, `lint`, `make test` (Python én platform, inclusief
typecheck) en de productiebouw. Dat is het commando vóór een commit. De
onderdelen blijven los te draaien; `make check-data` draait bovendien als hook
bij elke commit.

**Het CFO-rapport staat niet in dit lijstje, en dat is sinds 18 augustus 2026 de
bedoeling.** Er is geen `make rapport-pdf` meer en er wordt geen PDF-bestand meer
gebouwd. Het rapport is een bladzijde in het platform geworden: klik rechtsboven
op **Rapport**, vink aan welke onderdelen erin moeten, en kies in het rapport
**Afdrukken of PDF** — daar zit "Opslaan als PDF" in het venster van de browser.
Twee dingen zijn daarmee weg: het rapport kan niet meer ouder zijn dan de cijfers
op het scherm ernaast (het leest hetzelfde contract, bij elk verzoek), en er is
geen tweede opmaaklaag meer die van de schermen kon afwijken. Wie na een
herberekening een nieuw rapport wil, herlaadt de bladzijde; er valt niets te
bouwen.

## De nachtelijke sync (blok 8 — gebouwd, wacht op één handmatige run)

De ketting staat in `scripts/nachtelijke_sync.py` en hergebruikt de bestaande
stappen: poortwachter → extract → canoniek → laden → contractbouw →
contract laden. Elke run schrijft één rij in `etl_run` (bron
`nachtelijke-sync`): gestart, geslaagd of gefaald, met de reden. Een run die
halverwege sterft laat een "bezig"-rij achter — dat is de dodemansknop die
het platform toont.

- **De poortwachter kijkt naar `write_date`.** Eén goedkope vraag aan Odoo
  (de jongste `write_date` op de kassaorders) naast de jongste geslaagde run
  in `etl_run`, met één uur speling voor het klokverschil. Niets gewijzigd —
  bijvoorbeeld tijdens de zomersluiting — dan stopt de job meteen, met alleen
  een logregel. **Bewust géén incrementeel extract:** het extract aggregeert
  aan de bron tot dag × product × kassa, en een dag die half opnieuw wordt
  opgehaald en dan geüpsert overschrijft het volledige dagtotaal met een
  gedeeltelijk — stille corruptie. Het volledige extract is goedkoop genoeg
  om bij elke echte wijziging integraal te draaien (`bakkerij/db/sync.py`
  legt dit uit).
- **De workflow** is `.github/workflows/nachtelijke-sync.yml`, en **de
  nachtelijke planning staat sinds 18 augustus uit** (het schedule-blok —
  cron 01:30 UTC, 03:30 Belgische zomertijd — is in het workflowbestand
  uitgecommentarieerd). De reden waarom hij uitstond, is sinds 19 augustus
  weg: de runner miste de TGTG-bestanden en de beheerconfig, en die invoer is
  intussen geregeld — het bevroren TGTG-kanaal komt uit de database terug, de
  sluitingslijst staat in git, het kostenmodel wordt in de database bewaard,
  en de krimpwacht van de contractlader weigert nu ook een inhoudelijk
  verarmde schrijfbeurt. **Wat rest is één handeling die een mens hoort te
  doen en geen commit:** in GitHub één keer *Run workflow* (workflow_dispatch)
  drukken en die run groen zien; de optie "volledig" slaat de poortwachter
  over en laadt hoe dan ook. Pas daarna de drie schedule-regels in het bestand
  activeren — een planning aanzetten die nog nooit één keer geslaagd is,
  levert elke nacht een rode job op waar niemand naar kijkt. De workflow
  ververst eerst de schoolvakanties (`scripts/vakanties_ververs.py`) en draait
  dan de sync. Als de planning aanstaat: de planner van GitHub Actions is best
  effort en kan tientallen minuten later vuren; daarom toont het platform
  wanneer de cijfers voor het laatst ververst zijn (`etl_run`) in plaats van
  te beloven dat het elke nacht lukt.
- **Vijf secrets, alle vijf verplicht** (Settings → Secrets and variables →
  Actions): `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY`,
  `SUPABASE_DB_URL`. Ze staan sinds 18 augustus gezet. Ontbreekt er één, dan
  faalt een handmatige run meteen en leesbaar; er lekt niets, de
  foutmeldingen bevatten nooit de verbindingsstring zelf.
- **Het contract gaat sinds 18 augustus mee de database in.** Na het laden
  van de feiten bouwt de sync het contract (beide talen) en schrijft
  `scripts/contract_laad.py` alle antwoorden naar `contract_antwoord`
  (migratie 006; sleutel scherm × taal × winkel, JSON identiek aan de
  bestandsvorm, eigen `etl_run`-rij onder bron `contract`). Het platform
  leest die tabel alleen met `CONTRACT_BRON=db` — zonder die vlag blijft de
  bestandsroute bit voor bit dezelfde, en een test legt dat vast
  (`platform/tests/contract-bron.test.ts`). Los van de sync kan het ook met
  de hand: `make db-contract` (en `make db-contract-droog` zonder sleutel).
- `make sync-droog` bewijst de hele ketting lokaal zonder sleutels: canoniek,
  het laadpad en het contractpad in droge modus, op de lokale data. Dat is de
  toets die vandaag al kan.

## GitHub zet de planning na zestig dagen stilte vanzelf uit

Dit is de stille faalmodus van dit platform, en hij treft precies de toestand
waarin het na de oplevering hoort te verkeren: die van een repo waar niemand
nog aan werkt.

- **Wat er gebeurt.** GitHub schakelt een workflow met een `schedule:`-trigger
  automatisch uit na **zestig dagen zonder activiteit in de repository**. De
  workflow blijft gewoon bestaan en ziet er ongewijzigd uit; hij vuurt alleen
  niet meer. Dit speelt pas zodra de nachtelijke planning aanstaat — vandaag
  staat het `schedule:`-blok nog uitgecommentarieerd, zie hierboven.
- **Waarom.** De teller kijkt naar de repo, niet naar de workflow: commits,
  handmatige runs, en dergelijke. Een opgeleverd platform dat maandenlang
  correct doet wat het moet doen, produceert niets van dat alles. Wie het met
  rust laat zoals het bedoeld is, zet de synchronisatie dus uit.
- **Hoe je het merkt.** Niet aan een rode run: er faalt niets, er gebeurt
  niets, en er komt dus ook geen faalmelding en geen issue. Wat het wél meldt
  is de dodemansknop (migratie 010, view `public.sync_stand`): die oordeelt op
  het moment van kijken en zet de stand op `let_op` en daarna op `fout`, en
  vanaf dat moment staat er in de voettekst van elk scherm **"Let op:
  synchronisatie"** en op Instellingen de zin voluit. Zie de uitleg bij de
  nachtelijke sync hierboven; hij is precies voor dit soort uitval gebouwd.
- **Hoe je het herstelt.** GitHub → **Actions** → in de lijst links
  **nachtelijke-sync** → **Enable workflow**. Draai er daarna één keer
  *Run workflow* achteraan, zodat je ziet dat de ketting weer loopt en de
  cijfers bij zijn; de planning pakt de nacht erna vanzelf weer op.
- **Hoe je het voorkomt.** Elke activiteit in de repo zet de teller op nul.
  Eén handmatige run per kwartaal volstaat. Reken er niet op dat dat vanzelf
  gebeurt: de dodemansknop is hier de vangrail, niet het geheugen van een
  beheerder.

## Periodieke handelingen

| Wanneer | Wat | Hoe |
|---|---|---|
| wanneer er TGTG-pdf's zijn (geen vaste aanvoer meer, zie hieronder) | TGTG-pdf's binnenbrengen | pdf's in `data/raw/TGTG overzicht/`, dan `make tgtg && make alles` |
| na elke bron-update | keten verversen | `make alles` |
| bij nieuwe kosteninvoer | beheerder stelt kostencriteria samen en vult per productgroep percentages in op Instellingen | opslaan herrekent het contract vanzelf en zet de invoer in `data/config/kostenmodel.json` — dat bestand (net als `winkels.json` voor een eventuele winkelindeling) **bestaat pas zodra de beheerder het via het scherm invult**; zolang er niets is ingevuld, is er ook niets om te back-uppen. Vanaf de eerste invoer: **meenemen in elke back-up**, het is de enige handinvoer. (Het oudere `marges.json` is de v1-vorm met één brutomarge per groep; die invoer gaat niet verloren en verschijnt als "Totale kost") |
| maandelijks met de hand; de sync-workflow doet het ook bij elke run (nu alleen handmatig — de nachtelijke planning staat uit, zie hierboven) | schoolvakanties verversen | `make vakanties` — haalt beide regimes bij de OpenHolidays-API. Nieuwe toekomstige periodes gaan er automatisch in; wijzigingen aan het verleden worden geweigerd tot je ze bewust toepast met `make vakanties FORCEER=1`, en dan hoort `make backtest-rapport` erachteraan omdat het trackrecord verschuift. Na elke wijziging: `make contract`. Loopt de kalender ooit te kort, dan meldt het prognosescherm dat zelf (dekkingswacht) |
| bij een agenda-feed (vraag 46) | `AGENDA_ICS_URL` in `.env`, dan `make agenda && make canoniek` | het afwijkingsrapport verschijnt in `reports/` |

## TGTG: bevroren kanaal, handwerk blijft mogelijk

**Blok 9 (de ingestmailbox) is op 17 augustus geschrapt op vraag van Lien**,
inclusief de periodieke TGTG-maandmail en de Deliveroo-commissiemail (S7/S8/S9
zijn vervallen). Het gevolg, eerlijk opgeschreven: zonder aanvoer **bevriest
het TGTG-kanaal op de geparste historiek tot en met juli 2026** en veroudert
het vanaf dan zichtbaar. Het scherm behandelt dat niet als "geen data": een
kanaal mét historiek buiten het venster meldt per kanaal tot wanneer zijn data
loopt en dat er sindsdien niets meer is aangeleverd (harde regel 8).

Er gaat niets onherstelbaar verloren: TGTG bewaart de documenten zelf in
MyStore. Wie het kanaal weer wil laten meelopen, haalt de pdf's daar op en
volgt het handmatige pad uit de tabel hierboven — pdf's in
`data/raw/TGTG overzicht/`, dan `make tgtg && make alles`.

## Twee datums waarop iets ophoudt

Op 19 augustus 2026 nagemeten, en hier genoteerd omdat het de twee dingen zijn
die vanzelf verlopen zonder dat er iets kapotgaat dat je ziet.

**24 augustus 2026 — de bestandslijst is op, en dat is sinds 19 augustus geen
klif meer.** `config/sluitingsdagen.json` loopt tot en met 23 augustus. Tot
19 augustus betekende dat: daarna kent de prognose geen sluitingen meer, en op
19 december staat er een gewone vrijdagomzet op 25 december. Sindsdien bestaat
het scherm **Sluitingsdagen** (in het menu, boven Prognose): een beheerder
bevestigt daar per feestdag open of dicht, voegt eigen periodes toe, en zet
desgewenst een vaste wekelijkse sluitingsdag. De datums zelf blijven de invoer
van de opdrachtgever (**vraag 64**) en worden niet door ons geraden: welke
dagen de zaak dicht is, is een gegeven van de zaak en geen aanname van ons.
Zolang niemand bevestigt, zegt het prognosescherm per dag eerlijk dat er geen
antwoord is.

**10 mei 2027 — de Franstalige schoolvakanties zijn op.**
`bakkerij/features/schoolvakanties.json` dekt VL tot 2028-03-05 maar FR maar tot
2027-05-09, en het productiemodel draait op het Franstalige regime. Vanaf 10 mei
2027 is de vakantievlag voor toekomstige dagen overal onwaar terwijl de
modelkaart "met schoolvakantiecorrectie" blijft claimen. De dekkingswacht meldt
dat op het prognosescherm, dus ook hier verdwijnt niets stilzwijgend.

`make vakanties` lost het op zodra de bron verder reikt — op 19 augustus 2026
gedraaid en toen leverde het niets: de OpenHolidays-API publiceert het
Franstalige regime zelf nog niet verder. Het is dus geen vergeten commando maar
een wachtstand. Draai `make vakanties` opnieuw in het voorjaar van 2027, en
daarna `make contract`.

Let op bij het automatiseren van dat eerste: de nachtelijke workflow drááit
`vakanties_ververs.py` wel, maar commit het resultaat niet — het staat er zelfs
bij in het workflowbestand. Op de runner werkt het dus één run lang en is het
daarna weer weg. Wie dit permanent wil maken, heeft een aparte job met
`contents: write` nodig, en dat is een rechtenwijziging op de nachtrun.

## De sluitingsdagen bijhouden

De prognose zwijgt over dagen waarvan bekend is dat de zaak dicht is. Sinds
19 augustus 2026 is de gewone route daarvoor het scherm **Sluitingsdagen** in
het platform zelf (in het menu, boven Prognose): een bevestigingslijst van de
Belgische feestdagen twaalf maanden vooruit — per dag `open`, `dicht` of nog
niet beantwoord — plus eigen periodes (jaarlijkse sluiting, verbouwing) en één
vaste wekelijkse sluitingsdag als regel. Bewerken kan alleen een beheerder;
een lezer ziet dezelfde stand als woorden. Drie dingen om te weten:

- **Een opslag staat meteen op het scherm en telt mee in de prognose vanaf de
  eerstvolgende nachtelijke herrekening** — dezelfde cadans als het
  kostenmodel, en het scherm zegt dat er ook bij. Wie het vandaag nog in de
  prognose wil zien, draait `make canoniek && make contract && make
  db-contract` met `CONTRACT_BRON=db`.
- **"Bevestigd open" is ook een antwoord.** Het haalt voor die dag het
  voorbehoud "geen sluiting bekend" van het prognosescherm; alleen
  onbeantwoorde dagen houden dat voorbehoud. Onbekend is niet hetzelfde als
  open, en het scherm behandelt ze ook verschillend.
- De invoer staat in Postgres (`sluitingsdag`, `sluitingsregel`, migratie 011)
  en wordt geschreven via één functie (`bewaar_sluitingskalender`, migraties
  012/014) — één verzoek, één transactie, en de schrijvende rol heeft geen
  rechtstreekse tabelrechten. De rangorde van de bronnen is **agenda >
  database > bestand**: een iCal-agenda (vraag 46) gaat voor, en een dag die
  op het scherm bevestigd open is, wint van een dicht-dag uit het bestand.

**Het bestand `config/sluitingsdagen.json` blijft bestaan** als eenmalige
invoer en historisch record — het is op 19 augustus met `make db-sluitingen`
naar de database overgezet (dat doel weigert sindsdien zolang de database
gevuld is; `FORCEER=1` alleen voor een bewust herstel). Het bestand staat
**in git**, de enige uitzondering op de regel dat config buiten de repo
blijft: het zijn de dagen dat de zaak dicht is, geen transacties, geen
personen, geen bedragen. Eén gevolg om te onthouden, en het geldt óók voor de
reden op het scherm: het `reden`-veld belandt in de geschiedenis en op beide
taalversies van het scherm, dus daar horen geen namen of persoonlijke
omstandigheden in — laat het veld dan liever leeg.

```json
{
  "sluitingen": [
    {"van": "2026-08-17", "tot": "2026-08-23", "reden": "Jaarlijkse sluiting"},
    {"van": "2026-12-25", "reden": "Kerstmis"}
  ]
}
```

- `tot` mag weg voor één dag. `reden` komt letterlijk op het scherm te staan,
  dus schrijf hem zoals de klant hem zou lezen. Let op: het is vrije tekst en
  het platform vertaalt geen handinvoer — dezelfde reden verschijnt dus ook
  letterlijk op het Franstalige scherm ("Jaarlijkse sluiting" blijft daar
  Nederlands). Kies de bewoording met beide lezers in gedachten.
- Na een wijziging: `make canoniek && make contract`. De canoniekbouw drukt af
  hoeveel periodes en dagen hij gelezen heeft en tot wanneer de lijst reikt.
- **De volgorde wordt sinds 17 augustus afgedwongen:** is de sluitingslijst
  jonger dan de canonieke kalender, dan stopt `make contract` (en dus ook
  `make ui`) hard, met de juiste opdracht erbij ("Draai eerst: make
  canoniek"). Anders zou het scherm de nieuwe dekking melden terwijl de
  prognose nog met de oude kalender rekent — twee waarheden op één scherm.
- **Een fout in dit bestand stopt de bouw**, met de regel erbij. Dat is bewust:
  een sluitingsdag die door een typefout niet meedoet, levert een
  omzetverwachting op voor een dag dat de deur dicht is.
- Overlappende periodes worden geweigerd. Voeg ze samen; twee redenen voor
  dezelfde dag is er één te veel.
- **Vul aan vóórdat de horizon erin loopt.** De prognose kijkt zeven dagen
  vooruit. Staat een sluiting er pas in op de dag zelf, dan heeft het scherm
  er een week lang omzet voor voorspeld. Het scherm zegt zelf tot wanneer de
  lijst reikt — die regel is er precies voor.
- Er is ook een wacht de andere kant op (sinds 15 augustus): eindigt de
  méting in een gesloten reeks die de lijst niet verklaart, dan zegt het
  scherm dat, met het aantal dagen erbij. Hij corrigeert niets — het platform
  verzint geen sluitingskalender — maar hij zwijgt niet meer.
- Zodra de klant de iCal-agenda deelt (vraag 46), vult die dezelfde kolom en
  wordt deze lijst een aanvulling in plaats van de enige bron. De reden uit de
  agenda gaat dan voor.

## De taal van de schermen

Het platform is tweetalig (NL/FR). De knop staat linksonder op elk scherm, ook
op het aanmeldscherm. Wat je moet weten als beheerder:

- **Het contract wordt twee keer gebouwd**, één keer per taal:
  `platform/contract/` is Nederlands, `platform/contract/fr/` is Frans. Eén
  `make contract` doet beide. De cijfers zijn identiek — alleen de labels en de
  redenen verschillen.
- `make contract` drukt af hoeveel teksten nog in het Nederlands staan in de
  Franse map, en schrijft de volledige lijst naar `reports/onvertaald.md`.
  Sinds 17 augustus bestaat wat overblijft uit productnamen (zie hieronder);
  het getal hoort nooit meer te stijgen.
- Een vertaling los je op in `bakkerij/contract.py` (voor teksten uit het
  contract) of in `platform/lib/taal.ts` (voor de vaste schermteksten). Niet in
  `reports/onvertaald.md` — dat is uitvoer.
- **Productnamen worden niet vertaald.** Ze komen uit Odoo en staan zoals de
  bakkerij ze heeft ingevoerd; een vertaald assortiment zou namen tonen die op
  geen enkele kassabon staan.

## Prognosescenario's (blok 22 — gebouwd, niet zichtbaar)

De scenariomotor (`bakkerij/model/scenario.py`) staat klaar in afwachting van
vraag 55 (scenario's in fase 1 of fase 2?). Draai je `make contract` met
`PROGNOSE_SCENARIOS=1` in de omgeving, dan krijgt het prognose-antwoord een
veld `scenarios` met drie kalendervarianten — deze week alsof het vakantie is,
alsof het geen vakantie is, en zonder de vakantiecorrectie — allemaal uit
dezelfde gebackteste voorspeller. Een scenario is nooit een vrije schuif;
alleen de kalenderínvoer wisselt, de echte prognose blijft het anker. Zonder
de vlag bestaat het veld niet, en **geen enkel scherm toont de scenario's
zolang vraag 55 openstaat** — voorbereiden mag, tonen niet.

## Als iets faalt

| Symptoom | Eerste stap |
|---|---|
| Scherm zegt "poort 3000 weigert" | de dev-server draait niet: `make dev` (bewust los van de contractbouw — een Python-fout is geen UI-fout) |
| Build faalt op ontbrekende JSON | `make contract` nooit gedraaid op deze machine: `make canoniek && make contract` |
| `make contract` stopt op "config/sluitingsdagen.json is jonger dan de canonieke kalender" | de bedoelde volgorde-stop: draai `make canoniek` en dan opnieuw |
| Kosten opgeslagen maar Margebewaking beweegt niet | de herrekening faalde; draai `make contract` in de terminal en lees de fout. De invoer zelf staat veilig in `data/config/kostenmodel.json` (aangemaakt bij die eerste opslag) |
| Wachter op "fout" of bron op "stil" op Instellingen | de toelichting bij de wachter zegt wat er gemeten is; begin bij de bron (extract verouderd?) |
| Een (handmatige) sync-workflow-run faalt | de vijf secrets staan sinds 18 aug gezet, dus een rode run is geen verwachte stand meer: lees het joblog en de jongste rij in `etl_run`. De nachtelijke planning zelf staat nog uit tot die eerste handmatige run groen is (zie hierboven) |
| "network is unreachable" bij db-doelen | vrijwel altijd de verkeerde verbindingsstring: gebruik de Session pooler (poort 5432), niet de directe IPv6-verbinding — `bakkerij/db/verbinding.py` legt de drie valkuilen uit |
| Het rapport is leeg of mist een onderdeel | de keuze staat in het adres (`/rapport?deel=…`); een onbekende waarde wordt genegeerd en zonder geldige waarde bevat het rapport álle onderdelen. Vink opnieuw aan via **Onderdelen** in het rapport |
| De afdruk mist de uitleg die op het scherm ingeklapt staat | het rapport klapt die zelf open; gebeurt dat niet, dan is JavaScript uitgeschakeld — klap de blokken met de hand open vóór het afdrukken |
| De afdruk heeft geen bordeaux vlakken | dat is ontwerp: op papier draagt de haarlijn de structuur en blijft bordeaux in koppen, staven en lijnen. Zo ziet de afdruk er hetzelfde uit of "achtergronden meenemen" in het printvenster nu aanstaat of niet |

## Toegang en geheimen

- Gebruikers staan in `PLATFORM_GEBRUIKERS` (`platform/.env.local`):
  `naam:rol:<zout>.<afdruk>`, afdruk maken met `scripts/maak_gebruiker.mjs`.
  Rollen: `beheerder` (mag kosten opslaan), `lezer` (tot 18 augustus heette
  die rol in code en docs "bekijker"; het woord is overal gelijkgetrokken met
  scope D6 en vraag 57).
- **`AUTH_BRON` kiest de aanmeldlaag.** Standaard (of `AUTH_BRON=omgeving`)
  toetst het platform tegen `PLATFORM_GEBRUIKERS`. Met `AUTH_BRON=supabase`
  wisselt alléén de functie `verifieer()` — zoals `platform/lib/auth.ts`
  vanaf dag één beloofde: Supabase Auth toetst e-mail en wachtwoord, de rol
  komt **strikt uit `app_metadata.rol`** ("beheerder" of "lezer"), en
  zonder geldige rol komt er géén sessie — geen terugval op "lezer", want
  dat zou een configuratiefout verzwijgen als geldige toegang. De sessie
  zelf blijft de onze: eigen ondertekende cookie (`PLATFORM_SESSIE_SLEUTEL`),
  twaalf uur geldig, bij elk verzoek getoetst. Vereist
  `NEXT_PUBLIC_SUPABASE_URL` en `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` in de
  omgeving. **Omschakelen wacht op S12** (zelfregistratie uit, alleen een
  Administrator kan dat zetten) **en S13** (de gebruikerslijst, met per
  persoon de rol in `app_metadata`); tot dan blijft de omgevingslaag gewoon
  werken.
- Het gedeelde testwachtwoord **moet vervangen zijn vóór de eindklant het
  platform ziet** (stand-van-zaken §1 Aanmelden).
- Geheimen (`.env`, `.env.local`) staan nooit in git; bij oplevering rotatie
  en overdracht volgens F3.

## De gehoste versie (uitgevoerd op 18 augustus 2026)

Dit hoofdstuk was tot 18 augustus een draaiboek voor de dag dat het
databasewachtwoord zou binnenkomen. Die dag is geweest: de stappen hieronder
zijn uitgevoerd, de database staat vol (316.469 rijen) en het platform staat
online op `https://renard-bakery.vercel.app` met de database als contractbron.
Wat er staat, blijft nuttig als recept — voor een tweede omgeving, voor een
herbouw, of voor wie na de oplevering moet begrijpen hoe dit is opgezet.
Herhalen doe je zo:

1. `SUPABASE_DB_URL` (pooler-hostname, poort 5432, gebruiker
   `postgres.<project-ref>`, `sslmode=require`) in `.env`.
2. `make db-migreer` — idempotent; alle migraties uit `db/migraties/`, RLS per
   tabel. Bij de uitvoering op 18 augustus was de tweede ronde leeg, zoals het
   hoort.
3. `make db-laad` — canoniek model naar Postgres, en `make db-contract` —
   de contractantwoorden erachteraan. De droge modi
   (`db-droog`/`db-laad-droog`/`db-contract-droog`) toetsen alles zonder
   verbinding.
4. Kosteninvoer: het kostenmodel gaat naar de databasevorm uit migratie 005
   (die vervangt `marge_instelling` uit 004). Sinds 19 augustus schrijft het
   kostenformulier op de gehoste omgeving zelf naar de database, via één
   functie die het hele model in één transactie bewaart; de rol waarmee het
   platform schrijft heeft geen schrijfrechten op de tabellen zelf.
5. De vijf GitHub-secrets zetten (gedaan op 18 augustus) en de workflow één
   keer handmatig draaien (workflow_dispatch, optie "volledig"). Pas als die
   run groen is, de nachtelijke planning aanzetten (het schedule-blok in het
   workflowbestand activeren); daarna kijkt `etl_run` mee. **Dit is de enige
   stap die nog openstaat.**
6. O13: `CONTRACT_BRON=db` plus `NEXT_PUBLIC_SUPABASE_URL` en
   `SUPABASE_SECRET_KEY` in de Vercel-serveromgeving (de leesroute loopt
   via PostgREST; het databasewachtwoord blijft weg van Vercel — zie
   `stack.md`, "Waar de secrets staan"). Op 18 augustus omgezet en nagemeten:
   elk scherm in beide talen uit beide bronnen opgehaald en vergeleken,
   inhoudelijk identiek. Blok 12 omschakelen (`AUTH_BRON=supabase`) wacht nog
   op S12 en S13. Draaiboek: `setup-supabase.md`.
