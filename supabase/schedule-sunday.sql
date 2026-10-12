-- ShipStiffs, Bandon 2026: make Bandon Dunes a regular Sunday round, and add Pacific Dunes
-- (Sun 3:10 PM) after it. Paste into Supabase > SQL Editor > Run. Safe to run again.
-- Scores, matches and the other rounds are not touched. Phones update within a few seconds.

update public.docs
set data = jsonb_set(data, '{rounds}',
  (select jsonb_agg(case when r->>'id' = 'dunes' then r || '{"day": "Sun 10/18"}' else r end order by n)
     from jsonb_array_elements(data->'rounds') with ordinality as t(r, n))
  || case when data->'rounds' @> '[{"id": "pacific"}]' then '[]'::jsonb
          else '[{"id": "pacific", "course": "pacific", "name": "Pacific Dunes", "day": "Sun 10/18 · 3:10 PM"}]'::jsonb end)
where collection = 'setup' and id = 'main'
returning data->'rounds';
