# Demodraaiboek — oplevering 27 augustus 2026

> Doel van de dag: aanvaarding van D1–D9 volgens `scope.md`, § "Oplevering en aanvaarding".
> Twee clausules dragen de demo: **een geblokkeerd cijfer dat zich als onbeschikbaar toont mét reden, telt als antwoord**, en **de prognose wordt aanvaard op het backtest-rapport, niet op smaak**.
> Dit draaiboek beschrijft wie wat klikt, in welke volgorde, met welke boodschap per scherm, en wat de terugvalposities zijn. Het is geschreven om óók te werken als er op de demodag nog iets openstaat — sinds 18 augustus is dat niet meer de database (die staat vol en het platform leest eruit), maar wel S1 (Deliveroo), S12/S13 (login) en vraag 55.

## De dag ervoor (26 aug, checklist)

- [ ] **`make extract` (en `make extract-bonnen`, `make extract-uren`) vóór `make alles`.** `make alles` is `canoniek → contract → backtest` en haalt zélf géén verse data op: zonder deze stap demonstreer je op het extract van 7 augustus, en toont een platform dat "dagelijks bijwerkt" een meetgat van drie weken. Vergt de Odoo-sleutel in `.env`.
- [ ] `make alles` groen op de demomachine (canoniek → contract → backtest), daarna niets meer aanraken.
- [ ] `make test` en `make test-ui` groen. Het criterium is groen, niet een aantal: `make test` meldt het aantal zelf. De databasesuite (`tests/test_db_echt.py`) wordt overgeslagen zonder `TEST_DB_URL`; overgeslagen is daar de juiste uitkomst, niet een gemiste test.
- [ ] `make steekproef` draaien en de 24 beelden (6 schermen × 2 talen × 2 standen) één keer doorbladeren — geen verrassingen op de dag zelf.
- [ ] `gemeten_tot` in het contract controleren: klopt de datum met de jongste aanvoer, en zegt de UI dat ook?
- [ ] Het rapport één keer helemaal doorlopen: **Rapport** → alle onderdelen → **Afdrukken of PDF**, en één exemplaar **op papier** meenemen. Het CFO-rapport fysiek overhandigen is het goedkoopste indrukmoment van de dag, en het bewijst tegelijk dat de PDF geen apart product is maar dezelfde schermen.
- [ ] Eén tweede afdruk klaarleggen met een **selectie** (bijvoorbeeld alleen Dagoverzicht en Prognose): dat is het verschil tussen "hier is een rapport" en "u stelt uw rapport zelf samen".
- [ ] Beslissen welke bron de demo draait: de gehoste versie op de database (de standaard sinds 18 aug) of de lokale bestandsroute. **Niet op de demodag zelf omschakelen.**
- [ ] Taalkeuze klaarzetten: begin in het Nederlands, wissel op het dagoverzicht één keer naar het Frans om de tweetaligheid te tonen, en wissel terug.
- [ ] `docs/voortgang-voor-lien.md` en het antwoordenblok van `vragen-aan-lien.md` nalezen: wat is sinds de vorige demo beloofd, en klopt dat met wat er staat?

## De route (± 30 minuten, Kwinten klikt, Lien kijkt mee)

De volgorde is een verhaal, geen rondleiding: van "wat gebeurde er" naar "wat gaat er gebeuren". De prognose is de climax en komt daarom laat.

### 1. Login (2 min)
**Boodschap:** dit is een toepassing met toegang, geen rapport dat rondgemaild wordt.
Aanwijzen: het tweeluik in huisstijl, en benoemen dat de rollen *lezer* en *beheerder* bestaan. Als blok 12 dan af is: inloggen met een account uit de gebruikerslijst van S13. Zo niet: interim-login, en hardop zeggen dat de omschakeling naar Supabase Auth klaarstaat en alleen op S12/S13 wacht.

### 2. Dagoverzicht (5 min)
**Boodschap:** dit is wat Odoo niet geeft — de zaak in één oogopslag, met jaar-op-jaar en ritme.
Aanwijzen: de briefing bovenaan (signalering, geen advies), het bordeaux kerncijfer (vaste positie, verhuist nooit met goed of slecht nieuws — dat is het huisstijlprincipe, één zin waard), de periodekiezer, het weekdagprofiel, de bonontbinding (bonnen × bongrootte). Hier de taalwissel NL → FR → NL doen.

### 3. Kanalen (4 min)
**Boodschap:** elk kanaal heeft een andere marge, en dit platform toont "de wig" (bruto → commissie → netto) die nergens anders bestaat.
Aanwijzen: winkel en TGTG met echte cijfers, en **Deliveroo als onbeschikbaar mét reden**. Dat is geen excuus maar het ontwerpprincipe: *dit platform toont nooit een cijfer dat niemand heeft aangeleverd.* Meteen de brug naar de gevraagde actie: de Partner Hub-rapporten (S1) verliezen elke dag permanent een dag historiek.

### 4. Producten (4 min)
**Boodschap:** 425 producten, 19 groepen, en de vraag die een CFO stelt: komt de omzetbeweging door prijs of door volume?
Aanwijzen: de prijs-vs-volume-ontbinding, stijgers/dalers, de concentratie ("hoeveel producten dragen de helft van de omzet").

### 5. Marge (3 min — bewust kort, bewust niet overslaan)
**Boodschap:** dit scherm is bijna leeg, en dat is juist.
Er is kostprijs voor 3 van 425 producten in Odoo; een marge tonen op die basis zou een verzonnen cijfer zijn. Het scherm zegt dat, met reden, en het kostenmodel op Instellingen is de weg om het te vullen. Dit is het moment om regel 8 hardop te maken: *een CFO-platform dat een marge toont die niemand heeft aangeleverd, is erger dan een platform dat geen marge toont.*

### 6. Prognose (7 min — de climax)
**Boodschap:** dit is geen mening, dit is een gemeten model met een trackrecord.
Volgorde binnen het scherm:
1. De 7-daagse prognose met band, en het weektotaal.
2. De modelkaart: **7,8 % WAPE** tegenover 27,4 % voor het naïeve model — het model is ruim drie keer zo goed als "morgen wordt zoals vandaag".
3. De band is **gekalibreerd op gemeten dekking** (doel 80 %), niet op een aanname.
4. Het trackrecord van 28 dagen: het platform rekent zichzelf elke dag af, in het zicht.
5. Eén zin over wat er *niet* staat en waarom: geen prognose per product per dag op een scherm (20,2 % fout is te zwak om op te sturen — gemeten, niet vermoed) en geen scenario's zolang vraag 55 open staat.
Als er doorgevraagd wordt: `reports/backtest-rapport.md` ligt klaar, inclusief de kandidaten die zijn **afgewezen** met reden. Dat document is het aanvaardingscriterium, zo staat het in de scope.

### 7. Instellingen (3 min)
**Boodschap:** de beheerder kan zelf, zonder ons.
Aanwijzen: de datakwaliteitswachters (zeven stuks — het platform bewaakt zijn eigen aanvoer), het kostenmodel-formulier (invullen → herrekent het contract), de winkelindeling (een tweede vestiging is een configregel, geen verbouwing).

### 8. Het rapport, en afsluiting (4 min)
**Boodschap:** wat op het scherm staat, gaat mee de vergadering in — samengesteld door de lezer, niet door ons.
Rechtsboven op **Rapport**, twee onderdelen uitvinken, openen. Benoemen wat er dan gebeurt: er wordt niets gebouwd, het rapport leest hetzelfde contract als de schermen op ditzelfde moment. Dan **Afdrukken of PDF** aanklikken en het printvenster tonen. Daarna de twee afgedrukte exemplaren overhandigen. Dan de gevraagde-acties-tabel uit `voortgang-voor-lien.md`: wat er van wie nodig is, met vraag 58 (de vijf meegebouwde uitbreidingen — één zin bevestiging) expliciet op tafel. Afspreken wanneer F3 (afsluiting: sleutels roteren, `.env` weg, `data/` leeg) plaatsvindt.

## Terugvalposities

| Situatie | Wat we doen | Wat we vragen |
|---|---|---|
| **De gehoste versie is onbereikbaar op de dag zelf** | De demo draait volwaardig op de lokale bestandsroute — elk scherm, elk cijfer, de hele keten `make alles`. Dat is geen noodgreep: beide bronnen zijn op 18 augustus per scherm en per taal vergeleken en inhoudelijk identiek bevonden. | Niets extra's; wel benoemen dat de gehoste versie sinds 18 augustus draait en waarom er die dag op de lokale route wordt gedemonstreerd. |
| **S1 niet binnen** | Deliveroo blijft onbeschikbaar-met-reden en wordt in de demo juist áángewezen (scherm 3) als bewijs van het ontwerpprincipe. | De rapporten alsnog, met de herinnering dat elke dag wachten permanent verlies is — inclusief de datum vanaf wanneer het venster begon te schuiven. |
| **S12/S13 niet binnen** | Interim-login tonen; de Supabase-omschakeling benoemen als klaarstaand codepad achter `AUTH_BRON`. | De zelfregistratie-instelling (het enige dat blok 12 echt blokkeert) en de gebruikerslijst. |
| **Vraag 58(b) onbeslecht** (notificaties / AI-uitleglaag) | Niet tonen, niet beloven. Het conflict staat op papier in vraag 58; in de demo alleen verwijzen naar dat papier. | Eén beslissing: fase 2, zoals voorgesteld. |
| **Er valt iets om tijdens de demo** | Niet live debuggen. De 24 schermafbeeldingen van de steekproef van 26 aug staan klaar als plan B voor elk scherm. | — |

## Wat bewust níét getoond wordt

- **Scenario's** (blok 22): gebouwd achter `PROGNOSE_SCENARIOS`, maar vraag 55 beslist of ze bestaan. Tonen vóór die beslissing is scope-druk uitlokken.
- **De beslislaag / newsvendor**: geschrapt op 12 aug. Hoogstens één zin als er zelf naar gevraagd wordt: "het denkwerk ligt in `model-ontwerp.md` en is een fase 2-beslissing."
- **Prognose per product per dag**: 20,2 % fout, bewust geen scherm. Als het gevraagd wordt is het antwoord het getal, niet een belofte.
- **Alles wat niet uit de berekeningslaag komt.** Geen ad-hoc-berekening "even snel" tijdens de demo, ook niet in een terzijde.
