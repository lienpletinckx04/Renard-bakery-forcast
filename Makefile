.PHONY: help setup controle bouw test test-py test-ui lint audit backtest backtest-rapport diagnose clean check-data extract extract-uren extract-bonnen censurering odoo-audit deliveroo agenda canoniek verzekering contract vakanties ui dev alles herbouw db-migreer db-droog db-laad db-laad-droog db-contract db-contract-droog db-kostenmodel db-sluitingen sync sync-droog steekproef

PY := .venv/bin/python
PIP := .venv/bin/pip

## Alle doelen, met de eerste regel van hun uitleg. Dit is het doel dat je
## zoekt als je dit project een jaar niet gezien hebt.
##
## WAAROM DIT ER PAS OP 19 AUG 2026 KWAM. Vrijwel elk doel hieronder droeg al
## een `##`-uitleg -- het patroon van een zelfdocumenterende Makefile -- maar
## er was niets dat ze oogstte. In plaats daarvan stond er in
## `docs/beheerdraaiboek.md` een met de hand bijgehouden lijstje van tien van
## de negenendertig doelen, en zo'n lijstje loopt uit elkaar met de Makefile
## zonder dat iemand het merkt. Dit doel kan dat niet.
##
## `.DEFAULT_GOAL` staat hier om een tweede reden: zonder die regel is `setup`
## het eerste doel in dit bestand, en dan bouwt een kale `make` de venv opnieuw
## op en draait `npm ci`. Dat is een vervelende manier om erachter te komen dat
## je de doelnaam vergeten was.
.DEFAULT_GOAL := help
help:
	@echo ""
	@echo "  Renard Bakery -- CFO-platform. Doelen:"
	@echo ""
	@awk 'BEGIN {FS = ":"} \
		/^##/ { if (!bezig) { uitleg = substr($$0, 4); bezig = 1 } ; next } \
		/^[a-z][a-z0-9-]*:/ { \
			if (bezig) printf "  \033[1m%-22s\033[0m %s\n", $$1, uitleg; \
			bezig = 0; next } \
		{ bezig = 0 }' $(MAKEFILE_LIST)
	@echo ""
	@echo "  Vóór een commit: make controle"
	@echo ""

## Beide helften, net als `make test`. Tot 18 aug 2026 maakte setup alleen de
## venv; de eerste `make test` op een verse machine viel dan op een npm-fout
## die niets zei over de oorzaak (node_modules ontbrak simpelweg).
setup:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	cd platform && npm ci
	@echo ""
	@echo "Klaar. Activeer met: source .venv/bin/activate"

## Sinds 14 aug dekt `make test` beide helften: één groene uitkomst betekent
## Python én platform. De TypeScript-helft was tot dan onzichtbaar voor make
## en kon stil breken (audit 14 aug, punt 5.1).
test: test-py test-ui

## ALLES WAT CI OOK DOET, in één commando. Gebruik dit vóór een commit.
##
## `make test` dekt pytest, de platformtests en de typecheck -- maar niet
## `lint`, niet `db-droog` en niet de productiebouw, en die drie draaien wél
## in .github/workflows/tests.yml. Tot 19 aug 2026 kon je dus lokaal groen
## zijn en toch een rode CI krijgen door een ruff-fout, een kapotte
## migratienummering of een buildbreuk die alleen `next build` ziet. Wie in
## 2028 nog één commando onthoudt van dit project, is dit het.
##
## check-data staat vooraan en niet achteraan: als er klantdata klaarstaat om
## gecommit te worden, hoeft de rest niet meer te draaien (harde regel 2).
controle: check-data lint test db-droog bouw

## De productiebouw. Staat apart zodat `make controle` hem kan aanroepen en
## zodat je hem los kunt draaien; hij is verreweg de traagste stap.
bouw:
	cd platform && npm run build

## Alleen de Python-helft van de tests. Voor een snelle ronde tijdens het
## werken; `make test` is de volledige lat en `make controle` alles wat CI doet.
test-py:
	$(PY) -m pytest tests/ -q

## `npm run typecheck` en niet `npx tsc`: zonder node_modules haalt npx stil
## een ándere TypeScript-versie van de registry — je typecheckt dan met iets
## anders dan CI (18 aug).
test-ui:
	cd platform && npm test && npm run typecheck

## Eén lat op alle Python in de repo. `scripts/` hoort er sinds 12 aug 2026 bij:
## de ruff-hook in .claude/hooks/ controleerde die map al bij elke edit, dit doel
## niet, en daardoor dreef scripts/ weg (O18).
lint:
	$(PY) -m ruff check bakkerij/ tests/ scripts/

## Dag-1 dataprofiler. Gebruik: make audit FILE=data/raw/export.csv
audit:
	@test -n "$(FILE)" || (echo "Gebruik: make audit FILE=data/raw/<bestand>"; exit 1)
	$(PY) -m bakkerij.audit.profile "$(FILE)"

## De lat voor de prognose: baselines door het rolling-origin harnas, op de
## canonieke data. Alleen open dagen, afgerekend in euro's. Vereist: make canoniek
backtest:
	$(PY) scripts/backtest_prognose.py

## Veiligheidscheck: staat er klantdata op het punt om gecommit te worden?
##
## Patroon en uitzonderingen staan in scripts/verdachte_bestanden.sh, en daar
## alleen. Dit doel en .claude/hooks/geen-klantdata.sh lezen allebei dat ene
## script. Tot 18 aug 2026 stond de lijst hier én in de hook met de hand, en
## ze waren al uiteengelopen: dit doel dekte minder (geen pdf, zip of json)
## terwijl het commentaar "dezelfde uitzondering" beloofde. Twee vangrails met
## één naam en twee gedragingen, en de zwakste won. Dit commentaar zélf zei tot
## 19 aug nog dat je "op beide plekken" moest wijzigen — een instructie die na
## de samenvoeging niemand meer hoeft te volgen, en die je dus naar een tweede
## plek stuurt die niet bestaat.
##
## De les van 13 augustus 2026 die in de vorm van dit doel zit: de oude
## schrijfwijze `grep && (…; exit 1) || echo` faalde nooit — de `exit 1`
## verliet alleen de subshell en de `||` maakte het geheel weer waar.
## Sinds 19 aug 2026 begint dit doel met de vraag of de vangrail zelf er nog
## is. Zonder die toets faalde het OPEN: een ontbrekend script gaf een lege
## uitkomst, en dan meldde make letterlijk "Schoon: geen databestanden in de
## staging area." Een vangrail die liegt in plaats van zwijgt is erger dan
## geen vangrail, want niemand kijkt er daarna nog achter.
check-data:
	@test -f scripts/verdachte_bestanden.sh || { \
		echo ""; echo "STOP: scripts/verdachte_bestanden.sh ontbreekt."; \
		echo "De vangrail tegen klantdata in de repo werkt dus niet."; exit 1; }
	@verdacht=$$(bash scripts/verdachte_bestanden.sh .); \
	if [ -n "$$verdacht" ]; then \
		echo ""; echo "STOP: er staat een databestand klaar om te committen:"; \
		echo "$$verdacht"; exit 1; \
	else \
		echo "Schoon: geen databestanden in de staging area."; \
	fi

## De werkomgeving weggooien: venv en cachemappen. Raakt `data/` niet en
## raakt niets in git. Na afloop is `make setup` nodig.
clean:
	rm -rf .venv .pytest_cache .ruff_cache
	find . -name '__pycache__' -type d -exec rm -rf {} +

## Data ophalen uit Odoo (vereist ingevulde .env)
extract:
	$(PY) scripts/odoo_extract.py --vanaf 2025-01-01

## Eerste en laatste verkoopuur per product per dag (O11, censureringsvraag O8)
extract-uren:
	$(PY) scripts/odoo_laatste_uur.py --vanaf 2025-01-02

## Aantal bonnen per dag per kassa, distinct aan de bron (traffic/ticket-as)
extract-bonnen:
	$(PY) scripts/odoo_bonnen.py --vanaf 2025-01-02

## De censureringsmeting op het jongste urenextract. Print alleen aggregaten.
censurering:
	$(PY) scripts/censurering_meting.py

## Volledig archief op bonregelniveau, parquet, lokaal. Duurt enkele minuten.
verzekering:
	$(PY) scripts/odoo_verzekering.py

## Wat staat er in Odoo: modellen, velden en aantallen. Verkenningsgereedschap
## uit de data-audit; print alleen aggregaten, nooit rijen.
odoo-audit:
	$(PY) scripts/odoo_audit.py

## Deliveroo-downloads inventariseren: welke bereiken liggen er, wat mist er,
## en waar zitten de gaten in de twaalf maanden. Parsen doet dit nog niet --
## dat wacht op echte CSV's uit Partner Hub (blok 5). Staat bewust niet in
## `alles`: zolang er niets te lezen is, hoort het kanaal onbeschikbaar te
## blijven met reden en niet op nul te staan.
deliveroo:
	$(PY) scripts/deliveroo_extract.py

## De postbus tonen: wat heeft een beheerder via het scherm /deliveroo
## opgeladen, en wat wacht er nog. Schrijft niets, vraagt wel een verbinding
## (SUPABASE_DB_URL). `make uploads-haal` schrijft de wachtende bestanden naar
## data/raw/postbus/ zonder ze af te vinken -- ophalen is geen verwerken.
## Verwerken (`--verwerk`) laat vandaag alles staan als `nog-niet-leesbaar`,
## want er is nog geen lezer; zie docs/plan-deliveroo-parser.md. Staat daarom
## bewust niet in `alles` of `herbouw`.
uploads:
	$(PY) scripts/uploads_verwerk.py

uploads-haal:
	$(PY) scripts/uploads_verwerk.py --haal

## De agenda van de bakkerij ophalen (optioneel spoor, vraag 46). Zonder
## AGENDA_ICS_URL in .env doet dit niets, en dat is geen fout maar de normale
## toestand zolang de klant niet geantwoord heeft. Staat bewust niet in `alles`.
agenda:
	$(PY) scripts/agenda_ophalen.py

## Canoniek datamodel bouwen: alle kanalen naar één verkooptabel + kalender
canoniek:
	$(PY) scripts/canoniek_bouw.py

## Schoolvakanties verversen vanaf de OpenHolidays-API. Idempotent: zonder
## bronwijzigingen blijft het bestand ongemoeid. Wijzigingen aan het verleden
## worden geweigerd; bekijk ze en draai dan bewust met FORCEER=1.
vakanties:
	$(PY) scripts/vakanties_ververs.py $(if $(FORCEER),--forceer)

## Berekening + contract: één JSON-antwoord per scherm (plus de winkelindex) die de
## schermen lezen. Uitvoer gaat naar platform/contract/ en dat is gitignored
## (klantdata).
contract:
	$(PY) scripts/contract_bouw.py

## De nachtelijke ketting (blok 8): poortwachter op write_date, dan
## extract -> canoniek -> laden, met één etl_run-rij per run. Lokaal draaien
## kan; in productie doet .github/workflows/nachtelijke-sync.yml dit elke nacht.
## SYNC_ARGS geeft argumenten door aan de ketting; vandaag alleen `--volledig`,
## dat de poortwachter overslaat. Zonder die doorgang was die vlag vanuit de
## workflow niet te bereiken (zie .github/workflows/nachtelijke-sync.yml).
sync:
	$(PY) scripts/nachtelijke_sync.py $(SYNC_ARGS)

## Dezelfde ketting zonder Odoo en zonder schrijven: canoniek + db-laad droog
## op de lokale data. De toets die zonder databasesleutel kan.
sync-droog:
	DROOG=1 $(PY) scripts/nachtelijke_sync.py

## Het schema naar Supabase. Idempotent: tweede keer draaien is een lege run.
## Vereist SUPABASE_DB_URL in .env (pooler, poort 5432, sslmode=require).
##
## Die twee regels stonden tot 19 aug 2026 boven `sync` en beschreven dus het
## verkeerde doel; `db-migreer` had zelf geen uitleg. `make help` maakte dat
## zichtbaar op de dag dat het doel er kwam — precies waar het voor is.
db-migreer:
	$(PY) scripts/db_migreer.py

## Toont welke migraties er zijn zonder verbinding te leggen. Werkt zonder
## sleutels, en draait daarom in CI (tests.yml) bij elke push.
db-droog:
	DROOG=1 $(PY) scripts/db_migreer.py

## Het canonieke model naar Postgres. Draai eerst: make canoniek, make db-migreer
db-laad:
	$(PY) scripts/db_laad.py

## Alles behalve schrijven: leest, bereidt voor, ontdubbelt en controleert de
## verwijzingen naar de dimensies. Werkt zonder sleutel, en vangt precies de
## fouten die niets met de verbinding te maken hebben.
db-laad-droog:
	DROOG=1 $(PY) scripts/db_laad.py

## De gebouwde contractantwoorden naar Postgres (migratie 006). Draai eerst:
## make contract. Het platform leest deze tabel alleen met CONTRACT_BRON=db;
## zonder die vlag blijft de bestandsroute bit voor bit ongewijzigd.
db-contract:
	$(PY) scripts/contract_laad.py

## Leest en valideert de volledige contractboom (beide talen, alle winkels)
## en telt wat er geschreven zou worden. Zonder verbinding en zonder sleutel.
db-contract-droog:
	DROOG=1 $(PY) scripts/contract_laad.py

## De beheerinvoer (kostenmodel) van data/config/ naar Postgres (migratie 005).
## Eenmalig, om de lokaal ingevulde kosten over te zetten: daarna schrijft het
## formulier op Instellingen rechtstreeks naar dezelfde tabellen (migratie 009)
## en is dit doel alleen nog herstelgereedschap. Bewust GEEN deel van de
## nachtketting — anders schrijft de bouwmachine elke nacht haar bestand over de
## invoer van het formulier heen. Droog: DROOG=1 make db-kostenmodel
db-kostenmodel:
	$(PY) scripts/kostenmodel_laad.py

## De sluitingslijst (config/sluitingsdagen.json) naar Postgres (migratie 011).
## Eenmalig, om het scherm Sluitingsdagen met een gevulde kalender te laten
## beginnen: daarna schrijft dat scherm rechtstreeks naar dezelfde tabellen
## (migratie 012) en weigert dit doel zolang de database gevuld is (FORCEER=1
## voor een bewust herstel). Bewust GEEN deel van de nachtketting — zelfde
## argument als db-kostenmodel. Droog: DROOG=1 make db-sluitingen
db-sluitingen:
	$(PY) scripts/sluitingen_laad.py

## Het backtest-rapport (E4): elke bewering over de prognose, met de meting
## ernaast — inclusief wat getoetst en afgewezen is. Naar reports/ (gitignored).
backtest-rapport:
	$(PY) scripts/backtest_rapport.py

## WAPE-diagnose van de productieprognose (blok 23): waar de fout woont, per
## weekdag, horizonstap, feestdag, vakantie en maand, plus twee gemeten
## verbeteringskandidaten. Naar reports/ (gitignored).
diagnose:
	$(PY) scripts/backtest_diagnose.py

## HET CFO-RAPPORT HEEFT GEEN DOEL MEER. Hier stond tot 18 aug 2026
## `rapport-pdf`: WeasyPrint bouwde een PDF uit de contractantwoorden en het
## platform serveerde dat bestand van schijf. Het rapport is nu een weergave in
## het platform (/rapport): je kiest de onderdelen in het menu en drukt af of
## bewaart als PDF. Er valt dus niets meer vooraf te bouwen — en het bestand kon
## per definitie ouder zijn dan de cijfers op het scherm ernaast.
## Nodig je ooit een PDF zonder browser (een maandelijkse archiefkopie, een
## bijlage per mail), dan is dat een klein script over dezelfde route, in de
## trant van scripts/visuele_steekproef.mjs: Chrome openen op /rapport met een
## sessiekoekje en page.pdf() aanroepen. Gemeten en werkend bevonden op 18 aug;
## bewust niet gebouwd zolang niemand het vraagt.

## De visuele steekproef: elk scherm in beide talen als PNG, voor menselijke
## ogen. Vereist een draaiende dev-server (make dev) en de sleutels in
## platform/.env.local; de kop van het script legt de details uit. Stond tot
## 18 aug 2026 nergens in dit bestand en was daarmee onvindbaar voor wie de
## Makefile als index gebruikt — en dat is precies waar dit bestand voor is.
steekproef:
	node scripts/visuele_steekproef.mjs reports/steekproef

## Het platform lokaal draaien op het echte contract. Draai eerst: make contract
ui: contract
	cd platform && npm run dev

## Alleen de dev-server, zonder de contractbouw. Een fout in contract_bouw.py
## presenteert zich via `ui` als "de UI start niet"; dit doel houdt die twee uit
## elkaar. Vereist dat platform/contract/ er al staat (eenmalig: make contract).
dev:
	cd platform && npm run dev

## Volledige keten vanaf de bronbestanden tot een draaiend contract.
## Sinds 18 aug 2026 zonder PDF-stap: het rapport wordt niet meer gebouwd maar
## gelezen (zie hierboven), en deze keten blijft daarmee browserloos.
alles: canoniek contract backtest

## De volledige herbouw uit de bron: schema, extract, canoniek, database,
## contract. Dit is het "één commando" uit CLAUDE.md (laag 2 en
## app-gereedheid). Vergt .env met ODOO_* en SUPABASE_DB_URL.
herbouw: db-migreer extract extract-bonnen extract-uren canoniek db-laad contract db-contract
