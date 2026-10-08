-- Version the existing production lifecycle ledger and six-argument RPC.
-- No exposure, answer history, or existing session rows are changed.
create table if not exists public.mbu_question_lifecycle_events (
 user_id uuid not null,
 session_id uuid not null,
 course_id text not null,
 exam_id text not null,
 question_uid text not null,
 content_version text not null,
 event text not null check (event in ('viewed','answered')),
 created_at timestamptz not null default now(),
 primary key (user_id,session_id,question_uid,content_version,event)
);
alter table public.mbu_question_lifecycle_events enable row level security;
revoke all on public.mbu_question_lifecycle_events from anon,authenticated;
grant select,insert on public.mbu_question_lifecycle_events to authenticated;
do $$ begin
 if not exists(select 1 from pg_policies where schemaname='public' and tablename='mbu_question_lifecycle_events' and policyname='users manage own question lifecycle events') then
  create policy "users manage own question lifecycle events" on public.mbu_question_lifecycle_events for all to authenticated using (user_id=(select auth.uid())) with check (user_id=(select auth.uid()));
 end if;
end $$;
drop function if exists public.mbu_mark_question_lifecycle(text,text,text,text,text);
create or replace function public.mbu_mark_question_lifecycle(p_course_id text,p_exam_id text,p_question_uid text,p_content_version text,p_event text,p_session_id uuid)
returns boolean language plpgsql security invoker set search_path='' as $$
declare inserted boolean;
begin
 if (select auth.uid()) is null then raise exception 'authentication required'; end if;
 if p_event not in ('viewed','answered') then raise exception 'invalid lifecycle event'; end if;
 if p_session_id is null then raise exception 'session required'; end if;
 insert into public.mbu_question_lifecycle_events(user_id,session_id,course_id,exam_id,question_uid,content_version,event)
 values((select auth.uid()),p_session_id,left(p_course_id,100),left(p_exam_id,100),p_question_uid,p_content_version,p_event)
 on conflict do nothing;
 inserted:=found;
 if not inserted then return true; end if;
 if p_event='viewed' then
  update public.mbu_question_exposure set first_viewed_at=coalesce(first_viewed_at,now()),last_viewed_at=now(),times_viewed=times_viewed+1
  where user_id=(select auth.uid()) and course_id=left(p_course_id,100) and exam_id=left(p_exam_id,100) and question_uid=p_question_uid and content_version=p_content_version;
 else
  update public.mbu_question_exposure set first_answered_at=coalesce(first_answered_at,now()),last_answered_at=now(),times_answered=times_answered+1
  where user_id=(select auth.uid()) and course_id=left(p_course_id,100) and exam_id=left(p_exam_id,100) and question_uid=p_question_uid and content_version=p_content_version;
 end if;
 if not found then raise exception 'question exposure not found'; end if;
 return true;
end $$;
revoke all on function public.mbu_mark_question_lifecycle(text,text,text,text,text,uuid) from public,anon;
grant execute on function public.mbu_mark_question_lifecycle(text,text,text,text,text,uuid) to authenticated;
