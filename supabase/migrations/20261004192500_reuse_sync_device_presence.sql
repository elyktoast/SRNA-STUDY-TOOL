drop function if exists public.snar_user_heartbeat();
drop table if exists private.snar_user_presence;

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
    d.last_seen_at,
    coalesce(d.last_seen_at >= now()-interval '6 minutes',false)
  from auth.users u
  left join lateral (
    select max(sd.last_seen_at) as last_seen_at
    from public.mbu_sync_devices sd
    where sd.user_id=u.id
  ) d on true
  order by u.created_at desc;
end;
$$;
revoke all on function public.snar_admin_accounts() from public, anon;
grant execute on function public.snar_admin_accounts() to authenticated;
