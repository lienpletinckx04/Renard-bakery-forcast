-- 013 | De waardenchecks van 007 verruimd voor de sluitingskalender.
--
-- Migratie 007 legt vast welke schermen en welke etl-bronnen bestaan, en dat
-- is precies waarom deze migratie nodig is: het scherm `sluitingsdagen`
-- (contractbouw, 19 aug 2026) en de laadbron `sluitingen` (make
-- db-sluitingen) bestonden toen nog niet. Zonder deze verruiming weigert de
-- database het nieuwe contractantwoord — gemeten op 19 aug 2026, bij de
-- eerste `make db-contract` na de bouw van de sluitingskalender: de check
-- brak de transactie en het oude contract bleef staan, precies zoals
-- bedoeld. Dit bestand is de deur die daarna open moet.
--
-- MEE GEREPAREERD: de bron `kostenmodel` ontbrak óók in etl_run_bron_bekend.
-- `make db-kostenmodel` (scripts/kostenmodel_laad.py, start_run met bron
-- "kostenmodel") zou vandaag op dezelfde check stranden; dat is nooit
-- opgevallen omdat dat script vóór 007 voor het laatst gedraaid heeft. Een
-- wacht die het eerstvolgende herstelgereedschap blokkeert, is zelf de fout.
--
-- Een nieuwe migratie en geen wijziging aan 007: toegepaste migraties zijn
-- onveranderlijk (de checksum-vangrail in bakkerij/db/migratie.py). Zelfde
-- naam, drop-vooraf: dit bestand is op zichzelf herhaalbaar.

alter table public.contract_antwoord
    drop constraint if exists contract_antwoord_scherm_bekend;
alter table public.contract_antwoord
    add constraint contract_antwoord_scherm_bekend check (scherm in
        ('overzicht', 'kanalen', 'producten', 'marge', 'prognose', 'stand',
         'sluitingsdagen', 'winkels'));

alter table public.etl_run
    drop constraint if exists etl_run_bron_bekend;
alter table public.etl_run
    add constraint etl_run_bron_bekend check (bron in
        ('nachtelijke-sync', 'canoniek', 'contract', 'kostenmodel',
         'sluitingen'));
