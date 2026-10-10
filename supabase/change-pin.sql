-- ShipStiffs: let the organizer change the trip PIN from the app's Setup tab.
-- 1) Replace CHANGE-ME below with an organizer PIN only you know (not the trip PIN).
-- 2) Paste this whole script into Supabase > SQL Editor > Run. Safe to run again.

insert into private.settings (k, v) values ('admin_pin', 'CHANGE-ME')   -- your organizer PIN
  on conflict (k) do update set v = excluded.v;

create or replace function public.change_pin(p_admin text, p_new text) returns text
language plpgsql security definer set search_path = private as $fn$
declare admin text := (select v from private.settings where k = 'admin_pin');
begin
  if admin is null or admin = 'CHANGE-ME' then return 'not_set_up'; end if;
  if lower(coalesce(p_admin, '')) is distinct from lower(admin) then return 'wrong_admin'; end if;
  if length(trim(coalesce(p_new, ''))) < 4 then return 'too_short'; end if;
  update private.settings set v = trim(p_new) where k = 'pin';
  return 'ok';
end
$fn$;
grant execute on function public.change_pin(text, text) to anon, authenticated;
