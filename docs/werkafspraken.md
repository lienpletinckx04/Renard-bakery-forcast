# Werkafspraken en operationele hygiëne

Dit document gaat niet over code. Het gaat over de dingen die achteraf duur worden als je ze vooraf niet regelt.

## 1. Repo-eigendom

- De repository staat **privé onder de eigen organisatie `liveatwembley`** (`github.com/liveatwembley/asklien-bakkerij`), niet onder het account van de opdrachtgever.
- De opdrachtgever krijgt leestoegang zodra daar aanleiding voor is, en collaborator-toegang bij oplevering.
- **Overdracht gebeurt bij eindbetaling.** Zet dat in de overeenkomst als het er niet in staat. Dit is geen wantrouwen, het is de standaardpraktijk die conflicten voorkomt.
- Tot overdracht wordt er in de eigen repo gewerkt en gepusht. De belofte "als ik klaar ben push ik het naar u" wordt daarmee waargemaakt zonder dat het werk onderweg buiten de eigen controle valt.

## 2. Credentials

- Nooit in code, nooit in een commit, nooit in een chatbericht, nooit in een LLM-context.
- Alles in een wachtwoordbeheerder of in de macOS-sleutelhanger. Lokaal alleen in `.env`, die gitignored is.
- **Vraag om projectgebonden toegang, niet om een hoofdaccount.** Een service-account of een gescopete key per dienst. Als iemand een hoofdwachtwoord doorstuurt: aparte key vragen, en het doorgestuurde wachtwoord als gecompromitteerd behandelen.
- Bij oplevering worden alle door de opdrachtgever verstrekte sleutels geroteerd. Meld dat proactief, het is een teken van vakmanschap en het beëindigt de aansprakelijkheid.
- Lijst bij te houden in `.env.example`: welke sleutel, van wie, waarvoor, wanneer gekregen, wanneer te roteren.

## 3. Machine- en accountscheiding

Er wordt gewerkt met de Claude-abonnementscredits van de opdrachtgever. Dat is afgesproken en prima, maar het vraagt scheiding.

- Aparte Claude Code-configuratiemap voor dit project, zodat het eigen account voor eigen werk ingelogd blijft. Zie `docs/setup-mac.md`.
- Aparte git-identiteit per repo (`git config user.email` binnen de repo), zodat commits onder de zakelijke identiteit staan.
- **Geen enkel bestand van dit project komt in de buurt van andere repositories.** Geen gedeelde datamappen, geen symlinks, geen "even hier neerzetten".
- Klantdata staat op één machine. Niet op een cloudschijf, niet in een codespace, niet in een gedeelde map.

## 4. Communicatie

- Alles inhoudelijk loopt via de gedeelde groep, zodat er een spoor is.
- Vragen worden **gebundeld** in `vragen-aan-lien.md` en in blokken gesteld, niet druppelsgewijs. Dat scheelt haar tijd en het maakt van de vragen een document in plaats van ruis.
- De eindklant wordt niet rechtstreeks gecontacteerd, tenzij de opdrachtgever daar expliciet toe uitnodigt.
- In een groep waarin meerdere betrokkenen zitten, wordt over geen van hen iets gezegd dat je niet tegen hen zou zeggen. Ook niet als een ander het wel doet.
- Wat mondeling wordt afgesproken, wordt dezelfde dag schriftelijk bevestigd in één zin. "Zoals besproken: X, geraamd op Y dagen." Dat is geen formaliteit, het is het enige dat later bestaat.

## 5. Dagrapport

Elke werkdag eindigt met een entry in `dagboek.md`, die dezelfde dag naar de opdrachtgever gaat. Vier regels volstaan: wat gedaan, wat geblokkeerd, welke beslissing genomen, wat morgen.

Dit is bewust geen bureaucratie. Drie redenen:
1. De opdrachtgever heeft er expliciet om gevraagd.
2. Het is de volledige verdediging tegen een later "dat duurde toch lang"-gesprek.
3. Het is de onderbouwing voor de raming van fase 2.

## 6. Facturatie

- Voorschot van vijftig procent vóór dag 1. Geen voorschot, geen start.
- In de overeenkomst hoort **een dagprijs met een geraamd aantal dagen**, niet een totaalbedrag. Een totaalbedrag maakt van een dagprijs stilzwijgend een vaste prijs, en dan draag jij het risico van data die tegenvalt.
- Als er bewust onder het standaardtarief gewerkt wordt, staat het woord **introductietarief** letterlijk in de overeenkomst, met het standaardtarief ernaast. Dat kost nu niets en verzet het anker voor fase 2.
- Betalingstermijn expliciet. Bij een tussenpersoon nooit "na betaling door de eindklant": dat verplaatst het incassorisico naar jou.
- Meerwerk wordt vooraf schriftelijk goedgekeurd, aan hetzelfde dagtarief.

## 7. Aansprakelijkheid en verwachtingen

Eén zin die in het eindrapport hoort en die je vanaf dag 1 herhaalt: **een voorspelling is een hulpmiddel bij een beslissing, geen garantie.** Het model geeft aantallen met een onzekerheidsmarge. De bakker beslist. Dit is dezelfde doctrine als bij evaluatieve AI: het instrument informeert, de mens beslist, en dat wordt nooit vager gemaakt om het beter te laten klinken.

Concreet betekent dat: geen enkele belofte over een percentage minder verspilling vóór de backtest die dat aantoont.

---
*Aangemaakt 7 augustus 2026.*
