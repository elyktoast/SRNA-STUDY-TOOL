-- Protect concurrent same-account devices; unviewed abandoned reservations expire after 30 minutes.
CREATE OR REPLACE FUNCTION public.mbu_record_question_session(p_session_id uuid, p_course_id text, p_exam_id text, p_mode text, p_items jsonb, p_new_count integer DEFAULT 0, p_review_count integer DEFAULT 0)
 RETURNS boolean
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare item jsonb;uid text;topic_name text;version_name text;cycle_no integer;lock_key bigint;conflicts integer;
begin
 if (select auth.uid()) is null then raise exception 'authentication required'; end if;
 if p_session_id is null or jsonb_typeof(p_items)<>'array' then raise exception 'invalid session payload'; end if;
 lock_key:=hashtextextended((select auth.uid())::text||':'||left(p_course_id,100)||':'||left(p_exam_id,100),0);
 perform pg_advisory_xact_lock(lock_key);
 if exists(select 1 from public.mbu_question_sessions where user_id=(select auth.uid()) and session_id=p_session_id) then return true; end if;
 select count(*) into conflicts
 from jsonb_array_elements(p_items) x
 join public.mbu_question_exposure e
 on e.user_id=(select auth.uid()) and e.course_id=left(p_course_id,100)
 and e.exam_id=left(p_exam_id,100) and e.question_uid=x->>'uid'
 and e.content_version=coalesce(x->>'version','1')
 where coalesce(x->>'kind','coverage')='coverage'
 and e.coverage_cycle>=greatest(1,coalesce((x->>'cycle')::integer,1))
 and (e.times_viewed>0 or (e.times_issued>0 and e.last_issued_at>now()-interval '30 minutes'));
 if conflicts>0 then raise exception using errcode='40001',message='question coverage changed; retry selection'; end if;
 insert into public.mbu_question_sessions(user_id,session_id,course_id,exam_id,mode,question_uids,new_count,review_count)
 values((select auth.uid()),p_session_id,left(p_course_id,100),left(p_exam_id,100),left(p_mode,40),
 (select coalesce(jsonb_agg(x->>'uid'),'[]'::jsonb) from jsonb_array_elements(p_items) x),greatest(0,p_new_count),greatest(0,p_review_count));
 for item in select value from jsonb_array_elements(p_items) loop
  uid:=left(coalesce(item->>'uid',''),220);topic_name:=left(coalesce(item->>'topic','Other'),220);
  version_name:=left(coalesce(item->>'version','1'),80);cycle_no:=greatest(1,coalesce((item->>'cycle')::integer,1));
  if uid='' then continue; end if;
  insert into public.mbu_question_exposure(user_id,course_id,exam_id,question_uid,topic,content_version,coverage_cycle,last_session_id)
  values((select auth.uid()),left(p_course_id,100),left(p_exam_id,100),uid,topic_name,version_name,cycle_no,p_session_id)
  on conflict(user_id,course_id,exam_id,question_uid,content_version) do update
  set last_issued_at=now(),times_issued=public.mbu_question_exposure.times_issued+1,
  coverage_cycle=greatest(public.mbu_question_exposure.coverage_cycle,excluded.coverage_cycle),
  topic=excluded.topic,last_session_id=excluded.last_session_id;
 end loop;
 return true;
end $function$
;
