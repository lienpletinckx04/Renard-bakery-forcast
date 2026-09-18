-- 006 | Het contract in de database: de gebouwde antwoorden, per scherm en taal.
--
-- Tot deze migratie leefde het contract alleen als bestanden in
-- platform/contract/ (gitignored, lokaal). Dat volstaat voor een dev-server
-- op de machine waar de contractbouw draait, maar niet voor een deploy: op
-- Vercel bestaat die map niet, en het contract in de build stoppen zou het
-- bevriezen op het moment van deployen (zie het commentaar in
-- platform/lib/laadContract.ts — precies daarom leest de UI per verzoek).
--
-- Deze tabel is de gehoste vorm van diezelfde bestanden, en niets meer dan
-- dat. Eén rij per gebouwd antwoord; `antwoord` draagt de JSON bit voor bit
-- zoals de contractbouw hem schreef. BEWUST GEEN NORMALISATIE van de inhoud:
-- het contract ís het contract (genummerde antwoorden, één vorm voor alle
-- consumenten). Kolommen uit de JSON trekken zou een tweede waarheid maken
-- die bij elke contractwijziging mee moet verhuizen.
--
-- De sleutel volgt de bestandsboom van de contractbouw:
--   scherm  overzicht|kanalen|producten|marge|prognose|stand,
--           plus 'winkels' voor de winkelindex (winkels.json)
--   taal    'nl' of 'fr' — dezelfde cijfers, andere labels
--   winkel  de winkelslug uit de winkelindeling, of '' voor het totaal.
--           Lege string en geen null: null kan geen deel van een primaire
--           sleutel zijn, en "geen winkel" is hier een gewone waarde.
--
-- De inhoud is geaggregeerde productverkoop met labels — precies wat volgens
-- harde regel 3 in de gehoste database mag. Toch alleen leesbaar voor
-- ingelogde gebruikers: het zijn de omzetcijfers van de eindklant.

create table if not exists public.contract_antwoord (
    scherm      text        not null,
    taal        text        not null,
    winkel      text        not null default '',
    antwoord    jsonb       not null,
    gebouwd_op  timestamptz not null default now(),
    primary key (scherm, taal, winkel)
);

comment on table public.contract_antwoord is
    'De gebouwde contractantwoorden, één rij per scherm x taal x winkel. '
    'Geschreven door de nachtelijke sync (scripts/contract_laad.py), gelezen '
    'door het platform met CONTRACT_BRON=db. De JSON is identiek aan de '
    'bestandsvorm in platform/contract/.';

comment on column public.contract_antwoord.winkel is
    'Winkelslug uit de winkelindeling, of lege string voor het totaal.';

comment on column public.contract_antwoord.gebouwd_op is
    'Wanneer deze rij geschreven is. De inhoudelijke versheid (bijgewerkt_op, '
    'gemeten_tot) zit in het antwoord zelf; dit is het bouwtijdstip.';

alter table public.contract_antwoord enable row level security;
alter table public.contract_antwoord force row level security;

drop policy if exists "authenticated leest contract_antwoord" on public.contract_antwoord;
create policy "authenticated leest contract_antwoord" on public.contract_antwoord
    for select to authenticated using (true);

revoke all on public.contract_antwoord from anon, authenticated;
grant select on public.contract_antwoord to authenticated;
