-- DRAFT ONLY. Do not apply before verifying the project's global Storage limit.
-- This dedicated private bucket is sized for complete textbooks up to 500 MiB.
-- TUS transfers chunks but DOES NOT bypass the global per-object size limit.
-- This statement is safe to retry and fails if an existing bucket is misconfigured.
insert into storage.buckets (id,name,public,file_size_limit,allowed_mime_types)
values ('ai-textbook-sources','ai-textbook-sources',false,524288000,array['application/pdf']::text[])
on conflict (id) do nothing;

do $$
begin
 if not exists (
  select 1 from storage.buckets
  where id='ai-textbook-sources' and public=false
    and file_size_limit=524288000
    and allowed_mime_types=array['application/pdf']::text[]
 ) then
  raise exception 'ai-textbook-sources bucket configuration mismatch';
 end if;
end $$;

-- No storage.objects policies are granted to browser roles.
-- Never expose service-role credentials to browser TUS clients.
-- Use a server-authorized resumable transfer with an appropriate restricted
-- upload credential; verify access control and ownership before enabling.
