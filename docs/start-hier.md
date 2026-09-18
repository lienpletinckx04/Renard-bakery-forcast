# Start hier

_Geschreven 7 augustus 2026, aan het einde van de opzetdag; leesroute bijgewerkt 18 augustus 2026. Voor wie dit project na een onderbreking oppakt — de eerstvolgende werkdag of eind augustus, en ook als dat jezelf is._

## Waar alles staat

| | |
|---|---|
| Repo | `github.com/liveatwembley/asklien-bakkerij`, **privé** |
| Werkkopie | lokaal op de Mac — dat is de werkmachine. Het pad is vrij te kiezen; de repo is de waarheid, niet de map. |
| Data | `data/raw/`, gitignored, verlaat die map niet |
| Sleutels | `.env` lokaal, mastercopy in de wachtwoordmanager |
| Commerciële context | buiten deze repo bewaard, zie waarschuwing onderaan |

## Eerste keer opzetten op de Mac

Dit is het ene kloonrecept (het `git clone`-voorbeeld in `setup-mac.md` is de oudere vorm; dit recept wint):

```bash
gh repo clone liveatwembley/asklien-bakkerij
cd asklien-bakkerij

cp .env.example .env        # Odoo-sleutel uit de wachtwoordmanager
make setup                  # venv + dependencies
make odoo-audit             # verifieert de verbinding, kost niets
make extract                # verkoophistoriek naar data/raw
make test
make help                   # alle doelen, met uitleg
```

Vóór je iets commit: `make controle`. Dat draait alles wat CI ook draait —
de klantdata-check, lint, beide testsuites, de typecheck en de productiebouw.

**En dan het platform, want daar zit een tweede `.env`.** Next leest alleen
`platform/.env.local`; de `.env` in de wortel bereikt de UI niet. Sla je dit
over, dan is alles groen en komt er tóch niemand binnen — `PLATFORM_GEBRUIKERS`
is dan leeg, en leeg betekent per ontwerp "niemand". Dat is geen storing maar
het bedoelde gedrag, en precies daarom is het zo verwarrend.

```bash
cp platform/.env.example platform/.env.local
node -e "console.log(require('node:crypto').randomBytes(32).toString('base64url'))"
#   -> in PLATFORM_SESSIE_SLEUTEL

node scripts/maak_gebruiker.mjs <naam> beheerder   # wachtwoord via stdin
#   -> de uitvoerregel in PLATFORM_GEBRUIKERS
```

Controleer daarna één keer, het duurt tien seconden:

```bash
make check-data             # moet "Schoon" zeggen
```

## Waarom op de Mac en niet in een codespace

De volledige verkoophistoriek van een klant op gehoste containerinfrastructuur zetten is verdedigbaar maar onnodig, want de bron is één API-call ver. Een codespace kan bovendien verdwijnen of herbouwd worden. De Mac is de werkmachine, en `data/` blijft daar.

## De data hoeft nooit verplaatst te worden

Niet kopiëren tussen machines. Niet via Drive, niet via USB, niet via mail. **Opnieuw ophalen uit de bron**, met `make extract`. Dat is één commando, het duurt een paar minuten, en het levert exact hetzelfde op. Elke kopie die je maakt, is een kopie die je later moet opruimen en waarvan je moet kunnen aantonen dat je ze opgeruimd hebt.

## Waarom de data niet gestript hoeft te worden

`scripts/odoo_extract.py` **vraagt de persoonsvelden nooit op.** Geen `partner_id`, geen `customer_note`, geen naam of adres. Wat eruit komt is:

```
datum | filiaal_id | product_id | product_naam | kanaal | aantal | omzet_excl_btw
```

Dat is het verschil tussen ophalen-en-schoonmaken en nooit-ophalen. Wie achteraf filtert, heeft een AVG-vraag die goed beantwoord is en die iemand later kan betwisten. Wie nooit ophaalt, heeft geen AVG-vraag. Geaggregeerde productverkoop per dag per kassa is geen persoonsgegeven, dus artikel 7 en de AVG spelen hier niet.

**Vertrouwelijk is het wél.** De omzetcijfers zijn bedrijfsgeheim van de eindklant. Vandaar: `data/` gitignored, nooit naar een clouddrive of gedeelde map, en bij oplevering schriftelijk vastleggen of het verwijderd of overgedragen wordt. Die bevestiging hoort in `docs/beslissingen.md`.

## Claude Code

Dit project draait op een eigen stoel in de Claude Team van de opdrachtgever. Verbruik wordt afgerekend op de organisatie waaronder je werkt, dus het direnv-profiel uit `docs/setup-mac.md` sectie 3 is verplicht en niet optioneel: binnen deze map de stoel van de opdrachtgever, daarbuiten je eigen account.

`.claude/settings.json` weigert lezen in `data/` en `.env`, zodat regel 1 uit `CLAUDE.md` afgedwongen is en niet alleen opgeschreven staat.

## Leesvolgorde voor wie hier binnenkomt

_(Herschreven 18 augustus; de oude lijst hieronder verwees naar de audit van 7 augustus en naar vragen die intussen gesloten zijn. Dit is de ene leesroute — andere documenten verwijzen hierheen in plaats van een eigen lijst te dragen.)_

1. Dit document — waar alles staat en hoe de machine opgezet wordt
2. `docs/volgende-sessie.md` — wat de vorige sessie klaarlegde voor de volgende
3. `docs/todo.md` — **de ene blokkadelijst** (S-nummers, met eigenaars) en de reststand per blok
4. `docs/scope.md` — waar de grens van fase 1 ligt
5. `CLAUDE.md` — de acht harde regels en de werkvolgorde

Achtergrond wie dieper wil: `docs/stand-van-zaken.md` (overdracht), `docs/beslissingen.md` (waarom iets is zoals het is), `docs/data-audit.md` (de gemeten fundering van 7/12 aug).

## De drie dingen die het werk sturen

Kort samengevat, uitgewerkt in `docs/data-audit.md`:

**De verkoopdata draagt het model.** Negentien volle maanden op bonregelniveau, 1,56 miljoen regels, 331 producten mét verkoop sinds jan 2025 (de catalogus telt er 425), actueel, volledige jaarcyclus met overlap. De baselines kunnen meteen draaien.

**Drie dingen staan niet in Odoo:** geen filiaaldimensie, geen kanaal (Deliveroo en TGTG bestaan er niet), en kostprijzen op één procent van de catalogus. Dat is geen tegenslag maar het bewijs dat dit project geen duplicaat is van de bestaande Odoo-rapportering.

**De vraag is niet gemeten, alleen de verkoop.** Nul productieorders, nul afvalregistratie. Het model voorspelt verkoop, niet vraag, en dat hoort in elke uitspraak die eruit komt.

## Waarschuwing bij het opruimen

**Bijgesteld 12 aug 2026.** `_prive/` is uit deze repo weggehaald en staat nu volledig buiten het project, in een aparte werkmap die niet met deze repo meeverhuist. Reden: de repo gaat volgens artikel 6 na betaling over naar de opdrachtgever, en commerciële notities horen niet in iets dat overgedragen wordt. Ze eruit halen is sluitender dan ze erin houden achter een gitignore-regel en erop vertrouwen dat niemand `git add -A` typt.

Gevolg voor deze repo: er staat niets meer in dat niet mee mag. Wat hierboven "vóór oplevering verwijderen" was, is nu gewoon afwezig.

Bij oplevering blijft over: `.env` verwijderen, de Odoo-sleutel laten roteren door Idealis, en controleren dat `data/` leeg is. Controlecommando op de historiek:

```bash
git log --all --name-only --pretty=format: | sort -u | grep -E '^(_prive/|\.env$)' && echo "PROBLEEM" || echo "schoon"
```
