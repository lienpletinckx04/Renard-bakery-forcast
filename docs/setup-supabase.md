# Supabase opzetten

_Geschreven 13 augustus 2026. Afvinklijst, geen achtergrondverhaal — het waaróm staat in `stack.md` en `architectuur.md`._

> **Sleutels gaan nooit door een chatbericht.** Ook niet naar mij. Vul ze rechtstreeks in `.env` in; dat bestand is gitignored en dat blijft zo.

---

## 0. Op wiens account — beslist

Beslist met vraag 40: het project staat binnen de Supabase-organisatie van asklien.ai, verrekend via het onderhoudsabonnement. Wat er nog rest is juridisch, niet technisch: de verwerkersovereenkomst Lien↔Renard en de exitregeling (vraag 41/S10), te regelen vóór de livegang.

---

## 1. Het project aanmaken — historisch, gedaan op 14 augustus 2026

> **Deze stap is klaar:** Lien heeft het project op 14 augustus aangemaakt (organisatie `asklien.ai`, plan Pro, regio `eu-north-1`, Stockholm). De sectie blijft staan voor het geval er ooit een tweede project nodig is; **het draaiboek begint bij §2.**

| | |
|---|---|
| **Regio** | een **specifieke** EU-regio, niet "Europe" en niet "closest to me". Dit project draait in `eu-north-1` (Stockholm), door de opdrachtgever gekozen op 14 aug 2026 |
| **Plan** | **Pro** ($25/maand) |
| **Naam** | vrij, bijvoorbeeld `renard-bakery` |

**Waarom Pro en niet Free:** Free pauzeert het project bij inactiviteit en heeft geen dagelijkse back-ups. Een CFO-platform dat op maandagochtend gepauzeerd blijkt, is stuk. Eén betaald project volstaat; komt er later een dev-omgeving, dan is dat een **gratis** project ernaast. Meerdere betaalde projecten is de manier waarop de kosten hier ontsporen.

Bij het aanmaken kies je een **databasewachtwoord**. Dat zie je één keer. Meteen in een wachtwoordbeheerder — je hebt het nodig bij stap 3 en het is niet opnieuw op te vragen, alleen te resetten.

> **EU-regio is hier technisch, niet juridisch.** Compute in Stockholm verandert niets aan het feit dat Supabase en AWS Amerikaanse entiteiten zijn. Bedoelt de eindklant "EU" juridisch, dan is dat een gesprek vóór de livegang.

---

## 2. De API-sleutels

**Project Settings → API Keys.**

| Wat je zoekt | Waar het heen gaat in `.env` |
|---|---|
| projecturl `https://<ref>.supabase.co` | `NEXT_PUBLIC_SUPABASE_URL` |
| de `sb_publishable_…`-sleutel | `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` |
| de `sb_secret_…`-sleutel | **leeg tot `CONTRACT_BRON=db`** |

De secret key blijft leeg zolang het contract uit bestanden komt. Zodra `CONTRACT_BRON=db` aangaat, krijgt hij precies één plek: `SUPABASE_SECRET_KEY` in de **Vercel-serveromgeving**, waar het platform er de contractantwoorden mee leest via PostgREST (zie de slotsectie hieronder en `stack.md`, "Waar de secrets staan"). De ETL schrijft via een rechtstreekse Postgres-verbinding en heeft hem niet nodig. Een sleutel die nergens anders staat, kan niet lekken.

**Zie je alleen `anon` en `service_role`?** Dan zit het project op de oude sleutelgeneratie. Meld het; dan passen we de namen in `.env.example` aan. Alles met `NEXT_PUBLIC_` wordt in de JavaScript-bundel gebakken — er bestaat geen server-only variant. Eén typefout lekt een sleutel permanent, ook in de deploy-geschiedenis.

---

## 3. De verbindingsstring — hier zit de valkuil

**Project Settings → Database → Connection string → tabblad `Session pooler`.**

Neem **niet** de "Direct connection" die standaard bovenaan staat.

```
postgresql://postgres.<project-ref>:<wachtwoord>@aws-0-<regio>.pooler.supabase.com:5432/postgres?sslmode=require
```

De regio in die hostnaam is die van je project (hier `eu-north-1`). De controle in
`bakkerij/db/verbinding.py` kijkt bewust alleen naar het achtervoegsel
`.pooler.supabase.com` en niet naar de regio — een project verhuizen mag geen
codewijziging vergen.

Vier dingen om na te lopen:

- [ ] hostnaam bevat **`pooler.supabase.com`** — niet `db.<ref>.supabase.co`
- [ ] poort **5432** — niet 6543
- [ ] gebruiker **`postgres.<project-ref>`** — niet kaal `postgres`
- [ ] **`?sslmode=require`** erachter — dat moet je zelf toevoegen, Supabase zet het er niet in

Dit gaat in `.env` als `SUPABASE_DB_URL`. **Die regel bestaat nog niet, je moet hem zelf toevoegen.**

Je hoeft dit niet te onthouden: `make db-droog` en `make db-laad-droog` toetsen alle vier en weigeren te starten met een leesbare uitleg. Zie ook de foutentabel onderaan.

---

## 4. Twee instellingen die nu moeten

**Authentication → Sign In / Providers → zelfregistratie UIT.** Standaard kan iedereen met een e-mailadres een account maken. Op een platform met de omzetcijfers van de klant is dat geen instelling die je "later" doet. Gebruikers komen binnen via een uitnodiging.

**Authentication → JWT Keys → ES256: mag, maar niets in de code hangt eraan.** De oorspronkelijke motivering ("zonder ES256 doet `getClaims()` een netwerkcall per verzoek") is op 18 augustus tegen de code gelegd en klopt niet meer: `platform/lib/auth-supabase.ts` gebruikt geen SDK en geen `getClaims()` — het toetst het wachtwoord via de token-endpoint, gooit het access token weg en tekent een eigen sessiecookie. Er wordt dus nergens een Supabase-JWT geverifieerd, en het ondertekeningsalgoritme is voor dit platform onverschillig. **Gevolg voor S12: die blokkade is smaller dan de lijst suggereert** — wat écht moet vóór `AUTH_BRON=supabase` is alleen de zelfregistratie uit (plus S13, de gebruikerslijst). ES256 aanzetten blijft een redelijke toekomstvaste instelling voor het geval er later wél tokens gelezen worden; het blokkeert alleen niets. S12 blijft als nummer bestaan; de noot staat ook bij S12 in `todo.md`.

---

## 5. Dan het schema erin

```bash
make db-droog        # toont de migraties, legt geen verbinding
make db-migreer      # past ze toe. Idempotent: tweede keer is een lege run
```

Verwachte uitvoer: tien migraties toegepast (001 t/m 010, van `001_dimensies` tot `010_syncstand`).

```bash
make db-laad-droog   # leest, bereidt voor, controleert verwijzingen. Schrijft niet
make db-laad         # schrijft alles weg in één etl_run
make db-contract     # de contractantwoorden erachteraan, naar contract_antwoord
```

Verwachte orde van grootte: 2.652 kalenderdagen, 331 producten (die mét verkoop sinds jan 2025), 221.375 verkoopregels.

---

## 6. Na afloop controleren

- [ ] **Supabase-linter draaien** (Database → Advisors). Die vlagt tabellen zonder RLS en policies zonder `TO`. Er zou niets uit moeten komen — de migraties zetten RLS per tabel — maar draai hem, want dit is de enige controle die de echte database ziet.
- [ ] **`etl_run`** bevat één rij met status `goed` en een gevulde `geeindigd_op`.
- [ ] **Test de afscherming:** haal een tabel op met de publiceerbare sleutel zonder ingelogd te zijn. Dat hoort niets terug te geven. Lukt het wél, dan staat er iets open dat dicht hoort.

---

## 7. Als er iets misgaat

Deze foutmeldingen wijzen naar iets ánders dan de oorzaak. Daarom staan ze hier.

| Wat je ziet | Wat het werkelijk is |
|---|---|
| `network is unreachable`, vooral in GitHub Actions | Je gebruikt `db.<ref>.supabase.co`. Die is IPv6-only en runners hebben onbetrouwbare IPv6-uitgang. Neem de pooler-hostname. Je gaat anders firewalls en Supabase-status controleren |
| Een SQL- of prepared-statement-fout bij `COPY` | Poort 6543 (transaction mode) in plaats van 5432. Transaction mode kent geen prepared statements en botst met psycopg3 |
| `FATAL: password authentication failed for user "postgres"` | **Het wachtwoord, en niets anders.** Zie de meting hieronder: dit is níét het spoor van een verkeerde gebruikersnaam of een verkeerd project — die geven een andere fout |
| `ENOIDENTIFIER: no tenant identifier provided (external_id or sni_hostname required)` | Gebruiker `postgres` in plaats van `postgres.<project-ref>`. De pooler weet dan niet naar welk project hij moet routeren en komt niet eens bij het wachtwoord |
| `ENOTFOUND: tenant/user ... not found` | De project-ref in de gebruikersnaam bestaat niet. Een typefout in de ref, of het wachtwoord van een ánder project met de ref van dit project |
| `ON CONFLICT DO UPDATE command cannot affect row a second time` | Dubbele sleutel in de bron. `make db-laad-droog` vangt dit vóór het schrijven en meldt hoeveel |
| Migratie werpt over een gewijzigde checksum | Een al toegepaste migratie is aangepast. Dat doe je niet — schrijf een nieuwe migratie die het verschil maakt |

**De drie authenticatiefouten zijn op 18 augustus 2026 gemeten**, niet beredeneerd, en dat was nodig: deze tabel zei tot die dag dat een authenticatiefout op een kale gebruikersnaam wijst. Dat is onwaar, en het stuurt je precies de verkeerde kant op — je gaat aan de verbindingsstring sleutelen terwijl er niets mee aan de hand is. De meting, met dezelfde string en alleen de gebruikersnaam gevarieerd:

| Gebruikersnaam | Wat Supavisor antwoordt |
|---|---|
| `postgres.<echte-ref>` | `password authentication failed for user "postgres"` |
| `postgres.<verzonnen-ref>` | `ENOTFOUND tenant/user ... not found` |
| `postgres` | `ENOIDENTIFIER no tenant identifier provided` |

Ze zijn dus van elkaar te onderscheiden, en dat is de hele winst: zie je de eerste, dan is het project goed, is de hostnaam goed, is de vorm goed — en klopt alleen het wachtwoord niet. Vraag dan om een nieuw wachtwoord in plaats van te gaan sleutelen.

**Nog één valkuil, en die is gemeen:** libpq percent-decodeert de userinfo van een `postgresql://`-URI. Staat er een `@`, `:`, `/`, `?`, `#` of `%` letterlijk in het wachtwoord, dan komt er iets anders bij de server aan dan wat in `.env` staat — en de foutmelding is dezelfde `password authentication failed`. Encodeer die tekens, of laat Supabase een wachtwoord genereren (die zijn alfanumeriek en hebben het niet nodig).

---

## Wat er daarna vrijkomt

Blok 8 (nachtelijke sync op GitHub Actions), blok 12 (login op Supabase Auth in plaats van de huidige env-gebaseerde toegang), en de online deploy — die kon tot nu toe niet, omdat `platform/contract/` gitignored is en een git-deploy dus zonder data aankwam. Met de database als bron vervalt dat bezwaar: sinds 18 aug schrijft de sync de contractantwoorden naar `contract_antwoord` (migratie 006, `make db-contract`) en leest het platform ze met `CONTRACT_BRON=db` — op Vercel samen met `NEXT_PUBLIC_SUPABASE_URL` en `SUPABASE_SECRET_KEY` (PostgREST; het databasewachtwoord blijft daar weg).
