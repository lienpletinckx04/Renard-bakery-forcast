# Plan fase 1

_Geschreven 12 augustus 2026, herzien dezelfde dag nadat de baklijst uit de scope ging en het CFO-platform het product werd. Dit document zegt in welke volgorde er gebouwd wordt en waarom die volgorde niet vrijblijvend is. Wat er gebouwd wordt, staat in `scope.md`._

> **Stand 19 augustus 2026: het plan is grotendeels uitgevoerd.** Per stap, in één regel; de actuele blokkades (S-nummers) staan in `todo.md`.
>
> - **Stap 0** (omgeving, extract, TGTG-pdf's): ✅ af — extract van 12 aug, 250 pdf's geparst, alles reproduceerbaar.
> - **Stap 1** (kassavraag): ✅ gesloten 12 aug — gemeten: alle drie de kassa's zijn de bakkerij en tellen op tot één geheel (data-audit addendum 3).
> - **Stap 2** (datamodel en database): ✅ af — canoniek model, het Supabase-project bestaat (14 aug), de migraties staan in de repo en zijn op 18 augustus toegepast; de database staat vol (316.469 rijen) en het platform leest eruit.
> - **Stap 3** (berekening en contract): ✅ af — één genummerd JSON-antwoord per scherm plus de winkelindex, herbouwbaar met `make alles`.
> - **Stap 4** (toegang): interim-login draait (rollen `beheerder`/`lezer`); Supabase Auth is gebouwd achter `AUTH_BRON=supabase` en wacht op S12/S13.
> - **Stap 5** (schermen): ✅ af — zes dashboardschermen achter een login (acht routes, waarvan zeven bewaakt; alleen het aanmeldscherm erbuiten), tweetalig; marge toont onbeschikbaar tot de eerste kosteninvoer (add-on sinds 12/13 aug).
> - **Stap 6** (prognose, tot 12 aug "vooruitblik"): ✅ af — 7,8% WAPE dagomzet uit de rolling-origin backtest; per product (20,2%) is een backtestbevinding, geen scherm.
> - **Stap 7** (oplevering): `oplevering.md` en `beheerdraaiboek.md` staan; de afsluiting (F3: sleutels, `.env`, `data/`) is open tot 27 aug.

## De stelling in één alinea

Een platform wordt van onder naar boven gebouwd: bron, model, database, berekening, contract, toegang, scherm. De verleiding is om met het scherm te beginnen, want dat is het enige wat de klant ziet. Dat is ook precies hoe je eindigt met schermen die elk hun eigen query doen, cijfers die onderling niet kloppen, en een app in fase 2 die alles opnieuw moet.

## Wat de volgorde bepaalt

**Eerst het contract, dan het scherm.** Een scherm dat zelf rekent, is een scherm dat de app later niet kan hergebruiken en waarvan het cijfer afwijkt van de export. De contractlaag is geen ceremonie: ze is het verschil tussen aanhaken en herbouwen.

**Eerst het harnas, dan het model.** Binnen de prognose geldt onverkort: baselines en rolling-origin backtest vóór er een model komt. Voor een bakkerij is "dezelfde weekdag vorige week" een sterke baseline, en dat vroeg weten is een besparing.

**Eerst wat niet geblokkeerd is.** Op 12 augustus stonden alle acht poorten open (`scope.md`); geen ervan blokkeerde stap 0 en 1. G7 — waar de database komt te staan — blokkeerde alles vanaf stap 2 en was daarmee de eerstvolgende beslissing; ze is op 14 augustus genomen en opgevolgd door S11, die op 18 augustus binnenkwam. Zie voor de actuele stand de poortentabel in `scope.md` en de S-lijst in `todo.md`.

## Stap 0 — Omgeving, extract, en de TGTG-pdf's

**Doel:** alle beschikbare bronnen staan lokaal en reproduceerbaar.

- `make setup`, `.env` invullen met de Odoo-sleutel uit de wachtwoordmanager
- `make odoo-audit` als verbindingstest, `make extract` voor de historiek vanaf 2025-01-01
- TGTG: 250 pdf's parsen naar dag × pakkettype × aantal, plus de uitbetaling per pakket uit Factuur en Rekeningoverzicht
- `make test`, `make check-data`

**Waarom nu:** de audit draaide live tegen de preprod en liet niets op schijf achter. Aanname A14 zegt dat die preprod een bevroren kopie kán zijn, en de omgeving is al één keer herbouwd. Een lokaal extract maakt het werk onafhankelijk van wat daar gebeurt.

**Waarom de pdf's meer werk zijn dan ze lijken:** zeven jaar documenten van dezelfde leverancier veranderen doorgaans een keer van vorm. De parser moet dat merken en niet stilzwijgend nul teruggeven. Reken op een dag, met tests op minstens één document per jaar.

**Af wanneer:** de Odoo-reeks staat in canonieke vorm in `data/raw`, de TGTG-reeks staat als dagtabel, en de audit-cijfers zijn reproduceerbaar.

## Stap 1 — Welke kassa is de bakkerij

G2 blokkeert het hele datamodel en wacht op Lien. Wachten is niet hetzelfde als niets doen. Vier toetsen, in volgorde van bewijskracht:

| Toets | Wat het zegt |
|---|---|
| **Correlatie met de TGTG-volumes** | De pakketten zijn bakkerijoverschot. De kassa die meebeweegt met de TGTG-dagen is de bakkerij. Dit is de sterkste toets, want het bewijs komt uit een tweede bron |
| **Productmix per kassa** | Koffiekoeken, brood en pistolets tegenover dranken en lunch |
| **Openingsuur per kassa** | Een bakkerij begint 's ochtends vroeg, een horecazaak piekt later. `date_order` bevat het uur |
| **Gemiddelde bon** | Bakkerij laag met veel bonnen, ander concept hoger met minder |

De uitkomst vervangt de bevestiging niet, maar ze maakt de vraag aan Lien scherper: niet "zijn het drie winkels" maar "wij meten dat Kassa N de bakkerij is, klopt dat". Dat is in één regel te beantwoorden.

**Af wanneer:** er ligt één kassa-id met vier onderbouwingen, en de vraag staat bij Lien.

## Stap 2 — Datamodel en database

**Geblokkeerd tot G7 beslist is.** Zolang niet vaststaat waar de database staat en op wiens naam, wordt er geen omgeving opgezet.

- Canoniek datamodel: `verkopen`, `kalender`, `kanaalkost`, `marges`
- `kanaal` is vanaf de eerste regel een volwaardige dimensie: `winkel`, `tgtg`, `deliveroo`, `overig`. Deliveroo blijft leeg en wordt getoond als onbeschikbaar met reden
- Sluitingsdagen als *geen meting*, niet als nul. 149 van 688 dagen hebben geen enkele bon, geklonterd in augustus en tussen Kerst en Nieuwjaar. Wie die als nulverkoop inleest, laat het platform een instorting tonen die er niet is
- Groeperen gebeurt op product-id, nooit op naam: `Cappuccino` en `Sandwich` bestaan elk twee keer met een eigen id en substantieel volume op beide
- `Bag` (44.204 stuks) is verpakking, geen product. De categorie `All` (64.187 stuks) is Odoo's "niet ingedeeld" en krijgt een eigen behandeling
- Migraties in de repo, database herbouwbaar met één commando

## Stap 3 — Berekening en contract

- Nachtelijke run die alle afgeleide tabellen opnieuw opbouwt uit de feiten: omzet, stuks, gemiddelde bon, per dag, kanaal, productgroep en product
- Jaar-op-jaar vergelijking. De data leent zich ervoor: januari tot juli bestaat twee keer, met ongeveer acht procent omzetgroei bij licht dalend bonaantal. Dat verschil is prijs of assortiment, en het hoort zichtbaar te zijn zonder dat iemand het uitrekent
- Marge zodra G1 open is. Tot dan is het veld leeg met een reden, niet geschat
- Contractlaag: per scherm één genummerd JSON-antwoord, klein en voorgeaggregeerd, met tests op de vorm

**Af wanneer:** één commando bouwt alles opnieuw, en het contract ligt vast met tests. Nog geen scherm.

## Stap 4 — Toegang

- Login met e-mail en wachtwoord, wachtwoordherstel, verlopende sessies
- Twee rollen: lezer en beheerder
- Aanmeldingen gelogd

Klein maar het bestaat: hier komen persoonsgegevens in het spel — die van de gebruikers, niet die van de klanten van de bakkerij. Dat hoort in het verwerkingsregister van de eindklant, en het staat in het opleverdocument.

## Stap 5 — De schermen

Pas nu, en alleen op het contract van stap 3.

- Kerncijfers, tijdreeks, periodevergelijking, top-producten, kanaalverdeling, marge, prognose
- Huisstijl: beige vlak, bordeaux als merkaccent, Inter Tight, **alle cijfers zwart**. Richting via teken en pijl, nooit via kleur
- Elk geblokkeerd cijfer toont zich als onbeschikbaar met de reden erbij

## Stap 6 — De prognose

- Drie baselines: naive, seasonal naive, voortschrijdend gemiddelde per weekdag
- Rolling-origin backtest over meerdere origins verspreid over het jaar, nooit willekeurig gesplitst, afgerekend in euro's en per product gerapporteerd
- Pas daarna een model, en alleen als het de baselines materieel verslaat
- De censurering blijft gelden: er is geen productie- en geen restregistratie, dus het model voorspelt verkoop en niet vraag. Dat hoort bij elke uitspraak die eruit komt. De TGTG-reeks is de enige meting van de aanbodkant die er is

## Stap 7 — Oplevering

- Opleverdocument: waar komt elk cijfer vandaan, wat toont het platform niet, hoe wordt het beheerd
- Backtest-rapport in euro's, met de beperkingen expliciet
- Sleutels roteren, `.env` verwijderen, controleren dat `data/` leeg is, en schriftelijk vastleggen of de ruwe data verwijderd of overgedragen wordt

## Wat er elke dag gebeurt

- Beginnen met `dagboek.md` en `vragen-aan-lien.md`
- Eindigen met een dagboekentry die dezelfde dag naar de opdrachtgever gaat. Vier regels. "Geblokkeerd door" blijft nooit leeg omdat het ongemakkelijk is
- Elke aanname naar `aannames.md`, elke beslissing naar `beslissingen.md`

## De drie manieren waarop dit plan faalt

**De schermen slokken de tijd op.** Een dashboard is oneindig verfijnbaar en elke verfijning voelt als vooruitgang. De schermen zijn klaar wanneer ze de cijfers uit het contract tonen.

**G7 blijft hangen.** Zonder beslissing over waar de database staat, staat alles vanaf stap 2 stil. Dat is geen technische vraag maar een eigendoms- en factuurvraag, en die duurt langer dan mensen denken.

**Deliveroo wordt een open einde.** De export kan niet door de bakker zelf opgehaald worden; het loopt via de accountmanagers en dus via wachten. Het platform moet zonder dat kanaal opleverbaar zijn, met het gat zichtbaar in plaats van weggewerkt.

---
*Aangemaakt 12 augustus 2026, herzien dezelfde dag na de scopewijziging.*
