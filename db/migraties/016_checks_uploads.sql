-- 016 | De bron `uploads` toelaten in etl_run, zodat het leegmaken van de
--       postbus zichzelf kan boekhouden.
--
-- WAAROM DEZE MIGRATIE BESTAAT
--
-- Migratie 015 zette een postbus neer (`bron_upload`): het platform legt er
-- een opgeladen bronbestand in, en de Python-inlaadlaag haalt het er weer uit.
-- Dat leeghalen is een ETL-stap zoals de andere, en elke ETL-stap schrijft een
-- rij in `etl_run` — gestart, geëindigd, goed of fout. Zonder die rij is een
-- gestorven run niet te onderscheiden van een run die nooit gestart is, en dat
-- is precies het onderscheid waarvoor `etl_run` bestaat (zie 003).
--
-- `etl_run.bron` draagt sinds 007 een check met de toegestane bronnen, en
-- 013 heeft die al eens moeten verruimen. De aanleiding daar is het lezen
-- waard, want ze herhaalt zich hier: `kostenmodel` ontbrak in de lijst, en dat
-- was niemand opgevallen omdat het bijbehorende script sinds 007 niet meer
-- gedraaid had. Een nieuwe bron die niet in de check staat, laat `start_run`
-- de transactie afbreken op het moment dat iemand hem voor het eerst nodig
-- heeft — meestal precies wanneer het uitkomt.
--
-- `scripts/uploads_verwerk.py` opent zijn run met bron `uploads`. Zonder deze
-- migratie strandt dat script op zijn eerste regel.
--
-- WAAROM `uploads` EN NIET `deliveroo`
--
-- De waarden in deze kolom benoemen een STAP en niet een leverancier:
-- `canoniek`, `contract`, `kostenmodel`, `sluitingen`. De postbus is bewust
-- niet Deliveroo-specifiek — ze draagt een kolom `bron` die later een tweede
-- platform kan dragen — en de stap die haar leegmaakt is dat evenmin. Wie hier
-- `deliveroo` zou zetten, zou bij het tweede platform een tweede stapnaam
-- moeten verzinnen voor hetzelfde werk.
--
-- WAT ER BEWUST NIET IN ZIT
--
-- Geen wijziging aan 007 of 013. Toegepaste migraties zijn onveranderlijk (de
-- checksum-vangrail in `bakkerij/db/migratie.py`), dus een lijst die groeit
-- hoort per definitie in een nieuw bestand. Zelfde naam, drop vooraf: dit
-- bestand is op zichzelf herhaalbaar.
--
-- Geen nieuw scherm, en dus geen aanpassing aan `contract_antwoord_scherm_bekend`.
-- Het uploadscherm leest zijn lijst rechtstreeks uit `bron_upload` en niet uit
-- het contract, want die lijst is beheerinvoer en geen berekend cijfer.

alter table public.etl_run
    drop constraint if exists etl_run_bron_bekend;
alter table public.etl_run
    add constraint etl_run_bron_bekend check (bron in
        ('nachtelijke-sync', 'canoniek', 'contract', 'kostenmodel',
         'sluitingen', 'uploads'));
