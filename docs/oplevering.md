# Opleverdocument (F1)

_Fase 1, stand 19 augustus 2026. Dit document zegt waar elk cijfer vandaan komt,
wat het platform bewust niet toont, en wat er nog openstaat. Het hoort samen met
`beheerdraaiboek.md` (hoe het draait) en `scope.md` (wat er is afgesproken)._

## Wat er staat

Een financieel stuurplatform met zes dashboardschermen achter een login
(acht routes, waarvan zeven bewaakt; alleen het aanmeldscherm staat
erbuiten), in twee talen (NL/FR), met
een briefing bovenaan elk scherm en een samen te stellen CFO-rapport om af te
drukken of als PDF te bewaren, gebouwd als keten van
lagen die elk apart te controleren zijn:

```
bronnen (Odoo-kassa)                     make extract
  -> canoniek datamodel                  make canoniek
  -> berekening + contract (één JSON     make contract
     per scherm plus de winkelindex,
     twee keer gebouwd: NL en FR)
  -> schermen én rapport                 make dev
```

Het rapport staat bewust niet als eigen stap in die keten: het is dezelfde
schermen, gekozen per onderdeel, gelezen uit hetzelfde contract op het moment
dat iemand het opvraagt (`/rapport`, achter de login). Daarmee kan het nooit
oudere cijfers tonen dan het scherm ernaast, en bestaat er geen tweede
opmaaklaag die van de huisstijl van de schermen kan afwijken. De PDF maakt de
browser: **Rapport** → onderdelen aanvinken → **Afdrukken of PDF**.

Elke laag is herbouwbaar uit de vorige met één commando; `make alles` bouwt
de lokale rekenketen (canoniek → contract → backtest), en de volledige
herbouw uit de bron — schema, extract, canoniek, database én contract, het
"één commando" uit `CLAUDE.md` — is `make herbouw`. De schermen lezen
uitsluitend het contract en rekenen zelf niets —
daardoor kan de app van fase 2 dezelfde antwoorden hergebruiken.

**De gehoste versie draait.** Het databasewachtwoord kwam binnen op 18 augustus;
diezelfde avond zijn de migraties toegepast, is de database gevuld (316.469
rijen) en staat het platform online op `https://renard-bakery.vercel.app`, met
de database als contractbron (`CONTRACT_BRON=db`). Wat daar nog omheen staat:
de nachtelijke sync (Odoo → canoniek → Postgres, GitHub Actions met een
poortwachter op `write_date`) is gebouwd en droog bewezen (`make sync-droog`),
de secrets staan gezet, en er rest één handmatige run in GitHub Actions vóór
de planning aan mag. De login op Supabase Auth zit achter `AUTH_BRON=supabase`
en wacht op S12/S13. Zie `beheerdraaiboek.md` en de tabel onderaan.

## Waar elk cijfer vandaan komt

| Cijfer | Bron | Bewerkingsregels |
|---|---|---|
| Omzet, stuks (winkel) | Odoo-kassaregels, alle drie de kassa's opgeteld | excl. btw; alleen gemeten open dagen (drempelregel `DREMPEL_OPEN`); geld in centen, half naar boven |
| Deliveroo | — | geen data; het kanaal toont zich als onbeschikbaar met reden (poort G4/S1) |
| Vergelijkingen | eigen historiek | alleen bij gelijk aantal gemeten open dagen, anders "geen vergelijking, met reden"; periodes vergelijken op gemiddelde per open dag met beide aantallen in het label |
| Marges | **handinvoer** door een beheerder (Instellingen, kostenmodel: zelf samengestelde kostencriteria per productgroep; brutomarge = 100 − som van de ingevulde criteria) | Odoo heeft geen kostprijzen (1.556.054 van 1.556.770 bonregels op nul); gewogen marge telt alleen over ingevulde groepen, de dekking staat erbij |
| Prognose | `weekdag_niveau` + schoolvakantiecorrectie (Franstalig regime) | 7,8% WAPE dagomzet, gemeten in een rolling-origin backtest; band gekalibreerd op out-of-sample gemeten dekking; per categorie een eigen prognose met eigen WAPE; aangekondigde sluitingsdagen (`config/sluitingsdagen.json`, later de agenda) vallen uit het venster, met de reden op het scherm |
| Datakwaliteit | dodemansknop + zeven wachters | op Instellingen voluit; de ergste uitkomst in de voettekst van elk scherm |

TGTG stond hier tot 18 september 2026 als derde kanaal (netto, bevroren op de historiek t/m juli 2026). Het is sindsdien uit scope: het kanaal, zijn data en het bevriezingsmechanisme zijn verwijderd (zie `beslissingen.md`).

## Wat het platform bewust niet toont

- **Geen cijfer zonder bron.** Een geblokkeerd cijfer staat er als
  "niet beschikbaar" met de reden (harde regel 8) — Deliveroo, marges zonder
  invoer, vergelijkingen over ongelijke vensters, weekdagen zonder meting. (Tot
  18 september 2026 gold hetzelfde voor een bevroren kanaal, TGTG; dat kanaal
  is sindsdien uit scope.)
- **Geen vraagprognose.** Het model voorspelt verkoop; 33% van de gewogen
  product-dagen draagt een leeg-reksignaal (uitverkoop), dus de echte vraag
  ligt op die dagen hoger. Zie `reports/backtest-rapport.md` §5.
- **Geen productprognose op het scherm.** Gemeten op 20,2% WAPE per
  product-dag; zonder marges is er geen beslissing die daarop kan bouwen.
- **Geen scenario's op het scherm.** De motor bestaat (drie kalendervarianten
  uit dezelfde gebackteste voorspeller, achter `PROGNOSE_SCENARIOS=1` in de
  contractbouw), maar geen enkel scherm toont ze zolang vraag 55 openstaat —
  en een vrije schuif zoals "prijs +5%" komt er ook daarna niet (harde
  regel 7).
- **Geen B2B-kanaal** (€ 1,8 mln facturatie): buiten scope, vraag 43.

## Wat nog openstaat

| | Wat | Wacht op |
|---|---|---|
| Nachtelijke sync | de planning staat nog uit. Alles eromheen is klaar: de workflow, de vijf secrets, en de invoer die de runner nodig heeft | één handmatige run in GitHub Actions die groen komt; daarna gaat het schedule-blok aan |
| Login op Supabase Auth | omschakelen naar `AUTH_BRON=supabase`; de code is klaar, rol strikt uit `app_metadata` | **S12** (zelfregistratie uit) + **S13** (gebruikerslijst) |
| Deliveroo | het hele kanaal | **S1** (Partner Hub-rapporten, bij Sophie — het venster schuift dagelijks) |
| Marges | de eerste échte invoer (tien categorieën dekken 95% van de omzet) | eindklant, vraag 19 herformuleerd |
| Sluitingskalender | de agenda-aansluiting staat klaar; tot dan voedt `config/sluitingsdagen.json` de prognose | vraag 45/46 |
| Scenario's op de prognose | het scherm; de motor en het contractveld bestaan | vraag 55 |
| Rollen | lezersrol afdwingen in de database, gebruikersbeheer, aanmeldlogboek | C3/C4, na S12/S13 |

## De eerlijkheidsclausule

Aanvaarding van de prognose hangt niet af van de vraag of ze goed genoeg is
naar de smaak van de eindklant (scope.md): het backtest-rapport
(`make backtest-rapport`) toont wat ze kan én wat getoetst en afgewezen is.
Elke bewering op een scherm is na te rekenen uit de lagen eronder.
