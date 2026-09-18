# Instructies bij de overname — voor Lien

_Geschreven 19 augustus 2026, bij de transfer van deze repository. Dit is de
doe-lijst; de verantwoording erachter staat in `docs/overdracht.md`. Waar de
twee elkaar tegenspreken, wint `overdracht.md` — daar staan de redenen._

> **Sleutels gaan nooit door een chatbericht of een mail.** Alles hieronder
> verhuist via een wachtwoordbeheerder of een eenmalige link, en anders niet.

---

## 0. Eerst dit: er breekt niets op het moment van de transfer

De nachtelijke synchronisatie **staat nog uit**, en de testworkflow gebruikt
geen enkele sleutel. Direct na de overname draait de CI dus gewoon door en
gebeurt er verder niets. Dat is met opzet: zo is er geen periode waarin de
cijfers stil verouderen omdat een sleutel ontbreekt. Neem de tijd voor stap 1
tot 3, in die volgorde.

Het platform blijft ondertussen online op `https://renard-bakery.vercel.app`.

---

## 1. De vijf GitHub-secrets opnieuw zetten

GitHub-secrets verhuizen niet mee bij een repo-transfer. Ze staan dus leeg —
en de waarden komen **niet** van Kwinten: je maakt ze nieuw aan. Dat is meteen
de sleutelrotatie die bij een oplevering hoort, en ze beëindigt zijn toegang
tot de systemen van de bakkerij.

Repo → **Settings → Secrets and variables → Actions → New repository secret**.

### `SUPABASE_DB_URL`

Deze haal je zelf op; niemand hoeft hem je te bezorgen.

1. Supabase → project *Renard Bakery* → **Project Settings → Database →
   Reset database password**.
2. Bewaar het nieuwe wachtwoord meteen in je wachtwoordbeheerder. Het is
   later **niet meer op te vragen**, alleen opnieuw te resetten.
3. Op dezelfde pagina: **Connection string → tabblad Session pooler**. Neem
   díe string, niet die van "Direct connection" of "Transaction pooler".
4. Controleer vier dingen vóór je plakt:
   - de hostname bevat `pooler`;
   - de poort is **5432** (niet 6543 — de code weigert die bewust);
   - de gebruiker is `postgres.<project-ref>`;
   - er staat `?sslmode=require` achteraan.

### `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY`

Deze vier komen van Idealis Consulting (technisch contact: Antoine Ludovico).
Vraag hem:

- een **nieuwe** API-sleutel — de bestaande hoort bij de oplevering ongeldig
  te worden;
- bij voorkeur meteen een aparte **botgebruiker met alleen leesrechten**, in
  plaats van een persoonlijke account;
- bevestiging of dit de preprod- of de productieomgeving is. **Vandaag draait
  alles op preprod**; de productielicentie staat nog open.

---

## 2. Eén keer met de hand draaien

- Repo → **Actions → nachtelijke-sync → Run workflow**, optie *volledig*.
- Wacht tot die run **groen** is.
- Faalt hij, dan zegt de foutmelding wat er ontbreekt. Er lekt niets: de
  verbindingsstring en de sleutels staan nooit in de logs.

---

## 3. Pas dán de nachtelijke planning aanzetten

- Open `.github/workflows/nachtelijke-sync.yml` en haal het commentaar weg
  voor de drie `schedule:`-regels bovenaan.
- **Niet eerder.** Een planning aanzetten die nog nooit gelukt is, levert
  elke nacht een rode job op waar niemand naar kijkt.
- Onthoud: GitHub schakelt een geplande workflow automatisch uit na 60 dagen
  zonder activiteit in de repo. Loopt de sync ooit stil, kijk daar dan eerst.

---

## 4. Iemand moet de repo volgen

- De faalmelding van de nachtsync is **geen mail maar een GitHub-issue** in
  deze repo, aangemaakt door de laatste stap van de workflow.
- GitHub mailt bij geplande runs alleen wie het workflowbestand het laatst
  bewerkte, en dat blijft Kwinten — ook na de transfer. Te smal om een
  ochtendcontrole op te bouwen.
- Zet daarom minstens één persoon aan jouw kant op **Watch → All Activity**,
  en spreek af wie er 's ochtends kijkt.

---

## 5. Wat er evenmin met deze transfer meekomt

### Het Vercel-project

Het platform draait vandaag in Kwintens persoonlijke Vercel-scope. Dat is
tijdelijk: zijn rol in team `asklien` is `DEVELOPER`, en die mag naar een
bestaand project deployen maar er geen aanmaken.

- Maak in team `asklien` één **leeg** project met de naam `renard-bakery`.
  Verder niets instellen: geen omgevingsvariabelen, geen git-koppeling.
- Daarna verhuist het platform daarheen, en werkt ook de regiokeuze `arn1`
  (Stockholm, naast de database) — dat is een Pro-eigenschap, en het team
  ís Pro.
- Bij die verhuizing horen vijf omgevingsvariabelen die niet vanzelf
  meekomen. Ze staan opgesomd in `docs/overdracht.md` §1.

### Supabase Authentication

`Site URL` en `Redirect URLs` moeten gezet zijn zodra de login op Supabase
Auth overgaat. Dat kan pas als de gebruikerslijst er is — zie punt 6.

---

## 6. Wat er verder bij jou ligt

- **De gebruikerslijst.** Per persoon: naam, e-mailadres en rol (lezer of
  beheerder). Plus: wie wordt de eerste beheerder, en wat is de bewaarregel
  wanneer iemand uit dienst gaat?
- **Het gedeelde testwachtwoord moet vervangen zijn vóór de bakkerij het
  platform ziet.** Iedereen die het ooit gekregen heeft, kan anders bij de
  omzetcijfers.
- **De sluitingsdagen bevestigen** op het scherm *Sluitingsdagen*, met een
  beheerdersaccount. Een kwartiertje, twee klikken per feestdag — en "open"
  is daar net zo waardevol als "dicht". Zonder bevestiging neemt de prognose
  eerlijk aan dat de zaak open is, en dan staat er in december alsnog een
  gewone vrijdagomzet op 25 december.
- **De Deliveroo-rapporten** uit de Partner Hub (Items Sold en Orders, twaalf
  maanden in blokken van negentig dagen). Het venster in de Partner Hub
  schuift dagelijks op: wat eruit valt, is later niet meer op te halen. Dit
  is het enige punt op de hele lijst waar uitstel onherstelbaar is.

---

## 7. Twee dingen om schriftelijk vast te leggen

- **Wat er met de ruwe data gebeurt.** Er staat vandaag 79 MB kassahistoriek
  op Kwintens machine, buiten git. Wissen, of eerst overdragen aan de
  eindklant? Dat is nog nergens vastgelegd. Let op dat het legen geen
  archieffunctie wegneemt: de bakkerij bewaart de bronstukken zelf tien jaar,
  en dit platform is bewust nooit het enige archief.
- **Wie de subverwerker-aankondigingen van Supabase leest.** Dertig dagen
  vooraf, vijf dagen bezwaartermijn, en die mail komt bij jouw organisatie
  binnen. Een termijn van vijf dagen bestaat alleen als iemand de mail ook
  echt opent.

Voor het dossier van de eindklant staat de rest in `docs/overdracht.md` §6:
de Supabase-DPA (versie 1, 1 augustus 2026 — niets te tekenen, wél de versie
te noteren), de verwerkersovereenkomst met de subverwerkers benoemd, en de
regiokeuze met de eerlijke noot dat "EU-regio" hier technisch is en niet
juridisch.

---

## 8. Waar je verder alles vindt

| Vraag | Document |
|---|---|
| Hoe zet ik dit op, van nul? | `docs/setup-supabase.md`, `docs/setup-mac.md` |
| Hoe beheer ik het van dag tot dag? | `docs/beheerdraaiboek.md` |
| Wat is er opgeleverd, en wat niet? | `docs/oplevering.md`, `docs/scope.md` |
| Waarom is iets zo gebouwd? | `docs/beslissingen.md` |
| Wat staat er nog open? | `docs/open-punten.md`, `docs/todo.md` |
| De volledige overdracht, met de redenen | `docs/overdracht.md` |
