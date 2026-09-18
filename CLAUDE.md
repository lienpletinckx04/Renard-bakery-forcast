# asklien-bakkerij - projectgids voor Claude Code

## Wat dit project is
Een **CFO-platform** voor een bakkerij. Opdrachtgever is asklien.ai (Lien Pletinckx), die op haar beurt Renard Bakery als eindklant heeft. Fase 1 is afgebakend in `docs/scope.md`, de volgorde staat in `docs/plan-fase1.md`.

De deliverable is een **toepassing met een login**: een database die dagelijks bijwerkt uit de bronsystemen, een berekeningslaag, een API, en een web-UI in de huisstijl van het merk. Daarin zit ook een prognose per product per dag. (Het scherm heette tot 12 augustus 2026 "Vooruitblik"; die naam is overal vervangen door "Prognose", tot in de contractsleutels.)

**De baklijst is geschrapt op 12 augustus 2026.** Eerdere versies van deze gids zeiden dat wie dit als dashboardproject behandelt het verkeerde ding bouwt. Dat is achterhaald: het dashboard *is* het ding. Het denkwerk over de beslislaag blijft in `model-ontwerp.md` staan omdat het de waarde van een latere fase bepaalt, maar het wordt in fase 1 niet gebouwd.

Wat het platform onderscheidt van de Odoo-rapportering die er al is: de kanalen die Odoo niet kent (Deliveroo), de marge die Odoo niet berekent, en de prognose die Odoo niet heeft.

## Harde regels (niet-onderhandelbaar)

1. **Klantdata gaat nooit in een modelcontext.** Geen rijen, geen klantnamen, geen transactiedetail in prompts. Wel toegestaan: kolomnamen, dtypes, aantallen, datumbereiken, null-percentages, aggregaten, foutmeldingen zonder data. Bij twijfel: aggregeer eerst, stuur dan.
2. **Klantdata gaat nooit de git-repo in.** `data/` is gitignored. Controleer `git status` vóór elke commit. Als er ooit een export in de index belandt, is dat geen kleine fout.
3. **Wat wél naar de gehoste database gaat, is geaggregeerde productverkoop.** Geen `partner_id`, geen klantnaam, geen adres, geen bonnotitie. De extractie vraagt die velden nooit op, en dat blijft zo. Zie `scope.md`, "Waar de database hangt".
4. **De UI rekent nooit.** Elk cijfer op een scherm komt uit de berekeningslaag via het contract. Staat de logica in de UI, dan bestaat ze niet voor de app van fase 2 en niet voor een export.
5. **Niets bouwen dat buiten `docs/scope.md` valt.** Als iets nuttig lijkt maar buiten scope ligt: noteer het in `docs/vragen-aan-lien.md` en bouw het niet.
6. **Elke aanname die niet uit de data blijkt, gaat in `docs/aannames.md`** met de naam van wie ze moet bevestigen.
7. **Nooit een voorspelling presenteren die niet uit een backtest komt.** Een voorspelling zonder backtest is een mening.
8. **Een geblokkeerd cijfer wordt getoond als onbeschikbaar, met de reden.** Niet geschat, niet stilzwijgend weggelaten. Een CFO-platform dat een marge toont die niemand heeft aangeleverd, is erger dan een platform dat geen marge toont.

## De lagen (volgorde niet omgooien)
```
1. Inlaadlaag      -> Odoo naar het canonieke datamodel, met tests
2. Database        -> Postgres, migraties in de repo, herbouwbaar met één commando
3. Berekening      -> nachtelijk, alle afgeleide tabellen opnieuw uit de feiten
4. API / contract  -> genummerde JSON-antwoorden, klein en voorgeaggregeerd
5. Toegang         -> login, sessies, twee rollen
6. Pas dan de UI   -> schermen lezen uit het contract, en rekenen niet
7. Prognose        -> baselines en backtest-harnas VÓÓR het model
```
Stap 4 vóór stap 6 is de belangrijkste regel van het platform: een scherm dat zelf query't, kan de app later niet hergebruiken.
Binnen stap 7 geldt: baselines en harnas vóór het model. Zonder harnas weet je niet of je model iets doet.

## App-gereedheid (fase 2 bouwt de app, fase 1 maakt haar mogelijk)
- De kern is headless: de berekening produceert tabellen, de UI leest ze.
- Eén contract, meerdere consumenten. Web-UI nu, app later, zelfde antwoord.
- Geen bedrijfslogica in de presentatielaag.
- Alles herbouwbaar uit de bron met één commando. Geen toestand die alleen in de UI leeft.
- Antwoorden klein en voorgeaggregeerd. Een telefoon haalt geen 50.000 rijen op.
- Geen app-framework kiezen in fase 1. De investering is het contract, niet de technologie.

## Huisstijl
Vastgelegd in de logogids van de klant, niet vrij in te vullen. De uitgewerkte regels staan in `.claude/skills/huisstijl/SKILL.md`; hieronder de kern.
- Beige `#F4EDE6` draagt het vlak, bordeaux `#A6192E` is het merkaccent, geel `#F2F0A1` en warm grijs `#C9C0AF` zijn steunkleuren, wit `#FFFFFF` is kaart en paneel, zwart `#000000` is inkt.
- Typografie **Inter Tight**, hiërarchie via gewicht. Secundair het handgeschreven **Des Montilles** — maar dat fontbestand is niet aangeleverd en zit niet in de repo; tot het er is, is Des Montilles nergens bruikbaar.
- **Alle cijfers staan in zwart.** Getallen worden nooit gekleurd, ook niet bij stijging of daling. Richting komt uit het teken en een pijl, niet uit kleur. Kleur zit alleen in de vlakken en lijnen van een grafiek, en bordeaux is daar identiteit en nooit betekenis.
- **Eén verfijning, sinds 12 augustus 2026:** op een effen bordeaux vlak — naar de flyer uit de logogids — staat het cijfer in wit en het label in beige. Voorwaarde: zo'n vlak ligt vast op een positie (het eerste kerncijfer, het weektotaal) en verhuist nooit mee met goed of slecht nieuws. Daarmee blijft de onderliggende regel onverkort overeind: de kleur van een cijfer draagt nooit betekenis, ze volgt alleen de drager waarop het cijfer staat. Buiten zo'n vast bordeaux vlak is een niet-zwart cijfer een schending.
- Rustig, veel witruimte, dunne lijnen, geen kaders om alles heen.

## Technische keuzes
- Python 3.11+, pandas, numpy voor de inlaad- en berekeningslaag. Geen zware ML-stack tenzij de backtest bewijst dat het nodig is.
- Postgres als database. Migraties in de repo, geen wijzigingen met de hand.
- Geen notebooks in de repo. Verkennend werk mag in een notebook, wat blijft is een module met een test.
- Elke transformatie is een functie met een test. Geen scripts die alleen bij jou draaien.
- Tijdzone Europe/Brussels. Datums zijn `date`, geen `datetime`, tenzij het uur echt betekenis heeft.
- Geld in `Decimal` of in centen als int. Nooit floats voor euro's in output.

## Datamodel (canoniek, alles wordt hiernaartoe genormaliseerd)
```
verkopen:  datum | filiaal_id | product_id | kanaal | aantal | omzet_excl_btw
kanaalkost: kanaal | product_id (of groep) | commissie_pct | uitbetaling_per_eenheid
kalender:  datum | weekdag | feestdag | schoolvakantie | brugdag | evenement
kosten:    productgroep | criterium | pct             (kostenmodel, door de beheerder; brutomarge = 100 − som)
winkels:   winkel | filialen                          (optionele indeling; zonder config één geheel)
weer:      datum | locatie | tmax | neerslag_mm | ...                (fase 2)
```
`kanaal` is een van: `winkel`, `deliveroo`, `overig`. De kanaalsplitsing is niet cosmetisch: elk kanaal heeft een andere marge, en het platform toont die apart.

**Alle drie de kassa's tellen mee.** De aanname dat twee van de drie andere concepten waren is op 12 augustus gemeten en weerlegd: alle drie verkopen hetzelfde bakkerijassortiment in vrijwel dezelfde verhoudingen (zie `data-audit.md` addendum 3). Filteren op één kassa zou tweederde van de bakkerijomzet weggooien. Ze worden opgeteld tot één geheel; `filiaal_id` blijft in het model bestaan tot de opdrachtgever bevestigt of het registers of vestigingen zijn (vraag 18).

## Wat je nooit doet
- Een cijfer tonen dat niet uit de berekeningslaag komt.
- Een deliverable uitbreiden omdat het "maar een uurtje" is.
- Credentials in code, in commits, of in een chatbericht.
- De eindklant rechtstreeks contacteren. Alles loopt via Lien.
- Iets over de andere betrokkenen zeggen in de gedeelde WhatsApp-groep dat je niet tegen hen zou zeggen.

## Sessiediscipline
- Start elke sessie met de jongste dagboekentry (`docs/dagboek.md`) en de blokkadelijst in `docs/todo.md` — de sessiestart-hook zet die twee al automatisch in de context — plus `docs/vragen-aan-lien.md` voor wat er bij de opdrachtgever ligt.
- Eindig elke werkdag met een dagboek-entry. Die gaat dezelfde dag naar de opdrachtgever.
- Bij scope-druk: verwijs naar `docs/scope.md`, noteer in `docs/vragen-aan-lien.md`, bouw niet.
