create table if not exists public.mbu_question_exposure (
  user_id uuid not null references auth.users(id) on delete cascade,
  course_id text not null,
  exam_id text not null,
  question_uid text not null,
  topic text not null default 'Other',
  content_version text not null default '1',
  first_issued_at timestamptz not null default now(),
  last_issued_at timestamptz not null default now(),
  times_issued integer not null default 1 check (times_issued > 0),
  coverage_cycle integer not null default 1 check (coverage_cycle > 0),
  last_session_id uuid,
  primary key (user_id, course_id, exam_id, question_uid, content_version)
);
create index if not exists mbu_question_exposure_user_topic_idx on public.mbu_question_exposure(user_id,course_id,exam_id,topic,last_issued_at);
alter table public.mbu_question_exposure enable row level security;
revoke all on table public.mbu_question_exposure from anon, authenticated;
grant select, insert, update on table public.mbu_question_exposure to authenticated;
create policy "question exposure select own" on public.mbu_question_exposure for select to authenticated using ((select auth.uid())=user_id);
create policy "question exposure insert own" on public.mbu_question_exposure for insert to authenticated with check ((select auth.uid())=user_id);
create policy "question exposure update own" on public.mbu_question_exposure for update to authenticated using ((select auth.uid())=user_id) with check ((select auth.uid())=user_id);

create table if not exists public.mbu_question_sessions (
  user_id uuid not null references auth.users(id) on delete cascade,
  session_id uuid not null,
  course_id text not null,
  exam_id text not null,
  mode text not null,
  question_uids jsonb not null,
  new_count integer not null default 0,
  review_count integer not null default 0,
  created_at timestamptz not null default now(),
  primary key(user_id,session_id)
);
create index if not exists mbu_question_sessions_user_created_idx on public.mbu_question_sessions(user_id,created_at desc);
alter table public.mbu_question_sessions enable row level security;
revoke all on table public.mbu_question_sessions from anon, authenticated;
grant select, insert on table public.mbu_question_sessions to authenticated;
create policy "question sessions select own" on public.mbu_question_sessions for select to authenticated using ((select auth.uid())=user_id);
create policy "question sessions insert own" on public.mbu_question_sessions for insert to authenticated with check ((select auth.uid())=user_id);

create or replace function public.mbu_record_question_session(
  p_session_id uuid,
  p_course_id text,
  p_exam_id text,
  p_mode text,
  p_items jsonb,
  p_new_count integer default 0,
  p_review_count integer default 0
) returns boolean
language plpgsql security invoker set search_path=''
as $$
declare item jsonb; uid text; topic_name text; version_name text; cycle_no integer;
begin
  if (select auth.uid()) is null then raise exception 'authentication required'; end if;
  if p_session_id is null or jsonb_typeof(p_items)<>'array' then raise exception 'invalid session payload'; end if;
  insert into public.mbu_question_sessions(user_id,session_id,course_id,exam_id,mode,question_uids,new_count,review_count)
  values((select auth.uid()),p_session_id,left(p_course_id,100),left(p_exam_id,100),left(p_mode,40),
    (select coalesce(jsonb_agg(x->>'uid'),'[]'::jsonb) from jsonb_array_elements(p_items) x),
    greatest(0,p_new_count),greatest(0,p_review_count))
  on conflict(user_id,session_id) do nothing;
  if not found then return true; end if;
  for item in select value from jsonb_array_elements(p_items)
  loop
    uid:=left(coalesce(item->>'uid',''),220); topic_name:=left(coalesce(item->>'topic','Other'),220);
    version_name:=left(coalesce(item->>'version','1'),80); cycle_no:=greatest(1,coalesce((item->>'cycle')::integer,1));
    if uid='' then continue; end if;
    insert into public.mbu_question_exposure(user_id,course_id,exam_id,question_uid,topic,content_version,coverage_cycle,last_session_id)
    values((select auth.uid()),left(p_course_id,100),left(p_exam_id,100),uid,topic_name,version_name,cycle_no,p_session_id)
    on conflict(user_id,course_id,exam_id,question_uid,content_version) do update
      set last_issued_at=now(), times_issued=public.mbu_question_exposure.times_issued+1,
          coverage_cycle=greatest(public.mbu_question_exposure.coverage_cycle,excluded.coverage_cycle),
          topic=excluded.topic,last_session_id=excluded.last_session_id;
  end loop;
  return true;
end $$;
revoke all on function public.mbu_record_question_session(uuid,text,text,text,jsonb,integer,integer) from public,anon;
grant execute on function public.mbu_record_question_session(uuid,text,text,text,jsonb,integer,integer) to authenticated;
