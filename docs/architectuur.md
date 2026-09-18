# Architectuur

_Geschreven 12 augustus 2026. Dit document zegt waar elk stuk draait en waarom daar. Wat er gebouwd wordt staat in `scope.md`, in welke volgorde in `plan-fase1.md`._

> **Stand 19 augustus 2026.** De tekening en de afwegingen hieronder zijn op deze datum bijgewerkt aan wat er werkelijk draait: de sync is een volledig extract met een poortwachter op `write_date` (geen incrementeel extract, beslist 17 aug), de cron staat op 01:30 UTC maar is nog uitgeschakeld — de runner-invoer is sinds 19 aug geregeld, wat rest is één handmatige run in GitHub Actions die groen moet komen (zie `beheerdraaiboek.md`), Deliveroo loopt via een download die Sophie zelf uit Partner Hub haalt (S1), TGTG is bevroren op de historiek t/m juli 2026 (blok 9 geschrapt 17 aug), en het hostingmodel is beslist: een project binnen de organisatie van asklien.ai (vraag 40, zie `scope.md` derde herziening).

## De tekening

```
  BRONNEN
  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
  │ Odoo             │  │ TGTG             │  │ Deliveroo            │
  │ XML-RPC          │  │ pdf-dump         │  │ CSV's uit Partner    │
  │ volledig extract,│  │ bevroren t/m     │  │ Hub, door Sophie     │
  │ poortwachter op  │  │ juli 2026        │  │ zelf; nog niet       │
  │ write_date       │  │ (blok 9 weg)     │  │ ontvangen (S1)       │
  └────────┬─────────┘  └────────┬─────────┘  └──────────┬───────────┘
           │                     │                       │
           └─────────────────────┼───────────────────────┘
                                 ▼
                   ┌─────────────────────────────┐
                   │  INLAADLAAG + BEREKENING    │   Python, pandas
                   │  GitHub Actions, 01:30 UTC  │   NIET op Vercel
                   │  (cron nu bewust uit)       │
                   │  normaliseren → aggregeren  │
                   └──────────────┬──────────────┘
                                  │ schrijft alleen aggregaten
                                  ▼
        ┌──────────────────────────────────────────────┐
        │  SUPABASE (EU-regio)                         │
        │  ┌────────────────────┐  ┌────────────────┐  │
        │  │ Postgres           │  │ Auth           │  │
        │  │ feiten + afgeleide │  │ login, sessies │  │
        │  │ tabellen           │  │ 2 rollen       │  │
        │  └────────────────────┘  └────────────────┘  │
        └───────────────────────┬──────────────────────┘
                                │ leest, rekent niet
                                ▼
        ┌──────────────────────────────────────────────┐
        │  VERCEL                                      │
        │  API-routes  =  het contract (JSON, klein)   │
        │  Web-UI      =  schermen in de huisstijl     │
        └───────────────────────┬──────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │ Mobiele app, fase 2   │
                    │ zelfde contract       │
                    └───────────────────────┘

  BLIJFT LOKAAL, gaat nooit naar de cloud en nooit in git:
  de ruwe Odoo-extract, de 250 TGTG-pdf's, het verzekeringsextract
```

## Waarom de ETL niet op Vercel draait

Vercel is serverless Node met korte tijdslimieten. De inlaadlaag is Python met pandas, parst 250 pdf's en praat XML-RPC met Odoo. Dat past daar niet in, en het erin wringen levert een fragiele constructie op die bij elke groei opnieuw stukgaat.

Drie opties, in volgorde van voorkeur:

| | | |
|---|---|---|
| **GitHub Actions op cron** | *voorkeur* | Gratis binnen de limieten, in de repo versioneerd, logs en secrets zitten er al, niets extra te beheren. Bij oplevering verhuist het mee met de repo |
| Kleine VPS met cron | alternatief | Een paar euro per maand, maar het is een machine die iemand moet onderhouden en die bij overdracht apart geregeld moet worden |
| Supabase Edge Functions | afgeraden | Deno/TypeScript. Zou betekenen dat de hele inlaadlaag herschreven wordt in een taal die slechter is in dataverwerking |

De cron staat op 01:30 UTC, maar is sinds 18 augustus uitgeschakeld (het schedule-blok is uitgecommentarieerd). De reden — de runner miste de TGTG-bestanden en de beheerconfig — is sinds 19 augustus weg: het bevroren TGTG-kanaal komt uit de database, de sluitingslijst staat in git en het kostenmodel wordt in de database bewaard. Wat rest is één handmatige run via workflow_dispatch die groen komt; pas daarna gaat het schedule-blok aan. Als hij draait, geldt: zolang de bakkerij dicht is, is er niets bij te werken, en de poortwachter maakt dat zichtbaar in de logs in plaats van stil.

## Wat waar staat

| Laag | Waar | Wie beheert |
|---|---|---|
| Ruwe brondata | lokaal op de werkmachine, `data/`, gitignored | wij, tot oplevering |
| Verzekeringsextract | lokaal, parquet, eenmalig | wij |
| Inlaadlaag en berekening | GitHub Actions, code in de repo | wij, daarna overdraagbaar |
| Database en auth | Supabase, `eu-north-1` (project sinds 14 aug) | project in de Supabase-organisatie van asklien.ai (vraag 40, zie `scope.md` derde herziening), beheertoegang voor ons |
| API en UI | Vercel (Lien) | idem |

**G7 is beslist (14 augustus) en afgehandeld.** De vraag die hier eerst stond — infrastructuur op naam van de eindklant of van Lien — is beantwoord met vraag 40: het project staat binnen de Supabase-organisatie en het Vercel-team van asklien.ai, verrekend via het onderhoudsabonnement aan de eindklant. S11, het databasewachtwoord, kwam binnen op 18 augustus; de database staat sindsdien vol en het platform online. Wat er juridisch nog bij hoort (verwerkersovereenkomst Lien↔Renard, exitregeling vóór de livegang) staat in vraag 41/S10.

## Wat er in de database komt, en wat niet

**Wel:** geaggregeerde productverkoop — datum, product, kanaal, aantal, omzet, en de afgeleide tabellen die daaruit volgen. Plus de gebruikers van het platform.

**Niet:** `partner_id`, klantnaam, adres, bonnotitie, of welk klantveld dan ook. De extractie vraagt die nooit op. Ook niet: de ruwe pdf's, de bonregels, het verzekeringsextract.

Gevolg: er staan geen persoonsgegevens van bakkerijklanten in het systeem. Wel die van de **gebruikers** van het platform, zodra er een login is. Klein, maar het bestaat, en het hoort in het verwerkingsregister van de eindklant.

## Het contract

Elk scherm heeft één genummerd JSON-antwoord. Niet één grote endpoint waar alles uit komt, en niet één endpoint per grafiek.

Regels die vastliggen:
- Antwoorden zijn voorgeaggregeerd en klein. Een scherm haalt geen 50.000 rijen op
- Elk antwoord is versioneerd, zodat de app van fase 2 niet breekt als de web-UI verandert
- Elk veld dat geblokkeerd is (marge zonder G1, Deliveroo zonder G4) komt terug als expliciet `onbeschikbaar` met een reden, niet als `null` en niet als nul
- De UI rekent nooit. Wat er niet in het contract zit, staat niet op het scherm

---
*Aangemaakt 12 augustus 2026.*
