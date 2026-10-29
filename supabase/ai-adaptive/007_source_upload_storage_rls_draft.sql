-- DRAFT ONLY: security review and isolated integration testing required.
-- Prerequisites: private.ai_source_upload_intents (006), private bucket (004).
-- Browser may INSERT only a PDF at the exact path of its own active upload intent.
-- No browser SELECT/UPDATE/DELETE policy is created for this bucket.
-- Storage TUS authorization behavior must be verified before enabling in production.

create or replace function private.can_insert_ai_source_object(
 p_bucket text, p_path text
) returns boolean
language sql stable security definer
set search_path = ''
as $$
 select p_bucket = 'ai-textbook-sources'
   and (select auth.uid()) is not null
   and exists (
    select 1 from private.ai_source_upload_intents i
    where i.actor_id = (select auth.uid())
      and i.storage_bucket = p_bucket
      and i.storage_path = p_path
      and i.mime_type = 'application/pdf'
      and i.status = 'uploading'
      and i.expires_at > now()
   );
$$;

revoke all on function private.can_insert_ai_source_object(text,text) from public;
revoke all on function private.can_insert_ai_source_object(text,text) from anon;
grant execute on function private.can_insert_ai_source_object(text,text) to authenticated;

drop policy if exists ai_source_intent_insert on storage.objects;
create policy ai_source_intent_insert on storage.objects
 for insert to authenticated
 with check (
  bucket_id = 'ai-textbook-sources'
  and private.can_insert_ai_source_object(bucket_id,name)
 );

-- Do not grant upsert, read, list, update, or delete to browser roles.
-- Never use user_metadata as an authorization source.
-- Server-side finalizer validates object bytes and digest before registration.
