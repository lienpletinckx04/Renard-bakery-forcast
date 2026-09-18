-- 001 | De dimensies: de kalender en het product.
--
-- Volgorde is niet vrij: de feitentabellen in 002 verwijzen hiernaar.
--
-- Over RLS in dit bestand: elke tabel krijgt RLS in dezelfde migratie waarin
-- ze ontstaat. In Supabase hangt PostgREST aan de database, dus een tabel
-- zonder RLS is leesbaar voor iedereen die de publiceerbare sleutel heeft --
-- en die sleutel staat per definitie in de JavaScript-bundel. "RLS erbij in
-- een latere migratie" betekent dus een venster waarin de omzet van de klant
-- publiek staat. Dat venster bestaat hier niet.
--
-- Het patroon (stack.md, "RLS"): wie ingelogd is mag lezen, niemand mag
-- schrijven, de ETL schrijft via een rechtstreekse Postgres-verbinding en
-- omzeilt RLS daarmee volledig. Er zijn daarom bewust GEEN insert-, update-
-- of delete-policies. Dat is geen omissie.

-- --------------------------------------------------------------------------
-- dim_kalender
-- --------------------------------------------------------------------------
-- Eén rij per kalenderdag over het hele bereik van de verkopen, plus zestig
-- dagen overloop (canoniek.VOORUIT_DAGEN) zodat de prognose kalenderrijen
-- heeft voor dagen die nog moeten komen.
--
-- Het onderscheid dat deze tabel draagt en dat nergens anders bestaat:
--   winkel_gemeten  valt de datum binnen het bereik van het Odoo-extract
--   winkel_open     was er die dag kassaverkoop van betekenis
--
-- `winkel_open` is alleen betekenisvol waar `winkel_gemeten` waar is. Een
-- dag die niet gemeten is, is niet "dicht" -- we weten het gewoon niet, en
-- dat verschil is precies waar de dodemansknop en de wachters op draaien.

create table if not exists public.dim_kalender (
    datum              date        primary key,
    weekdag            smallint    not null check (weekdag between 0 and 6),
    weekdagnaam        text        not null,
    is_weekend         boolean     not null,
    feestdag           boolean     not null,
    feestdagnaam       text        not null default '',
    dag_voor_feestdag  boolean     not null,
    dag_na_feestdag    boolean     not null,
    brugdag            boolean     not null,
    maand              smallint    not null check (maand between 1 and 12),
    weeknr             smallint    not null check (weeknr between 1 and 53),
    dag_van_jaar       smallint    not null check (dag_van_jaar between 1 and 366),
    winkel_gemeten     boolean     not null,
    winkel_open        boolean     not null
);

-- Twee kolommen die het canonieke datamodel in CLAUDE.md wél noemt maar die
-- hier bewust ONTBREKEN, omdat de kalenderlaag ze niet produceert:
--
--   schoolvakantie  -- open punt O10 / vraag 47: Franstalig, Nederlandstalig
--                      of beide? In Elsene lopen die twee regimes niet gelijk,
--                      dus dit is geen detail dat je even invult.
--   evenement       -- nog geen bron voor.
--
-- Ze worden toegevoegd zodra de kalenderlaag ze levert. Een kolom die er wel
-- staat maar altijd leeg is, is erger dan een kolom die er niet staat: de
-- eerste suggereert dat er gemeten is.

comment on table public.dim_kalender is
    'Eén rij per kalenderdag. winkel_open is alleen betekenisvol waar winkel_gemeten waar is.';

alter table public.dim_kalender enable row level security;
alter table public.dim_kalender force row level security;

drop policy if exists "authenticated leest dim_kalender" on public.dim_kalender;
create policy "authenticated leest dim_kalender" on public.dim_kalender
    for select to authenticated using (true);

revoke all on public.dim_kalender from anon, authenticated;
grant select on public.dim_kalender to authenticated;

-- --------------------------------------------------------------------------
-- dim_product
-- --------------------------------------------------------------------------
-- Het assortiment. `product_id` is tekst en geen getal: het komt zo uit Odoo
-- en uit de TGTG-parser, en er zit geen rekenkundige betekenis in.
--
-- De naam hoort hier en niet in de feitentabel. Een productnaam wijzigt in
-- Odoo (spelling, hoofdletters, een toevoeging) zonder dat het product een
-- ander product wordt; stond de naam in elke feitrij, dan zou zo'n wijziging
-- de historie in tweeën splitsen. Welke naam er wint bij meerdere varianten
-- wordt in de laadlaag bepaald door een functie met een test, niet hier.

create table if not exists public.dim_product (
    product_id     text  primary key,
    product_naam   text  not null
);

comment on table public.dim_product is
    'Assortiment. Eén naam per product_id; de laadlaag kiest welke bij varianten.';

alter table public.dim_product enable row level security;
alter table public.dim_product force row level security;

drop policy if exists "authenticated leest dim_product" on public.dim_product;
create policy "authenticated leest dim_product" on public.dim_product
    for select to authenticated using (true);

revoke all on public.dim_product from anon, authenticated;
grant select on public.dim_product to authenticated;
