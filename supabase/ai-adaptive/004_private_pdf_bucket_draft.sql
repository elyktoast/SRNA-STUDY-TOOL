-- DRAFT ONLY. Review and apply separately after the private source tables are ready.
-- This bucket is distinct from the existing source-materials bucket.
-- 40 MiB matches the currently observed source-materials bucket limit; it is NOT
-- a guarantee about the project's global Storage limit.
-- For larger textbooks, first confirm/raise the project's global upload limit
-- and adjust both this bucket and the backend request size together.
insert into storage.buckets (id,name,public,file_size_limit,allowed_mime_types)
values ('ai-textbook-sources','ai-textbook-sources',false,41943040,array['application/pdf']::text[])
on conflict (id) do nothing;

-- Fail closed on configuration drift; do not silently modify an existing bucket.
do $$
begin
 if not exists (
  select 1 from storage.buckets
  where id='ai-textbook-sources'
    and public=false
    and file_size_limit=41943040
    and allowed_mime_types=array['application/pdf']::text[]
 ) then
  raise exception 'ai-textbook-sources bucket settings require manual review';
 end if;
end $$;

-- No policies granting anon/authenticated read/write access are created here.
-- Trusted server uses a privileged Storage client only after admin verification.
-- Before applying, inspect existing storage.objects policies and the global
-- Storage upload limit. Run negative access tests afterward.
