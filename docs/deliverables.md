# Deliverables

_Volledige lijst, bijgewerkt 19 augustus 2026. Dit is de werklijst; `scope.md` is de contractuele afbakening. Waar ze verschillen, wint `scope.md`._

**Statuscodes:** ✅ klaar · 🔄 bezig · ⬜ open · 🔒 geblokkeerd (met poort)

## A. Bronnen en datafundering

| | Deliverable | Status | Klaar wanneer | Hangt af van |
|---|---|---|---|---|
| A1 | Data-audit | ✅ 7 aug, hercontrole 12 aug | Alle blokken beantwoord met gemeten cijfers | — |
| A2 | Odoo-werkextract | ✅ 13 aug | Dag × product × kassa × kanaal (12 aug), en het eerste en laatste verkoopuur per product per dag als aparte aggregaat-extractie (`odoo_laatste_uur.py`, 13 aug) | Odoo-sleutel ✅ |
| A3 | Odoo-verzekeringsextract | ✅ 12 aug | Eenmalig: 1,56 mln bonregels zonder klantvelden + dimensietabellen, lokaal | A2 |
| A4 | TGTG-parser | ✅ 12 aug | 250 pdf's, drie formaatvarianten, 2019-2026, nul onleesbare documenten | — |
| A5 | TGTG-restwaarde | ✅ 13 aug | `make tgtg-restwaarde`: per kwartaal stuks, netto, commissie en bruto, 29 kwartalen terug tot 2019 (reports/, gitignored) | A4 |
| A6 | Kassa-identificatie | ✅ 12 aug | Gemeten en beantwoord: alle drie de kassa's verkopen hetzelfde bakkerijassortiment en tellen op tot één geheel (data-audit addendum 3, vraag 18) | A2, A4 |
| A7 | Canoniek datamodel | ✅ 12 aug | Eén tabelstructuur waar alle bronnen in landen; kanaal als volwaardige dimensie; sluitingsdagen als *geen meting* (`canoniek.py`) | A6 |
| A8 | Kalenderlaag | ✅ 12 aug, verbreed 13 aug | Weekdag, feestdag, brugdag, `winkel_gemeten`/`winkel_open`; sinds 13 aug ook beide schoolvakantieregimes als geverifieerde data (O10 empirisch beantwoord: FR wint) | A7 |
| A9 | Deliveroo-inlaadlaag | 🔒 G4 | Zodra het rapport er is: zelfde canonieke vorm als de rest | rapport van Deliveroo |

## B. Database, koppelingen en berekening

| | Deliverable | Status | Klaar wanneer | Hangt af van |
|---|---|---|---|---|
| B1 | Postgres-schema en migraties | ✅ 18 aug — migraties toegepast op Supabase, idempotent (tweede ronde leeg), 316.469 rijen geladen | Schema in de repo, database herbouwbaar met één commando | A7, Supabase-project ✅ 14 aug |
| B2 | **Odoo-koppeling, nachtelijk** | 🔄 gebouwd 17 aug, secrets gezet 18 aug, runner-invoer geregeld 19 aug; wacht op één handmatige run in GitHub Actions vóór de planning aangaat | Volledige sync vanaf GitHub Actions met `write_date` als **poortwachter** (niets gewijzigd → run stopt meteen). Bewust géén incrementeel extract: een half opgehaalde dag zou het dagtotaal stil corrumperen, zie `beslissingen.md` 17 aug | B1 |
| B3 | ~~**TGTG-ingest, periodiek**~~ | ⛔ | **Vervallen 17 aug** (blok 9 geschrapt op vraag van de opdrachtgever); het kanaal bevriest op de historiek t/m juli 2026. Handmatig binnenbrengen blijft mogelijk, zie `beheerdraaiboek.md` | — |
| B4 | **Deliveroo-koppeling** | 🔒 G4 | Idem, zodra er een bron is | B1, A9 |
| B5 | Berekeningslaag | ✅ 13 aug | Gebouwd, databaseloos (blok 10): één run bouwt alle afgeleide tabellen opnieuw uit de feiten; de nachtelijke variant hangt aan B2 | A7 |
| B6 | Datakwaliteitswachters | ✅ 13 aug | Gebouwd: dodemansknop plus zeven wachters, met een eigen contractantwoord (`stand.json`) op Instellingen én in de voettekst van elk scherm | B5 |

De rangorde die de opdrachtgever gaf: **Odoo eerst, Deliveroo tweede, TGTG derde.** Dat stuurde de volgorde van B2 en B4 — maar niet van A4, want die data ligt er al. B3 is sinds 17 aug vervallen.

## C. API en toegang

| | Deliverable | Status | Klaar wanneer | Hangt af van |
|---|---|---|---|---|
| C1 | Contract v1 | ✅ 12 aug | Eén genummerd JSON-antwoord per scherm (plus de winkelindex), versioneerd, geen float in een bedrag, `onbeschikbaar` als eersteklas veld, met tests op de vorm (`contract.py`) | B5 |
| C2 | Authenticatie | 🔄 | Interim-login draait: PBKDF2-afdrukken in de omgeving, ondertekende sessies, bewaking vóór de router (13 aug). De Supabase-versie (e-mail, wachtwoordherstel) blijft 🔒 S12+S13; wat dan wisselt is alleen `verifieer()` | Supabase-project ✅ 14 aug |
| C3 | Rollen en rechten | ⬜ | Lezer en beheerder, afgedwongen in de database en niet alleen in de UI | C2 |
| C4 | Aanmeldingslogboek | ⬜ | Wie logde wanneer in. Nodig voor het verwerkingsregister | C2 |

## D. Het platform

| | Deliverable | Status | Klaar wanneer | Hangt af van |
|---|---|---|---|---|
| D1 | **Skelet** | ✅ 12 aug | Navigatie, layout, designtokens in de huisstijl; alle schermen draaien | — |
| D2 | Scherm Overzicht | ✅ 12 aug, lokaal | Kerncijfers, omzet- en stuksverloop, jaar-op-jaar, op het echte contract | C1, D1 |
| D3 | Scherm Kanalen | ✅ 12 aug, lokaal | Winkel naast Deliveroo; Deliveroo toont zich als onbeschikbaar met reden (G4). (Tot 18 sep 2026 stond hier ook TGTG; dat kanaal is sindsdien uit scope, zie `beslissingen.md`.) | C1 |
| D4 | Scherm Producten | ✅ 12 aug, lokaal | Top-producten, stijgers en dalers, met verloop | C1 |
| D5 | Scherm Marge | 🔄 13 aug | De invoerroute bestaat: een beheerder vult categoriemarges in op Instellingen en Margebewaking rekent (gewogen marge, dekking, per groep). Zonder invoer: onbeschikbaar-staat met reden. Wacht op de eerste échte invoer door de klant (vraag 19, herformuleerd) | C1 |
| D6 | Scherm Prognose (tot 12 aug "Vooruitblik") | ✅ 12 aug, lokaal | Dagprognose met gekalibreerde band, plus prognoses per categorie, met de beperkingen erbij. Per product staat er bewust géén prognose op een scherm: dat cijfer is een backtestbevinding (20,2% WAPE per product-dag, zie `oplevering.md`) | E3 |
| D7 | Instellingen | 🔄 13 aug | Marges per productgroep invoeren wérkt (server action met rolcontrole, herrekent het contract). Gebruikersbeheer blijft ⬜ tot C3/S12/S13 | C3 |
| D8 | Onbeschikbaar-toestanden | ✅ 12 aug | Elk geblokkeerd cijfer toont zich expliciet als onbeschikbaar met reden, met leesbaar label (O12) | D1 |

## E. Prognose

| | Deliverable | Status | Klaar wanneer | Hangt af van |
|---|---|---|---|---|
| E1 | Baselines | ✅ 12 aug | Naive, seasonal naive, voortschrijdend gemiddelde per weekdag, op de echte reeks (`model/baseline.py`) | A7 |
| E2 | Backtest-harnas | ✅ 12 aug | Rolling origin over meerdere origins (`backtest/rolling.py`); gemeten lat: 8,4% WAPE dagomzet, 20,2% per product-dag | E1 |
| E3 | Model | ✅ 13 aug | weekdag_niveau + schoolvakantiecorrectie (FR): 7,8% WAPE dagomzet, band gekalibreerd op gemeten dekking; categorieprognoses met eigen WAPE. Som-van-categorieën en VL-regime getoetst en afgewezen | E2 |
| E4 | Backtest-rapport | ✅ 13 aug | `make backtest-rapport`: de lat, alle kandidaten (ook de afgewezen), fout per horizonstap, bandkalibratie, per-categorie-WAPE en de censureringsbevinding (reports/, gitignored) | E3 |

## F. Oplevering

| | Deliverable | Status | Klaar wanneer |
|---|---|---|---|
| F1 | Opleverdocument | ✅ 13 aug | `docs/oplevering.md`: waar elk cijfer vandaan komt, wat het platform niet toont en waarom |
| F2 | Beheerdraaiboek | ✅ 13 aug | `docs/beheerdraaiboek.md`: de keten, de periodieke handelingen, wat te doen bij een storing |
| F3 | Afsluiting | ⬜ | Sleutels geroteerd, `.env` verwijderd, `data/` leeg, schriftelijk vastgelegd wat er met de ruwe data gebeurt |

## W. Werkomgeving

_(Tot 18 augustus heetten deze rijen G1–G4, botsend met de poortletters hieronder; hernoemd naar W1–W4.)_

| | Deliverable | Status | Klaar wanneer |
|---|---|---|---|
| W1 | Commit-wachter | ✅ | `geen-klantdata.sh` draait vóór elke commit en blokkeert bij een databestand in de index. Harde regel 2 is een mechanisme, geen belofte |
| W2 | Skill: huisstijl | ✅ | `.claude/skills/huisstijl/SKILL.md`; elk scherm en elke grafiek volgt dezelfde regels |
| W3 | Skill: dagrapport | ⬜ | Dagboekentry plus het bericht aan Lien in het huisformaat |
| W4 | Skill: poortcheck | ⬜ | Loopt de acht poorten na en maakt er een vragenblok van |

---

## De acht poorten

Geen enkele deliverable die op een poort wacht, wordt stilzwijgend uitgesteld. Wat geblokkeerd is, staat hierboven met 🔒 en wordt in het dagboek gemeld.

| | Poort | Blokkeert | Bij wie ligt het |
|---|---|---|---|
| G1 | Brutomarge per productgroep | D5, marge overal | eindklant, via Lien |
| G2 | Welke kassa is de bakkerij | A7 en alles erboven | Lien, na onze analyse |
| G3 | TGTG-export | — (binnen) | **Vervallen 18 sep 2026**: TGTG is uit scope, zie `beslissingen.md` |
| G4 | Deliveroo-rapport | A9, B4, D3 gedeeltelijk | Deliveroo, via Lien |
| G5 | Synchroniseert de preprod | B2 | Idealis |
| G6 | Odoo-productielicentie | B2 op echte data | eindklant |
| G7 | Waar de database staat | B1, C2, alles erboven | Lien |
| G8 | Wie krijgt toegang | C2, C3 | Lien |
