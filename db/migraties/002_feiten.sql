-- 002 | De feiten: verkoop, bonnen, verkoopuren, kanaalkost.
--
-- Wat hier NIET in komt, en dat is een harde grens uit scope.md en
-- architectuur.md: `partner_id`, klantnaam, adres, bonnotitie, of welk
-- klantveld dan ook. De extractie vraagt die velden nooit op. Ook de ruwe
-- bonregels en het verzekeringsextract blijven lokaal -- niet alleen om
-- privacyredenen maar ook om kosten: miljoenen ruwe rijen in Postgres is
-- precies wat het prijskaartje laat ontsporen (stack.md, "Kosten").
--
-- Over geld: `numeric`, nooit `double precision`. De projectregel is Decimal
-- of centen als int; `numeric` is de Postgres-vorm daarvan en psycopg3 geeft
-- hem als `Decimal` terug. Een float voor euro's telt niet op tot de cent, en
-- er staan invarianten in de berekeningslaag die precies dát eisen.

-- --------------------------------------------------------------------------
-- fact_verkoop
-- --------------------------------------------------------------------------
-- De kern. Eén rij per dag / filiaal / product / kanaal.
--
-- Alle drie de kassa's tellen mee en worden opgeteld tot één geheel; dat is
-- op 12 augustus 2026 gemeten en niet aangenomen. `filiaal_id` blijft in het
-- model bestaan tot de opdrachtgever bevestigt of het registers of vestigingen
-- zijn (vraag 18) -- daarom staat het in de sleutel en niet weggeaggregeerd.

create table if not exists public.fact_verkoop (
    datum            date           not null references public.dim_kalender (datum),
    filiaal_id       text           not null,
    product_id       text           not null references public.dim_product (product_id),
    kanaal           text           not null check (kanaal in ('winkel', 'deliveroo', 'tgtg', 'overig')),
    aantal           numeric(14,3)  not null,
    omzet_excl_btw   numeric(14,2)  not null,
    primary key (datum, kanaal, filiaal_id, product_id)
);

-- `aantal` is numeric en geen integer: TGTG rekent in pakketten en de
-- kassa kent producten per gewicht. Een integer zou daar stilzwijgend op
-- afronden.

-- De sleutel begint op datum omdat vrijwel elke query een datumbereik
-- afbakent. Deze twee indexen dekken de twee andere ingangen die de
-- berekeningslaag gebruikt: per product over de tijd, en per kanaal per dag.
create index if not exists fact_verkoop_product_idx
    on public.fact_verkoop (product_id, datum);
create index if not exists fact_verkoop_kanaal_idx
    on public.fact_verkoop (kanaal, datum);

comment on table public.fact_verkoop is
    'Geaggregeerde productverkoop per dag/filiaal/product/kanaal. Geen klantvelden.';

alter table public.fact_verkoop enable row level security;
alter table public.fact_verkoop force row level security;

drop policy if exists "authenticated leest fact_verkoop" on public.fact_verkoop;
create policy "authenticated leest fact_verkoop" on public.fact_verkoop
    for select to authenticated using (true);

revoke all on public.fact_verkoop from anon, authenticated;
grant select on public.fact_verkoop to authenticated;

-- --------------------------------------------------------------------------
-- fact_bonnen
-- --------------------------------------------------------------------------
-- Aantal bonnen per dag per filiaal, distinct geteld aan de bron. Dit is de
-- noemer onder "klanten of mandje?": omzet is klanten x gemiddeld bonbedrag,
-- en zonder deze tabel valt die ontbinding niet te maken.

create table if not exists public.fact_bonnen (
    datum        date      not null references public.dim_kalender (datum),
    filiaal_id   text      not null,
    bonnen       integer   not null check (bonnen >= 0),
    primary key (datum, filiaal_id)
);

comment on table public.fact_bonnen is
    'Aantal kassabonnen per dag per filiaal, distinct aan de bron geteld.';

alter table public.fact_bonnen enable row level security;
alter table public.fact_bonnen force row level security;

drop policy if exists "authenticated leest fact_bonnen" on public.fact_bonnen;
create policy "authenticated leest fact_bonnen" on public.fact_bonnen
    for select to authenticated using (true);

revoke all on public.fact_bonnen from anon, authenticated;
grant select on public.fact_bonnen to authenticated;

-- --------------------------------------------------------------------------
-- fact_product_uren
-- --------------------------------------------------------------------------
-- Eerste en laatste verkoopuur per product per dag, in Europe/Brussels.
--
-- Waarvoor dit bestaat: een product dat structureel om 10u zijn laatste bon
-- heeft terwijl de winkel tot 17u open is, was uitverkocht. Dat is het
-- leeg-reksignaal (censurering), en zonder dat signaal leest de prognose een
-- uitverkochte dag als een dag met weinig vraag.

create table if not exists public.fact_product_uren (
    datum         date     not null references public.dim_kalender (datum),
    product_id    text     not null references public.dim_product (product_id),
    eerste_uur    numeric(5,2)  not null check (eerste_uur >= 0 and eerste_uur < 24),
    laatste_uur   numeric(5,2)  not null check (laatste_uur >= 0 and laatste_uur < 24),
    bonnen        integer  not null check (bonnen >= 0),
    primary key (datum, product_id),
    check (laatste_uur >= eerste_uur)
);

comment on table public.fact_product_uren is
    'Eerste/laatste verkoopuur per product per dag (Europe/Brussels). Basis voor het leeg-reksignaal.';

alter table public.fact_product_uren enable row level security;
alter table public.fact_product_uren force row level security;

drop policy if exists "authenticated leest fact_product_uren" on public.fact_product_uren;
create policy "authenticated leest fact_product_uren" on public.fact_product_uren
    for select to authenticated using (true);

revoke all on public.fact_product_uren from anon, authenticated;
grant select on public.fact_product_uren to authenticated;

-- --------------------------------------------------------------------------
-- fact_kanaalkost
-- --------------------------------------------------------------------------
-- De wig per kanaal per maand: wat de klant betaalde, wat het platform
-- inhield, wat er overbleef.
--
-- Per maand en niet per dag, omdat dat het niveau is waarop TGTG zijn
-- tarieven zet. `maand` is tekst in de vorm `JJJJ-MM`, precies zoals
-- canoniek.kanaalkost_tgtg hem produceert -- een date zou een dag suggereren
-- die er niet is.

create table if not exists public.fact_kanaalkost (
    kanaal                text           not null check (kanaal in ('winkel', 'deliveroo', 'tgtg', 'overig')),
    maand                 text           not null check (maand ~ '^[0-9]{4}-[0-9]{2}$'),
    stuks                 numeric(14,3)  not null,
    bruto_per_stuk        numeric(14,4)  not null,
    commissie_per_stuk    numeric(14,4)  not null,
    inhouding_pct         numeric(6,4)   not null check (inhouding_pct between 0 and 1),
    primary key (kanaal, maand)
);

comment on table public.fact_kanaalkost is
    'Kanaalkost per maand: bruto, commissie en inhouding. Per maand want dat is het tariefniveau.';

alter table public.fact_kanaalkost enable row level security;
alter table public.fact_kanaalkost force row level security;

drop policy if exists "authenticated leest fact_kanaalkost" on public.fact_kanaalkost;
create policy "authenticated leest fact_kanaalkost" on public.fact_kanaalkost
    for select to authenticated using (true);

revoke all on public.fact_kanaalkost from anon, authenticated;
grant select on public.fact_kanaalkost to authenticated;
