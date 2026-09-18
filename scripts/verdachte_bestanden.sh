#!/usr/bin/env bash
# Welke bestanden in de werkboom eruitzien als klantdata die de repo in wil.
#
# EEN BRON, TWEE LEZERS. Deze lijst stond tot 18 aug 2026 twee keer met de
# hand: in `make check-data` en in .claude/hooks/geen-klantdata.sh. Die twee
# waren al uiteengelopen -- de hook miste `html`, `tsv`, `ics` en `xlsm`
# terwijl de .gitignore ze alle vier als klantdata noemt, en
# reports/voortgang-voor-lien.html is 798 KB klantcijfers. Een vangrail die
# zichzelf tegenspreekt, is een vangrail waarvan je niet weet wat hij dekt.
#
# Print één verdacht pad per regel op stdout, en niets als het schoon is.
# Eindigt altijd met status 0: de aanroepers bepalen wat een treffer betekent
# (de Makefile faalt, de hook weigert de commit).
#
# UITZONDERINGEN, elk met de reden -- wie hier iets bij zet, zet een stuk
# vangrail uit:
#   package.json / package-lock.json / tsconfig  projectconfiguratie
#   .claude/                                     harnasconfiguratie
#   db/migraties/*.sql                           de migraties ZIJN de repo
#   bakkerij/features/schoolvakanties.json       publieke overheidsdata
#   config/sluitingsdagen.json                   de dagen dat de zaak dicht is
#   tests/fixtures/*.csv|*.ics                   vrijgegeven, geanonimiseerd
#   platform/vercel.json                         deploy-configuratie, geen data
#   platform/public/brand/*.png|*.jpg            merkassets, geen klantdata
#
# WAT ER OP 19 AUG 2026 BIJ IS GEKOMEN, en waarom het een echt gat was. De
# lijst eindigde op `$` en kende alleen kale extensies, dus `omzet.json.gz`
# eindigde op "gz" en glipte erdoor. Erger: `png` stond er helemaal niet in,
# terwijl `make steekproef` élk scherm in beide talen als PNG wegschrijft --
# dat zijn schermafbeeldingen vol klantcijfers. Allebei staan ze wél in
# .gitignore onder "Output die klantcijfers kan bevatten", dus één `git add -f`
# passeerde beide vangrails terwijl .gitignore ze juist tegenhield. Toegevoegd:
# gz, jsonl, png, jpg/jpeg, pkl en feather. De merkassets in
# platform/public/brand/ zijn de uitzondering, precies zoals in .gitignore:
# zonder hen mist een verse checkout het inlogscherm.
#
# Over die sluitingsdagen, want het is de enige uitzondering die op 19 aug 2026
# is toegevoegd en de enige die uitleg vraagt. Ze stond in data/config/ en dus
# buiten git, en daardoor kon de nachtelijke synchronisatie op een runner nooit
# slagen: zonder die lijst verdwijnt `gepland_dicht` uit de kalender en meldt
# het platform een geplande sluiting als ACHTERSTAND. Het bestand bevat geen
# klantdata -- geen transacties, geen personen, geen bedragen -- alleen datums
# en een zakelijke reden. Het `reden`-veld is wél vrije tekst, en dat staat als
# waarschuwing in het bestand zelf: geen namen, geen persoonlijke
# omstandigheden. Wie daar toch iets persoonlijks in zet, zet het in de
# git-geschiedenis, voorgoed.
set -uo pipefail

wortel="${1:-.}"
cd "$wortel" || exit 0

git status --porcelain 2>/dev/null \
  | grep -E '^.?[AMRC?]' \
  | sed 's/^...//' \
  | grep -Ei '\.(csv|tsv|xlsx?|xls|xlsm|parquet|feather|pkl|pdf|zip|gz|sqlite|db|dump|sql|jsonl?|html?|ics|png|jpe?g)$' \
  | grep -vE '(^|/)(package(-lock)?\.json|tsconfig[^/]*\.json)$' \
  | grep -vE '^\.claude/' \
  | grep -vE '^db/migraties/[^/]+\.sql$' \
  | grep -vE '^bakkerij/features/schoolvakanties\.json$' \
  | grep -vE '^config/sluitingsdagen\.json$' \
  | grep -vE '^tests/fixtures/[^/]+\.(csv|ics)$' \
  | grep -vE '^platform/vercel\.json$' \
  | grep -vE '^platform/public/brand/[^/]+\.(png|jpe?g)$'

exit 0
