-- 009 | De schrijfroute van het kostenmodel: één functie, één transactie.
--
-- WAAROM DEZE MIGRATIE BESTAAT
--
-- De tabellen `kosten_criterium` en `kosten_waarde` staan sinds migratie 005,
-- maar niemand kon erin schrijven vanaf de gehoste omgeving. Het formulier op
-- Instellingen weigerde daar met zoveel woorden ("dit formulier kan daar nog
-- niet in schrijven"), en dus kon de beheerder de kostencriteria nooit invullen
-- op het live platform — en zonder kostencriteria blijft het margescherm leeg.
-- Dat was de grootste commerciële leegte van het platform: alles omzet, geen
-- marge.
--
-- WAAROM EEN FUNCTIE EN NIET GEWOON GRANTS
--
-- Het platform op Vercel heeft géén Postgres-verbinding: `SUPABASE_DB_URL`
-- (het databasewachtwoord) staat daar bewust niet, en dat blijft zo (stack.md,
-- "Waar de secrets staan"). Het schrijft dus via PostgREST met
-- `SUPABASE_SECRET_KEY`, en dat komt binnen als de rol `service_role`.
--
-- Over PostgREST is één verzoek één transactie. Het kostenmodel bewaren raakt
-- twee tabellen — eerst het menu van criteria, dan de waarden per groep — en
-- dat moet alles-of-niets zijn, precies zoals de ETL dat in bakkerij/db/laden.py
-- doet. Twee losse PostgREST-verzoeken zouden een halve staat kunnen achterlaten:
-- criteria weg, waarden nog niet geschreven, en dan staat er een kostenmodel in
-- de database dat niemand heeft ingevuld.
--
-- Eén functie is dus één verzoek en één transactie. En het is nog strakker dan
-- grants: migratie 008 zegt "SELECT EN NIETS MEER — wie er ooit schrijfrechten
-- aan toevoegt, moet zich eerst afvragen waarom de schrijfroute niet meer
-- volstaat". Dat is hier het antwoord: `service_role` krijgt nog steeds geen
-- insert, update of delete op deze tabellen. Hij mag precies één ding, en dat
-- ene ding is geschreven, na te lezen en getest (tests/test_db_echt.py).
--
-- `security definer` hoort daarbij: de functie draait met de rechten van de
-- eigenaar, zodat de aanroeper zelf geen tabelrechten nodig heeft.
-- `set search_path = ''` sluit de bekende val van definer-functies (een
-- aanroeper die zijn eigen `public` vóór de echte zet); alle tabellen hieronder
-- staan daarom volledig gekwalificeerd. Types en ingebouwde functies blijven
-- werken: `pg_catalog` wordt altijd impliciet gezocht.
--
-- WAT DE FUNCTIE NIET DOET
--
-- Rekenen. De brutomarge is 100 min de som van de criteria, en die som staat in
-- `berekening.marge_per_groep` — één plaats, zoals harde regel 4 wil. Deze
-- functie bewaart invoer en niets meer.
--
-- Percentages blijven `numeric` (kolomtype uit 005): een kost van 30,5% die als
-- float rondreist, is op het scherm een keer 30,499...

create or replace function public.bewaar_kostenmodel(model jsonb, door text)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
    aantal_criteria integer;
    aantal_waarden  integer;
begin
    -- `door` is niet vrijblijvend: `bewaard_door` is `not null` in 005 omdat
    -- elke wijziging aan de cijferbasis de naam draagt van wie hem deed.
    if door is null or btrim(door) = '' then
        raise exception
            'bewaar_kostenmodel: "door" is leeg; elke wijziging draagt de naam '
            'van wie hem deed (kolom bewaard_door).';
    end if;

    if model is null
       or jsonb_typeof(model -> 'criteria') is distinct from 'array'
       or jsonb_typeof(model -> 'waarden') is distinct from 'object' then
        raise exception
            'bewaar_kostenmodel: het model mist "criteria" (lijst) of '
            '"waarden" (object van groep -> criterium -> percentage).';
    end if;

    -- Dezelfde grens als bakkerij/kostenmodel.py (MAX_CRITERIA) en
    -- platform/lib/kostenmodel.ts. Die twee toetsen eerder en met een leesbare
    -- melding; dit is de vangrail voor het geval er ooit een derde schrijver
    -- komt.
    select count(*) into aantal_criteria
    from jsonb_array_elements(model -> 'criteria');
    if aantal_criteria > 12 then
        raise exception
            'bewaar_kostenmodel: % criteria; het kostenmodel draagt er '
            'hoogstens 12.', aantal_criteria;
    end if;

    -- Een naamloos criterium kan geen kost dragen, en een naam langer dan
    -- NAAM_MAX (60) hoort niet in een tabelkop. Het schema kan dit niet zien:
    -- de primaire sleutel weert dubbele namen, niet lege of eindeloze.
    if exists (
        select 1
        from jsonb_array_elements(model -> 'criteria') as e(waarde)
        where btrim(coalesce(regexp_replace(e.waarde ->> 'naam', '\s+', ' ', 'g'), '')) = ''
           or length(btrim(regexp_replace(e.waarde ->> 'naam', '\s+', ' ', 'g'))) > 60
    ) then
        raise exception
            'bewaar_kostenmodel: een criteriumnaam is leeg of langer dan 60 '
            'tekens.';
    end if;

    if exists (
        select 1 from jsonb_each(model -> 'waarden') as g
        where btrim(g.key) = ''
    ) then
        raise exception
            'bewaar_kostenmodel: een productgroep zonder naam kan geen kosten '
            'dragen.';
    end if;

    -- Alles weg, dan alles erin — binnen deze ene functieaanroep, dus binnen
    -- één transactie. Dezelfde vorm als contract_antwoord (zie
    -- bakkerij/db/contract_rijen.py): een criterium dat de beheerder schrapt,
    -- hoort ook uit de database te verdwijnen, en er bestaat geen moment waarop
    -- een lezer een halve invoer ziet. Faalt er iets hieronder, dan rolt de
    -- hele aanroep terug en staat het oude kostenmodel er nog.
    --
    -- kosten_waarde eerst, ook al zou de cascade van 005 hem meenemen: expliciet
    -- is hier goedkoper dan afhankelijk zijn van een refereert-naar-clausule die
    -- iemand later kan versoepelen.
    delete from public.kosten_waarde;
    delete from public.kosten_criterium;

    -- `with ordinality` geeft de volgorde van het formulier; die volgorde is de
    -- kolomvolgorde op het scherm en hoort dus bewaard te blijven.
    insert into public.kosten_criterium (naam, omschrijving, volgorde, bewaard_door)
    select btrim(regexp_replace(e.waarde ->> 'naam', '\s+', ' ', 'g')),
           btrim(coalesce(e.waarde ->> 'omschrijving', '')),
           e.nr::integer,
           btrim(door)
    from jsonb_array_elements(model -> 'criteria')
             with ordinality as e(waarde, nr);

    -- `#>> '{}'` haalt de tekst uit de waarde, of hij nu als JSON-string
    -- ("30.50") of als JSON-getal (30.5) aankomt. De cast naar numeric en de
    -- check-clausule uit 005 (0 t/m 100) doen de rest; een percentage buiten
    -- bereik laat deze hele aanroep vallen in plaats van stil door te gaan.
    insert into public.kosten_waarde (groep, criterium, pct, bewaard_door)
    select btrim(g.key),
           btrim(regexp_replace(k.key, '\s+', ' ', 'g')),
           (k.value #>> '{}')::numeric,
           btrim(door)
    from jsonb_each(model -> 'waarden') as g
             cross join lateral jsonb_each(g.value) as k;

    select count(*) into aantal_waarden from public.kosten_waarde;
    return aantal_waarden;
end;
$$;

comment on function public.bewaar_kostenmodel(jsonb, text) is
    'Bewaart het volledige kostenmodel (criteria + waarden per productgroep) '
    'in één transactie: alles weg, dan alles erin. Enige schrijfroute voor de '
    'gehoste omgeving, die via PostgREST werkt en dus geen meerstapstransactie '
    'kan. Rekent niets uit; de brutomarge blijft 100 min de som, berekend in '
    'bakkerij/berekening.py.';

-- Publiek uitvoerrecht is de standaard voor een nieuwe functie, en bij
-- `security definer` is dat precies wat je niet wil: dan mag `anon` — de
-- publiceerbare sleutel, die in elke JavaScript-bundel zit — het kostenmodel
-- overschrijven. Eerst alles weg, dan één rol erbij.
revoke all on function public.bewaar_kostenmodel(jsonb, text) from public;
revoke all on function public.bewaar_kostenmodel(jsonb, text) from anon, authenticated;
grant execute on function public.bewaar_kostenmodel(jsonb, text) to service_role;
