# Stack en bouwregels

_Vastgelegd 12 augustus 2026, op basis van geverifieerde versies van die dag. Wie hier iets wijzigt, noteert waarom in `beslissingen.md`._

## Versies, exact te pinnen

| Pakket | Versie | Waarom deze |
|---|---|---|
| `next` | **16.3.0** | App Router. Pages Router krijgt geen nieuwe functies meer |
| `react` / `react-dom` | 19.x | volgt Next 16 |
| `psycopg` | 3.3.x | voor de ETL |

**Er is bewust géén Supabase-SDK** (`@supabase/supabase-js`, `@supabase/ssr`): `platform/lib/auth-supabase.ts` praat met kale fetch tegen de auth-endpoints, en de contractleesroute gebruikt PostgREST eveneens via fetch. De motivering staat in dat bestand zelf. Eerdere versies van dit document pinden hier beide pakketten; die pins zijn vervallen met de SDK.

## Vier dingen die anders zijn dan de meeste handleidingen zeggen

**1. `middleware.ts` heet nu `proxy.ts`.** Sinds Next 16 is de oude naam afgeschaft en draait het bestand op de Node-runtime. Bestaande tutorials kloppen niet meer. Migreren kan met `npx @next/codemod@canary middleware-to-proxy .`

**2. De Supabase-sleutels heten anders.** `anon` en `service_role` worden vervangen door `sb_publishable_…` en `sb_secret_…`. Nieuwe projecten krijgen de oude niet meer. Bouw meteen op de nieuwe namen.

**3. Het gangbare `getSession()`/`getClaims()`-advies is hier niet van toepassing — er ís geen Supabase-sessie.** De handleidingen waarschuwen terecht dat `getSession()` in servercode het token niet valideert en dat je `getClaims()` moet gebruiken; dat gaat over apps die de Supabase-sessie zelf dragen. Dit platform doet dat niet: `platform/lib/auth-supabase.ts` toetst e-mail en wachtwoord met één kale fetch tegen de token-endpoint (`grant_type=password`), **gooit het teruggegeven access token weg** en tekent daarna een eigen sessiecookie (`PLATFORM_SESSIE_SLEUTEL`), die bij elk verzoek getoetst wordt. Er wordt dus nergens een Supabase-JWT gelezen of geverifieerd. _(Herschreven 18 aug; de eerdere tekst hier adviseerde `getClaims()` plus ES256 en sprak het eigen "geen SDK"-punt hierboven tegen. Gevolg voor S12: zie `setup-supabase.md` §4.)_

**4. De proxy is geen beveiliging.** Server Functions gaan niet als aparte route door de matcher. De echte grens is RLS in de database. Een knop verbergen in React is geen autorisatie.

## Rollen

Twee rollen, in de code `beheerder` en `lezer` (de rol-string heette tot 18 aug "bekijker"; code en docs zijn die dag gelijkgetrokken met scope D6 en vraag 57), en de rol komt **strikt uit `app_metadata.rol`** (beslissing 17 aug, zie `beslissingen.md` en `beheerdraaiboek.md`). `app_metadata` is alleen door een Administrator te zetten en nooit door de gebruiker zelf; zonder geldige rol komt er géén sessie — geen terugval op `lezer`, want dat zou een configuratiefout verzwijgen als geldige toegang. De sessie zelf blijft de onze: een eigen ondertekende cookie, bij elk verzoek getoetst.

**Verworpen alternatief:** een `user_roles`-tabel in Postgres plus een Custom Access Token Hook en een `is_admin()`-helper in RLS. Verworpen om de eenvoud: bij een handvol benoemde gebruikers is `app_metadata` dezelfde waarheid zonder extra tabel en hook om te beheren.

Zelfregistratie staat **uit** (S12). Gebruikers komen binnen via een uitnodiging, met de rol meteen in `app_metadata` (S13).

## RLS

Het patroon voor dit platform: iedereen die ingelogd is mag alles lezen, niemand mag schrijven, de ETL schrijft met de secret key en omzeilt RLS.

```sql
alter table public.fact_verkoop enable row level security;
alter table public.fact_verkoop force row level security;

create policy "authenticated leest" on public.fact_verkoop
for select to authenticated using ( true );

-- bewust GEEN insert/update/delete-policies
revoke all on public.fact_verkoop from anon;
grant select on public.fact_verkoop to authenticated;
```

Drie details die er echt toe doen:

- **`to authenticated` altijd expliciet.** Zonder `TO` wordt de policy ook voor anonieme bezoekers geëvalueerd
- **Functieaanroepen in een subquery wikkelen**: `using ( (select mijn_check()) )`, niet `using ( mijn_check() )`. Postgres cachet dan per statement in plaats van per rij. (Geldt voor elke helper; de eerder overwogen `is_admin()` is met de user_roles-route verworpen, zie "Rollen")
- **Na elke migratie de Supabase-linter draaien.** Die vlagt tabellen zonder RLS en policies zonder `TO`

## De ETL naar de database

**Rechtstreekse Postgres-verbinding via de gedeelde pooler in session mode. Niet via de REST-API.**

```
aws-<n>-<regio>.pooler.supabase.com:5432   <- regio = die van het project
gebruiker: postgres.<project-ref>        <- niet 'postgres'
sslmode=require
```

Waarom dit en niets anders:

- **`db.<ref>.supabase.co` is IPv6-only.** GitHub Actions-runners hebben onbetrouwbare IPv6-uitgang. Dat geeft `network is unreachable`, en dat is de valkuil waar dit ontwerp anders op stukloopt. De pooler-hostname is altijd IPv4
- **Session mode (5432), niet transaction mode (6543).** Transaction mode kent geen prepared statements, wat botst met psycopg3 en met `COPY`
- **Niet via PostgREST.** Geen `COPY`, geen transacties over meerdere statements, en tienduizenden rijen worden een chunking-probleem

**Schrijfpatroon:** `COPY` naar een tijdelijke tabel, dan één `insert … on conflict` binnen dezelfde transactie. Alles of niets. Met een expliciete `statement_timeout` per sessie.

Verbinding laat openen en snel sluiten: doe het pdf-parsen en het rekenwerk vóór je de database aanspreekt, niet terwijl de verbinding openstaat — de pooler knipt inactieve verbindingen.

## Waar de secrets staan

| | GitHub Actions | Vercel server | Browser |
|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | – | ✅ | ✅ mag publiek |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | – | ✅ | ✅ mag publiek |
| `SUPABASE_SECRET_KEY` | alleen indien nodig | ✅ zodra `CONTRACT_BRON=db` (zie hieronder) | ❌ **nooit** |
| `CONTRACT_BRON` | – | `db` zodra het contract uit Postgres komt | – |
| `SUPABASE_DB_URL` (met wachtwoord) | ✅ | ❌ | ❌ |
| Odoo-url, gebruiker, sleutel | ✅ | ❌ | ❌ |

**Elke variabele met `NEXT_PUBLIC_` wordt in de JavaScript-bundel gebakken.** Er bestaat geen server-only variant daarvan. Eén typefout lekt de sleutel permanent, ook in de build-artefacten en de deploy-geschiedenis.

In dit ontwerp schrijft alleen de ETL. Sinds 18 augustus 2026 heeft Vercel wél één leestaak voor de secret key: met `CONTRACT_BRON=db` haalt het platform de contractantwoorden uit `contract_antwoord` via PostgREST (`platform/lib/contract-bron.ts`). Dat is bewust PostgREST en niet een rechtstreekse Postgres-verbinding: zo blijft `SUPABASE_DB_URL` — het databasewachtwoord — weg van Vercel, precies zoals deze tabel altijd zei. De bezwaren tegen PostgREST hierboven gaan over de ETL die tienduizenden rijen schrijft; hier wordt één voorgeaggregeerde rij per scherm gelezen. Zonder de vlag is de sleutel op Vercel nergens voor nodig en zetten we hem daar ook niet.

## Kosten

Ruwe orde van grootte: **€ 42 tot € 65 per maand.** Supabase Pro $25 (Free pauzeert bij inactiviteit en heeft geen dagelijkse back-ups, dus geen optie), compute $0–15, Vercel Pro $20 per zetel, GitHub Actions gratis binnen de limieten.

Twee dingen die dit laten ontsporen:

- **Miljoenen ruwe brondata-rijen in Postgres zetten.** Boven 8 GB komt er opslagkost bij én zwaardere compute. De ruwe bonregels blijven lokaal; alleen aggregaten gaan naar de database
- **Meerdere betaalde projecten** voor dev, staging en productie. Eén betaald project plus een gratis project voor ontwikkeling

## Twee risico's om nu te benoemen

**De nachtelijke run is de zwakste schakel.** De planner van GitHub Actions is *best effort*: hij kan tientallen minuten later vuren bij drukte. Voor een dagelijks CFO-overzicht is dat aanvaardbaar, maar als de klant "elke ochtend om zeven uur ververst" als harde eis stelt, moet daar een externe planner voor komen. Los daarvan hoort er hoe dan ook een dodemansknop in: de ETL schrijft haar eindtijd weg, en het platform toont die datum. Een dashboard zonder datum is een dashboard dat je niet kan vertrouwen.

**EU-regio is technisch, niet juridisch.** Compute en database in de EU — het project draait sinds 14 augustus 2026 in `eu-north-1` (Stockholm) — verandert niets aan het feit dat Vercel en AWS Amerikaanse entiteiten zijn. Als de eindklant "EU" juridisch bedoelt en niet alleen technisch, is dat een gesprek dat vóór de bouw gevoerd moet worden en niet erna.

## Wat snel verandert

- De Supabase-SDK wordt niet gebruikt (zie "Versies"); komt hij ooit alsnog in beeld, weeg dan opnieuw — `@supabase/ssr` staat pre-1.0 en `supabase-js` v3 komt eraan met breekpunten
- De uitfasering van de oude sleutels is al eens opgeschoven. Changelog checken vóór productie
- `middleware.ts` werkt nu nog naast `proxy.ts`, maar verdwijnt vermoedelijk in Next 17
