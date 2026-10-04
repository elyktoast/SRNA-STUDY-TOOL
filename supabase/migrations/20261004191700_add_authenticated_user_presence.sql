create table if not exists private.snar_user_presence (
  user_id uuid primary key references auth.users(id) on delete cascade,
  last_seen_at timestamptz not null default now()
);

revoke all on table private.snar_user_presence from public, anon, authenticated;

create or replace function public.snar_user_heartbeat()
returns boolean
language plpgsql
security definer
set search_path=''
as $$
declare uid uuid := auth.uid();
begin
  if uid is null then raise exception 'Authentication required'; end if;
  insert into private.snar_user_presence(user_id,last_seen_at)
  values(uid,now())
  on conflict (user_id) do update set last_seen_at=excluded.last_seen_at;
  return true;
end;
$$;
revoke all on function public.snar_user_heartbeat() from public, anon;
grant execute on function public.snar_user_heartbeat() to authenticated;

drop function if exists public.snar_admin_accounts();
create function public.snar_admin_accounts()
returns table(
  user_id uuid,email text,created_at timestamptz,last_sign_in_at timestamptz,
  access_status text,current_legal_accepted boolean,cat_used boolean,is_admin boolean,
  last_seen_at timestamptz,is_online boolean
)
language plpgsql stable security definer set search_path=''
as $$
begin
  if not private.snar_is_admin(auth.uid()) then raise exception 'Admin required'; end if;
  return query
  select
    u.id,u.email::text,u.created_at,u.last_sign_in_at,
    case when private.snar_account_is_active(u.id) then 'active'::text else 'suspended'::text end,
    exists(select 1 from private.snar_legal_acceptances a where a.user_id=u.id and a.terms_version='2026-09-27-v6' and a.privacy_version='2026-09-27-v6'),
    exists(select 1 from private.mbu_item_contributions c where c.user_id=u.id and c.session_mode='adaptive'),
    private.snar_is_admin(u.id),
    p.last_seen_at,
    coalesce(p.last_seen_at >= now()-interval '5 minutes',false)
  from auth.users u
  left join private.snar_user_presence p on p.user_id=u.id
  order by u.created_at desc;
end;
$$;
revoke all on function public.snar_admin_accounts() from public, anon;
grant execute on function public.snar_admin_accounts() to authenticated;
