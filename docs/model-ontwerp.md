# Modelontwerp

> **Status, 12 augustus 2026: gedeeltelijk buiten scope.** De baklijst en de beslislaag zijn uit fase 1 gehaald; het product is een CFO-platform. Wat hieronder staat over **laag 1, de vraagverdeling, de baselines en het backtest-harnas** geldt onverkort: dat is de vooruitblik in het platform (D8). Wat hieronder staat over **laag 2, de beslislaag, het kritieke percentiel en de baklijst** wordt in fase 1 niet gebouwd.
>
> Het blijft staan om twee redenen. Het legt uit waarom een restwaardekanaal zoals TGTG economisch iets anders is dan een opruimkanaal, en dat inzicht bepaalt de waarde van een latere fase. En het documenteert wat er nodig zou zijn — brutomarges per productgroep — als de eindklant die stap alsnog wil zetten. (TGTG zelf is sinds 18 september 2026 uit scope, zie `beslissingen.md`; het voorbeeld hieronder blijft staan als economische illustratie, niet als beschrijving van een bestaand kanaal.)

## De kernstelling

Dit is geen voorspellingsprobleem met een beslissing erachter. Het is een **beslissingsprobleem** dat toevallig een voorspelling nodig heeft.

De bakker vraagt niet "hoeveel ga ik er verkopen". Hij vraagt "hoeveel bak ik er". Dat zijn verschillende getallen, en het verschil is precies waar het geld zit. Wie de eerste vraag beantwoordt en het tweede getal eraan gelijkstelt, laat systematisch marge liggen.

## Twee lagen

```
LAAG 1  Vraagverdeling
        Per product, per filiaal, per dag, per kanaal.
        Niet één getal maar een verdeling: mediaan, en de spreiding eromheen.

LAAG 2  Beslislaag
        Van verdeling naar aantal, met de echte kosten van te veel en te weinig.
        Dit is waar TGTG, Deliveroo-commissie en grondstofkost binnenkomen.
```

Laag 1 alleen levert een grafiek. Laag 2 levert een baklijst. De opdracht wás de baklijst.

## Waarom een verdeling en niet één getal

Een puntvoorspelling van 40 broden zegt niets over of je er 40 of 48 moet bakken. Dat hangt af van de asymmetrie: als een onverkocht brood je 0,60 euro kost en een gemiste verkoop 1,80 euro marge, dan bak je bewust boven de mediaan. Het optimale percentiel is:

```
kritiek percentiel = kost van te weinig / (kost van te weinig + kost van te veel)
```

Met bovenstaande cijfers: 1,80 / (1,80 + 0,60) = 0,75. Je bakt dus op het 75e percentiel van de vraagverdeling, niet op het gemiddelde. Dat is het krantenverkopersprobleem, en het is de hele reden dat laag 1 een verdeling moet opleveren.

**Wat TGTG hiermee doet:** een onverkocht brood dat via TGTG nog 0,30 euro opbrengt in plaats van 0 kost je geen 0,60 maar 0,30. Het kritieke percentiel gaat dan naar 1,80 / (1,80 + 0,30) = 0,86. Je bakt méér. Too Good To Go is dus geen opruimkanaal maar een knop die het optimum verschuift, en het optimum ligt niet op nul verspilling.

Dat inzicht is de inhoudelijke kern van dit project. Het is ook het stuk dat een dashboardbouwer niet levert.

## Waarom geen machine learning

Niet uit principe, uit rekenwerk.

- Het dataveld is **kort en dun**: een paar honderd producten, een handvol filialen, één tot twee jaar dagen. Een gradient-boosting-model heeft daar niet genoeg signaal per cel om zijn extra vrijheidsgraden te verdienen.
- De structuur is **grotendeels bekend**: weekdag, kalender, seizoen, trend. Als je die er expliciet in zet, blijft er weinig over dat een model moet ontdekken.
- De klant moet de lijst **vertrouwen**. "Waarom moet ik er morgen 12 meer bakken" is een redelijke vraag, en het antwoord "het model zegt het" verliest die discussie. Uitlegbaar wint hier van accuraat.
- Als de backtest aantoont dat een zwaarder model materieel beter is in euro's, dan komt het er alsnog in. Die volgorde, niet omgekeerd.

## De opbouw, in volgorde

### 1. Baselines (bouwen vóór het model)
- **Naive**: morgen is als vandaag.
- **Seasonal naive**: morgen is als dezelfde weekdag vorige week. Voor een bakkerij is dit verrassend sterk en het is de baseline die verslagen moet worden.
- **Voortschrijdend gemiddelde per weekdag**: gemiddelde van de laatste vier dezelfde weekdagen.

Als het uiteindelijke model de seasonal naive niet materieel verslaat, is dat het eerlijke resultaat en gaat het zo in het rapport.

### 2. Backtest-harnas (bouwen vóór het model)
- **Rolling origin**: train tot dag T, voorspel T+1, schuif op, herhaal. Nooit willekeurig splitsen, dat lekt de toekomst.
- **Meerdere origins over het hele jaar**, zodat seizoen niet uit één toevallige periode beoordeeld wordt.
- **Afgerekend in euro's**, niet in MAPE. MAPE straft fouten op kleine producten onevenredig en zegt niets over marge. De maat is: wat had deze beslisregel gekost aan verspilling plus gemiste verkoop.
- Per product en per filiaal gerapporteerd, niet alleen als totaal. Een model dat gemiddeld goed is en op de tien belangrijkste producten slecht, is slecht.

### 3. Vraagverdeling
- Start bij een decompositie: niveau, weekdagpatroon, jaarpatroon, kalendereffecten.
- Kwantielen uit de empirische spreiding van de residuen, per product-filiaal-groep. Producten met te weinig data lenen hun spreiding van hun productgroep.
- Correctie voor gecensureerde vraag als de audit uitwijst dat uitverkoop meetbaar is. Zie `data-audit.md`, blok E.

### 4. Beslislaag
- Kritiek percentiel per product per kanaal, uit marge en restwaarde.
- Afronding naar bakbare eenheden. Een oven bakt in platen, niet in stuks. Uitvragen.
- Ondergrenzen voor toonbankpresentatie: een leeg rek verkoopt ook de rest niet. Dit is een businessregel, geen modelregel, en hij hoort expliciet in de configuratie.

### 5. Baklijst
- Per filiaal, per product, één getal, plus een bandbreedte en een korte reden.
- Formaat dat om vier uur 's ochtends bruikbaar is. Dat betekent papier of telefoon, niet een dashboard waarop je moet inzoomen.

## Wat we bewust niet doen

- Geen voorspelling op uurniveau in fase 1. De beslissing valt per dag.
- Geen weer in fase 1. Weer is echt maar het effect is kleiner dan kalender, en het voegt een externe afhankelijkheid toe voordat de basis staat.
- Geen automatische bestellingen. Het model adviseert, de mens beslist.
- Geen belofte over een percentage minder verspilling vóór de backtest die het aantoont.

---
*Aangemaakt 7 augustus 2026. Bij te werken na de data-audit, want de audit kan hele stukken hiervan onmogelijk maken.*
