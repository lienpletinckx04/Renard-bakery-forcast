-- 005 | Het kostenmodel: kostencriteria per productgroep, beheerd door de klant.
--
-- Vervangt marge_instelling (004). Die tabel droeg één brutomarge per groep;
-- het kostenmodel bouwt diezelfde brutomarge op uit criteria die de beheerder
-- zelf samenstelt (grondstoffen, verlies, ...): brutomarge = 100 - som van de
-- ingevulde criteria. Dit is de databasevorm van `data/config/kostenmodel.json`;
-- zolang S2 open staat, leeft de invoer in dat bestand en neemt deze tabel het
-- 1-op-1 over zodra de database er is. marge_instelling is nooit uitgerold
-- (er bestaat nog geen omgeving), dus droppen is hier veilig en geen dataverlies.
--
-- Percentages als numeric, nooit double precision: een kost van 30,5% die als
-- float rondreist, is op het scherm een keer 30,499...

drop table if exists public.marge_instelling;

create table if not exists public.kosten_criterium (
    naam            text primary key,
    omschrijving    text not null default '',
    volgorde        integer not null default 0,
    bewaard_door    text not null,
    bewaard_op      timestamptz not null default now()
);

comment on table public.kosten_criterium is
    'Het menu van kostencriteria, samengesteld door een beheerder. Geen brondata.';

create table if not exists public.kosten_waarde (
    groep           text not null,
    criterium       text not null
                    references public.kosten_criterium (naam) on delete cascade,
    pct             numeric(5, 2) not null
                    check (pct >= 0 and pct <= 100),
    bewaard_door    text not null,
    bewaard_op      timestamptz not null default now(),
    primary key (groep, criterium)
);

comment on table public.kosten_waarde is
    'Kost per productgroep per criterium, als percentage van de omzet. '
    'Brutomarge van een groep = 100 - som van haar ingevulde criteria.';

-- De winkelindeling: welke filialen samen één verkooppunt vormen. De
-- bestandsvorm is data/config/winkels.json; zie bakkerij/winkels.py.
create table if not exists public.winkel (
    slug            text primary key,
    naam            text not null unique,
    bewaard_door    text not null,
    bewaard_op      timestamptz not null default now()
);

comment on table public.winkel is
    'Eén rij per verkooppunt. Zonder rijen telt alles als één geheel; zie bakkerij/winkels.py.';

create table if not exists public.winkel_filiaal (
    filiaal_id      text primary key,
    winkel_slug     text not null
                    references public.winkel (slug) on delete cascade
);

comment on table public.winkel_filiaal is
    'Een filiaal (kassa of bron-store-id) hoort bij precies één winkel.';

-- Zelfde toegangsregels als 004: alleen ingelogde gebruikers lezen; schrijven
-- loopt via de service-rol van de berekeningslaag, nooit rechtstreeks.
alter table public.kosten_criterium enable row level security;
alter table public.kosten_criterium force row level security;
alter table public.kosten_waarde enable row level security;
alter table public.kosten_waarde force row level security;
alter table public.winkel enable row level security;
alter table public.winkel force row level security;
alter table public.winkel_filiaal enable row level security;
alter table public.winkel_filiaal force row level security;

drop policy if exists "authenticated leest kosten_criterium" on public.kosten_criterium;
create policy "authenticated leest kosten_criterium" on public.kosten_criterium
    for select to authenticated using (true);
drop policy if exists "authenticated leest kosten_waarde" on public.kosten_waarde;
create policy "authenticated leest kosten_waarde" on public.kosten_waarde
    for select to authenticated using (true);
drop policy if exists "authenticated leest winkel" on public.winkel;
create policy "authenticated leest winkel" on public.winkel
    for select to authenticated using (true);
drop policy if exists "authenticated leest winkel_filiaal" on public.winkel_filiaal;
create policy "authenticated leest winkel_filiaal" on public.winkel_filiaal
    for select to authenticated using (true);

revoke all on public.kosten_criterium from anon, authenticated;
revoke all on public.kosten_waarde from anon, authenticated;
revoke all on public.winkel from anon, authenticated;
revoke all on public.winkel_filiaal from anon, authenticated;
grant select on public.kosten_criterium to authenticated;
grant select on public.kosten_waarde to authenticated;
grant select on public.winkel to authenticated;
grant select on public.winkel_filiaal to authenticated;
