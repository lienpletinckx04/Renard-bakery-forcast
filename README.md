# asklien-bakkerij

CFO-platform voor Renard Bakery. Opdracht via asklien.ai (Lien Pletinckx).

Een toepassing met een login, een database die dagelijks bijwerkt uit de bronsystemen, en een web-UI in de huisstijl van het merk. Inclusief een prognose (dagtotaal met band, en per categorie). Zie `docs/scope.md` voor de afbakening en `docs/plan-fase1.md` voor de volgorde.

**De baklijst is op 12 augustus 2026 uit de scope gehaald.** Eerdere versies van dit bestand beschreven dit project als een beslissingsmodel met een dashboard erop. Dat is omgekeerd: het platform is het product. Het denkwerk over de beslislaag staat nog in `docs/model-ontwerp.md`, als voorbereiding op een latere fase.

## Wat dit oplost

Een bakkerij verkoopt via de toonbank en via Deliveroo. Odoo kent alleen het eerste, berekent geen marge, en kijkt niet vooruit. Het gevolg is dat er geen enkele plek is waar de zaakvoerder ziet wat er echt binnenkomt, per kanaal, tegen welke marge, en wat er de komende dagen aankomt.

Dat is wat dit platform doet. Het is geen tweede versie van de Odoo-rapportering: het onderscheid zit in de ontbrekende kanalen, in de marge, en in de prognose.

## De lagen

```
BRONNEN       Odoo (XML-RPC)   Deliveroo (rapport, nog niet ontvangen)
   -> INLAADLAAG      normaliseren naar het canonieke datamodel
   -> DATABASE        Postgres, bron van waarheid
   -> BEREKENING      nachtelijk: aggregaties, marge, prognose
   -> API/CONTRACT    genummerde JSON-antwoorden
   -> TOEGANG         login, sessies, rollen
   -> PRESENTATIE     web-UI in de huisstijl   (fase 2: mobiele app op dezelfde API)
```

De regel die dit draagt: **de UI rekent nooit.** Dat is wat de app van fase 2 mogelijk maakt zonder verbouwing, en het is waarom een cijfer op het scherm hetzelfde cijfer is als in een export.

## Structuur

```
docs/                 Alles wat je moet lezen vóór je code schrijft
  instructies-lien.md Neem je deze repo over? Begin hier: de handelingen, in volgorde
  overdracht.md       Dezelfde overdracht, maar met de redenen en de volledigheid
  start-hier.md       Waar alles staat, de opzet van de machine, en de ene leesroute
  volgende-sessie.md  Wat de vorige sessie klaarlegde voor de volgende
  todo.md             De ene blokkadelijst (S-nummers) en de reststand per blok
  scope.md            Wat fase 1 wel en niet is (spiegel van de overeenkomst)
  plan-fase1.md       In welke volgorde er gebouwd is, met de stand per stap
  oplevering.md       Waar elk cijfer vandaan komt, wat het platform bewust niet toont
  beheerdraaiboek.md  Hoe het draait, de periodieke handelingen, wat te doen bij storing
  data-audit.md       Wat de data draagt, ingevuld met gemeten cijfers
  aannames.md         Lopende lijst van aannames + wie ze moet bevestigen
  vragen-aan-lien.md  Openstaande vragen (queue, niet ad hoc pingen)
  beslissingen.md     Beslissingen met datum en reden
  dagboek.md          Dagrapport. Dit is een contractueel bewijsstuk, geen dagboek.

bakkerij/             De Python-kern: inladen, berekenen, contract bouwen
  canoniek.py         Alle bronnen naar het canonieke datamodel
  contract.py         Eén genummerd JSON-antwoord per scherm (plus de winkelindex), NL en FR
  kwaliteit.py        Dodemansknop en de zeven datakwaliteitswachters
  sources/            Koppelingen naar de bronsystemen
  features/           Kalender: weekdag, feestdagen, schoolvakanties
  model/              Baselines en het prognosemodel
  backtest/           Rolling-origin backtest, afgerekend in euro's
  db/                 Verbinding, laden en sync richting Postgres

platform/             Next.js-web-UI. Leest uitsluitend het contract, rekent nooit
  app/                Zeven schermen; negen routes, waarvan acht bewaakt (alleen /login erbuiten)
  lib/                Contract lezen, auth, taal, opmaak
  proxy.ts            Toegangsbewaking vóór de router

db/migraties/         Postgres-migraties, oplopend genummerd
scripts/              Uitvoerbare stappen: extract, canoniek, contract, nachtelijke sync
tests/                Tests voor de Python-kant (platform/tests/ voor de UI)
reports/              Gegenereerde rapporten (backtest, onvertaald)
data/                 Gitignored. Ruwe brondata verlaat deze machine niet.
```

## Setup (macOS)

```bash
cp .env.example .env                        # Odoo-sleutel
cp platform/.env.example platform/.env.local # sessiesleutel + gebruikers
make setup      # venv + Python-dependencies + npm ci in platform/
make odoo-audit # verbindingstest, kost niets
make extract    # verkoophistoriek naar data/raw
make test       # beide helften: de Python-suite en de platformtests
```

`make help` toont alle doelen met hun uitleg. Vóór een commit: `make controle`
— dat is alles wat CI ook doet (klantdata-check, lint, beide testsuites,
typecheck en de productiebouw), zodat je niet lokaal groen kunt zijn en toch
een rode CI krijgt.

**Twee `.env`-bestanden, en dat is geen slordigheid:** Next leest uitsluitend
`platform/.env.local`, de Python-kant leest de `.env` in de wortel. Wie de
tweede vergeet, krijgt alles groen en kan tóch niet inloggen — een lege
`PLATFORM_GEBRUIKERS` betekent per ontwerp "niemand komt binnen". Zie
`docs/start-hier.md` voor het invullen ervan.

Een deel van de tests wordt lokaal overgeslagen: dat is de databasesuite
(`tests/test_db_echt.py`), die een echte Postgres via `TEST_DB_URL` vergt en in
CI draait. Overgeslagen is daar de juiste uitkomst. Het aantal tests staat hier
bewust niet — `make test` meldt het zelf, en een getal in een document is
binnen een week achterhaald.

Vereist Python 3.11+ en Node 22.6+ (zie `platform/.nvmrc`; de testrunner
gebruikt `--experimental-strip-types`).

Zie `docs/werkafspraken.md` voor de credential- en machinediscipline.

## Harde regels

**De acht harde regels staan in `CLAUDE.md`; dat document is de bron, dit is een samenvatting.** De kern: klantdata gaat nooit de repo of een modelcontext in, naar de gehoste database gaat alleen geaggregeerde productverkoop, de UI rekent nooit, en een geblokkeerd cijfer toont zich als onbeschikbaar met de reden — nooit als schatting.
