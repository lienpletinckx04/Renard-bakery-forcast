-- 010 | De dodemansknop aansluiten: één rij die zegt of de sync nog leeft.
--
-- WAAROM DEZE MIGRATIE BESTAAT
--
-- `etl_run` bestaat sinds migratie 003 en wordt trouw geschreven: één rij per
-- run, geopend bij het begin en afgesloten bij het eind. Alleen las niemand
-- hem. Een sync die drie nachten faalt was op het scherm onzichtbaar, en de
-- cijfers stonden er even zelfverzekerd bij als op de dag dat ze klopten. Voor
-- een CFO-platform is dat de ergste soort fout: niet een verkeerd getal, maar
-- een oud getal dat zich voordoet als een vers getal.
--
-- WAAROM EEN VIEW EN NIET EEN VELD IN HET CONTRACT
--
-- De voor de hand liggende plek leek een extra veld in `stand.json`. Dat werkt
-- niet, en het is de moeite waard om op te schrijven waarom: het contract wordt
-- gebouwd DOOR de nachtelijke sync. Op het moment dat de contractbouw draait,
-- staat de eigen run op 'bezig' -- dus zou dat veld voor eeuwig "de sync loopt
-- nu" zeggen, ook drie nachten nadat er niets meer gedraaid heeft. Een oordeel
-- over versheid dat zelf bevriest, is geen dodemansknop maar een decoratie.
--
-- Het oordeel moet dus vallen op het moment van KIJKEN, niet op het moment van
-- bouwen. Dat kan op twee plaatsen: in de UI of in de database. In de UI mag
-- het niet -- harde regel 4, de UI rekent nooit, en een drempel die in een
-- component staat, bestaat niet voor de app van fase 2 en niet voor een export.
-- Blijft de database over. De drempels staan hieronder, één keer, in SQL, en
-- het platform toont wat eruit komt.
--
-- WAT DE VIEW TERUGGEEFT
--
-- Altijd precies één rij, ook wanneer `etl_run` helemaal leeg is. Dat is opzet:
-- "er heeft nog nooit een sync gedraaid" is zelf een antwoord dat op het scherm
-- hoort, en nul rijen zou in de UI niet te onderscheiden zijn van een kapotte
-- verbinding.
--
--   geval    de machinereden, waar het platform zijn zin bij zoekt
--   oordeel  'goed' | 'let_op' | 'fout', dezelfde drie woorden als de
--            wachters in bakkerij/kwaliteit.py -- de voettekst weegt ze samen
--
-- DE DREMPELS, EN WAAROM ZE ZO STAAN
--
--   36 uur   tot hier is 'goed'. De planner van GitHub Actions is best effort
--            en kan tientallen minuten later vuren; één overgeslagen nacht mag
--            dus geen alarm zijn, twee wel.
--   3 dagen  daarboven is het 'fout'. Dat is de grens die de opdracht zelf
--            noemde: "een sync die drie nachten faalt".
--   3 uur    een run die zolang op 'bezig' staat, is gestorven. De job zelf
--            heeft een timeout van 90 minuten (nachtelijke-sync.yml), dus
--            daarboven kan hij niet eerlijk nog lopen.
--
-- EEN SLUITING IS GEEN STORING -- en dat regelt zichzelf hier. Tijdens een
-- sluiting stopt de poortwachter de ketting meteen, maar hij sluit zijn run wel
-- af als 'goed' met nul rijen (bakkerij/db/sync.py). De klok blijft dus lopen
-- op een geslaagde run, en het platform zwijgt. Dat is dezelfde regel als bij
-- de bronstanden: een permanent alarm is onzichtbaar op de dag van de echte
-- storing.

create or replace view public.sync_stand
with (security_invoker = true) as
select
    laatste.status                                as laatste_status,
    laatste.gestart_op                            as laatste_gestart_op,
    laatste.geeindigd_op                          as laatste_geeindigd_op,
    laatste.melding                               as laatste_melding,
    geslaagd.gestart_op                           as geslaagd_gestart_op,
    case
        when laatste.status is null                              then 'nooit'
        when laatste.status = 'fout'                             then 'gefaald'
        when laatste.status = 'bezig'
             and now() - laatste.gestart_op > interval '3 hours' then 'gestrand'
        when laatste.status = 'bezig'                            then 'loopt'
        when geslaagd.gestart_op is null                         then 'gefaald'
        when now() - geslaagd.gestart_op > interval '3 days'     then 'oud'
        when now() - geslaagd.gestart_op > interval '36 hours'   then 'achter'
        else 'vers'
    end                                           as geval,
    case
        -- 'nooit' is bewust 'let_op' en niet 'fout': zolang de planning uit
        -- staat is dit de normale toestand, en een rood scherm dat maandenlang
        -- rood blijft, leest niemand nog. Wel 'let_op', want het is echt iets
        -- om te weten: deze cijfers verversen niet vanzelf.
        when laatste.status is null                              then 'let_op'
        when laatste.status = 'fout'                             then 'fout'
        when laatste.status = 'bezig'
             and now() - laatste.gestart_op > interval '3 hours' then 'fout'
        when laatste.status = 'bezig'                            then 'goed'
        when geslaagd.gestart_op is null                         then 'fout'
        when now() - geslaagd.gestart_op > interval '3 days'     then 'fout'
        when now() - geslaagd.gestart_op > interval '36 hours'   then 'let_op'
        else 'goed'
    end                                           as oordeel
from (select 1) as eenrij
-- Twee lateralen en geen enkele join op etl_run zelf: zo staat er altijd
-- precies één rij, ook bij een lege tabel. De jongste run en de jongste
-- GESLAAGDE run zijn bewust twee vragen -- na een mislukte nacht wil je zowel
-- weten dat hij mislukte als hoe oud de laatste goede stand is.
left join lateral (
    select status, gestart_op, geeindigd_op, melding
      from public.etl_run
     where bron = 'nachtelijke-sync'
     order by gestart_op desc
     limit 1
) as laatste on true
left join lateral (
    select gestart_op
      from public.etl_run
     where bron = 'nachtelijke-sync' and status = 'goed'
     order by gestart_op desc
     limit 1
) as geslaagd on true;

comment on view public.sync_stand is
    'Eén rij: leeft de nachtelijke sync nog? Het oordeel valt hier en niet in '
    'het contract, want het contract wordt door de sync zelf gebouwd en zou '
    'dus voor eeuwig "loopt nu" zeggen. Drempels: 36 uur goed, 3 dagen fout.';

-- `security_invoker = true` hierboven: de view leest met de rechten van wie
-- haar bevraagt, niet met die van haar eigenaar. Zonder dat zou ze de RLS op
-- `etl_run` (migratie 003) omzeilen, en dan is een view een achterdeur.
-- `melding` draagt alleen foutmeldingen zonder data -- dat staat als eis bij de
-- kolom in 003 en geldt hier onverkort, want dit is de plek waar hij op een
-- scherm terechtkomt.
revoke all on public.sync_stand from anon, authenticated;
grant select on public.sync_stand to authenticated;
grant select on public.sync_stand to service_role;
