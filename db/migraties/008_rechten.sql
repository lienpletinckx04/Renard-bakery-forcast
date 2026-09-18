-- 008 | De rechten van service_role expliciet maken.
--
-- WAAROM DEZE MIGRATIE BESTAAT
--
-- Het platform leest het contract met SUPABASE_SECRET_KEY (zie
-- platform/lib/contract-bron.ts), en die sleutel komt bij PostgREST binnen als
-- de rol `service_role`. Die rol draagt BYPASSRLS, dus row level security
-- houdt hem niet tegen — maar BYPASSRLS zegt niets over TABELRECHTEN, en tot
-- deze migratie gaf geen enkele migratie `service_role` een grant.
--
-- Op Supabase werkte dat toch, omdat het project default privileges op schema
-- public heeft staan die elke nieuwe tabel automatisch aan service_role
-- toekennen. Dat is een eigenschap van de omgeving en niet van deze repo: ze
-- staat in geen enkel bestand, ze is niet herbouwbaar uit de migraties, en ze
-- kan door Supabase gewijzigd worden zonder dat hier iets verandert.
--
-- Gemeten op 18 aug 2026 tegen een kale Postgres 17 met dezelfde drie rollen:
-- de zeven migraties draaien schoon, maar `set role service_role; select ...`
-- geeft `permission denied for table contract_antwoord`. Op de bestandsroute
-- valt dat niet op; onder CONTRACT_BRON=db is het elk scherm van het platform,
-- als een 500 en niet als een leesbare melding.
--
-- Deze migratie maakt de aanname een feit. Ze is idempotent en op Supabase een
-- no-op als de default privileges hun werk al deden.
--
-- SELECT EN NIETS MEER
--
-- De ETL schrijft over de Postgres-verbinding als eigenaar, niet via
-- PostgREST. `service_role` hoeft dus alleen te lezen, en krijgt hier
-- uitsluitend select. Wie er ooit schrijfrechten aan toevoegt, moet zich eerst
-- afvragen waarom de schrijfroute niet meer volstaat.

grant select on public.dim_kalender       to service_role;
grant select on public.dim_product        to service_role;
grant select on public.fact_verkoop       to service_role;
grant select on public.fact_bonnen        to service_role;
grant select on public.fact_product_uren  to service_role;
grant select on public.fact_kanaalkost    to service_role;
grant select on public.etl_run            to service_role;
-- `marge_instelling` staat hier bewust NIET bij: migratie 004 maakte die tabel
-- en 005 dropt hem weer (het kostenmodel verving hem). Een grant erop laat
-- deze migratie vallen met `relation does not exist` — gemeten op 18 aug 2026.
grant select on public.kosten_criterium   to service_role;
grant select on public.kosten_waarde      to service_role;
grant select on public.winkel             to service_role;
grant select on public.winkel_filiaal     to service_role;
grant select on public.contract_antwoord  to service_role;
