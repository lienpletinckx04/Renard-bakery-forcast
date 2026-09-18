# Setup op macOS

Eenmalig, ongeveer twintig minuten.

## 1. Basisgereedschap

```bash
# Homebrew, indien nog niet aanwezig
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install git gh python@3.11 direnv node
```

Node moet minstens 22.6 zijn (de platformtests draaien op
`--experimental-strip-types`); `brew install node` voldoet, CI draait 22.

`direnv` is de sleutel voor de accountscheiding hieronder. Activeer het in je shell:

```bash
# in ~/.zshrc
eval "$(direnv hook zsh)"
```

## 2. Repository

```bash
gh auth login                      # eigen GitHub-account
mkdir -p ~/werk && cd ~/werk
git clone git@github.com:<jouw-account>/asklien-bakkerij.git
cd asklien-bakkerij
```

Per-repo identiteit, zodat commits onder de zakelijke identiteit staan en niet onder je andere profiel:

```bash
git config user.name "Kwinten Van Hoecke"
git config user.email "<zakelijk adres>"
```

## 3. Claude Code

**Bijgesteld 12 aug 2026.** De opdrachtgever heeft een Claude Team, en de uitvoerder heeft daar een eigen stoel in (uitgenodigd op een zakelijk adres; een consumentendomein zoals gmail wordt door Team geweigerd). Het werk aan dit project loopt op die stoel.

Een account hoort bij een organisatie, en het verbruik wordt afgerekend op de organisatie waaronder je werkt. Dat maakt het gescheiden profiel hieronder **noodzakelijk en niet optioneel**: zonder scheiding zou ander werk per ongeluk op de Team-stoel van de opdrachtgever belanden, of dit project op het eigen abonnement.

Gesprekken blijven lokaal bewaard per projectmap, los van welk account ingelogd is. Terugkeren naar een lopend gesprek doe je met `claude --resume`.

**Het gescheiden profiel** regel je met `direnv` en een `.envrc` in de repo (staat in gitignore):

```bash
# .envrc
export CLAUDE_CONFIG_DIR="$HOME/.claude-asklien"
```

```bash
direnv allow && mkdir -p ~/.claude-asklien && claude
```

Log binnen die map één keer in met `/login`, op het zakelijke adres dat in de Team van de opdrachtgever zit. Binnen deze map draait Claude vanaf dan onder die stoel, buiten de map onder je eigen account. Eén keer instellen, daarna nooit meer omschakelen en dus niets om te vergeten.

Werkt inloggen wel maar weigert Claude Code te starten, dan is dat vrijwel zeker het stoeltype aan de kant van de opdrachtgever en niet iets aan jouw kant.

**De stoel is niet van jou.** Loopt de opdracht af, dan vervalt hij. Zorg dat wat telt in de repo staat en niet alleen in gesprekken onder de organisatie van de opdrachtgever.

**Wat wél per repo geldt** is `CLAUDE.md` en `.claude/settings.json`. Die staan er, en regel 1 daarin (geen klantrijen in een modelcontext) is de belangrijkste.

## 4. Python en platform

```bash
make setup
```

Dat maakt een `.venv`, installeert de Python-dependencies én draait
`npm ci` in `platform/` — `make test` dekt beide helften, dus de setup ook.

**Let op de tweede `.env`.** Next leest uitsluitend `platform/.env.local`; de
`.env` in de wortel bereikt de UI niet. Zonder die tweede is alles groen en
komt er tóch niemand binnen, want een lege `PLATFORM_GEBRUIKERS` betekent per
ontwerp "niemand". Het invulrecept staat in `docs/start-hier.md`.

```bash
cp platform/.env.example platform/.env.local
```

Daarna:

```bash
source .venv/bin/activate
make test
```

## 5. Data

```bash
# Exports komen hier, en verlaten deze map nooit
open data/raw
```

`data/` is volledig gitignored. Controleer dat één keer met een testbestand:

```bash
touch data/raw/test.csv && git status --short
# mag NIETS tonen. Toont het wel iets: stop, en fix de gitignore eerst.
rm data/raw/test.csv
```

Doe deze controle. Het duurt tien seconden en het is het enige wat tussen jou en een vervelend gesprek staat.

## 6. Secrets

```bash
cp .env.example .env
# vul in, en zet niets in .env dat niet strikt nodig is
```

Wachtwoorden en sleutels van de opdrachtgever horen in een wachtwoordbeheerder of in de sleutelhanger, niet los in een bestand. `.env` bevat verwijzingen en projectgebonden sleutels, geen hoofdaccounts.

## Werkritme

```bash
# aan het begin van elke werkdag
cd ~/werk/asklien-bakkerij && git pull

# aan het einde van elke werkdag
#  1. docs/dagboek.md invullen
#  2. git status controleren op data-bestanden
#  3. committen en pushen
#  4. dagboek-entry naar de opdrachtgever sturen
```
