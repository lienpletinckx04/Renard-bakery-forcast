# Overdracht

_Geschreven 19 augustus 2026. De repo gaat naar Lien (transfer aangekondigd
19 augustus) en zij deployt zelf. Dit document is de uitvoering van F3 uit
`deliverables.md`: sleutels, `data/`, rotatie en wat er schriftelijk
vastgelegd hoort. Het beschrijft een handeling die precies één keer
plaatsvindt en die niemand kan overdoen als ze fout gaat — een secret dat
niet meeverhuist, merkt niemand, tot de nachtelijke synchronisatie stil
blijft._

> **Sleutels gaan nooit door een chatbericht** (`werkafspraken.md` §2,
> `setup-supabase.md`). Alles hieronder verhuist via een wachtwoordbeheerder
> of een eenmalige link, en anders niet.

> **De doe-lijst staat apart: `docs/instructies-lien.md`.** Dit document
> draagt de redenen en de volledigheid; dat document draagt de handelingen, in
> volgorde, voor wie de repo overneemt. Spreken de twee elkaar tegen, dan wint
> dit document — en dan hoort de instructie bijgewerkt te worden.

## 1. Welke sleutels waar staan, en hoe ze overgaan

| Plaats | Wat er staat | Verhuist mee met de repo-transfer? |
|---|---|---|
| `.env` (repowortel, op Kwintens machine) | `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, `SUPABASE_DB_URL`, `CONTRACT_BRON` | **Nee.** Gitignored, nooit in git geweest |
| `platform/.env.local` (op Kwintens machine) | `PLATFORM_SESSIE_SLEUTEL`, `AUTH_BRON`, `PLATFORM_GEBRUIKERS`, `CONTRACT_BRON`, en dezelfde drie Supabase-variabelen | **Nee.** Idem |
| GitHub Actions-secrets | de vijf uit §2, gezet op 18 augustus | **Nee.** Secrets verhuizen niet mee bij een repo-transfer |
| Vercel-serveromgeving (vandaag Kwintens persoonlijke scope) | `CONTRACT_BRON=db`, `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `PLATFORM_SESSIE_SLEUTEL`, `PLATFORM_GEBRUIKERS` | **Nee.** Die hangen aan het project, zie §3 |
| Supabase-project | de sleutels zelf, in het dashboard | N.v.t. — het project staat sinds 14 augustus al in de organisatie van asklien.ai |

Wat de repo wél meebrengt: `.env.example` en `platform/.env.example`, die per
variabele beschrijven wat hij is, waar hij vandaan komt en waar hij niet mag
staan; en `config/sluitingsdagen.json`, die sinds 19 augustus bewust in git
staat en dus gewoon meeverhuist.

Eén regel verandert daar niet mee: `SUPABASE_DB_URL` — het
databasewachtwoord — staat op GitHub Actions en nergens anders. Niet op
Vercel, want het platform leest het contract via PostgREST met
`SUPABASE_SECRET_KEY` (`stack.md`, "Waar de secrets staan"). Houd dat zo.

## 2. De vijf GitHub-secrets, opnieuw te zetten na de transfer

Settings → Secrets and variables → Actions. Alle vijf verplicht; ontbreekt er
één, dan faalt de run meteen en leesbaar, en er lekt niets — de foutmeldingen
bevatten de verbindingsstring nooit.

| Secret | Waar de waarde vandaan komt |
|---|---|
| `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY` | de Odoo-toegang die op 12 augustus is ingevuld. Technisch contact: Antoine Ludovico, Idealis Consulting. Let op: dit is vandaag de **preprod**-omgeving; de productielicentie is poort G6 en staat nog open |
| `SUPABASE_DB_URL` | Supabase → Project Settings → Database → Connection string → tabblad **Session pooler**. Vier vormeisen (pooler-hostname, poort 5432, gebruiker `postgres.<project-ref>`, `?sslmode=require`) staan in `setup-supabase.md` §3. Het wachtwoord is niet op te vragen, alleen te resetten |

Volgorde na het zetten: eerst één keer *Run workflow* (workflow_dispatch), die
run groen zien, en **pas daarna** de drie `schedule:`-regels in
`.github/workflows/nachtelijke-sync.yml` activeren. Zie ook het draaiboek over
de zestigdagenregel: een planning die aanstaat, kan er ook weer vanzelf uit.

## 3. Het Vercel-project (S14)

Het platform draait vandaag op `https://renard-bakery.vercel.app` in Kwintens
persoonlijke Vercel-scope. Dat is tijdelijk: zijn rol in team `asklien` is
`DEVELOPER` en die mag naar een bestaand project deployen maar er geen
aanmaken (gemeten: 403). Zodra Lien in team `asklien` één **leeg** project
`renard-bakery` aanmaakt, verhuist het daarheen, en dan werkt ook de
regiokeuze `arn1` (Stockholm, naast de database) — dat is een Pro-eigenschap.

Bij die verhuizing horen twee dingen die niet vanzelf meekomen: de vijf
omgevingsvariabelen uit §1, en `Site URL` + `Redirect URLs` in Supabase
Authentication (het restant van S12, pas nodig bij `AUTH_BRON=supabase`).
Zet Deployment Protection bewust: die stond aan en is op 18 augustus
uitgezet zodat de URL deelbaar is; de cijfers zitten achter onze eigen login
en de Supabase-kant is gemeten dicht (`anon` krijgt 401 op alles).

## 4. Wat er met `data/` gebeurt

`data/` is gitignored en is het nooit anders geweest: op 18 augustus zijn de
251 ooit toegevoegde paden in de volledige git-historiek nagelopen, met nul
exports. De map staat vandaag met 79 MB op één machine, die van Kwinten, en
bevat `raw/`, `interim/`, `processed/` en `config/`.

Bij de afsluiting: `.env` en `platform/.env.local` verwijderen, `data/` legen,
en schriftelijk vastleggen wat er met de ruwe data gebeurt. Controle op de
historiek (uit `start-hier.md`):

```bash
git log --all --name-only --pretty=format: | sort -u | grep -E '^(_prive/|\.env$)' && echo "PROBLEEM" || echo "schoon"
```

Twee dingen om niet te vergeten. Het legen van `data/` mag nergens een
archieffunctie wegnemen: de bakkerij bewaart de bronstukken zelf tien jaar
(`wetgevend-kader.md` §2), en het platform is bewust nooit het enige archief.
En in `data/config/` staat nog één handinvoer, `marges.json` (94 bytes, de
v1-vorm met één brutomarge per groep); het echte kostenmodel woont sinds
migratie 009 in de database en verhuist dus mee met het Supabase-project.

**Open: wat er met `data/` gebeurt — wissen, of eerst overdragen aan de
eindklant — is nog nergens vastgelegd. Te beantwoorden door Lien.**

## 5. Welke sleutels geroteerd worden, door wie, en op welke termijn

Werkafspraak §2 is ondubbelzinnig: bij oplevering worden **alle** door de
opdrachtgever verstrekte sleutels geroteerd, en dat wordt actief gemeld. Het
is geen formaliteit — het beëindigt de aansprakelijkheid.

| Sleutel | Handeling | Bij wie |
|---|---|---|
| `ODOO_API_KEY` | nieuwe sleutel, en bij voorkeur meteen een botgebruiker met alleen leesrechten (staat nog open in `todo.md`) | via Idealis |
| databasewachtwoord (`SUPABASE_DB_URL`) | Project Settings → Database → Reset database password, daarna het GitHub-secret bijwerken | Lien |
| `SUPABASE_SECRET_KEY` | nieuwe secret key in het dashboard, daarna de Vercel-omgeving bijwerken | Lien |
| `PLATFORM_SESSIE_SLEUTEL` | nieuwe waarde genereren (32 willekeurige bytes, base64url). Wisselen maakt alle lopende sessies ongeldig — dat is meteen de noodrem | wie het platform beheert |
| het gedeelde testwachtwoord | **moet vervangen zijn vóór de eindklant het platform ziet** (`stand-van-zaken.md` §1) | wie de eerste beheerder wordt (S13) |

De workflow noemt voor `ODOO_API_KEY` een rotatieplan van maximaal 90 dagen.
Dat plan bestaat vandaag als voornemen en niet als afspraak.

**Open: wie voert elke rotatie uit en op welke datum, en wie bewaakt daarna
de 90-dagentermijn op de Odoo-sleutel? Te beantwoorden door Lien, voor de
Odoo-kant samen met Idealis.**

## 6. Wat er in het dossier van de eindklant hoort

- **De Supabase-DPA v1, van kracht 1 augustus 2026.** Er valt niets te
  tekenen — aanvaarding gaat automatisch bij gebruik, en Liens organisatie
  heeft hem dus al aanvaard door het project op 14 augustus aan te maken —
  maar er valt wél iets vast te leggen: de verwijzing naar versie 1
  (1 aug 2026) mét de aanmaakdatum van het project. Een verwerkersovereenkomst
  waarvan niemand de versie noteerde, is bij een controle net zo goed als geen.
- **De verwerkersovereenkomst bakkerij↔asklien.ai** (art. 28 AVG), met de
  subverwerkers benoemd: Supabase, en wij zolang wij productietoegang hebben.
  Daarin ook de datalekketen (72 uur naar de GBA door de verantwoordelijke,
  "zonder onredelijke vertraging" door de verwerker) en de exitregeling —
  vraag 41, nog open, en S10 in `todo.md`.
- **De keuze van de regio:** `eu-north-1` (Stockholm), gekozen 14 augustus,
  een EU-lidstaat. Met de eerlijke noot erbij dat EU-regio hier technisch is
  en niet juridisch: Supabase, AWS en Vercel blijven Amerikaanse entiteiten.
- **De gebruikersaccounts zijn de enige persoonsgegevens in het systeem**,
  met de bewaarregel bij uitdiensttreding (vraag 57b, onderdeel van S13).
- Nog niet gebouwd en hier vermeld omdat het dossier het nodig heeft: het
  aanmeldingslogboek (C4 in `deliverables.md`, open).

## 7. Wie welke terugkerende post leest

- **Supabase' subverwerker-aankondigingen: 30 dagen vooraf, 5 dagen
  bezwaartermijn.** Die mail komt binnen bij het account van Liens
  organisatie, niet bij ons. Een termijn van vijf dagen bestaat alleen als
  iemand de mail ook echt leest. **Open: wie is dat? Te beantwoorden door
  Lien** (staat ook als infrastructuurpunt in `todo.md`).
- **De faalmelding van de nachtelijke sync is geen mail maar een
  GitHub-issue** in deze repo, aangemaakt door de laatste stap van de
  workflow. Dat is bewust: GitHub mailt bij geplande runs alleen wie het
  workflowbestand het laatst wijzigde, en dat is na de transfer nog steeds
  Kwinten — te smal om een ochtendcontrole op te bouwen. **Open: wie volgt
  de repo (watch) en leest die issues na de overdracht? Te beantwoorden door
  Lien.**
- **De facturatie** van Supabase Pro en Vercel Pro loopt bij asklien.ai en
  wordt verrekend via het onderhoudsabonnement aan de eindklant
  (`scope.md`, "Waar de database hangt"). Orde van grootte: € 42 tot € 65 per
  maand (`stack.md`).
- **Afschrijvingen van GitHub-actieruntimes.** Op 19 augustus draaiden drie
  acties nog op de afgeschreven node20-runtime, waaronder juist de stap die
  bij een gefaalde nacht de melding aanmaakt. Er is vandaag niemand
  aangewezen die zulke aankondigingen opvangt. **Open, te beantwoorden door
  Lien.**

## 8. Wat er misgaat als dit niet gebeurt

- **Secrets niet opnieuw gezet (§2).** Staat de planning uit, dan gebeurt er
  niets en verouderen de cijfers stil tot de dodemansknop het meldt. Staat ze
  aan, dan is het elke nacht een rode run plus een nieuw issue.
- **Vercel-project niet verhuisd (§3).** De productie-URL van de eindklant
  blijft hangen in de persoonlijke Hobby-scope van iemand die na de oplevering
  geen partij meer is. Verdwijnt dat account, dan verdwijnt het platform, en
  de regio blijft weg van de database.
- **`data/` niet geleegd en niets vastgelegd (§4).** 79 MB kassahistoriek van
  de eindklant blijft staan op een machine die niet van de klant is, zonder
  afspraak. Dat is precies wat harde regel 2 en werkafspraak §3 moeten
  voorkomen.
- **Sleutels niet geroteerd (§5).** Kwinten houdt na de eindbetaling
  leestoegang op Odoo en schrijftoegang op de database van de klant. Dat is
  geen vertrouwenskwestie maar een aansprakelijkheidskwestie.
- **Het gedeelde testwachtwoord blijft staan (§5).** Iedereen die het ooit
  gekregen heeft, kan bij de omzetcijfers van de bakkerij.
- **DPA-versie niet genoteerd (§6).** Bij een controle staat de eindklant met
  lege handen, terwijl er wel degelijk een geldige overeenkomst was.
- **Niemand leest de subverwerker-mail (§7).** De bezwaartermijn van vijf
  dagen verloopt ongebruikt en een nieuwe subverwerker komt er stil bij,
  zonder dat de verwerkingsverantwoordelijke het weet.
- **Niemand volgt de repo (§7).** De faalmelding komt aan bij niemand, en de
  eerste die het merkt is een CFO die naar cijfers van vorige week kijkt.
