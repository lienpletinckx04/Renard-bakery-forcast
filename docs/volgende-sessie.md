# Volgende sessie — plan (bijgewerkt 25 aug 2026, ná het skelet van blok 5)

_Lees dit vóór je iets doet, samen met de jongste `dagboek.md`-entry en de blokkadelijst in `todo.md`. Verwijder of herschrijf dit bestand zodra het op zijn beurt achterhaald is._

## Het einddoel, in één zin

Fase 1 levert op **27 augustus** een werkend CFO-platform met login: cijfers uit de berekeningslaag, twee talen, huisstijl, gebackteste prognose, en elk gat eerlijk getoond met de reden. Alles wat daar niet rechtstreeks aan bijdraagt is bijzaak — toets elke taak hieraan vóór je begint.

## Als je maar één ding leest

**De opleverdatum van fase 1 is 27 augustus, en er is tussen 19 en 25 augustus geen enkele commit bijgekomen** — de zes dagen ertussen hebben aan de codekant niets bewogen. Wat de 27e nog kan bedreigen ligt alle vier bij anderen: S1 (Deliveroo, dagelijks permanent verlies), S13 (gebruikerslijst), S14 (leeg Vercel-project) en vraag 55. De tabel "Geblokkeerd door anderen" hieronder is de stand van 19 augustus en is op 25 augustus **niet opnieuw nagegaan** — doe dat eerst, vóór je aan iets anders begint.

**De repo-transfer is een feit.** Hij staat nu op `Asklien/asklien-bakkerij` (org `Asklien`, private). Kwinten heeft daar `pull`, `push` en `triage` — géén `admin`: settings, secrets en collaborators liggen bij Lien. De oude remote-URL (`liveatwembley/...`) werkte nog via de GitHub-redirect en is op 25 augustus rechtgezet naar de canonieke URL, want zo'n redirect breekt zodra iemand een nieuwe repo op de oude naam aanmaakt. Alles over de overdracht: `docs/overdracht.md` en `docs/instructies-lien.md`.

## Af op 25 augustus: het skelet van blok 5

Twee commits (`9d2ab88` code, `1e07a0c` docs), CI groen, suite op 780. De volledige verantwoording staat in de dagboekentry van 25 aug en in `beslissingen.md` (vier entries).

- **Gebouwd is alles dat niet van de exportvorm afhangt.** `DeliverooFormaatFout`, de vorm van beide Partner Hub-rapporten, de mappenconventie in code (`data/raw/Deliveroo/JJJJ-MM-DD_JJJJ-MM-DD/`), `klopt_met_bereik` (de dag/maand-vanger) en `gaten_in_dekking`. Plus `make deliveroo`: het inventariseert de downloads, meldt welk rapporttype mist en waar de gaten in de twaalf maanden zitten, en schrijft niets.
- **Niet gebouwd, met opzet.** `parse_items_sold` en `parse_orders` heffen `NotImplementedError` met de weg erin — geen lege lijst, want dat zou een kanaal op nul zetten dat hoort te melden dat het onbeschikbaar is.
- **Eén valstrik staat gedocumenteerd op de plek waar iemand hem nodig heeft.** Op de laaddag verhuist het kanaal in `kwaliteit.py` van `BEKEND_AFWEZIG` naar `BEVROREN`, en dat moeten beide regels zijn in dezelfde commit. Wie alleen de eerste doet, laat een kanaal met data zwijgen over zijn achterstand; wie de tweede vergeet, laat het na twee dagen permanent 'achter' staan (`_stand_dagelijks`, `MAX_ONGEMETEN_DAGEN` = 2) op een bron die per definitie niet dagelijks bijkomt.
- **De databasekant vraagt niets.** Migratie 002 laat `deliveroo` al toe in `fact_kanaalkost` en `bereid_kanaalkost` geeft de kanaalkolom al door. Geen migratie 015.
- **Eén correctie op het plan van diezelfde ochtend:** de raming van 0,5 dag gold voor het gunstige geval, en het alarm bij een vergeten `BEVROREN`-regel gaat na twee dagen af en niet na 45. Beide staan nu goed in de code en in het plan.

## De sluitingskalender (19 augustus): gebouwd, live en getest

**De sluitingskalender is gebouwd, live en getest.** Het scherm Sluitingsdagen staat in het menu boven Prognose: de Belgische feestdagen twaalf maanden vooruit als bevestigingslijst (open / dicht / nog niet beantwoord), eigen periodes, en één vaste wekelijkse sluitingsdag als regel. Migraties 011–014 staan op Supabase, de bestandslijst is eenmalig overgezet (`make db-sluitingen`), de schrijfroute is end-to-end tegen de echte database getest, en het per-dag-voorbehoud vervangt het venstervoorbehoud op het prognosescherm. De zin "vul het JSON-bestand aan" bestaat niet meer.

Wat daarbij mee naar boven kwam en óók gerepareerd is: **pg-safeupdate op de gehoste route weigerde de kale deletes van migratie 009** — de kostenmodel-opslag vanaf het formulier had dus nog nooit kunnen werken; niemand had het gemerkt omdat nog niemand had opgeslagen. Migratie 014 herdefinieert beide schrijffuncties met `delete ... where true`. De les staat in 014 zelf: een lokale Postgres en de CI-container laden die bibliotheek niet, dus groene tests bewijzen de gehoste schrijfroute niet — meet die apart.

Het valt buiten `scope.md` en is gebouwd op beslissing van Kwinten vóór het antwoord op vraag 65; die vraag is nu een **bevestiging achteraf** (1 dag bouwtijd, onder de raming van 1,5). Vraag 64 — de datums zelf — ligt onveranderd bij Lien, alleen is het antwoord nu twee klikken per rij op het scherm in plaats van een lijstje per mail.

## Stand: het platform staat online

- **Live:** `https://renard-bakery.vercel.app`, met `CONTRACT_BRON=db`. Twee beheerders via `PLATFORM_GEBRUIKERS`.
- **Database:** migraties t/m **014** toegepast op Supabase (idempotent), 316.469 rijen, contract in `contract_antwoord` (**zestien antwoorden**: zeven schermen plus winkelindex, beide talen). RLS gemeten, `anon` nul leesrecht, van buitenaf 401.
- **Sluitingskalender:** `sluitingsdag` draagt de 23 dagen van de zomersluiting (bron `bestand`), nul weekregels; alles wat een beheerder op het scherm bewaart, telt mee vanaf de eerstvolgende herrekening.
- **Tijdelijk in Kwintens persoonlijke Vercel-scope** — zie **S14** in `todo.md`.
- **De repo gaat naar Lien**; zij deployt zelf. Alles daarover: **`docs/overdracht.md`**. Belangrijkste feit: **GitHub-secrets verhuizen niet mee bij een repo-transfer**.

## Af op 19 augustus (avondsessie): twee contractschulden

Additief, en beide bewezen op het scherm én in de database. De verantwoording staat in de dagboekentry en in `beslissingen.md`.

- **`briefing.gedeeld`** — hetzelfde briefingpunt staat in een volledig rapport nog één keer in plaats van zes. Het merk wordt gezet op de uitgangen van `_versheidspunten`; de component zet `data-gedeeld`, en één CSS-regel naast `data-buiten-rapport` verbergt het in elk onderdeel behalve het eerste. **Lees de grens vóór je hem uitbreidt:** `gedeeld` betekent "staat op élk scherm". Merk je een punt dat maar op twee schermen staat, dan verdwijnt het uit elk rapport dat met een ander onderdeel begint — daarom draagt het Deliveroo-actiepunt het merk niet.
- **`kerncijfer.<sleutel>`** — `berekening.Kerncijfer` heeft nu een `sleutel` (`omzet_7`, `omzet_30`, `stuks_7`, `gemiddelde_dagomzet`) naast zijn tweetalige `label`. Wie er een vijfde kerncijfer bij zet, zet er een label bij in `platform/lib/toelichting.ts`; een test leest dat bestand en valt anders om.

## Openstaand eigen werk, in volgorde van belang

1. **De nachtelijke cron aanzetten.** Er is geen inhoudelijke blokkade meer. Wat rest is één handeling die een mens hoort te doen: Actions → nachtelijke-sync → *Run workflow*, die run groen zien, en dán pas de drie regels in het `on:`-blok activeren. _Op 19 aug (avond) geprobeerd vanaf de opdrachtregel: de `gh`-CLI op deze machine krijgt zijn credential-keyring niet open, dus dit moet via de webinterface._ Let op: de nachtrun draait nu ook de sluitingskalender mee (canoniekbouw leest de database onder `CONTRACT_BRON=db`); een onbereikbare database is daar een harde stop, met reden.
2. **Deliveroo-parser** (blok 5) — **op 25 augustus gesplitst; de helft die niet van de exportvorm afhangt staat er.** Gebouwd: `bakkerij/sources/deliveroo_parse.py` (foutklasse, de vorm van beide rapporten, mappenconventie, `klopt_met_bereik`, `gaten_in_dekking`), `scripts/deliveroo_extract.py` + `make deliveroo` (inventaris, schrijft niets), 12 tests, en de schakelinstructie in `kwaliteit.py` op beide plekken. Wat rest is het lezen zelf, en dat wacht op échte bestanden — de les van de TGTG-parser. **Lees `docs/plan-deliveroo-parser.md` vóór je begint; daar staat alles.** De raming is niet langer 0,5 dag: het is 0,5 mét order-sleutel en 1 à 1,5 zonder, en welke van de twee beslist **vraag 66** (één proefexport van drie dagen). Die vraag gaat aan S1 vooraf zonder die te vervangen.
3. **De gebruikersaanmaakroute** (S13, afspraak 19 aug): Lien doet de lijst zelf, wij leveren de mogelijkheid om gebruikers te maken. Vandaag bestaat alleen `scripts/maak_gebruiker.mjs`.

## Geblokkeerd door anderen

| | Wat | Bij wie |
|---|---|---|
| **S1** | Deliveroo-rapporten uit Partner Hub | Sophie — **elke dag venster is permanent verlies** |
| **S13** | Gebruikers: Lien doet de lijst zelf, wij leveren de aanmaakroute | Lien |
| **S14** | Eén leeg Vercel-project in team `asklien` | Lien |
| **S15 / vraag 64** | De sluitingsdagen t/m eind 2027 **bevestigen op het scherm Sluitingsdagen** — een kwartiertje met een beheerdersaccount | Lien |
| **vraag 66** | Eén proefexport van drie dagen uit Partner Hub, beide rapporttypes — beslist de bouwwijze én of Items Sold per dag uitsplitst (zo niet: ~365 downloads in plaats van 4) | Lien → Sophie |
| vraag 55 | Scenario-UI ja of nee | Lien |
| vraag 58 | Bevestiging van vijf uitbreidingen + de knoop notificaties/AI-uitleg | Lien |
| vragen 59–63 | Vijf voorstellen uit de externe review, alle vijf buiten fase 1 gehouden | Lien |
| **vraag 65** | De sluitingskalender: bevestiging achteraf (gebouwd 19 aug, 1 dag) | Lien |

## Af op 19 augustus (dagsessie): de sluitingskalender, van migratie tot scherm

De volledige verantwoording staat in de dagboekentry. Wat je moet weten om verder te kunnen:

- **Nieuwe lagen:** migraties 011 (tabellen) t/m 014 (safeupdate-reparatie); `bakkerij/sluitingskalender.py` (uitspraken, weekregels, kalenderverrijking, per-dag-dekking); `bakkerij/db/sluitingen_db.py`; `scripts/sluitingen_laad.py` (`make db-sluitingen`); contractantwoord `sluitingsdagen`; scherm + server-actie + `lib/sluitingsdagen(-db).ts`.
- **Rangorde van de sluitingsbronnen: agenda > database > bestand.** Een bevestigd-open dag knipt een dicht-dag uit het bestand weg; een agenda-dag wint altijd en een conflict wordt gemeld, niet stil beslecht. Binnen de database wint de uitspraak (één dag) van de weekregel.
- **Het voorbehoud op het prognosescherm werkt per dag.** Een dag is beantwoord als hij binnen het bereik van de bestandslijst valt of een uitspraak in de database heeft; alleen onbeantwoorde dagen dragen nog het voorbehoud, met de handeling erbij (het scherm, niet het bestand).
- **De opslag is meteen zichtbaar op het scherm, de prognose volgt 's nachts** — zelfde cadans als het kostenmodel, en het scherm zegt dat eerlijk.
- **`DATASLEUTELS` in `tests/test_contract.py` en het `Scherm`-type kennen nu zeven schermen**; de contractboom telt zestien sleutels per krimpwachtvergelijking.

## Twee datums waarop iets vanzelf ophoudt

Stonden hier als geheugensteun; één ervan is nu structureel opgelost.

- ~~**24 augustus 2026** — de sluitingslijst is op.~~ **Opgelost op 19 augustus:** het scherm Sluitingsdagen vervangt het bestand. Wat rest is vraag 64 — de bevestigingen zelf.
- **10 mei 2027** — de Franstalige schoolvakanties zijn op (het regime waarop het productiemodel draait). `make vakanties` gedraaid op 19 aug: de bron publiceert zelf nog niet verder. Een wachtstand, geen vergeten commando. Een test wordt op 1 september 2027 vanzelf rood.

## Wat níét is opgelost, en niet verhuld wordt

- **De galette-/Driekoningenpiek.** Januari draagt 24,2 % van de jaarfout, de drie galette-dagen staan op 46,1 % WAPE. Elke kandidaat is gemeten en verloor. De oorzaak is de historiek (één januari in het venster), niet het model. Nieuw sinds 19 aug: een beheerder kan 6 januari als **bevestigd open** aanmerken, wat het voorbehoud weghaalt — aan de piekfout zelf verandert dat niets.
- **Uit het sluitingskalender-ontwerp bewust niet meegebouwd:** de periodevergelijking eerlijk maken wanneer er een sluiting in één van de twee periodes valt, en een briefingpunt "volgende week twee dagen dicht". Genoteerd in `open-punten.md`; apart afwegen, niet stilzwijgend meenemen.

## Werkafspraken die blijven gelden

- **Eerst kijken, dan bouwen.** Een zichtbare wijziging die je niet op een afbeelding hebt gezien, is niet af.
- **Repareer de wacht, niet alleen de vondst.** (Vandaag toegepast: niet alleen de sluitingsfunctie gerepareerd maar ook de identieke fout in het kostenmodel, plus de les gedocumenteerd dat lokale tests de gehoste schrijfroute niet bewijzen.)
- **Controleer elke bewering vóór ze in een document gaat.** Agentbevindingen zijn vondsten, geen feiten.
- **Focus op deze ene eindklant.** Review-input over andere bakkerijen of multi-tenant wordt niet gebouwd en niet als optie opgebracht.
- Einde sessie: dagboek-entry (zelfde dag naar Lien), beslissingen via de beslissingsschrijver, commits gescheiden per spoor, en `make controle` vóór de commit.
