-- ShipStiffs, Bandon Warm-ups: the Bandon Crossings scorecard (pars, men's handicap holes,
-- ratings and slopes for every tee). Paste into Supabase > SQL Editor > Run. Safe to run again.
-- Only needed if the Warm-ups event already has Bandon Crossings; a new round at Bandon Crossings
-- gets this card automatically. Pick today's tees on the Scores tab (it starts on Blue).
insert into public.docs (collection, id, data)
values ('bandon-crossings.courses', 'crossings', '{"name":"Bandon Crossings","holes":18,"pars":[4,4,4,5,5,3,4,4,3,4,3,5,5,3,4,4,3,5],"si":[15,11,7,9,3,13,5,1,17,8,18,12,2,6,16,10,14,4],"par":72,"tees":"Blue","rating":71.1,"slope":127,"teeSets":[{"name":"Black","rating":74.0,"slope":139,"par":72},{"name":"Blue","rating":71.1,"slope":127,"par":72},{"name":"Blue/White","rating":70.1,"slope":124,"par":72},{"name":"White","rating":69.0,"slope":122,"par":72},{"name":"White/Red","rating":67.1,"slope":118,"par":72},{"name":"Red","rating":65.7,"slope":117,"par":72},{"name":"Gold","rating":62.3,"slope":107,"par":72}],"source":"Bandon Crossings card (09/2020). Ratings and handicap holes are for men; hole 5 is a par 5 for men."}'::jsonb)
on conflict (collection, id) do update set data = public.docs.data || excluded.data
returning data->>'name', data->>'tees';
